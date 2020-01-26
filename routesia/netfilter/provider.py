"""
routesia/interface/provider.py - Netfilter provider
"""

import subprocess
import tempfile

from routesia.config.provider import ConfigProvider
from routesia.injector import Provider
from routesia.netfilter.config import NetfilterConfig


class NetfilterProvider(Provider):
    def __init__(self, config: ConfigProvider):
        self.config = config

    def handle_config_update(self, old, new):
        self.apply()

    def apply(self):
        config = NetfilterConfig(self.config.data.netfilter)
        temp = tempfile.NamedTemporaryFile()
        temp.write(str(config).encode('utf8'))
        temp.flush()
        try:
            subprocess.run(['/usr/sbin/nft', '--file', temp.name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        except subprocess.CalledProcessError as e:
            print(e.stdout.decode('utf8'))
            print(e)
            print(config)

    def flush(self):
        subprocess.run(['/usr/sbin/nft', 'flush', 'ruleset'])

    def startup(self):
        self.apply()

    def shutdown(self):
        self.flush()
