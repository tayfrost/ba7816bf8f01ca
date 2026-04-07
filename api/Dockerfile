FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY api/ /app/api/
COPY database/ /app/database/

EXPOSE 8000

CMD ["sh", "-c", "python database/database/tables.py && uvicorn api.main:app --host 0.0.0.0 --port 8000"]
