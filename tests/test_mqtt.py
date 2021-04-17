"""
tests/test_mqtt.py
"""

from paho.mqtt.client import MQTTMessage


def test_subscribe_on_connect(mqtt):
    def fn():
        pass

    mqtt.subscribe("foo/bar", fn)
    mqtt.on_connect(mqtt.client, None, None, None)
    assert "foo/bar" in mqtt.client.subscriptions


def test_on_message(mqtt):
    calls = []

    def fn(msg):
        calls.append(msg)

    mqtt.subscribe("foo/bar", fn)
    testmsg = MQTTMessage(topic=b"foo/bar")
    mqtt.on_message(mqtt.client, None, testmsg)

    assert testmsg in calls
