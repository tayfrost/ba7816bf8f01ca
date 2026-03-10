"""
Test inference with multiple ONNX model variants.

Tests that all quantized models (FP32, FP16, Dynamic INT8, Static INT8)
produce valid responses through both gRPC endpoints.
"""

import grpc
import sys
import pytest
from pathlib import Path

# Add generated proto files to path
filter_dir = Path(__file__).parent.parent
sys.path.insert(0, str(filter_dir / "generated"))

from filter.v1 import filter_pb2
from filter.v1 import filter_pb2_grpc

# Test messages covering different categories
TEST_MESSAGES = [
    {
        "message": "Just had another amazing day at work! The team is fantastic.",
        "expected_category": "neutral",
        "description": "Neutral/positive message",
    },
    {
        "message": "I'm feeling overwhelmed with deadlines and can't seem to catch up.",
        "expected_category": "stress",
        "description": "Stress-related message",
    },
    {
        "message": "I'm completely burned out and don't want to work anymore.",
        "expected_category": "burnout",
        "description": "Burnout message",
    },
    {
        "message": "Feeling really down lately, nothing seems to help.",
        "expected_category": "depression",
        "description": "Depression-related message",
    },
]

# Model variants to test
MODEL_VARIANTS = ["fp32", "fp16", "dynamic_int8", "static_int8"]


def validate_response(response, model_name="default"):
    """
    Validate that a ClassifyResponse has valid fields.
    
    Args:
        response: ClassifyResponse from gRPC
        model_name: Name of model used (for error messages)
    """
    # Check required fields exist
    assert response.category is not None, f"[{model_name}] Category is None"
    assert response.severity is not None, f"[{model_name}] Severity is None"
    assert isinstance(response.is_risk, bool), f"[{model_name}] is_risk must be boolean"
    
    # Check confidence scores are valid probabilities
    assert 0 <= response.category_confidence <= 1.0, \
        f"[{model_name}] Invalid category_confidence: {response.category_confidence}"
    assert 0 <= response.severity_confidence <= 1.0, \
        f"[{model_name}] Invalid severity_confidence: {response.severity_confidence}"
    
    # Check category is valid
    valid_categories = [
        "neutral", "humor_sarcasm", "stress", "burnout",
        "depression", "harassment", "suicidal_ideation"
    ]
    assert response.category in valid_categories, \
        f"[{model_name}] Invalid category: {response.category}"
    
    # Check severity is valid
    valid_severities = ["none", "early", "middle", "late"]
    assert response.severity in valid_severities, \
        f"[{model_name}] Invalid severity: {response.severity}"
    
    # Check all_responses field exists (can be empty string)
    assert response.all_responses is not None, \
        f"[{model_name}] all_responses is None"


def test_classify_message_default():
    """Test default ClassifyMessage endpoint (backward compatible)."""
    print("\n" + "="*80)
    print("Testing ClassifyMessage (default model)")
    print("="*80)
    
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = filter_pb2_grpc.FilterServiceStub(channel)
        
        for test_case in TEST_MESSAGES:
            print(f"\nTest: {test_case['description']}")
            print(f"Message: {test_case['message'][:60]}...")
            
            request = filter_pb2.ClassifyRequest(
                message=test_case['message']
            )
            
            response = stub.ClassifyMessage(request)
            validate_response(response, "default")
            
            print(f"  ✓ Category: {response.category} ({response.category_confidence:.3f})")
            print(f"  ✓ Severity: {response.severity} ({response.severity_confidence:.3f})")
            print(f"  ✓ Is Risk: {response.is_risk}")


@pytest.mark.parametrize("model_name", MODEL_VARIANTS)
def test_classify_message_with_model(model_name):
    """Test ClassifyMessageWithModel endpoint for each model variant."""
    print(f"\n{'='*80}")
    print(f"Testing ClassifyMessageWithModel: {model_name.upper()}")
    print("="*80)
    
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = filter_pb2_grpc.FilterServiceStub(channel)
        
        for test_case in TEST_MESSAGES:
            print(f"\nTest: {test_case['description']}")
            print(f"Message: {test_case['message'][:60]}...")
            print(f"Model: {model_name}")
            
            request = filter_pb2.ModelClassifyRequest(
                message=test_case['message'],
                model_name=model_name
            )
            
            response = stub.ClassifyMessageWithModel(request)
            validate_response(response, model_name)
            
            print(f"  ✓ Category: {response.category} ({response.category_confidence:.3f})")
            print(f"  ✓ Severity: {response.severity} ({response.severity_confidence:.3f})")
            print(f"  ✓ Is Risk: {response.is_risk}")


