from __future__ import annotations

import sys
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
PACKAGE_PARENT = TESTS_DIR.parent.parent

if str(PACKAGE_PARENT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_PARENT))
