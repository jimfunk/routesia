from google.protobuf import text_format
import os

from routesia import config_pb2
from routesia.injector import Provider

SCHEMA = "1.0"


class Config(Provider):
    def __init__(self, location='/etc/routesia/config'):
        self.location = location
        self.data = config_pb2.Config()
        self.staged_data = config_pb2.Config()

        # Map of sections to providers
        self.sections = {}

        if not os.path.isdir(self.location):
            os.makedirs(self.location, 0o700)

        self.version = self.get_latest_config_version()

        if self.version is not None:
            self.load_config()
        else:
            self.init_config()

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

    def init_config(self):
        self.version = 0
        self.data.system.schema = SCHEMA
        self.data.system.version = self.version
        self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as f:
            f.write(str(self.data))

    def load_config(self):
        with open(self.config_file) as f:
            text_format.Merge(f.read(), self.data)

    def register_section(self, name, provider):
        self.sections[name] = provider
