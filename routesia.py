#!/usr/bin/python3
#
# routesia -- Routing system
#

import pdb
import sys
import traceback

from routesia.config import Config
from routesia.command import CommandProvider
from routesia.dhcp.dhcp import DHCPProvider
from routesia.server import Server
from routesia.interface.interface import InterfaceProvider
from routesia.interface.address.address import AddressProvider
from routesia.ipam.ipam import IPAMProvider
from routesia.rtnetlink.iproute import IPRouteProvider
from routesia.netfilter.netfilter import NetfilterProvider

if __name__ == '__main__':
    server = Server()

    server.add_provider(CommandProvider)
    server.add_provider(Config)
    server.add_provider(IPAMProvider)
    server.add_provider(IPRouteProvider)
    server.add_provider(InterfaceProvider)
    server.add_provider(AddressProvider)
    server.add_provider(NetfilterProvider)
    server.add_provider(DHCPProvider)

    server.start()
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    except:
        extype, value, tb = sys.exc_info()
        traceback.print_exc()
        pdb.post_mortem(tb)
    finally:
        server.stop()
