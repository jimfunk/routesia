"""
routesia/mqtt.py - MQTT broker
"""

from threading import Thread
import paho.mqtt.client as mqtt

from routesia.injector import Provider


class MQTT(Provider):
    def __init__(self, host='localhost', port=1883):
        super().__init__()
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

    def on_connect(self, client, obj, flags, rc):
        print("Connected to broker")

    def on_message(self, client, obj, msg):
        pass

    def mqtt_thread(self):
        pass
