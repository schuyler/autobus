from urllib.parse import urlparse

from .base import Transport
from .multicast import MulticastTransport


def create_transport(url: str = None) -> Transport:
    """
    Create a transport from a URL string.

    Supported schemes:
        - redis://host:port - Redis pub/sub transport
        - rediss://host:port - Redis pub/sub with TLS
        - udp://group:port - UDP multicast transport
        - None - defaults to UDP multicast

    Examples:
        create_transport("redis://localhost:6379")
        create_transport("rediss://secure.redis.host:6379")
        create_transport("udp://239.255.0.1:5000")
        create_transport()  # UDP multicast with defaults
    """
    if url is None:
        return MulticastTransport()

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme in ("redis", "rediss"):
        from .redis import RedisTransport
        return RedisTransport(url=url)
    elif scheme == "udp":
        group = parsed.hostname or "239.255.0.1"
        port = parsed.port or 5000
        return MulticastTransport(group=group, port=port)
    else:
        raise ValueError(f"Unknown transport scheme: {scheme}")


__all__ = ["Transport", "MulticastTransport", "create_transport"]

# Note: RedisTransport is intentionally not in __all__ to avoid import errors
# when redis is not installed. Use create_transport("redis://...") or import directly:
#   from autobus.transport.redis import RedisTransport
