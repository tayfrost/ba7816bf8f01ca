"""gRPC server implementation for SentinelAI Filter Service.

Currently uses PyTorch as the primary inference backend for stability 
and consistent classification logic.
"""

# pylint: disable=wrong-import-position,import-error,no-name-in-module

# NOTE: Only respect disabled linting if you are adhering to best practices
#       in retrospect. The import structure is designed to allow the server
#       to run without issues regardless of execution context.

# WARNING: Only ignore import errors if you have verified that the imports
#          work correctly in all execution contexts.

import logging
import os
import json
import sys
import time
import urllib.request
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Add parent and generated proto files to path BEFORE other imports
filter_dir = Path(__file__).parent.parent
sys.path.insert(0, str(filter_dir / "generated"))
sys.path.insert(0, str(filter_dir))

import grpc
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, start_http_server as prometheus_start_http_server
from transformers import AutoTokenizer

from filter.v1 import filter_pb2  # type: ignore[reportMissingImports]
from filter.v1 import filter_pb2_grpc  # type: ignore[reportMissingImports]

import config

from services.model_factory import load_onnx_model_and_tokenizer, load_production_model
from services.classification_utils import (
    tokenize_message,
    create_chunks,
    prepare_chunk_inputs,
    run_chunk_inference,
    process_chunk_predictions,
    aggregate_chunk_results
)

load_dotenv()

# --- prometheus metrics ---
# Exposed via a lightweight HTTP server on port 9091 (scraped by prometheus).
# gRPC has no HTTP layer, so start_http_server runs in a background daemon thread.

grpc_requests_total = Counter(
    "grpc_requests_total",
    "Total gRPC calls handled by the filter service",
    ["method", "outcome"],  # outcome: success | error
)

