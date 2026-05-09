from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from .case_analyzer import build_case_analysis
from .intake_engine import analyze_case_intake
from .interpretation_engine import build_interpretation
from .loader import load_therapeutic_course_data
from .models import CaseInput, TherapeuticKnowledgeBase
from .reasoning_engine import generate_reasoning
from .response_builder import build_therapeutic_response

THERAPEUTIC_SYSTEM_PROMPT = """
Eres el Asistente Terapéutico de Holoacademia, experto en biomagnetismo, holobiomagnetismo y terapias holísticas.
Tu función es orientar al terapeuta para trabajar el caso con criterio clínico, basándote en los protocolos y patrones del curso.

Reglas:
- Responde siempre desde los protocolos y conocimiento del curso, no desde supuestos genéricos.
- Sé concreto: indica qué protocolo abrir, por qué, qué validar primero y qué pregunta hacer al paciente.
- Usa lenguaje clínico pero accesible para un terapeuta formado.
- Estructura la respuesta en 3-4 bloques cortos: lectura del caso, ruta recomendada, protocolo principal, preguntas clave.
- No diagnostiques enfermedades ni sustituyas atención médica.
- Si faltan datos, indícalo y sugiere qué información específica completar.
""".strip()


def _build_genogram_resolution(case_input: Dict[str, Any]) -> Dict[str, Any]:
    family_notes = str(case_input.get("family_notes", "") or "").lower()
    context = str(case_input.get("contexto_emocional", "") or "").lower()
    antecedentes = " ".join(str(a) for a in (case_input.get("antecedentes") or [])).lower()
    full_text = f"{family_notes} {context} {antecedentes}"

    if not full_text.strip():
        return {}

    materna_tokens = {"madre", "mama", "mamá", "abuela materna", "linea materna", "línea materna", "tia", "tía", "hermana", "hija"}
    paterna_tokens = {"padre", "papa", "papá", "abuelo paterno", "linea paterna", "línea paterna", "tio", "tío", "hermano", "hijo"}
    infancia_tokens = {"infancia", "niñez", "niño", "niña", "escuela", "abuso", "maltrato", "abandono", "crianza", "adoptado", "adoptada"}

    scores = {"materna": 0, "paterna": 0, "infancia": 0}
    signals: list[str] = []

    for token in materna_tokens:
        if token in full_text:
            scores["materna"] += 1
            signals.append(f"referencia materna: {token}")
    for token in paterna_tokens:
        if token in full_text:
            scores["paterna"] += 1
            signals.append(f"referencia paterna: {token}")
    for token in infancia_tokens:
        if token in full_text:
            scores["infancia"] += 1
            signals.append(f"referencia infancia: {token}")

    if all(v == 0 for v in scores.values()):
        return {}

    dominant_axis = max(scores, key=lambda k: scores[k])
    labels = {
        "materna": "función materna",
        "paterna": "función paterna",
        "infancia": "herida de infancia",
    }
    repairs = {
        "materna": "reparar el vínculo con la figura materna o su linaje",
        "paterna": "reparar el vínculo con la figura paterna o su linaje",
        "infancia": "integrar y liberar la herida de infancia",
    }
    interview_focuses = {
        "materna": "explorar figuras maternas: madre, abuelas, tías y su historia de vida",
        "paterna": "explorar figuras paternas: padre, abuelos, tíos y su historia de vida",
        "infancia": "explorar experiencias tempranas, crianza y eventos significativos de la infancia",
    }
    dominant_label = labels[dominant_axis]
    summary = f"El genograma abre primero por {dominant_label}."
    if scores[dominant_axis] < 2:
        summary = "El genograma tiene señales iniciales pero conviene profundizar antes de cerrar hipótesis."

    return {
        "dominant_axis": dominant_axis,
        "dominant_label": dominant_label,
        "repair_target": repairs[dominant_axis],
        "interview_focus": interview_focuses[dominant_axis],
        "summary": summary,
        "supporting_signals": signals[:4],
        "scores": scores,
    }


