"""
Filter Service
gRPC client stub to communicate with the AI filter microservice.
Supports single-message and batch classification.
"""
import os
import grpc
import logging
from typing import List, Optional
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


def _response_to_result(response) -> FilterResult:
    return FilterResult(
        is_risk=response.is_risk,
        category=response.category,
        category_confidence=response.category_confidence,
        severity=response.severity,
        severity_confidence=response.severity_confidence,
    )


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

            return _response_to_result(response)

    except grpc.RpcError as e:
        logger.error(f"gRPC error calling filter service: {e.code()} - {e.details()}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling filter service: {e}")
        return None


def filter_messages(texts: List[str]) -> List[Optional[FilterResult]]:
    """
    Classify multiple messages in a single gRPC call.
    Falls back to per-message calls if the batch RPC is unavailable.

    Args:
        texts: List of message texts to analyze

    Returns:
        List of FilterResult | None in input order.
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

            results = [_response_to_result(r) for r in response.results]

            risk_count = sum(1 for r in results if r.is_risk)
            logger.info(f"Batch filter: {len(texts)} messages, {risk_count} flagged as risk")

            return results

    except grpc.RpcError as e:
        logger.warning(f"Batch gRPC failed ({e.code()}), falling back to per-message calls")
    except Exception as e:
        logger.error(f"Unexpected batch error: {e}, falling back to per-message calls")

    results = []
    for text in texts:
        try:
            results.append(filter_message(text))
        except Exception as exc:
            logger.error(f"Single filter_message fallback failed: {exc}, defaulting to None")
            results.append(None)
    return results
