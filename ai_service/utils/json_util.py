import re
import json
import logging
from json_repair import repair_json

logger = logging.getLogger(__name__)

def safe_json_loads(text: str) -> dict:
    """
    Two-layer repair: 
    1. Regex extracts the first JSON block.
    2. json-repair fixes syntax errors (quotes, commas, etc).
    """
    try:
        # Layer 1: Regex Extraction
        # Finds everything between the first '{' and the last '}'
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            logger.error("No JSON braces found in LLM response.")
            return {"is_risk": False, "reasoning": "Failed to find JSON structure."}
        
        json_content = match.group(0)

        # Layer 2: json-repair + Parsing
        # repair_json returns a valid JSON string
        repaired_json = repair_json(json_content)
        result = json.loads(repaired_json)
        
        return result

    except Exception as e:
        logger.error(f"Failed to parse or repair JSON: {e}")
        # Return a safe default to prevent the graph from breaking
        return {"is_risk": False, "reasoning": "Error during JSON repair."}