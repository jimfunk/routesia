from dataclasses import dataclass

from routesia.service import Provider, Service, Event


class FooProvider(Provider):
    def __init__(self, start_list=None, stop_list=None):
        self.start_list = start_list
        self.stop_list = stop_list

    def start(self):
        if self.start_list:
            self.start_list.append("foo")

    def stop(self):
        if self.stop_list:
            self.stop_list.append("foo")


class BarProvider(Provider):
    def __init__(self, foo: FooProvider, start_list=None, stop_list=None):
        self.start_list = start_list
        self.stop_list = stop_list

    def start(self):
        if self.start_list:
            self.start_list.append("foo")

    def stop(self):
        if self.stop_list:
            self.stop_list.append("foo")


async def test_load_providers(service):
    service.add_provider(FooProvider)
    await service.load_providers()

    assert len(service.providers) == 2
    assert Service in service.providers
    assert isinstance(service.providers[Service], Service)
    assert FooProvider in service.providers
    assert isinstance(service.providers[FooProvider], FooProvider)


async def test_load_providers_requirement(service):
    service.add_provider(BarProvider)
    service.add_provider(FooProvider)
    await service.load_providers()

    assert len(service.providers) == 3
    assert FooProvider in service.providers
    assert isinstance(service.providers[FooProvider], FooProvider)
    assert BarProvider in service.providers
    assert isinstance(service.providers[BarProvider], BarProvider)


@dataclass
class FooEvent(Event):
    data: str


@dataclass
class BarEvent(Event):
    data: str


async def test_event_subscriber(service):
    future = service.main_loop.create_future()

    async def handler(event):
        future.set_result(event)

    service.subscribe_event(FooEvent, handler)
    service.publish_event(FooEvent("foo"))
    await future
    assert future.done()
    event = future.result()
    assert isinstance(event, FooEvent)
    assert event.data == "foo"


async def test_event_subscriber_wait_event(service, wait_for_event):
    async with wait_for_event(FooEvent) as waiter:
        service.publish_event(FooEvent("foo"))

    assert waiter.done()
    assert isinstance(waiter.result(), FooEvent)
    assert waiter.result().data == "foo"


async def test_event_subscriber_eventwatcher(service, eventwatcher):
    eventwatcher.subscribe(FooEvent)
    service.publish_event(FooEvent("foo"))
    event = await eventwatcher.wait_for(FooEvent)

    assert isinstance(event, FooEvent)
    assert event.data == "foo"
