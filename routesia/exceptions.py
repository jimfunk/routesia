"""
routesia/exceptions.py - Exceptions for Routesia
"""


class RoutesiaException(Exception):
    pass


class InvalidProvider(RoutesiaException):
    pass


class EntityNotFound(RoutesiaException):
    pass


class RPCException(RoutesiaException):
    pass


class RPCUnspecifiedError(RPCException):
    pass


class RPCHandlerNotFound(RPCException):
    pass


class RPCEntityNotFound(RPCException):
    pass


class CommandError(RoutesiaException):
    pass
