"""Tests for agent state and output schemas validation."""

import pytest
from pydantic import ValidationError
from schema.agent_state import AgentState
from schema.output import AgentOutput, MentalHealthScore

_VALID_SCORE = dict(
    neutral_score=10,
    humor_sarcasm_score=5,
    stress_score=50,
    burnout_score=75,
    depression_score=30,
    harassment_score=45,
    suicidal_ideation_score=20,
)

_ALL_DIMENSIONS = list(_VALID_SCORE.keys())


class TestAgentState:
    """Tests for AgentState schema."""

    def test_agent_state_valid_minimal(self):
        state = AgentState(raw_message="Test message")
        assert state.raw_message == "Test message"
        assert state.is_confirmed_risk is None
        assert state.retrieved_resources is None
        assert state.hr_report is None

    def test_agent_state_valid_full(self):
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
        with pytest.raises(ValidationError) as exc_info:
            AgentState()
        assert "raw_message" in str(exc_info.value)

    def test_agent_state_structure(self):
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
        score = MentalHealthScore(**_VALID_SCORE)
        assert score.stress_score == 50
        assert score.suicidal_ideation_score == 20
        assert score.burnout_score == 75

    def test_mental_health_score_boundary_values(self):
        score = MentalHealthScore(
            neutral_score=100,
            humor_sarcasm_score=0,
            stress_score=0,
            burnout_score=0,
            depression_score=100,
            harassment_score=50,
            suicidal_ideation_score=0,
        )
        assert score.neutral_score == 100
        assert score.depression_score == 100

    def test_mental_health_score_out_of_range(self):
        with pytest.raises(ValidationError) as exc_info:
            MentalHealthScore(**{**_VALID_SCORE, "stress_score": 150})
        assert "stress_score" in str(exc_info.value)

    def test_mental_health_score_negative_value(self):
        with pytest.raises(ValidationError):
            MentalHealthScore(**{**_VALID_SCORE, "stress_score": -10})

    def test_mental_health_score_structure(self):
        score = MentalHealthScore(**_VALID_SCORE)
        schema = score.model_json_schema()
        for dimension in _ALL_DIMENSIONS:
            assert dimension in schema["properties"]
            assert dimension in schema["required"]


class TestAgentOutput:
    """Tests for AgentOutput schema."""

    def test_agent_output_valid(self):
        output = AgentOutput(
            score=MentalHealthScore(**_VALID_SCORE),
            response="Analysis complete. Moderate stress detected."
        )
        assert output.score.stress_score == 50
        assert output.response == "Analysis complete. Moderate stress detected."

    def test_agent_output_empty_response(self):
        with pytest.raises(ValidationError) as exc_info:
            AgentOutput(score=MentalHealthScore(**_VALID_SCORE), response="")
        assert "response" in str(exc_info.value)

    def test_agent_output_whitespace_response(self):
        with pytest.raises(ValidationError):
            AgentOutput(score=MentalHealthScore(**_VALID_SCORE), response="   ")

    def test_agent_output_structure(self):
        output = AgentOutput(score=MentalHealthScore(**_VALID_SCORE), response="Test response")
        schema = output.model_json_schema()
        assert "score" in schema["properties"]
        assert "response" in schema["properties"]
        assert set(schema["required"]) == {"score", "response"}

    def test_agent_output_json_serialization(self):
        output = AgentOutput(score=MentalHealthScore(**_VALID_SCORE), response="Test response")
        json_data = output.model_dump()
        assert "score" in json_data
        assert json_data["score"]["stress_score"] == 50
        assert json_data["response"] == "Test response"

    def test_agent_output_from_dict(self):
        data = {
            "score": {
                "neutral_score": 5,
                "humor_sarcasm_score": 10,
                "stress_score": 65,
                "burnout_score": 70,
                "depression_score": 45,
                "harassment_score": 20,
                "suicidal_ideation_score": 10,
            },
            "response": "Assessment completed successfully"
        }
        output = AgentOutput(**data)
        assert output.score.stress_score == 65
        assert output.response == "Assessment completed successfully"