class TherapeuticLLMClient:
    def __init__(self) -> None:
        self.use_model = os.getenv("THERAPEUTIC_ASSISTANT_USE_MODEL", "false").strip().lower() in {"1", "true", "yes", "on"}
        provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY", "").strip()
            base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").strip()
            model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b").strip()
        else:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            base_url = os.getenv("LLM_BASE_URL", "").strip() or None
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.model = model
        self.base_url = base_url
        self.enabled = bool(self.use_model and api_key and OpenAI is not None)
        self.client = None
        if self.enabled:
            kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = OpenAI(**kwargs)

    def generate_answer(self, case_summary: str, structured_data: dict[str, Any]) -> str:
        if not self.enabled or self.client is None:
            return ""
        protocols = structured_data.get("protocolo_principal", {})
        protocol_name = protocols.get("nombre", "") if isinstance(protocols, dict) else ""
        protocol_why = protocols.get("por_que", "") if isinstance(protocols, dict) else ""
        protocol_goal = protocols.get("que_busca_resolver", "") if isinstance(protocols, dict) else ""
        validaciones = "; ".join(structured_data.get("validaciones_clave", [])[:4])
        preguntas = "; ".join(structured_data.get("priority_questions", [])[:4])
        ruta = structured_data.get("ruta_principal", "")
        accion = structured_data.get("accion_inmediata", "")
        pasos = "; ".join(structured_data.get("pasos_inmediatos", [])[:4])

        prompt = (
            f"Datos del caso:\n{case_summary}\n\n"
            f"Análisis estructurado del motor:\n"
            f"- Ruta principal: {ruta}\n"
            f"- Acción inmediata: {accion}\n"
            f"- Protocolo principal: {protocol_name} — {protocol_why} — objetivo: {protocol_goal}\n"
            f"- Validaciones clave: {validaciones}\n"
            f"- Preguntas prioritarias: {preguntas}\n"
            f"- Pasos inmediatos: {pasos}\n\n"
            "Con base en los protocolos del curso y los datos anteriores, escribe una orientación terapéutica clara y práctica para el terapeuta. "
            "Estructura: 1) lectura breve del caso, 2) ruta y protocolo recomendado con sus pasos principales, "
            "3) qué validar primero, 4) 2-3 preguntas clave para hacer al paciente."
        )
        try:
            resp = self.client.responses.create(
                model=self.model,
                instructions=THERAPEUTIC_SYSTEM_PROMPT,
                input=prompt,
                max_output_tokens=int(os.getenv("THERAPEUTIC_ASSISTANT_MAX_TOKENS", "800")),
                timeout=float(os.getenv("THERAPEUTIC_ASSISTANT_TIMEOUT_SECONDS", "25")),
            )
            text = getattr(resp, "output_text", "") or ""
            if not text.strip():
                for item in getattr(resp, "output", []) or []:
                    for content in getattr(item, "content", []) or []:
                        value = getattr(content, "text", None)
                        if value:
                            text += value
            return text.strip()
        except Exception:
            return ""


