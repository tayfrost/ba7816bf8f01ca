FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy proto files and compile them
COPY ../protos/ ./protos/
RUN mkdir -p generated && \
    python -m grpc_tools.protoc \
    -I./protos \
    --python_out=./generated \
    --grpc_python_out=./generated \
    ./protos/filter/v1/filter.proto

# Copy application code
COPY models/ ./models/
COPY services/ ./services/
COPY inference/ ./inference/
COPY config.py .

# Expose gRPC port
EXPOSE 50051

# Expose metrics port
EXPOSE 8000

# Run the server
CMD ["python", "main.py"]
