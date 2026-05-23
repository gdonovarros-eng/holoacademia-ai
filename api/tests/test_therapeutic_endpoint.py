from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from api.main import app


class TherapeuticEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_therapeutic_analyze_returns_structured_guidance(self) -> None:
        response = self.client.post(
            "/therapeutic/analyze",
            json={
                "motivo_consulta": "Dolor digestivo recurrente",
                "sintomas": ["ardor estomacal", "inflamación"],
                "inicio": "Empezó después de una separación",
                "frecuencia": "Aparece varias veces por semana",
                "contexto_emocional": "Mucho miedo y ansiedad desde entonces",
                "antecedentes": ["cirugía de vesícula"],
                "pregunta_del_terapeuta": "¿por dónde abrirías primero?",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["answer"])
        self.assertIn(body["confidence"], {"high", "medium", "low"})
        self.assertIsInstance(body["evidencias_principales"], list)
        self.assertIsInstance(body["pasos_inmediatos"], list)
        self.assertIsInstance(body["protocolo_principal"], dict)
        self.assertTrue(body["ruta_principal"])
        self.assertTrue(body["accion_inmediata"])


if __name__ == "__main__":
    unittest.main()
