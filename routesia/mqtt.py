"""
routesia/mqtt.py - MQTT broker
"""

import asyncio
from dataclasses import dataclass
from enum import IntEnum
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
        self.loop = asyncio.get_running_loop()
        self.client = client()
        self.client.on_socket_open = self.on_socket_open
        self.client.on_socket_close = self.on_socket_close
        self.client.on_socket_register_write = self.on_socket_register_write
        self.client.on_socket_unregister_write = self.on_socket_unregister_write
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client_task: asyncio.Task | None = None
        self.connected = False
        self.connect_future = self.loop.create_future()
        self.messagequeue = asyncio.Queue()

    async def wait_connect(self):
        """
        Wait for client to connect. If it is already connected, return immediately.
        """
        if self.connect_future:
            if self.connect_future.done():
                return
            await self.connect_future

    def on_socket_open(self, client, userdata, sock):
        self.loop.add_reader(sock, self.handle_socket_read)

    def handle_socket_read(self):
        self.client.loop_read()

    def on_socket_close(self, client, userdata, sock):
        self.loop.remove_reader(sock)

    def on_socket_register_write(self, client, userdata, sock):
        self.loop.add_writer(sock, self.handle_write)

    def handle_write(self):
        self.client.loop_write()

    def on_socket_unregister_write(self, client, userdata, sock):
        self.loop.remove_writer(sock)

    def on_connect(self, client, obj, flags, rc):
        logger.info("Connected to MQTT broker")
        self.connected = True
        for topic in self.subscribers:
            self.client.subscribe(topic)
        self.connect_future.set_result(True)

    def on_disconnect(self, client, obj, rc):
        logger.info("Disconnected from MQTT broker")
        self.connected = False

    def on_message(self, client, obj, message):
        logger.debug(f"Received {message.topic}")
        self.messagequeue.put_nowait(MQTTEvent(message.topic, message.payload))

    def subscribe(self, topic, callback):
        if topic in self.subscribers:
            self.subscribers[topic].append(callback)
        else:
            self.subscribers[topic] = [callback]
            if self.connected:
                self.client.subscribe(topic)

    def publish(self, topic, **kwargs):
        logger.debug(f"Publishing {topic}")
        return self.client.publish(topic, **kwargs)

    async def handle_message(self, message_event):
        try:
            for topic, callbacks in self.subscribers.items():
                if mqtt.topic_matches_sub(topic, message_event.topic):
                    for callback in callbacks:
                        await callback(message_event)
        except Exception:
            logger.exception("Exception in MQTT message event handler")

    async def start(self):
        """
        Start MQTT client.
        """
        self.client.connect(self.host, port=self.port)
        self.client_task = self.loop.create_task(self.client_loop(), name="MQTT provider client task")

    async def stop(self):
        if self.client_task:
            self.client_task.cancel()
            await self.client_task
            self.client_task = None

    async def client_loop(self):
        try:
            while True:
                ret = self.client.loop_misc()
                if ret != mqtt.MQTT_ERR_SUCCESS:
                    logger.error(f"MQTT loop error: {mqtt.error_string(ret)}")
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass

    async def main(self):
        try:
            while True:
                await self.handle_message(await self.messagequeue.get())
        except asyncio.CancelledError:
            pass
