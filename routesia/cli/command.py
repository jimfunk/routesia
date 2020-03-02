"""
routesia/cli/command.py - Command line interface command definitions
"""
from collections import OrderedDict

from routesia.exceptions import CommandError


class CLICommand:
    """
    Base class for CLI commands.

    Each command is defined as a single CLICommand subclass, for example::

        class EchoCommand(CLICommand):
            command = 'echo'
            parameters = (
                ('text', String(required=True)),
            )

            async def call(self, text, **kwargs):
                message = Message()
                message.text = text
                return await self.client.request('/echo', message)

    The command attribute must be a string representing what the user will
    type to call the command. The command is split up and placed in the
    command tree. The call method must implement the command itself.

    If the command accepts parameters, they must be described using the
    parameters class attribute. Each parameter must be described as a 2-tuple
    of the parameter name, and an instance a Parameter subclass from
    routesia.cli.parameters.

    Inside the call implementation, the RPCClient instance can be accessed as
    ``self.client``.

    Arguments on the command line are always passed to the Parameter subclass
    as strings for type conversion if necessary. The value stored in the
    dictionary is dependent on the associated Parameter class. Any parameters
    not given are not included in the dictionary.

    If any extra arguments are given they are included as a simple list in the
    dictionary with the key ``__extra__``.

    Arguments are whitespace delimited unless quoted according to standard
    shell rules.

    Since the commands are represented by a tree, commands can be layered in a
    hierarchy. For example, say we have the following commands::

        class ShowFoo(CLICommand):
            command = 'show foo'
            ...

        class ShowBar(CLICommand):
            command = 'show bar'
            ...

        class ShowSomethingElse(CLICommand):
            command = 'show something else'
            ...

    We can now use either of these inputs to call the appropriate command::

        show foo
        show bar
        show something else

    At this time, command matches are terminating, so it is not currently
    possible to set up commands like this from the main tree::

        class ShowFoo(CLICommand):
            command = 'show foo'
            ...

        class ShowFooBar(CLICommand):
            command = 'show foo bar'
            ...

    In this case, the ShowFoo command will always be matched. The reason for
    this is due to the ambiguity of sub-commands versus arguments. To get
    around this, a sub-tree can be implemented on the ShowFoo command::

        from routesia.cli import CLICommandTreeNode

        class ShowFooBar(CLICommand):
            command = 'bar'
            ...

        class ShowFoo(CLICommand):
            command = 'show foo'
            parameters = (
                ('subcommand', String()),
            )

            def __init__(self, client):
                super().__init(client)
                self.command_tree = CLICommandTreeNode(self.client, None)
                self.command_tree.register_command(ShowFooBar)

            async def call(self, **kwargs):
                if "subcommand" in kwargs:
                    return await self.command_tree.handle([kwargs["subcommand"]] + kwargs["__extra__"])
                # Normal command implementation

    The arguments of the call method may be subject to completion, provided
    there is a ``get_<argument_name>_completion()`` method defined on the
    command. The function is async, in case the client is needed to look up
    the values. The function is given the suggestion, which may be an empty
    string if the argument is empty so far. Any already known arguments are
    given as **kwargs``.

    For example:

        class ShowFoo(CLICommand):
            command = 'show foo'
            parameters = (
                ("first_arg", String(required=True)),
                ("second_arg", String(required=True)),
            )

            async def call(self, first_arg, second_arg, **kwargs):
                ...

            async def get_first_arg_completions(self, suggestion, **kwargs):
                completions = []
                for candidate in get_first_arg_values():
                    if candidate.startswith(suggestion):
                        completions.append(candidate)
                return completions

            async def get_second_arg_completions(self, suggestion, **kwargs):
                first_arg = args[0]
                completions = []
                # You can use the first argument to filter the second argument
                for candidate in get_second_arg_values(first_arg=first_arg):
                    if candidate.startswith(suggestion):
                        completions.append(candidate)
                return completions

    Some parameter types may also have built-in completion functions that are
    used even the command does not explicitly define a completion function for
    the parameter. For example, the ``Bool()`` parameter will offer the "true"
    and "false" completions.
    """

    command = None
    parameters = tuple()

    def __init__(self, client):
        self.client = client
        self.parameter_map = OrderedDict(self.parameters)

    def check_args(self, command):
        keyword_args_present = False
        kwargs = {}
        extra_args = []

        for i, arg in enumerate(command):
            param_name = None
            param_value = arg

            if i >= len(self.parameters) or arg == "|":
                extra_args = command[i:]
                break

            if "=" in arg:
                name, value = arg.split("=", 1)
                if name in self.parameter_map:
                    keyword_args_present = True
                    param_name = name
                    param_value = value

            if not param_name:
                if keyword_args_present:
                    raise CommandError("Positional argument given after named argument")
                param_name = list(self.parameter_map.keys())[i]

            try:
                kwargs[param_name] = self.parameter_map[param_name](param_value)
            except Exception as e:
                raise CommandError(str(e))

        if extra_args:
            kwargs["__extra__"] = extra_args

        return kwargs, keyword_args_present

    async def handle(self, command):
        kwargs, _ = self.check_args(command)
        result = await self.call(**kwargs)
        # TODO: If we get a '|' in extra_args, parse into a filter
        self.display(result)

    async def get_parameter_completions(self, param_name, suggestion, **kwargs):
        # Try command-specific completion
        completion_method = getattr(
            self, "get_%s_completions" % param_name.replace(".", "_"), None
        )
        if completion_method:
            return await completion_method(suggestion, **kwargs)

        # Try parameter-specific completions
        completion_method = getattr(
            self.parameter_map[param_name], "get_completions", None
        )
        if completion_method:
            return completion_method()

        return []

    async def get_completions(self, args, suggestion, **kwargs):
        if len(args) + 1 > len(self.parameters):
            # No more params available
            return []

        completions = []

        # Get any args already given
        kwargs, keyword_args_present = self.check_args(args)

        param_name = None
        param_value = suggestion
        positional = True

        if "=" in suggestion:
            name, value = suggestion.split("=", 1)
            if name in self.parameter_map:
                positional = False
                param_name = name
                param_value = value

        if keyword_args_present:
            # Only kwargs are valid at this point
            positional = False

        if positional:
            positional_param_name = list(self.parameter_map.keys())[len(args)]
            for completion in await self.get_parameter_completions(
                positional_param_name, param_value, **kwargs
            ):
                completions.append(completion)

        if param_name:
            for completion in await self.get_parameter_completions(
                param_name, param_value, **kwargs
            ):
                completions.append("%s=%s" % (param_name, completion))
        else:
            # Suggest unused kwargs
            for name in self.parameter_map.keys():
                if name not in kwargs:
                    completions.append("%s=" % name)

        return completions

    async def call(self):
        raise NotImplementedError

    def display(self, result):
        """
        Display result
        """
        if result is not None:
            print(result)


class CLICommandSet:
    """
    Represents a set of CLICommand classes.
    """

    commands = tuple()


class CLIEnum:
    """
    Wraps a protobuf enum for use as a type annotation converting a string to
    the emnumerated value.
    """

    def __init__(self, enum):
        self.enum = enum

    def __call__(self, value):
        if value is None:
            return self.enum.values()[0]
        return self.enum.Value(value)
