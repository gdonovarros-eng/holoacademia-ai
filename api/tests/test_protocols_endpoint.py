from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from api.main import app


class ProtocolsEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_protocol_found_by_name(self) -> None:
        response = self.client.post(
            "/protocols/guide",
            json={"protocol_name": "Entrevista inicial de rastreo"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["found"])
        self.assertTrue(body["pasos"])

    def test_protocol_not_found_returns_prudent_response(self) -> None:
        response = self.client.post(
            "/protocols/guide",
            json={"protocol_name": "protocolo inexistente total"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["found"])
        self.assertTrue(body["answer"])


if __name__ == "__main__":
    unittest.main()
