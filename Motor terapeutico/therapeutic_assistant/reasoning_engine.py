from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from .models import CaseAnalysis, CaseInput, ReasoningOutput, TherapeuticKnowledgeBase


STOPWORDS = {
    "de",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "y",
    "o",
    "que",
    "del",
    "al",
    "por",
    "con",
    "en",
    "para",
    "se",
    "lo",
    "como",
}


ENTITY_HINTS = {
    "microorganismos_patogenos": {
        "keywords": ["microbio", "microbios", "patogeno", "patógeno", "infeccion", "infección", "virus", "bacteria", "hongo", "parásito", "parasito"],
        "protocol_ids": ["rastreo_de_microorganismos_y_pares_biomagneticos"],
        "pattern_ids": ["patron_busqueda_ordenada"],
    },
    "par_biomagnetico": {
        "keywords": ["par biomagnetico", "par biomagnético", "pares", "pares biomagneticos", "pares biomagnéticos"],
        "protocol_ids": ["rastreo_de_microorganismos_y_pares_biomagneticos", "rastreo_y_desarticulacion_de_impacto_emocional"],
        "pattern_ids": ["patron_busqueda_ordenada"],
    },
    "chakras": {
        "keywords": ["chakra", "chakras"],
        "protocol_ids": ["rastreo_y_desarticulacion_de_impacto_emocional"],
        "pattern_ids": ["patron_conflicto_emocional"],
    },
    "meridianos": {
        "keywords": ["meridiano", "meridianos"],
        "protocol_ids": ["rastreo_y_desarticulacion_de_impacto_emocional", "rastreo_de_5_elementos_global", "eft_pro"],
        "pattern_ids": ["patron_canal_exceso", "patron_conflicto_emocional"],
    },
    "molde_energetico": {
        "keywords": ["cirugia", "cirugía", "organo", "órgano"],
        "protocol_ids": ["rastreo_holobiomagnetico_condensado"],
        "pattern_ids": ["patron_molde_organico"],
    },
}


def _tokenize(text: str) -> set:
    return {
        token
        for token in re.findall(r"[a-záéíóúñ]+", (text or "").lower())
        if token not in STOPWORDS and len(token) > 2
    }


def _contains_keyword(text: str, keywords: List[str]) -> bool:
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in keywords)


def _pattern_score(pattern: Any, bag: set, symptom_text: str) -> Tuple[float, List[str]]:
    evidence: List[str] = []
    score = 0.0
    trigger_tokens = _tokenize(pattern.trigger)
    matched_trigger = sorted(trigger_tokens & bag)
    if matched_trigger:
        score += min(len(matched_trigger) * 0.8, 2.4)
        evidence.append(f"trigger:{', '.join(matched_trigger[:4])}")

    observe_tokens = _tokenize(" ".join(pattern.que_observar))
    matched_observe = sorted(observe_tokens & bag)
    if matched_observe:
        score += min(len(matched_observe) * 0.45, 1.6)
        evidence.append(f"observa:{', '.join(matched_observe[:4])}")

    question_tokens = _tokenize(" ".join(pattern.preguntas_clave))
    matched_questions = sorted(question_tokens & bag)
    if matched_questions:
        score += min(len(matched_questions) * 0.35, 1.1)
        evidence.append(f"preguntas:{', '.join(matched_questions[:4])}")

    if pattern.id.endswith("recurrencia") and any(token in symptom_text for token in ("recur", "cada", "episodio", "vuelve")):
        score += 1.4
        evidence.append("heuristica:recurrencia")
    if "origen" in pattern.id and any(token in symptom_text for token in ("desde", "empez", "inicio")):
        score += 1.2
        evidence.append("heuristica:cronologia")
    if "emocion" in pattern.id or "conflicto" in pattern.id or "qi_" in pattern.id:
        if any(token in symptom_text for token in ("miedo", "enojo", "triste", "ansiedad", "conflicto", "emoc")):
            score += 1.2
            evidence.append("heuristica:emocional")
    if pattern.id == "patron_busqueda_ordenada" and any(
        token in symptom_text
        for token in ("microbio", "microbios", "patogeno", "patógeno", "pares", "par biomagn", "frecuencia")
    ):
        score += 2.4
        evidence.append("heuristica:busqueda_ordenada")
    if pattern.id == "patron_conflicto_emocional" and any(
        token in symptom_text
        for token in ("impacto emocional", "conflicto", "chakra", "chakras", "persona implicada", "meridiano", "meridianos")
    ):
        score += 2.1
        evidence.append("heuristica:impacto_emocional")
    if pattern.id == "patron_canal_exceso" and any(
        token in symptom_text for token in ("meridiano", "meridianos", "canal")
    ):
        score += 2.0
        evidence.append("heuristica:meridianos")

    return score, evidence


