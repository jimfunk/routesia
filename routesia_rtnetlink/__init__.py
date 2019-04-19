"""
routesia_rtnetlink/__init__.py - RTNETLINK for Routesia
"""


from routesia.plugin import Plugin
from routesia_rtnetlink.iproute import IPRouteProvider


class RtnetlinkPlugin(Plugin):
    static_providers = [
        IPRouteProvider,
    ]
