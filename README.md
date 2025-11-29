# autobus

Autobus is a lightweight, networked, opinionated event bus for Python 3.

Autobus supports two transport backends:
- **UDP multicast** (default) - Zero configuration, no external dependencies
- **Redis pub/sub** - For distributed systems across network boundaries

It also leans on [asyncio](https://docs.python.org/3/library/asyncio.html),
[pydantic](https://docs.pydantic.dev/), and
[schedule](https://schedule.readthedocs.io/en/stable/) to do most of its heavy
lifting.

## Synopsis

```python
import autobus
import asyncio

@autobus.subscribe(MyEventClass)
def handle_my_event(event):
    # do something in response
    ...

autobus.run()
```

and then elsewhere, maybe in another process entirely:

```python
event = MyEventClass(...)
autobus.publish(event)
autobus.run()
```

Presto! The event you published in one place is transparently handled in
another.

## Installation

```sh
pip install autobus
```

For Redis transport support:

```sh
pip install autobus[redis]
```

If you want to build from source:

```sh
git clone https://github.com/schuyler/autobus
cd autobus
pip install -e .
```

## Usage

### Defining events

```python
import autobus

class SomethingHappened(autobus.Event):
    id: int
    name: str
    details: dict
    ...
```

Now `autobus.Event` is just a subclass of `pydantic.BaseModel`, so anything
[Pydantic](https://docs.pydantic.dev/usage/models/) can do, `autobus.Event` can
do also.

### Publishing an event to the bus

```python
event = SomethingHappened(...)
autobus.publish(event)
```

When `publish()` is called, the event object is serialized to JSON and sent out
over the transport. All subscribers to that event class will receive a
copy of the event object.

### Receving an event from the bus

Receving an event is as simple as using the `@autobus.subscribe` decorator:

```python
@autobus.subscribe(MyEventClass)
def handle_my_event(event):
    # do something in response
    ...
```

The event handler can be either a regular Python function or an `async`
function. If the latter, the `async` function is run with
`asyncio.create_task()` and later awaited.

Either way, the event handler's return value is discarded.

### Running recurring tasks

Autobus uses the [Schedule](https://schedule.readthedocs.io/en/stable/) module
to run tasks on a recurring basis.

```python
from autobus import every

@autobus.schedule(every(10).minutes)
def do_this_regularly():
    # this will get called ~every 10 minutes
    ...
```

As with event handlers, the scheduled function can be regular or `async`, and
the return value is discarded.

### Running the event bus itself

Autobus relies on [asyncio](https://docs.python.org/3/library/asyncio.html) for
concurrency. You need to have the bus running in order to send and receive
events. The easiest way to run Autobus is to pass its `run()` function to
`asyncio.run()`:

```python
import asyncio

if __name__ == "__main__":
    autobus.run()
```

## Configuration

### Transport backends

Autobus supports two transport backends, selected via URL scheme:

#### UDP Multicast (default)

UDP multicast requires no external services and works out of the box for
processes on the same network segment:

```python
# Default - uses UDP multicast on 239.255.0.1:5000
autobus.run()

# Explicit UDP configuration
autobus.run(url="udp://239.255.0.1:5000")
```

**Note:** UDP multicast has a message size limit of approximately 64KB. For
larger messages, use the Redis transport.

#### Redis pub/sub

For distributed systems across network boundaries, use Redis:

```python
autobus.run(url="redis://my.redis.host:6379")

# Redis with TLS
autobus.run(url="rediss://secure.redis.host:6379")
```

Autobus does not use Redis for storage in any way; it only uses the
[pub/sub functions](https://redis.io/docs/manual/pubsub/).

**Note:** Redis transport requires the `redis` package. Install with
`pip install autobus[redis]`.

### Adding an application namespace

If you want to run multiple, separate buses on the same transport, you can
configure autobus with a namespace:

```python
autobus.run(namespace="distinct_namespace")
```

Two autobus clients with different namespaces will not be able to share
messages, which is probably what you wanted.

### Encrypting events over the bus

Finally, you can optionally encrypt events sent over the bus using a shared key:

```python
autobus.run(shared_key=my_shared_key)
```

If a `shared_key` is supplied, autobus will use symmetric Fernet encryption for
all events sent and received on the bus. Any events received by autobus which
cannot be decrypted and verified using the supplied key will be discarded.

This functionality relies on [Fernet](https://cryptography.io/en/latest/fernet/)
from the Python [cryptography](https://cryptography.io/en/latest/) module, which
must be installed for `shared_key` to work.

To generate a key suitable for shared encryption, run this command from the
command line, and then supply the Base64 string it prints out to your autobus
application:

```sh
python -m autobus.serializer generate
```

## Operation

### Logging and exception handling

Autobus relies on Python's built-in
[logging](https://docs.python.org/3/howto/logging.html) facility. You can set
the log level, et cetera, using `logging.basicConfig(...)` in the usual way, and
get different degrees of detail from inside autobus.

Autobus attempts to catch exceptions thrown inside handler functions. Any
exceptions will get logged along with tracebacks using `logging.exception()`.

### Running alongside other asyncio applications

Autobus is designed to play nicely with other asyncio applications.

`autobus.run()` is basically a wrapper for:

```python
try:
    await autobus.start()
    # ... wait until told to stop ...
finally:
    await autobus.stop()
```

Instead of calling `run()`, you can call `start()` and `stop()` as needed.
Currently an autobus client cannot be restarted.

Suppose you have an API server that emits events, and so you want to run autobus
and uvicorn in the same process. Following [this
example](https://www.uvicorn.org/#uvicornrun) from the uvicorn docs, you could
do something like:

```python
async def main():
    config = uvicorn.Config("main:app", port=5000, log_level="info")
    server = uvicorn.Server(config)

    try:
        await autobus.start()
        await server.serve()
    finally:
        await autobus.stop()

asyncio.run(main())
```

It is also possible to run multiple autobus clients in a single process, by
instantiating and using `autobus.Client` directly.

```python
async def main():
    client = autobus.Client(...)
    try:
        await client.start()
    finally:
        await client.stop()

asyncio.run(main())
```

### Long-running handlers

Python's `asyncio` provides concurrency but _not_ parallelism. Everything runs
in a single thread by default. If you want your event handlers and scheduled
functions to be non-blocking, you should consider defining them `async` and
having them `await` as appropriate.

### Caveats on event definition

Currently, you don't _have_ to use `autobus.Event` as the base class for your
events -- in principle, any simple class will work, so long as you can call
`dict(obj)` and get back a dict that you can pass as keyword args to the
constructor.

Two other small caveats apply:

- Events are routed by their Python class name, which means that all of your
  event classes must be uniquely named in order to be routed correctly.
- Autobus adds a _type_ key to the return value from `dict(event)` before
  serializing the result, so that the event can be identified on the other end.
  (You aren't using `type` as the name of an instance property in Python,
  are you?)

## Testing

### Running the tests

```sh
# Run UDP multicast tests (no external dependencies)
pytest tests/test_multicast.py

# Run Redis tests (requires Redis)
REDIS_URL=redis://localhost:6379 pytest tests/test_redis.py
```

### Redis on MacOS

Just for my future reference. You _can_ install Redis with `brew install redis`,
but if you have Docker running locally, this works too:

```sh
docker pull redis:alpine
docker run --name redis -d -p 6379:6379 redis:alpine
```

## Contributing

I regard autobus as essentially feature complete, so a lack of recent releases
just means that no one's reported any bugs.

That said, patches are welcome. By all means, please send pull requests!

## License

MIT. See [LICENSE.md](LICENSE.md) for details.

## References

Autobus was significantly inspired by [Lightbus](https://lightbus.org/latest/).
Lightbus is more feature rich than Autobus, and, honestly, Adam Charnock not
only has a Discord chat but he actually publishes a phone number and encourages
you to call him if you want to talk about the project. You should probably use
Lightbus instead of Autobus. For myself. I wanted something similar to Lightbus
but simpler, and I thought it would be fun to write my own, which it was. So
here we are.

Thanks to [@javawizard](https://github.com/javawizard) for donating ownership
of the `autobus` project in PyPI.

Autobus was conceived and written to support AI chatbot experiments in
collaboration with [@hackerfriendly](https://github.com/hackerfriendly). Thanks
as always for the collaboration, Rob!
