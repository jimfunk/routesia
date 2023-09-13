"""
routesia/systemd/provider.py - SystemD support
"""
import dbus

from routesia.service import Provider


class SystemdProvider(Provider):
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.systemd1 = self.bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
        self.manager = dbus.Interface(self.systemd1, 'org.freedesktop.systemd1.Manager')

    def start_unit(self, unit):
        self.manager.RestartUnit(unit, "replace")

    def stop_unit(self, unit):
        self.manager.StopUnit(unit, "replace")
