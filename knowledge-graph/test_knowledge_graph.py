"""
Unit tests for SentinelAI Knowledge Graph
Tests data integrity, agent integration, and query functionality.

Run: python -m pytest test_knowledge_graph.py -v
"""

import json
import os
import pytest

from agent_integration import WellnessAgent, TOPIC_KEYWORDS

PAPERS_PATH = os.path.join(os.path.dirname(__file__), "papers.json")


@pytest.fixture
def dataset():
    with open(PAPERS_PATH, "r") as f:
        return json.load(f)


@pytest.fixture
def agent():
    return WellnessAgent()


# --- Data Integrity Tests ---

class TestDataIntegrity:

    def test_dataset_loads(self, dataset):
        assert dataset is not None
        assert "metadata" in dataset
        assert "papers" in dataset
        assert "topics" in dataset
        assert "techniques" in dataset

    def test_paper_count(self, dataset):
        assert len(dataset["papers"]) == dataset["metadata"]["total_papers"]

    def test_topic_count(self, dataset):
        assert len(dataset["topics"]) == dataset["metadata"]["topics"]

    def test_technique_count(self, dataset):
        assert len(dataset["techniques"]) == dataset["metadata"]["techniques"]

    def test_all_papers_have_required_fields(self, dataset):
        required = ["id", "title", "authors", "year", "source", "topics", "advice"]
        for paper in dataset["papers"]:
            for field in required:
                assert field in paper, f"Paper {paper.get('id', '?')} missing {field}"

    def test_all_advice_has_required_fields(self, dataset):
        for paper in dataset["papers"]:
            for adv in paper["advice"]:
                assert "text" in adv
                assert "technique" in adv
                assert "confidence" in adv
                assert 0 <= adv["confidence"] <= 1

    def test_paper_topics_reference_valid_ids(self, dataset):
        valid_ids = {t["id"] for t in dataset["topics"]}
        for paper in dataset["papers"]:
            for tid in paper["topics"]:
                assert tid in valid_ids, f"Paper {paper['id']} references unknown topic {tid}"

    def test_advice_techniques_reference_valid_ids(self, dataset):
        valid_ids = {t["id"] for t in dataset["techniques"]}
        for paper in dataset["papers"]:
            for adv in paper["advice"]:
                assert adv["technique"] in valid_ids, \
                    f"Paper {paper['id']} advice references unknown technique {adv['technique']}"

    def test_technique_topics_reference_valid_ids(self, dataset):
        valid_ids = {t["id"] for t in dataset["topics"]}
        for tech in dataset["techniques"]:
            for tid in tech["topics"]:
                assert tid in valid_ids, f"Technique {tech['id']} references unknown topic {tid}"

    def test_unique_paper_ids(self, dataset):
        ids = [p["id"] for p in dataset["papers"]]
        assert len(ids) == len(set(ids)), "Duplicate paper IDs found"

    def test_unique_topic_ids(self, dataset):
        ids = [t["id"] for t in dataset["topics"]]
        assert len(ids) == len(set(ids)), "Duplicate topic IDs found"

    def test_unique_technique_ids(self, dataset):
        ids = [t["id"] for t in dataset["techniques"]]
        assert len(ids) == len(set(ids)), "Duplicate technique IDs found"

    def test_papers_have_citations(self, dataset):
        for paper in dataset["papers"]:
            assert paper["citations"] >= 0

    def test_papers_have_authors(self, dataset):
        for paper in dataset["papers"]:
            assert len(paper["authors"]) > 0

    def test_advice_text_not_empty(self, dataset):
        for paper in dataset["papers"]:
            for adv in paper["advice"]:
                assert len(adv["text"].strip()) > 10


# --- Agent Tests ---

class TestWellnessAgent:

    def test_agent_initializes(self, agent):
        assert agent is not None
        assert agent.dataset is not None

    def test_detect_stress(self, agent):
        concerns = agent.detect_concerns("I'm feeling really stressed at work")
        assert "workplace_stress" in concerns

    def test_detect_anxiety(self, agent):
        concerns = agent.detect_concerns("I'm so anxious about the presentation")
        assert "anxiety" in concerns

    def test_detect_anger(self, agent):
        concerns = agent.detect_concerns("I'm angry at my colleague")
        assert "anger_management" in concerns

    def test_detect_sleep(self, agent):
        concerns = agent.detect_concerns("I can't sleep properly")
        assert "sleep_issues" in concerns

    def test_detect_burnout(self, agent):
        concerns = agent.detect_concerns("I feel burned out and exhausted")
        assert "burnout" in concerns

    def test_detect_depression(self, agent):
        concerns = agent.detect_concerns("I feel depressed and hopeless")
        assert "depression" in concerns

    def test_detect_multiple_concerns(self, agent):
        concerns = agent.detect_concerns("I'm stressed and anxious and can't sleep")
        assert len(concerns) >= 2

    def test_default_concern(self, agent):
        concerns = agent.detect_concerns("hello")
        assert concerns == ["workplace_stress"]

    def test_get_advice_returns_results(self, agent):
        result = agent.get_advice("I'm feeling stressed")
        assert "advice" in result
        assert len(result["advice"]) > 0

    def test_advice_has_disclaimer(self, agent):
        result = agent.get_advice("I'm stressed")
        assert "disclaimer" in result
        assert len(result["disclaimer"]) > 0

    def test_advice_has_paper_citations(self, agent):
        result = agent.get_advice("I'm anxious about work")
        for adv in result["advice"]:
            assert "paper" in adv
            assert "arxiv_id" in adv

    def test_advice_limited_by_max_results(self, agent):
        result = agent.get_advice("I'm stressed", max_results=3)
        assert len(result["advice"]) <= 3

    def test_get_topics(self, agent):
        topics = agent.get_topics()
        assert len(topics) > 0
        assert any(t["id"] == "workplace_stress" for t in topics)

    def test_get_techniques_for_topic(self, agent):
        techniques = agent.get_techniques_for_topic("workplace_stress")
        assert len(techniques) > 0

    def test_get_stats(self, agent):
        stats = agent.get_stats()
        assert stats["papers"] > 0
        assert stats["advice"] > 0
        assert stats["topics"] > 0
        assert stats["techniques"] > 0

    def test_format_response(self, agent):
        result = agent.get_advice("stressed", max_results=2)
        formatted = agent.format_response(result)
        assert "Detected concerns" in formatted
        assert "Source:" in formatted
        assert "Confidence:" in formatted


# --- Keyword Coverage Tests ---

class TestKeywordCoverage:

    def test_all_topics_have_keywords(self):
        for topic_id in TOPIC_KEYWORDS:
            assert len(TOPIC_KEYWORDS[topic_id]) > 0

    def test_keywords_are_lowercase(self):
        for topic_id, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                assert kw == kw.lower(), f"Keyword '{kw}' for {topic_id} is not lowercase"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
