"""
conftest.py — shared pytest configuration.

Ensures the repo root is on sys.path so imports like
`from app.services.x import y` resolve correctly regardless of
where pytest is invoked from.
"""

import sys
import os

# Insert the repo root (parent of this file) at the front of sys.path
sys.path.insert(0, os.path.dirname(__file__))