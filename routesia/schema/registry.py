"""
routesia/schema/registry.py - Schema message registry
"""

from google.protobuf.message import Message
import importlib
import inspect
import pkgutil

import routesia.schema.v2
from routesia.service import Provider


class SchemaRegistryException(Exception):
    pass


class SchemaRegistry(Provider):
    def __init__(self):
        super().__init__()
        self.types = {}
        self.load_schema_package(routesia.schema.v2)

    def load_schema_package(self, package):
        for module_info in pkgutil.iter_modules(package.__path__):
            if module_info.name.endswith("_pb2"):
                module = importlib.import_module(f"{package.__package__}.{module_info.name}")
                self.load_schema_module(module)

    def load_schema_module(self, module):
        for _, cls in inspect.getmembers(module):
            if inspect.isclass(cls) and issubclass(cls, Message):
                self.types[f"{module.DESCRIPTOR.package}.{cls.DESCRIPTOR.name}"] = cls

    def get_message_type_from_type_name(self, type_name):
        try:
            return self.types[type_name]
        except KeyError:
            raise SchemaRegistryException(f"Unknown type {type_name}")
