"""
routesia/command.py - Command line support
"""

import paho.mqtt.client as mqtt

from routesia.injector import Provider


class CommandHandler:
    def __init__(self):
        self.sub_handlers = {}

    def get_sub_handler(self, name):
        return self.sub_handlers[name]

    def register_sub_handler(self, name, handler):
        self.sub_handlers[name] = handler

    def get_commands(self):
        return self.sub_handlers.keys()


class ShowHandler(CommandHandler):
    def __init__(self):
        super().__init__()
        self.handlers = {}

    def handle(self, *args):
        raise NotImplementedError


class Command(CommandHandler, Provider):
    def __init__(self, host='localhost', port=1883):
        super().__init__()
        self.register_sub_handler('show', ShowHandler())
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

    def on_connect(self, client, obj, flags, rc):
        print("Connected to broker")

    def on_message(self, client, obj, msg):
        pass

    def mqtt_thread(self):
        pass
