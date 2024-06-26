"""
routesia/config/provider.py - Routesia config provider
"""
from google.protobuf import text_format
import logging
import os

from routesia.schema.v1.config_pb2 import Config, CommitResult
from routesia.rpc import RPC
from routesia.service import Provider


logger = logging.getLogger("config")


SCHEMA = "1.0"


class InvalidConfig(Exception):
    pass


class ConfigProvider(Provider):
    def __init__(self, rpc: RPC, location="/etc/routesia/config"):
        self.rpc = rpc
        self.location = location

        self.data = Config()
        self.staged_data = Config()

        self.init_config_handlers = []
        self.change_handlers = []

        if not os.path.isdir(self.location):
            os.makedirs(self.location, 0o700)

        self.version = self.get_latest_config_version()

        if self.version is not None:
            self.load_config()
        else:
            self.init_config()

        self.rpc.register("config/running/get", self.rpc_get_running)
        self.rpc.register("config/staged/get", self.rpc_get_staged)
        self.rpc.register("config/staged/drop", self.rpc_drop_staged)
        self.rpc.register("config/staged/commit", self.rpc_commit)

    @property
    def config_file(self):
        return "%s/%s.conf" % (self.location, self.version)

    def get_latest_config_version(self):
        latest = None
        for filename in os.listdir(self.location):
            if "." in filename:
                base, ext = filename.split(".", 1)
                if ext == "conf" and base.isdigit():
                    version = int(base)
                    if latest is None or version > latest:
                        latest = version
        return latest

    def register_init_config_handler(self, handler):
        self.init_config_handlers.append(handler)

    def register_change_handler(self, handler):
        self.change_handlers.append(handler)

    def call_change_handlers(self):
        success = True
        for handler in self.change_handlers:
            try:
                handler(self.data)
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
        self.version = self.data.system.version
        with open(self.config_file, "w") as f:
            f.write(str(self.data))

    def load_config(self):
        with open(self.config_file) as f:
            text_format.Merge(f.read(), self.data)

    async def rpc_get_running(self) -> Config:
        return self.data

    async def rpc_get_staged(self) -> Config:
        return self.staged_data

    async def rpc_drop_staged(self) -> Config:
        self.staged_data.CopyFrom(self.data)

    async def rpc_commit(self) -> CommitResult:
        result = CommitResult()

        if self.data.SerializeToString() == self.staged_data.SerializeToString():
            result.result_code = CommitResult.COMMIT_UNCHANGED
            result.message = "No staged changes."
        else:
            previous_data = self.data
            self.data = self.staged_data
            self.data.system.version += 1

            result = CommitResult()

            if self.call_change_handlers():
                self.save_config()
                self.staged_data = Config()
                self.staged_data.CopyFrom(self.data)

                result.result_code = CommitResult.COMMIT_SUCCESS
                result.message = "Committed version %s." % self.data.system.version
            else:
                # Roll back
                self.data = previous_data
                self.call_change_handlers()
                result.result_code = CommitResult.COMMIT_ERROR
                result.message = "Failed to commit changes. Attempting rollback but the system may be in an unexpected state."

        return result

    def start(self):
        self.staged_data.CopyFrom(self.data)
