"""Pytest configuration and root sys.path initialization for orca-core tests."""

from __future__ import annotations

import sys
from pathlib import Path

ORCA_CORE_ROOT = Path(__file__).resolve().parent.parent
if str(ORCA_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(ORCA_CORE_ROOT))
