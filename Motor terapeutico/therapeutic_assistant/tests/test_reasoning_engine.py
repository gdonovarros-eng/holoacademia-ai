from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from therapeutic_assistant.case_analyzer import build_case_analysis
from therapeutic_assistant.loader import load_therapeutic_course_data
from therapeutic_assistant.reasoning_engine import generate_reasoning
from therapeutic_assistant.service import TherapeuticAssistantService


class ReasoningEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.knowledge = load_therapeutic_course_data()

    def test_case_with_recurrence_generates_reasoning(self) -> None:
        analysis = build_case_analysis(
            {
                "motivo_consulta": "Cefalea",
                "sintomas": ["dolor pulsátil", "migraña"],
                "inicio": "Desde hace un año",
                "frecuencia": "Vuelve cada mes",
            }
        )
        result = generate_reasoning(analysis, self.knowledge, {"pregunta_del_terapeuta": "¿Qué patrones mirarías aquí?"})
        pattern_ids = [item["id"] for item in result["matched_patterns"]]
        self.assertIn("patron_recurrencia", pattern_ids)
        self.assertIn(result["confidence"], {"medium", "high"})

    def test_low_base_case_stays_prudent(self) -> None:
        service = TherapeuticAssistantService()
        response = service.answer_therapeutic_query({"motivo_consulta": "No me siento bien"})
        self.assertEqual(response["confidence"], "low")
        self.assertTrue(response["priority_questions"])

    def test_case_with_sufficient_data_returns_lines_and_warnings(self) -> None:
        service = TherapeuticAssistantService()
        response = service.answer_therapeutic_query(
            {
                "motivo_consulta": "Dolor digestivo recurrente",
                "sintomas": ["ardor", "malestar estomacal"],
                "inicio": "Empezó después de una separación",
                "frecuencia": "Aparece varias veces por semana",
                "contexto_emocional": "Mucho miedo y ansiedad desde entonces",
                "antecedentes": ["cirugía de vesícula"],
                "pregunta_del_terapeuta": "Quiero una lectura inicial prudente",
            }
        )
        self.assertTrue(response["possible_lines"])
        self.assertTrue(response["warnings"])

    def test_response_is_prioritized_and_actionable(self) -> None:
        service = TherapeuticAssistantService()
        response = service.answer_therapeutic_query(
            {
                "motivo_consulta": "Cefalea recurrente con ansiedad",
                "sintomas": ["cefalea", "tensión cervical", "episodios que vuelven"],
                "inicio": "Empezó después de un periodo de mucho miedo",
                "frecuencia": "Vuelve cada mes",
                "contexto_emocional": "Miedo y ansiedad",
                "pregunta_del_terapeuta": "¿Por dónde abrirías el caso?",
            }
        )
        self.assertTrue(response["ruta_principal"])
        self.assertTrue(response["entrevista_base"])
        self.assertTrue(response["ruta_sugerida"])
        self.assertTrue(response["accion_inmediata"])
        self.assertTrue(response["evidencias_principales"])
        self.assertTrue(response["protocolo_sugerido"])
        self.assertTrue(response["protocolo_principal"] or response["protocolo_sugerido"])
        self.assertTrue(response["herramientas_clave"])
        self.assertTrue(response["herramientas_relevantes"])
        self.assertTrue(response["pasos_inmediatos"])
        self.assertTrue(response["punto_de_decision"])
        self.assertTrue(response["si_no_confirma"])
        self.assertIn("Lo primero que conviene hacer es", response["answer"])
        self.assertIn("Esto se sostiene por:", response["answer"])
        self.assertLessEqual(len(response["evidencias_principales"]), 4)
        self.assertLessEqual(len(response["validaciones_clave"]), 4)
        self.assertLessEqual(len(response["pasos_inmediatos"]), 6)
        self.assertLessEqual(len(response["herramientas_relevantes"]), 4)
        self.assertLessEqual(len(response["used_patterns"]), 2)
        self.assertLessEqual(len(response["possible_lines"]), 1)
        self.assertLessEqual(len(response["priority_questions"]), 4)
        self.assertIsInstance(response["puerta_principal"], dict)
        self.assertTrue(response["puerta_principal"])
        self.assertEqual(len(response["evidencias_principales"]), len(set(response["evidencias_principales"])))

        protocol_payload = response["protocolo_sugerido"]
        self.assertIn("principal", protocol_payload)
        self.assertLessEqual(len(protocol_payload.keys()), 2)
        self.assertEqual(len(response["validaciones_clave"]), len(set(response["validaciones_clave"])))
        self.assertIn("Secuencia sugerida:", response["answer"])

    def test_microbios_y_pares_entran_como_herramientas_de_sesion(self) -> None:
        service = TherapeuticAssistantService()
        response = service.answer_therapeutic_query(
            {
                "motivo_consulta": "Posible componente infeccioso",
                "sintomas": ["ardor digestivo", "inflamación"],
                "inicio": "desde hace semanas",
                "pregunta_del_terapeuta": "¿Conviene abrir microbios y pares biomagnéticos?",
            }
        )
        tool_ids = [item.get("id") for item in response["herramientas_relevantes"] if isinstance(item, dict)]
        self.assertIn("microorganismos_patogenos", tool_ids)
        self.assertIn("par_biomagnetico", tool_ids)

    def test_chakras_entran_como_herramienta_complementaria_si_la_ruta_lo_soporta(self) -> None:
        service = TherapeuticAssistantService()
        response = service.answer_therapeutic_query(
            {
                "motivo_consulta": "Conflicto emocional activo",
                "sintomas": ["opresión en pecho"],
                "inicio": "después de una ruptura fuerte",
                "contexto_emocional": "mucho llanto, impacto emocional y miedo",
                "pregunta_del_terapeuta": "Si hay que precisar más, ¿tendría sentido revisar chakra o meridiano?",
            }
        )
        tool_ids = [item.get("id") for item in response["herramientas_relevantes"] if isinstance(item, dict)]
        self.assertTrue("chakras" in tool_ids or "meridianos" in tool_ids)


if __name__ == "__main__":
    unittest.main()
