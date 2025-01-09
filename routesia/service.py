"""
Base service and provider framework
"""

import asyncio
from collections import OrderedDict
from contextlib import suppress
import inspect
import logging
import systemd.daemon
from typing import Callable, Type

from routesia.event import Event
from routesia.eventqueue import EventQueue


class ServiceException(Exception):
    pass


class InvalidProvider(ServiceException):
    pass


class ProviderDependencyMissing(ServiceException):
    pass


class ProviderDependencyLoop(ServiceException):
    pass


logger = logging.getLogger("service")


class Provider:
    """
    Base class for providers.

    A provider is a processing unit running within a service. It can emit or
    handle events and may have it's own main loop in a thread or coroutine.

    Providers are not intended to be initialized directly. Provider subclasses
    are passed to ``Service.add_provider()``, along with any desired keyword
    arguments to be passed on initialization. For each class, exactly one
    instance will be created.

    The ``__init__()`` method may define non-optional arguments annotated with
    ``Provider`` subclasses to indicate that the instance of that provider
    should be passed to that argument. As such, these annotations influence
    the order in which providers are initialised.

    Each provider may implement ``start()`` or ``stop()`` methods which will
    be executed before and after the main loop, respectively. The ``start()``
    methods are executed in the same order as the providers are initialized
    and the ``stop()`` methods are executed in the reverse order. These
    methods may optionally be async.

    For testing, it is sometimes useful to replace the implementation of a
    provider with a different or modified one. To make the replacement class
    be treated as the original reimplement the ``get_provider_class`` property
    class to return the class it replaces.
    """
    def __init__(self):
        pass

    @classmethod
    def get_provider_class(cls):
        return cls

    @classmethod
    def get_name(cls):
        return cls.__name__

    def start(self):
        """
        Called when the service starts
        """
        pass

    def stop(self):
        """
        Called when the service stops
        """
        pass


class EventSubscription:
    """
    Represents an event subscription.
    """
    def __init__(self, callback: Callable, params: dict):
        self.callback = callback
        self.params = params

    def match(self, event: Event):
        """
        Mach the event params.

        Only params that have been specified will be considered. If no params were
        given, all events will match.
        """
        for item, value in self.params.items():
            if getattr(event, item) != value:
                return False
        return True


