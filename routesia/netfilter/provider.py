"""
routesia/interface/provider.py - Netfilter provider
"""

import logging

from routesia.config.provider import ConfigProvider
from routesia.injector import Provider
from routesia.netfilter.config import NetfilterConfig
from routesia.netfilter.nftables import Nftables
from routesia.netfilter import netfilter_pb2
from routesia.rpc.provider import RPCProvider


logger = logging.getLogger(__name__)


class NetfilterProvider(Provider):
    def __init__(self, config: ConfigProvider, rpc: RPCProvider):
        self.config = config
        self.rpc = rpc
        self.nft = Nftables()
        self.applied = False

    def on_config_change(self, config):
        self.apply()

    def apply(self):
        if not self.config.data.netfilter.enabled:
            if self.applied:
                # Just disabled
                self.flush()
            return

        logger.info("Applying nftables")
        config = NetfilterConfig(self.config.data.netfilter)
        self.nft.cmd(str(config))
        self.applied = True

    def flush(self):
        logger.info("Flushing nftables")
        self.nft.cmd("flush ruleset")

    def load(self):
        self.config.register_change_handler(self.on_config_change)

    def startup(self):
        self.rpc.register("/netfilter/config/get", self.rpc_config_get)
        self.rpc.register("/netfilter/config/update", self.rpc_config_update)
        self.apply()

    def shutdown(self):
        self.flush()

    def rpc_config_get(self, msg: None) -> netfilter_pb2.NetfilterConfig:
        return self.config.staged_data.netfilter

    def rpc_config_update(self, msg: netfilter_pb2.NetfilterConfig) -> None:
        self.config.staged_data.netfilter.CopyFrom(msg)
