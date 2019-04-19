#!/usr/bin/python3
#
# routesia -- Routing system
#

from routesia.command import Command
from routesia.config import Config
from routesia.server import Server
from routesia.injector import Injector
from routesia.plugin import PluginManager

if __name__ == '__main__':
    server = Server()
    plugin_manager = PluginManager()
    plugin_manager.load_all_plugin_modules()
    plugin_manager.load_plugins()
    injector = Injector(
        plugin_manager,
        {
            Command: Command(),
            Config: Config(),
            Server: server,
        }
    )
    server.start()
    try:
        server.run()
    except KeyboardInterrupt:
        server.stop()
