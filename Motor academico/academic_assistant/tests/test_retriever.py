from __future__ import annotations

import unittest
from pathlib import Path

from academic_assistant.models import AcademicKnowledgeBase, Concept, GlossaryEntry, ModuleSummary, FAQCandidate
from academic_assistant.retriever import detect_query_intent, resolve_course_concept, search_academic_context


class RetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.knowledge = AcademicKnowledgeBase(
            course_dir=Path("."),
            course_id="holobiomagnetismo_2021",
            line="salud",
            concepts=[
                Concept(
                    id="par_biomagnetico",
                    termino="Par biomagnético",
                    aliases=["pares biomagneticos"],
                    definicion="Relación funcional entre dos puntos corporales.",
                    explicacion_simple="Es una dupla de puntos que se evalúa en el rastreo.",
                    explicacion_extendida="Se usa para entender relaciones energéticas dentro del curso.",
                    modulo="modulo_2",
                    curso="holobiomagnetismo_2021",
                    linea="salud",
                    source="merged",
                    confidence="high",
                )
            ,
                Concept(
                    id="polaridad",
                    termino="Polaridad",
                    aliases=["polaridades", "positivo y negativo"],
                    definicion="Orientación funcional de la carga de un punto.",
                    explicacion_simple="Es la dirección energética con la que se interpreta un punto.",
                    explicacion_extendida="Se usa para entender cómo se organiza el rastreo en el curso.",
                    modulo="modulo_2",
                    curso="holobiomagnetismo_2021",
                    linea="salud",
                    source="merged",
                    confidence="high",
                )
            ],
            glossary=[
                GlossaryEntry(
                    id="par_biomagnetico_glossary",
                    termino="Par biomagnético",
                    definicion_corta="Dupla funcional de puntos.",
                    curso="holobiomagnetismo_2021",
                    linea="salud",
                    source="merged",
                    confidence="high",
                    referencia_concepto="par_biomagnetico",
                )
            ,
                GlossaryEntry(
                    id="polaridad_glossary",
                    termino="Polaridad",
                    definicion_corta="Orientación energética de referencia.",
                    curso="holobiomagnetismo_2021",
                    linea="salud",
                    source="merged",
                    confidence="high",
                    referencia_concepto="polaridad",
                )
            ,
                GlossaryEntry(
                    id="cronologia_clinica_glossary",
                    termino="Cronología clínica",
                    definicion_corta="Orden temporal del inicio y evolución del síntoma.",
                    curso="holobiomagnetismo_2021",
                    linea="salud",
                    source="merged",
                    confidence="high",
                    referencia_concepto="",
                )
            ],
            module_summaries=[
                ModuleSummary(
                    id="modulo_2",
                    titulo="Módulo 2",
                    resumen="Introduce pares biomagnéticos y bases del rastreo.",
                    temas_clave=["pares biomagnéticos"],
                    curso="holobiomagnetismo_2021",
                    linea="salud",
                    source="merged",
                    confidence="high",
                )
            ,
                ModuleSummary(
                    id="modulo_1",
                    titulo="Módulo 1",
                    resumen="Introduce cronología clínica y apertura del rastreo.",
                    temas_clave=["cronología clínica", "apertura", "inicio del síntoma"],
                    curso="holobiomagnetismo_2021",
                    linea="salud",
                    source="merged",
                    confidence="high",
                )
            ],
            faq_candidates=[
                FAQCandidate(
                    id="faq_par_biomagnetico",
                    pregunta="¿Qué es el par biomagnético?",
                    respuesta="Es una relación funcional entre puntos que el curso trabaja en el rastreo.",
                    curso="holobiomagnetismo_2021",
                    linea="salud",
                    source="merged",
                    confidence="high",
                )
            ],
            module_inventory=[
                {"id": "modulo_1", "titulo": "Módulo 1", "modulo": "modulo_1", "tema": "cronología clínica"},
                {"id": "modulo_2", "titulo": "Módulo 2", "modulo": "modulo_2", "tema": "pares biomagnéticos"},
            ],
            transcript_inventory=[
                {"id": "segmento_cronologia", "titulo": "Cronología clínica", "modulo": "modulo_1", "tema": "cronología clínica"},
            ],
        )

    def test_exact_concept_match_has_priority(self) -> None:
        results = search_academic_context("¿Qué es el par biomagnético?", self.knowledge, top_k=3)
        self.assertTrue(results)
        self.assertEqual(results[0].source_type, "concepts")
        self.assertEqual(results[0].id, "par_biomagnetico")

    def test_detect_definition_intent(self) -> None:
        intent = detect_query_intent("¿Qué es un par biomagnético?", self.knowledge)
        self.assertEqual(intent["intent"], "definition")

    def test_resolve_course_concept_direct_match(self) -> None:
        resolution = resolve_course_concept("¿Qué es par biomagnético?", self.knowledge)
        self.assertTrue(resolution["resolved"])
        self.assertEqual(resolution["resolved_concept_id"], "par_biomagnetico")
        self.assertIn(resolution["resolution_source"], {"concept", "alias", "glossary"})

    def test_resolve_course_concept_without_accent(self) -> None:
        resolution = resolve_course_concept("Explícame par biomagnetico", self.knowledge)
        self.assertTrue(resolution["resolved"])
        self.assertEqual(resolution["resolved_concept_id"], "par_biomagnetico")

    def test_resolve_course_concept_from_glossary(self) -> None:
        resolution = resolve_course_concept("¿Qué es cronologia clinica?", self.knowledge)
        self.assertTrue(resolution["resolved"])
        self.assertEqual(resolution["resolved_concept_id"], "cronologia_clinica_glossary")
        self.assertEqual(resolution["resolution_source"], "glossary")

    def test_resolve_course_concept_ambiguous_does_not_force_high_confidence(self) -> None:
        resolution = resolve_course_concept("¿Qué es energía?", self.knowledge)
        self.assertFalse(resolution["resolved"] or resolution["resolution_confidence"] == "high")

    def test_resolve_course_concept_without_clear_target(self) -> None:
        resolution = resolve_course_concept("Explícamelo mejor", self.knowledge)
        self.assertFalse(resolution["resolved"])
        self.assertEqual(resolution["resolution_confidence"], "low")

    def test_detect_comparison_intent_and_targets(self) -> None:
        intent = detect_query_intent("¿Cuál es la diferencia entre polaridad y par biomagnético?", self.knowledge)
        self.assertEqual(intent["intent"], "comparison")
        self.assertEqual(intent["targets"], ["polaridad", "par biomagnetico"])

    def test_detect_module_summary_intent(self) -> None:
        intent = detect_query_intent("Resume el módulo 2", self.knowledge)
        self.assertEqual(intent["intent"], "module_summary")
        self.assertEqual(intent["module_hint"], "modulo_2")

    def test_detect_simple_language_need(self) -> None:
        intent = detect_query_intent("Explícamelo como si apenas estuviera empezando", self.knowledge)
        self.assertTrue(intent["needs_simple_language"])

    def test_detect_locate_in_course_intent(self) -> None:
        intent = detect_query_intent("¿En qué parte del curso se habla de cronología clínica?", self.knowledge)
        self.assertEqual(intent["intent"], "locate_in_course")

    def test_comparison_search_recovers_both_targets(self) -> None:
        intent = detect_query_intent("¿Cuál es la diferencia entre polaridad y par biomagnético?", self.knowledge)
        results = search_academic_context(
            "¿Cuál es la diferencia entre polaridad y par biomagnético?",
            self.knowledge,
            top_k=5,
            intent_data=intent,
        )
        ids = {hit.id for hit in results if hit.source_type == "concepts"}
        self.assertIn("par_biomagnetico", ids)
        self.assertIn("polaridad", ids)

    def test_module_summary_query_prioritizes_module_summary(self) -> None:
        intent = detect_query_intent("Resume el módulo 2", self.knowledge)
        results = search_academic_context("Resume el módulo 2", self.knowledge, top_k=3, intent_data=intent)
        self.assertTrue(results)
        self.assertEqual(results[0].source_type, "module_summaries")

    def test_resolves_approximate_pairs_target(self) -> None:
        intent = detect_query_intent("Explícame los pares", self.knowledge)
        trace = intent["target_resolution_trace"][0]
        self.assertEqual(trace["resolved_target"], "par_biomagnetico")
        self.assertIn(trace["resolution_confidence"], {"medium", "high"})

    def test_resolves_positive_negative_to_polaridad(self) -> None:
        intent = detect_query_intent("Eso de positivo y negativo", self.knowledge)
        trace = intent["target_resolution_trace"][0]
        self.assertEqual(trace["resolved_target"], "polaridad")

    def test_resolves_comparison_with_approximate_target(self) -> None:
        intent = detect_query_intent("Diferencia entre los pares y polaridad", self.knowledge)
        self.assertEqual(intent["intent"], "comparison")
        self.assertEqual(intent["targets"], ["par biomagnetico", "polaridad"])

    def test_resolves_inicio_del_sintoma_to_supported_module(self) -> None:
        intent = detect_query_intent("Lo del inicio del síntoma", self.knowledge)
        trace = intent["target_resolution_trace"][0]
        self.assertEqual(trace["resolved_kind"], "module")
        self.assertEqual(trace["resolved_target"], "modulo_1")

    def test_ambiguous_anaphoric_query_does_not_force_resolution(self) -> None:
        intent = detect_query_intent("Explícamelo mejor", self.knowledge)
        self.assertTrue(intent["anaphoric_without_target"])
        self.assertEqual(intent["target_resolution_trace"], [])


if __name__ == "__main__":
    unittest.main()
