import autobus
import pytest
import os

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
    await autobus.stop()

    assert received == list(range(5))

if "REDIS_URL" not in os.environ:
    pytest.skip("set REDIS_URL to enable tests", allow_module_level=True)
