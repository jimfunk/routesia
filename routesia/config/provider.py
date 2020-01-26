"""
routesia/config/provider.py - Routesia config provider
"""
from google.protobuf import text_format
import logging
import os

from routesia.config import config_pb2
from routesia.rpc.provider import RPCProvider
from routesia.injector import Provider


logger = logging.getLogger(__name__)


SCHEMA = "1.0"


class ConfigProvider(Provider):
    def __init__(self, rpc: RPCProvider, location='/etc/routesia/config'):
        self.rpc = rpc
        self.location = location

        self.data = config_pb2.Config()
        self.staged_data = config_pb2.Config()

        self.init_config_handlers = set()
        self.change_handlers = set()

    @property
    def config_file(self):
        return '%s/%s.conf' % (self.location, self.version)

    def get_latest_config_version(self):
        latest = None
        for filename in os.listdir(self.location):
            if '.' in filename:
                base, ext = filename.split('.', 1)
                if ext == 'conf' and base.isdigit():
                    version = int(base)
                    if latest is None or version > latest:
                        latest = version
        return latest

    def register_init_config_handler(self, handler):
        self.init_config_handlers.add(handler)

    def register_change_handler(self, handler):
        self.change_handlers.add(handler)

    def call_change_handlers(self, old, new):
        success = True
        for handler in self.change_handlers:
            try:
                handler(old, new)
            except Exception:
                logger.exception("Change handler failed (%s)" % handler)
                success = False
        return success

    def init_config(self):
        self.version = 0
        self.data.system.schema = SCHEMA
        self.data.system.version = self.version
        for hook in self.init_config_handlers:
            hook(self.data)
        self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as f:
            f.write(str(self.data))

    def load_config(self):
        with open(self.config_file) as f:
            text_format.Merge(f.read(), self.data)

    def load(self):
        if not os.path.isdir(self.location):
            os.makedirs(self.location, 0o700)

        self.version = self.get_latest_config_version()

        if self.version is not None:
            self.load_config()
        else:
            self.init_config()

    def rpc_get_running(self, msg):
        return self.data

    def rpc_get_staged(self, msg):
        return self.staged_data

    def rpc_commit(self, msg):
        result = config_pb2.CommitResult()

        if self.data.SerializeToString() == self.staged_data.SerializeToString():
            result.result_code = config_pb2.CommitResult.COMMIT_UNCHANGED
            result.message = 'No staged changes.'
        else:
            previous_data = self.data
            self.data = self.staged_data
            self.data.system.version += 1

            result = config_pb2.CommitResult()

            if self.call_change_handlers(previous_data, self.data):
                result.result_code = config_pb2.CommitResult.COMMIT_SUCCESS
                result.message = 'Committed version %s.' % self.data.system.version
            else:
                result.result_code = config_pb2.CommitResult.COMMIT_ERROR
                result.message = 'Committed version %s but application failed. The system may be in an unexpected state.' % self.data.system.version

        return result

    def startup(self):
        self.staged_data.CopyFrom(self.data)

        # Register RPC methods
        #
        self.rpc.register('/config/running/get', self.rpc_get_running)
        self.rpc.register('/config/staged/get', self.rpc_get_staged)
        self.rpc.register('/config/staged/commit', self.rpc_commit)
