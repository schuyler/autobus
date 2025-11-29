import asyncio
from typing import Optional

from .client import Client
from .event import Event
from .transport import Transport, MulticastTransport, create_transport

client: Optional[Client] = None


def _get_client() -> Client:
    global client
    if client is None:
        client = Client()
    return client


def _reset_client() -> None:
    """Reset the global client. Primarily for testing."""
    global client
    client = None


def subscribe(event_cls):
    return _get_client().subscribe(event_cls)


def unsubscribe(event_cls, fn):
    _get_client().unsubscribe(event_cls, fn)


def schedule(job):
    def schedule_decorator(fn):
        _get_client().schedule(job, fn)
        return fn
    return schedule_decorator


def every(*args):
    return _get_client().every(*args)


def publish(event):
    _get_client().publish(event)


def start(
    namespace: str = "",
    url: Optional[str] = None,
    shared_key: Optional[str] = None
):
    """
    Start the autobus client.

    Args:
        namespace: Event namespace for channel isolation
        url: Transport URL. Supported schemes:
            - redis://host:port - Redis pub/sub
            - rediss://host:port - Redis pub/sub with TLS
            - udp://group:port - UDP multicast
            - None - defaults to UDP multicast
        shared_key: Optional Fernet encryption key for message encryption
    """
    global client
    if client is None:
        client = Client(url=url, namespace=namespace, shared_key=shared_key)
    else:
        # Update existing client's configuration
        # Setting url will invalidate cached transport if URL changed
        client.url = url
        client.namespace = namespace
        if shared_key:
            from .serializer import EncryptedSerializer
            client.serializer = EncryptedSerializer(shared_key)
    return client.start()


def stop():
    return _get_client().stop()


def run(
    namespace: str = "",
    url: Optional[str] = None,
    shared_key: Optional[str] = None
):
    """
    Run the autobus event loop (blocking).

    Args:
        namespace: Event namespace for channel isolation
        url: Transport URL. Supported schemes:
            - redis://host:port - Redis pub/sub
            - rediss://host:port - Redis pub/sub with TLS
            - udp://group:port - UDP multicast
            - None - defaults to UDP multicast
        shared_key: Optional Fernet encryption key for message encryption
    """
    global client
    if client is None:
        client = Client(url=url, namespace=namespace, shared_key=shared_key)
    else:
        # Update existing client's configuration
        # Setting url will invalidate cached transport if URL changed
        client.url = url
        client.namespace = namespace
        if shared_key:
            from .serializer import EncryptedSerializer
            client.serializer = EncryptedSerializer(shared_key)
    asyncio.run(client.run())
