from queue import Queue, Empty
import logging
import systemd.daemon

from routesia.event import Event
from routesia.injector import Injector, Provider


logger = logging.getLogger(__name__)


class Server(Provider):
    def __init__(self):
        self.running = False

        self.injector = Injector()
        self.injector.add_provider(Server, self)

        self.event_registry = {}
        self.eventqueue = Queue()

    def add_provider(self, cls):
        self.injector.add_provider(cls, self.injector.run(cls))

    def start(self):
        if not self.running:
            self.injector.load()
            self.injector.startup()
            self.running = True

    def stop(self):
        if self.running:
            logger.info("Stopping Routesia")
            self.injector.shutdown()
            self.running = False
            logger.info("Stopped Routesia")

    def run(self):
        "Main loop for the server thread"
        systemd.daemon.notify("READY=1")
        logger.info("Starting Routesia")
        while self.running:
            try:
                self.handle_event(self.eventqueue.get(timeout=1))
            except Empty:
                pass

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
                try:
                    subscriber(event)
                except Exception:
                    logger.exception("Failure in event handler for %s" % event)
