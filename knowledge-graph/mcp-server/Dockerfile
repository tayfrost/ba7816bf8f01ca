FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/data/.cache
WORKDIR /app
RUN useradd -m -u 1000 sentineluser
COPY knowledge-graph/mcp-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/data && chown -R sentineluser:sentineluser /app/data
COPY --chown=sentineluser:sentineluser knowledge-graph/data/papers.json /app/data/papers.json
COPY --chown=sentineluser:sentineluser knowledge-graph/mcp-server/server.py .
COPY --chown=sentineluser:sentineluser knowledge-graph/mcp-server/sentinelai_kg ./sentinelai_kg
ENV KG_DATA_PATH=/app/data/papers.json \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8001
USER sentineluser
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8001))" || exit 1
CMD ["python", "server.py"]