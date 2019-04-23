"""
routesia/mqtt.py - MQTT broker
"""

import paho.mqtt.client as mqtt

from routesia.injector import Provider


class MQTT(Provider):
    def __init__(self, host='localhost', port=1883):
        super().__init__()
        self.host = host
        self.port = port
        self.subscribers = {}
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.host, port=self.port)

    def on_connect(self, client, obj, flags, rc):
        print("Connected to broker")

    def on_message(self, client, obj, message):
        for topic, callbacks in self.subscribers:
            if mqtt.topic_matches_sub(topic, message.topic):
                for callback in callbacks:
                    callback(message)

    def subscribe(self, topic, callback, qos=0):
        if topic in self.subscribers:
            self.subscribers[topic].append(callback)
        else:
            self.subscribers[topic] = [callback]
            self.client.subscribe(topic, qos=qos)

    def startup(self):
        self.client.loop_start()

    def shutdown(self):
        self.client.loop_stop()
