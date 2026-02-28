"""Tests for mental health assessment agent."""

import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from agent import app, assess_risk, grade_message, generate_recommendations, should_continue
from schema.agent_state import AgentState
from schema.output import AgentOutput


client = TestClient(app)


class TestEndpoints:
    """Test FastAPI endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint returns healthy status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "SentinelAI" in data["service"]
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "mistral_api_configured" in data
    
    @patch.dict(os.environ, {}, clear=True)
    def test_analyze_missing_api_key(self):
        """Test analyze endpoint fails without API key."""
        response = client.post("/analyze", json={"message": "test"})
        assert response.status_code == 500
        assert "MISTRAL_API_KEY" in response.json()["detail"]
    
    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test_key"})
    @patch("agent.llm")
    def test_analyze_no_risk_message(self, mock_llm):
        """Test analyze with non-risk message."""
        mock_response = MagicMock()
        mock_response.content = '{"is_risk": false, "reasoning": "No indicators"}'
        mock_llm.invoke.return_value = mock_response
        
        response = client.post("/analyze", json={"message": "Great day at work!"})
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "response" in data
        assert data["response"] == "No significant mental health risk detected."
    
    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test_key"})
    @patch("agent.llm")
    def test_analyze_risk_message(self, mock_llm):
        """Test analyze with risk message."""
        # Mock responses for assess_risk, grade_message, generate_recommendations
        mock_responses = [
            MagicMock(content='{"is_risk": true, "reasoning": "Stress indicators"}'),
            MagicMock(content='{"stress_level": 75, "suicide_risk": 20, "burnout_score": 80, "depression_indicators": 45, "anxiety_markers": 60, "isolation_tendency": 35}'),
            MagicMock(content='{"recommendations": ["EAP referral", "Manager check-in"], "response": "High stress detected. Recommend immediate support."}')
        ]
        mock_llm.invoke.side_effect = mock_responses
        
        response = client.post("/analyze", json={"message": "I'm completely burned out"})
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert data["score"]["stress_level"] == 75
        assert data["score"]["burnout_score"] == 80
        assert "High stress detected" in data["response"]


class TestWorkflowNodes:
    """Test LangGraph workflow nodes."""
    
    @patch("agent.llm")
    def test_assess_risk_node_positive(self, mock_llm):
        """Test assess_risk node with risk detected."""
        mock_response = MagicMock()
        mock_response.content = '{"is_risk": true, "reasoning": "Burnout indicators"}'
        mock_llm.invoke.return_value = mock_response
        
        state = AgentState(raw_message="I can't take it anymore")
        result = assess_risk(state)
        
        assert result['is_confirmed_risk'] is True
    
    @patch("agent.llm")
    def test_assess_risk_node_negative(self, mock_llm):
        """Test assess_risk node with no risk."""
        mock_response = MagicMock()
        mock_response.content = '{"is_risk": false, "reasoning": "Positive message"}'
        mock_llm.invoke.return_value = mock_response
        
        state = AgentState(raw_message="Having a great day!")
        result = assess_risk(state)
        
        assert result['is_confirmed_risk'] is False
    
    @patch("agent.llm")
    def test_grade_message_node(self, mock_llm):
        """Test grade_message node."""
        mock_response = MagicMock()
        mock_response.content = '{"stress_level": 65, "suicide_risk": 15, "burnout_score": 70, "depression_indicators": 40, "anxiety_markers": 50, "isolation_tendency": 25}'
        mock_llm.invoke.return_value = mock_response
        
        state = AgentState(raw_message="Feeling stressed", is_confirmed_risk=True)
        result = grade_message(state)
        
        assert result['hr_report'] is not None
        assert result['hr_report']['scores']['stress_level'] == 65
        assert result['hr_report']['scores']['burnout_score'] == 70
    
    @patch("agent.llm")
    def test_generate_recommendations_node(self, mock_llm):
        """Test generate_recommendations node."""
        mock_response = MagicMock()
        mock_response.content = '{"recommendations": ["Contact EAP", "Schedule 1-on-1"], "response": "Moderate stress. Recommend intervention."}'
        mock_llm.invoke.return_value = mock_response
        
        state = AgentState(
            raw_message="Overwhelmed with work",
            is_confirmed_risk=True,
            hr_report={"scores": {"stress_level": 60}}
        )
        result = generate_recommendations(state)
        
        assert "recommendations" in result['hr_report']
        assert len(result['hr_report']['recommendations']) == 2
        assert "response" in result['hr_report']
    
    def test_should_continue_with_risk(self):
        """Test conditional routing with risk."""
        state = AgentState(raw_message="test", is_confirmed_risk=True)
        assert should_continue(state) == "grade"
    
    def test_should_continue_no_risk(self):
        """Test conditional routing without risk."""
        state = AgentState(raw_message="test", is_confirmed_risk=False)
        assert should_continue(state) == "end"


class TestSchemaValidation:
    """Test schema validation in workflow."""
    
    def test_analyze_request_validation(self):
        """Test AnalyzeRequest validates input."""
        response = client.post("/analyze", json={})
        assert response.status_code == 422  # Validation error
    
    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test_key"})
    @patch("agent.llm")
    def test_output_schema_validation(self, mock_llm):
        """Test AgentOutput schema validation."""
        mock_response = MagicMock()
        mock_response.content = '{"is_risk": false, "reasoning": "test"}'
        mock_llm.invoke.return_value = mock_response
        
        response = client.post("/analyze", json={"message": "test"})
        assert response.status_code == 200
        data = response.json()
        
        # Validate against AgentOutput schema
        output = AgentOutput(**data)
        assert output.score is not None
        assert output.response is not None


class TestLLMConnectivity:
    """Test LLM connectivity."""
    
    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test_key"})
    def test_llm_initialization(self):
        """Test LLM is properly initialized."""
        from agent import llm
        assert llm is not None
        assert llm.model == "mistral-large-latest"
    
    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test_key"})
    @patch("agent.ChatMistralAI")
    def test_llm_invocation_structure(self, mock_mistral_class):
        """Test LLM invocation with correct message structure."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"is_risk": false, "reasoning": "test"}'
        mock_llm_instance.invoke.return_value = mock_response
        mock_mistral_class.return_value = mock_llm_instance
        
        # Import after mocking
        import importlib
        import agent as agent_module
        importlib.reload(agent_module)
        
        state = AgentState(raw_message="test message")
        result = agent_module.assess_risk(state)
        
        assert mock_llm_instance.invoke.called
