from abc import ABC, abstractmethod
from typing import Optional

class Transport(ABC):
    """Abstract base class for autobus transport backends."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the transport backend."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the transport backend."""
        pass

    @abstractmethod
    async def publish(self, channel: str, message: str) -> None:
        """Publish a message to the specified channel."""
        pass

    @abstractmethod
    async def subscribe(self, channel: str) -> None:
        """Subscribe to a channel to receive messages."""
        pass

    @abstractmethod
    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        pass

    @abstractmethod
    async def receive(self, timeout: float = 1.0) -> Optional[tuple[str, str]]:
        """
        Receive the next message from any subscribed channel.

        Returns:
            Tuple of (channel, message) or None if timeout
        """
        pass
