"""
routesia/cli/command.py - Command line interface command definitions
"""
import inspect

from routesia.exceptions import CommandError


class CLICommand:
    """
    Base class for CLI commands.

    Each command is defined as a single CLICommand subclass, for example::

        class EchoCommand(CLICommand):
            command = 'echo'

            async def call(self, text):
                message = Message()
                message.text = text
                return await self.client.request('/echo', message)

    The command attribute must be a string representing what the user will
    type to call the command. The command is split up and placed in the
    command tree. The call method must implement the command itself.

    Inside the call implementation, the RPCClient instance can be accessed as
    ``self.client``.

    Arguments to the call method are pulled from the command line and passed
    the same way as any python function, but the arguments are whitespace
    delimited and strings need not be quoted unless they contain whitespace.
    Arguments are passed as strings unless the parameters are given type
    annotations, in which case they are coerced first.

    For example, given the following call implementation::

        async def call(self, msg, a:float, b:int, operation='+')

    The following command inputs are interpreted as below:
        * ``hey 1 2`` is equivalent to ``call("hey", 1, 2.0)``
        * ``ho 1 2 -`` is equivalent to ``call("ho", 1, 2.0, "-")``
        * ``"let's go!" '1 2 operation=*`` is equivalent to ``call("let's go!", 1, 2.0, operation="*")``

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

            def __init__(self, client):
                super().__init(client)
                self.command_tree = CLICommandTreeNode(self.client, None)
                self.command_tree.register_command(ShowFooBar)

            async def call(self, *args):
                if args:
                    return await self.command_tree.handle(args)
                # Normal command implementation

    The arguments of the call method may be subject to completion, provided
    there is a ``get_<argument_name>_completion()`` method defined on the
    command. The function is async, in case the client is needed to look up
    the values. The function is given the suggestion, which may be an empty
    string if the argument is empty so far. Any already known arguments are
    given as ``*args`` and **kwargs``.

    For example:

        class ShowFoo(CLICommand):
            command = 'show foo'

            async def call(self, first_arg, second_arg):
                ...

            async def get_first_arg_completions(self, suggestion, *args, **kwargs):
                completions = []
                for candidate in get_first_arg_values():
                    if candidate.startswith(suggestion):
                        completions.append(candidate)
                return completions

            async def get_second_arg_completions(self, suggestion, *args, **kwargs):
                first_arg = args[0]
                completions = []
                # You can use the first argument to filter the second argument
                for candidate in get_second_arg_values(first_arg=first_arg):
                    if candidate.startswith(suggestion):
                        completions.append(candidate)
                return completions
    """
    command = None

    def __init__(self, client):
        self.client = client
        self.signature = inspect.Signature.from_callable(self.call)
        self.parameters = self.signature.parameters
        self.positional_parameters = [p for p in self.parameters.values() if p.kind == p.POSITIONAL_OR_KEYWORD]
        self.num_positional_parameters = len(self.positional_parameters)
        self.keyword_parameters = [p for p in self.parameters.values() if p.kind == p.KEYWORD_ONLY]

    def check_args(self, command, test=True):
        args = []
        kwargs = {}

        for i, arg in enumerate(command):
            if '=' in arg:
                param_name, value = arg.split('=', 1)
                if param_name in self.parameters:
                    param = self.parameters[param_name]
                    if param.annotation is not param.empty:
                        try:
                            value = param_name.annotation(value)
                        except Exception as e:
                            raise CommandError(str(e))
                    kwargs[param_name] = value
                    continue
            param = list(self.parameters.values())[i]
            if param.annotation is not param.empty:
                try:
                    arg = param_name.annotation(arg)
                except Exception as e:
                    raise CommandError(str(e))
            args.append(arg)

        if test:
            try:
                self.signature.bind(*args, **kwargs)
            except TypeError as e:
                raise CommandError(str(e))

        # TODO: If we get a '|' in the commmands, parse into a filter. Perhaps
        # return a bound method as a 3rd value?

        return args, kwargs

    async def handle(self, command):
        args, kwargs = self.check_args(command)
        result = await self.call(*args, **kwargs)
        # TODO: filter
        self.display(result)

    async def get_completions(self, args, suggestion, **kwargs):
        completions = []

        # Get any args already given
        args, kwargs = self.check_args(args, test=False)

        if kwargs or len(args) >= self.num_positional_parameters:
            # If we have any kwargs or the positionals are all defined, this
            # suggestion is a kwarg
            if '=' in suggestion:
                param_name, value = suggestion.split('=', 1)
                if param_name in self.kwargs:
                    # Already given as kwarg. Not valid
                    return []
                if param_name not in self.parameters:
                    # Not a param
                    return []
                param = self.parameters[param_name]
                if param.kind == param.POSITIONAL_OR_KEYWORD:
                    # Already given as positional
                    return []
                completion_method = getattr(self, 'get_%s_completions' % param.name, None)
                if completion_method:
                    for completion in await completion_method(suggestion, *args, **kwargs):
                        completions.append('%s=%s' % (param_name, completion))
                return completions
            else:
                # If we don't know which one, just suggest unused kwargs
                for parameter in self.keyword_parameters:
                    if parameter.name not in kwargs:
                        completions.append('%s=' % parameter.name)
                    return completions
        else:
            # This is positional
            param = list(self.parameters.values())[len(args)]
            completion_method = getattr(self, 'get_%s_completions' % param.name, None)
            if completion_method:
                return await completion_method(suggestion, *args, **kwargs)

        return completions

    async def call(self):
        raise NotImplementedError

    def display(self, result):
        """
        Display result
        """
        print(result)


class CLICommandSet:
    """
    Represents a set of CLICommand classes.
    """
    commands = tuple()
