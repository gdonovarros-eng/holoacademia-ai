from __future__ import annotations

import os
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from .models import AcademicAnswer
from .prompt_builder import build_academic_prompt
from .retriever import normalize_text


DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_OPENAI_MODEL = "gpt-5-mini"


class AcademicLLMClient:
    def __init__(self) -> None:
        self.use_model = (os.getenv("ACADEMIC_ASSISTANT_USE_MODEL", "false").strip().lower() in {"1", "true", "yes", "on"})
        self.provider = (os.getenv("LLM_PROVIDER", "groq").strip() or "groq").lower()
        if self.provider == "groq":
            api_key = os.getenv("GROQ_API_KEY", "").strip()
            base_url = os.getenv("LLM_BASE_URL", DEFAULT_GROQ_BASE_URL).strip() or DEFAULT_GROQ_BASE_URL
            model = os.getenv("ACADEMIC_ASSISTANT_MODEL", "").strip() or os.getenv("OPENAI_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL
        else:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            base_url = os.getenv("LLM_BASE_URL", "").strip() or None
            model = os.getenv("ACADEMIC_ASSISTANT_MODEL", "").strip() or os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
        self.model = model
        self.enabled = bool(self.use_model and api_key and OpenAI is not None)
        self.client = None
        if self.enabled:
            kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = OpenAI(**kwargs)

    def complete(self, messages: list[dict[str, str]], response_mode: str = "fast") -> dict[str, Any]:
        if not self.enabled or self.client is None:
            return {"text": "", "ok": False, "finish_reason": "disabled", "error": "llm_disabled"}
        max_tokens = (
            int(os.getenv("ACADEMIC_ASSISTANT_DEEP_MAX_TOKENS", "1000"))
            if response_mode == "deep"
            else int(os.getenv("ACADEMIC_ASSISTANT_FAST_MAX_TOKENS", "600"))
        )
        timeout_seconds = (
            float(os.getenv("ACADEMIC_ASSISTANT_DEEP_TIMEOUT_SECONDS", "14"))
            if response_mode == "deep"
            else float(os.getenv("ACADEMIC_ASSISTANT_FAST_TIMEOUT_SECONDS", "8"))
        )
        try:
            system_msg = next((m["content"] for m in messages if m.get("role") == "system"), "")
            user_msg = next((m["content"] for m in messages if m.get("role") == "user"), "")
            response = self.client.responses.create(
                model=self.model,
                instructions=system_msg,
                input=user_msg,
                max_output_tokens=max_tokens,
                timeout=timeout_seconds,
            )
            text = getattr(response, "output_text", "") or ""
            if not text.strip():
                for item in getattr(response, "output", []) or []:
                    for content in getattr(item, "content", []) or []:
                        value = getattr(content, "text", None)
                        if value:
                            text += value
            finish = "stop"
            incomplete = getattr(response, "incomplete_details", None)
            if isinstance(incomplete, dict) and incomplete.get("reason") == "max_output_tokens":
                finish = "length"
            return {
                "text": text.strip(),
                "ok": True,
                "finish_reason": finish,
                "error": "",
            }
        except Exception as exc:
            return {"text": "", "ok": False, "finish_reason": "error", "error": str(exc)}


def _infer_confidence(context: dict[str, Any]) -> str:
    trace = context.get("retrieval_trace", [])
    if not trace:
        return "low"
    top = max(item.get("score", 0.0) for item in trace)
    if top >= 90 and len(context.get("main_concepts", [])) >= 1:
        return "high"
    if top >= 65:
        return "medium"
    return "low"


def _extract_concepts_used(context: dict[str, Any]) -> list[str]:
    return [item["id"] for item in context.get("main_concepts", [])]


def _response_looks_incomplete(text: str) -> bool:
    clean = (text or "").strip()
    if not clean:
        return True
    if len(clean) < 40:
        return False
    if clean.endswith((" y", " o", " porque", " pero", " aunque", " entonces", " por ejemplo")):
        return True
    return clean[-1] not in ".?!»”\""


def _fallback_answer(query: str, context: dict[str, Any], concise: bool = False) -> str:
    concepts = context.get("main_concepts", [])
    modules = context.get("module_summaries", [])
    glossary = context.get("supporting_glossary", [])
    q = normalize_text(query)
    intent = (context.get("intent") or {}).get("intent", "general_academic")
    if (context.get("intent") or {}).get("anaphoric_without_target"):
        return (
            "Puedo ayudarte, pero aquí me falta una referencia clara. "
            "Si me dices el concepto, el módulo o la parte exacta que no entendiste, te lo explico mejor."
        )

    if intent == "locate_in_course":
        module_summary = context.get("module_summary")
        if module_summary:
            modulo = module_summary.get("modulo") or module_summary.get("id") or "una parte del curso"
            return (
                f"Este tema se trabaja sobre todo en {module_summary.get('title', modulo)}.\n\n"
                f"Ahí el curso lo presenta así: {module_summary.get('content', '')}"
            )

    if "diferencia" in q and intent == "comparison":
        first = context.get("concept_a")
        second = context.get("concept_b")
        if not first or not second:
            missing = context.get("missing_targets", [])
            if missing:
                return (
                    "Puedo ver que la pregunta es comparativa, pero no encontré base suficiente para ubicar con claridad "
                    f"estos conceptos dentro del curso: {', '.join(missing)}. "
                    "Prefiero no compararlos mal. Si quieres, podemos probar con los nombres exactos usados en clase o con un módulo concreto."
                )
        if not first or not second:
            return (
                "La pregunta es comparativa, pero no encontré los dos conceptos con suficiente claridad dentro del material recuperado. "
                "Prefiero no forzar una comparación imprecisa."
            )
        answer = (
            f"{first['title']} y {second['title']} se relacionan, pero no significan lo mismo.\n\n"
            f"{first['title']} se entiende así dentro del curso: {first['content']}\n\n"
            f"En cambio, {second['title']} se explica así: {second['content']}\n\n"
            "La diferencia principal es que cada uno apunta a una idea distinta del tema, "
            "aunque en clase puedan aparecer conectados."
        )
        if concise:
            return (
                f"{first['title']} y {second['title']} no significan lo mismo.\n\n"
                f"{first['title']}: {first['content']}\n\n"
                f"{second['title']}: {second['content']}"
            )
        return answer
    if "resume" in q or "resumen" in q:
        module = context.get("module_summary") or (modules[0] if modules else None)
        if module:
            answer = (
                f"{module['title']} trata, en esencia, de esto:\n\n"
                f"{module['content']}\n\n"
                "Si quieres, después te lo convierto en un resumen todavía más corto o en puntos clave."
            )
            if concise:
                return f"{module['title']} trata, en esencia, de esto: {module['content']}"
            return answer
    if concepts:
        concept = concepts[0]
        answer = (
            f"{concept['title']} se entiende, de forma sencilla, así:\n\n"
            f"{concept['content']}\n\n"
            "Si te sirve, también te lo puedo bajar todavía más a lenguaje de principiante o compararlo con otro concepto."
        )
        if concise:
            return f"{concept['title']} se entiende, de forma sencilla, así: {concept['content']}"
        return answer
    if modules:
        module = modules[0]
        answer = (
            "No encontré una definición aislada y cerrada de ese término dentro de los conceptos estructurados del curso, "
            f"pero sí aparece trabajado en {module['title']}.\n\n"
            f"Lo que el curso deja claro ahí es esto: {module['content']}\n\n"
            "Si quieres, te lo reformulo como si lo estuviéramos viendo en clase desde cero."
        )
        if concise:
            return (
                "No encontré una definición formal aislada, pero el curso lo trabaja aquí: "
                f"{module['title']}. La idea central es: {module['content']}"
            )
        return answer
    if glossary:
        item = glossary[0]
        answer = (
            f"{item['title']} se usa en el curso con esta idea básica: {item['content']}\n\n"
            "Si quieres, puedo ampliarlo un poco más para que quede mejor entendido."
        )
        if concise:
            return f"{item['title']} se usa en el curso con esta idea básica: {item['content']}"
        return answer
    if context.get("faq_support"):
        faq = context["faq_support"][0]
        return faq["content"]
    return (
        "No encontré base suficiente dentro del curso para responder eso con precisión académica. "
        "Si quieres, puedo intentar con otro término, con un módulo concreto o con una pregunta más específica."
    )


def _suggested_followups(query: str, context: dict[str, Any]) -> list[str]:
    concepts = context.get("main_concepts", [])
    if concepts:
        main = concepts[0]["title"]
        return [
            f"Explícame {main} más fácil",
            f"¿En qué módulo del curso se trabaja mejor {main}?",
            f"¿Cuál es la diferencia entre {main} y otro concepto relacionado?",
        ]
    modules = context.get("module_summaries", [])
    if modules:
        return [
            f"Desarrolla mejor {modules[0]['title']}",
            "Dame los temas clave de ese módulo",
        ]
    return [
        "Dame un glosario rápido de este curso",
        "Resume el tema como si fuera estudiante nuevo",
    ]


def generate_academic_answer(
    query: str,
    context: dict[str, Any],
    llm_client: AcademicLLMClient | None = None,
    response_mode: str = "fast",
) -> dict[str, Any]:
    llm = llm_client or AcademicLLMClient()
    messages = build_academic_prompt(query, context)
    llm_result = llm.complete(messages, response_mode=response_mode) if llm.enabled else {"text": "", "ok": False, "finish_reason": "disabled", "error": "llm_disabled"}
    answer = llm_result.get("text", "")
    used_fallback = False
    if (
        not answer
        or llm_result.get("finish_reason") == "length"
        or _response_looks_incomplete(answer)
    ):
        answer = _fallback_answer(query, context, concise=(response_mode == "fast"))
        used_fallback = True

    payload = AcademicAnswer(
        answer=answer,
        confidence=_infer_confidence(context),
        sources_used=context.get("citations", []),
        concepts_used=_extract_concepts_used(context),
        suggested_followups=_suggested_followups(query, context),
        retrieval_trace=context.get("retrieval_trace", []),
        context=context,
    )
    data = payload.to_dict()
    data["used_fallback"] = used_fallback
    data["mode_used"] = response_mode
    data["generation"] = {
        "provider_used": llm.provider if llm.enabled else "fallback_only",
        "model_used": llm.model if llm.enabled else "",
        "llm_finish_reason": llm_result.get("finish_reason", ""),
        "used_fallback": used_fallback,
        "llm_error": llm_result.get("error", ""),
    }
    return data
