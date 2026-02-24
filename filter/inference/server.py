import grpc
from concurrent import futures
import sys
import os

# Add generated proto files to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated'))

from filter.v1 import filter_pb2
from filter.v1 import filter_pb2_grpc


class FilterServiceServicer(filter_pb2_grpc.FilterServiceServicer):
    def ClassifyMessage(self, request, context):
        """Classify a message and return category, severity, and risk assessment."""
        try:
            message = request.message
            
            # Default/dummy logic for now
            return filter_pb2.ClassifyResponse(
                category="General",
                category_confidence=0.85,
                severity="Low",
                severity_confidence=0.90,
                is_risk=False
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error processing message: {str(e)}")
            return filter_pb2.ClassifyResponse()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    filter_pb2_grpc.add_FilterServiceServicer_to_server(
        FilterServiceServicer(), server
    )
    
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Filter gRPC server started on port 50051")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
