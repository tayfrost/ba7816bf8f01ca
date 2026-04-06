"""Shared formatting and clamping helpers."""


def clamp_results(max_results: int, ceiling: int = 20) -> int:
    """Clamp max_results between 1 and ceiling."""
    return max(1, min(max_results, ceiling))


def format_recommendation(r: dict) -> dict:
    """Format a raw advice item into the public recommendation shape."""
    return {
        "advice": r["text"],
        "confidence": r["confidence"],
        "technique": r["technique_name"],
        "technique_id": r["technique_id"],
        "technique_description": r["technique_description"],
        "paper_title": r["paper_title"],
        "paper_id": r["paper_id"],
        "doi": r["paper_doi"],
        "citations": r["paper_citations"],
    }
