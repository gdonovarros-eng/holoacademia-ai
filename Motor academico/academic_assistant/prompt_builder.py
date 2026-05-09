from __future__ import annotations

from typing import Any


ACADEMIC_SYSTEM_PROMPT = """
Eres el Asistente Académico de Holoacademia.

Habla como un profesor paciente y claro que está explicando en clase.

Tu trabajo es responder dudas académicas sobre conceptos, módulos, manuales y contenidos del curso.
Responde solo con base en el contexto proporcionado.

Límites estrictos:
- no inventes teoría ni detalles ausentes en el curso
- no mezcles razonamiento terapéutico, intake clínico ni protocolos de aplicación
- no guíes tratamientos ni resolución de casos clínicos
- si la base no alcanza, dilo con honestidad y sin rellenar huecos

Estilo de respuesta:
- explica primero en palabras simples
- usa un tono natural, humano y pedagógico
- responde en una extensión breve a media por defecto
- usa párrafos cortos
- evita listas largas salvo que de verdad ayuden
- evita tablas salvo que el usuario las pida
- no suenes enciclopédico, rígido ni artificial
- no uses tono médico o demasiado técnico a menos que el usuario lo pida
- si el usuario dice que va empezando, simplifica todavía más el lenguaje
- termina de forma natural, no robótica

Guía de estructura:
- si aplica, abre con una definición breve o una idea central
- luego desarrolla la explicación con claridad
- si ayuda, añade un ejemplo corto o una comparación natural
- si el usuario pregunta la diferencia entre dos conceptos, explica cada uno brevemente y luego marca la diferencia principal
- si el usuario pide un resumen, hazlo en párrafos cortos o viñetas breves, sin extenderte de más

Nunca menciones detalles internos del sistema ni nombres técnicos como JSON, retriever, chunks o fuentes internas.
""".strip()


def _render_entries(title: str, entries: list[dict[str, Any]]) -> str:
    if not entries:
        return ""
    lines = [title]
    for entry in entries:
        modulo = f" [{entry['modulo']}]" if entry.get("modulo") else ""
        lines.append(f"- {entry.get('title', entry.get('id', ''))}{modulo}: {entry.get('content', '')}")
    return "\n".join(lines)


def _format_history(history: list) -> str:
    if not history:
        return ""
    lines = []
    for item in history[-8:]:
        role = str(item.get("role", "user")).strip()
        content = str(item.get("content", "") or item.get("answer", "")).strip()
        if content:
            label = "Alumno" if role == "user" else "Asistente"
            lines.append(f"{label}: {content[:300]}")
    return "\n".join(lines)


def build_academic_prompt(query: str, context: dict[str, Any]) -> list[dict[str, str]]:
    intent_data = context.get("intent") or {}
    intent = intent_data.get("intent", "general_academic")
    response_mode = context.get("response_mode", "fast")
    blocks = [
        _render_entries("Conceptos principales:", context.get("main_concepts", [])),
        _render_entries("Glosario de apoyo:", context.get("supporting_glossary", [])),
        _render_entries("Resúmenes de módulo:", context.get("module_summaries", [])),
        _render_entries("Preguntas frecuentes útiles:", context.get("faq_support", [])),
    ]
    course_context = context.get("course_context") or {}
    if course_context.get("content"):
        blocks.append(
            "Contexto del curso:\n"
            f"- {course_context.get('title', 'Curso')}: {course_context.get('content', '')}"
        )

    if intent == "comparison":
        comparison_parts = []
        if context.get("concept_a"):
            comparison_parts.append(_render_entries("Concepto A:", [context["concept_a"]]))
        if context.get("concept_b"):
            comparison_parts.append(_render_entries("Concepto B:", [context["concept_b"]]))
        if context.get("comparison_notes"):
            comparison_parts.append("Notas para comparar:\n" + "\n".join(f"- {note}" for note in context["comparison_notes"]))
        blocks = comparison_parts + blocks
    elif intent in {"module_summary", "locate_in_course"} and context.get("module_summary"):
        blocks = [
            _render_entries("Módulo objetivo:", [context["module_summary"]]),
            "Temas de apoyo:\n" + "\n".join(f"- {topic}" for topic in context.get("supporting_topics", []))
            if context.get("supporting_topics") else "",
        ] + blocks

    intent_note = ""
    if intent == "comparison":
        intent_note = "La intención es comparativa: explica brevemente cada concepto y luego marca su diferencia principal."
    elif intent == "module_summary":
        intent_note = "La intención es resumir un módulo: prioriza el resumen del módulo y no te extiendas más de lo necesario."
    elif intent == "locate_in_course":
        intent_note = "La intención es ubicar un tema dentro del curso: responde dónde aparece o en qué parte se trabaja."
    elif intent == "simple_explanation" or intent_data.get("needs_simple_language"):
        intent_note = "La intención es una explicación simple: usa lenguaje todavía más claro y básico."

    mode_note = (
        "Modo fast: responde de forma breve a media, muy clara, sin rodeos y sin abrir demasiadas ramas."
        if response_mode == "fast"
        else "Modo deep: responde con más desarrollo y contexto útil, pero mantén la respuesta controlada y evita exagerar la longitud."
    )

    history_text = _format_history(context.get("history", []))
    user_content = (
        f"Pregunta del alumno:\n{query}\n\n"
        + (f"Conversación previa:\n{history_text}\n\n" if history_text else "")
        + f"Modo de respuesta:\n{mode_note}\n\n"
        + (f"Intención detectada:\n{intent_note}\n\n" if intent_note else "")
        + "Contexto académico disponible:\n"
        + "\n\n".join(block for block in blocks if block)
        + "\n\nResponde directamente para el alumno con una explicación clara, natural y moderadamente breve. "
          "Si hay conversación previa, mantén continuidad con lo que ya se explicó. "
          "Si la información no alcanza, indícalo con honestidad sin inventar."
    )
    return [
        {"role": "system", "content": ACADEMIC_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
