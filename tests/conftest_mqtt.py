"""
Test MQTT broker and client
"""

import asyncio
from paho.mqtt.client import MQTTMessage, topic_matches_sub
import pytest


class MockMQTTClient:
    def __init__(self, broker, *args, **kwargs):
        self.broker = broker

    def subscribe(self, topic, qos=0):
        self.broker.subscribe(self, topic)

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.broker.publish(topic, payload)

    def connect(self, host, port=1883, keepalive=60, bind_address=""):
        cb = getattr(self, "on_connect", None)
        if cb:
            cb(self, None, 0, 0)

    def loop_read(self):
        pass

    def loop_write(self):
        pass

    def loop_misc(self) -> int:
        return 0


class MockMQTTBroker:
    def __init__(self):
        self.subscriptions = []
        self.queue = asyncio.Queue()
        self.running = False
        self.task = None

    def get_client(self, *args, **kwargs):
        return MockMQTTClient(self)

    def subscribe(self, client, topic):
        self.subscriptions.append((topic, client))

    def publish(self, topic, payload=None):
        self.queue.put_nowait((topic, payload))

    async def message_handler(self):
        try:
            while self.running:
                topic, payload = await self.queue.get()

                for sub, client in self.subscriptions:
                    if topic_matches_sub(sub, topic):
                        cb = getattr(client, "on_message", None)
                        if cb:
                            msg = MQTTMessage(0, topic.encode())
                            msg.payload = payload
                            cb(client, None, msg)
        except asyncio.CancelledError:
            pass

    async def start(self):
        loop = asyncio.get_running_loop()
        self.running = True
        self.task = loop.create_task(self.message_handler())

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            await self.task
            self.task = None


@pytest.fixture
def mqttbroker():
    return MockMQTTBroker()
