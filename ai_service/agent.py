"""Mental health risk assessment agent with LangGraph workflow."""

import os
import asyncio
import logging
import re
import time
from typing import Literal, List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from fastmcp import Client
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from services.prompt_service import PromptService
from services.mcp_service import get_mcp_client
from schema.agent_state import AgentState
from schema.output import AgentOutput, MentalHealthScore, BatchAgentOutput
from schema.request import AnalyzeRequest, BatchAnalyzeRequest

load_dotenv()

# --- prometheus metrics ---

_SERVICE = "ai_service"
_ID_RE = re.compile(r"/([0-9]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")

_http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code", "service"],
)
_http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint", "service"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)
_http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Requests currently being processed",
    ["method", "service"],
)
_http_request_size_bytes = Histogram(
    "http_request_size_bytes", "Request body size", ["method", "endpoint", "service"],
)
_http_response_size_bytes = Histogram(
    "http_response_size_bytes", "Response body size", ["method", "endpoint", "service"],
)

# ai_service-specific: track LLM pipeline calls
ai_pipeline_calls_total = Counter(
    "ai_pipeline_calls_total",
    "Total LangGraph agent invocations",
    ["mode", "outcome"],  # mode: single|batch, outcome: success|error
)
ai_pipeline_duration_seconds = Histogram(
    "ai_pipeline_duration_seconds",
    "End-to-end LangGraph agent processing time",
    ["mode"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)


class _PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        method = request.method
        path = _ID_RE.sub("/{id}", request.url.path)
        _http_requests_in_progress.labels(method=method, service=_SERVICE).inc()
        body = await request.body()
        _http_request_size_bytes.labels(method=method, endpoint=path, service=_SERVICE).observe(len(body))
        status_code = 500
        resp_size = 0
        start = time.perf_counter()
        try:
            resp = await call_next(request)
            status_code = resp.status_code
            resp_body = b""
            async for chunk in resp.body_iterator:
                resp_body += chunk if isinstance(chunk, bytes) else chunk.encode()
            resp_size = len(resp_body)
            return Response(
                content=resp_body,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                media_type=resp.media_type,
            )
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start
            _http_requests_total.labels(
                method=method, endpoint=path, status_code=str(status_code), service=_SERVICE,
            ).inc()
            _http_request_duration_seconds.labels(method=method, endpoint=path, service=_SERVICE).observe(duration)
            _http_response_size_bytes.labels(method=method, endpoint=path, service=_SERVICE).observe(resp_size)
            _http_requests_in_progress.labels(method=method, service=_SERVICE).dec()


async def _metrics_endpoint(request: Request):
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


app = FastAPI(title="SentinelAI Mental Health Assessment")
app.add_middleware(_PrometheusMiddleware)
app.add_route("/metrics", _metrics_endpoint, methods=["GET"])

# Initialize services
prompt_service = PromptService()

# Import state functions
from states.redactor_state import redactor
from states.assess_risk_state import assess_risk
from states.grade_message_state import grade_message
from states.generate_recommendations_state import generate_recommendations
from states.store_incident_state import store_incident


def should_continue(state: AgentState) -> Literal["grade", "end"]:
    """Route based on risk assessment."""
    if state.get('is_confirmed_risk'):
        return "grade"
    return "end"


# Build LangGraph workflow
workflow = StateGraph(AgentState)

workflow.add_node("redactor", redactor)
workflow.add_node("assess_risk", assess_risk)
workflow.add_node("grade_message", grade_message)
workflow.add_node("generate_recommendations", generate_recommendations)
workflow.add_node("store_incident", store_incident)

workflow.set_entry_point("redactor")
workflow.add_edge("redactor", "assess_risk")
workflow.add_conditional_edges(
    "assess_risk",
    should_continue,
    {
        "grade": "grade_message",
        "end": END
    }
)
workflow.add_edge("grade_message", "generate_recommendations")
workflow.add_edge("generate_recommendations", "store_incident")
workflow.add_edge("store_incident", END)

agent = workflow.compile()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "SentinelAI"}


