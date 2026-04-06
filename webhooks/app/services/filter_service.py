"""
Filter Service
gRPC client stub to communicate with the AI filter microservice.

Fire-and-forget dispatch: messages are sent without waiting for a response.
Identifiers are embedded in the message string as a JSON envelope so the
filter service can reconstruct context without proto changes:

    {"meta": {"user_id": "...", "company_id": 1, ...}, "text": "..."}
"""
import os
import json
import grpc
import logging
from dataclasses import dataclass
from typing import List, Optional
from filter.v1 import filter_pb2, filter_pb2_grpc

logger = logging.getLogger(__name__)

FILTER_SERVICE_HOST = os.getenv("FILTER_SERVICE_HOST", "filter:50051")

# Persistent channel — kept alive for the process lifetime so that
# fire-and-forget .future() calls are not killed by a closing context manager.
_channel = grpc.insecure_channel(FILTER_SERVICE_HOST)
_stub    = filter_pb2_grpc.FilterServiceStub(_channel)


@dataclass
class FilterResult:
    is_risk: bool
    category: str
    category_confidence: float
    severity: str
    severity_confidence: float


def dispatch_to_filter(meta: dict, text: str) -> None:
    """
    Fire-and-forget: send message + identifiers to the filter service.
    Does not block; the filter service owns the rest of the pipeline.

    meta should contain at minimum:
        user_id, company_id, source
    and optionally:
        team_id, slack_user_id, email, conversation_id
    """
    payload = json.dumps({"meta": meta, "text": text}, default=str)
    try:
        future = _stub.ClassifyMessage.future(
            filter_pb2.ClassifyRequest(message=payload)
        )
        # Attach a no-op callback so gRPC doesn't log unhandled errors loudly.
        future.add_done_callback(lambda f: _on_dispatch_done(f, meta))
    except Exception as e:
        logger.error(f"dispatch_to_filter failed to send: {e}")


def _on_dispatch_done(future, meta: dict) -> None:
    try:
        future.result()
    except grpc.RpcError as e:
        logger.warning(
            f"filter dispatch RPC error for user_id={meta.get('user_id')}: "
            f"{e.code()} - {e.details()}"
        )
    except Exception as e:
        logger.warning(f"filter dispatch unexpected error: {e}")


# ── Synchronous helpers (kept for any internal callers that still need them) ──

def _response_to_result(response) -> FilterResult:
    return FilterResult(
        is_risk=response.is_risk,
        category=response.category,
        category_confidence=response.category_confidence,
        severity=response.severity,
        severity_confidence=response.severity_confidence,
    )


def filter_message(text: str) -> Optional[FilterResult]:
    try:
        with grpc.insecure_channel(FILTER_SERVICE_HOST) as channel:
            stub = filter_pb2_grpc.FilterServiceStub(channel)
            response = stub.ClassifyMessage(
                filter_pb2.ClassifyRequest(message=text)
            )
            return _response_to_result(response)
    except grpc.RpcError as e:
        logger.error(f"gRPC error calling filter service: {e.code()} - {e.details()}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling filter service: {e}")
        return None


def filter_messages(texts: List[str]) -> List[Optional[FilterResult]]:
    if not texts:
        return []
    if len(texts) == 1:
        return [filter_message(texts[0])]
    try:
        with grpc.insecure_channel(FILTER_SERVICE_HOST) as channel:
            stub = filter_pb2_grpc.FilterServiceStub(channel)
            response = stub.ClassifyMessages(
                filter_pb2.BatchClassifyRequest(messages=texts)
            )
            return [_response_to_result(r) for r in response.results]
    except grpc.RpcError as e:
        logger.warning(
            f"Batch gRPC failed ({getattr(e, 'code', lambda: 'unknown')()}), "
            f"falling back to per-message calls"
        )
    except Exception as e:
        logger.error(f"Unexpected batch error: {e}, falling back to per-message calls")

    results = []
    for text in texts:
        try:
            results.append(filter_message(text))
        except Exception as exc:
            logger.error(f"Single filter_message fallback failed: {exc}")
            results.append(None)
    return results
