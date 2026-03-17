"""gRPC server implementation for SentinelAI Filter Service."""

# pylint: disable=wrong-import-position,import-error,no-name-in-module

# NOTE: Only respect disabled linting if you are adhering to best practices
#       in retrospect. The import structure is designed to allow the server
#       to run without issues regardless of execution context.

# WARNING: Only ignore import errors if you have verified that the imports
#          work correctly in all execution contexts.

import os
import sys
from concurrent import futures
from datetime import datetime
from pathlib import Path

# Add parent and generated proto files to path BEFORE other imports
filter_dir = Path(__file__).parent.parent
sys.path.insert(0, str(filter_dir / "generated"))
sys.path.insert(0, str(filter_dir))

import grpc
from dotenv import load_dotenv

from filter.v1 import filter_pb2  # type: ignore[reportMissingImports]
from filter.v1 import filter_pb2_grpc  # type: ignore[reportMissingImports]
import config
from services.model_factory import load_onnx_model_and_tokenizer
from services.classification_utils import (
    tokenize_message,
    create_chunks,
    prepare_chunk_inputs,
    run_chunk_inference,
    process_chunk_predictions,
    aggregate_chunk_results
)

load_dotenv()


class FilterServiceServicer(filter_pb2_grpc.FilterServiceServicer):
    """gRPC Servicer for the Filter Service."""

    def __init__(self):
        """Initialise tokenizer and ONNX model."""
        print("[SERVER] Initialising FilterServiceServicer...")

        self.model_name = os.environ.get("MODEL_NAME", config.MODEL_NAME)
        self.max_length = int(os.environ.get("MAX_TOKEN_LENGTH", config.MAX_LENGTH))
        self.overlap = int(os.environ.get("OVERLAP", 32))
        self.threshold = float(os.environ.get("THRESHOLD", 0.5))

        print("[SERVER] Configuration loaded:")
        print(f"[SERVER]   Model: {self.model_name}")
        print(f"[SERVER]   Max length: {self.max_length}")
        print(f"[SERVER]   Overlap: {self.overlap}")
        print(f"[SERVER]   Threshold: {self.threshold}")

        print("[SERVER] Loading ONNX model and tokenizer...")
        self.onnx_session, self.tokenizer = load_onnx_model_and_tokenizer()

        # Get special token IDs from tokenizer
        self.cls_token_id = self.tokenizer.token_to_id('[CLS]')  # type: ignore
        self.sep_token_id = self.tokenizer.token_to_id('[SEP]')  # type: ignore
        self.pad_token_id = self.tokenizer.token_to_id('[PAD]')  # type: ignore
        print(f"[SERVER] Special tokens - CLS: {self.cls_token_id}, "
              f"SEP: {self.sep_token_id}, PAD: {self.pad_token_id}")

        print("[SERVER] ✓ FilterServiceServicer initialised successfully")

    def ClassifyMessage(self, request, context):  # pylint: disable=invalid-name
        """Classify a message using sliding window approach."""
        print("[REQUEST] Received classification request")
        try:
            # Prepend timestamp at current time as context
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            message = f"[{now}] {request.message}"
            print(f"[REQUEST] Message length: {len(message)} chars (context included)")

            # Tokenize message
            tokens = tokenize_message(self.tokenizer, message)
            print(f"[REQUEST] Tokenized into {len(tokens)} tokens")

            # Handle empty messages
            if len(tokens) == 0:
                return filter_pb2.ClassifyResponse(
                    category="neutral",
                    category_confidence=1.0,
                    severity="none",
                    severity_confidence=1.0,
                    is_risk=False,
                    all_responses=""
                )

            # Create chunks with sliding window
            chunks = create_chunks(tokens, self.max_length, self.overlap)
            print(f"[REQUEST] Split into {len(chunks)} chunks for processing")

            # Process each chunk
            category_labels = {v: k for k, v in config.CATEGORY_MAP.items()}
            severity_labels = {v: k for k, v in config.SEVERITY_MAP.items()}

            chunk_results = []
            for chunk in chunks:
                # Prepare inputs
                input_ids, attention_mask = prepare_chunk_inputs(
                    chunk,
                    self.cls_token_id,
                    self.sep_token_id,
                    self.pad_token_id,
                    self.max_length
                )

                # Run inference
                category_logits, severity_logits = run_chunk_inference(
                    self.onnx_session,
                    input_ids,
                    attention_mask
                )

                # Process predictions
                result = process_chunk_predictions(
                    category_logits,
                    severity_logits,
                    category_labels,
                    severity_labels,
                    config.RISK_CATEGORIES
                )
                chunk_results.append(result)

            # Aggregate results
            final_result = aggregate_chunk_results(chunk_results, self.threshold)

            print(f"[RESPONSE] Classification complete: category={final_result['category']}"
                  f"({final_result['category_confidence']:.3f}), "
                  f"severity={final_result['severity']}"
                  f"({final_result['severity_confidence']:.3f}), "
                  f"is_risk={final_result['is_risk']}")

            return filter_pb2.ClassifyResponse(
                category=final_result["category"],
                category_confidence=final_result["category_confidence"],
                severity=final_result["severity"],
                severity_confidence=final_result["severity_confidence"],
                is_risk=final_result["is_risk"],
                all_responses=final_result["all_responses"]
            )

        except Exception as e: # pylint: disable=broad-exception-caught
            print(f"[ERROR] Failed to process message: {str(e)}")

            import traceback # pylint: disable=import-outside-toplevel
            traceback.print_exc()

            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error processing message: {str(e)}")
            return filter_pb2.ClassifyResponse()


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
