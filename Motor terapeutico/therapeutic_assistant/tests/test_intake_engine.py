from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from therapeutic_assistant.intake_engine import analyze_case_intake
from therapeutic_assistant.loader import load_therapeutic_course_data
from therapeutic_assistant.models import CaseInput


class IntakeEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.knowledge = load_therapeutic_course_data()

    def test_incomplete_case_detects_missing_and_priority_questions(self) -> None:
        case_input = CaseInput.from_dict({"motivo_consulta": "Dolor de cabeza"})
        result = analyze_case_intake(case_input, self.knowledge)
        self.assertIn("síntomas", result["missing_data"])
        self.assertTrue(result["priority_questions"])
        self.assertIn("¿Desde cuándo empezó, aunque sea de forma aproximada?", [item["pregunta"] for item in result["priority_questions"]])


if __name__ == "__main__":
    unittest.main()
