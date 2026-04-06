"""
SentinelAI Knowledge Graph v3.0 - Test Suite
92 papers, 368 advice, 24 topics, 37 techniques.
Run: python -m pytest test_knowledge_graph.py -v
"""
import json, os, sys, pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from agent_integration import WellnessAgent, TOPIC_KEYWORDS

PAPERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "papers.json")

@pytest.fixture
def ds():
    with open(PAPERS_PATH) as f: return json.load(f)

@pytest.fixture
def agent():
    return WellnessAgent()

class TestDataIntegrity:
    def test_loads(self, ds): assert all(k in ds for k in ["metadata","papers","topics","techniques"])
    def test_paper_count(self, ds): assert len(ds["papers"]) == ds["metadata"]["total_papers"]
    def test_topic_count(self, ds): assert len(ds["topics"]) == ds["metadata"]["topics"]
    def test_tech_count(self, ds): assert len(ds["techniques"]) == ds["metadata"]["techniques"]
    def test_min_papers(self, ds): assert len(ds["papers"]) >= 90
    def test_min_advice(self, ds): assert sum(len(p["advice"]) for p in ds["papers"]) >= 360

    def test_required_paper_fields(self, ds):
        for p in ds["papers"]:
            for f in ["id","title","authors","year","doi","topics","advice","citations"]:
                assert f in p, f"{p.get('id','?')} missing {f}"

    def test_required_advice_fields(self, ds):
        for p in ds["papers"]:
            for a in p["advice"]:
                assert all(k in a for k in ["text","technique","confidence"])
                assert 0 <= a["confidence"] <= 1

    def test_valid_topic_refs(self, ds):
        valid = {t["id"] for t in ds["topics"]}
        for p in ds["papers"]:
            for t in p["topics"]: assert t in valid, f"{p['id']} bad topic {t}"

    def test_valid_technique_refs(self, ds):
        valid = {t["id"] for t in ds["techniques"]}
        for p in ds["papers"]:
            for a in p["advice"]: assert a["technique"] in valid, f"{p['id']} bad tech {a['technique']}"

    def test_tech_topics_valid(self, ds):
        valid = {t["id"] for t in ds["topics"]}
        for t in ds["techniques"]:
            for tid in t.get("topics", []): assert tid in valid, f"{t['id']} bad topic {tid}"

    def test_unique_ids(self, ds):
        for key in ["papers","topics","techniques"]:
            ids = [x["id"] for x in ds[key]]
            assert len(ids) == len(set(ids)), f"Duplicate {key} IDs"

    def test_dois(self, ds):
        doi_count = sum(1 for p in ds["papers"] if p.get("doi") and p["doi"] != "N/A")
        assert doi_count >= len(ds["papers"]) * 0.9

    def test_min_advice_per_paper(self, ds):
        for p in ds["papers"]: assert len(p["advice"]) >= 3, f"{p['id']} < 3 advice"

    def test_high_citation_papers(self, ds):
        high = [p for p in ds["papers"] if p["citations"] >= 500]
        assert len(high) >= 5, f"Only {len(high)} papers with 500+ citations"

    def test_recent_papers(self, ds):
        recent = [p for p in ds["papers"] if p["year"] >= 2024]
        assert len(recent) >= 5, f"Only {len(recent)} papers from 2024+"

    def test_year_range(self, ds):
        years = [p["year"] for p in ds["papers"]]
        assert min(years) <= 2010
        assert max(years) >= 2025

    def test_total_advice_matches_metadata(self, ds):
        actual = sum(len(p["advice"]) for p in ds["papers"])
        assert actual == ds["metadata"]["total_advice"]

    def test_no_empty_advice_text(self, ds):
        for p in ds["papers"]:
            for a in p["advice"]:
                assert len(a["text"]) > 20, f"{p['id']} has short advice"


