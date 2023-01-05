import autobus
import pytest
import asyncio

from autobus import every

counter = 0

@pytest.mark.asyncio
async def test_scheduler():
    @autobus.schedule(every(0.25).seconds)
    def add_one():
        global counter
        counter += 1

    await autobus.start()
    await asyncio.sleep(1.1)
    await autobus.stop()

    assert counter == 4
