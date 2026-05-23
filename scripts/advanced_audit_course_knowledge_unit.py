from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import sys

from normalize_course_knowledge_unit import (
    DEFAULT_COURSE_DIR,
    compact,
    ensure_list,
    infer_course_metadata,
    load_json,
    normalize_text,
    observation_list,
    slugify,
    write_json,
)


CONCEPT_ERROR_HINTS = {
    "holobiomagnetismo": [
        "Reducirlo a biomagnetismo clásico sin integrar dimensión emocional y bioenergética."
    ],
    "entrevista_de_rastreo": [
        "Tomar la etiqueta diagnóstica como si ya fuera información clínica suficiente.",
        "Omitir cronología, frecuencia o moduladores del síntoma.",
    ],
    "sustituto_temporal": [
        "Usarlo sin comprobación de identidad.",
        "Omitir la aceptación explícita del sustituto antes del rastreo.",
    ],
    "molde_energetico": [
        "Descartar la lectura energética solo porque el órgano ya no está anatómicamente presente."
    ],
    "qi": [
        "Interpretar la emoción sin observar cómo cambia la dirección o calidad del Qi."
    ],
    "cinco_elementos": [
        "Usar los elementos como equivalencias rígidas en lugar de una lectura dinámica.",
        "Leer solo el síntoma del día sin mirar el estado energético de fondo.",
    ],
    "comandos_de_busqueda": [
        "Rastrear sin comprobar antes si el sistema sabe qué se está buscando."
    ],
    "eft_pro_concepto": [
        "Aplicarlo sin definir antes el conflicto, emoción o recuerdo que se va a trabajar."
    ],
    "holograma_impacto_emocional": [
        "Forzar todas las capas complementarias cuando el sistema no las está pidiendo."
    ],
}


GUIDE_CONTEXT_MAP = {
    "guide_entrevista": "Cuando el paciente llega con etiquetas vagas o con poca descripción corporal del problema.",
    "guide_5_elementos_global": "Cuando el caso requiere lectura del terreno energético global y no solo del síntoma puntual.",
    "guide_emocion_qi": "Cuando hay una emoción predominante que parece modular el cuadro clínico.",
    "guide_organos_y_moldes": "Cuando existe antecedente de cirugía o ausencia anatómica de un órgano.",
    "guide_metal": "Cuando la entrevista o el rastreo orientan hacia metal.",
    "guide_madera": "Cuando la entrevista o el rastreo orientan hacia madera.",
    "guide_distancia": "Cuando se hará trabajo terapéutico a distancia con sustituto temporal.",
}


GUIDE_NOT_APPLIES = {
    "guide_entrevista": ["Cuando el síntoma ya está descrito con suficiente precisión fenomenológica."],
    "guide_5_elementos_global": ["Cuando el objetivo es solamente ejecutar una corrección local ya definida."],
    "guide_emocion_qi": ["Cuando no hay una emoción dominante identificable en el caso."],
    "guide_organos_y_moldes": ["Cuando no existe antecedente quirúrgico ni persistencia energética asociada."],
    "guide_metal": ["Cuando metal no aparece como eje del caso ni del rastreo."],
    "guide_madera": ["Cuando madera no aparece como eje del caso ni del rastreo."],
    "guide_distancia": ["Cuando el consultante está presente y no se usará sustituto."],
}


GUIDE_RISK = {
    "guide_entrevista": "medio",
    "guide_5_elementos_global": "medio",
    "guide_emocion_qi": "medio",
    "guide_organos_y_moldes": "medio",
    "guide_metal": "bajo",
    "guide_madera": "bajo",
    "guide_distancia": "alto",
}


REASONING_PROTOCOL_HINTS = {
    "patron_vaguedad_sintoma": ["entrevista_inicial_de_rastreo"],
    "patron_recurrencia": ["entrevista_inicial_de_rastreo"],
    "patron_origen_aproximado": ["entrevista_inicial_de_rastreo"],
    "patron_terapia_empieza_en_entrevista": ["entrevista_inicial_de_rastreo"],
    "patron_subyacente_vs_sintoma": ["rastreo_holobiomagnetico_condensado", "rastreo_de_5_elementos_global"],
    "patron_molde_organico": ["rastreo_holobiomagnetico_condensado"],
    "patron_qi_miedo": ["rastreo_de_5_elementos_global"],
    "patron_qi_enojo": ["rastreo_de_5_elementos_global"],
    "patron_qi_tristeza": ["rastreo_de_5_elementos_global"],
    "patron_metal_social": ["rastreo_de_5_elementos_global"],
    "patron_madera_direccion": ["rastreo_de_5_elementos_global"],
    "patron_fuego_expresion": ["rastreo_de_5_elementos_global"],
    "patron_canal_exceso": ["rastreo_de_5_elementos_global"],
    "patron_busqueda_ordenada": [
        "rastreo_de_microorganismos_y_pares_biomagneticos",
        "rastreo_holobiomagnetico_condensado",
        "rastreo_de_frecuencias_y_soportes_vibratorios",
    ],
    "patron_conflicto_emocional": [
        "rastreo_y_desarticulacion_de_impacto_emocional",
        "eft_pro",
    ],
}


REASONING_QUESTION_HINTS = {
    "patron_vaguedad_sintoma": ["intake_caracteristicas"],
    "patron_recurrencia": ["intake_frecuencia", "intake_recurrencia"],
    "patron_origen_aproximado": ["intake_origen"],
    "patron_terapia_empieza_en_entrevista": ["intake_conflicto_critico", "intake_vida_post_conflicto"],
    "patron_subyacente_vs_sintoma": ["intake_tipo_sintoma", "intake_relacion_elemental"],
    "patron_molde_organico": ["intake_antecedentes_control"],
    "patron_qi_miedo": ["intake_emocion_actual", "intake_relacion_elemental"],
    "patron_qi_enojo": ["intake_emocion_actual", "intake_relacion_elemental"],
    "patron_qi_tristeza": ["intake_emocion_actual", "intake_relacion_elemental"],
    "patron_metal_social": ["intake_conflicto_critico", "intake_emocion_actual"],
    "patron_madera_direccion": ["intake_conflicto_critico", "intake_relacion_elemental"],
    "patron_fuego_expresion": ["intake_emocion_actual", "intake_relacion_elemental"],
    "patron_canal_exceso": ["intake_tipo_sintoma", "intake_relacion_elemental"],
    "patron_busqueda_ordenada": ["intake_sintoma_principal"],
    "patron_conflicto_emocional": ["intake_conflicto_critico", "intake_emocion_actual"],
}


FAQ_CONCEPT_HINTS = {
    "faq_que_diferencia_a_holobiomagnetismo_del_biomagnetis": ["holobiomagnetismo"],
    "faq_el_curso_trabaja_solo_sintomas_fisicos": ["holobiomagnetismo", "factor_psicoemocional"],
    "faq_se_puede_trabajar_a_distancia": ["cibertelepatia", "sustituto_temporal"],
    "faq_para_que_sirven_los_5_elementos_dentro_del_curso": ["cinco_elementos", "qi"],
    "faq_que_se_registra_de_un_sintoma_al_iniciar": ["entrevista_de_rastreo"],
    "faq_el_curso_incluye_medicina_tradicional_china_comple": ["biomagnetopuntura", "meridianos", "qi", "cinco_elementos"],
    "faq_que_herramientas_complementarias_incorpora_el_curs": [
        "frecuencias_biomagneticas",
        "frecuencias_bioenergeticas",
        "farmacopea_homeopatica",
        "flores_de_bach",
        "sales_de_schussler",
    ],
    "faq_que_es_eft_pro_dentro_de_este_curso": ["eft_pro_concepto"],
    "faq_el_curso_entrega_comandos_de_busqueda_concretos": ["comandos_de_busqueda"],
    "faq_el_manual_deja_listo_todo_el_diagnostico": ["entrevista_de_rastreo", "factor_psicoemocional"],
}


