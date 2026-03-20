import grpc
from concurrent import futures
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent and generated proto files to path
filter_dir = Path(__file__).parent.parent
sys.path.insert(0, str(filter_dir / "generated"))
sys.path.insert(0, str(filter_dir))

load_dotenv()

from filter.v1 import filter_pb2
from filter.v1 import filter_pb2_grpc
import config
from inference_services.onnx_factory import load_onnx_model_and_tokenizer
from inference_services.classification_utils import (
    tokenize_message,
    create_chunks,
    prepare_chunk_inputs,
    run_chunk_inference,
    process_chunk_predictions,
    aggregate_chunk_results
)


class FilterServiceServicer(filter_pb2_grpc.FilterServiceServicer):
    def __init__(self):
        """Initialize tokenizer and ONNX model."""
        print("[SERVER] Initializing FilterServiceServicer...")
        
        self.model_name = os.environ.get("MODEL_NAME", config.MODEL_NAME)
        self.max_length = int(os.environ.get("max_token_length", config.MAX_LENGTH))
        self.overlap = int(os.environ.get("overlap", 32))
        self.threshold = float(os.environ.get("threshold", 0.5))
        
        print(f"[SERVER] Configuration loaded:")
        print(f"[SERVER]   Model: {self.model_name}")
        print(f"[SERVER]   Max length: {self.max_length}")
        print(f"[SERVER]   Overlap: {self.overlap}")
        print(f"[SERVER]   Threshold: {self.threshold}")
        
        print(f"[SERVER] Loading ONNX model and tokenizer...")
        self.onnx_session, self.tokenizer = load_onnx_model_and_tokenizer()
        
        # Get special token IDs from tokenizer
        self.cls_token_id = self.tokenizer.token_to_id('[CLS]')
        self.sep_token_id = self.tokenizer.token_to_id('[SEP]')
        self.pad_token_id = self.tokenizer.token_to_id('[PAD]')
        print(f"[SERVER] Special tokens - CLS: {self.cls_token_id}, SEP: {self.sep_token_id}, PAD: {self.pad_token_id}")
        
        print(f"[SERVER] ✓ FilterServiceServicer initialized successfully")
    
    def _classify_single(self, message: str) -> dict:
        """Core classification logic for a single message. Returns a result dict."""
        tokens = tokenize_message(self.tokenizer, message)

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
        print(f"[REQUEST] Received classification request")
        try:
            message = request.message
            print(f"[REQUEST] Message length: {len(message)} chars")

            final_result = self._classify_single(message)

            print(f"[RESPONSE] Classification complete: category={final_result['category']}({final_result['category_confidence']:.3f}), "
                  f"severity={final_result['severity']}({final_result['severity_confidence']:.3f}), is_risk={final_result['is_risk']}")

            return self._result_to_response(final_result)

        except Exception as e:
            print(f"[ERROR] Failed to process message: {str(e)}")
            import traceback
            traceback.print_exc()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error processing message: {str(e)}")
            return filter_pb2.ClassifyResponse()

    def ClassifyMessages(self, request, context):
        """Classify multiple messages in a single RPC call."""
        messages = list(request.messages)
        print(f"[BATCH] Received batch classification request: {len(messages)} messages")
        try:
            results = []
            for i, message in enumerate(messages):
                print(f"[BATCH] Processing message {i+1}/{len(messages)} ({len(message)} chars)")
                result = self._classify_single(message)
                results.append(self._result_to_response(result))

            print(f"[BATCH] Batch complete: {len(results)} messages classified")
            return filter_pb2.BatchClassifyResponse(results=results)

        except Exception as e:
            print(f"[ERROR] Batch classification failed: {str(e)}")
            import traceback
            traceback.print_exc()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Batch error: {str(e)}")
            return filter_pb2.BatchClassifyResponse()


def serve():
    print("[SERVER] Starting gRPC server...")
    print("[SERVER] Creating thread pool executor with 10 workers...")
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    print("[SERVER] Initializing FilterServiceServicer...")
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
