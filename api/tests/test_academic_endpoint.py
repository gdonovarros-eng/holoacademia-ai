from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from api.main import app


class AcademicEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_academic_ask_returns_structured_response(self) -> None:
        response = self.client.post("/academic/ask", json={"query": "¿Qué es un par biomagnético?"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["answer"])
        self.assertIn(body["confidence"], {"high", "medium", "low"})
        self.assertIsInstance(body["sources_used"], list)
        self.assertIsInstance(body["concepts_used"], list)
        self.assertIsInstance(body["suggested_followups"], list)


if __name__ == "__main__":
    unittest.main()