def _dedupe_preserve(items: List[str], limit: int) -> List[str]:
    seen: Dict[str, None] = {}
    for item in items:
        value = str(item or "").strip()
        if value and value not in seen:
            seen[value] = None
        if len(seen) >= limit:
            break
    return list(seen.keys())


def _build_protocol_index(protocols: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for protocol in protocols:
        protocol_id = str(protocol.get("id", "")).strip()
        if protocol_id:
            index[protocol_id] = protocol
    return index


def _build_structured_protocol_index(protocols: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for protocol in protocols:
        protocol_id = str(protocol.get("id", "")).strip()
        if protocol_id:
            index[protocol_id] = protocol
    return index


def _build_concept_index(concepts: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for concept in concepts:
        concept_id = str(concept.get("id", "")).strip()
        if concept_id:
            index[concept_id] = concept
    return index


def _protocol_hint(
    protocol_id: str,
    protocol_index: Dict[str, Dict[str, Any]],
    structured_protocol_index: Dict[str, Dict[str, Any]],
    why: str,
) -> Dict[str, Any]:
    protocol = protocol_index.get(protocol_id, {})
    structured = structured_protocol_index.get(protocol_id, {})
    steps = protocol.get("pasos", []) if isinstance(protocol.get("pasos"), list) else []
    primeros_pasos: List[str] = []
    for step in steps[:2]:
        if not isinstance(step, dict):
            continue
        title = str(step.get("titulo", "")).strip()
        instruction = str(step.get("instruccion", "")).strip()
        if title and instruction:
            primeros_pasos.append(f"{title}: {instruction}")
        elif instruction:
            primeros_pasos.append(instruction)
    return {
        "id": protocol_id,
        "nombre": str(structured.get("nombre") or protocol.get("nombre", protocol_id.replace("_", " "))).strip(),
        "tipo": str(structured.get("tipo", "")).strip(),
        "por_que": why.strip(),
        "cuando_abrirlo": _dedupe_preserve([*structured.get("cuando_abrirlo", []), *protocol.get("cuando_usarlo", []), *protocol.get("observaciones", [])], 3),
        "que_busca_resolver": str(structured.get("objetivo") or protocol.get("objetivo") or protocol.get("descripcion") or "").strip(),
        "validaciones": _dedupe_preserve(structured.get("validaciones", []), 4),
        "preguntas_clave": _dedupe_preserve(structured.get("preguntas_clave", []), 4),
        "pares_prioritarios": _dedupe_preserve(structured.get("pares_prioritarios", []), 3),
        "microbios_relacionados": _dedupe_preserve(structured.get("microbios_relacionados", []), 2),
        "chakras_relacionados": _dedupe_preserve(structured.get("chakras_relacionados", []), 2),
        "datos_previos_necesarios": _dedupe_preserve(structured.get("datos_previos_necesarios", []), 4),
        "si_confirma": str(structured.get("si_confirma", "")).strip(),
        "si_no_confirma": str(structured.get("si_no_confirma", "")).strip(),
        "protocolo_siguiente": list(structured.get("protocolo_siguiente", []))[:2],
        "primeros_pasos": _dedupe_preserve(primeros_pasos, 2),
        "pasos": steps[:5],
    }


def _top_observation_note(knowledge: TherapeuticKnowledgeBase, bag: set) -> str:
    for observation in knowledge.therapeutic_observations:
        obs_tokens = _tokenize(f"{observation.observacion} {observation.utilidad_terapeutica}")
        if obs_tokens & bag:
            return observation.observacion.strip()
    return ""


def _build_primary_door(
    top_pattern: Dict[str, Any],
    observation_note: str,
) -> Dict[str, Any]:
    trigger = str(top_pattern.get("trigger", "")).strip()
    interpretacion = str(top_pattern.get("interpretacion", "")).strip()
    acciones = list(top_pattern.get("acciones_sugeridas", []))
    observaciones = list(top_pattern.get("que_observar", []))

    return {
        "id": str(top_pattern.get("id", "")).strip(),
        "titulo": trigger or "Apertura inicial del caso",
        "por_que": interpretacion or trigger,
        "que_revisar": _dedupe_preserve(acciones + observaciones + ([observation_note] if observation_note else []), 3),
    }


def _clean_text(value: str) -> str:
    text = str(value or "").strip()
    return text.rstrip(" .!?,;:")


def _build_route_statement(top_pattern: Dict[str, Any], puerta_principal: Dict[str, Any]) -> str:
    titulo = _clean_text(str(puerta_principal.get("titulo", "")))
    por_que = _clean_text(str(puerta_principal.get("por_que", "")))
    if titulo and por_que:
        return f"Abrir primero por {titulo.lower()}, porque {por_que[0].lower() + por_que[1:] if len(por_que) > 1 else por_que.lower()}."
    if titulo:
        return f"Abrir primero por {titulo.lower()}."
    trigger = _clean_text(str(top_pattern.get('trigger', 'la puerta principal del caso')))
    return f"Abrir primero por {trigger.lower()}."


def _build_steps(
    accion_inmediata: str,
    validaciones_clave: List[str],
    protocolos_sugeridos: List[Dict[str, Any]],
) -> List[str]:
    steps: List[str] = []
    if accion_inmediata:
        steps.append(accion_inmediata)
    for item in validaciones_clave[:3]:
        steps.append(f"validar: {item}")
    if protocolos_sugeridos:
        principal = protocolos_sugeridos[0]
        steps.append(f"si confirma, abrir {principal.get('nombre', 'el protocolo principal')}")
        for protocol_step in principal.get("primeros_pasos", [])[:1]:
            steps.append(protocol_step)
    if len(protocolos_sugeridos) > 1:
        alterno = protocolos_sugeridos[1]
        steps.append(f"si la primera ruta no sostiene, considerar {alterno.get('nombre', 'el protocolo alterno')}")
    return _dedupe_preserve(steps, 5)


def _entity_tool(entity_id: str, tipo: str, nombre: str, why: str, order: int) -> Dict[str, Any]:
    return {
        "id": entity_id,
        "tipo": tipo,
        "nombre": nombre,
        "orden": order,
        "por_que": _clean_text(why),
        "que_valida": [],
        "que_hacer_despues": "Si esta herramienta confirma la ruta, continúa con el siguiente paso del protocolo principal.",
    }


def _concept_tool(
    concept_id: str,
    concept_index: Dict[str, Dict[str, Any]],
    why: str,
    order: int,
) -> Dict[str, Any]:
    concept = concept_index.get(concept_id, {})
    name = str(concept.get("termino") or concept_id.replace("_", " ")).strip()
    module = str(concept.get("modulo", "")).strip()
    validations = list(concept.get("aliases", []))
    if concept.get("cuando_se_aplica"):
        validations.append(str(concept.get("cuando_se_aplica", "")).strip())
    return {
        "id": concept_id,
        "tipo": "concepto",
        "nombre": name,
        "orden": order,
        "por_que": _clean_text(why),
        "que_valida": _dedupe_preserve(validations, 2),
        "que_hacer_despues": f"Si esta herramienta orienta bien, úsala para sostener la apertura del caso{f' en {module}' if module else ''}.",
    }


def _protocol_tool(protocol_hint: Dict[str, Any], order: int) -> Dict[str, Any]:
    return {
        "id": str(protocol_hint.get("id", "")).strip(),
        "tipo": "protocolo",
        "nombre": str(protocol_hint.get("nombre", "")).strip(),
        "orden": order,
        "por_que": str(protocol_hint.get("por_que", "")).strip(),
        "que_valida": list(protocol_hint.get("cuando_abrirlo", []))[:2],
        "que_hacer_despues": (
            f"Después sigue con {protocol_hint.get('primeros_pasos', [])[0]}"
            if protocol_hint.get("primeros_pasos")
            else "Después continúa con el siguiente paso del protocolo."
        ),
    }


def _build_tools_sequence(
    top_pattern: Dict[str, Any],
    protocolos_sugeridos: List[Dict[str, Any]],
    concept_index: Dict[str, Dict[str, Any]],
    case_text: str,
) -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = []
    order = 1
    if protocolos_sugeridos:
        tools.append(_protocol_tool(protocolos_sugeridos[0], order))
        order += 1
        principal = protocolos_sugeridos[0]
        entity_stream: List[Dict[str, str]] = []
        if principal.get("pares_prioritarios"):
            entity_stream.append({"id": "par_biomagnetico", "tipo": "par", "nombre": "Par biomagnético"})
        if principal.get("microbios_relacionados"):
            entity_stream.append({"id": "microorganismos_patogenos", "tipo": "microbio", "nombre": "Microorganismos patógenos"})
        if principal.get("chakras_relacionados"):
            entity_stream.append({"id": "chakras", "tipo": "chakra", "nombre": "Chakras"})
        if "meridianos" in " ".join(principal.get("validaciones", [])).lower():
            entity_stream.append({"id": "meridianos", "tipo": "sistema", "nombre": "Meridianos"})
        for entity in entity_stream[:2]:
            tools.append(
                _entity_tool(
                    entity["id"],
                    entity["tipo"],
                    entity["nombre"],
                    str(principal.get("por_que", "")),
                    order,
                )
            )
            order += 1

    protocol_ids = [str(item.get("id", "")).strip() for item in protocolos_sugeridos if isinstance(item, dict)]
    pattern_id = str(top_pattern.get("id", "")).strip()
    explicit_candidates: List[str] = []
    for concept_id, rule in ENTITY_HINTS.items():
        if (
            _contains_keyword(case_text, rule["keywords"])
            or any(pid in rule["protocol_ids"] for pid in protocol_ids)
            or pattern_id in rule["pattern_ids"]
        ):
            explicit_candidates.append(concept_id)

    concept_candidates: List[str] = explicit_candidates + list(top_pattern.get("relacionado_conceptos", []))

    for concept_id in _dedupe_preserve(concept_candidates, 3):
        if concept_id in concept_index:
            tools.append(
                _concept_tool(
                    concept_id,
                    concept_index,
                    str(top_pattern.get("interpretacion", "") or top_pattern.get("trigger", "")).strip(),
                    order,
                )
            )
            order += 1

    if len(protocolos_sugeridos) > 1:
        tools.append(_protocol_tool(protocolos_sugeridos[1], order))

    deduped: Dict[str, Dict[str, Any]] = {}
    for tool in tools:
        tool_id = str(tool.get("id", "")).strip()
        if tool_id and tool_id not in deduped:
            deduped[tool_id] = tool
    return list(deduped.values())[:5]


def generate_reasoning(
    case_analysis: Any,
    knowledge: TherapeuticKnowledgeBase,
    case_input: Any = None,
) -> Dict[str, Any]:
    normalized_analysis = case_analysis if isinstance(case_analysis, CaseAnalysis) else CaseAnalysis(**case_analysis)
    normalized_case = case_input if isinstance(case_input, CaseInput) or case_input is None else CaseInput.from_dict(case_input)
    case_text = " ".join(
        normalized_analysis.key_elements
        + normalized_analysis.symptoms_detected
        + normalized_analysis.timeline_elements
        + normalized_analysis.context_elements
        + ([normalized_analysis.case_summary] if normalized_analysis.case_summary else [])
        + ([normalized_case.pregunta_del_terapeuta] if normalized_case else [])
    ).lower()
    bag = _tokenize(case_text)

    matched_patterns: List[Dict[str, Any]] = []
    reasoning_trace: List[Dict[str, Any]] = []
    possible_lines: List[str] = []
    validation_prompts: List[str] = []
    protocol_hints: List[Dict[str, Any]] = []
    protocol_index = _build_protocol_index(knowledge.protocols)
    structured_protocol_index = _build_structured_protocol_index(knowledge.structured_case_protocols)
    concept_index = _build_concept_index(knowledge.concepts)

    for pattern in knowledge.reasoning_patterns:
        score, evidence = _pattern_score(pattern, bag, case_text)
        if score < 1.15:
            continue

        matched_patterns.append(
            {
                "id": pattern.id,
                "trigger": pattern.trigger,
                "interpretacion": pattern.interpretacion,
                "que_observar": pattern.que_observar[:3],
                "acciones_sugeridas": pattern.acciones_sugeridas[:3],
                "score": round(score, 3),
                "source": pattern.source,
                "preguntas_clave": pattern.preguntas_clave[:3],
                "relacionado_conceptos": pattern.relacionado_conceptos[:3],
                "relacionado_protocolos": pattern.relacionado_protocolos[:2],
            }
        )
        reasoning_trace.append(
            {
                "pattern_id": pattern.id,
                "score": round(score, 3),
                "evidence": evidence,
                "related_intake": pattern.relacionado_intake,
            }
        )

    matched_patterns.sort(key=lambda item: item["score"], reverse=True)
    top_patterns = matched_patterns[:2]

    for pattern in top_patterns:
        interpretacion = str(pattern.get("interpretacion", "")).strip()
        if interpretacion:
            possible_lines.append(interpretacion)
        validation_prompts.extend(pattern.get("preguntas_clave", []))
        validation_prompts.extend(pattern.get("que_observar", []))

        for protocol_id in pattern.get("relacionado_protocolos", []):
            if protocol_id in protocol_index:
                protocol_hints.append(
                    _protocol_hint(
                        protocol_id,
                        protocol_index,
                        structured_protocol_index,
                        interpretacion or str(pattern.get("trigger", "")),
                    )
                )

    possible_lines = _dedupe_preserve(possible_lines, 2)
    protocol_hints = [dict(item) for item in {hint["id"]: hint for hint in protocol_hints}.values()][:2]
    protocol_validation_prompts = []
    if protocol_hints:
        principal_hint = protocol_hints[0]
        protocol_validation_prompts.extend(principal_hint.get("validaciones", []))
        protocol_validation_prompts.extend(principal_hint.get("preguntas_clave", []))
    validation_prompts = _dedupe_preserve(protocol_validation_prompts + validation_prompts, 4)
    interview_base = dict(structured_protocol_index.get("entrevista_inicial_de_rastreo", {}))

    if not top_patterns:
        confidence = "low"
    elif len(top_patterns) >= 2 and len(normalized_analysis.missing_elements) <= 1:
        confidence = "high"
    else:
        confidence = "medium"

    if normalized_analysis.missing_elements and confidence == "high":
        confidence = "medium"
    if len(normalized_analysis.missing_elements) >= 3:
        confidence = "low"
    elif len(normalized_analysis.missing_elements) >= 2 and confidence == "high":
        confidence = "medium"

    top_pattern = top_patterns[0] if top_patterns else {}
    observation_note = _top_observation_note(knowledge, bag)
    puerta_principal = _build_primary_door(top_pattern, observation_note) if top_pattern else {}
    ruta_principal = _build_route_statement(top_pattern, puerta_principal) if top_pattern else ""

    accion_inmediata = ""
    if top_pattern:
        if protocol_hints and protocol_hints[0].get("validaciones"):
            accion_inmediata = f"validar primero {str(protocol_hints[0]['validaciones'][0]).strip().lower()}"
        elif validation_prompts:
            accion_inmediata = f"validar primero {validation_prompts[0].lower()}"
        else:
            first_action = _dedupe_preserve(list(top_pattern.get("acciones_sugeridas", [])), 1)
            if first_action:
                accion_inmediata = first_action[0]

    pasos_inmediatos = _build_steps(accion_inmediata, validation_prompts[:4], protocol_hints)
    herramientas_relevantes = _build_tools_sequence(top_pattern, protocol_hints, concept_index, case_text) if top_pattern else []
    principal_protocol = protocol_hints[0] if protocol_hints else {}
    punto_de_decision = ""
    si_no_confirma = ""
    if principal_protocol and validation_prompts:
        punto_de_decision = (
            f"Si al validar {validation_prompts[0].lower()} esta puerta se sostiene, sigue con "
            f"{principal_protocol.get('nombre', 'el protocolo principal')}."
        )
    elif validation_prompts:
        punto_de_decision = f"Si al validar {validation_prompts[0].lower()} esta puerta se sostiene, continúa profundizando por la misma línea."

    if len(top_patterns) > 1:
        alternate = top_patterns[1]
        alt_trigger = _clean_text(str(alternate.get("trigger", "la siguiente ruta")))
        alt_protocol = protocol_hints[1].get("nombre") if len(protocol_hints) > 1 else ""
        si_no_confirma = (
            f"Si no se confirma esta ruta, cambia hacia {alt_trigger.lower()}"
            + (f" y considera {alt_protocol}" if alt_protocol else "")
            + "."
        )
    elif validation_prompts:
        si_no_confirma = "Si no se confirma esta ruta, vuelve a entrevista y cronología antes de abrir otra hipótesis."

    ruta_sugerida = ""
    if principal_protocol:
        ruta_sugerida = (
            f"Después de la entrevista base, abrir {principal_protocol.get('nombre', 'el protocolo principal')} "
            f"para {principal_protocol.get('que_busca_resolver', '').lower()}."
        ).strip()
    elif ruta_principal:
        ruta_sugerida = f"Después de la entrevista base, sostener la ruta clínica principal y validar antes de abrir otro protocolo."

    return ReasoningOutput(
        matched_patterns=top_patterns,
        possible_interpretive_lines=possible_lines,
        recommended_followup_questions=validation_prompts[:4],
        entrevista_base=interview_base,
        ruta_principal=ruta_principal,
        puerta_principal=puerta_principal,
        ruta_sugerida=ruta_sugerida,
        accion_inmediata=accion_inmediata,
        validaciones_clave=validation_prompts[:4],
        protocolos_sugeridos=protocol_hints,
        herramientas_relevantes=herramientas_relevantes,
        pasos_inmediatos=pasos_inmediatos,
        punto_de_decision=punto_de_decision,
        si_no_confirma=si_no_confirma,
        reasoning_trace=reasoning_trace[:3],
        confidence=confidence,
    ).to_dict()