FAQ_PROTOCOL_HINTS = {
    "faq_se_puede_trabajar_a_distancia": ["programa_de_sustitucion_temporal_para_trabajo_a_distancia"],
    "faq_para_que_sirven_los_5_elementos_dentro_del_curso": ["rastreo_de_5_elementos_global"],
    "faq_que_se_registra_de_un_sintoma_al_iniciar": ["entrevista_inicial_de_rastreo"],
    "faq_que_herramientas_complementarias_incorpora_el_curs": ["rastreo_de_frecuencias_y_soportes_vibratorios", "eft_pro"],
    "faq_que_es_eft_pro_dentro_de_este_curso": ["eft_pro"],
    "faq_el_curso_entrega_comandos_de_busqueda_concretos": [
        "rastreo_de_microorganismos_y_pares_biomagneticos",
        "rastreo_holobiomagnetico_condensado",
    ],
}


FAQ_RESPONSE_HINTS = {
    "faq_que_diferencia_a_holobiomagnetismo_del_biomagnetis": (
        "Holobiomagnetismo amplía el biomagnetismo clásico porque no se limita a microorganismos y pares; integra lectura energética, mental y emocional del caso."
    ),
    "faq_el_curso_trabaja_solo_sintomas_fisicos": (
        "No. El curso pide distinguir desde la entrevista lo físico, lo psicoemocional y lo mixto, y trata esa información como parte del análisis clínico."
    ),
    "faq_se_puede_trabajar_a_distancia": (
        "Sí, pero el curso lo condiciona al uso de sustituto temporal, comprobación de identidad y validación previa del programa de trabajo."
    ),
    "faq_para_que_sirven_los_5_elementos_dentro_del_curso": (
        "Sirven para leer el terreno energético de fondo, relacionar emoción, órgano y dirección del Qi, y orientar el rastreo más allá del síntoma puntual."
    ),
    "faq_que_se_registra_de_un_sintoma_al_iniciar": (
        "Se registra cómo se siente, dónde aparece, su frecuencia, desde cuándo ocurre y qué lo agrava o lo inhibe."
    ),
    "faq_el_curso_incluye_medicina_tradicional_china_comple": (
        "Integra bases operativas de medicina tradicional china útiles para el curso, especialmente Qi, meridianos, cinco elementos y biomagnetopuntura, dentro del marco de holobiomagnetismo."
    ),
    "faq_que_herramientas_complementarias_incorpora_el_curs": (
        "Además de pares e imanes, el curso incorpora rastreo de frecuencias biomagnéticas, soportes bioenergéticos, homeopatía, flores de Bach y sales de Schüssler."
    ),
    "faq_que_es_eft_pro_dentro_de_este_curso": (
        "EFT Pro es la secuencia emocional operativa del curso para trabajar conflicto, recuerdo, tapping, reencuadre y liberación emocional guiada."
    ),
    "faq_el_curso_entrega_comandos_de_busqueda_concretos": (
        "Sí. El curso enseña comandos verbales para abrir búsqueda, comprobar programa y ordenar el rastreo por categorías o bloques."
    ),
    "faq_el_manual_deja_listo_todo_el_diagnostico": (
        "No. El manual orienta, pero el curso insiste en que la entrevista y el rastreo son los que convierten la información en criterio terapéutico usable."
    ),
}


CONCEPT_PROTOCOL_HINTS = {
    "holobiomagnetismo": ["entrevista_inicial_de_rastreo", "rastreo_holobiomagnetico_condensado"],
    "biomagnetopuntura": ["rastreo_de_5_elementos_global"],
    "cibertelepatia": ["programa_de_sustitucion_temporal_para_trabajo_a_distancia"],
    "yin_yang": ["rastreo_de_5_elementos_global"],
    "homologacion_de_puntos": ["rastreo_de_5_elementos_global", "eft_pro"],
    "frecuencias_biomagneticas": ["rastreo_de_frecuencias_y_soportes_vibratorios"],
    "frecuencias_bioenergeticas": ["rastreo_de_frecuencias_y_soportes_vibratorios"],
    "farmacopea_homeopatica": ["rastreo_de_frecuencias_y_soportes_vibratorios"],
    "flores_de_bach": ["rastreo_de_frecuencias_y_soportes_vibratorios"],
    "sales_de_schussler": ["rastreo_de_frecuencias_y_soportes_vibratorios"],
    "eft_pro_concepto": ["rastreo_y_desarticulacion_de_impacto_emocional", "eft_pro"],
}


CONCEPT_REASONING_HINTS = {
    "holobiomagnetismo": ["patron_subyacente_vs_sintoma", "patron_conflicto_emocional"],
    "entrevista_de_rastreo": [
        "patron_vaguedad_sintoma",
        "patron_recurrencia",
        "patron_origen_aproximado",
        "patron_terapia_empieza_en_entrevista",
    ],
    "molde_energetico": ["patron_molde_organico"],
    "qi": ["patron_qi_miedo", "patron_qi_enojo", "patron_qi_tristeza"],
    "cinco_elementos": [
        "patron_qi_miedo",
        "patron_qi_enojo",
        "patron_qi_tristeza",
        "patron_metal_social",
        "patron_madera_direccion",
        "patron_fuego_expresion",
    ],
    "yin_yang": ["patron_subyacente_vs_sintoma", "patron_canal_exceso"],
    "meridianos": ["patron_canal_exceso"],
    "holograma_impacto_emocional": ["patron_conflicto_emocional"],
    "eft_pro_concepto": ["patron_conflicto_emocional"],
    "comandos_de_busqueda": ["patron_busqueda_ordenada"],
    "factor_psicoemocional": ["patron_conflicto_emocional"],
}


CONCEPT_CONCEPT_HINTS = {
    "holobiomagnetismo": ["entrevista_de_rastreo", "comandos_de_busqueda", "factor_psicoemocional"],
    "biomagnetopuntura": ["meridianos", "qi", "homologacion_de_puntos"],
    "cibertelepatia": ["sustituto_temporal", "comandos_de_busqueda"],
    "yin_yang": ["qi", "cinco_elementos", "meridianos"],
    "homologacion_de_puntos": ["biomagnetopuntura", "meridianos"],
    "frecuencias_biomagneticas": ["frecuencias_bioenergeticas"],
    "frecuencias_bioenergeticas": ["frecuencias_biomagneticas", "farmacopea_homeopatica", "flores_de_bach", "sales_de_schussler"],
    "farmacopea_homeopatica": ["frecuencias_bioenergeticas", "flores_de_bach", "sales_de_schussler"],
    "eft_pro_concepto": ["holograma_impacto_emocional", "meridianos", "factor_psicoemocional"],
}


GUIDE_CONCEPT_HINTS = {
    "guide_entrevista": ["entrevista_de_rastreo"],
    "guide_5_elementos_global": ["cinco_elementos", "yin_yang", "qi"],
    "guide_emocion_qi": ["qi", "cinco_elementos", "factor_psicoemocional"],
    "guide_organos_y_moldes": ["molde_energetico"],
    "guide_metal": ["cinco_elementos", "qi"],
    "guide_madera": ["cinco_elementos", "qi"],
    "guide_distancia": ["sustituto_temporal", "cibertelepatia", "comandos_de_busqueda"],
}


