"""
routesia/cli/command.py - Command line interface command definitions
"""


class CLICommand:
    """
    Base class for CLI commands.

    Each command is defined as a single CLICommand subclass, for example::

        class EchoCommand(CLICommand):
            command = ('echo',)

            async def __call__(self, client, text):
                message = Message()
                message.text = text
                return await client.request('/echo', message)

    The command attribute must be a list of strings defining where the command
    is placed in the command tree amd the __call__ method must implement the
    command itself.

    Arguments to __call__ must be (self, client) at minimum, where the client
    is always set to the RPCClient instance. Additional arguments are passed
    from the command line.

    With the above example, we have the command 'echo' with the required
    positional argument 'text'. The following inputs are valid::

        echo foo
        echo "foo bar"

    The following inputs are invalid::

        echo
        echo foo bar

    Since the commands are represented by a tree, commands can be layered in a
    hierarchy. For example, say we have the following commands::

        class ShowFoo(CLICommand):
            command = ('show', 'foo')
            ...

        class ShowBar(CLICommand):
            command = ('show', 'bar')
            ...

        class ShowSomethingElse(CLICommand):
            command = ('show', 'something', 'else')
            ...

    We can now use either of these inputs to call the appropriate command::

        show foo
        show bar
        show something else

    At this time, command matches are terminating, so it is not currently
    possible to set up commands like this from the main tree::

        class ShowFoo(CLICommand):
            command = ('show', 'foo')
            ...

        class ShowFooBar(CLICommand):
            command = ('show', 'foo', 'bar')
            ...

    In this case, the ShowFoo command will always be matched. The reason for
    this is due to the ambiguity of sub-commands versus arguments. To get
    around this, a sub-tree can be implemented on the ShowFoo command.
    """
    command = []

    # async def get_completions(self, client, name, suggestion, **kwargs):
    #     if hasattr(self, 'get_%s_completions' % name):
    #         return await getattr(self, 'get_%s_completions' % name)(client, name, suggestion, kwargs)
    #     return []

    async def __call__(self, client):
        raise NotImplementedError


class CLICommandSet:
    """
    Represents a set of CLICommand classes.
    """
    pass
