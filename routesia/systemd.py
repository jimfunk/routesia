"""
routesia/systemd/provider.py - SystemD support
"""
import dbus
import logging

from routesia.service import Provider


logger = logging.getLogger("systemd")


class SystemdProvider(Provider):
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.systemd1 = self.bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
        self.manager = dbus.Interface(self.systemd1, 'org.freedesktop.systemd1.Manager')

    def start_unit(self, unit):
        logger.info(f"Starting unit {unit}")
        self.manager.RestartUnit(unit, "replace")

    def stop_unit(self, unit):
        logger.info(f"Stopping unit {unit}")
        self.manager.StopUnit(unit, "replace")
