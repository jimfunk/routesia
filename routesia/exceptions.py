"""
routesia/exceptions.py - Exceptions for Routesia
"""


class RoutesiaException(Exception):
    pass


class InvalidProvider(RoutesiaException):
    pass


class CommandNotFound(RoutesiaException):\
    pass
