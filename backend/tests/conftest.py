"""Pytest configuration for backend test suite.

Ensures backend root directory is on sys.path for all test modules.
"""

import sys
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
