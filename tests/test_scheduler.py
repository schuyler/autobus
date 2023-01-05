import autobus
import pytest
import asyncio, os

from autobus import every

counter = 0

@pytest.mark.asyncio
async def test_scheduler():
    @autobus.schedule(every(0.25).seconds)
    def add_one():
        global counter
        counter += 1

    await autobus.start(url=os.environ.get("REDIS_URL"))
    await asyncio.sleep(1.1)
    await autobus.stop()

    assert counter == 4

if "REDIS_URL" not in os.environ:
    pytest.skip("set REDIS_URL to enable tests", allow_module_level=True)