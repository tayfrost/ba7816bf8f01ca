# SentinelAI Filter Inference Service

## Overview

gRPC-based inference service for the SentiBERT dual-head classifier. Provides fast, typed RPC endpoints for mental health risk classification from workplace messages.

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
- `torch` + `transformers` + `peft` - Model inference
- `protobuf` - Protocol Buffers

## Status

🚧 **In Development** - Service scaffolding and implementation in progress.