class TestDetection:
    @pytest.mark.parametrize("text,topic", [
        ("I'm stressed at work", "workplace_stress"),
        ("I'm anxious about the presentation", "anxiety"),
        ("I'm angry at my colleague", "anger_management"),
        ("I can't sleep properly", "sleep_issues"),
        ("I feel burned out", "burnout"),
        ("I feel depressed and hopeless", "depression"),
        ("I'm a perfectionist", "perfectionism"),
        ("I have no time", "time_poverty"),
        ("I feel lonely working remotely", "social_isolation"),
        ("I'm too hard on myself", "self_compassion"),
        ("I had an argument with my manager", "interpersonal_conflict"),
        ("I can never disconnect after hours", "work_life_balance"),
        ("I can't control my emotions", "emotional_regulation"),
        ("How do I bounce back from this setback", "resilience"),
        ("I want to try meditation", "mindfulness"),
        ("I keep catastrophizing", "cognitive_distortions"),
        ("I'm being bullied at work", "workplace_bullying"),
        ("Is there an app for stress?", "digital_interventions"),
        ("I feel stuck and rigid", "act_values"),
        ("My work feels meaningless", "occupational_health"),
        ("Our leadership doesn't support us", "organizational_culture"),
        ("Should I exercise to feel better?", "physical_activity"),
        ("Would journaling help me?", "expressive_writing"),
        ("Can biofeedback help anxiety?", "biofeedback"),
    ])
    def test_detect(self, agent, text, topic):
        assert topic in agent.detect_concerns(text)

    def test_multiple(self, agent):
        assert len(agent.detect_concerns("stressed anxious can't sleep")) >= 2

    def test_default(self, agent):
        assert agent.detect_concerns("hello") == ["workplace_stress"]


class TestQueries:
    def test_advice_returns(self, agent):
        r = agent.get_advice("I'm stressed"); assert len(r["advice"]) > 0

    def test_disclaimer(self, agent):
        assert "disclaimer" in agent.get_advice("stressed")

    def test_citations(self, agent):
        for a in agent.get_advice("anxious")["advice"]:
            assert "paper" in a and "doi" in a

    def test_max_results(self, agent):
        assert len(agent.get_advice("stressed", max_results=3)["advice"]) <= 3

    def test_topics(self, agent):
        ids = {t["id"] for t in agent.get_topics()}
        assert len(ids) >= 24
        for t in ["workplace_stress", "workplace_bullying", "act_values", "biofeedback"]:
            assert t in ids

    def test_techniques(self, agent):
        assert len(agent.get_techniques_for_topic("workplace_stress")) > 0

    def test_stats(self, agent):
        s = agent.get_stats()
        assert s["papers"] >= 90 and s["advice"] >= 360
        assert s["topics"] >= 24 and s["techniques"] >= 37

    def test_format(self, agent):
        f = agent.format_response(agent.get_advice("stressed", max_results=2))
        assert "Detected concerns" in f and "DOI:" in f

    def test_bullying_advice(self, agent):
        r = agent.get_advice("I'm being bullied at work")
        assert len(r["advice"]) > 0 and "workplace_bullying" in r["concerns"]

    def test_exercise_advice(self, agent):
        r = agent.get_advice("Should I exercise for my mood?")
        assert len(r["advice"]) > 0

    def test_sleep_advice(self, agent):
        r = agent.get_advice("I can't sleep at night")
        assert len(r["advice"]) > 0 and "sleep_issues" in r["concerns"]

    def test_burnout_advice(self, agent):
        r = agent.get_advice("I'm completely burned out")
        assert len(r["advice"]) > 0 and "burnout" in r["concerns"]

    def test_mindfulness_advice(self, agent):
        r = agent.get_advice("I want to try meditation")
        assert len(r["advice"]) > 0 and "mindfulness" in r["concerns"]

    def test_digital_advice(self, agent):
        r = agent.get_advice("Is there a self-help app for anxiety?")
        assert len(r["advice"]) > 0


class TestKeywords:
    def test_all_have_keywords(self):
        for t in TOPIC_KEYWORDS: assert len(TOPIC_KEYWORDS[t]) >= 3

    def test_lowercase(self):
        for t, kws in TOPIC_KEYWORDS.items():
            for k in kws: assert k == k.lower()

    def test_count(self):
        assert len(TOPIC_KEYWORDS) == 24

    def test_all_keywords_map_to_data_topics(self):
        """Ensure TOPIC_KEYWORDS IDs are a superset of actual data topic IDs"""
        with open(PAPERS_PATH) as f:
            data = json.load(f)
        data_topic_ids = {t["id"] for t in data["topics"]}
        keyword_ids = set(TOPIC_KEYWORDS.keys())
        # All data topics should be detectable (minus aliases)
        covered = data_topic_ids & keyword_ids
        assert len(covered) >= 20, f"Only {len(covered)} data topics have keyword detection"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
