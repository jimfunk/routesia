import dbus

from routesia.injector import Provider


class SystemdProvider(Provider):
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.systemd1 = self.bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
        self.manager = dbus.Interface(self.systemd1, 'org.freedesktop.systemd1.Manager')
