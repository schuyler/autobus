import asyncio
import json
import logging
import socket
import struct
from typing import Optional

from .base import Transport

logger = logging.getLogger('autobus.transport.multicast')


# Python 3.11+ has loop.sock_sendto() and loop.sock_recvfrom()
# For older versions, we need compatibility shims using add_reader/add_writer
async def _sock_sendto_compat(loop, sock, data, addr):
    """Compatibility wrapper for loop.sock_sendto() on Python < 3.11."""
    if hasattr(loop, 'sock_sendto'):
        return await loop.sock_sendto(sock, data, addr)

    future = loop.create_future()
    fd = sock.fileno()

    def callback():
        try:
            result = sock.sendto(data, addr)
            loop.remove_writer(fd)
            if not future.done():
                future.set_result(result)
        except BlockingIOError:
            pass  # Socket not ready, will try again
        except Exception as e:
            loop.remove_writer(fd)
            if not future.done():
                future.set_exception(e)

    loop.add_writer(fd, callback)
    try:
        return await future
    except asyncio.CancelledError:
        loop.remove_writer(fd)
        raise


async def _sock_recvfrom_compat(loop, sock, bufsize):
    """Compatibility wrapper for loop.sock_recvfrom() on Python < 3.11."""
    if hasattr(loop, 'sock_recvfrom'):
        return await loop.sock_recvfrom(sock, bufsize)

    future = loop.create_future()
    fd = sock.fileno()

    def callback():
        try:
            data, addr = sock.recvfrom(bufsize)
            loop.remove_reader(fd)
            if not future.done():
                future.set_result((data, addr))
        except BlockingIOError:
            pass  # Socket not ready, will try again
        except Exception as e:
            loop.remove_reader(fd)
            if not future.done():
                future.set_exception(e)

    loop.add_reader(fd, callback)
    try:
        return await future
    except asyncio.CancelledError:
        loop.remove_reader(fd)
        raise


# Maximum safe UDP payload size (64KB minus headers, with some margin)
MAX_UDP_PAYLOAD = 65000

# Maximum number of messages to buffer before blocking
MAX_QUEUE_SIZE = 10000


def _is_valid_multicast_address(address: str) -> bool:
    """Check if an IP address is in the valid multicast range (224.0.0.0 - 239.255.255.255)."""
    try:
        octets = [int(x) for x in address.split('.')]
        if len(octets) != 4:
            return False
        return 224 <= octets[0] <= 239
    except (ValueError, AttributeError):
        return False


class MulticastTransport(Transport):
    """
    UDP multicast transport backend.

    Note: UDP has a maximum payload size of approximately 64KB. Messages larger
    than this will raise a ValueError.
    """

    def __init__(
        self,
        group: str = "239.255.0.1",
        port: int = 5000,
        ttl: int = 1
    ):
        if not _is_valid_multicast_address(group):
            raise ValueError(
                f"Invalid multicast address: {group}. "
                "Must be in range 224.0.0.0 - 239.255.255.255"
            )

        self.group = group
        self.port = port
        self.ttl = ttl

        self._send_socket: Optional[socket.socket] = None
        self._recv_socket: Optional[socket.socket] = None
        self._message_queue: Optional[asyncio.Queue] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._subscribed_channels: set[str] = set()
        self._channels_lock: Optional[asyncio.Lock] = None
        self._connected = False

    async def connect(self) -> None:
        if self._connected:
            logger.warning("Multicast transport already connected")
            return

        logger.info("Initializing multicast transport on %s:%d", self.group, self.port)
        self._message_queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        self._channels_lock = asyncio.Lock()

        # Create send socket
        self._send_socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )
        self._send_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.ttl)
        self._send_socket.setblocking(False)

        # Create receive socket
        self._recv_socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )
        self._recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # SO_REUSEPORT allows multiple processes to bind to the same port
        if hasattr(socket, 'SO_REUSEPORT'):
            self._recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self._recv_socket.bind(('', self.port))

        # Join multicast group
        mreq = struct.pack("4sl", socket.inet_aton(self.group), socket.INADDR_ANY)
        self._recv_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self._recv_socket.setblocking(False)

        # Start receive loop
        self._receive_task = asyncio.create_task(
            self._receive_loop(), name="multicast_receive"
        )
        self._connected = True

    async def disconnect(self) -> None:
        if not self._connected:
            return

        logger.info("Shutting down multicast transport")

        # Cancel receive task
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # Leave multicast group and close receive socket
        if self._recv_socket:
            try:
                mreq = struct.pack("4sl", socket.inet_aton(self.group), socket.INADDR_ANY)
                self._recv_socket.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
            except OSError:
                pass
            self._recv_socket.close()
            self._recv_socket = None

        # Close send socket
        if self._send_socket:
            self._send_socket.close()
            self._send_socket = None

        self._subscribed_channels.clear()
        self._message_queue = None
        self._channels_lock = None
        self._connected = False

    async def publish(self, channel: str, message: str) -> None:
        if not self._connected:
            raise RuntimeError("Multicast transport not connected")

        # Wrap message with channel info for filtering on receive
        envelope = json.dumps({"channel": channel, "data": message})
        data = envelope.encode('utf-8')

        # Check message size
        if len(data) > MAX_UDP_PAYLOAD:
            raise ValueError(
                f"Message too large for UDP transport: {len(data)} bytes "
                f"(max {MAX_UDP_PAYLOAD}). Consider using Redis transport for large messages."
            )

        logger.debug("Publishing to %s:%d (channel: %s)", self.group, self.port, channel)

        loop = asyncio.get_event_loop()
        await _sock_sendto_compat(loop, self._send_socket, data, (self.group, self.port))

    async def subscribe(self, channel: str) -> None:
        if not self._connected:
            raise RuntimeError("Multicast transport not connected")
        logger.debug("Subscribing to channel: %s", channel)
        async with self._channels_lock:
            self._subscribed_channels.add(channel)

    async def unsubscribe(self, channel: str) -> None:
        if not self._connected:
            raise RuntimeError("Multicast transport not connected")
        logger.debug("Unsubscribing from channel: %s", channel)
        async with self._channels_lock:
            self._subscribed_channels.discard(channel)

    async def receive(self, timeout: float = 1.0) -> Optional[tuple[str, str]]:
        if not self._connected:
            raise RuntimeError("Multicast transport not connected")
        try:
            return await asyncio.wait_for(self._message_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def _receive_loop(self) -> None:
        """Background task to receive from multicast socket."""
        loop = asyncio.get_event_loop()
        while True:
            try:
                data, addr = await _sock_recvfrom_compat(loop, self._recv_socket, 65535)
                envelope = json.loads(data.decode('utf-8'))
                channel = envelope.get("channel")

                # Only queue if subscribed to this channel (async-safe check)
                async with self._channels_lock:
                    is_subscribed = channel in self._subscribed_channels

                if is_subscribed:
                    await self._message_queue.put((channel, envelope["data"]))

            except asyncio.CancelledError:
                break
            except json.JSONDecodeError as e:
                logger.warning("Received malformed JSON message: %s", e)
            except UnicodeDecodeError as e:
                logger.warning("Received message with invalid encoding: %s", e)
            except Exception as e:
                logger.warning("Error receiving multicast message: %s", e)
