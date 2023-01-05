import asyncio
import pytest_asyncio
import autobus

@pytest_asyncio.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(autouse=True)
def reload_autobus():
    autobus.client = autobus.Client()