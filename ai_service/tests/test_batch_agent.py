"""
Tests for POST /analyze/batch endpoint.
Follows patterns from test_agent.py.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from agent import app
from schema.output import AgentOutput, MentalHealthScore, BatchAgentOutput
from schema.request import BatchAnalyzeRequest

client = TestClient(app)


def _zero_score():
    return dict(stress_level=0, suicide_risk=0, burnout_score=0,
                depression_indicators=0, anxiety_markers=0, isolation_tendency=0)


def _risk_result(stress=75, burnout=80):
    return {
        "is_confirmed_risk": True,
        "hr_report": {
            "scores": dict(stress_level=stress, suicide_risk=20, burnout_score=burnout,
                           depression_indicators=45, anxiety_markers=60, isolation_tendency=35),
            "response": "High stress detected. Recommend immediate support.",
            "recommendations": ["EAP referral", "Manager check-in"],
        },
    }


def _no_risk_result():
    return {"is_confirmed_risk": False}


class TestAnalyzeBatchEndpoint:

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("agent.agent.ainvoke", new_callable=AsyncMock)
    def test_returns_correct_structure(self, mock_ainvoke):
        mock_ainvoke.return_value = _no_risk_result()
        resp = client.post("/analyze/batch", json={"messages": ["a", "b", "c"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["results"]) == 3
        assert "processed" in data

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("agent.agent.ainvoke", new_callable=AsyncMock)
    def test_single_message(self, mock_ainvoke):
        mock_ainvoke.return_value = _risk_result()
        resp = client.post("/analyze/batch", json={"messages": ["burned out"]})
        assert resp.status_code == 200
        assert resp.json()["results"][0]["score"]["stress_level"] == 75

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("agent.agent.ainvoke", new_callable=AsyncMock)
    def test_mixed_risk_and_safe(self, mock_ainvoke):
        mock_ainvoke.side_effect = [_no_risk_result(), _risk_result(90, 85), _no_risk_result()]
        resp = client.post("/analyze/batch", json={
            "messages": ["Great day!", "I'm completely burned out", "Lunch?"]
        })
        data = resp.json()
        assert data["results"][0]["response"] == "No significant mental health risk detected."
        assert data["results"][1]["score"]["stress_level"] == 90
        assert data["results"][2]["response"] == "No significant mental health risk detected."

    def test_empty_list_rejected(self):
        resp = client.post("/analyze/batch", json={"messages": []})
        assert resp.status_code == 422

    def test_exceeds_max_50(self):
        resp = client.post("/analyze/batch", json={"messages": [f"m{i}" for i in range(51)]})
        assert resp.status_code == 422

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("agent.agent.ainvoke", new_callable=AsyncMock)
    def test_exactly_50(self, mock_ainvoke):
        mock_ainvoke.return_value = _no_risk_result()
        resp = client.post("/analyze/batch", json={"messages": [f"m{i}" for i in range(50)]})
        assert resp.status_code == 200
        assert resp.json()["total"] == 50

    def test_missing_messages_field(self):
        resp = client.post("/analyze/batch", json={})
        assert resp.status_code == 422

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key(self):
        resp = client.post("/analyze/batch", json={"messages": ["test"]})
        assert resp.status_code == 500
        assert "OPENAI_API_KEY" in resp.json()["detail"]


class TestBatchPartialFailure:

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("agent._analyze_single", new_callable=AsyncMock)
    def test_one_failure_doesnt_crash_batch(self, mock_analyze):
        good = AgentOutput(score=MentalHealthScore(**_zero_score()),
                           response="No significant mental health risk detected.")
        mock_analyze.side_effect = [good, Exception("LangGraph timeout"), good]

        resp = client.post("/analyze/batch", json={"messages": ["ok1", "fail", "ok2"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["results"]) == 3
        failed = data["results"][1]
        assert failed["score"]["stress_level"] == 0
        assert "failed" in failed["response"].lower() or "error" in failed["response"].lower()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("agent._analyze_single", new_callable=AsyncMock)
    def test_all_failures_still_200(self, mock_analyze):
        mock_analyze.side_effect = Exception("MCP down")
        resp = client.post("/analyze/batch", json={"messages": ["f1", "f2"]})
        assert resp.status_code == 200
        data = resp.json()
        for r in data["results"]:
            assert r["score"]["stress_level"] == 0


class TestProcessedCount:

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("agent._analyze_single", new_callable=AsyncMock)
    def test_processed_counts_successes_only(self, mock_analyze):
        good = AgentOutput(score=MentalHealthScore(**_zero_score()),
                           response="No significant mental health risk detected.")
        mock_analyze.side_effect = [good, Exception("timeout"), good]

        resp = client.post("/analyze/batch", json={"messages": ["ok", "fail", "ok"]})
        data = resp.json()
        assert data["total"] == 3
        assert data["processed"] == 2  # only successful ones


class TestBatchOrderPreservation:

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("agent.agent.ainvoke", new_callable=AsyncMock)
    def test_results_in_input_order(self, mock_ainvoke):
        mock_ainvoke.side_effect = [
            _risk_result(10, 10), _risk_result(90, 90), _no_risk_result()
        ]
        resp = client.post("/analyze/batch", json={
            "messages": ["low", "high", "none"]
        })
        data = resp.json()
        assert data["results"][0]["score"]["stress_level"] == 10
        assert data["results"][1]["score"]["stress_level"] == 90
        assert data["results"][2]["response"] == "No significant mental health risk detected."


class TestBatchSchemaValidation:

    def test_request_min_length(self):
        with pytest.raises(Exception):
            BatchAnalyzeRequest(messages=[])

    def test_request_max_length(self):
        with pytest.raises(Exception):
            BatchAnalyzeRequest(messages=[f"m{i}" for i in range(51)])

    def test_request_valid(self):
        req = BatchAnalyzeRequest(messages=["a", "b", "c"])
        assert len(req.messages) == 3

    def test_output_schema(self):
        out = BatchAgentOutput(
            results=[AgentOutput(score=MentalHealthScore(**_zero_score()), response="OK")],
            total=1, processed=1,
        )
        assert out.total == 1
