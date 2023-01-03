import aioredis
import asyncio, json, logging 

logger = logging.getLogger('autobus')

class Client:
    def __init__(self, url="redis://localhost", namespace=""):
        self.redis_url = url
        self.namespace = namespace
        self.output = None
        self.listeners = {}
        self.event_types = {}
        self.tasks = []

    def subscribe(self, cls, fn):
        event_type = self._register(cls)
        logging.info("Subscribing %s to %s", fn.__name__, event_type)
        listeners = self.listeners.setdefault(event_type, set())
        listeners.add(fn)
    
    def unsubscribe(self, cls, fn):
        event_type = self._register(cls)
        listeners = self.listeners.get(event_type)
        if not listeners: return
        logger.info("Attempting to unsubscribe %s from %s", fn.__name__, event_type)
        listeners.discard(fn)

    def publish(self, obj):
        event_type = self._register(obj.__class__)
        channel = self._channel(obj)
        event = self._dump(obj)
        logger.debug("Publishing %s to %s", event_type, channel)
        if not self.output:
            raise Exception("Can't publish as autobus is not running yet")
        self.output.put_nowait((channel, event))

    def _channel(self, _obj): 
        return ":".join(("autobus", self.namespace, ""))

    def _load(self, blob):
        event = json.loads(blob)
        event_type = event.pop("type")
        if event_type not in self.event_types:
            return event_type, None
        cls = self.event_types[event_type]
        return event_type, cls(**event)

    def _dump(self, obj):
        event_type = obj.__class__.__name__
        event = dict(obj)
        event["type"] = event_type
        return json.dumps(event)

    def _register(self, cls):
        name = cls.__name__
        if name not in self.event_types:
            logger.info("Registering %s", name)
            self.event_types[name] = cls
        return name

    def _dispatch(self, event):
        event_type, obj = self._load(event)
        if not obj:
            logger.debug("Discarding unknown message: %s", event_type)
            return
        listeners = self.listeners.get(event_type, [])
        logger.debug("Dispatching %s to %d function(s)", event_type, len(listeners))
        for listener in listeners:
            try:
                listener(obj)
            except Exception as e:
                logger.exception("Listener failed")

    async def _transmit(self, redis):
        logger.debug("Ready to transmit events")
        while True:
            channel, event = await self.output.get()
            logger.debug("Publishing event to %s", channel)
            await redis.publish(channel, event)
            self.output.task_done()

    async def _receive(self, redis):
        logger.debug("Ready to receive events")
        async with redis.pubsub() as channel:
            await channel.subscribe(self._channel({}))
            while True:
                message = await channel.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is not None:
                    logger.debug("Event received")
                    self._dispatch(message["data"])

    def run(self):
        if self.tasks:
            logger.debug("autobus was already running; run() is a no-op")
            return
        self.output = asyncio.Queue()
        logger.info("Starting autobus (%s)", self.redis_url)
        redis = aioredis.from_url(self.redis_url, decode_responses=True)
        xmit = asyncio.create_task(self._transmit(redis), name="autobus_transmit")
        recv = asyncio.create_task(self._receive(redis), name="autobus_receive")
        self.tasks = [xmit, recv]

    async def stop(self):
        logger.info("Stopping autobus")
        await self.output.join()
        for t in self.tasks:
            t.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)