class TherapeuticAssistantService:
    def __init__(self, course_dir: Optional[Union[str, Path]] = None) -> None:
        self.knowledge: TherapeuticKnowledgeBase = load_therapeutic_course_data(course_dir)
        self.llm = TherapeuticLLMClient()

    def answer_therapeutic_query(self, case_input: Dict[str, Any]) -> Dict[str, Any]:
        normalized_case = CaseInput.from_dict(case_input)
        if not any(normalized_case.to_text_fragments()):
            return {
                "answer": "Todavía no tengo suficiente información del caso para ayudarte a ordenarlo. Si me compartes al menos el motivo de consulta, síntomas o una pregunta clínica concreta, ya puedo empezar a orientarte mejor.",
                "confidence": "low",
                "entrevista_base": {
                    "id": "entrevista_inicial_de_rastreo",
                    "nombre": "Entrevista inicial de rastreo",
                    "objetivo": "Convertir la queja del paciente en información clínica operable para rastreo e interpretación.",
                    "preguntas_clave": [
                        "¿Qué síntomas quiere trabajar hoy?",
                        "¿Cómo es exactamente el síntoma: dónde está, cómo duele o cómo se siente?",
                        "¿Desde cuándo empezó, aunque sea de forma aproximada?",
                    ],
                },
                "ruta_principal": "completar primero entrevista y cronología básica",
                "lectura_inicial": "Todavía no hay base suficiente para abrir el caso con criterio.",
                "puerta_principal": {},
                "ruta_sugerida": "Después de la entrevista base, completar síntoma, frecuencia e inicio antes de abrir otro protocolo.",
                "accion_inmediata": "aclarar motivo de consulta y síntoma principal",
                "evidencias_principales": [
                    "Todavía no hay un síntoma eje descrito con forma suficiente.",
                    "Falta cronología básica para elegir una ruta terapéutica con criterio.",
                    "Sin contexto clínico mínimo no conviene abrir protocolos mayores.",
                ],
                "validaciones_clave": [
                    "motivo de consulta principal",
                    "síntoma descrito en palabras simples",
                    "inicio aproximado del cuadro",
                ],
                "protocolo_principal": {},
                "protocolo_sugerido": {},
                "herramientas_clave": [
                    {
                        "id": "entrevista_inicial",
                        "tipo": "protocolo",
                        "nombre": "Entrevista inicial de rastreo",
                        "orden": 1,
                        "por_que": "sin base mínima no conviene abrir protocolos mayores",
                        "que_valida": ["motivo de consulta", "síntoma principal", "inicio aproximado"],
                        "que_hacer_despues": "Si aparece una puerta clara, recién ahí define la siguiente herramienta.",
                    }
                ],
                "herramientas_relevantes": [
                    {
                        "id": "entrevista_inicial",
                        "tipo": "protocolo",
                        "nombre": "Entrevista inicial de rastreo",
                        "orden": 1,
                        "por_que": "sin base mínima no conviene abrir protocolos mayores",
                        "que_valida": ["motivo de consulta", "síntoma principal", "inicio aproximado"],
                        "que_hacer_despues": "Si aparece una puerta clara, recién ahí define la siguiente herramienta.",
                    }
                ],
                "pasos_inmediatos": [
                    "aclarar motivo de consulta",
                    "describir síntoma en palabras simples",
                    "ubicar inicio aproximado",
                ],
                "punto_de_decision": "Si después de esto aparece una puerta clara, recién ahí conviene abrir protocolo.",
                "si_no_confirma": "Si sigue sin aparecer una puerta clara, mantén entrevista y no abras hipótesis amplias.",
                "preguntas_clave": [
                    "¿Qué síntomas quiere trabajar hoy?",
                    "¿Cómo es exactamente el síntoma: dónde está, cómo duele o cómo se siente?",
                    "¿Desde cuándo empezó, aunque sea de forma aproximada?",
                ],
                "limites": [
                    "Sin motivo de consulta y cronología básica no conviene abrir hipótesis amplias.",
                ],
                "missing_data": [
                    "motivo de consulta",
                    "síntomas",
                    "cronología básica del cuadro",
                ],
                "priority_questions": [
                    "¿Qué síntomas quiere trabajar hoy?",
                    "¿Cómo es exactamente el síntoma: dónde está, cómo duele o cómo se siente?",
                    "¿Desde cuándo empezó, aunque sea de forma aproximada?",
                ],
                "possible_lines": [],
                "warnings": [],
                "used_patterns": [],
                "used_guides": [],
                "trace": {"warnings": self.knowledge.warnings},
                "course_id": self.knowledge.course_id,
                "course_line": self.knowledge.line,
            }

        intake_output = analyze_case_intake(normalized_case, self.knowledge)
        case_analysis = build_case_analysis(normalized_case)
        reasoning_output = generate_reasoning(case_analysis, self.knowledge, normalized_case)
        interpretation_output = build_interpretation(case_analysis, reasoning_output, self.knowledge)
        response = build_therapeutic_response(
            case_input=case_input,
            case_analysis=case_analysis,
            intake_output=intake_output,
            reasoning_output=reasoning_output,
            interpretation_output=interpretation_output,
        )
        response["course_id"] = self.knowledge.course_id
        response["course_line"] = self.knowledge.line
        response["warnings_from_loader"] = self.knowledge.warnings

        if self.llm.enabled:
            case_fragments = normalized_case.to_text_fragments()
            case_summary = "\n".join(f"- {f}" for f in case_fragments if f.strip()) or "Sin datos suficientes"
            llm_answer = self.llm.generate_answer(case_summary, response)
            if llm_answer:
                response["answer"] = llm_answer

        genogram_resolution = _build_genogram_resolution(case_input)
        if genogram_resolution:
            response["genogram_resolution"] = genogram_resolution

        return response


def answer_therapeutic_query(case_input: Dict[str, Any], course_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    service = TherapeuticAssistantService(course_dir=course_dir)
    return service.answer_therapeutic_query(case_input)
