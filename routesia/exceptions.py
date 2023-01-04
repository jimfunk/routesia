"""
routesia/exceptions.py - Exceptions for Routesia
"""


class RoutesiaException(Exception):
    pass


class InvalidProvider(RoutesiaException):
    pass


class ProviderLoadError(RoutesiaException):
    pass


class EntityNotFound(RoutesiaException):
    pass


class InvalidConfig(RoutesiaException):
    pass


class RPCException(RoutesiaException):
    pass


class RPCUnspecifiedError(RPCException):
    pass


class RPCHandlerNotFound(RPCException):
    pass


class RPCInvalidParameters(RPCException):
    pass


class RPCEntityNotFound(RPCException):
    pass


class RPCEntityExists(RPCException):
    pass


class CommandError(RoutesiaException):
    pass


class NftablesException(RoutesiaException):
    pass
