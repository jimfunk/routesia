import pytest

from routesia.rpc import (
    RPCInvalidArgument,
    RPCNoSuchMethod,
    RPCUnspecifiedError,
)

from . import test_pb2


async def test_call(rpc, rpcclient, schema_registry):
    schema_registry.load_schema_module(test_pb2)

    async def handler():
        response = test_pb2.Test()
        response.string_value = "bar"
        response.int_value = 2
        return response

    rpc.register("foo", handler)

    result = await rpcclient.request("foo")

    assert isinstance(result, test_pb2.Test)
    assert result.string_value == "bar"
    assert result.int_value == 2


async def test_call_with_argument(rpc, rpcclient, schema_registry):
    schema_registry.load_schema_module(test_pb2)

    async def handler(arg):
        response = test_pb2.Test()
        response.string_value = arg.string_value
        response.int_value = arg.int_value + 1
        return response

    rpc.register("foo", handler)

    with pytest.raises(RPCInvalidArgument):
        await rpcclient.request("foo")

    argument = test_pb2.Test()
    argument.string_value = "baz"
    argument.int_value = 3
    result = await rpcclient.request("foo", argument)

    assert isinstance(result, test_pb2.Test)
    assert result.string_value == "baz"
    assert result.int_value == 4


async def test_call_unknown_method(rpc, rpcclient):
    with pytest.raises(RPCNoSuchMethod):
        await rpcclient.request("foo")


async def test_call_invalid_parameters(rpc, rpcclient):
    async def handler():
        raise RPCInvalidArgument("Bad")

    rpc.register("foo", handler)

    with pytest.raises(RPCInvalidArgument):
        await rpcclient.request("foo")


async def test_call_entity_not_found(rpc, rpcclient):
    async def handler():
        raise RPCInvalidArgument("Bad")

    rpc.register("foo", handler)

    with pytest.raises(RPCInvalidArgument):
        await rpcclient.request("foo")


async def test_call_entity_exists(rpc, rpcclient):
    async def handler():
        raise RPCInvalidArgument("Bad")

    rpc.register("foo", handler)

    with pytest.raises(RPCInvalidArgument):
        await rpcclient.request("foo")


async def test_call_unsppecifiedError(rpc, rpcclient):
    async def handler():
        raise ValueError("bar")

    rpc.register("foo", handler)

    with pytest.raises(RPCUnspecifiedError):
        await rpcclient.request("foo")
