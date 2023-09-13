"""
routesia/rpc.py - RPC implementation using MQTT and protobuf
"""

from google.protobuf.message import DecodeError
import inspect
import logging

from routesia.mqtt import MQTT
from routesia.schema.v1 import rpc_pb2
from routesia.schema.registry import SchemaRegistry
from routesia.service import Provider


logger = logging.getLogger("rpc")


class RPCException(Exception):
    pass


class RPCUnspecifiedError(RPCException):
    pass


class RPCNoSuchMethod(RPCException):
    pass


class RPCInvalidRequest(RPCException):
    pass


class RPCInvalidParameters(RPCException):
    pass


class RPCEntityNotFound(RPCException):
    pass


class RPCEntityExists(RPCException):
    pass


class RPC(Provider):
    """
    The RPC provider is an implementation of RPC over MQTT.

    Message topics for RPC will be appended to the given prefix. When there
    are multiple RPC servers on the same broker, they must use unique
    prefixes.

    The request topic will be ``<prefix>/request``. The payload is expected to
    be an RPCRequest protobuf message.

    The response topic will be ``<prefix>/response/<client_id>``. The payload
    will be an RPCResponse protobuf message.

    Consumers must register the RPC commands using register(topic, handler).
    The handler may have a single parameter. If the parameter exists and a
    message was sent with the request, the instance will be passed to the
    handler as the parameter.
    """
    def __init__(self, mqtt: MQTT, schema_registry: SchemaRegistry, prefix="rpc"):
        super().__init__()
        self.prefix = prefix
        self.mqtt = mqtt
        self.schema_registry = schema_registry
        self.handlers = {}

        self.response_prefix = f"{self.prefix}/response"

        self.mqtt.subscribe(f"{self.prefix}/request", self.handle_request)

    def register(self, method: str, handler: callable):
        """
        Register an RPC handler for the given topic.

        The topic should be given in the same format as as MQTT subscription.

        The handler must be a callable. If it takes an argument the message
        sent by the client will be passed to it.

        The handler must return a Protobuf message or None, unless an error
        occurs.

        Handlers may raise RPCEntityNotFound to indicate that a given entity from
        the request is not found.
        """
        method = method.lstrip('/')
        self.handlers[method] = handler

    def send_response(self, request: rpc_pb2.RPCRequest, response: rpc_pb2.RPCResponse):
        response.request_id = request.request_id
        self.mqtt.publish(f"{self.response_prefix}/{request.client_id}", payload=response.SerializeToString())

    async def handle_request(self, message):
        request = rpc_pb2.RPCRequest()
        response = rpc_pb2.RPCResponse()
        try:
            request.ParseFromString(message.payload)
        except DecodeError as e:
            response.response_code = rpc_pb2.RPCResponse.INVALID_REQUEST
            response.error_detail = f"Invalid request: {e}"
            self.send_response(request, response)
            return

        if request.method not in self.handlers:
            response.response_code = rpc_pb2.RPCResponse.NO_SUCH_METHOD
            response.error_detail = f"Method {request.method} does not exist"
            self.send_response(request, response)
            return

        handler = self.handlers[request.method]

        # Figure out if method requires a message and unpack it as the
        # expected type
        signature = inspect.Signature.from_callable(handler)
        args = []
        if signature.parameters:
            if not request.argument.TypeName():
                response.response_code = rpc_pb2.RPCResponse.INVALID_PARAMETERS
                response.error_detail = "Call requires argument"
                self.send_response(request, response)
                return

            message_type = self.schema_registry.get_message_type_from_type_name(request.argument.TypeName())
            message = message_type()
            request.argument.Unpack(message)
            args.append(message)

        try:
            result = await handler(*args)
        except RPCInvalidParameters as e:
            response.response_code = rpc_pb2.RPCResponse.INVALID_PARAMETERS
            response.error_detail = str(e)
            self.send_response(request, response)
            return
        except RPCEntityNotFound as e:
            response.response_code = rpc_pb2.RPCResponse.ENTITY_NOT_FOUND
            response.error_detail = str(e)
            self.send_response(request, response)
            return
        except RPCEntityExists as e:
            response.response_code = rpc_pb2.RPCResponse.ENTITY_EXISTS
            response.error_detail = str(e)
            self.send_response(request, response)
            return
        except Exception as e:
            logger.exception("Got exception handling %s." % request.method)
            response.response_code = rpc_pb2.RPCResponse.UNSPECIFIED_ERROR
            response.error_detail = str(e)
            self.send_response(request, response)
            return

        if result is not None:
            response.response.Pack(result)

        self.send_response(request, response)
