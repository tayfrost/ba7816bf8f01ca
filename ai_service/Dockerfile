FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Upgrade pip first (important for retry features)
RUN pip install --upgrade pip

# Install dependencies with higher timeout and retries
RUN for i in 1 2 3 4 5; do \
        pip install \
        --no-cache-dir \
        --default-timeout=200 \
        --retries=20 \
        --prefer-binary \
        -r requirements.txt && break || \
        sleep 10; \
    done

COPY .env .
COPY agent.py .
COPY prompts/ ./prompts/
COPY schema/ ./schema/
COPY services/ ./services/
COPY states/ ./states/

EXPOSE 8001

CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8001"]