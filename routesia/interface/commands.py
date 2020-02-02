"""
routesia/interface/commands.py - Routesia interface commands
"""
from routesia.cli.command import CLICommand, CLICommandSet
from routesia.exceptions import CommandError
from routesia.interface import interface_pb2


class ShowInterfaces(CLICommand):
    command = 'interface show'

    async def call(self, interface=None):
        data = await self.client.request('/interface/list', None)
        interfaces = interface_pb2.InterfaceList.FromString(data)
        if interface:
            for interface_object in interfaces.interface:
                if interface_object.name == interface:
                    return interface_object
            raise CommandError("No such interface: %s" % interface)
        return interfaces

    async def get_interface_completions(self, suggestion, *args, **kwargs):
        completions = []
        data = await self.client.request('/interface/list', None)
        interface_list = interface_pb2.InterfaceList.FromString(data)
        for interface in interface_list.interface:
            if interface.name.startswith(suggestion):
                completions.append(interface.name)
        return completions


class InterfaceCommandSet(CLICommandSet):
    commands = (
        ShowInterfaces,
    )
