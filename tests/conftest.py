import asyncio
import pytest
import pytest_asyncio
import autobus


@pytest.fixture(scope="function")
def event_loop():
    """Create a new event loop for each test function."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
def reset_autobus():
    """Reset the global autobus client before each test."""
    autobus._reset_client()
    yield
    autobus._reset_client()