class Service(Provider):
    """
    Service with dependency injected providers.

    Example::

        class MyProvider(Provider):
            async def main(self):
                while True:
                    asyncio.sleep(1)


        class AnotherProvider(Provider):
            def __init__(self, myprovider: MyProvider):
                # The instance of MyProvider is passed as the myprovider
                # argument due to the annotation
                self.myprovider = myprovider


        service = Service()
        service.add_provider(MyProvider)
        service.add_provider(AnotherProvider)
        asyncio.run(service.run())
    """
    def __init__(self):
        # Indexed by class, value is kwargs
        self.provider_classes: dict[Type[Provider], dict] = {
            self.__class__: {},
        }
        # Indexed by provider class, value is real class. Allows for provider
        # impersonation for testing
        self.provider_class_map: dict[Type[Provider], Type[Provider]] = {
            self.get_provider_class(): self.__class__,
        }
        # Provider instances, indexed by class, value is instance
        self.providers: OrderedDict[Type[Provider], Provider] = OrderedDict()

        self.main_loop: asyncio.AbstractEventLoop | None = None
        self.main_future: asyncio.Future | None = None
        self.main_task: asyncio.Task | None = None
        self.started: bool = False
        self.event_registry: dict[Type[Event], EventSubscription] = {}
        self.eventqueue = EventQueue()
        self.event_tasks: list[asyncio.Task] = []

    def add_provider(self, cls: Type[Event], **kwargs):
        """
        Add a provider class.

        If any keyword arguments are given, they are passed to the provider on
        initialization.
        """
        if not issubclass(cls, Provider):
            raise InvalidProvider
        self.provider_class_map[cls.get_provider_class()] = cls
        self.provider_classes[cls] = kwargs

    def exec(self, fn: Callable, **kwargs):
        """
        Execuite callable fn with context and providers. If an argument is
        provided via kwargs, it will be passed to the function, otherwise, the
        type annotation for the function argument is used to look up a
        provider.
        """
        if inspect.isclass(fn):
            items = fn.__init__.__annotations__.items()
        else:
            items = fn.__annotations__.items()
        for arg, cls in items:
            if issubclass(cls, Provider):
                if cls not in self.providers:
                    raise ProviderDependencyMissing(cls.__name__)
                kwargs[arg] = self.providers[cls]
        return fn(**kwargs)

    async def load_providers(self):
        """
        Load providers in order, according to their __init__ annotations.

        This can be executed multiple times to progressively load providers
        """
        # This service is a provider as well
        if self.__class__ not in self.providers:
            self.providers[self.get_provider_class()] = self

        pending_providers = list(set(self.provider_class_map.keys()) - set(self.providers.keys()))

        while pending_providers:
            len_pending = len(pending_providers)
            for provider in pending_providers:
                resolved = True
                for requirement in provider.__init__.__annotations__.values():
                    if not issubclass(requirement, Provider):
                        continue
                    if requirement not in self.provider_class_map:
                        raise ProviderDependencyMissing(f"Provider {provider.__class__.__name__} requires {requirement.__name__} but it is not available")
                    if requirement not in self.providers:
                        # Try again next iteration
                        resolved = False
                if resolved:
                    self.providers[provider] = self.exec(
                        self.provider_class_map[provider],
                        **self.provider_classes[provider],
                    )
                    pending_providers.remove(provider)
            if len_pending == len(pending_providers):
                provider_names = ", ".join([provider.get_name() for provider in pending_providers])
                raise ProviderDependencyLoop(f"Provider dependency loop detected among {provider_names}")

    async def get_provider(self, cls: Type[Provider]):
        """
        Return the instance of the provider ``cls``.
        """
        return self.providers[cls]

    async def start_providers(self):
        for provider in self.providers.values():
            if provider != self:
                logger.debug(f"Starting {provider.get_name()} provider")
                if inspect.iscoroutinefunction(provider.start):
                    await provider.start()
                else:
                    provider.start()

    async def stop_providers(self):
        for provider in reversed(self.providers.values()):
            if provider != self:
                logger.debug("Shutting down %s" % provider.__class__.__name__)
                if inspect.iscoroutinefunction(provider.stop):
                    await provider.stop()
                else:
                    provider.stop()

    async def wait_start(self):
        if self.started:
            return
        if not self.main_future:
            loop = asyncio.get_event_loop()
            self.main_future = loop.create_future()
        await self.main_future

    async def service_main(self) -> int:
        """
        Starts and runs all providers
        """
        logger.info("Starting providers")
        await self.start_providers()

        systemd.daemon.notify("READY=1")
        self.started = True
        if self.main_future:
            self.main_future.set_result(True)

        self.main_loop.add_reader(self.eventqueue, self.handle_eventqueue)

        main_tasks = []
        for provider in self.providers.values():
            if hasattr(provider, "main"):
                main_tasks.append(provider.main())

        ret = 0

        try:
            await asyncio.gather(*main_tasks)
        except asyncio.exceptions.CancelledError:
            logger.info("Service cancelled")
        except SystemExit as e:
            ret = e.code
        except KeyboardInterrupt:
            pass

        logger.info("Stopping providers")
        await self.stop_providers()

        return ret

    async def stop(self):
        for task in self.event_tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        self.event_tasks = []

    async def run(self) -> int:
        "Run the service"
        self.main_loop = asyncio.get_running_loop()
        await self.load_providers()
        return await self.service_main()

    async def start_background(self):
        """
        Run providers in a background task
        """
        self.main_loop = asyncio.get_running_loop()
        await self.load_providers()
        self.main_task = self.main_loop.create_task(self.service_main())

    async def stop_background(self):
        """
        Stop providers in the background task
        """
        if self.main_task:
            self.main_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.main_task
            self.main_task = None

    def subscribe_event(self, event_class: Type[Event], callback: Callable, **params):
        """
        Subscribe to an event. The callback must be a callable taking a single
        parameter for the event instance.

        If any ``params`` are given, the callback will only be called if the given
        parameters match the respective event properties.
        """
        if not inspect.iscoroutinefunction(callback):
            raise ServiceException("callback must be a coroutine")
        subscription = EventSubscription(callback, params)
        if event_class in self.event_registry:
            self.event_registry[event_class].append(subscription)
        else:
            self.event_registry[event_class] = [subscription]

    def unsubscribe_event(self, event_class: Type[Event], callback: Callable, **params):
        """
        Unsubscribe to an event. Parameters must match the one used for ``subscribe()``
        """
        if event_class in self.event_registry:
            subscriptions = self.event_registry[event_class]
            for index, subscription in enumerate(subscriptions):
                if subscription.callback == callback and subscription.params == params:
                    break
            else:
                # Not found
                return
            subscriptions.pop(index)

            if not subscriptions:
                del self.event_registry[event_class]

    def publish_event(self, event: Event):
        "Publish an event to listening providers"
        logger.debug(f"Publishing event: {event}")
        self.eventqueue.put(event)

    def handle_eventqueue(self):
        while True:
            try:
                event = self.eventqueue.get()
            except BlockingIOError:
                break
            task = self.main_loop.create_task(self.handle_event(event))
            self.event_tasks.append(task)

        # Clean up old tasks
        for task in self.event_tasks.copy():
            if task.done():
                self.event_tasks.remove(task)

    async def handle_event(self, event: Event):
        "Handle an event. Only called in the main thread"
        logger.debug(f"Handling event: {event}")
        if event.__class__ in self.event_registry:
            for subscriber in self.event_registry[event.__class__]:
                if subscriber.match(event):
                    try:
                        await subscriber.callback(event)
                    except Exception:
                        logger.exception("Failure in event handler for %s" % event)
