"""Tests for agent state and output schemas validation."""

import pytest
from pydantic import ValidationError
from schema.agent_state import AgentState
from schema.output import AgentOutput, MentalHealthScore


class TestAgentState:
    """Tests for AgentState schema."""
    
    def test_agent_state_valid_minimal(self):
        """Test AgentState with only required field."""
        state = AgentState(raw_message="Test message")
        assert state.raw_message == "Test message"
        assert state.is_confirmed_risk is None
        assert state.retrieved_resources is None
        assert state.hr_report is None
    
    def test_agent_state_valid_full(self):
        """Test AgentState with all fields populated."""
        state = AgentState(
            raw_message="I feel stressed",
            is_confirmed_risk=True,
            retrieved_resources=[{"type": "EAP", "contact": "1-800-XXX"}],
            hr_report={"risk_level": "high"}
        )
        assert state.raw_message == "I feel stressed"
        assert state.is_confirmed_risk is True
        assert len(state.retrieved_resources) == 1
        assert state.hr_report["risk_level"] == "high"
    
    def test_agent_state_missing_required(self):
        """Test AgentState validation fails without required field."""
        with pytest.raises(ValidationError) as exc_info:
            AgentState()
        assert "raw_message" in str(exc_info.value)
    
    def test_agent_state_structure(self):
        """Test AgentState has correct field types."""
        state = AgentState(raw_message="test")
        schema = state.model_json_schema()
        
        assert "raw_message" in schema["properties"]
        assert "is_confirmed_risk" in schema["properties"]
        assert "retrieved_resources" in schema["properties"]
        assert "hr_report" in schema["properties"]
        assert schema["required"] == ["raw_message"]


class TestMentalHealthScore:
    """Tests for MentalHealthScore schema."""
    
    def test_mental_health_score_valid(self):
        """Test MentalHealthScore with valid values."""
        score = MentalHealthScore(
            stress_level=50,
            suicide_risk=10,
            burnout_score=75,
            depression_indicators=30,
            anxiety_markers=45,
            isolation_tendency=20
        )
        assert score.stress_level == 50
        assert score.suicide_risk == 10
        assert score.burnout_score == 75
    
    def test_mental_health_score_boundary_values(self):
        """Test MentalHealthScore with boundary values."""
        score = MentalHealthScore(
            stress_level=0,
            suicide_risk=100,
            burnout_score=0,
            depression_indicators=100,
            anxiety_markers=50,
            isolation_tendency=0
        )
        assert score.stress_level == 0
        assert score.suicide_risk == 100
    
    def test_mental_health_score_out_of_range(self):
        """Test MentalHealthScore validation fails for out-of-range values."""
        with pytest.raises(ValidationError) as exc_info:
            MentalHealthScore(
                stress_level=150,
                suicide_risk=10,
                burnout_score=75,
                depression_indicators=30,
                anxiety_markers=45,
                isolation_tendency=20
            )
        assert "stress_level" in str(exc_info.value)
    
    def test_mental_health_score_negative_value(self):
        """Test MentalHealthScore validation fails for negative values."""
        with pytest.raises(ValidationError):
            MentalHealthScore(
                stress_level=-10,
                suicide_risk=10,
                burnout_score=75,
                depression_indicators=30,
                anxiety_markers=45,
                isolation_tendency=20
            )
    
    def test_mental_health_score_structure(self):
        """Test MentalHealthScore has all required dimensions."""
        score = MentalHealthScore(
            stress_level=50,
            suicide_risk=10,
            burnout_score=75,
            depression_indicators=30,
            anxiety_markers=45,
            isolation_tendency=20
        )
        schema = score.model_json_schema()
        
        required_dimensions = [
            "stress_level", "suicide_risk", "burnout_score",
            "depression_indicators", "anxiety_markers", "isolation_tendency"
        ]
        
        for dimension in required_dimensions:
            assert dimension in schema["properties"]
            assert dimension in schema["required"]


class TestAgentOutput:
    """Tests for AgentOutput schema."""
    
    def test_agent_output_valid(self):
        """Test AgentOutput with valid data."""
        output = AgentOutput(
            score=MentalHealthScore(
                stress_level=50,
                suicide_risk=10,
                burnout_score=75,
                depression_indicators=30,
                anxiety_markers=45,
                isolation_tendency=20
            ),
            response="Analysis complete. Moderate stress detected."
        )
        assert output.score.stress_level == 50
        assert output.response == "Analysis complete. Moderate stress detected."
    
    def test_agent_output_empty_response(self):
        """Test AgentOutput validation fails for empty response."""
        with pytest.raises(ValidationError) as exc_info:
            AgentOutput(
                score=MentalHealthScore(
                    stress_level=50,
                    suicide_risk=10,
                    burnout_score=75,
                    depression_indicators=30,
                    anxiety_markers=45,
                    isolation_tendency=20
                ),
                response=""
            )
        assert "response" in str(exc_info.value)
    
    def test_agent_output_whitespace_response(self):
        """Test AgentOutput validation fails for whitespace-only response."""
        with pytest.raises(ValidationError):
            AgentOutput(
                score=MentalHealthScore(
                    stress_level=50,
                    suicide_risk=10,
                    burnout_score=75,
                    depression_indicators=30,
                    anxiety_markers=45,
                    isolation_tendency=20
                ),
                response="   "
            )
    
    def test_agent_output_structure(self):
        """Test AgentOutput has correct structure."""
        output = AgentOutput(
            score=MentalHealthScore(
                stress_level=50,
                suicide_risk=10,
                burnout_score=75,
                depression_indicators=30,
                anxiety_markers=45,
                isolation_tendency=20
            ),
            response="Test response"
        )
        schema = output.model_json_schema()
        
        assert "score" in schema["properties"]
        assert "response" in schema["properties"]
        assert set(schema["required"]) == {"score", "response"}
    
    def test_agent_output_json_serialization(self):
        """Test AgentOutput can be serialized to JSON."""
        output = AgentOutput(
            score=MentalHealthScore(
                stress_level=50,
                suicide_risk=10,
                burnout_score=75,
                depression_indicators=30,
                anxiety_markers=45,
                isolation_tendency=20
            ),
            response="Test response"
        )
        json_data = output.model_dump()
        
        assert "score" in json_data
        assert "response" in json_data
        assert json_data["score"]["stress_level"] == 50
        assert json_data["response"] == "Test response"
    
    def test_agent_output_from_dict(self):
        """Test AgentOutput can be created from dictionary."""
        data = {
            "score": {
                "stress_level": 65,
                "suicide_risk": 10,
                "burnout_score": 70,
                "depression_indicators": 45,
                "anxiety_markers": 55,
                "isolation_tendency": 30
            },
            "response": "Assessment completed successfully"
        }
        output = AgentOutput(**data)
        assert output.score.stress_level == 65
        assert output.response == "Assessment completed successfully"
