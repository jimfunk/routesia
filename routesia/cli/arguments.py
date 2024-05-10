"""
Argument inspection and interpretation for callables.
"""

import inspect
import typing
from types import UnionType

from routesia.cli.exceptions import InvalidArgument


def interpret_arguments(fn: callable, args: dict[str, str], required: bool = False):
    """
    Interpret input command arguments for ``fn``, converting names and types according
    to callable arguments.

    If ``required`` is ``True`` this will raise :class:`InvalidArgument` if any given
    argument is not defined on ``fn`` or if a required parameter is not in ``args``.
    """
    signature = inspect.Signature.from_callable(fn)

    translated_args = {}
    for name, value in args.items():
        name = name.replace("-", "_").replace(".", "_")
        if name not in signature.parameters:
            if required:
                raise InvalidArgument(f"Argument {name} not defined by handler")
            continue
        annotation = signature.parameters[name].annotation
        if annotation == inspect.Parameter.empty:
            # No annotation defined. Assume string
            continue

        translated_args[name] = interpret_argument(annotation, value)


    for argument in signature.parameters.values():
        if argument.default == inspect.Parameter.empty and argument.name not in translated_args:
            raise InvalidArgument(f'Required argument "{argument.name}" missing')

    return translated_args


def interpret_argument(annotation, value):
    if isinstance(annotation, UnionType):
        errors = []
        for subannotation in typing.get_args(annotation):
            try:
                return interpret_argument(subannotation, value)
            except InvalidArgument as e:
                errors.append(str(e))
                continue
        raise InvalidArgument(", ".join(errors))
    elif annotation == bool:
        return interpret_bool(value)
    else:
        try:
            return annotation(value)
        except ValueError as e:
            raise InvalidArgument(str(e))


def interpret_bool(value: str) -> bool:
    value = value.lower()
    if value in ("1", "t", "true", "on", "yes"):
        return True
    elif value in ("0", "f", "false", "off", "no"):
        return False
    raise InvalidArgument(f'"{value}" could not be interpreted as boolean')
