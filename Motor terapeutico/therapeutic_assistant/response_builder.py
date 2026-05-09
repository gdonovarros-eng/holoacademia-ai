from __future__ import annotations

from typing import Any, Dict, List

from .models import TherapeuticResponse


def _question_texts(questions: List[Dict[str, Any]]) -> List[str]:
    return [str(item.get("pregunta", "")).strip() for item in questions if str(item.get("pregunta", "")).strip()]


def _dedupe(items: List[str], limit: int) -> List[str]:
    seen: Dict[str, None] = {}
    for item in items:
        value = str(item or "").strip()
        if value and value not in seen:
            seen[value] = None
        if len(seen) >= limit:
            break
    return list(seen.keys())


def _clean_text(value: str) -> str:
    text = " ".join(str(value or "").strip().split())
    return text.rstrip(" .!?,;:")


def _lowercase_first(value: str) -> str:
    cleaned = _clean_text(value)
    if len(cleaned) <= 1:
        return cleaned.lower()
    return cleaned[0].lower() + cleaned[1:]


def _protocol_payload(reasoning_output: Dict[str, Any]) -> Dict[str, Any]:
    protocols = reasoning_output.get("protocolos_sugeridos", [])
    if not isinstance(protocols, list) or not protocols:
        return {}
    principal = protocols[0] if isinstance(protocols[0], dict) else {}
    alterno = protocols[1] if len(protocols) > 1 and isinstance(protocols[1], dict) else {}
    payload = {"principal": principal}
    if alterno:
        payload["alterno"] = alterno
    return payload


def _friendly_trace_evidence(reasoning_trace: List[Dict[str, Any]]) -> List[str]:
    friendly: List[str] = []
    if not reasoning_trace:
        return friendly

    first_trace = reasoning_trace[0] if isinstance(reasoning_trace[0], dict) else {}
    for item in first_trace.get("evidence", []):
        evidence = str(item or "").strip().lower()
        if evidence == "heuristica:recurrencia":
            friendly.append("El cuadro se describe como recurrente o de repetición.")
        elif evidence == "heuristica:cronologia":
            friendly.append("Sí hay una cronología o un inicio que permite ordenar mejor la apertura.")
        elif evidence == "heuristica:emocional":
            friendly.append("El caso trae un componente emocional o conflictivo referido de forma explícita.")
        elif evidence == "heuristica:busqueda_ordenada":
            friendly.append("La consulta ya apunta a rastreo por microbios, pares o una búsqueda ordenada.")
        elif evidence == "heuristica:impacto_emocional":
            friendly.append("La narrativa del caso sugiere abrir por impacto emocional antes de ampliar otras rutas.")
        elif evidence == "heuristica:meridianos":
            friendly.append("La pregunta clínica ya está orientada a revisar canales o meridianos.")
        elif evidence.startswith("trigger:"):
            terms = evidence.split(":", 1)[1].replace(",", ", ")
            friendly.append(f"El patrón del curso coincide con términos clave del caso: {terms}.")
    return friendly


def _build_evidence_list(
    case_analysis: Dict[str, Any],
    reasoning_output: Dict[str, Any],
) -> List[str]:
    evidences: List[str] = []
    symptoms = [str(item).strip() for item in case_analysis.get("symptoms_detected", []) if str(item).strip()]
    if symptoms:
        evidences.append("Síntoma eje referido: " + ", ".join(symptoms[:2]) + ".")

    timeline = [str(item).strip() for item in case_analysis.get("timeline_elements", []) if str(item).strip()]
    if timeline:
        evidences.append("La cronología ya aporta datos útiles: " + " | ".join(timeline[:2]) + ".")

    contexts = [str(item).strip() for item in case_analysis.get("context_elements", []) if str(item).strip()]
    if contexts:
        evidences.append("Hay contexto o antecedentes que orientan la lectura: " + "; ".join(contexts[:2]) + ".")

    puerta = reasoning_output.get("puerta_principal", {}) if isinstance(reasoning_output.get("puerta_principal", {}), dict) else {}
    if puerta.get("por_que"):
        evidences.append("La puerta principal se sostuvo porque " + _lowercase_first(str(puerta.get("por_que", ""))) + ".")

    evidences.extend(_friendly_trace_evidence(list(reasoning_output.get("reasoning_trace", []))))
    return _dedupe(evidences, 4)


