FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py .
COPY prompts/ ./prompts/
COPY schema/ ./schema/
COPY services/ ./services/

EXPOSE 8001

CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8001"]