GUIDE_PROTOCOL_HINTS = {
    "guide_entrevista": ["entrevista_inicial_de_rastreo"],
    "guide_5_elementos_global": ["rastreo_de_5_elementos_global"],
    "guide_emocion_qi": ["rastreo_de_5_elementos_global", "rastreo_y_desarticulacion_de_impacto_emocional"],
    "guide_organos_y_moldes": ["rastreo_holobiomagnetico_condensado"],
    "guide_metal": ["rastreo_de_5_elementos_global"],
    "guide_madera": ["rastreo_de_5_elementos_global"],
    "guide_distancia": ["programa_de_sustitucion_temporal_para_trabajo_a_distancia"],
}


REASONING_ACTION_HINTS = {
    "patron_vaguedad_sintoma": [
        "pedir sensación, localización y cualidad antes de rastrear",
        "traducir la etiqueta diagnóstica en datos fenomenológicos",
    ],
    "patron_recurrencia": [
        "registrar periodicidad y episodios previos",
        "contrastar el patrón repetitivo con el terreno energético de fondo",
    ],
    "patron_origen_aproximado": [
        "ubicar el inicio por etapa de vida o hito relevante",
        "anotar una referencia temporal útil aunque no sea exacta",
    ],
    "patron_terapia_empieza_en_entrevista": [
        "seguir la asociación emocional que aparece en la entrevista",
        "usar el relato como puerta de entrada terapéutica, no solo administrativa",
    ],
    "patron_subyacente_vs_sintoma": [
        "leer primero el desequilibrio global y luego el síntoma puntual",
        "usar cinco elementos o rastreo condensado para priorizar fondo sobre forma",
    ],
    "patron_molde_organico": [
        "considerar el molde energético aunque el órgano ya no esté presente",
        "cruzar el antecedente quirúrgico con el rastreo energético actual",
    ],
    "patron_qi_miedo": [
        "explorar agua/riñón y la dirección descendente del Qi",
        "observar contracción corporal y sensación de repliegue",
    ],
    "patron_qi_enojo": [
        "explorar madera/hígado/vesícula",
        "observar ascenso energético, tensión o calor en la parte alta",
    ],
    "patron_qi_tristeza": [
        "explorar metal/pulmón/intestino grueso",
        "observar repliegue, desconexión o dificultad de soltar",
    ],
    "patron_metal_social": [
        "preguntar por vínculo con figura paterna y red social",
        "leer metal más allá del órgano aislado",
    ],
    "patron_madera_direccion": [
        "preguntar por decisiones pendientes y dirección vital",
        "relacionar el caso con enojo retenido o falta de rumbo",
    ],
    "patron_fuego_expresion": [
        "explorar expresión, alegría desbordada o agitación mental",
        "observar estado del Shen y la capacidad de articular lo vivido",
    ],
    "patron_canal_exceso": [
        "evaluar sobrecarga del canal y del sistema completo",
        "evitar quedarse en un punto local sin mirar el meridiano entero",
    ],
    "patron_busqueda_ordenada": [
        "declarar la búsqueda antes de rastrear",
        "comprobar programa y avanzar por categorías o bloques",
    ],
    "patron_conflicto_emocional": [
        "definir conflicto, emoción y recuerdo antes de intervenir",
        "valorar si conviene pasar a holograma emocional o EFT Pro",
    ],
}


REASONING_ERROR_HINTS = {
    "patron_vaguedad_sintoma": ["quedarse en la etiqueta médica", "rastrear sin precisar sensación y localización"],
    "patron_recurrencia": ["tratar cada episodio como aislado", "no preguntar por periodicidad"],
    "patron_origen_aproximado": ["descartar cronología por no tener fecha exacta"],
    "patron_terapia_empieza_en_entrevista": ["cortar la asociación emocional que surge durante la entrevista"],
    "patron_subyacente_vs_sintoma": ["perseguir síntomas secundarios sin leer el terreno energético"],
    "patron_molde_organico": ["asumir que un órgano ausente ya no puede rastrearse energéticamente"],
    "patron_qi_miedo": ["leer miedo sin observar la dirección del Qi"],
    "patron_qi_enojo": ["reducir el enojo a un dato psicológico sin correlato energético"],
    "patron_qi_tristeza": ["leer tristeza sin observar desconexión o bloqueo de metal"],
    "patron_metal_social": ["reducir metal a pulmón sin revisar la dimensión vincular"],
    "patron_madera_direccion": ["leer madera solo como ira y no como dirección o decisión"],
    "patron_fuego_expresion": ["confundir activación de fuego con simple entusiasmo pasajero"],
    "patron_canal_exceso": ["mirar solo el punto doloroso y no el canal completo"],
    "patron_busqueda_ordenada": ["saltar pasos de validación del programa"],
    "patron_conflicto_emocional": ["pasar a EFT Pro sin definir antes el conflicto"],
}


INTAKE_RELATION_HINTS = {
    "intake_sintoma_principal": ["entrevista_de_rastreo"],
    "intake_tipo_sintoma": ["entrevista_de_rastreo", "factor_psicoemocional"],
    "intake_caracteristicas": ["entrevista_de_rastreo"],
    "intake_frecuencia": ["entrevista_de_rastreo"],
    "intake_origen": ["entrevista_de_rastreo", "factor_psicoemocional"],
    "intake_factores": ["entrevista_de_rastreo", "factor_psicoemocional"],
    "intake_conflicto_critico": ["factor_psicoemocional", "holograma_impacto_emocional"],
    "intake_vida_post_conflicto": ["factor_psicoemocional", "holograma_impacto_emocional"],
    "intake_antecedentes_control": ["molde_energetico"],
    "intake_emocion_actual": ["qi", "cinco_elementos", "factor_psicoemocional"],
    "intake_recurrencia": ["entrevista_de_rastreo"],
    "intake_relacion_elemental": ["cinco_elementos", "qi"],
}


CORE_FIELDS = {"id", "curso", "linea", "source", "confidence"}


def invert_map_of_lists(mapping: dict[str, list[str]]) -> dict[str, list[str]]:
    inverse = defaultdict(list)
    for left, rights in mapping.items():
        for right in rights:
            inverse[right].append(left)
    cleaned = {}
    for key, value in inverse.items():
        seen = set()
        ordered = []
        for item in value:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        cleaned[key] = ordered
    return cleaned


REASONING_CONCEPT_HINTS = invert_map_of_lists(CONCEPT_REASONING_HINTS)


def build_concept_tokens(concepts: list[dict]) -> dict[str, set[str]]:
    token_map = {}
    for concept in concepts:
        variants = [concept.get("termino", "")] + ensure_list(concept.get("aliases"))
        token_map[concept["id"]] = {normalize_text(v) for v in variants if normalize_text(v)}
    return token_map


def combined_protocol_text(protocol: dict) -> str:
    parts = [
        protocol.get("nombre", ""),
        protocol.get("objetivo", ""),
        protocol.get("descripcion", ""),
        " ".join(ensure_list(protocol.get("cuando_usarlo"))),
        " ".join(ensure_list(protocol.get("prerequisitos"))),
        " ".join(ensure_list(protocol.get("observaciones"))),
        " ".join(ensure_list(protocol.get("advertencias"))),
    ]
    for step in ensure_list(protocol.get("pasos")):
        parts.extend(
            [
                step.get("titulo", ""),
                step.get("instruccion", ""),
                step.get("objetivo_del_paso", ""),
                " ".join(ensure_list(step.get("que_observar"))),
                " ".join(ensure_list(step.get("notas"))),
            ]
        )
    return normalize_text(" ".join(parts))


