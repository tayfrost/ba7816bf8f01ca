# SentinelAI Filter Inference Service

## Overview

gRPC-based inference service for the SentiBERT dual-head classifier. Provides fast, typed RPC endpoints for mental health risk classification from workplace messages.

## Optimizations

- **PyTorch-first Runtime**: Default backend is PyTorch for stable production behavior
- **Optional ONNX Runtime**: ONNX backend is available via `INFERENCE_BACKEND=onnx`
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

See `tests/test_onnx_workflow.py` for ONNX inference example:

```python
from services.model_factory import load_onnx_model_and_tokenizer

session, tokenizer = load_onnx_model_and_tokenizer(onnx_variant="dynamic_int8")
encoding = tokenizer.encode(text)
input_ids = np.array([encoding.ids], dtype=np.int64)
attention_mask = np.array([encoding.attention_mask], dtype=np.int64)
category_logits, severity_logits = session.run(
    ["category_logits", "severity_logits"],
    {"input_ids": input_ids, "attention_mask": attention_mask},
)
```

## Why gRPC?

- **Performance**: Binary protocol with HTTP/2, lower latency than REST
- **Type Safety**: Protocol Buffers provide strict schemas and code generation
- **Microservice Communication**: Industry standard for service-to-service calls
- **Streaming**: Supports batch inference and bidirectional streaming if needed
- **Language Agnostic**: Can be consumed by backend (Node.js/Go) easily

## Architecture

```text
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
- **Default Backend**: `pytorch`
- **Optional Backends**: `onnx` with variants `fp32`, `fp16`, `dynamic_int8`

## Monitoring

The filter service exposes a Prometheus metrics endpoint on **port 9091** (HTTP), separate from the gRPC port 50051. Prometheus scrapes `filter:9091/metrics` automatically.

| Metric | Type | Description |
|---|---|---|
| `grpc_requests_total` | Counter | Total RPC calls, labelled `method` + `outcome` (success/error) |
| `grpc_request_duration_seconds` | Histogram | Per-method call latency (p50/p95/p99 via `histogram_quantile`) |
| `grpc_batch_size` | Histogram | Distribution of batch sizes for `ClassifyMessages` calls |

The HTTP server starts in a background daemon thread alongside the gRPC server. Override the port via the `PROMETHEUS_PORT` environment variable (default `9091`).

## Dependencies

- `grpcio` / `grpcio-tools` - gRPC runtime and code generation
- `torch` / `transformers` / `peft` - Default PyTorch inference path
- `onnxruntime` - Optional ONNX inference backend
- `protobuf` - Protocol Buffers
- `prometheus-client` - Metrics HTTP server

## Status

✅ **Operational** - PyTorch-first inference server with optional ONNX backend and Prometheus metrics.
