import autobus
import pytest
import asyncio

class Ping(autobus.Event):
    id: int

@pytest.mark.asyncio
async def test_subscribe():
    received = []

    @autobus.subscribe(Ping)
    def receive_pings(ping):
        received.append(ping.id)

    await autobus.run()
    for n in range(5):
        autobus.publish(Ping(id=n))
    await autobus.stop()

    assert received == list(range(5))
