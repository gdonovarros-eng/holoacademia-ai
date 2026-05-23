from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


COURSE_SLUG = "course_holobiomagnetismo_2021"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _course_dir(course_slug: str = COURSE_SLUG) -> Path:
    return _project_root() / "data" / "knowledge_units" / course_slug


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dedupe(items: Iterable[str], limit: int | None = None) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
        if limit and len(out) >= limit:
            break
    return out


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _extract_keywords(text: str, keywords: Dict[str, List[str]]) -> List[str]:
    found: List[str] = []
    lowered = text.lower()
    for label, variants in keywords.items():
        if any(variant in lowered for variant in variants):
            found.append(label)
    return found


def _protocol_type(protocol_id: str) -> str:
    mapping = {
        "entrevista_inicial_de_rastreo": "entrevista_base",
        "rastreo_de_microorganismos_y_pares_biomagneticos": "rastreo_microbios_pares",
        "programa_de_sustitucion_temporal_para_trabajo_a_distancia": "trabajo_a_distancia",
        "rastreo_holobiomagnetico_condensado": "rastreo_global_condensado",
        "rastreo_y_desarticulacion_de_impacto_emocional": "impacto_emocional",
        "rastreo_de_frecuencias_y_soportes_vibratorios": "soporte_vibratorio",
        "eft_pro": "liberacion_emocional",
        "rastreo_de_5_elementos_global": "rastreo_5_elementos",
    }
    return mapping.get(protocol_id, "protocolo")


ORGAN_KEYWORDS = {
    "riñón": ["riñón", "rinon"],
    "hígado": ["hígado", "higado"],
    "vesícula": ["vesícula", "vesicula"],
    "pulmón": ["pulmón", "pulmon"],
    "intestino grueso": ["intestino grueso"],
    "corazón": ["corazón", "corazon"],
}

SYSTEM_KEYWORDS = {
    "5 elementos": ["5 elementos", "cinco elementos"],
    "meridianos": ["meridiano", "meridianos"],
    "yin / yang": ["yin", "yang"],
    "qi": ["qi", "chi"],
    "molde energético": ["molde energético", "molde energetico"],
    "sustitución temporal": ["sustitución temporal", "sustitucion temporal", "sustituto temporal"],
    "frecuencias": ["frecuencia", "frecuencias"],
    "impacto emocional": ["impacto emocional", "holograma", "conflicto"],
}

MICROBE_KEYWORDS = {
    "bacterias": ["bacteria", "bacterias"],
    "parásitos": ["parásito", "parásitos", "parasito", "parasitos"],
    "hongos": ["hongo", "hongos"],
    "virus": ["virus"],
    "priones": ["prion", "priones"],
    "microbio": ["microbio", "microbios"],
}


