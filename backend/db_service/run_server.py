from concurrent import futures
import grpc

from protos.db.v1 import db_pb2_grpc
from backend.db_service.server import DatabaseServiceServicer


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    db_pb2_grpc.add_DatabaseServiceServicer_to_server(
        DatabaseServiceServicer(),
        server,
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC DB server running on :50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()