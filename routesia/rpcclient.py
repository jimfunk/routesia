"""
routesia/rpcclient.py - RPC client implementation using MQTT and protobuf
"""

from google.protobuf.message import Message
import logging
import uuid

from routesia.mqtt import MQTT
from routesia.rpc import (
    RPCUnspecifiedError,
    RPCNoSuchMethod,
    RPCInvalidArgument,
    RPCInvalidRequest,
)
from routesia.schema.v1 import rpc_pb2
from routesia.schema.registry import SchemaRegistry
from routesia.service import Service, Provider


logger = logging.getLogger("rpcclient")


ERROR_CODE_MAP = {
    rpc_pb2.RPCResponse.UNSPECIFIED_ERROR: RPCUnspecifiedError,
    rpc_pb2.RPCResponse.NO_SUCH_METHOD: RPCNoSuchMethod,
    rpc_pb2.RPCResponse.INVALID_REQUEST: RPCInvalidRequest,
    rpc_pb2.RPCResponse.INVALID_ARGUMENT: RPCInvalidArgument,
}


class RPCRequest:
    def __init__(self, service, schema_registry: SchemaRegistry):
        self.schema_registry = schema_registry
        self.future = service.main_loop.create_future()

    def set_response(self, response):
        self.future.set_result(response)

    async def get_response(self):
        await self.future
        response = self.future.result()
        if response.response_code:
            raise ERROR_CODE_MAP[response.response_code](response.error_detail)
        if response.response.TypeName():
            message_type = self.schema_registry.get_message_type_from_type_name(response.response.TypeName())
            message = message_type()
            response.response.Unpack(message)
            return message
        return None


class RPCClient(Provider):
    """
    The RPCClient provider is an implementation of the client side of RPC over
    MQTT.

    Message topics for RPC will be appended to the given prefix. When there
    are multiple RPC servers on the same broker, they must use unique
    prefixes.
    """
    def __init__(self, mqtt: MQTT, service: Service, schema_registry: SchemaRegistry, prefix="rpc"):
        super().__init__()
        self.prefix = prefix
        self.mqtt = mqtt
        self.service = service
        self.schema_registry = schema_registry
        self.client_id = str(uuid.uuid4())
        self.request_id = 0
        self.in_flight_requests = {}

        self.request_topic = f"{self.prefix}/request"
        self.mqtt.subscribe(f"{self.prefix}/response/{self.client_id}", self.handle_response)

    def get_request_id(self):
        request_id = self.request_id
        self.request_id += 1
        return request_id

    async def request(self, method: str, argument: Message = None):
        """
        Send an RPC request with topic and protobuf message to the server.
        When the response arrives, the message will be returned.
        """
        request_message = rpc_pb2.RPCRequest()
        request_message.client_id = self.client_id
        request_message.request_id = self.get_request_id()
        request_message.method = method
        if argument is not None:
            request_message.argument.Pack(argument)
        self.mqtt.publish(self.request_topic, payload=request_message.SerializeToString())
        request = RPCRequest(self.service, self.schema_registry)
        self.in_flight_requests[request_message.request_id] = request
        return await request.get_response()

    def handle_response(self, message):
        response = rpc_pb2.RPCResponse()
        response.ParseFromString(message.payload)
        if response.request_id in self.in_flight_requests:
            self.in_flight_requests[response.request_id].set_response(response)
            del self.in_flight_requests[response.request_id]
