"""
SentinelAI Filter Service - Entry Point

This serves as the primary gRPC service wrapper for the SentiBERT filter.
"""

# pylint: disable=wrong-import-position

# NOTE: Only disable C0413 if maintaining consistency between files manually or using ruff.

import sys
from pathlib import Path

# Add parent directory to path to allow importing models and services
sys.path.append(str(Path(__file__).parent.parent))

from inference.server import serve


def init_app():
    """Initialise the application components."""
    print("[MAIN] SentinelAI Filter Service starting...")
    print("[MAIN] Python version:", sys.version)
    print("[MAIN] Working directory:", Path.cwd())

    # Start the gRPC server
    serve()


if __name__ == "__main__":
    print("[MAIN] Entry point reached")
    init_app()
