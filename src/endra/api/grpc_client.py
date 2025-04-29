from time import sleep
import threading
import grpc
from typing import Callable, Tuple
from . import myservice_pb2
from . import myservice_pb2_grpc



def send_request(address: Tuple[str, int], request: myservice_pb2.Request) -> myservice_pb2.Response:
    """Execute a remote procedure call.
    Args:
        address: IP address and port number
        request: The RPC data
    Returns:
        The response from the server
    """
    # Connect to the RPC server
    channel: grpc.Channel = grpc.insecure_channel(f"{address[0]}:{address[1]}")
    stub: myservice_pb2_grpc.MyServiceStub = myservice_pb2_grpc.MyServiceStub(channel)

    # Send the request and get the response
    response: myservice_pb2.Response = stub.ProcessRequest(request)
    return response

class MessageSubscriber:
    def __init__(self, address: Tuple[str, int], on_message_received: Callable[[str], None]) -> None:
        """Initialise Publish-Subscribe subscriber object.

        Args:
            address: IP address and port number
            on_message_received: event handler function to be called when a message is received
        """
        self.channel: grpc.Channel = grpc.insecure_channel(f"{address[0]}:{address[1]}")
        self.stub: myservice_pb2_grpc.MyServiceStub = myservice_pb2_grpc.MyServiceStub(self.channel)
        self.on_message_received: Callable[[str], None] = on_message_received
        self.running: bool = True

        # Start subscription in a separate thread
        self.thread: threading.Thread = threading.Thread(
            target=self._listen_for_messages, daemon=True)
        self.thread.start()

    def _listen_for_messages(self) -> None:
        """Private method to listen for messages in a separate thread."""
        request: myservice_pb2.SubscriptionRequest = myservice_pb2.SubscriptionRequest(topic="updates")  # Set your topic
        try:
            for message in self.stub.Subscribe(request):
                if not self.running:
                    break
                self.on_message_received(message.data)
        except grpc.RpcError as e:
            if self.running:  # Only log errors if we are not terminating
                print(f"Subscription error: {e}")


    def terminate(self) -> None:
        """Cleanup resources."""
        self.running = False  # Stop the message loop
        self.channel.close()  # Now safely close the channel
        print("Subscriber terminated.")

    def __del__(self) -> None:
        self.terminate()

# Example usage:
if __name__ == "__main__":
    def on_message_received(message: str) -> None:
        print(message)
    # Addresses for RPC and PUB-SUB
    RPC_ADDRESS: Tuple[str, int] = ("127.0.0.1", 8888)
    
    request: myservice_pb2.Request = myservice_pb2.Request(data="Test Data")
    response: myservice_pb2.Response = send_request(RPC_ADDRESS, request)
    print(response)
    assert response.result == "Processed: " + request.data

    subscriber: MessageSubscriber = MessageSubscriber(RPC_ADDRESS, on_message_received)
    sleep(5)
    subscriber.terminate()
