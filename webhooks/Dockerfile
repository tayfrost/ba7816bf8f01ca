FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY webhooks/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy protos
COPY protos/filter ./protos/filter

# Generate gRPC files
RUN python -m grpc_tools.protoc \
    -I./protos \
    --python_out=. \
    --grpc_python_out=. \
    ./protos/filter/v1/filter.proto && \
    touch filter/__init__.py && \
    touch filter/v1/__init__.py

# Copy application
COPY webhooks/ .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
