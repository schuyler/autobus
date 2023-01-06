from .client import Client
from .event import Event

client = Client()

def subscribe(event_cls):
    def subscribe_decorator(fn):
        client.subscribe(event_cls, fn)
        return fn
    return subscribe_decorator

def schedule(job):
    def schedule_decorator(fn):
        client.schedule(job, fn)
        return fn
    return schedule_decorator

def every(*args):
    return client.every(*args)

def publish(event):
    client.publish(event)

def start(namespace="", url="redis://localhost"):
    client.namespace = namespace
    client.redis_url = url
    return client.start()

def stop():
    return client.stop()

def run():
    return client.run()
