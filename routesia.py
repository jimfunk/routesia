#!/usr/bin/python3
#
# routesia -- Routing system
#

import logging
import pdb
import sys
import traceback

from routesia.config.provider import ConfigProvider
from routesia.dhcp.provider import DHCPProvider
from routesia.dns.cache.provider import DNSCacheProvider
from routesia.dns.authoritative.provider import AuthoritativeDNSProvider
from routesia.server import Server
from routesia.interface.provider import InterfaceProvider
from routesia.interface.address.provider import AddressProvider
from routesia.ipam.provider import IPAMProvider
from routesia.route.provider import RouteProvider
from routesia.rtnetlink.provider import IPRouteProvider
from routesia.netfilter.provider import NetfilterProvider

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    server = Server()

    server.add_provider(ConfigProvider)
    server.add_provider(IPAMProvider)
    server.add_provider(IPRouteProvider)
    server.add_provider(InterfaceProvider)
    server.add_provider(AddressProvider)
    server.add_provider(RouteProvider)
    server.add_provider(NetfilterProvider)
    server.add_provider(DHCPProvider)
    server.add_provider(DNSCacheProvider)
    server.add_provider(AuthoritativeDNSProvider)

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
