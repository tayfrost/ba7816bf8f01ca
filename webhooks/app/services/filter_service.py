"""
Filter Service
gRPC client stub to communicate with the AI filter microservice.
"""
import os
import grpc
import logging
from dataclasses import dataclass
from filter.v1 import filter_pb2, filter_pb2_grpc

logger = logging.getLogger(__name__)

FILTER_SERVICE_HOST = os.getenv("FILTER_SERVICE_HOST", "filter:50051")


@dataclass
class FilterResult:
    is_risk: bool
    category: str
    category_confidence: float
    severity: str
    severity_confidence: float


def filter_message(text: str) -> FilterResult | None:
    """
    Classify a message via gRPC and determine if it should be processed.

    Args:
        text: The message text to analyze

    Returns:
        FilterResult if successful, None on error (fail closed)
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

            return FilterResult(
                is_risk=response.is_risk,
                category=response.category,
                category_confidence=response.category_confidence,
                severity=response.severity,
                severity_confidence=response.severity_confidence,
            )

    except grpc.RpcError as e:
        logger.error(f"gRPC error calling filter service: {e.code()} - {e.details()}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling filter service: {e}")
        return None