@app.post("/analyze", response_model=AgentOutput)
async def analyze_message(request: AnalyzeRequest, mcp_client: Client = Depends(get_mcp_client)):
    """Analyze a single message for mental health risks."""
    logger.info("="*80)
    logger.info(f"[API] New analyze request received")
    logger.info(f"[API] Message length: {len(request.message)} chars")
    logger.info("="*80)

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    try:
        return await _analyze_single(request, mcp_client)
    except Exception as e:
        logger.error(f"[API] Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


async def _analyze_single(request: AnalyzeRequest, mcp_client: Client) -> AgentOutput:
    """Run the agent workflow on a single message. Reused by both endpoints."""
    initial_state: AgentState = {
        "raw_message": request.message,
        "user_id": request.user_id,
        "company_id": request.company_id,
        "source": request.source,
        "sent_at": request.sent_at,
        "conversation_id": request.conversation_id,
        "content_raw": request.content_raw,
        "filter_category": request.filter_category,
        "filter_severity": request.filter_severity,
    }
    _start = time.perf_counter()
    try:
        result = await agent.ainvoke(
            initial_state,
            config={"configurable": {"mcp_client": mcp_client}},
        )
        ai_pipeline_calls_total.labels(mode="single", outcome="success").inc()
    except Exception:
        ai_pipeline_calls_total.labels(mode="single", outcome="error").inc()
        raise
    finally:
        ai_pipeline_duration_seconds.labels(mode="single").observe(time.perf_counter() - _start)

    if not result.get("is_confirmed_risk"):
        return AgentOutput(
            score=MentalHealthScore(
                stress_level=0, suicide_risk=0, burnout_score=0,
                depression_indicators=0, anxiety_markers=0, isolation_tendency=0,
            ),
            response="No significant mental health risk detected.",
        )

    scores_dict = result["hr_report"]["scores"]
    return AgentOutput(
        score=MentalHealthScore(**scores_dict),
        response=result["hr_report"]["response"],
    )


# Semaphore to limit concurrent LangGraph invocations (protects shared MCP client)
_BATCH_SEMAPHORE = asyncio.Semaphore(5)


async def _analyze_single_throttled(message: str, mcp_client: Client) -> AgentOutput:
    """Throttled wrapper around _analyze_single to limit concurrency."""
    async with _BATCH_SEMAPHORE:
        return await _analyze_single(AnalyzeRequest(message=message), mcp_client)


@app.post("/analyze/batch", response_model=BatchAgentOutput)
async def analyze_messages_batch(
    request: BatchAnalyzeRequest,
    mcp_client: Client = Depends(get_mcp_client),
):
    """Analyze multiple messages concurrently (max 5 at a time)."""
    logger.info(f"[BATCH] Received batch request: {len(request.messages)} messages")

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    try:
        tasks = [_analyze_single_throttled(msg, mcp_client) for msg in request.messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outputs: List[AgentOutput] = []
        processed = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[BATCH] Message {i} failed: {result}")
                outputs.append(AgentOutput(
                    score=MentalHealthScore(
                        stress_level=0, suicide_risk=0, burnout_score=0,
                        depression_indicators=0, anxiety_markers=0, isolation_tendency=0,
                    ),
                    response=f"Analysis failed for this message: {str(result)}",
                ))
            else:
                outputs.append(result)
                processed += 1

        logger.info(f"[BATCH] Completed: {processed}/{len(request.messages)} messages successfully processed")
        return BatchAgentOutput(
            results=outputs,
            total=len(request.messages),
            processed=processed,
        )

    except Exception as e:
        logger.error(f"[BATCH] Batch analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Detailed health check with dependencies."""
    return {
        "status": "healthy",
        "openai_api_configured": bool(os.getenv("OPENAI_API_KEY")),
        "prompt_service": "ready",
        "agent": "compiled"
    }
