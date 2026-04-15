FROM python:3.11-slim

WORKDIR /app

COPY ai_service/requirements.txt .

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

COPY ai_service/.env .
COPY ai_service/agent.py .
COPY ai_service/prompts/ ./prompts/
COPY ai_service/schema/ ./schema/
COPY ai_service/services/ ./services/
COPY ai_service/states/ ./states/
COPY ai_service/utils/ ./utils/
COPY ai_service/llm.py .

EXPOSE 8001

CMD ["python", "-m","uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8001"]
