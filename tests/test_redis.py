import autobus
import pytest
import os, asyncio

class Ping(autobus.Event):
    id: int

class Pong(Ping):
    pass

@pytest.mark.asyncio
async def test_subscribe():
    received = []

    @autobus.subscribe(Ping)
    def receive_pings(ping):
        received.append(ping.id)

    await autobus.start(url=os.environ.get("REDIS_URL"))
    for n in range(5):
        autobus.publish(Ping(id=n))
    await asyncio.sleep(0.1)
    await autobus.stop()

    assert received == list(range(5))

@pytest.mark.asyncio
async def test_subscribe_async():
    received = []

    @autobus.subscribe(Ping)
    async def receive_pings(ping):
        received.append(ping)
        await asyncio.sleep(0)

    await autobus.start(url=os.environ.get("REDIS_URL"))
    for n in range(5):
        autobus.publish(Ping(id=n))
    await asyncio.sleep(0.1)
    await autobus.stop()

    assert len(received) == 5

@pytest.mark.asyncio
async def test_subscribe_filter():
    received = []

    @autobus.subscribe(Ping)
    def receive_pings(ping):
        received.append(ping.id)

    await autobus.start(url=os.environ.get("REDIS_URL"))
    for n in range(5):
        autobus.publish(Pong(id=n))
    autobus.publish(Ping(id=n+1))
    await asyncio.sleep(0.1)
    await autobus.stop()

    assert received == [5]

@pytest.mark.asyncio
async def test_unsubscribe():
    received = []

    @autobus.subscribe(Ping)
    def receive_pings(ping):
        received.append(ping.id)

    await autobus.start(url=os.environ.get("REDIS_URL"))
    for n in range(5):
        autobus.publish(Ping(id=n))
    await asyncio.sleep(0.1)

    autobus.unsubscribe(Ping, receive_pings)
    for n in range(5, 10):
        autobus.publish(Ping(id=n))
    await asyncio.sleep(0.1)
    await autobus.stop()

    assert received == list(range(5))

if "REDIS_URL" not in os.environ:
    pytest.skip("set REDIS_URL to enable tests", allow_module_level=True)
