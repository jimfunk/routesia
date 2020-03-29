"""
routesia/dhcp/server/commands/__init__.py - Routesia DHCP server command set
"""

from routesia.cli.command import CLICommandSet
from routesia.dhcp.server.commands.v4 import base
from routesia.dhcp.server.commands.v4 import client_class
from routesia.dhcp.server.commands.v4 import subnet


class DHCPServerCommandSet(CLICommandSet):
    commands = (
        base.V4ConfigInterfaceList,
        base.V4ConfigInterfaceAdd,
        base.V4ConfigInterfaceDelete,
        base.V4ConfigGlobalSettingsShow,
        base.V4ConfigGlobalSettingsUpdate,
        base.V4ConfigOptionDefinitionList,
        base.V4ConfigOptionDefinitionAdd,
        base.V4ConfigOptionDefinitionUpdate,
        base.V4ConfigOptionDefinitionDelete,
        base.V4ConfigOptionList,
        base.V4ConfigOptionAdd,
        base.V4ConfigOptionUpdate,
        base.V4ConfigOptionDelete,
        client_class.V4ConfigClientClassList,
        client_class.V4ConfigClientClassAdd,
        client_class.V4ConfigClientClassUpdate,
        client_class.V4ConfigClientClassDelete,
        client_class.V4ConfigClientClassOptionDefinitionList,
        client_class.V4ConfigClientClassOptionDefinitionAdd,
        client_class.V4ConfigClientClassOptionDefinitionUpdate,
        client_class.V4ConfigClientClassOptionDefinitionDelete,
        client_class.V4ConfigClientClassOptionList,
        client_class.V4ConfigClientClassOptionAdd,
        client_class.V4ConfigClientClassOptionUpdate,
        client_class.V4ConfigClientClassOptionDelete,
        subnet.V4ConfigSubnetList,
        subnet.V4ConfigSubnetAdd,
        subnet.V4ConfigSubnetUpdate,
        subnet.V4ConfigSubnetDelete,
        subnet.V4ConfigSubnetPoolAdd,
        subnet.V4ConfigSubnetPoolDelete,
        subnet.V4ConfigSubnetOptionList,
        subnet.V4ConfigSubnetOptionAdd,
        subnet.V4ConfigSubnetOptionUpdate,
        subnet.V4ConfigSubnetOptionDelete,
        subnet.V4ConfigSubnetReservationList,
        subnet.V4ConfigSubnetReservationAdd,
        subnet.V4ConfigSubnetReservationUpdate,
        subnet.V4ConfigSubnetReservationDelete,
    )
