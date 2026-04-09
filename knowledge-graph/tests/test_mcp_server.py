"""
Tests for the SentinelAI Knowledge Graph MCP Server.
Covers MCP tool functions, crisis detection, dataset loading, and input validation.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from server import (
    get_dataset,
    triage_crisis_risk,
    get_recommendation,
    get_recommendation_by_topic,
    get_recommendation_by_technique,
    list_topics,
    list_techniques,
    get_techniques_for_topic,
    search_papers,
    get_paper_details,
    get_stats,
    detect_concerns,
    MAX_INPUT_LENGTH,
    DISCLAIMER,
)


class TestDatasetLoading:
    def test_dataset_loads_successfully(self):
        ds = get_dataset()
        assert ds is not None
        assert "papers" in ds
        assert "advice" in ds
        assert "topics" in ds
        assert "techniques" in ds

    def test_dataset_has_expected_counts(self):
        ds = get_dataset()
        assert len(ds["papers"]) == 92
        assert len(ds["advice"]) == 368
        assert len(ds["topics"]) == 24
        assert len(ds["techniques"]) == 37

    def test_lazy_load_returns_same_instance(self):
        ds1 = get_dataset()
        ds2 = get_dataset()
        assert ds1 is ds2


class TestCrisisTriage:
    def test_detects_suicide(self):
        result = triage_crisis_risk("I am thinking about suicide")
        assert result["crisis_detected"] is True
        assert result["severity"] == "HIGH"

    def test_detects_self_harm(self):
        result = triage_crisis_risk("I want to hurt myself")
        assert result["crisis_detected"] is True

    def test_detects_end_my_life(self):
        result = triage_crisis_risk("I want to end my life")
        assert result["crisis_detected"] is True

    def test_no_crisis_for_normal_input(self):
        result = triage_crisis_risk("I'm feeling stressed about deadlines")
        assert result["crisis_detected"] is False

    def test_returns_crisis_resources(self):
        result = triage_crisis_risk("I want to kill myself")
        assert "crisis_resources" in result
        assert any("Samaritans" in r["name"] for r in result["crisis_resources"])

    def test_input_length_bounded(self):
        long_input = "suicide " * 10000
        result = triage_crisis_risk(long_input)
        assert result["crisis_detected"] is True

    def test_empty_input(self):
        result = triage_crisis_risk("")
        assert result["crisis_detected"] is False


class TestGetRecommendation:
    def test_returns_results_for_burnout(self):
        result = get_recommendation("I'm burned out and exhausted")
        assert result["returned"] > 0
        assert "recommendations" in result
        assert result["disclaimer"] == DISCLAIMER

    def test_auto_detects_concerns(self):
        result = get_recommendation("anxiety and insomnia keeping me up at night")
        assert len(result["detected_concerns"]) > 0
        assert "anxiety" in result["detected_concerns"]

    def test_returns_empty_for_unrelated(self):
        result = get_recommendation("the weather is nice today")
        assert result["returned"] == 0
        assert "hint" in result

    def test_crisis_input_returns_crisis_response(self):
        result = get_recommendation("I want to end it all")
        assert result.get("crisis_detected") is True

    def test_max_results_capped(self):
        result = get_recommendation("stress anxiety depression burnout", max_results=3)
        assert result["returned"] <= 3

    def test_max_results_cannot_exceed_ceiling(self):
        result = get_recommendation("stress", max_results=500)
        assert result["returned"] <= 20


class TestGetRecommendationByTopic:
    def test_valid_topic(self):
        result = get_recommendation_by_topic("burnout")
        assert result["returned"] > 0

    def test_invalid_topic(self):
        result = get_recommendation_by_topic("nonexistent_topic")
        assert "error" in result


class TestGetRecommendationByTechnique:
    def test_valid_technique(self):
        techniques = list_techniques()
        first_id = techniques["techniques"][0]["id"]
        result = get_recommendation_by_technique(first_id)
        assert "recommendations" in result

    def test_invalid_technique(self):
        result = get_recommendation_by_technique("fake_technique")
        assert "error" in result


class TestListEndpoints:
    def test_list_topics_count(self):
        result = list_topics()
        assert result["count"] == 24

    def test_list_techniques_count(self):
        result = list_techniques()
        assert result["count"] == 37

    def test_techniques_for_topic(self):
        result = get_techniques_for_topic("burnout")
        assert result["count"] > 0

    def test_techniques_for_invalid_topic(self):
        result = get_techniques_for_topic("nonexistent")
        assert "error" in result


class TestSearchPapers:
    def test_search_by_keyword(self):
        result = search_papers(query="mindfulness")
        assert result["total_matching"] > 0

    def test_search_by_topic(self):
        result = search_papers(topic_id="burnout")
        assert result["total_matching"] > 0

    def test_search_requires_at_least_one_param(self):
        result = search_papers()
        assert "error" in result

    def test_search_respects_limit(self):
        result = search_papers(query="stress", max_results=2)
        assert result["returned"] <= 2


class TestGetPaperDetails:
    def test_valid_paper(self):
        result = get_paper_details("paper_001")
        assert "title" in result
        assert "advice" in result

    def test_invalid_paper(self):
        result = get_paper_details("nonexistent_paper")
        assert "error" in result


class TestGetStats:
    def test_returns_stats(self):
        result = get_stats()
        assert result["papers"] == 92
        assert result["advice_items"] == 368
        assert result["topics"] == 24
        assert result["techniques"] == 37
        assert "top_cited_papers" in result


class TestDetectConcerns:
    def test_detects_stress(self):
        concerns = detect_concerns("I'm very stressed at work")
        assert "workplace_stress" in concerns

    def test_detects_multiple(self):
        concerns = detect_concerns("anxiety and burnout from overtime")
        assert "anxiety" in concerns
        assert "burnout" in concerns

    def test_empty_input(self):
        concerns = detect_concerns("")
        assert concerns == []

    def test_word_boundary_prevents_false_positive(self):
        concerns = detect_concerns("I'm feeling happy and content")
        assert "anxiety" not in concerns
