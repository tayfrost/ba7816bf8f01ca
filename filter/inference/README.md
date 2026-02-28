# SentinelAI Filter Inference Service

## Overview

gRPC-based inference service for the SentiBERT dual-head classifier. Provides fast, typed RPC endpoints for mental health risk classification from workplace messages.

## Optimizations

- **ONNX Runtime**: Converted model to ONNX format, removed torch/transformers from production build
- **Sliding Window**: Overlap-based chunking with OR/MAX aggregation for long messages
- **Risk Gating**: Returns highest risk score across all chunks

## Client Stub Generation

Generate client stubs from `.proto` files:

```bash
# Python
python -m grpc_tools.protoc -I../../protos --python_out=../generated --grpc_python_out=../generated ../../protos/filter/v1/filter.proto

# Node.js
grpc_tools_node_protoc --js_out=import_style=commonjs,binary:. --grpc_out=grpc_js:. --proto_path=../../protos ../../protos/filter/v1/filter.proto
```

## Usage Example

See `tests/test_onnx_workflow.py` for complete inference example:

```python
from services.model_factory import load_onnx_model_and_tokenizer

session, tokenizer = load_onnx_model_and_tokenizer()
inputs = tokenizer(text, max_length=128, padding="max_length", truncation=True, return_tensors="np")
category_logits, severity_logits = session.run(None, {"input_ids": inputs["input_ids"], "attention_mask": inputs["attention_mask"]})
```

## Why gRPC?

- **Performance**: Binary protocol with HTTP/2, lower latency than REST
- **Type Safety**: Protocol Buffers provide strict schemas and code generation
- **Microservice Communication**: Industry standard for service-to-service calls
- **Streaming**: Supports batch inference and bidirectional streaming if needed
- **Language Agnostic**: Can be consumed by backend (Node.js/Go) easily

## Architecture

```
┌─────────────────┐
│   Backend API   │
│  (Node.js/Go)   │
└────────┬────────┘
         │ gRPC
         ▼
┌─────────────────┐
│ Filter Service  │
│   (Python)      │
│                 │
│  - gRPC Server  │
│  - Model Cache  │
│  - SentiBERT    │
└─────────────────┘
```

## Service Contract

**Input**: Raw message text  
**Output**: 
- Category prediction (7 classes)
- Severity stage (4 levels)
- Risk flag (binary gate)
- Confidence scores

## Integration Points

- **Webhooks Service**: Receives Slack messages, calls filter for risk assessment
- **AI Service**: Filter acts as first-stage gatekeeper before LLM escalation
- **Backend**: May query filter directly for user analytics/dashboard

## Model Details

- **Base Model**: bert-base-uncased with LoRA adapters
- **Repo**: `OguzhanKOG/sentinelai-bert-filter`
- **Performance**: 97% recall, 95% precision (binary risk detection)
- **Latency Target**: <100ms p99 for single prediction

## Dependencies

- `grpcio` / `grpcio-tools` - gRPC runtime and code generation
- `onnxruntime` - ONNX model inference (replaces torch in production)
- `transformers` - Tokenizer only
- `protobuf` - Protocol Buffers

## Status

✅ **Operational** - ONNX-based inference server with sliding window aggregation.