def test_all_models_respond():
    """Test that all model variants produce responses (smoke test)."""
    print("\n" + "="*80)
    print("Smoke Test: All Models Respond")
    print("="*80)
    
    test_message = "I'm feeling okay today."
    
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = filter_pb2_grpc.FilterServiceStub(channel)
        
        # Test default endpoint
        print(f"\nTesting default model...")
        request = filter_pb2.ClassifyRequest(message=test_message)
        response = stub.ClassifyMessage(request)
        validate_response(response, "default")
        print(f"  ✓ Default model responds")
        
        # Test each variant
        for model_name in MODEL_VARIANTS:
            print(f"\nTesting {model_name}...")
            request = filter_pb2.ModelClassifyRequest(
                message=test_message,
                model_name=model_name
            )
            
            try:
                response = stub.ClassifyMessageWithModel(request)
                validate_response(response, model_name)
                print(f"  ✓ {model_name} responds")
            except grpc.RpcError as e:
                # Model might not be loaded - report but don't fail test
                if e.code() == grpc.StatusCode.INVALID_ARGUMENT:
                    print(f"  ⚠ {model_name} not available (not loaded)")
                else:
                    raise


def test_invalid_model_name():
    """Test that invalid model names are rejected."""
    print("\n" + "="*80)
    print("Testing Invalid Model Name Handling")
    print("="*80)
    
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = filter_pb2_grpc.FilterServiceStub(channel)
        
        request = filter_pb2.ModelClassifyRequest(
            message="Test message",
            model_name="invalid_model_123"
        )
        
        try:
            response = stub.ClassifyMessageWithModel(request)
            assert False, "Expected INVALID_ARGUMENT error for invalid model name"
        except grpc.RpcError as e:
            assert e.code() == grpc.StatusCode.INVALID_ARGUMENT, \
                f"Expected INVALID_ARGUMENT, got {e.code()}"
            print(f"  ✓ Invalid model name correctly rejected")
            print(f"  ✓ Error: {e.details()}")


def test_empty_message():
    """Test that empty messages are handled gracefully."""
    print("\n" + "="*80)
    print("Testing Empty Message Handling")
    print("="*80)
    
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = filter_pb2_grpc.FilterServiceStub(channel)
        
        # Test with default model
        print("\nTesting empty message with default model...")
        request = filter_pb2.ClassifyRequest(message="")
        response = stub.ClassifyMessage(request)
        validate_response(response, "default")
        print(f"  ✓ Category: {response.category}")
        print(f"  ✓ Severity: {response.severity}")
        
        # Test with specific model
        print("\nTesting empty message with fp32 model...")
        request = filter_pb2.ModelClassifyRequest(
            message="",
            model_name="fp32"
        )
        response = stub.ClassifyMessageWithModel(request)
        validate_response(response, "fp32")
        print(f"  ✓ Category: {response.category}")
        print(f"  ✓ Severity: {response.severity}")


def test_long_message():
    """Test that long messages are handled (chunking)."""
    print("\n" + "="*80)
    print("Testing Long Message Handling")
    print("="*80)
    
    # Create a long message that will require chunking
    long_message = " ".join([
        "I've been feeling really stressed out lately.",
        "Work has been overwhelming and deadlines keep piling up.",
        "I can't seem to catch a break and my sleep is suffering.",
        "Every day feels like a struggle and I'm exhausted all the time.",
        "I don't know how much longer I can keep this pace up.",
    ] * 10)  # Repeat to ensure it exceeds max_length
    
    print(f"\nMessage length: {len(long_message)} chars")
    
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = filter_pb2_grpc.FilterServiceStub(channel)
        
        # Test with default model
        print("\nTesting with default model...")
        request = filter_pb2.ClassifyRequest(message=long_message)
        response = stub.ClassifyMessage(request)
        validate_response(response, "default")
        print(f"  ✓ Category: {response.category} ({response.category_confidence:.3f})")
        print(f"  ✓ Severity: {response.severity} ({response.severity_confidence:.3f})")
        
        # Test with fp32 model
        print("\nTesting with fp32 model...")
        request = filter_pb2.ModelClassifyRequest(
            message=long_message,
            model_name="fp32"
        )
        response = stub.ClassifyMessageWithModel(request)
        validate_response(response, "fp32")
        print(f"  ✓ Category: {response.category} ({response.category_confidence:.3f})")
        print(f"  ✓ Severity: {response.severity} ({response.severity_confidence:.3f})")


if __name__ == '__main__':
    """Run tests manually without pytest."""
    print("\n" + "="*80)
    print("MULTI-MODEL INFERENCE TEST SUITE")
    print("="*80)
    print("\nNote: Server must be running on localhost:50051")
    print("Start server with: python filter/inference/server.py")
    print("")
    
    try:
        # Run tests
        test_classify_message_default()
        
        for model in MODEL_VARIANTS:
            test_classify_message_with_model(model)
        
        test_all_models_respond()
        test_invalid_model_name()
        test_empty_message()
        test_long_message()
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80)
        
    except Exception as e:
        print(f"\n" + "="*80)
        print(f"TEST FAILED: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()
