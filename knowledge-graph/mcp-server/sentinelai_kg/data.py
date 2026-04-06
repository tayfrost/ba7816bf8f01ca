"""Dataset resolution, loading, and lazy access."""

import json

from sentinelai_kg.config import (
    HF_DATASET_REPO,
    HF_DATASET_FILE,
    LOCAL_DATA_PATH,
    logger,
)
import os


def _resolve_data_path() -> str:
    """Resolve dataset path: HuggingFace Hub if configured, otherwise local file."""
    if HF_DATASET_REPO:
        try:
            from huggingface_hub import hf_hub_download
            path = hf_hub_download(
                repo_id=HF_DATASET_REPO,
                filename=HF_DATASET_FILE,
                repo_type="dataset",
            )
            logger.info("Loaded dataset from HuggingFace: %s", HF_DATASET_REPO)
            return path
        except Exception as exc:
            logger.warning("HF download failed (%s), falling back to local", exc)

    if os.path.exists(LOCAL_DATA_PATH):
        logger.info("Using local dataset: %s", LOCAL_DATA_PATH)
        return LOCAL_DATA_PATH

    raise FileNotFoundError(
        f"No dataset found. Set HF_DATASET_REPO or ensure {LOCAL_DATA_PATH} exists."
    )


def _load_dataset(data_path: str) -> dict:
    with open(data_path, "r") as f:
        data = json.load(f)

    topic_index = {t["id"]: t for t in data["topics"]}
    technique_index = {t["id"]: t for t in data["techniques"]}

    advice_items = []
    for paper in data["papers"]:
        for adv in paper["advice"]:
            technique_topics = technique_index.get(adv["technique"], {}).get("topics", [])
            advice_items.append({
                "text": adv["text"],
                "confidence": adv["confidence"],
                "technique_id": adv["technique"],
                "technique_name": technique_index.get(adv["technique"], {}).get("name", adv["technique"]),
                "technique_description": technique_index.get(adv["technique"], {}).get("description", ""),
                "paper_id": paper["id"],
                "paper_title": paper["title"],
                "paper_doi": paper.get("doi", "N/A"),
                "paper_year": paper["year"],
                "paper_citations": paper["citations"],
                "paper_topics": paper["topics"],
                "advice_topics": technique_topics if technique_topics else paper["topics"],
            })
    advice_items.sort(key=lambda x: (x["confidence"], x["paper_citations"]), reverse=True)

    return {
        "raw": data,
        "topics": topic_index,
        "techniques": technique_index,
        "advice": advice_items,
        "papers": data["papers"],
        "metadata": data["metadata"],
    }


_DATASET: dict | None = None


def get_dataset() -> dict:
    """Lazy-load dataset on first access. Fail-fast but import-safe for tests."""
    global _DATASET
    if _DATASET is None:
        data_path = _resolve_data_path()
        _DATASET = _load_dataset(data_path)
        logger.info(
            "Dataset loaded: %d papers, %d advice items",
            len(_DATASET["papers"]),
            len(_DATASET["advice"]),
        )
    return _DATASET
