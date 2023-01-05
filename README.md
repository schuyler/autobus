# autobus

Autobus is a lightweight, networked, opinionated event bus for Python 3.

Autobus leans on [Redis](https://redis.io/),
[asyncio](https://docs.python.org/3/library/asyncio.html),
[aioredis](https://aioredis.readthedocs.io/en/latest/),
[pydantic](https://docs.pydantic.dev/), and
[schedule](https://schedule.readthedocs.io/en/stable/) to do most of its heavy
lifting.

## Synopsis

```python
import autobus
import asyncio

@autobus.subcribe(MyEventClass)
def handle_my_event(event):
    # do something in response
    ...

asyncio.run(autobus.run())
```

and then elsewhere, maybe in another process entirely:

```python
event = MyEventClass(...)
autobus.publish(event)
```

Presto! The event you published in one place is transparently handled in
another.

## Installation

```sh
pip install autobus
```

or if you want to build from source,

```sh
git clone git@github.com:schuyler/autobus
cd autobus
pip install -r requirements.txt
```

You must have Redis running somewhere in order to use Autobus.

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

Currently, you don't _have_ to use `autobus.Event` as the base class for your
events -- in principle, any simple class will work, so long as you can call
`dict(obj)` and get back a dict that you can pass to the constructor. But this
may change in the future.

One other small caveat -- events are routed by their Python class name, which
means that all of your event classes must be uniquely named in order to be
routed correctly.

### Publishing an event to the bus

```python
event = SomethingHappened(...)
autobus.publish(event)
```

When `publish()` is called, the event object is serialized to JSON and sent out
over a Redis pub/sub channel. All subscribers to that event class will receive a
copy of the event object.

### Receving an event from the bus

Receving an event is as simple as using the `@autobus.subscribe` decorator:

```python
@autobus.subscribe(MyEventClass)
def handle_my_event(event):
    # do something in response
    ...
```

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

### Running the event bus

Autobus relies on [asyncio](https://docs.python.org/3/library/asyncio.html) for
concurrency. You need to have the bus running in order to send and receive
events. The easiest way to run Autobus is to pass its `run()` function to
`asyncio.run()`:

```python
import asyncio

if __name__ == "__main__":
    asyncio.run(autobus.run())
```

### Configuring the event bus

Autobus depends on Redis, and, by default, assumes that Redis is running on
`localhost:6379`. If you are running Redis somewhere else, you can pass a Redis
DSN URL to `autobus.run()`:

```python
autobus.run(url="redis://my.redis.host:6379")
```

Autobus does not use Redis for storage in any way; it only uses the
[pub/sub functions](https://redis.io/docs/manual/pubsub/).

Autobus provides no security features whatsoever. You are dependent on your
Redis configuration to secure your event bus.

If you want to run multiple, separate buses on the same Redis database, you can
configure autobus with a namespaces:

```python
autobus.run(namespace="distinct_namespace")
```

Two autobus clients with different namespaces will not be able to share
messages, which is probably what you wanted.

It is also possible to run multiple separate clients in a single process, by
instantiating and using `autobus.Client` directly.

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
def main():
    config = uvicorn.Config("main:app", port=5000, log_level="info")
    server = uvicorn.Server(config)
    redis_url = "redis://my.redis.host"
    await asyncio.gather(
        asyncio.create_task(autobus.run(url=redis_url)),
        asyncio.create_task(server.serve())
    )
```

### Long-running handlers

Python's `asyncio` provides concurrency but _not_ parallelism. Everything in an
asyncio event loop happens in the same thread. For convenience and simplicity,
all autobus handlers are treated as _synchronous_ functions -- that is, they are
not expected to be defined `async` and they are not called with `await`. This
means that, whatever your event handler is doing, it's blocking everything else
on (probably) the main thread.

This is great if your handler just transforms an event and kicks the data off
somewhere else. However, if you want an autobus handler to do something
long-running, it's best to either run it in a different thread, or (better yet)
use `asyncio.create_task()` to spawn an `async` function to do the work.

N.B. there is code to run async handlers directly from autobus, which would
obviate this issue, but this code needs additional work.

## Testing

### Running the tests

```sh
REDIS_URL=redis://localhost:6379 pytest
```

You will need Redis running in order to run the tests. Sorry. Mocking Redis
pubsub accurately in asyncio was not something I felt like bothering with.

### Redis on MacOS

Just for my future reference. You _can_ install Redis with `brew install redis`,
but if you have Docker running locally, this works too:

```sh
docker pull redis:alpine
docker run --name redis -d -p 6379:6379 redis:alpine
```

## Contributing

Patches welcome. By all means, please send pull requests!

## Todo

- Finish support for async handlers (as opposed to sync handlers, which are tested)
- Per-event-type pubsub channels (just need to do the bookkeeping)
- Pydoc API documentation

Otherwise I regard autobus as pretty feature complete.

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

Autobus was conceived and written to support Rob Flickenger's very cool
[Persyn](http://github.com/hackerfriendly/persyn) project, so you should check
that out as well.
