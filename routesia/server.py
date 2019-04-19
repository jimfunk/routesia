import paho.mqtt.client as mqtt
from queue import Queue

from routesia.event import Event


class Server:
    def __init__(self, host='localhost', port=1883):
        self.host = host
        self.port = port
        self.running = False

        self.event_registry = {}
        self.eventqueue = Queue()
        self.broker = mqtt.Client('core.server')

    def start(self):
        if not self.running:
            self.broker.connect(self.host, self.port)
            self.broker.loop_start()
            self.running = True

    def stop(self):
        if self.running:
            self.broker.loop_stop()
            self.running = False

    def run(self):
        "Main loop for the server thread"
        while self.running:
            self.handle_event(self.eventqueue.get())

    def subscribe_event(self, event_class, subscriber):
        """Subscribe to an event. The subscriber must be a callable taking a
        single parameter for the event instance."""
        if event_class in self.event_registry:
            self.event_registry[event_class].append(subscriber)
        else:
            self.event_registry[event_class] = [subscriber]

    def publish_event(self, event: Event):
        "Publish an event to listening providers"
        self.eventqueue.put(event)

    def handle_event(self, event):
        "Handle an event. Only called in the main thread"
        if event.__class__ in self.event_registry:
            for subscriber in self.event_registry[event.__class__]:
                subscriber(event)
