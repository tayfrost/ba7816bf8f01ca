FROM python:3.12-slim

WORKDIR /app

COPY knowledge-graph/mcp-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY knowledge-graph/mcp-server/server.py .
COPY knowledge-graph/data/papers.json ./data/papers.json

ENV KG_DATA_PATH=/app/data/papers.json
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8001

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/sse')" || exit 1

CMD ["python", "server.py"]
