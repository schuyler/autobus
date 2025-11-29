import autobus
import pytest
import asyncio

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

    # No URL = UDP multicast by default
    await autobus.start()
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

    await autobus.start()
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

    await autobus.start()
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

    await autobus.start()
    for n in range(5):
        autobus.publish(Ping(id=n))
    await asyncio.sleep(0.1)

    autobus.unsubscribe(Ping, receive_pings)
    for n in range(5, 10):
        autobus.publish(Ping(id=n))
    await asyncio.sleep(0.1)
    await autobus.stop()

    assert received == list(range(5))

@pytest.mark.asyncio
async def test_explicit_udp_url():
    received = []

    @autobus.subscribe(Ping)
    def receive_pings(ping):
        received.append(ping.id)

    # Explicit UDP URL
    await autobus.start(url="udp://239.255.0.1:5000")
    for n in range(3):
        autobus.publish(Ping(id=n))
    await asyncio.sleep(0.1)
    await autobus.stop()

    assert received == list(range(3))

@pytest.mark.asyncio
async def test_namespace_isolation():
    received_a = []
    received_b = []

    # Create two separate clients with different namespaces
    client_a = autobus.Client(namespace="ns_a")
    client_b = autobus.Client(namespace="ns_b")

    @client_a.subscribe(Ping)
    def receive_a(ping):
        received_a.append(ping.id)

    @client_b.subscribe(Ping)
    def receive_b(ping):
        received_b.append(ping.id)

    await client_a.start()
    await client_b.start()

    # Publish to namespace A only
    client_a.publish(Ping(id=1))
    client_a.publish(Ping(id=2))
    await asyncio.sleep(0.1)

    await client_a.stop()
    await client_b.stop()

    assert received_a == [1, 2]
    assert received_b == []