def combined_reasoning_text(item: dict) -> str:
    return normalize_text(
        " ".join(
            [
                item.get("trigger", ""),
                item.get("interpretacion", ""),
                " ".join(ensure_list(item.get("que_observar"))),
                " ".join(ensure_list(item.get("acciones_sugeridas"))),
            ]
        )
    )


def detect_related_ids(text: str, token_map: dict[str, set[str]]) -> list[str]:
    lowered = normalize_text(text)
    related = []
    for item_id, tokens in token_map.items():
        if any(token and token in lowered for token in tokens):
            related.append(item_id)
    return related


def unique_preserve(items: list[str]) -> list[str]:
    out = []
    seen = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def rename_in_list(items: list[str], rename_map: dict[str, str]) -> list[str]:
    return [rename_map.get(item, item) for item in ensure_list(items)]


def rename_concept_ids_across_course(course_dir: Path) -> dict[str, str]:
    concepts_path = course_dir / "03_academic" / "concepts.json"
    protocols_path = course_dir / "05_protocols" / "protocols.json"
    if not concepts_path.exists() or not protocols_path.exists():
        return {}

    concepts = load_json(concepts_path)
    protocols = load_json(protocols_path)
    concept_ids = {item["id"] for item in concepts}
    protocol_ids = {item["id"] for item in protocols}
    collisions = sorted(concept_ids & protocol_ids)
    if not collisions:
        return {}

    rename_map = {item_id: f"concepto_{item_id}" for item_id in collisions}
    for item in concepts:
        item["id"] = rename_map.get(item["id"], item["id"])
        item["relacionado_conceptos"] = rename_in_list(item.get("relacionado_conceptos"), rename_map)
    write_json(concepts_path, concepts)

    glossary_path = course_dir / "03_academic" / "glossary.json"
    if glossary_path.exists():
        glossary = load_json(glossary_path)
        for item in glossary:
            item["referencia_concepto"] = rename_map.get(item.get("referencia_concepto"), item.get("referencia_concepto", ""))
        write_json(glossary_path, glossary)

    faq_path = course_dir / "03_academic" / "faq_candidates.json"
    if faq_path.exists():
        faqs = load_json(faq_path)
        for item in faqs:
            item["relacionado_conceptos"] = rename_in_list(item.get("relacionado_conceptos"), rename_map)
        write_json(faq_path, faqs)

    reasoning_path = course_dir / "04_therapeutic" / "reasoning_patterns.json"
    if reasoning_path.exists():
        reasoning = load_json(reasoning_path)
        for item in reasoning:
            item["relacionado_conceptos"] = rename_in_list(item.get("relacionado_conceptos"), rename_map)
        write_json(reasoning_path, reasoning)

    guides_path = course_dir / "04_therapeutic" / "interpretation_guides.json"
    if guides_path.exists():
        guides = load_json(guides_path)
        for item in guides:
            item["relacionado_conceptos"] = rename_in_list(item.get("relacionado_conceptos"), rename_map)
        write_json(guides_path, guides)

    intake_path = course_dir / "04_therapeutic" / "intake_questions.json"
    if intake_path.exists():
        intake = load_json(intake_path)
        for item in intake:
            item["relacionado_conceptos"] = rename_in_list(
                item.get("relacionado_conceptos") or item.get("relacionado_con"),
                rename_map,
            )
            item.pop("relacionado_con", None)
        write_json(intake_path, intake)

    for protocol in protocols:
        protocol["relacionado_conceptos"] = rename_in_list(protocol.get("relacionado_conceptos"), rename_map)
    write_json(protocols_path, protocols)

    manifest_path = course_dir / "06_catalog" / "course_manifest.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        for group, entries in (manifest.get("entry_points") or {}).items():
            for entry in ensure_list(entries):
                if isinstance(entry, dict) and entry.get("tipo") == "concepto":
                    entry["id"] = rename_map.get(entry.get("id"), entry.get("id", ""))
        write_json(manifest_path, manifest)

    connection_map_path = course_dir / "09_connection_map.json"
    if connection_map_path.exists():
        connection_map_path.unlink()

    return rename_map


def classify_level_confidence(source: str, confidence: str) -> str:
    if confidence == "low":
        return "medio"
    if source == "merged":
        return "alto"
    return "medio"


def classify_flow_and_priority(question: dict) -> tuple[str, str]:
    objective = normalize_text(question.get("objetivo", ""))
    if any(key in objective for key in ["delimitar", "clasificar", "descripcion", "registrar antecedentes"]):
        return "inicio", "alta"
    if any(key in objective for key in ["cronologia", "evento critico", "continuidad", "agravan", "emocion predominante", "recurrencia"]):
        return "profundizacion", "alta"
    if "lectura energetica" in objective:
        return "validacion", "media"
    return "profundizacion", "media"


def infer_step_decision_points(step: dict) -> list[str]:
    title = normalize_text(step.get("titulo", ""))
    instruction = normalize_text(step.get("instruccion", ""))
    decisions = []
    if "comprobar" in title or "verificar" in title:
        decisions.append("Si la respuesta no confirma el programa o la validación esperada, reformular antes de continuar.")
    if "identidad" in title:
        decisions.append("Si la identidad no coincide con la persona objetivo, repetir la fórmula de sustitución y volver a comprobar.")
    if "entrevista" in title or "preguntar" in instruction or "pedir" in instruction:
        decisions.append("Si la respuesta sigue siendo vaga, pedir sensación, localización o cronología antes de avanzar.")
    if "rastrear" in title and "si se necesita" in instruction:
        decisions.append("Si el sistema no activa esa capa de búsqueda, pasar a la siguiente sin forzarla.")
    if "buscar patogenos" in normalize_text(title) or "categorias" in instruction:
        decisions.append("Si una categoría no muestra activación, continuar con la siguiente categoría de rastreo.")
    if "instalar" in title or "colocar" in instruction:
        decisions.append("Si no hubo validación previa del hallazgo, pausar la instalación y volver a comprobar el rastreo.")
    if not decisions:
        decisions.append("Si la información obtenida todavía no es suficiente para cumplir el objetivo del paso, profundizar antes de avanzar.")
    return unique_preserve(decisions)


def infer_step_errors(step: dict) -> list[str]:
    title = normalize_text(step.get("titulo", ""))
    errors = ["Avanzar sin registrar los hallazgos de este paso."]
    if "comprobar" in title or "verificar" in title:
        errors.append("Continuar aunque la comprobación no haya sido afirmativa.")
    if "identificar motivo" in title or "precisar" in title:
        errors.append("Aceptar respuestas vagas sin bajar a sensación y localización.")
    if "instalar" in title or "colocar" in title:
        errors.append("Aplicar la instalación sin validar primero qué se va a gestionar.")
    return unique_preserve(errors)


