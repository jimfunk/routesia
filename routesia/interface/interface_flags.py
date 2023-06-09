"""
routesia/interface/interface_flags.py - Interface flags
"""

# From linux/if.h
#
IFF_UP = 1 << 0
IFF_BROADCAST = 1 << 1
IFF_DEBUG = 1 << 2
IFF_LOOPBACK = 1 << 3
IFF_POINTOPOINT = 1 << 4
IFF_NOTRAILERS = 1 << 5
IFF_RUNNING = 1 << 6
IFF_NOARP = 1 << 7
IFF_PROMISC = 1 << 8
IFF_ALLMULTI = 1 << 9
IFF_MASTER = 1 << 10
IFF_SLAVE = 1 << 11
IFF_MULTICAST = 1 << 12
IFF_PORTSEL = 1 << 13
IFF_AUTOMEDIA = 1 << 14
IFF_DYNAMIC = 1 << 15
IFF_LOWER_UP = 1 << 16
IFF_DORMANT = 1 << 17
IFF_ECHO = 1 << 18

IFF_VOLATILE = IFF_LOOPBACK | IFF_POINTOPOINT | IFF_BROADCAST | IFF_ECHO | \
    IFF_MASTER | IFF_SLAVE | IFF_RUNNING | IFF_LOWER_UP | IFF_DORMANT
