"""Configuration, constants, and logging setup."""

import logging
import os
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("sentinelai-kg-mcp")

HF_DATASET_REPO = os.environ.get("HF_DATASET_REPO", "")
HF_DATASET_FILE = os.environ.get("HF_DATASET_FILE", "papers.json")

LOCAL_DATA_PATH = os.environ.get(
    "KG_DATA_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "papers.json"),
)

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8001"))

DISCLAIMER = (
    "This advice is based on peer-reviewed research and is not a "
    "substitute for professional mental health support."
)

MAX_INPUT_LENGTH = 2000

CRISIS_KEYWORDS = re.compile(
    r"\b("
    r"suicid(?:e|al|ality)|kill\s*my\s*self|end\s*(?:my\s*life|it\s*all)|want\s*to\s*die|"
    r"self[\s-]*harm(?:ing)?|cut(?:ting)?\s*my\s*self|hurt(?:ing)?\s*my\s*self|don'?t\s*want\s*to\s*live|"
    r"no\s*reason\s*to\s*live|better\s*off\s*dead|take\s*my\s*(?:own\s*)?life|"
    r"overdos(?:e|ed|ing)|hang\s*my\s*self"
    r")\b",
    re.IGNORECASE,
)
