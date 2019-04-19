from routesia.plugin import Plugin

from routesia_interface.interface import InterfaceProvider


class InterfacePlugin(Plugin):
    static_providers = [
        InterfaceProvider,
    ]
