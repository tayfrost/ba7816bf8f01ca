"""
Filter Service

gRPC client stub to communicate with the AI filter microservice.
"""

import os
import grpc
import logging

from filter.v1 import filter_pb2, filter_pb2_grpc

logger = logging.getLogger(__name__)

FILTER_SERVICE_HOST = os.getenv("FILTER_SERVICE_HOST", "filter:50051")


def filter_message(text: str) -> bool:
    """
    Classify a message via gRPC and determine if it should be processed.
    
    Args:
        text: The message text to analyze
        
    Returns:
        True if the message is a risk and should be processed/stored, False otherwise
    """
    try:
        with grpc.insecure_channel(FILTER_SERVICE_HOST) as channel:
            stub = filter_pb2_grpc.FilterServiceStub(channel)
            request = filter_pb2.ClassifyRequest(message=text)
            response = stub.ClassifyMessage(request)
            
            logger.info(
                f"Filter response: category={response.category}, "
                f"is_risk={response.is_risk}, confidence={response.category_confidence:.3f}"
            )
            
            return response.is_risk
    
    except grpc.RpcError as e:
        logger.error(f"gRPC error calling filter service: {e.code()} - {e.details()}")
        return False  # Fail closed - don't process on error
    except Exception as e:
        logger.error(f"Unexpected error calling filter service: {e}")
        return False
