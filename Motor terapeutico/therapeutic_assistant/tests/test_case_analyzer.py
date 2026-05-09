from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from therapeutic_assistant.case_analyzer import build_case_analysis


class CaseAnalyzerTests(unittest.TestCase):
    def test_case_with_timeline_and_recurrence_keeps_timeline_elements(self) -> None:
        result = build_case_analysis(
            {
                "motivo_consulta": "Cefalea recurrente",
                "sintomas": ["dolor de cabeza", "náusea"],
                "inicio": "Hace seis meses",
                "frecuencia": "Dos veces por semana",
            }
        )
        self.assertIn("Hace seis meses", result["timeline_elements"])
        self.assertIn("Dos veces por semana", result["timeline_elements"])
        self.assertTrue(result["case_summary"])


if __name__ == "__main__":
    unittest.main()