def build_structured_case_protocols(course_slug: str = COURSE_SLUG) -> List[Dict[str, Any]]:
    course_dir = _course_dir(course_slug)
    protocol_dir = course_dir / "05_protocols"
    therapeutic_dir = course_dir / "04_therapeutic"
    academic_dir = course_dir / "03_academic"
    root_dir = course_dir

    protocols = _load_json(protocol_dir / "protocols.json")
    reasoning_patterns = _load_json(therapeutic_dir / "reasoning_patterns.json")
    intake_questions = _load_json(therapeutic_dir / "intake_questions.json")
    connection_map = _load_json(root_dir / "09_connection_map.json")
    concepts = _load_json(academic_dir / "concepts.json")

    concepts_by_id = {item.get("id"): item for item in concepts if isinstance(item, dict)}
    reasoning_by_id = {item.get("id"): item for item in reasoning_patterns if isinstance(item, dict)}
    intake_by_id = {item.get("id"): item for item in intake_questions if isinstance(item, dict)}

    reasoning_to_protocol: Dict[str, List[str]] = {}
    for item in connection_map.get("reasoning_to_protocol", []):
        if not isinstance(item, dict):
            continue
        protocol_id = str(item.get("protocol_id", "")).strip()
        reasoning_id = str(item.get("reasoning_id", "")).strip()
        if protocol_id and reasoning_id:
            reasoning_to_protocol.setdefault(protocol_id, []).append(reasoning_id)

    concept_to_protocol: Dict[str, List[str]] = {}
    for item in connection_map.get("concept_to_protocol", []):
        if not isinstance(item, dict):
            continue
        protocol_id = str(item.get("protocol_id", "")).strip()
        concept_id = str(item.get("concept_id", "")).strip()
        if protocol_id and concept_id:
            concept_to_protocol.setdefault(protocol_id, []).append(concept_id)

    structured: List[Dict[str, Any]] = []

    for protocol in protocols:
        if not isinstance(protocol, dict):
            continue
        protocol_id = str(protocol.get("id", "")).strip()
        protocol_name = str(protocol.get("nombre", "")).strip()
        protocol_text = json.dumps(protocol, ensure_ascii=False)

        linked_reasoning_ids = _dedupe(reasoning_to_protocol.get(protocol_id, []))
        linked_patterns = [reasoning_by_id[rid] for rid in linked_reasoning_ids if rid in reasoning_by_id]
        linked_concept_ids = _dedupe(concept_to_protocol.get(protocol_id, []))
        linked_concepts = [concepts_by_id[cid] for cid in linked_concept_ids if cid in concepts_by_id]

        trigger_texts = _dedupe(pattern.get("trigger", "") for pattern in linked_patterns)
        conflict_texts = _dedupe(
            pattern.get("trigger", "")
            for pattern in linked_patterns
            if _contains_any(
                f"{pattern.get('trigger', '')} {pattern.get('interpretacion', '')}",
                ["emoción", "emocion", "conflicto", "miedo", "enojo", "tristeza", "persona", "evento"],
            )
        )

        all_text = " ".join(
            [
                protocol_text,
                *[json.dumps(item, ensure_ascii=False) for item in linked_patterns],
                *[json.dumps(item, ensure_ascii=False) for item in linked_concepts],
            ]
        )

        organos_relacionados = _extract_keywords(all_text, ORGAN_KEYWORDS)
        sistemas_relacionados = _extract_keywords(all_text, SYSTEM_KEYWORDS)
        microbios_relacionados = _extract_keywords(all_text, MICROBE_KEYWORDS)
        chakras_relacionados = ["chakra"] if "chakra" in all_text.lower() else []

        prereq = _dedupe(protocol.get("prerequisitos", []))
        if protocol_id != "entrevista_inicial_de_rastreo":
            if _contains_any(all_text, ["entrevista inicial", "después de entrevista", "haber completado la entrevista"]):
                prereq = _dedupe(["entrevista inicial completada", *prereq])

        related_intake_ids = _dedupe(
            intake_id
            for pattern in linked_patterns
            for intake_id in pattern.get("relacionado_intake", [])
            if intake_id in intake_by_id
        )
        preguntas_clave = _dedupe(
            [intake_by_id[iid].get("pregunta", "") for iid in related_intake_ids]
            + [question for pattern in linked_patterns for question in pattern.get("preguntas_clave", [])],
            limit=5,
        )

        validaciones = _dedupe(
            [step.get("titulo", "") for step in protocol.get("pasos", [])]
            + [item for pattern in linked_patterns for item in pattern.get("que_observar", [])]
            + [item for pattern in linked_patterns for item in pattern.get("acciones_sugeridas", [])],
            limit=6,
        )

        pares_prioritarios: List[str] = []
        if protocol_id == "rastreo_de_microorganismos_y_pares_biomagneticos":
            pares_prioritarios = [
                "pares biomagnéticos por región",
                "pares biomagnéticos por zona",
                "pares biomagnéticos por bloque",
            ]
        elif protocol_id == "rastreo_y_desarticulacion_de_impacto_emocional":
            pares_prioritarios = ["par biomagnético complementario al impacto", "par holobiomagnético activo y pulsante"]
        elif protocol_id == "rastreo_holobiomagnetico_condensado":
            pares_prioritarios = ["par holobiomagnético activo y pulsante"]

        si_confirma = ""
        si_no_confirma = ""
        protocolo_siguiente: List[str] = []

        if protocol_id == "entrevista_inicial_de_rastreo":
            si_confirma = "Abrir el protocolo que corresponda según el hallazgo de la entrevista."
            si_no_confirma = "Seguir aclarando síntoma, frecuencia, origen y moduladores antes de rastrear."
            protocolo_siguiente = [
                "rastreo_de_microorganismos_y_pares_biomagneticos",
                "rastreo_holobiomagnetico_condensado",
                "rastreo_y_desarticulacion_de_impacto_emocional",
                "rastreo_de_5_elementos_global",
            ]
        elif protocol_id == "rastreo_y_desarticulacion_de_impacto_emocional":
            si_confirma = "Cancelar el conflicto e instalar la información holobiomagnética activa y pulsante."
            si_no_confirma = "Cruzar con EFT Pro si el caso necesita ventilación y reprocesamiento consciente."
            protocolo_siguiente = ["eft_pro"]
        elif protocol_id == "rastreo_de_microorganismos_y_pares_biomagneticos":
            si_confirma = "Colocar y retirar los imanes en los pares encontrados."
            si_no_confirma = "Volver a comprobar el programa y la categoría rastreada antes de avanzar."
        elif protocol_id == "rastreo_de_5_elementos_global":
            si_confirma = "Interpretar el patrón del elemento y continuar la lectura por órgano, víscera y chi."
            si_no_confirma = "Regresar a entrevista o considerar rastreo holobiomagnético condensado si el cuadro sigue siendo global."
            protocolo_siguiente = ["rastreo_holobiomagnetico_condensado"]
        elif protocol_id == "eft_pro":
            si_confirma = "Recalibrar la intensidad y cerrar el circuito bioenergético."
            si_no_confirma = "Si la intensidad sigue alta, repetir desde el paso 5."
        elif protocol_id == "rastreo_holobiomagnetico_condensado":
            si_confirma = "Instalar la información del par holobiomagnético activo y pulsante."
            si_no_confirma = "Volver a entrevista o abrir 5 elementos si el caso sigue viéndose más global que local."
            protocolo_siguiente = ["rastreo_de_5_elementos_global"]
        elif protocol_id == "programa_de_sustitucion_temporal_para_trabajo_a_distancia":
            si_confirma = "Ejecutar el rastreo necesario e instalar información o pares si el protocolo lo requiere."
            si_no_confirma = "Repetir comprobación de identidad antes de seguir."
        elif protocol_id == "rastreo_de_frecuencias_y_soportes_vibratorios":
            si_confirma = "Instalar la frecuencia o soporte vibratorio indicado."
            si_no_confirma = "Volver a comprobar programa, bloque, potencia y duración."

        structured.append(
            {
                "id": protocol_id,
                "nombre": protocol_name,
                "tipo": _protocol_type(protocol_id),
                "cuando_abrirlo": _dedupe(protocol.get("cuando_usarlo", [])),
                "sintomas_disparadores": trigger_texts[:4],
                "conflictos_disparadores": conflict_texts[:4],
                "organos_relacionados": organos_relacionados[:4],
                "sistemas_relacionados": sistemas_relacionados[:4],
                "microbios_relacionados": microbios_relacionados[:2],
                "chakras_relacionados": chakras_relacionados[:2],
                "datos_previos_necesarios": prereq[:5],
                "preguntas_clave": preguntas_clave[:5],
                "validaciones": validaciones[:6],
                "pares_prioritarios": pares_prioritarios[:3],
                "objetivo": str(protocol.get("objetivo", "")).strip(),
                "pasos": protocol.get("pasos", []),
                "si_confirma": si_confirma,
                "si_no_confirma": si_no_confirma,
                "protocolo_siguiente": protocolo_siguiente,
                "source": str(protocol.get("source", "merged")).strip() or "merged",
                "confidence": str(protocol.get("confidence", "high")).strip() or "high",
            }
        )

    return structured


def main() -> None:
    course_dir = _course_dir()
    output_path = course_dir / "05_protocols" / "structured_case_protocols.json"
    structured = build_structured_case_protocols()
    output_path.write_text(json.dumps(structured, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(structured)} protocols to {output_path}")


if __name__ == "__main__":
    main()
