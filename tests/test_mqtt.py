from routesia.mqtt import MQTTEvent


async def test_handler(mqtt, mqttbroker, service):
    events = []
    future = service.main_loop.create_future()

    async def handler(event):
        events.append(event)
        future.set_result(True)

    mqtt.subscribe("foo", handler)

    mqttbroker.publish("foobar", "baz")
    mqttbroker.publish("foo", "bar")

    await future
    assert len(events) == 1
    assert isinstance(events[0], MQTTEvent)
    assert events[0].topic == "foo"
    assert events[0].payload == "bar"
