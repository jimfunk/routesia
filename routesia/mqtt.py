"""
routesia/mqtt.py - MQTT broker
"""

import asyncio
from dataclasses import dataclass
import inspect
import logging
import paho.mqtt.client as mqtt

from routesia.event import Event
from routesia.service import Provider


logger = logging.getLogger("mqtt")


@dataclass
class MQTTEvent(Event):
    topic: str
    payload: bytes = None


class MQTT(Provider):
    def __init__(self, host='localhost', port=1883, client=mqtt.Client):
        super().__init__()
        self.host = host
        self.port = port
        self.subscribers = {}
        self.client = client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.connected = False
        self.messagequeue = asyncio.Queue()

    def on_connect(self, client, obj, flags, rc):
        logger.info("Connected to MQTT broker")
        self.connected = True
        for topic in self.subscribers:
            self.client.subscribe(topic)

    def on_disconnect(self, client, obj, rc):
        logger.info("Disconnected from MQTT broker")
        self.connected = False

    def on_message(self, client, obj, message):
        self.loop.call_soon_threadsafe(self.put_message, MQTTEvent(message.topic, message.payload))

    def put_message(self, message):
        self.messagequeue.put_nowait(message)

    def subscribe(self, topic, callback):
        if topic in self.subscribers:
            self.subscribers[topic].append(callback)
        else:
            self.subscribers[topic] = [callback]
            if self.connected:
                self.client.subscribe(topic)

    def publish(self, topic, **kwargs):
        return self.client.publish(topic, **kwargs)

    async def handle_message(self, message_event):
        try:
            for topic, callbacks in self.subscribers.items():
                if mqtt.topic_matches_sub(topic, message_event.topic):
                    for callback in callbacks:
                        if inspect.iscoroutinefunction(callback):
                            await callback(message_event)
                        else:
                            callback(message_event)
        except Exception:
            logger.exception("Exception in MQTT message event handler")

    async def start(self):
        """
        Paho MQTT starts it's own thread
        """
        self.loop = asyncio.get_running_loop()
        self.client.connect_async(self.host, port=self.port)
        self.client.loop_start()

    async def stop(self):
        self.client.loop_stop()

    async def main(self):
        """
        Handle messages in the main thread
        """
        while True:
            message_event = await self.messagequeue.get()
            await self.handle_message(message_event)
