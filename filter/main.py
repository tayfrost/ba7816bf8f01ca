"""
SentinelAI Filter Service - Entry Point

This will serve as the service wrapper for the BERT filter.
To be implemented.
"""

# pylint: disable=wrong-import-position

# NOTE: Only disable C0413 if maintaining consistency between files manually or using ruff.

import sys
from pathlib import Path

# Add parent directory to path to allow importing models and services
sys.path.append(str(Path(__file__).parent.parent))

# import config
from services.model_factory import load_production_model


def init_app():
    """Initialise the application components."""
    return  # Stub


if __name__ == "__main__":
    init_app()
