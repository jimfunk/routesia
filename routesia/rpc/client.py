"""
routesia/rpc/client.py - Routesia RPC client
"""

import asyncio
import logging
import paho.mqtt.client
import time
from uuid import uuid4

from routesia.exceptions import (
    RPCUnspecifiedError,
    RPCHandlerNotFound,
    RPCInvalidParameters,
    RPCEntityNotFound,
    RPCEntityExists,
)
from routesia.rpc import rpc_pb2


logger = logging.getLogger(__name__)


class RPCResponse:
    """
    Map RPCError codes to exceptions.
    """

    error_map = {
        rpc_pb2.RPCError.UNSPECIFIED_ERROR: RPCUnspecifiedError,
        rpc_pb2.RPCError.HANDLER_NOT_FOUND: RPCHandlerNotFound,
        rpc_pb2.RPCError.INVALID_PARAMETERS: RPCInvalidParameters,
        rpc_pb2.RPCError.ENTITY_NOT_FOUND: RPCEntityNotFound,
        rpc_pb2.RPCError.ENTITY_EXISTS: RPCEntityExists,
    }

    """
    Represents a response to an RPC request.

    On success, message will be the resulting protobuf message and error will
    be None. On error, message will be None and error will be the resulting
    protobuf error message.
    """

    def __init__(self, request_id, message, error):
        self.request_id = request_id
        self.message = message
        self.error = error

    def raise_on_status(self):
        """
        Raise the appropriate exception if the response is an error.
        """
        if self.error:
            if self.error.response_code in self.error_map:
                raise self.error_map[self.error.response_code](self.error.message)
            else:
                raise RPCUnspecifiedError(
                    "Got error with unknown code %s" % self.error_map.response
                )


class RPCRequest:
    "Represents an RPC request"

    def __init__(self, id, message_info, callback=None):
        self.id = id
        self.message_info = message_info
        self.callback = callback


class RPCClient:
    def __init__(self, host="localhost", port=1883):
        self.host = host
        self.port = port

        self.client_id = uuid4()
        self.request_id = 0
        self.in_flight_requests = {}

        self.mqtt = paho.mqtt.client.Client(client_id=str(self.client_id))
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_message = self.on_message

    def connect(self):
        self.mqtt.connect(self.host, port=self.port)
        self.mqtt.subscribe("/response/%s/+/#" % self.client_id)

    def get_request_id(self):
        request_id = self.request_id
        self.request_id += 1
        return request_id

    def request(self, topic, message, callback=None):
        """
        Send an RPC request with topic and protobuf message to the server.
        When the response arrives, callback will be called with the message.

        The callback will be called with an instance of RPCResponse.

        Returns the generated request ID for the request.
        """
        if message is None:
            payload = b""
        else:
            payload = message.SerializeToString()
        request_id = self.get_request_id()
        topic = "/request/%s/%s/%s" % (self.client_id, request_id, topic.lstrip("/"),)
        message_info = self.mqtt.publish(topic, payload=payload)
        request = RPCRequest(request_id, message_info, callback)
        self.in_flight_requests[request.id] = request
        return request

    def on_connect(self, client, obj, flags, rc):
        logger.debug("Connected to broker")

    def on_message(self, client, obj, message):
        _, _, request_id, status = message.topic[9:].split("/", 3)
        request_id = int(request_id)
        request = self.in_flight_requests.pop(request_id)
        if request:
            if status == "error":
                error = rpc_pb2.RPCError.FromString(message.payload)
                response = RPCResponse(request_id, None, error)
            else:
                response = RPCResponse(request_id, message.payload, None)
            if request.callback:
                try:
                    request.callback(response)
                except Exception:
                    logger.exception(
                        "Caught exception running callback for request ID %s"
                        % request_id
                    )
        else:
            logger.warn("Got unexpected result for request %s." % request_id)

    def run(self):
        self.connect()
        self.mqtt.loop_forever()

    def run_until_complete(self, timeout=30):
        "Run until all responses have been received or timeout"
        deadline = time.time() + timeout
        while self.in_flight_requests:
            if time.time() >= deadline:
                logger.error(
                    "Timed out waiting for %s"
                    % ", ".join([str(i) for i in self.in_flight_requests.keys()])
                )
                break
            self.mqtt.loop()
        self.mqtt.disconnect()


class AsyncRPCClient(RPCClient):
    """
    An asyncio version of RPCClient
    """

    def __init__(self, loop, host="localhost", port=1883):
        super().__init__(host=host, port=port)
        self.loop = loop
        self.connect_future = self.loop.create_future()
        self.request_futures = {}
        self.mqtt.on_socket_open = self.on_socket_open
        self.mqtt.on_socket_close = self.on_socket_close
        self.mqtt.on_socket_register_write = self.on_socket_register_write
        self.mqtt.on_socket_unregister_write = self.on_socket_unregister_write

    def on_connect(self, client, obj, flags, rc):
        super().on_connect(client, obj, flags, rc)
        self.connect_future.set_result(True)

    def on_socket_open(self, client, userdata, sock):
        self.loop.add_reader(sock, client.loop_read)

    def on_socket_close(self, client, userdata, sock):
        self.loop.remove_reader(sock)

    def on_socket_register_write(self, client, userdata, sock):
        self.loop.add_writer(sock, client.loop_write)

    def on_socket_unregister_write(self, client, userdata, sock):
        self.loop.remove_writer(sock)

    def handle_response(self, response):
        future = self.request_futures.pop(response.request_id)
        future.set_result(response)

    async def wait_connect(self):
        await self.connect_future

    async def request(self, topic, message):
        request = super().request(topic, message, self.handle_response)
        future = self.loop.create_future()
        self.request_futures[request.id] = future
        response = await future
        response.raise_on_status()
        return response.message

    async def run(self):
        self.connect()
        while self.mqtt.loop_misc() == paho.mqtt.client.MQTT_ERR_SUCCESS:
            self.mqtt.loop_write()
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
