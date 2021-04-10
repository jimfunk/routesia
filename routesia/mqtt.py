"""
routesia/mqtt.py - MQTT broker
"""

import logging
import paho.mqtt.client as mqtt

from routesia.injector import Provider


logger = logging.getLogger(__name__)


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

    def on_connect(self, client, obj, flags, rc):
        logger.info("Connected to MQTT broker")
        self.connected = True
        for topic in self.subscribers:
            self.client.subscribe(topic)

    def on_disconnect(self, client, obj, rc):
        logger.info("Disconnected from MQTT broker")
        self.connected = False

    def on_message(self, client, obj, message):
        try:
            for topic, callbacks in self.subscribers.items():
                if mqtt.topic_matches_sub(topic, message.topic):
                    for callback in callbacks:
                        callback(message)
        except Exception as e:
            logger.exception(e)
            raise

    def subscribe(self, topic, callback):
        if topic in self.subscribers:
            self.subscribers[topic].append(callback)
        else:
            self.subscribers[topic] = [callback]
            if self.connected:
                self.client.subscribe(topic)

    def publish(self, topic, **kwargs):
        return self.client.publish(topic, **kwargs)

    def startup(self):
        self.client.connect_async(self.host, port=self.port)
        self.client.loop_start()

    def shutdown(self):
        self.client.loop_stop()
