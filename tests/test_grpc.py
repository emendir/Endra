from datetime import datetime
import walytis_beta_api as waly
import os
import shutil
import tempfile

import _testing_utils
import walytis_identities
import pytest
import walytis_beta_api as walytis_api
from _testing_utils import mark, test_threads_cleanup
from walytis_identities.did_objects import Key
import walytis_mutability
import walytis_offchain
import endra
from endra import Profile, MessageContent, Correspondence
from walytis_identities import GroupDidManager
walytis_api.log.PRINT_DEBUG = False

_testing_utils.assert_is_loaded_from_source(
    source_dir=os.path.dirname(os.path.dirname(__file__)), module=endra
)
# test.py
import threading
import time
import grpc
import pytest
from typing import Tuple, List
from endra.api import myservice_pb2
from endra.api import myservice_pb2_grpc
from endra.api.grpc_server import GrpcServer  # Assuming the server file is named server.py
from endra.api.grpc_client import send_request, MessageSubscriber  # Assuming client file is client.py


RPC_ADDRESS: Tuple[str, int] = ("127.0.0.1", 50051)

@pytest.fixture(scope="module")
def grpc_server():
    """Fixture to start and stop the gRPC server."""
    server = GrpcServer(RPC_ADDRESS, lambda request: myservice_pb2.Response(result="Processed: " + request.data))
    thread = threading.Thread(target=lambda: time.sleep(5), daemon=True)
    thread.start()
    yield server
    server.terminate()


def test_rpc_functionality(grpc_server):
    """Test sending an RPC request and receiving a response."""
    print("Running RPC Test...")
    request = myservice_pb2.Request(data="Hello, Server!")
    response = send_request(RPC_ADDRESS, request)
    mark( response.result == "Processed: Hello, Server!", "RPC")


def test_pubsub_functionality(grpc_server):
    """Test message publishing and subscribing."""
    received_messages: List[str] = []

    def on_message_received(message: str) -> None:
        received_messages.append(message)

    subscriber = MessageSubscriber(RPC_ADDRESS, on_message_received)
    time.sleep(1)  # Ensure the subscription is active

    test_message = "Test PubSub Message"
    grpc_server.publish("updates", test_message)
    
    time.sleep(2)  # Allow time for message propagation
    subscriber.terminate()
    
    mark(test_message in received_messages, "PubSub")

def run_tests():
    server_instance = GrpcServer(RPC_ADDRESS, lambda request: myservice_pb2.Response(result="Processed: " + request.data))
    
    test_rpc_functionality(server_instance)
    print("RPC Test Passed")
    
    print("Running PubSub Test...")
    test_pubsub_functionality(server_instance)
    print("PubSub Test Passed")
    
    server_instance.terminate()
    
    test_threads_cleanup()
if __name__ == "__main__":
    _testing_utils.PYTEST=False
    run_tests()