"""
Filter Service

gRPC client stub to communicate with the AI filter microservice.
Supports single-message and batch classification.
"""

import os
import grpc
import logging
from typing import List

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
        return False
    except Exception as e:
        logger.error(f"Unexpected error calling filter service: {e}")
        return False


def filter_messages(texts: List[str]) -> List[bool]:
    """
    Classify multiple messages in a single gRPC call.
    Falls back to per-message calls if the batch RPC is unavailable.

    Args:
        texts: List of message texts to analyze

    Returns:
        List of booleans — True where the message is a risk, False otherwise.
        Length and order match the input list.
    """
    if not texts:
        return []

    if len(texts) == 1:
        return [filter_message(texts[0])]

    try:
        with grpc.insecure_channel(FILTER_SERVICE_HOST) as channel:
            stub = filter_pb2_grpc.FilterServiceStub(channel)
            request = filter_pb2.BatchClassifyRequest(messages=texts)
            response = stub.ClassifyMessages(request)

            results = [r.is_risk for r in response.results]

            risk_count = sum(results)
            logger.info(f"Batch filter: {len(texts)} messages, {risk_count} flagged as risk")

            return results

    except grpc.RpcError as e:
        logger.warning(f"Batch gRPC failed ({e.code()}), falling back to per-message calls")
        return [filter_message(text) for text in texts]
    except Exception as e:
        logger.error(f"Unexpected batch error: {e}, falling back to per-message calls")
        return [filter_message(text) for text in texts]
