"""
Pytest configuration: ensure repo root and tools/ are importable
in all test modules, regardless of how pytest resolves __file__.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent  # repo root (tests/ parent)
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
