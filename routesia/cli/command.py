"""
routesia/cli/command.py - Command line interface command definitions
"""
from collections import OrderedDict

from routesia.exceptions import CommandError, RPCException


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

    Completion for parameters is implemented via the ``get_completions()``
    method on the parameter. Some basic parameter types such as ``Bool()``
    will have built-in completion, otherwise completion may be implemented by
    priving an async function as the ``completer`` argument to the paramter or
    overriding the ``get_completions()`` method.

    The method is given an instance of the MQTT client and the suggestion,
    which may be an empty string if the argument is empty so far. Any already
    known arguments are given as **kwargs`` to allow for filtering.

    For example, to pass functions::

        async def get_first_arg_completions(client, suggestion, **kwargs):
            completions = []
            for candidate in client.request("/something/list"):
                if candidate.startswith(suggestion):
                    completions.append(candidate)
            return completions

        async def get_second_arg_completions(client, suggestion, **kwargs):
            first_arg = kwargs.get('first_arg', None)
            completions = []
            # You can use the first argument to filter the second argument
            for candidate in client.request("/something/else/list", first_arg):
                if candidate.startswith(suggestion):
                    completions.append(candidate)
            return completions

        class ShowFoo(CLICommand):
            command = 'show foo'
            parameters = (
                ("first_arg", String(required=True, completer=get_first_arg_completions)),
                ("second_arg", String(required=True, completer=get_second_arg_completions)),
            )

            async def call(self, first_arg, second_arg, **kwargs):
                ...


    To use ``Parameter`` subclasses::

        class FirstArg(String):
            async def get_completions(self, client, suggestion, **kwargs):
                completions = []
                for candidate in client.request("/something/list"):
                    if candidate.startswith(suggestion):
                        completions.append(candidate)
                return completions

        class SecondArg(String):
            async def get_completions(self, client, suggestion, **kwargs):
                first_arg = kwargs.get('first_arg', None)
                completions = []
                # You can use the first argument to filter the second argument
                for candidate in client.request("/something/else/list", first_arg):
                    if candidate.startswith(suggestion):
                        completions.append(candidate)
                return completions

        class ShowFoo(CLICommand):
            command = 'show foo'
            parameters = (
                ("first_arg", FirstArg(required=True)),
                ("second_arg", SecondArg(required=True)),
            )

            async def call(self, first_arg, second_arg, **kwargs):
                ...
    """

    command = None
    parameters = tuple()

    def __init__(self, client):
        self.client = client
        self.parameter_map = OrderedDict(self.parameters)

    def check_args(self, command, ignore_errors=False):
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
                else:
                    if not ignore_errors:
                        raise CommandError("Unknown parameter: %s" % name)
                    continue

            if not param_name:
                if keyword_args_present:
                    if not ignore_errors:
                        raise CommandError(
                            "Positional argument given after named argument"
                        )
                        continue
                param_name = list(self.parameter_map.keys())[i]

            try:
                kwargs[param_name] = self.parameter_map[param_name](param_value)
            except Exception as e:
                if not ignore_errors:
                    raise CommandError(str(e))

        if extra_args:
            kwargs["__extra__"] = extra_args

        return kwargs, keyword_args_present

    async def handle(self, command):
        kwargs, _ = self.check_args(command)

        for name, param in self.parameters:
            if param.required and name not in kwargs:
                raise CommandError("Required parameter %s not given" % name)

        try:
            result = await self.call(**kwargs)
        except RPCException as e:
            raise CommandError(str(e))
        # TODO: If we get a '|' in extra_args, parse into a filter
        self.display(result)

    async def get_completions(self, args, suggestion, **kwargs):
        if len(args) + 1 > len(self.parameters):
            # No more params available
            return []

        completions = []

        # Get any args already given
        kwargs, keyword_args_present = self.check_args(args, ignore_errors=True)

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
            for completion in await self.parameter_map[
                positional_param_name
            ].get_completions(self.client, param_value, **kwargs):
                completions.append(completion)

        if param_name:
            for completion in await self.parameter_map[param_name].get_completions(
                self.client, param_value, **kwargs
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

    def _update_message_from_args(self, msg, **kwargs):
        """
        Internal recursive message update
        """
        sub_msg_args = {}

        for param_name in kwargs:
            if "." in param_name:
                sub, field = param_name.split(".", 1)
                if sub not in sub_msg_args:
                    sub_msg_args[sub] = {}
                sub_msg_args[sub][field] = kwargs[param_name]
                continue

            msg_param = param_name.replace("-", "_")
            if msg_param in msg.DESCRIPTOR.fields_by_name:
                desc = msg.DESCRIPTOR.fields_by_name[msg_param]
                if desc.label == desc.LABEL_REPEATED:
                    getattr(msg, msg_param)[:] = kwargs[param_name]
                else:
                    setattr(msg, msg_param, kwargs[param_name])

        for sub, args in sub_msg_args.items():
            self._update_message_from_args(getattr(msg, sub), **args)

    def update_message_from_args(self, msg, **kwargs):
        """
        Update a message from any given kwargs found in the parameters of the
        command
        """
        self._update_message_from_args(
            msg,
            **{key: val for key, val in kwargs.items() if key in self.parameter_map}
        )


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
