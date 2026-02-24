FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY filter/requirements-dev.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 300 -r requirements-dev.txt

# Copy proto files and compile them
COPY protos/ ./protos/
RUN mkdir -p generated && \
    python -m grpc_tools.protoc \
    -I./protos \
    --python_out=./generated \
    --pyi_out=./generated \
    --grpc_python_out=./generated \
    ./protos/filter/v1/filter.proto && \
    touch generated/filter/__init__.py && \
    touch generated/filter/v1/__init__.py

# Copy ONNX model (structure + external weights)
COPY filter/models/sentibert_model.onnx ./models/
COPY filter/models/sentibert_model.onnx.data ./models/

# Copy application code
COPY filter/inference/ ./inference/
COPY filter/config.py .
COPY filter/main.py .

# Expose gRPC port
EXPOSE 50051

# Expose metrics port
EXPOSE 8000

# Run the server
CMD ["python", "main.py"]