def _tool_sequence_text(herramientas: List[Dict[str, Any]]) -> List[str]:
    sequence: List[str] = []
    for tool in herramientas[:3]:
        if not isinstance(tool, dict):
            continue
        nombre = _clean_text(tool.get("nombre", "esta herramienta"))
        por_que = _clean_text(tool.get("por_que", ""))
        if por_que:
            sequence.append(f"usar {nombre} porque {por_que[0].lower() + por_que[1:] if len(por_que) > 1 else por_que.lower()}")
        else:
            sequence.append(f"usar {nombre}")
    return _dedupe(sequence, 3)


def _build_answer(
    ruta_principal: str,
    accion_inmediata: str,
    evidencias_principales: List[str],
    validaciones_clave: List[str],
    protocolo_sugerido: Dict[str, Any],
    pasos_inmediatos: List[str],
    punto_de_decision: str,
    si_no_confirma: str,
) -> str:
    parts: List[str] = []

    if ruta_principal:
        route_text = _clean_text(ruta_principal)
        if route_text.lower().startswith("abrir primero por"):
            parts.append(f"Con lo que compartes, la ruta principal sería: {route_text}.")
        else:
            parts.append(f"Con lo que compartes, abriría primero por {route_text[0].lower() + route_text[1:] if len(route_text) > 1 else route_text.lower()}.")

    if accion_inmediata:
        parts.append(f"Lo primero que conviene hacer es {accion_inmediata}.")

    if evidencias_principales:
        parts.append("Esto se sostiene por: " + "; ".join(evidencias_principales[:3]) + ".")

    if validaciones_clave:
        parts.append("Valida primero: " + "; ".join(validaciones_clave[:3]) + ".")

    principal = protocolo_sugerido.get("principal", {}) if isinstance(protocolo_sugerido, dict) else {}
    if principal:
        protocol_name = _clean_text(principal.get("nombre", "el protocolo principal"))
        protocol_why = _clean_text(principal.get("por_que", ""))
        protocol_goal = _clean_text(principal.get("que_busca_resolver", ""))
        sentence = f"Si esto se confirma, sigue con {protocol_name}"
        if protocol_why:
            sentence += f" porque {_lowercase_first(protocol_why)}"
        sentence += "."
        parts.append(sentence)
        if protocol_goal:
            parts.append(f"Lo usaría para {_lowercase_first(protocol_goal)}.")

    if punto_de_decision:
        parts.append(_clean_text(punto_de_decision) + ".")
    if si_no_confirma:
        parts.append(_clean_text(si_no_confirma) + ".")

    if not parts and pasos_inmediatos:
        parts.append("Con la base actual, yo ordenaría el caso así: " + "; ".join(pasos_inmediatos[:3]) + ".")

    return "\n\n".join(part for part in parts if part.strip())


