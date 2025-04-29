import threading
import grpc
from concurrent import futures
import time
from typing import Callable, Dict, Any, Tuple
from . import myservice_pb2
from . import myservice_pb2_grpc
import queue


class MyService(myservice_pb2_grpc.MyServiceServicer):
    def __init__(self, on_request_received: Callable[[myservice_pb2.Request], myservice_pb2.Response]) -> None:
        self.on_request_received: Callable[[myservice_pb2.Request], myservice_pb2.Response] = on_request_received
        self.subscribers: Dict[str, "queue.Queue[str]"] = {}  # Dictionary to hold queues per topic

    def ProcessRequest(self, request: myservice_pb2.Request, context: grpc.ServicerContext) -> myservice_pb2.Response:
        """Handles the RPC call."""
        response: myservice_pb2.Response = self.on_request_received(request)
        return response

    def Subscribe(self, request: myservice_pb2.SubscriptionRequest, context: grpc.ServicerContext) -> Any:
        """Handles client subscriptions and sends updates."""
        topic: str = request.topic
        if topic not in self.subscribers:
            self.subscribers[topic] = queue.Queue()

        print(f"Client subscribed to {topic}")

        while True:
            try:
                message: str = self.subscribers[topic].get(timeout=10)  # Wait for a message
                yield myservice_pb2.Message(data=message)
            except queue.Empty:
                continue  # Keep the stream open

    def publish(self, topic: str, message: str) -> None:
        """Publishes a message to subscribers."""
        if topic in self.subscribers:
            self.subscribers[topic].put(message)


class GrpcServer:
    def __init__(self, address: Tuple[str, int], on_request_received: Callable[[myservice_pb2.Request], myservice_pb2.Response]) -> None:
        """Listen for RPC calls.

        Args:
            address: IP address and port number
            on_request_received: Function to get executed when a remote procedure call is received.
        """
        self.executor = futures.ThreadPoolExecutor(max_workers=10)  # Store executor
        self.server = grpc.server(self.executor)
        self.service: MyService = MyService(on_request_received)
        myservice_pb2_grpc.add_MyServiceServicer_to_server(self.service, self.server)
        self.server.add_insecure_port(f"{address[0]}:{address[1]}")
        self.server.start()
        print(f"RPC server started at {address[0]}:{address[1]}")

    def publish(self, topic: str, message: str) -> None:
        """Publishes a message to all subscribers of a topic."""
        self.service.publish(topic, message)

    def terminate(self) -> None:
        """Cleanup resources."""
        print("Shutting down server...")
        
        # Stop the server gracefully
        self.server.stop(5)
        
        # Allow executor to finish any pending tasks
        self.executor.shutdown(wait=False, cancel_futures=True)  # Don't wait indefinitely
        
        # # Force termination if threads are still running after a brief wait
        # timeout = 3  # Timeout in seconds
        # start_time = time.time()
        # 
        # while time.time() - start_time < timeout:
        #     if self.executor._work_queue.empty() and len(self.executor._threads) == 0:
        #         break
        #     time.sleep(0.1)  # Check every 100 ms
        # 
        # # Forcefully stop remaining threads if still hanging
        # if len(self.executor._threads) > 0:
        #     print("Forcing shutdown of remaining threads.")
        #     for t in self.executor._threads:
        #         t.join()  # Wait for threads to finish
        # 
        # print("Server shut down successfully.")


if __name__ == "__main__":
    def on_request_received(request: myservice_pb2.Request) -> myservice_pb2.Response:
        """
        Function to get executed when a remote procedure call is received.
        Args:
            request: the RPC data
        Returns:
            response to the RPC call
        """
        response: myservice_pb2.Response = myservice_pb2.Response(result="Processed: " + request.data)
        return response

    RPC_ADDRESS: Tuple[str, int] = ("127.0.0.1", 8888)
    rpc_listener: GrpcServer = GrpcServer(RPC_ADDRESS, on_request_received)

    try:
        for i in range(5):
            time.sleep(1)  # Keep the server running
            rpc_listener.publish("updates", "New data available!")
    except KeyboardInterrupt:
        rpc_listener.terminate()