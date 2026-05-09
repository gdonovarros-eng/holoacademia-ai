from __future__ import annotations

import unittest

from academic_assistant.answer_generator import generate_academic_answer
from academic_assistant.service import detect_response_mode


class FakeLLMClient:
    def __init__(self, text: str, *, enabled: bool = True, finish_reason: str = "stop", error: str = "") -> None:
        self.text = text
        self.enabled = enabled
        self.finish_reason = finish_reason
        self.error = error
        self.provider = "fake"
        self.model = "fake-model"

    def complete(self, messages, response_mode: str = "fast"):
        return {
            "text": self.text,
            "ok": bool(self.text),
            "finish_reason": self.finish_reason,
            "error": self.error,
        }


class AnswerGeneratorModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = {
            "main_concepts": [
                {
                    "id": "par_biomagnetico",
                    "title": "Par biomagnético",
                    "content": "Es una dupla funcional de puntos usada en el rastreo del curso.",
                }
            ],
            "supporting_glossary": [],
            "module_summaries": [],
            "faq_support": [],
            "course_context": {},
            "citations": [],
            "retrieval_trace": [],
            "intent": {"intent": "definition", "targets": [], "module_hint": None, "needs_simple_language": False},
        }

    def test_detect_response_mode_fast_by_default(self) -> None:
        self.assertEqual(detect_response_mode("¿Qué es un par biomagnético?"), "fast")

    def test_detect_response_mode_deep_when_requested(self) -> None:
        self.assertEqual(detect_response_mode("Explícame más a fondo el par biomagnético"), "deep")

    def test_generate_answer_marks_used_fallback_when_provider_fails(self) -> None:
        llm = FakeLLMClient("", enabled=True, finish_reason="error", error="provider_failed")
        result = generate_academic_answer(
            query="¿Qué es un par biomagnético?",
            context=self.context,
            llm_client=llm,
            response_mode="fast",
        )
        self.assertTrue(result["used_fallback"])
        self.assertEqual(result["mode_used"], "fast")

    def test_generate_answer_marks_used_fallback_false_when_provider_succeeds(self) -> None:
        llm = FakeLLMClient("Par biomagnético es una dupla funcional de puntos.", enabled=True)
        result = generate_academic_answer(
            query="¿Qué es un par biomagnético?",
            context=self.context,
            llm_client=llm,
            response_mode="deep",
        )
        self.assertFalse(result["used_fallback"])
        self.assertEqual(result["mode_used"], "deep")


if __name__ == "__main__":
    unittest.main()
