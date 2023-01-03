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

    async def send_pings():
        for n in range(5):
            autobus.publish(Ping(id=n))

    autobus.run()
    await asyncio.sleep(0.1)
    await send_pings()
    await autobus.stop()

    assert received == list(range(5))
