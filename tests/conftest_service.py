"""
Service fixtures
"""

import asyncio
import pytest
from typing import Type

from routesia.service import Event, Service


@pytest.fixture
def service(netns):
    return Service()


class EventWatcher:
    def __init__(self, service):
        self.service = service
        self.events = []
        self.waiters = {}

    async def handler(self, event):
        self.events.append(event)
        if event.__class__ in self.waiters:
            self.waiters[event.__class__].set_result(event)

    def subscribe(self, *event_classes):
        for event_class in event_classes:
            self.service.subscribe_event(event_class, self.handler)

    async def wait_for(self, event_class):
        future = self.service.main_loop.create_future()
        self.waiters[event_class] = future
        await future
        del self.waiters[event_class]
        return future.result()


@pytest.fixture
def eventwatcher(service):
    return EventWatcher(service)


class EventWaiter:
    def __init__(self, service: Service, event_class: Type[Event], **params):
        self.service = service
        self.event_class = event_class
        self.params = params

        self.future = asyncio.get_running_loop().create_future()
        self.service.subscribe_event(event_class, self._handle, **self.params)

    @property
    def result(self):
        return self.future.result()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.wait()

    async def wait(self):
        return await self.future

    async def _handle(self, event: Event):
        self.service.unsubscribe_event(self.event_class, self._handle, **self.params)
        self.future.set_result(event)


@pytest.fixture
def wait_for(service):
    async def waiter(event_class, **params):
        return EventWaiter(service, event_class, **params)

    return waiter