def infer_step_advance(step: dict) -> list[str]:
    title = normalize_text(step.get("titulo", ""))
    criteria = []
    if "identificar motivo" in title:
        criteria.append("El motivo principal de consulta quedó definido.")
    if "precisar" in title:
        criteria.append("El síntoma ya puede describirse por sensación, localización y cualidad.")
    if "registrar frecuencia" in title:
        criteria.append("La frecuencia o recurrencia del cuadro quedó anotada.")
    if "ubicar origen" in title:
        criteria.append("Existe una referencia temporal útil del inicio del cuadro.")
    if "comprobar" in title or "verificar" in title:
        criteria.append("La validación fue afirmativa.")
    if "rastrear" in title or "buscar" in title:
        criteria.append("Los hallazgos solicitados quedaron detectados y registrados.")
    if "instalar" in title or "colocar" in title:
        criteria.append("La aplicación quedó registrada con duración u observación final.")
    if not criteria:
        criteria.append(compact(step.get("objetivo_del_paso", ""), 120) or "El objetivo del paso quedó cumplido.")
    return unique_preserve(criteria)


def enrich_protocols(course_dir: Path, course_slug: str, linea: str, concepts: list[dict], reasoning_patterns: list[dict]) -> tuple[list[dict], dict]:
    path = course_dir / "05_protocols" / "protocols.json"
    protocols = load_json(path)
    concept_tokens = build_concept_tokens(concepts)
    reasoning_by_id = {item["id"]: item for item in reasoning_patterns}

    protocol_relations = defaultdict(list)
    reasoning_to_protocol = defaultdict(list)

    for protocol in protocols:
        text = combined_protocol_text(protocol)
        related_concepts = detect_related_ids(text, concept_tokens)
        related_reasoning = []
        for reasoning in reasoning_patterns:
            hint_ids = REASONING_PROTOCOL_HINTS.get(reasoning["id"], [])
            if protocol["id"] in hint_ids:
                related_reasoning.append(reasoning["id"])
                continue
            trigger_tokens = normalize_text(reasoning.get("trigger", ""))
            if trigger_tokens and trigger_tokens[:40] in text:
                related_reasoning.append(reasoning["id"])
        protocol["relacionado_conceptos"] = unique_preserve(related_concepts)
        protocol["relacionado_reasoning"] = unique_preserve(related_reasoning)
        for concept_id in protocol["relacionado_conceptos"]:
            protocol_relations[concept_id].append(protocol["id"])
        for reasoning_id in protocol["relacionado_reasoning"]:
            reasoning_to_protocol[reasoning_id].append(protocol["id"])

        for step in ensure_list(protocol.get("pasos")):
            step["id"] = step.get("id") or f"{protocol['id']}_paso_{step.get('orden')}"
            step["curso"] = course_slug
            step["linea"] = linea
            step["source"] = protocol.get("source", "merged")
            step["confidence"] = protocol.get("confidence", "high")
            step["decision_points"] = infer_step_decision_points(step)
            step["errores_comunes"] = infer_step_errors(step)
            step["criterios_de_avance"] = infer_step_advance(step)

    write_json(path, protocols)
    return protocols, {
        "concept_to_protocol": {key: unique_preserve(value) for key, value in protocol_relations.items()},
        "reasoning_to_protocol": {key: unique_preserve(value) for key, value in reasoning_to_protocol.items()},
    }


def enrich_concepts(course_dir: Path, protocols: list[dict], reasoning_patterns: list[dict]) -> tuple[list[dict], dict]:
    path = course_dir / "03_academic/concepts.json"
    concepts = load_json(path)
    protocol_by_id = {item["id"]: item for item in protocols}
    reasoning_by_id = {item["id"]: item for item in reasoning_patterns}
    concept_tokens = build_concept_tokens(concepts)
    concept_to_reasoning = defaultdict(list)

    for concept in concepts:
        concept_id = concept["id"]
        related_reasoning = []
        for reasoning in reasoning_patterns:
            text = combined_reasoning_text(reasoning)
            if concept_id in detect_related_ids(text, {concept_id: concept_tokens[concept_id]}):
                related_reasoning.append(reasoning["id"])
        related_reasoning.extend(CONCEPT_REASONING_HINTS.get(concept_id, []))
        related_protocols = []
        for protocol in protocols:
            if concept_id in ensure_list(protocol.get("relacionado_conceptos")):
                related_protocols.append(protocol["id"])
        related_protocols.extend(CONCEPT_PROTOCOL_HINTS.get(concept_id, []))
        related_concepts = []
        for protocol_id in related_protocols:
            if protocol_id not in protocol_by_id:
                continue
            for other in ensure_list(protocol_by_id[protocol_id].get("relacionado_conceptos")):
                if other != concept_id:
                    related_concepts.append(other)
        for reasoning_id in related_reasoning:
            if reasoning_id not in reasoning_by_id:
                continue
            for other in detect_related_ids(combined_reasoning_text(reasoning_by_id[reasoning_id]), concept_tokens):
                if other != concept_id:
                    related_concepts.append(other)
        related_concepts.extend(CONCEPT_CONCEPT_HINTS.get(concept_id, []))

        concept["relacionado_protocolos"] = unique_preserve(related_protocols)
        concept["relacionado_reasoning"] = unique_preserve(related_reasoning)
        concept["relacionado_conceptos"] = unique_preserve(related_concepts)[:8]
        if concept["relacionado_protocolos"]:
            protocol_names = [protocol_by_id[item]["nombre"] for item in concept["relacionado_protocolos"][:2] if item in protocol_by_id]
            concept["cuando_se_aplica"] = (
                f"Se usa especialmente dentro de {' y '.join(protocol_names)}."
                if protocol_names
                else concept.get("cuando_se_aplica", "")
            )
        elif concept.get("modulo"):
            concept["cuando_se_aplica"] = f"Se aborda dentro de {concept['modulo'].replace('_', ' ')}."
        else:
            concept["cuando_se_aplica"] = ""
        concept["errores_comunes"] = CONCEPT_ERROR_HINTS.get(concept_id, [])
        for reasoning_id in concept["relacionado_reasoning"]:
            concept_to_reasoning[concept_id].append(reasoning_id)

    write_json(path, concepts)

    glossary_path = course_dir / "03_academic/glossary.json"
    glossary = load_json(glossary_path)
    by_term = {normalize_text(item["termino"]): item for item in glossary}
    for concept in concepts:
        item = by_term.get(normalize_text(concept["termino"]))
        if item is None:
            continue
        item["referencia_concepto"] = concept["id"]
        item["uso"] = "rápido"
    write_json(glossary_path, glossary)

    return concepts, {key: unique_preserve(value) for key, value in concept_to_reasoning.items()}


def enrich_reasoning(course_dir: Path, intake_questions: list[dict], concept_relation_map: dict[str, list[str]], protocol_maps: dict) -> list[dict]:
    path = course_dir / "04_therapeutic/reasoning_patterns.json"
    items = load_json(path)
    intake_by_id = {item["id"]: item for item in intake_questions}
    concept_tokens = build_concept_tokens(load_json(course_dir / "03_academic/concepts.json"))
    for item in items:
        hinted = [intake_by_id[qid]["pregunta"] for qid in REASONING_QUESTION_HINTS.get(item["id"], []) if qid in intake_by_id]
        if not hinted:
            hinted = [q["pregunta"] for q in intake_questions[:2]]
        item["preguntas_clave"] = hinted
        item["nivel_confianza"] = classify_level_confidence(item.get("source", "merged"), item.get("confidence", "low"))
        item["acciones_sugeridas"] = unique_preserve(REASONING_ACTION_HINTS.get(item["id"], []) + ensure_list(item.get("acciones_sugeridas")))
        item["errores_comunes"] = REASONING_ERROR_HINTS.get(item["id"], [])
        related_concepts = detect_related_ids(combined_reasoning_text(item), concept_tokens)
        related_concepts.extend(REASONING_CONCEPT_HINTS.get(item["id"], []))
        item["relacionado_conceptos"] = unique_preserve(related_concepts)
        item["relacionado_protocolos"] = protocol_maps["reasoning_to_protocol"].get(item["id"], [])
        item["relacionado_intake"] = unique_preserve(REASONING_QUESTION_HINTS.get(item["id"], []))
    write_json(path, items)
    return items


