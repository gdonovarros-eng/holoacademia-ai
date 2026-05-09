from __future__ import annotations

import unittest

from academic_assistant.context_builder import build_academic_context
from academic_assistant.models import RetrievalHit


class ContextBuilderTests(unittest.TestCase):
    def test_build_context_groups_and_dedupes(self) -> None:
        results = [
            RetrievalHit(
                id="par_biomagnetico",
                source_type="concepts",
                score=98.0,
                title="Par biomagnético",
                content="Definición extensa",
                modulo="modulo_2",
                curso="holobiomagnetismo_2021",
                linea="salud",
                source="merged",
                confidence="high",
            ),
            RetrievalHit(
                id="par_biomagnetico",
                source_type="concepts",
                score=89.0,
                title="Par biomagnético",
                content="Definición breve",
                modulo="modulo_2",
                curso="holobiomagnetismo_2021",
                linea="salud",
                source="merged",
                confidence="high",
            ),
            RetrievalHit(
                id="modulo_2",
                source_type="module_summaries",
                score=80.0,
                title="Módulo 2",
                content="Resumen de módulo",
                modulo="modulo_2",
                curso="holobiomagnetismo_2021",
                linea="salud",
                source="merged",
                confidence="high",
            ),
        ]
        context = build_academic_context("Explica el par biomagnético", results)
        self.assertEqual(len(context["main_concepts"]), 1)
        self.assertEqual(context["main_concepts"][0]["id"], "par_biomagnetico")
        self.assertEqual(len(context["module_summaries"]), 1)
        self.assertTrue(context["citations"])

    def test_build_context_for_comparison(self) -> None:
        results = [
            RetrievalHit(
                id="polaridad",
                source_type="concepts",
                score=97.0,
                title="Polaridad",
                content="Define la orientación energética.",
                modulo="modulo_2",
                curso="holobiomagnetismo_2021",
                linea="salud",
                source="merged",
                confidence="high",
            ),
            RetrievalHit(
                id="par_biomagnetico",
                source_type="concepts",
                score=96.0,
                title="Par biomagnético",
                content="Define la relación funcional entre puntos.",
                modulo="modulo_2",
                curso="holobiomagnetismo_2021",
                linea="salud",
                source="merged",
                confidence="high",
            ),
        ]
        intent_data = {
            "intent": "comparison",
            "targets": ["polaridad", "par biomagnetico"],
            "module_hint": None,
            "needs_simple_language": False,
        }
        context = build_academic_context("Diferencia entre polaridad y par biomagnético", results, intent_data=intent_data)
        self.assertEqual(context["concept_a"]["id"], "polaridad")
        self.assertEqual(context["concept_b"]["id"], "par_biomagnetico")
        self.assertTrue(context["comparison_notes"])

    def test_build_context_for_module_summary(self) -> None:
        results = [
            RetrievalHit(
                id="modulo_2",
                source_type="module_summaries",
                score=95.0,
                title="Módulo 2",
                content="Resumen del módulo 2.",
                modulo="modulo_2",
                curso="holobiomagnetismo_2021",
                linea="salud",
                source="merged",
                confidence="high",
                metadata={"temas_clave": ["pares biomagnéticos", "rastreo"]},
            )
        ]
        intent_data = {
            "intent": "module_summary",
            "targets": [],
            "module_hint": "modulo_2",
            "needs_simple_language": False,
        }
        context = build_academic_context("Resume el módulo 2", results, intent_data=intent_data)
        self.assertEqual(context["target_module"], "modulo_2")
        self.assertEqual(context["module_summary"]["id"], "modulo_2")
        self.assertIn("pares biomagnéticos", context["supporting_topics"])


if __name__ == "__main__":
    unittest.main()
