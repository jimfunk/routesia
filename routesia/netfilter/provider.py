"""
routesia/interface/provider.py - Netfilter provider
"""

import logging
import subprocess
import tempfile

from routesia.config.provider import ConfigProvider
from routesia.injector import Provider
from routesia.netfilter.config import NetfilterConfig
from routesia.netfilter import netfilter_pb2
from routesia.rpc.provider import RPCProvider


logger = logging.getLogger(__name__)


class NetfilterProvider(Provider):
    def __init__(self, config: ConfigProvider, rpc: RPCProvider):
        self.config = config
        self.rpc = rpc

    def on_config_change(self, config):
        self.apply()

    def apply(self):
        config = NetfilterConfig(self.config.data.netfilter)
        temp = tempfile.NamedTemporaryFile()
        temp.write(str(config).encode('utf8'))
        temp.flush()
        try:
            subprocess.run(['/usr/sbin/nft', '--file', temp.name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(e.stdout.decode('utf8'))
            logger.error(e)
            logger.error(config)

    def flush(self):
        subprocess.run(['/usr/sbin/nft', 'flush', 'ruleset'])

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
