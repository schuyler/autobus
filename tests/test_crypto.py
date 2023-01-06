import autobus
import pytest
import os, asyncio

try:
    from cryptography.fernet import Fernet
except ImportError:
    pytest.skip("install cryptography module to run crypto tests", allow_module_level=True)

class Ping(autobus.Event):
    id: int

@pytest.mark.asyncio
async def test_subscribe_encrypted():
    client = autobus.Client(
        shared_key=Fernet.generate_key(),
        url=os.environ["REDIS_URL"]
    )
    received = []

    @client.subscribe(Ping)
    def receive_pings(ping):
        received.append(ping.id)

    await client.start()
    for n in range(5):
        client.publish(Ping(id=n))
    await asyncio.sleep(0.1)
    await client.stop()

    assert received == list(range(5))

if "REDIS_URL" not in os.environ:
    pytest.skip("set REDIS_URL to enable tests", allow_module_level=True)