"""
routesia/rpc/provider.py - RPC over MQTT
"""

import logging

from routesia.exceptions import EntityNotFound
from routesia.injector import Provider
from routesia.mqtt import MQTT
from routesia.rpc import rpc_pb2


logger = logging.getLogger(__name__)


class RPCProvider(Provider):
    """
    The RPC provider is an implementation of RPC over MQTT.

    Consumers must register the RPC commands using register(topic, handler)
    """
    def __init__(self, mqtt: MQTT):
        super().__init__()
        self.mqtt = mqtt
        self.handlers = {}

    def register(self, handler_topic, handler):
        """
        Register an RPC handler for the given topic.

        The topic should be given in the same format as as MQTT subscription.

        The handler must be a callable. It will be called with the following
        arguments:

        * message - The MQTT message
        * handler_topic - The full handler topic

        The handler must return a Protobuf message, unless an error occurs.

        Handlers may raise EntityNotFound to indicate that a given entity from
        the request is not found.
        """
        handler_topic = handler_topic.lstrip('/')
        self.handlers[handler_topic] = handler

    def send_error(self, client_id, request_id, code, message):
        error = rpc_pb2.RPCError()
        error.response_code = code
        error.message = message
        self.mqtt.publish("/response/%s/%s/error" % (client_id, request_id), payload=error.SerializeToString())

    def handle_request(self, message):
        # /request/<client_id>/<request_id>/<handler_topic>
        client_id, request_id, handler_topic = message.topic[9:].split('/', 2)
        if handler_topic not in self.handlers:
            self.send_error(client_id, request_id, rpc_pb2.RPCError.HANDLER_NOT_FOUND, "No handler for %s found." % handler_topic)
            return

        try:
            result = self.handlers[handler_topic](message)
        except EntityNotFound as e:
            self.send_error(client_id, request_id, rpc_pb2.RPCError.ENTITY_NOT_FOUND, "Entity not found: %s" % e)
            return
        except Exception:
            logger.exception("Got exception handling %s." % handler_topic)

            self.send_error(client_id, request_id, rpc_pb2.RPCError.UNSPECIFIED_ERROR, "An unspecified server error occured.")
            return

        self.mqtt.publish('/response/%s/%s/result' % (client_id, request_id), payload=result.SerializeToString())

    def startup(self):
        self.mqtt.subscribe('/request/+/+/#', self.handle_request)