def enrich_intake(course_dir: Path, reasoning_patterns: list[dict]) -> list[dict]:
    path = course_dir / "04_therapeutic/intake_questions.json"
    items = load_json(path)
    reasoning_by_id = {item["id"]: item for item in reasoning_patterns}

    for index, item in enumerate(items):
        flujo, prioridad = classify_flow_and_priority(item)
        item["flujo"] = flujo
        item["prioridad"] = prioridad
        item["siguiente_posible"] = [items[index + 1]["id"]] if index + 1 < len(items) else []
        related_reasoning = unique_preserve(
            [
                reasoning["id"]
                for reasoning in reasoning_patterns
                if item["id"] in ensure_list(reasoning.get("relacionado_intake"))
                or item["id"] in ensure_list(REASONING_QUESTION_HINTS.get(reasoning["id"], []))
            ]
        )
        related_concepts = unique_preserve(
            ensure_list(item.get("relacionado_conceptos"))
            or ensure_list(item.get("relacionado_con"))
            or INTAKE_RELATION_HINTS.get(item["id"], [])
        )
        related_protocols = unique_preserve(
            protocol_id
            for reasoning_id in related_reasoning
            for protocol_id in ensure_list(reasoning_by_id.get(reasoning_id, {}).get("relacionado_protocolos"))
        )
        item["relacionado_conceptos"] = related_concepts
        item["relacionado_reasoning"] = related_reasoning
        item["relacionado_protocolos"] = related_protocols
        item.pop("relacionado_con", None)

    write_json(path, items)
    return items


def enrich_guides(course_dir: Path, protocols: list[dict], concepts: list[dict], reasoning_patterns: list[dict]) -> list[dict]:
    path = course_dir / "04_therapeutic/interpretation_guides.json"
    items = load_json(path)
    concept_tokens = build_concept_tokens(concepts)
    concept_by_id = {item["id"]: item for item in concepts}
    protocol_by_id = {item["id"]: item for item in protocols}
    reasoning_sorted = sorted(
        reasoning_patterns,
        key=lambda item: (
            -(len(ensure_list(item.get("relacionado_protocolos"))) + len(ensure_list(item.get("relacionado_conceptos")))),
            item.get("id", ""),
        ),
    )

    def fallback_guide(idx: int) -> tuple[dict | None, dict | None]:
        reasoning = reasoning_sorted[idx] if idx < len(reasoning_sorted) else (reasoning_sorted[0] if reasoning_sorted else None)
        protocol = None
        if reasoning:
            for protocol_id in ensure_list(reasoning.get("relacionado_protocolos")):
                protocol = protocol_by_id.get(protocol_id)
                if protocol:
                    break
        if not protocol and protocols:
            protocol = protocols[min(idx, len(protocols) - 1)]
        return reasoning, protocol

    for item in items:
        guide_index = items.index(item)
        fallback_reasoning, fallback_protocol = fallback_guide(guide_index)
        if not item.get("contexto") and fallback_reasoning:
            item["contexto"] = f"Cuando se observa el patrón: {fallback_reasoning.get('trigger', '')}".strip()
        item["contexto"] = item.get("contexto") or GUIDE_CONTEXT_MAP.get(item["id"], "")
        if not item.get("interpretacion") and fallback_reasoning:
            item["interpretacion"] = fallback_reasoning.get("interpretacion", "")
        if not item.get("interpretacion") and fallback_protocol:
            item["interpretacion"] = compact(fallback_protocol.get("objetivo", ""), 220)
        if not item.get("factores_clave") and fallback_reasoning:
            item["factores_clave"] = ensure_list(fallback_reasoning.get("que_observar"))[:5]
        if not item.get("factores_clave") and fallback_protocol:
            item["factores_clave"] = [
                concept_by_id[concept_id]["termino"]
                for concept_id in ensure_list(fallback_protocol.get("relacionado_conceptos"))
                if concept_id in concept_by_id
            ][:5]
        if not item.get("errores_comunes") and fallback_reasoning:
            item["errores_comunes"] = ensure_list(fallback_reasoning.get("errores_comunes"))
        if not item.get("errores_comunes"):
            item["errores_comunes"] = [
                "Aplicar esta guía sin verificar antes que el contexto realmente corresponde al caso.",
                "Usar la interpretación como conclusión cerrada sin contrastarla con entrevista o protocolo.",
            ]
        item["cuando_no_aplica"] = GUIDE_NOT_APPLIES.get(item["id"], [])
        if not item["cuando_no_aplica"]:
            item["cuando_no_aplica"] = ["Cuando el patrón o contexto descrito no aparece en el caso."]
        item["nivel_riesgo"] = GUIDE_RISK.get(item["id"], "medio")
        related_concepts = detect_related_ids(
            normalize_text(" ".join([item.get("contexto", ""), item.get("interpretacion", ""), " ".join(ensure_list(item.get("factores_clave")))])),
            concept_tokens,
        )
        related_concepts.extend(GUIDE_CONCEPT_HINTS.get(item["id"], []))
        if fallback_reasoning:
            related_concepts.extend(ensure_list(fallback_reasoning.get("relacionado_conceptos")))
        if fallback_protocol:
            related_concepts.extend(ensure_list(fallback_protocol.get("relacionado_conceptos")))
        item["relacionado_conceptos"] = unique_preserve(related_concepts)
        related_protocols = []
        for protocol in protocols:
            if any(concept in ensure_list(protocol.get("relacionado_conceptos")) for concept in item["relacionado_conceptos"]):
                related_protocols.append(protocol["id"])
        if item["id"] == "guide_distancia":
            related_protocols.append("programa_de_sustitucion_temporal_para_trabajo_a_distancia")
        related_protocols.extend(GUIDE_PROTOCOL_HINTS.get(item["id"], []))
        if fallback_reasoning:
            related_protocols.extend(ensure_list(fallback_reasoning.get("relacionado_protocolos")))
        if fallback_protocol:
            related_protocols.append(fallback_protocol["id"])
        item["relacionado_protocolos"] = unique_preserve(related_protocols)
    write_json(path, items)
    return items


