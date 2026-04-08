"""Tests for mental health assessment agent."""

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
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
        assert "openai_api_configured" in data
    
    @patch.dict(os.environ, {}, clear=True)
    def test_analyze_missing_api_key(self):
        """Test analyze endpoint fails without API key."""
        response = client.post("/analyze", json={"message": "test"})
        assert response.status_code == 500
        assert "OPENAI_API_KEY" in response.json()["detail"]
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("agent.agent.ainvoke", new_callable=AsyncMock)
    def test_analyze_no_risk_message(self, mock_agent_ainvoke):
        """Test analyze with non-risk message."""
        mock_agent_ainvoke.return_value = {"is_confirmed_risk": False}
        
        response = client.post("/analyze", json={"message": "Great day at work!"})
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "response" in data
        assert data["response"] == "No significant mental health risk detected."
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("agent.agent.ainvoke", new_callable=AsyncMock)
    def test_analyze_risk_message(self, mock_agent_ainvoke):
        """Test analyze with risk message."""
        mock_agent_ainvoke.return_value = {
            "is_confirmed_risk": True,
            "hr_report": {
                "scores": {
                    "neutral_score": 5,
                    "humor_sarcasm_score": 0,
                    "stress_score": 75,
                    "burnout_score": 80,
                    "depression_score": 45,
                    "harassment_score": 20,
                    "suicidal_ideation_score": 20,
                },
                "response": "High stress detected. Recommend immediate support.",
                "recommendations": ["EAP referral", "Manager check-in"],
            },
        }

        response = client.post("/analyze", json={"message": "I'm completely burned out"})
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert data["score"]["stress_score"] == 75
        assert data["score"]["burnout_score"] == 80
        assert "High stress detected" in data["response"]


class TestWorkflowNodes:
    """Test LangGraph workflow nodes."""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("states.assess_risk_state.ChatOpenAI")
    async def test_assess_risk_node_positive(self, mock_chat_openai):
        """Test assess_risk node with risk detected."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"is_risk": true, "reasoning": "Burnout indicators"}'
        mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_openai.return_value = mock_llm_instance
        
        state = AgentState(raw_message="I can't take it anymore")
        result = await assess_risk(state)
        
        assert result['is_confirmed_risk'] is True
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("states.assess_risk_state.ChatOpenAI")
    async def test_assess_risk_node_negative(self, mock_chat_openai):
        """Test assess_risk node with no risk."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"is_risk": false, "reasoning": "Positive message"}'
        mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_openai.return_value = mock_llm_instance
        
        state = AgentState(raw_message="Having a great day!")
        result = await assess_risk(state)
        
        assert result['is_confirmed_risk'] is False
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("states.grade_message_state.ChatOpenAI")
    async def test_grade_message_node(self, mock_chat_openai):
        """Test grade_message node."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"neutral_score": 10, "humor_sarcasm_score": 0, "stress_score": 65, "burnout_score": 70, "depression_score": 40, "harassment_score": 20, "suicidal_ideation_score": 15}'
        mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_openai.return_value = mock_llm_instance

        state = AgentState(raw_message="Feeling stressed", is_confirmed_risk=True)
        result = await grade_message(state)

        assert result['hr_report'] is not None
        assert result['hr_report']['scores']['stress_score'] == 65
        assert result['hr_report']['scores']['burnout_score'] == 70
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("states.generate_recommendations_state.load_mcp_tools", new_callable=AsyncMock)
    @patch("states.generate_recommendations_state.ChatOpenAI")
    async def test_generate_recommendations_node(self, mock_chat_openai, mock_load_mcp_tools):
        """Test generate_recommendations node."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"recommendations": ["Contact EAP", "Schedule 1-on-1"], "response": "Moderate stress. Recommend intervention."}'
        mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_instance.bind_tools.return_value = mock_llm_instance
        mock_chat_openai.return_value = mock_llm_instance
        mock_load_mcp_tools.return_value = []
        
        state = AgentState(
            raw_message="Overwhelmed with work",
            is_confirmed_risk=True,
            hr_report={"scores": {"stress_score": 60}},
            mcp_client=MagicMock(),
        )
        result = await generate_recommendations(state)
        
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
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("agent.agent.ainvoke", new_callable=AsyncMock)
    def test_output_schema_validation(self, mock_agent_ainvoke):
        """Test AgentOutput schema validation."""
        mock_agent_ainvoke.return_value = {"is_confirmed_risk": False}
        
        response = client.post("/analyze", json={"message": "test"})
        assert response.status_code == 200
        data = response.json()
        
        # Validate against AgentOutput schema
        output = AgentOutput(**data)
        assert output.score is not None
        assert output.response is not None


class TestLLMConnectivity:
    """Test LLM connectivity."""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("states.assess_risk_state.ChatOpenAI")
    async def test_llm_initialization(self, mock_chat_openai):
        """Test OpenAI LLM client is initialized with expected config."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"is_risk": false, "reasoning": "test"}'
        mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_openai.return_value = mock_llm_instance

        state = AgentState(raw_message="test message")
        await assess_risk(state)

        assert mock_chat_openai.called
        kwargs = mock_chat_openai.call_args.kwargs
        assert kwargs["model"] == os.getenv("MODEL", "gpt-5-nano")
        assert kwargs["api_key"] == "test_key"
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("states.assess_risk_state.ChatOpenAI")
    async def test_llm_invocation_structure(self, mock_openai_class):
        """Test LLM invocation with correct message structure."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"is_risk": false, "reasoning": "test"}'
        mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_llm_instance

        state = AgentState(raw_message="test message")
        await assess_risk(state)
        
        assert mock_llm_instance.ainvoke.called
