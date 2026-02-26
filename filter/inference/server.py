import grpc
from concurrent import futures
import sys
import os
from pathlib import Path
import numpy as np
from dotenv import load_dotenv
from transformers import AutoTokenizer

# Add parent and generated proto files to path
filter_dir = Path(__file__).parent.parent
sys.path.insert(0, str(filter_dir / "generated"))
sys.path.insert(0, str(filter_dir))

load_dotenv()

from filter.v1 import filter_pb2
from filter.v1 import filter_pb2_grpc
import config
from services.model_factory import load_model_for_inference


class FilterServiceServicer(filter_pb2_grpc.FilterServiceServicer):
    def __init__(self):
        """Initialize tokenizer and ONNX model."""
        self.model_name = os.environ.get("MODEL_NAME", config.MODEL_NAME)
        self.max_length = int(os.environ.get("max_token_length", config.MAX_LENGTH))
        self.overlap = int(os.environ.get("overlap", 32))
        self.threshold = float(os.environ.get("threshold", 0.5))
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.onnx_session = load_model_for_inference()
        
        print(f"✓ Model loaded: {self.model_name}")
        print(f"✓ Max length: {self.max_length}, Overlap: {self.overlap}, Threshold: {self.threshold}")
    
    def ClassifyMessage(self, request, context):
        """Classify a message using sliding window approach."""
        try:
            message = request.message
            
            # Tokenize full message
            tokens = self.tokenizer.encode(message, add_special_tokens=False)
            
            # Handle empty or short messages
            if len(tokens) == 0:
                return filter_pb2.ClassifyResponse(
                    category="neutral",
                    category_confidence=1.0,
                    severity="none",
                    severity_confidence=1.0,
                    is_risk=False,
                    all_responses=""
                )
            
            # Sliding window with overlap
            chunks = []
            start = 0
            while start < len(tokens):
                end = min(start + self.max_length - 2, len(tokens))  # -2 for [CLS] and [SEP]
                chunk = tokens[start:end]
                chunks.append(chunk)
                
                if end >= len(tokens):
                    break
                start += (self.max_length - self.overlap - 2)
            
            # Run inference on each chunk
            all_responses = []
            max_category_conf = 0.0
            max_category = "neutral"
            max_severity_conf = 0.0
            max_severity = "none"
            max_risk_score = 0.0
            
            category_labels = {v: k for k, v in config.CATEGORY_MAP.items()}
            severity_labels = {v: k for k, v in config.SEVERITY_MAP.items()}
            
            for i, chunk in enumerate(chunks):
                # Add special tokens
                input_ids = [self.tokenizer.cls_token_id] + chunk + [self.tokenizer.sep_token_id]
                attention_mask = [1] * len(input_ids)
                
                # Pad to max_length
                padding_length = self.max_length - len(input_ids)
                input_ids += [self.tokenizer.pad_token_id] * padding_length
                attention_mask += [0] * padding_length
                
                # Convert to numpy arrays
                input_ids_array = np.array([input_ids], dtype=np.int64)
                attention_mask_array = np.array([attention_mask], dtype=np.int64)
                
                # Run inference
                outputs = self.onnx_session.run(
                    None,
                    {
                        "input_ids": input_ids_array,
                        "attention_mask": attention_mask_array
                    }
                )
                
                category_logits, severity_logits = outputs
                
                # Get predictions
                category_probs = self._softmax(category_logits[0])
                severity_probs = self._softmax(severity_logits[0])
                
                category_idx = int(np.argmax(category_probs))
                category_conf = float(category_probs[category_idx])
                category_name = category_labels[category_idx]
                
                severity_idx = int(np.argmax(severity_probs))
                severity_conf = float(severity_probs[severity_idx])
                severity_name = severity_labels[severity_idx]
                
                # Calculate risk score (confidence if category is in risk categories)
                is_risk_category = category_name in config.RISK_CATEGORIES
                risk_score = category_conf if is_risk_category else 0.0
                
                # Store response
                response_str = f"[Chunk {i+1}] Category: {category_name}({category_conf:.3f}), Severity: {severity_name}({severity_conf:.3f}), Risk: {risk_score:.3f}"
                all_responses.append(response_str)
                
                # Update maximums
                if risk_score > max_risk_score:
                    max_risk_score = risk_score
                    max_category = category_name
                    max_category_conf = category_conf
                    max_severity = severity_name
                    max_severity_conf = severity_conf
                elif risk_score == max_risk_score and category_conf > max_category_conf:
                    max_category = category_name
                    max_category_conf = category_conf
                    max_severity = severity_name
                    max_severity_conf = severity_conf
            
            # Determine final risk status
            is_risk = max_risk_score > self.threshold
            
            # Combine all responses into single string
            all_responses_text = " | ".join(all_responses)
            
            return filter_pb2.ClassifyResponse(
                category=max_category,
                category_confidence=max_category_conf,
                severity=max_severity,
                severity_confidence=max_severity_conf,
                is_risk=is_risk,
                all_responses=all_responses_text
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error processing message: {str(e)}")
            return filter_pb2.ClassifyResponse()
    
    @staticmethod
    def _softmax(x):
        
        """Compute softmax values."""
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    filter_pb2_grpc.add_FilterServiceServicer_to_server(
        FilterServiceServicer(), server
    )
    
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Filter gRPC server started on port 50051")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
