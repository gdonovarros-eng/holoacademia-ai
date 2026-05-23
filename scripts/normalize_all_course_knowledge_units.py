from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_UNITS = ROOT / "data" / "knowledge_units"
NORMALIZER = ROOT / "scripts" / "normalize_course_knowledge_unit.py"


def main() -> None:
    course_dirs = sorted(
        path
        for path in KNOWLEDGE_UNITS.iterdir()
        if path.is_dir() and path.name.startswith("course_")
    )
    if not course_dirs:
        raise SystemExit("No se encontraron cursos en data/knowledge_units.")

    failures: list[str] = []
    for course_dir in course_dirs:
        result = subprocess.run([sys.executable, str(NORMALIZER), str(course_dir)], check=False)
        if result.returncode != 0:
            failures.append(course_dir.name)

    if failures:
        raise SystemExit(f"Falló la normalización en: {', '.join(failures)}")


if __name__ == "__main__":
    main()
