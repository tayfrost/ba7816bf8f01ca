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

import os
import json
import sys
import urllib.request
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Add parent and generated proto files to path BEFORE other imports
filter_dir = Path(__file__).parent.parent
sys.path.insert(0, str(filter_dir / "generated"))
sys.path.insert(0, str(filter_dir))

import grpc
from dotenv import load_dotenv
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

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai_service:8001/analyze")
_AI_DISPATCH_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ai-dispatch")


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
            print(f"[AI] Dispatched to AI service — status={resp.status} user_id={meta.get('user_id')}")
    except Exception as e:
        print(f"[AI] Failed to dispatch to AI service for user_id={meta.get('user_id')}: {e}")


class FilterServiceServicer(filter_pb2_grpc.FilterServiceServicer):
    """gRPC Servicer for the Filter Service."""

    def __init__(self):
        """Initialise tokenizer and ONNX model."""
        print("[SERVER] Initialising FilterServiceServicer...")

        self.model_name = os.environ.get("MODEL_NAME", config.MODEL_NAME)
        # Keep compatibility with both lowercase and current uppercase envs
        self.max_length = int(
            os.environ.get("MAX_TOKEN_LENGTH", os.environ.get("max_token_length", config.MAX_LENGTH))
        )
        self.overlap = int(os.environ.get("OVERLAP", os.environ.get("overlap", 32)))
        self.threshold = float(os.environ.get("THRESHOLD", os.environ.get("threshold", 0.5)))
        self.inference_backend = os.environ.get("INFERENCE_BACKEND", "pytorch").strip().lower()
        self.onnx_variant = os.environ.get("ONNX_VARIANT", "fp32")

        print("[SERVER] Configuration loaded:")
        print(f"[SERVER]   Model: {self.model_name}")
        print(f"[SERVER]   Max length: {self.max_length}")
        print(f"[SERVER]   Overlap: {self.overlap}")
        print(f"[SERVER]   Threshold: {self.threshold}")
        print(f"[SERVER]   Inference backend: {self.inference_backend}")
        print(f"[SERVER]   ONNX variant: {self.onnx_variant}")

        if self.inference_backend == "pytorch":
            print("[SERVER] Loading PyTorch model and tokenizer...")
            self.onnx_session = load_production_model()
            self.tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
        else:
            print("[SERVER] Loading ONNX model and tokenizer...")
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
        print(f"[SERVER] Special tokens - CLS: {self.cls_token_id}, "
              f"SEP: {self.sep_token_id}, PAD: {self.pad_token_id}")

        print("[SERVER] ✓ FilterServiceServicer initialised successfully")

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
        print("[REQUEST] Received classification request")
        try:
            message = request.message
            print(f"[REQUEST] Message length: {len(message)} chars")

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

            print(f"[RESPONSE] Classification complete: category={final_result['category']}({final_result['category_confidence']:.3f}), "
                  f"severity={final_result['severity']}({final_result['severity_confidence']:.3f}), is_risk={final_result['is_risk']}")

            if final_result["is_risk"] and meta:
                print(f"[AI] Risk detected — dispatching to AI service for user_id={meta.get('user_id')}")
                _AI_DISPATCH_POOL.submit(_dispatch_to_ai, meta, text, final_result)

            return self._result_to_response(final_result)

        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"[ERROR] Failed to process message: {str(e)}")

            import traceback # pylint: disable=import-outside-toplevel
            traceback.print_exc()

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
        print(f"[BATCH] Received batch classification request: {len(messages)} messages")

        if not messages:
            return filter_pb2.BatchClassifyResponse(results=[])

        results = []
        for i, message in enumerate(messages):
            try:
                print(f"[BATCH] Processing message {i+1}/{len(messages)} ({len(message)} chars)")
                result = self._classify_single(message)
                results.append(self._result_to_response(result))
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"[BATCH] Message {i+1} failed, returning safe default: {e}")
                results.append(self._result_to_response(self._SAFE_DEFAULT))

        print(f"[BATCH] Batch complete: {len(results)} messages classified")
        return filter_pb2.BatchClassifyResponse(results=results)


def serve():
    """Start the gRPC server."""
    print("[SERVER] Starting gRPC server...")
    print("[SERVER] Creating thread pool executor with 10 workers...")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    print("[SERVER] Initialising FilterServiceServicer...")
    filter_pb2_grpc.add_FilterServiceServicer_to_server(
        FilterServiceServicer(), server
    )

    print("[SERVER] Binding to port 50051...")
    server.add_insecure_port('[::]:50051')

    print("[SERVER] Starting server...")
    server.start()

    print("="*60)
    print("[SERVER] ✓ Filter gRPC server is ready and listening on port 50051")
    print("="*60)

    server.wait_for_termination()


if __name__ == '__main__':
    serve()
