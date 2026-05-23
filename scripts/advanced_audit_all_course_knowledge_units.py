from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_ROOT = ROOT / "data" / "knowledge_units"
SCRIPT = ROOT / "scripts" / "advanced_audit_course_knowledge_unit.py"


def main() -> None:
    course_dirs = sorted(
        path for path in KNOWLEDGE_ROOT.iterdir() if path.is_dir() and path.name.startswith("course_")
    )
    failures: list[str] = []
    for course_dir in course_dirs:
        try:
            subprocess.run([sys.executable, str(SCRIPT), str(course_dir)], check=True)
            print(f"OK {course_dir.name}")
        except subprocess.CalledProcessError as exc:
            failures.append(f"{course_dir.name}: exit {exc.returncode}")

    if failures:
        raise SystemExit("Fallos en auditoría avanzada:\n" + "\n".join(failures))


if __name__ == "__main__":
    main()
