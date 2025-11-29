import logging
from typing import Optional

try:
    from redis import asyncio as aioredis
except ImportError:
    try:
        import aioredis
    except ImportError:
        aioredis = None

from .base import Transport

logger = logging.getLogger('autobus.transport.redis')


class RedisTransport(Transport):
    """Redis pub/sub transport backend."""

    def __init__(self, url: str = "redis://localhost"):
        if aioredis is None:
            raise ImportError(
                "Redis transport requires the 'redis' package. "
                "Install it with: pip install autobus[redis]"
            )
        self.url = url
        self._redis = None
        self._pubsub = None
        self._connected = False

    async def connect(self) -> None:
        if self._connected:
            logger.warning("Redis transport already connected")
            return
        logger.info("Connecting to Redis at %s", self.url)
        self._redis = aioredis.from_url(self.url, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        self._connected = True

    async def disconnect(self) -> None:
        if not self._connected:
            return
        logger.info("Disconnecting from Redis")
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
        if self._redis:
            await self._redis.close()
            self._redis = None
        self._connected = False

    async def publish(self, channel: str, message: str) -> None:
        if not self._connected:
            raise RuntimeError("Not connected to Redis")
        logger.debug("Publishing to channel: %s", channel)
        await self._redis.publish(channel, message)

    async def subscribe(self, channel: str) -> None:
        if not self._connected:
            raise RuntimeError("Not connected to Redis")
        logger.debug("Subscribing to channel: %s", channel)
        await self._pubsub.subscribe(channel)

    async def unsubscribe(self, channel: str) -> None:
        if not self._connected:
            raise RuntimeError("Not connected to Redis")
        logger.debug("Unsubscribing from channel: %s", channel)
        await self._pubsub.unsubscribe(channel)

    async def receive(self, timeout: float = 1.0) -> Optional[tuple[str, str]]:
        if not self._connected:
            raise RuntimeError("Not connected to Redis")
        message = await self._pubsub.get_message(
            ignore_subscribe_messages=True,
            timeout=timeout
        )
        if message is not None:
            return (message["channel"], message["data"])
        return None
