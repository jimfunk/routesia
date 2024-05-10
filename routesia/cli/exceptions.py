"""
CLI exceptions
"""

class CommandException(Exception):
    pass


class CommandNotFound(CommandException):
    pass


class InvalidCommandDefinition(CommandException):
    pass


class InvalidArgument(CommandException):
    pass


class DuplicateArgument(CommandException):
    pass