def build_therapeutic_response(
    case_input: dict[str, Any],
    case_analysis: dict[str, Any],
    intake_output: dict[str, Any],
    reasoning_output: dict[str, Any],
    interpretation_output: dict[str, Any],
) -> Dict[str, Any]:
    del case_input

    confidence = str(reasoning_output.get("confidence", "low"))
    entrevista_base = dict(reasoning_output.get("entrevista_base", {}))
    missing_data = _dedupe(list(intake_output.get("missing_data", [])) + list(case_analysis.get("missing_elements", [])), 4)
    intake_priority = _question_texts(intake_output.get("priority_questions", []))
    route_validations = list(reasoning_output.get("validaciones_clave", []))
    validaciones_clave = _dedupe(route_validations + intake_priority, 4)

    ruta_principal = _clean_text(str(reasoning_output.get("ruta_principal", "")))
    ruta_sugerida = _clean_text(str(reasoning_output.get("ruta_sugerida", "")))
    accion_inmediata = _clean_text(str(reasoning_output.get("accion_inmediata", "")))
    pasos_inmediatos = _dedupe(list(reasoning_output.get("pasos_inmediatos", [])), 6)
    punto_de_decision = _clean_text(str(reasoning_output.get("punto_de_decision", "")))
    si_no_confirma = _clean_text(str(reasoning_output.get("si_no_confirma", "")))
    protocolo_sugerido = _protocol_payload(reasoning_output)
    herramientas_relevantes = list(reasoning_output.get("herramientas_relevantes", []))
    evidencias_principales = _build_evidence_list(case_analysis, reasoning_output)

    limits = _dedupe(list(interpretation_output.get("limits_of_interpretation", [])), 2)
    warnings = [
        item.get("advertencia", "")
        for item in interpretation_output.get("warnings", [])
        if isinstance(item, dict) and item.get("advertencia")
    ]
    warnings = _dedupe(warnings, 2)

    if not ruta_principal and missing_data:
        ruta_principal = "completar primero entrevista y cronología básica"
        ruta_sugerida = "Después de la entrevista base, volver a delimitar síntoma y cronología antes de abrir un protocolo específico."
        accion_inmediata = accion_inmediata or "aterrizar el síntoma en sensación, lugar, inicio y frecuencia"
        validaciones_clave = _dedupe(validaciones_clave + missing_data, 4)
        evidencias_principales = _dedupe(
            evidencias_principales
            + [
                "Todavía no hay síntomas descritos con suficiente forma clínica." if not case_analysis.get("symptoms_detected") else "",
                "La cronología sigue incompleta y eso limita la elección del protocolo." if not case_analysis.get("timeline_elements") else "",
                "Falta contexto emocional o detonante para sostener una ruta más precisa." if not case_analysis.get("context_elements") else "",
            ],
            3,
        )
        pasos_inmediatos = _dedupe(
            pasos_inmediatos
            + [accion_inmediata, "confirmar inicio aproximado", "confirmar frecuencia real del cuadro"],
            6,
        )
        punto_de_decision = punto_de_decision or "Si al completar entrevista aparece un patrón claro, recién ahí conviene abrir protocolo."
        si_no_confirma = si_no_confirma or "Si sigue sin aparecer una puerta clara, mantén la entrevista y evita abrir hipótesis mayores."

    answer = _build_answer(
        ruta_principal=ruta_principal,
        accion_inmediata=accion_inmediata,
        evidencias_principales=evidencias_principales,
        validaciones_clave=validaciones_clave,
        protocolo_sugerido=protocolo_sugerido,
        pasos_inmediatos=pasos_inmediatos,
        punto_de_decision=punto_de_decision,
        si_no_confirma=si_no_confirma,
    )

    tool_sequence = _tool_sequence_text(herramientas_relevantes)
    if tool_sequence:
        answer += "\n\nSecuencia sugerida: " + "; ".join(tool_sequence) + "."

    used_patterns = [item.get("id", "") for item in reasoning_output.get("matched_patterns", []) if isinstance(item, dict) and item.get("id")]
    used_guides = [item.get("id", "") for item in interpretation_output.get("relevant_guides", []) if isinstance(item, dict) and item.get("id")]

    return TherapeuticResponse(
        answer=answer,
        confidence=confidence,
        entrevista_base={
            "id": entrevista_base.get("id", "entrevista_inicial_de_rastreo"),
            "nombre": entrevista_base.get("nombre", "Entrevista inicial de rastreo"),
            "objetivo": entrevista_base.get("objetivo", "Convertir la queja del paciente en información clínica operable."),
            "preguntas_clave": list(entrevista_base.get("preguntas_clave", []))[:5],
        },
        ruta_principal=ruta_principal,
        lectura_inicial=answer.split("\n\n")[0] if answer else "",
        puerta_principal=dict(reasoning_output.get("puerta_principal", {})),
        ruta_sugerida=ruta_sugerida,
        accion_inmediata=accion_inmediata,
        evidencias_principales=evidencias_principales[:4],
        validaciones_clave=validaciones_clave[:4],
        protocolo_principal=dict(protocolo_sugerido.get("principal", {})),
        protocolo_sugerido=protocolo_sugerido,
        herramientas_clave=herramientas_relevantes[:4],
        herramientas_relevantes=herramientas_relevantes[:4],
        pasos_inmediatos=pasos_inmediatos[:6],
        punto_de_decision=punto_de_decision,
        si_no_confirma=si_no_confirma,
        preguntas_clave=validaciones_clave[:4],
        limites=limits,
        missing_data=missing_data,
        priority_questions=validaciones_clave[:4],
        possible_lines=[ruta_principal] if ruta_principal else [],
        warnings=warnings,
        used_patterns=used_patterns[:2],
        used_guides=used_guides[:1],
        trace={
            "intake_matches": intake_output.get("intake_trace", []),
            "pattern_matches": reasoning_output.get("reasoning_trace", []),
            "guide_matches": interpretation_output.get("interpretation_trace", []),
            "warning_matches": interpretation_output.get("warnings", []),
            "analysis_trace": case_analysis.get("analysis_trace", []),
        },
    ).to_dict()
