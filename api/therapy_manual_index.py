from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = BASE_DIR / "data" / "therapy_manual_index.json"


@lru_cache(maxsize=1)
def get_therapy_manual_index() -> dict:
    if not INDEX_PATH.exists():
        return {
            "manual_count": 0,
            "manuals": [],
            "course_index": {},
            "system_index": {},
            "tag_index": {},
        }
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))