grpc_request_duration_seconds = Histogram(
    "grpc_request_duration_seconds",
    "gRPC call duration in seconds",
    ["method"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

grpc_batch_size = Histogram(
    "grpc_batch_size",
    "Number of messages per ClassifyMessages batch call",
    buckets=[1, 2, 5, 10, 25, 50, 100],
)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai_service:8001/analyze")
_AI_DISPATCH_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ai-dispatch")

_GRPC_SECRET = os.getenv("GRPC_SECRET", "")


class _SecretInterceptor(grpc.ServerInterceptor):
    """Reject requests that don't carry the correct x-grpc-secret metadata header.
    If GRPC_SECRET is not set the interceptor is a no-op (backward compatible)."""

    def intercept_service(self, continuation, handler_call_details):
        if not _GRPC_SECRET:
            return continuation(handler_call_details)
        metadata = dict(handler_call_details.invocation_metadata)
        if metadata.get("x-grpc-secret") != _GRPC_SECRET:
            logger.warning("Rejected gRPC call — bad or missing secret")

            def _reject(request, context):
                context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid gRPC secret")

            return grpc.unary_unary_rpc_method_handler(_reject)
        return continuation(handler_call_details)


def _dispatch_to_ai(meta: dict, text: str, result: dict) -> None:
    """POST a risk-flagged message to the AI service. Runs in _AI_DISPATCH_POOL."""
    payload = {
        "message":         text,
        "filter_category": result["category"],
        "filter_severity": result["severity"],
        "company_id":      meta.get("company_id"),
        "user_id":         str(meta.get("user_id", "")),
        "source":          meta.get("source", ""),
        "sent_at":         meta.get("sent_at", ""),
        "conversation_id": meta.get("conversation_id", ""),
        "content_raw":     meta.get("content_raw", {"text": text}),
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            AI_SERVICE_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            logger.info("Dispatched to AI service — status=%s user_id=%s", resp.status, meta.get("user_id"))
    except Exception as e:
        logger.error("Failed to dispatch to AI service for user_id=%s: %s", meta.get("user_id"), e)


class FilterServiceServicer(filter_pb2_grpc.FilterServiceServicer):
    """gRPC Servicer for the Filter Service."""

    def __init__(self):
        """Initialise tokenizer and ONNX model."""
        self.model_name = os.environ.get("MODEL_NAME", config.MODEL_NAME)
        # Keep compatibility with both lowercase and current uppercase envs
        self.max_length = int(
            os.environ.get("MAX_TOKEN_LENGTH", os.environ.get("max_token_length", config.MAX_LENGTH))
        )
        self.overlap = int(os.environ.get("OVERLAP", os.environ.get("overlap", 32)))
        self.threshold = float(os.environ.get("THRESHOLD", os.environ.get("threshold", 0.5)))
        self.soft_conf_threshold = float(os.environ.get("SOFT_CONF_THRESHOLD", 0.8))
        self.risk_escalation_floor = float(os.environ.get("RISK_ESCALATION_FLOOR", 0.2))
        self.inference_backend = os.environ.get("INFERENCE_BACKEND", "pytorch").strip().lower()
        self.onnx_variant = os.environ.get("ONNX_VARIANT", "fp32")

        logger.info(
            "Config — model=%s backend=%s max_length=%d overlap=%d threshold=%.2f",
            self.model_name, self.inference_backend, self.max_length, self.overlap, self.threshold,
        )

        if self.inference_backend == "pytorch":
            logger.info("Loading PyTorch model and tokenizer...")
            self.onnx_session = load_production_model()
            self.tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
        else:
            logger.info("Loading ONNX model (%s)...", self.onnx_variant)
            self.onnx_session, self.tokenizer = load_onnx_model_and_tokenizer(
                onnx_variant=self.onnx_variant,
            )

        if self.onnx_session is None:
            raise RuntimeError(
                "Inference model failed to load. "
                f"Backend='{self.inference_backend}'"
            )

        if self.tokenizer is None:
            raise RuntimeError(
                "Tokenizer failed to load. "
                f"Backend='{self.inference_backend}'"
            )

        # Get special token IDs from tokenizer (supports tokenizers + transformers)
        if hasattr(self.tokenizer, "token_to_id"):
            self.cls_token_id = self.tokenizer.token_to_id('[CLS]')  # type: ignore
            self.sep_token_id = self.tokenizer.token_to_id('[SEP]')  # type: ignore
            self.pad_token_id = self.tokenizer.token_to_id('[PAD]')  # type: ignore
        else:
            self.cls_token_id = int(self.tokenizer.cls_token_id)
            self.sep_token_id = int(self.tokenizer.sep_token_id)
            self.pad_token_id = int(self.tokenizer.pad_token_id)

        logger.info("Ready — CLS=%d SEP=%d PAD=%d", self.cls_token_id, self.sep_token_id, self.pad_token_id)

    @staticmethod
    def _parse_enveloped_message(raw_message: str) -> tuple[str, str | None]:
        """Parse optional webhooks envelope and return (text, sent_at)."""
        try:
            payload = json.loads(raw_message)
            if isinstance(payload, dict) and "text" in payload:
                text = payload.get("text") or ""
                meta = payload.get("meta") or {}
                sent_at = meta.get("sent_at") if isinstance(meta, dict) else None
                return str(text), sent_at if isinstance(sent_at, str) else None
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        return raw_message, None

    def _build_contextual_message(self, raw_message: str) -> str:
        """Build classification text from parsed payload content only."""
        text, _ = self._parse_enveloped_message(raw_message)
        return text

    def _classify_single(self, message: str) -> dict:
        """Core classification logic for a single message. Returns a result dict."""
        # Preserve empty-input behavior contract before payload text extraction.
        if not (message or "").strip():
            return {
                "category": "neutral",
                "category_confidence": 1.0,
                "severity": "none",
                "severity_confidence": 1.0,
                "is_risk": False,
                "all_responses": "",
            }

        contextual_message = self._build_contextual_message(message)
        tokens = tokenize_message(self.tokenizer, contextual_message)

        if len(tokens) == 0:
            return {
                "category": "neutral",
                "category_confidence": 1.0,
                "severity": "none",
                "severity_confidence": 1.0,
                "is_risk": False,
                "all_responses": "",
            }

        chunks = create_chunks(tokens, self.max_length, self.overlap)
        category_labels = {v: k for k, v in config.CATEGORY_MAP.items()}
        severity_labels = {v: k for k, v in config.SEVERITY_MAP.items()}

        chunk_results = []
        for chunk in chunks:
            input_ids, attention_mask = prepare_chunk_inputs(
                chunk, self.cls_token_id, self.sep_token_id,
                self.pad_token_id, self.max_length,
            )
            category_logits, severity_logits = run_chunk_inference(
                self.onnx_session, input_ids, attention_mask,
            )
            result = process_chunk_predictions(
                category_logits, severity_logits,
                category_labels, severity_labels, config.RISK_CATEGORIES,
            )
            chunk_results.append(result)

        return aggregate_chunk_results(chunk_results, self.threshold)

    def _result_to_response(self, result: dict) -> "filter_pb2.ClassifyResponse":
        return filter_pb2.ClassifyResponse(
            category=result["category"],
            category_confidence=result["category_confidence"],
            severity=result["severity"],
            severity_confidence=result["severity_confidence"],
            is_risk=result["is_risk"],
            all_responses=result["all_responses"],
        )

    def ClassifyMessage(self, request, context):
        """Classify a single message using sliding window approach."""
        logger.debug("ClassifyMessage: %d chars", len(request.message))
        _start = time.perf_counter()
        try:
            message = request.message

            # Parse envelope for AI dispatch context.
            # _classify_single receives the original message so payload text extraction
            # remains consistent with webhook envelopes.
            try:
                envelope = json.loads(message)
                text = envelope.get("text", message) if isinstance(envelope, dict) else message
                meta = envelope.get("meta", {}) if isinstance(envelope, dict) else {}
            except (json.JSONDecodeError, AttributeError):
                text = message
                meta = {}

            final_result = self._classify_single(message)

            logger.info(
                "Classified: category=%s(%.2f) severity=%s(%.2f) is_risk=%s",
                final_result["category"], final_result["category_confidence"],
                final_result["severity"], final_result["severity_confidence"],
                final_result["is_risk"],
            )

            cat = final_result["category"]
            conf = final_result["category_confidence"]
            soft_hit = cat in {"neutral", "humor_sarcasm"} and conf < self.soft_conf_threshold
            risk_hit = cat in config.RISK_CATEGORIES and conf >= self.risk_escalation_floor
            should_dispatch = final_result["is_risk"] or soft_hit or risk_hit

            if should_dispatch and meta:
                logger.info(
                    "Dispatching to AI — reason: is_risk=%s soft_hit=%s risk_hit=%s user_id=%s",
                    final_result["is_risk"], soft_hit, risk_hit, meta.get("user_id"),
                )
                _AI_DISPATCH_POOL.submit(_dispatch_to_ai, meta, text, final_result)

            grpc_requests_total.labels(method="ClassifyMessage", outcome="success").inc()
            grpc_request_duration_seconds.labels(method="ClassifyMessage").observe(time.perf_counter() - _start)
            return self._result_to_response(final_result)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception("Failed to process message: %s", e)
            grpc_requests_total.labels(method="ClassifyMessage", outcome="error").inc()
            grpc_request_duration_seconds.labels(method="ClassifyMessage").observe(time.perf_counter() - _start)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error processing message: {str(e)}")
            return filter_pb2.ClassifyResponse()

    _SAFE_DEFAULT = {
        "category": "neutral", "category_confidence": 0.0,
        "severity": "none", "severity_confidence": 0.0,
        "is_risk": False, "all_responses": "",
    }

    def ClassifyMessages(self, request, _context):
        """Classify multiple messages in a single RPC call.

        Individual message failures are caught and returned as safe defaults
        so that one bad message does not abort the entire batch.
        """
        messages = list(request.messages)
        logger.info("ClassifyMessages: %d messages", len(messages))
        grpc_batch_size.observe(len(messages))

        if not messages:
            return filter_pb2.BatchClassifyResponse(results=[])

        _start = time.perf_counter()
        results = []
        for i, message in enumerate(messages):
            try:
                result = self._classify_single(message)
                results.append(self._result_to_response(result))
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Batch message %d/%d failed, using safe default: %s", i + 1, len(messages), e)
                results.append(self._result_to_response(self._SAFE_DEFAULT))

        grpc_requests_total.labels(method="ClassifyMessages", outcome="success").inc()
        grpc_request_duration_seconds.labels(method="ClassifyMessages").observe(time.perf_counter() - _start)
        logger.info("Batch complete: %d/%d classified", len(results), len(messages))
        return filter_pb2.BatchClassifyResponse(results=results)


_METRICS_PORT = int(os.getenv("PROMETHEUS_PORT", "9091"))


def serve():
    """Start the gRPC server and a sidecar HTTP server for Prometheus metrics."""
    # Start prometheus HTTP metrics endpoint in a background daemon thread.
    # Prometheus scrapes this at filter:9091/metrics.
    prometheus_start_http_server(_METRICS_PORT)
    logger.info("Prometheus metrics server listening on port %d", _METRICS_PORT)

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[_SecretInterceptor()],
    )

    filter_pb2_grpc.add_FilterServiceServicer_to_server(FilterServiceServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()

    logger.info("Filter gRPC server listening on port 50051")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