def enrich_faq(course_dir: Path, concepts: list[dict], protocols: list[dict]) -> list[dict]:
    path = course_dir / "03_academic/faq_candidates.json"
    items = load_json(path)
    concept_by_id = {item["id"]: item for item in concepts}
    protocol_by_id = {item["id"]: item for item in protocols}
    concept_tokens = build_concept_tokens(concepts)

    for item in items:
        related_concepts = list(FAQ_CONCEPT_HINTS.get(item["id"], []))
        if not related_concepts:
            related_concepts = detect_related_ids(item.get("pregunta", ""), concept_tokens)

        related_protocols = list(FAQ_PROTOCOL_HINTS.get(item["id"], []))
        if not related_protocols:
            question_text = normalize_text(item.get("pregunta", ""))
            for protocol in protocols:
                if normalize_text(protocol.get("nombre", "")) in question_text:
                    related_protocols.append(protocol["id"])
            if not related_protocols:
                for protocol in protocols:
                    if any(concept_id in ensure_list(protocol.get("relacionado_conceptos")) for concept_id in related_concepts):
                        related_protocols.append(protocol["id"])

        parts = []
        if item["id"] in FAQ_RESPONSE_HINTS:
            parts.append(FAQ_RESPONSE_HINTS[item["id"]])
        for concept_id in related_concepts[:2]:
            concept = concept_by_id.get(concept_id)
            if concept:
                parts.append(concept.get("explicacion_simple") or concept.get("definicion"))
        for protocol_id in related_protocols[:1]:
            protocol = protocol_by_id.get(protocol_id)
            if protocol and protocol.get("cuando_usarlo"):
                parts.append(f"En la práctica del curso esto aparece en {protocol['nombre']}.")
        response = compact(" ".join(part for part in parts if part), 420)
        item["respuesta"] = response or item.get("respuesta", "")
        item["relacionado_conceptos"] = unique_preserve(related_concepts)
        item["relacionado_protocolos"] = unique_preserve(related_protocols)
        item["tipo_usuario"] = "alumno"
        item["confidence"] = "high" if item["respuesta"] else "low"
    write_json(path, items)
    return items


def enrich_course_manifest(course_dir: Path) -> None:
    path = course_dir / "06_catalog/course_manifest.json"
    manifest = load_json(path)
    curso = manifest.get("curso", "holobiomagnetismo_2021")
    linea = manifest.get("linea", "salud")
    concepts = load_json(course_dir / "03_academic/concepts.json") if (course_dir / "03_academic/concepts.json").exists() else []
    reasoning = load_json(course_dir / "04_therapeutic/reasoning_patterns.json") if (course_dir / "04_therapeutic/reasoning_patterns.json").exists() else []
    intake = load_json(course_dir / "04_therapeutic/intake_questions.json") if (course_dir / "04_therapeutic/intake_questions.json").exists() else []
    guides = load_json(course_dir / "04_therapeutic/interpretation_guides.json") if (course_dir / "04_therapeutic/interpretation_guides.json").exists() else []
    protocols = load_json(course_dir / "05_protocols/protocols.json") if (course_dir / "05_protocols/protocols.json").exists() else []

    top_concepts = sorted(
        concepts,
        key=lambda item: (
            -(
                len(ensure_list(item.get("relacionado_protocolos")))
                + len(ensure_list(item.get("relacionado_reasoning")))
                + len(ensure_list(item.get("relacionado_conceptos")))
            ),
            item.get("id", ""),
        ),
    )[:4]
    top_reasoning = sorted(
        reasoning,
        key=lambda item: (
            -(len(ensure_list(item.get("relacionado_protocolos"))) + len(ensure_list(item.get("relacionado_conceptos")))),
            item.get("id", ""),
        ),
    )[:2]
    top_guides = sorted(
        guides,
        key=lambda item: (
            -(len(ensure_list(item.get("relacionado_protocolos"))) + len(ensure_list(item.get("relacionado_conceptos")))),
            item.get("id", ""),
        ),
    )[:2]
    top_intake = sorted(
        intake,
        key=lambda item: (
            -(len(ensure_list(item.get("relacionado_reasoning"))) + len(ensure_list(item.get("relacionado_protocolos"))) + len(ensure_list(item.get("relacionado_conceptos")))),
            item.get("id", ""),
        ),
    )[:4]
    top_protocols = sorted(
        protocols,
        key=lambda item: (
            -(len(ensure_list(item.get("relacionado_conceptos"))) + len(ensure_list(item.get("relacionado_reasoning"))) + len(ensure_list(item.get("pasos")))),
            item.get("id", ""),
        ),
    )[:4]

    manifest["entry_points"] = {
        "aprendizaje": [
            {"tipo": "concepto", "id": item["id"], "curso": curso, "linea": linea, "source": item.get("source", "merged"), "confidence": item.get("confidence", "high")}
            for item in top_concepts
        ],
        "terapia": [
            *[
                {"tipo": "reasoning", "id": item["id"], "curso": curso, "linea": linea, "source": item.get("source", "merged"), "confidence": item.get("confidence", "high")}
                for item in top_reasoning
            ],
            *[
                {"tipo": "guide", "id": item["id"], "curso": curso, "linea": linea, "source": item.get("source", "merged"), "confidence": item.get("confidence", "high")}
                for item in top_guides
            ],
            *[
                {"tipo": "intake", "id": item["id"], "curso": curso, "linea": linea, "source": item.get("source", "merged"), "confidence": item.get("confidence", "high")}
                for item in top_intake[:2]
            ],
        ][:4],
        "protocolos": [
            {"tipo": "protocol", "id": item["id"], "curso": curso, "linea": linea, "source": item.get("source", "merged"), "confidence": item.get("confidence", "high")}
            for item in top_protocols
        ],
    }
    manifest["mapa_conocimiento"] = {
        "conceptos_centrales": [item["id"] for item in top_concepts],
        "reasoning_clave": [item["id"] for item in top_reasoning],
        "preguntas_de_entrada": [item["id"] for item in top_intake],
        "guias_interpretativas": [item["id"] for item in top_guides],
        "protocolos_clave": [item["id"] for item in top_protocols],
    }
    write_json(path, manifest)


def write_connection_map(course_dir: Path, concepts: list[dict], reasoning_patterns: list[dict], protocols: list[dict]) -> None:
    concept_to_protocol = []
    concept_to_reasoning = []
    reasoning_to_protocol = []

    for concept in concepts:
        for protocol_id in ensure_list(concept.get("relacionado_protocolos")):
            concept_to_protocol.append(
                {
                    "id": f"{concept['id']}__{protocol_id}",
                    "curso": concept["curso"],
                    "linea": concept["linea"],
                    "source": "merged",
                    "confidence": "high",
                    "concept_id": concept["id"],
                    "protocol_id": protocol_id,
                }
            )
        for reasoning_id in ensure_list(concept.get("relacionado_reasoning")):
            concept_to_reasoning.append(
                {
                    "id": f"{concept['id']}__{reasoning_id}",
                    "curso": concept["curso"],
                    "linea": concept["linea"],
                    "source": "merged",
                    "confidence": "high",
                    "concept_id": concept["id"],
                    "reasoning_id": reasoning_id,
                }
            )

    for reasoning in reasoning_patterns:
        for protocol_id in ensure_list(reasoning.get("relacionado_protocolos")):
            reasoning_to_protocol.append(
                {
                    "id": f"{reasoning['id']}__{protocol_id}",
                    "curso": reasoning["curso"],
                    "linea": reasoning["linea"],
                    "source": "merged",
                    "confidence": "high",
                    "reasoning_id": reasoning["id"],
                    "protocol_id": protocol_id,
                }
            )

    write_json(
        course_dir / "09_connection_map.json",
        {
            "id": "connection_map",
            "curso": concepts[0]["curso"] if concepts else "",
            "linea": concepts[0]["linea"] if concepts else "",
            "source": "merged",
            "confidence": "high",
            "concept_to_protocol": concept_to_protocol,
            "concept_to_reasoning": concept_to_reasoning,
            "reasoning_to_protocol": reasoning_to_protocol,
        },
    )


