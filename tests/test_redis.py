import autobus
import pytest
import os, asyncio, logging

class Ping(autobus.Event):
    id: int

@pytest.mark.asyncio
async def test_subscribe():
    received = []

    @autobus.subscribe(Ping)
    def receive_pings(ping):
        received.append(ping.id)

    await autobus.start(url=os.environ.get("REDIS_URL"))
    for n in range(5):
        autobus.publish(Ping(id=n))
    await asyncio.sleep(0.01)
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
    await asyncio.sleep(0.01)
    await autobus.stop()

    assert len(received) == 5

if "REDIS_URL" not in os.environ:
    pytest.skip("set REDIS_URL to enable tests", allow_module_level=True)