def iter_dict_objects(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from iter_dict_objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_dict_objects(item)


def check_core_fields(collection_name: str, items: list[dict]) -> list[str]:
    issues = []
    for item in items:
        missing = [field for field in CORE_FIELDS if field not in item or item.get(field) in (None, "")]
        if missing:
            issues.append(f"{collection_name}:{item.get('id', 'sin_id')} sin campos base: {', '.join(sorted(missing))}")
    return issues


def audit_json_file_core_fields(path: Path) -> list[str]:
    issues = []
    if not path.exists():
        return issues
    payload = load_json(path)
    for obj in iter_dict_objects(payload):
        if {"id", "curso", "linea", "source", "confidence"} & set(obj.keys()):
            missing = [field for field in CORE_FIELDS if obj.get(field) in (None, "")]
            if missing:
                issues.append(f"{path.name}:{obj.get('id', 'sin_id')} sin campos base: {', '.join(sorted(missing))}")
    return issues


def build_advanced_audit(course_dir: Path, concepts: list[dict], faqs: list[dict], protocols: list[dict], reasoning: list[dict]) -> None:
    errors_criticos = []
    mejoras_aplicadas = [
        "Se añadieron relaciones explícitas entre conceptos, razonamientos y protocolos.",
        "Se enriquecieron pasos de protocolos con puntos de decisión, errores comunes y criterios de avance.",
        "Se enriquecieron preguntas de intake con flujo, prioridad y siguiente_posible.",
        "Se completaron respuestas de FAQ con base en conceptos y protocolos del propio curso.",
        "Se convirtió course_manifest.json en un router con entry_points por uso.",
    ]
    elementos_debiles = []
    elementos_excelentes = []
    campos_faltantes = []

    all_ids = []
    all_ids.extend(item["id"] for item in concepts)
    all_ids.extend(item["id"] for item in faqs)
    all_ids.extend(item["id"] for item in protocols)
    all_ids.extend(item["id"] for item in reasoning)
    duplicates = [item for item, count in Counter(all_ids).items() if count > 1]
    if duplicates:
        errors_criticos.append(f"IDs duplicados detectados: {', '.join(duplicates)}")

    for name, items in [
        ("concepts", concepts),
        ("faq_candidates", faqs),
        ("protocols", protocols),
        ("reasoning_patterns", reasoning),
    ]:
        campos_faltantes.extend(check_core_fields(name, items))

    for path in [
        course_dir / "03_academic" / "glossary.json",
        course_dir / "03_academic" / "module_summaries.json",
        course_dir / "04_therapeutic" / "intake_questions.json",
        course_dir / "04_therapeutic" / "interpretation_guides.json",
        course_dir / "05_protocols" / "protocols.json",
        course_dir / "06_catalog" / "course_manifest.json",
        course_dir / "09_connection_map.json",
    ]:
        campos_faltantes.extend(audit_json_file_core_fields(path))

    for faq in faqs:
        if not faq.get("respuesta"):
            errors_criticos.append(f"FAQ sin respuesta utilizable: {faq['id']}")
        if len(normalize_text(faq.get("pregunta", "")).split()) < 4:
            elementos_debiles.append(f"FAQ poco específica: {faq['id']}")
        if faq.get("confidence") == "low":
            elementos_debiles.append(f"FAQ con respuesta todavía débil: {faq['id']}")

    for concept in concepts:
        if not concept.get("definicion") or not concept.get("explicacion_simple"):
            errors_criticos.append(f"Concepto incompleto: {concept['id']}")
        linked_count = (
            len(ensure_list(concept.get("relacionado_protocolos")))
            + len(ensure_list(concept.get("relacionado_reasoning")))
            + len(ensure_list(concept.get("relacionado_conceptos")))
        )
        if linked_count < 2 and not concept.get("cuando_se_aplica"):
            elementos_debiles.append(f"Concepto poco conectado: {concept['id']}")
        if concept.get("modulo") and concept.get("relacionado_protocolos") and concept.get("relacionado_reasoning"):
            elementos_excelentes.append(f"Concepto bien anclado y conectable: {concept['id']}")
        if concept.get("confidence") == "low" and linked_count < 2:
            elementos_debiles.append(f"Concepto todavía ambiguo para recuperación: {concept['id']}")

    for protocol in protocols:
        if not protocol.get("pasos"):
            errors_criticos.append(f"Protocolo sin pasos: {protocol['id']}")
            continue
        if len(protocol.get("pasos", [])) >= 4 and protocol.get("relacionado_conceptos") and protocol.get("relacionado_reasoning"):
            elementos_excelentes.append(f"Protocolo operativo y conectado: {protocol['id']}")
        for step in protocol.get("pasos", []):
            if not step.get("instruccion"):
                errors_criticos.append(f"Paso sin instrucción: {step.get('id')}")
            if not step.get("decision_points"):
                elementos_debiles.append(f"Paso con decisión poco guiada: {step.get('id')}")

    for item in reasoning:
        if not item.get("acciones_sugeridas") or not item.get("preguntas_clave"):
            errors_criticos.append(f"Patrón terapéutico incompleto: {item['id']}")
        if item.get("preguntas_clave") and item.get("relacionado_protocolos") and item.get("relacionado_conceptos"):
            elementos_excelentes.append(f"Patrón terapéutico accionable: {item['id']}")

    guides = load_json(course_dir / "04_therapeutic" / "interpretation_guides.json")
    for guide in guides:
        if not guide.get("errores_comunes") or not guide.get("cuando_no_aplica"):
            errors_criticos.append(f"Guía interpretativa incompleta: {guide['id']}")
        if not guide.get("relacionado_protocolos"):
            elementos_debiles.append(f"Guía poco conectada operativamente: {guide['id']}")

    payload = {
        "errores_criticos": unique_preserve(errors_criticos),
        "mejoras_aplicadas": unique_preserve(mejoras_aplicadas),
        "campos_faltantes": unique_preserve(campos_faltantes)[:30],
        "elementos_debiles": unique_preserve(elementos_debiles)[:20],
        "elementos_excelentes": unique_preserve(elementos_excelentes)[:20],
        "listo_para_rag": len(errors_criticos) == 0 and len(campos_faltantes) == 0,
    }
    write_json(course_dir / "08_advanced_audit_report.json", payload)


def main() -> None:
    course_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_COURSE_DIR
    if not course_dir.exists():
        raise SystemExit(f"No existe el curso: {course_dir}")

    course_slug, linea = infer_course_metadata(course_dir)
    rename_concept_ids_across_course(course_dir)

    intake_questions = load_json(course_dir / "04_therapeutic/intake_questions.json")
    reasoning_patterns = load_json(course_dir / "04_therapeutic/reasoning_patterns.json")
    concepts = load_json(course_dir / "03_academic/concepts.json")

    protocols, protocol_maps = enrich_protocols(course_dir, course_slug, linea, concepts, reasoning_patterns)
    concepts, concept_reasoning_map = enrich_concepts(course_dir, protocols, reasoning_patterns)
    reasoning_patterns = enrich_reasoning(course_dir, intake_questions, concept_reasoning_map, protocol_maps)
    intake_questions = enrich_intake(course_dir, reasoning_patterns)
    enrich_guides(course_dir, protocols, concepts, reasoning_patterns)
    faqs = enrich_faq(course_dir, concepts, protocols)
    enrich_course_manifest(course_dir)
    write_connection_map(course_dir, concepts, reasoning_patterns, protocols)
    build_advanced_audit(course_dir, concepts, faqs, protocols, reasoning_patterns)


if __name__ == "__main__":
    main()
