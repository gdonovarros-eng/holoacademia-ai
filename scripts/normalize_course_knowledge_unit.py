from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COURSE_DIR = ROOT / "data" / "knowledge_units" / "course_holobiomagnetismo_2021"


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    stripped = stripped.lower().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", stripped).strip()


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    stripped = stripped.lower().replace("/", " ").replace("-", " ")
    stripped = re.sub(r"[^a-z0-9]+", "_", stripped)
    return stripped.strip("_")


def infer_course_metadata(course_dir: Path) -> tuple[str, str]:
    course_slug = course_dir.name.removeprefix("course_")
    candidate_paths = [
        course_dir / "06_catalog" / "course_manifest.json",
        course_dir / "01_sources" / "course_manifest_source.json",
        course_dir / "01_sources" / "metadata.json",
    ]
    linea_raw = ""
    for path in candidate_paths:
        if not path.exists():
            continue
        try:
            data = load_json(path)
        except Exception:
            continue
        if isinstance(data, dict):
            linea_raw = data.get("linea") or linea_raw
        if linea_raw:
            break
    linea = slugify(linea_raw) if linea_raw else ""
    return course_slug, linea


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item not in (None, "")]
    return [value] if value != "" else []


def compact(text: str, limit: int = 300) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[:limit]
    for marker in (". ", "; ", ": "):
        idx = cut.rfind(marker)
        if idx >= int(limit * 0.6):
            return cut[: idx + 1].strip()
    return cut.rstrip(" ,;:") + "…"


def split_listish(text: str) -> list[str]:
    if not text:
        return []
    items = []
    for chunk in re.split(r";|,|\sy\s", text):
        candidate = " ".join(chunk.split()).strip(" .")
        if candidate:
            items.append(candidate)
    return items


def extract_module_number(value) -> str:
    texts = [str(item) for item in ensure_list(value)]
    if not texts:
        return ""
    joined = " ".join(texts)
    match = re.search(r"modulo[s]?[_\s]+(\d+)", normalize_text(joined).replace("-", "_"))
    if match:
        return match.group(1)
    match = re.search(r"m[oó]dulo[s]?\s+(\d+)", joined, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    if len(texts) == 1 and re.fullmatch(r"\d+", texts[0].strip()):
        return texts[0].strip()
    return ""


def classify_source(values) -> str:
    texts = " ".join(normalize_text(v) for v in ensure_list(values))
    has_manual = "manual" in texts or "pdf" in texts
    has_transcript = "transcrip" in texts
    has_merged = "merged" in texts
    if has_merged or (has_manual and has_transcript):
        return "merged"
    if has_manual:
        return "manual"
    if has_transcript:
        return "transcript"
    return "merged"


def parse_modulo_and_seccion(value) -> tuple[str, str]:
    texts = [str(item) for item in ensure_list(value)]
    if not texts:
        return "", ""
    joined = " ".join(texts)
    normalized_joined = normalize_text(joined).replace("-", "_").replace(" ", "_")
    numbers = re.findall(r"m[oó]dulo[s]?\s+(\d+)", joined, flags=re.IGNORECASE)
    if not numbers:
        normalized_matches = re.findall(r"modulo[s]?_([0-9_]+)", normalized_joined)
        for match in normalized_matches:
            numbers.extend([piece for piece in match.split("_") if piece.isdigit()])
    if not numbers and len(texts) == 1 and re.fullmatch(r"\d+", texts[0].strip()):
        numbers = [texts[0].strip()]
    unique_numbers = []
    for number in numbers:
        if number not in unique_numbers:
            unique_numbers.append(number)
    modulo = ""
    if unique_numbers:
        modulo = f"modulo_{unique_numbers[0]}" if len(unique_numbers) == 1 else "modulos_" + "_".join(unique_numbers)
    cleaned_joined = normalize_text(joined)
    seccion = ""
    if cleaned_joined in {"manual", "transcript", "merged"}:
        return modulo, ""
    if not modulo and cleaned_joined:
        seccion = slugify(cleaned_joined[:80])
    return modulo, seccion


def infer_aliases(term: str, aliases: list[str]) -> list[str]:
    seen = set()
    ordered = []

    def add(value: str) -> None:
        cleaned = " ".join((value or "").split()).strip()
        if not cleaned:
            return
        key = normalize_text(cleaned)
        if key in seen or key == normalize_text(term):
            return
        seen.add(key)
        ordered.append(cleaned)

    for alias in aliases:
        add(alias)

    ascii_term = "".join(ch for ch in unicodedata.normalize("NFKD", term) if not unicodedata.combining(ch))
    if ascii_term != term:
        add(ascii_term)

    unslashed = term.replace("/", " ").replace("  ", " ").strip()
    if unslashed != term:
        add(unslashed)

    return ordered


def infer_confidence(source: str, required_fields: list[str], low_if_inferred: bool = False) -> str:
    if any(not field for field in required_fields):
        return "low"
    if low_if_inferred:
        return "low"
    if source in {"manual", "transcript", "merged"}:
        return "high"
    return "low"


def observation_list(value) -> list[str]:
    if isinstance(value, list):
        return [compact(str(item), 180) for item in value if str(item).strip()]
    return [compact(item, 180) for item in split_listish(str(value))]


def make_unique_id(base: str, seen: dict[str, int]) -> str:
    if base not in seen:
        seen[base] = 1
        return base
    seen[base] += 1
    return f"{base}_{seen[base]}"


def find_related_concepts(text: str, concept_index: dict[str, str]) -> list[str]:
    lowered = normalize_text(text)
    related = []
    for term, concept_id in concept_index.items():
        if term and term in lowered and concept_id not in related:
            related.append(concept_id)
    return related[:6]


INTAKE_OBJECTIVE_BY_CATEGORY = {
    "motivo_consulta": "delimitar motivo de consulta",
    "clasificacion": "clasificar el síntoma en plano físico, psicoemocional o mixto",
    "caracterizacion": "obtener descripción fenomenológica del síntoma",
    "cronologia": "determinar cronología clínica",
    "moduladores": "identificar factores que agravan, alivian o disparan",
    "conflicto": "ubicar evento crítico asociado al cuadro",
    "seguimiento": "evaluar continuidad del conflicto en el tiempo",
    "seguridad": "registrar antecedentes y condiciones de control",
    "emocional": "identificar emoción predominante y su localización corporal",
    "patrones": "detectar recurrencia o repetición del cuadro",
    "lectura_energetica": "orientar lectura energética por cinco elementos",
}

INTAKE_WHEN_BY_CATEGORY = {
    "motivo_consulta": ["al inicio de la entrevista clínica"],
    "clasificacion": ["durante la apertura de entrevista"],
    "caracterizacion": ["cuando el paciente describe el síntoma de forma vaga"],
    "cronologia": ["antes del rastreo principal", "cuando se necesita ubicar el origen del cuadro"],
    "moduladores": ["después de caracterizar el síntoma"],
    "conflicto": ["cuando el cuadro parece ligado a un evento crítico"],
    "seguimiento": ["cuando el conflicto o síntoma se ha cronificado"],
    "seguridad": ["antes de intervención con imanes o rastreo"],
    "emocional": ["cuando se abre trabajo emocional o EFT Pro"],
    "patrones": ["cuando el cuadro aparece por episodios o ciclos"],
    "lectura_energetica": ["cuando se desea orientar lectura por cinco elementos"],
}

REASONING_ACTIONS = {
    "pattern_vaguedad_sintoma": ["pedir descripción concreta del síntoma", "registrar localización y cualidad"],
    "pattern_recurrencia": ["registrar periodicidad", "explorar episodios previos similares"],
    "pattern_origen_aproximado": ["ubicar etapa vital aproximada", "anotar referencia temporal útil"],
    "pattern_terapia_empieza_en_entrevista": ["profundizar memoria y asociaciones", "observar cambios emocionales durante la entrevista"],
    "pattern_subyacente_vs_sintoma": ["leer estado energético global", "priorizar desequilibrio de fondo sobre síntoma aislado"],
    "pattern_molde_organico": ["rastrear molde energético del órgano", "considerar antecedente quirúrgico sin descartar lectura energética"],
    "pattern_qi_miedo": ["evaluar dinámica agua/riñón", "explorar miedo y contracción corporal"],
    "pattern_qi_enojo": ["evaluar madera/hígado/vesícula", "explorar rabia presente o retenida"],
    "pattern_qi_tristeza": ["evaluar metal/pulmón/intestino grueso", "explorar tristeza y desconexión"],
    "pattern_metal_social": ["explorar vínculo con figura paterna", "preguntar por conexión social y círculos elegidos"],
    "pattern_madera_direccion": ["explorar decisiones pendientes", "preguntar por dirección vital"],
    "pattern_fuego_expresion": ["explorar expresión de ideas y proyectos", "observar estado del Shen y la mente consciente"],
    "pattern_canal_exceso": ["revisar sobrecarga energética general", "no limitar la lectura a un punto local"],
    "pattern_busqueda_ordenada": ["declarar comando de búsqueda", "comprobar programa antes de rastrear"],
    "pattern_conflicto_emocional": ["identificar emoción principal", "priorizar abordaje emocional si el caso lo requiere"],
}

GUIDE_COMMON_ERRORS = {
    "guide_entrevista": ["tratar la etiqueta médica como dato suficiente", "omitir cronología o moduladores del síntoma"],
    "guide_5_elementos_global": ["leer solo el síntoma del día", "usar los elementos como equivalencias rígidas"],
    "guide_emocion_qi": ["separar emoción y cuerpo", "interpretar la emoción sin observar dirección del Qi"],
    "guide_organos_y_moldes": ["descartar un órgano solo por ausencia anatómica"],
    "guide_metal": ["reducir metal a pulmón e intestino grueso sin mirar vínculo social"],
    "guide_madera": ["leer madera solo como enojo sin revisar dirección o decisión"],
    "guide_distancia": ["trabajar a distancia sin comprobación de identidad", "omitir aceptación del sustituto"],
}


def normalize_concepts(course_dir: Path, course_slug: str, linea: str, report: dict) -> tuple[list[dict], dict[str, str]]:
    path = course_dir / "03_academic" / "concepts.json"
    raw = load_json(path)
    normalized = []
    seen_ids: dict[str, int] = {}
    concept_index: dict[str, str] = {}

    for item in raw:
        term = item.get("termino", "").strip()
        base_id = slugify(term)
        item_id = make_unique_id(base_id, seen_ids)
        source = classify_source([item.get("fuente_principal"), item.get("fuente_secundaria")])
        modulo, seccion = parse_modulo_and_seccion(item.get("modulo o tema") or item.get("modulo_o_tema") or item.get("modulo"))
        definicion = compact(item.get("definicion") or item.get("explicacion_simple") or item.get("explicacion_extendida"), 280)
        explicacion_simple = compact(item.get("explicacion_simple") or item.get("definicion") or item.get("explicacion_extendida"), 320)
        explicacion_extendida = compact(item.get("explicacion_extendida") or item.get("explicacion_simple") or item.get("definicion"), 900)
        confidence = infer_confidence(source, [term, definicion, explicacion_simple, explicacion_extendida], low_if_inferred=not modulo and not seccion)
        aliases = infer_aliases(term, ensure_list(item.get("aliases")))
        concept = {
            "id": item_id,
            "termino": term,
            "aliases": aliases,
            "definicion": definicion,
            "explicacion_simple": explicacion_simple,
            "explicacion_extendida": explicacion_extendida,
            "modulo": modulo,
            "seccion": seccion,
            "curso": course_slug,
            "linea": linea,
            "source": source,
            "confidence": confidence,
        }
        if not definicion or not explicacion_simple or not explicacion_extendida:
            report["campos_faltantes"].append(f"concepts.json::{item_id} tuvo campos explicativos incompletos y se completaron por arrastre interno.")
            report["mejoras_aplicadas"].append(f"Se consolidaron definiciones y explicaciones del concepto {item_id}.")
        normalized.append(concept)
        concept_index[normalize_text(term)] = item_id
        for alias in aliases:
            concept_index.setdefault(normalize_text(alias), item_id)

    write_json(path, normalized)
    return normalized, concept_index


def normalize_glossary(course_dir: Path, course_slug: str, linea: str, concepts: list[dict], report: dict) -> None:
    path = course_dir / "03_academic" / "glossary.json"
    normalized = []
    for concept in concepts:
        normalized.append(
            {
                "id": f"glosario_{concept['id']}",
                "termino": concept["termino"],
                "definicion_corta": compact(concept["definicion"], 160),
                "curso": course_slug,
                "linea": linea,
                "modulo": concept["modulo"],
                "seccion": concept["seccion"],
                "source": concept["source"],
                "confidence": concept["confidence"],
            }
        )
    write_json(path, normalized)
    report["mejoras_aplicadas"].append("Se homogeneizó glossary.json usando el schema académico común.")


def normalize_module_summaries(course_dir: Path, course_slug: str, linea: str, concepts: list[dict], report: dict) -> None:
    path = course_dir / "03_academic" / "module_summaries.json"
    raw = load_json(path)
    concept_terms = [(normalize_text(item["termino"]), item["termino"]) for item in concepts]
    normalized = []
    for item in raw:
        module_num = extract_module_number([item.get("module_number"), item.get("modulo"), item.get("id")])
        summary = compact(item.get("summary") or item.get("summary_text") or " ".join(ensure_list(item.get("summary_points"))), 1200)
        title = item.get("title") or item.get("titulo") or f"Módulo {module_num}"
        source = classify_source(item.get("sources"))
        temas_clave = []
        lowered = normalize_text(" ".join([title, item.get("focus", ""), summary]))
        for normalized_term, original_term in concept_terms:
            if normalized_term and normalized_term in lowered and original_term not in temas_clave:
                temas_clave.append(original_term)
        if not temas_clave and item.get("focus"):
            temas_clave = [compact(item["focus"], 120)]
        if not summary:
            if temas_clave:
                summary = compact(f"Módulo dedicado a {title.lower()}. Temas clave: {', '.join(temas_clave)}.", 320)
            else:
                summary = compact(f"Módulo dedicado a {title.lower()}.", 220)
        normalized.append(
            {
                "id": f"modulo_{module_num}",
                "titulo": title,
                "resumen": summary,
                "temas_clave": temas_clave[:6],
                "curso": course_slug,
                "linea": linea,
                "modulo": f"modulo_{module_num}" if module_num else "",
                "seccion": "",
                "source": source,
                "confidence": infer_confidence(source, [title, summary], low_if_inferred=False if module_num else True),
            }
        )
    write_json(path, normalized)
    report["mejoras_aplicadas"].append("Se normalizó module_summaries.json a campos estables de resumen y temas clave.")


def enrich_concepts_with_modules(course_dir: Path, report: dict) -> None:
    concepts_path = course_dir / "03_academic" / "concepts.json"
    glossary_path = course_dir / "03_academic" / "glossary.json"
    summaries_path = course_dir / "03_academic" / "module_summaries.json"

    concepts = load_json(concepts_path)
    glossary = load_json(glossary_path)
    summaries = load_json(summaries_path)

    summary_texts = []
    for summary in summaries:
        haystack = normalize_text(
            " ".join(
                [
                    summary.get("titulo", ""),
                    summary.get("resumen", ""),
                    " ".join(ensure_list(summary.get("temas_clave"))),
                ]
            )
        )
        summary_texts.append((summary.get("modulo", ""), haystack))

    glossary_by_term = {normalize_text(item.get("termino", "")): item for item in glossary}

    updated = 0
    for concept in concepts:
        if concept.get("modulo"):
            continue
        variants = [concept.get("termino", "")] + ensure_list(concept.get("aliases"))
        matches = []
        for modulo, haystack in summary_texts:
            for variant in variants:
                token = normalize_text(variant)
                if token and token in haystack:
                    matches.append(modulo)
                    break
        unique_matches = []
        for match in matches:
            if match and match not in unique_matches:
                unique_matches.append(match)
        if len(unique_matches) == 1:
            concept["modulo"] = unique_matches[0]
            concept["confidence"] = "high"
            glossary_item = glossary_by_term.get(normalize_text(concept.get("termino", "")))
            if glossary_item is not None:
                glossary_item["modulo"] = unique_matches[0]
                glossary_item["confidence"] = "high"
            updated += 1

    if updated:
        write_json(concepts_path, concepts)
        write_json(glossary_path, glossary)
        report["mejoras_aplicadas"].append(f"Se asignó módulo aproximado a {updated} conceptos y entradas de glosario cuando hubo coincidencia única con module_summaries.json.")


def normalize_course_overview(course_dir: Path, course_slug: str, linea: str, report: dict) -> None:
    path = course_dir / "03_academic" / "course_overview.json"
    raw = load_json(path)
    normalized = {
        "id": "course_overview",
        "curso": course_slug,
        "linea": linea,
        "modulo": "",
        "seccion": "overview_academico",
        "source": "merged",
        "confidence": "high",
        "nombre_curso": raw.get("course_name") or raw.get("nombre_del_curso"),
        "tipo": raw.get("tipo", ""),
        "nota_edicion": raw.get("edition_note", ""),
        "descripcion": raw.get("description", ""),
        "ejes_principales": ensure_list(raw.get("main_axes") or raw.get("temas_principales")),
        "posicionamiento": raw.get("positioning", ""),
        "prerrequisitos": ensure_list(raw.get("prerequisites")),
        "modulos_detectados": ensure_list(raw.get("detected_modules")),
    }
    write_json(path, normalized)


def normalize_faq(course_dir: Path, course_slug: str, linea: str, report: dict) -> None:
    path = course_dir / "03_academic" / "faq_candidates.json"
    raw = load_json(path)
    normalized = []
    seen: dict[str, int] = {}
    for item in raw:
        question = item.get("question") or item.get("pregunta") or ""
        faq_id = make_unique_id(f"faq_{slugify(question)[:50]}", seen)
        normalized.append(
            {
                "id": faq_id,
                "pregunta": question,
                "respuesta": compact(item.get("answer") or item.get("respuesta_breve") or "", 320),
                "curso": course_slug,
                "linea": linea,
                "modulo": "",
                "seccion": "faq_academico",
                "source": classify_source(item.get("source")),
                "confidence": "high" if question and (item.get("answer") or item.get("respuesta_breve")) else "low",
            }
        )
    write_json(path, normalized)


def normalize_intake(course_dir: Path, course_slug: str, linea: str, concept_index: dict[str, str], report: dict) -> None:
    path = course_dir / "04_therapeutic" / "intake_questions.json"
    raw = load_json(path)
    normalized = []
    seen: dict[str, int] = {}
    for item in raw:
        question = item.get("question") or item.get("pregunta") or ""
        category = item.get("category", "")
        item_id = make_unique_id(slugify(item.get("id") or question), seen)
        source = classify_source(item.get("source"))
        modulo, _ = parse_modulo_and_seccion([item.get("modulo"), item.get("module"), item.get("source_detail")])
        seccion = slugify(category) if category else "entrevista_clinica"
        objective = INTAKE_OBJECTIVE_BY_CATEGORY.get(category, compact(item.get("why_it_matters") or item.get("objetivo") or "", 120))
        if not objective:
            objective = "orientar entrevista clínica"
        normalized.append(
            {
                "id": item_id,
                "pregunta": question,
                "objetivo": objective,
                "cuando_usarla": INTAKE_WHEN_BY_CATEGORY.get(category, ["durante entrevista clínica"]),
                "relacionado_con": find_related_concepts(question + " " + (item.get("why_it_matters") or ""), concept_index),
                "curso": course_slug,
                "linea": linea,
                "modulo": modulo,
                "seccion": seccion,
                "source": source,
                "confidence": infer_confidence(source, [question, objective], low_if_inferred=False),
            }
        )
    write_json(path, normalized)
    report["mejoras_aplicadas"].append("Se completaron objetivos y metadatos en intake_questions.json.")


def normalize_reasoning_patterns(course_dir: Path, course_slug: str, linea: str, concept_index: dict[str, str], report: dict) -> None:
    path = course_dir / "04_therapeutic" / "reasoning_patterns.json"
    raw = load_json(path)
    normalized = []
    seen: dict[str, int] = {}
    for item in raw:
        original_id = item.get("id", "")
        pattern_id = make_unique_id(slugify(original_id.replace("pattern_", "patron_")), seen)
        trigger = item.get("trigger") or item.get("si_aparece") or ""
        observacion = item.get("que_observar") or item.get("observar") or []
        observe_list = observation_list(observacion)
        interpretacion = item.get("interpretacion") or item.get("considerar") or ""
        modulo, _ = parse_modulo_and_seccion([item.get("modulo"), item.get("module"), item.get("source_detail")])
        normalized.append(
            {
                "id": pattern_id,
                "trigger": trigger,
                "interpretacion": compact(interpretacion, 260),
                "que_observar": observe_list,
                "acciones_sugeridas": REASONING_ACTIONS.get(original_id, ["profundizar entrevista", "contrastar con rastreo clínico"]),
                "curso": course_slug,
                "linea": linea,
                "modulo": modulo,
                "seccion": "razonamiento_terapeutico",
                "source": classify_source(item.get("source")),
                "confidence": infer_confidence(classify_source(item.get("source")), [trigger, interpretacion], low_if_inferred=False),
            }
        )
    write_json(path, normalized)


def normalize_interpretation_guides(course_dir: Path, course_slug: str, linea: str, report: dict) -> None:
    path = course_dir / "04_therapeutic" / "interpretation_guides.json"
    raw = load_json(path)
    normalized = []
    seen: dict[str, int] = {}
    for item in raw:
        guide_id = make_unique_id(slugify(item.get("id", "")), seen)
        title = item.get("titulo", "")
        context = item.get("uso") or title
        source = classify_source(item.get("source"))
        modulo, _ = parse_modulo_and_seccion([item.get("modulo"), item.get("module"), item.get("source_detail")])
        normalized.append(
            {
                "id": guide_id,
                "contexto": context,
                "interpretacion": item.get("lectura") or item.get("interpretacion") or "",
                "factores_clave": ensure_list(item.get("senales") or item.get("factores_clave")),
                "errores_comunes": GUIDE_COMMON_ERRORS.get(item.get("id", ""), []),
                "curso": course_slug,
                "linea": linea,
                "modulo": modulo,
                "seccion": "guias_de_interpretacion",
                "source": source,
                "confidence": infer_confidence(source, [context, item.get("lectura") or item.get("interpretacion") or ""], low_if_inferred=False),
            }
        )
    write_json(path, normalized)


def normalize_observations(course_dir: Path, course_slug: str, linea: str, concept_index: dict[str, str]) -> None:
    path = course_dir / "04_therapeutic" / "therapeutic_observations.json"
    raw = load_json(path)
    normalized = []
    seen: dict[str, int] = {}
    for item in raw:
        text = item.get("observacion", "")
        item_id = make_unique_id(f"observacion_{slugify(item.get('id') or text)[:50]}", seen)
        source = classify_source(item.get("source"))
        modulo, _ = parse_modulo_and_seccion([item.get("modulo"), item.get("module"), item.get("source_detail")])
        normalized.append(
            {
                "id": item_id,
                "observacion": text,
                "utilidad_terapeutica": "Ayuda a orientar observación clínica y criterio del caso.",
                "relacionado_con": find_related_concepts(text, concept_index),
                "curso": course_slug,
                "linea": linea,
                "modulo": modulo,
                "seccion": "observaciones_terapeuticas",
                "source": source,
                "confidence": infer_confidence(source, [text], low_if_inferred=False),
            }
        )
    write_json(path, normalized)


def normalize_warnings(course_dir: Path, course_slug: str, linea: str) -> None:
    path = course_dir / "04_therapeutic" / "clinical_warnings.json"
    raw = load_json(path)
    normalized = []
    seen: dict[str, int] = {}
    for item in raw:
        warning = item.get("warning") or item.get("advertencia") or ""
        item_id = make_unique_id(f"advertencia_{slugify(item.get('id') or warning)[:50]}", seen)
        source = classify_source(item.get("source"))
        modulo, _ = parse_modulo_and_seccion([item.get("modulo"), item.get("module"), item.get("source_detail")])
        normalized.append(
            {
                "id": item_id,
                "tipo": item.get("tipo", "advertencia_general"),
                "advertencia": warning,
                "detalle": item.get("detalle", ""),
                "curso": course_slug,
                "linea": linea,
                "modulo": modulo,
                "seccion": "advertencias_clinicas",
                "source": source,
                "confidence": infer_confidence(source, [warning], low_if_inferred=False),
            }
        )
    write_json(path, normalized)


def normalize_protocols(course_dir: Path, course_slug: str, linea: str, report: dict) -> None:
    path = course_dir / "05_protocols" / "protocols.json"
    raw = load_json(path)
    normalized = []
    seen: dict[str, int] = {}
    for item in raw:
        protocol_id = make_unique_id(slugify(item.get("nombre") or item.get("id")), seen)
        source = classify_source(item.get("fuente") or item.get("source"))
        modulo, seccion = parse_modulo_and_seccion(item.get("fuente") or item.get("source"))
        confidence_value = item.get("confidence")
        if confidence_value not in {"high", "low"}:
            extraction_conf = item.get("confianza_extraccion", 0)
            confidence_value = "high" if isinstance(extraction_conf, (int, float)) and extraction_conf >= 0.8 else "low"
        steps = []
        for step in ensure_list(item.get("pasos")):
            instruction = step.get("instruccion", "").strip()
            if not instruction:
                report["errores_detectados"].append(f"{protocol_id} tenía un paso sin instrucción y fue descartado.")
                continue
            steps.append(
                {
                    "orden": step.get("orden"),
                    "titulo": step.get("titulo") or f"Paso {step.get('orden')}",
                    "instruccion": instruction,
                    "objetivo_del_paso": step.get("objetivo_del_paso") or "Ejecutar la acción terapéutica indicada.",
                    "que_observar": observation_list(step.get("que_observar")),
                    "que_registrar": observation_list(step.get("que_registrar")),
                    "notas": observation_list(step.get("notas")),
                }
            )
        if not steps:
            report["errores_detectados"].append(f"{protocol_id} no tenía pasos válidos y no se conservó.")
            continue
        normalized.append(
            {
                "id": protocol_id,
                "nombre": item.get("nombre", ""),
                "objetivo": item.get("objetivo", ""),
                "descripcion": item.get("descripcion", ""),
                "cuando_usarlo": observation_list(item.get("cuando_usarlo")),
                "prerequisitos": observation_list(item.get("prerequisitos")),
                "pasos": steps,
                "observaciones": observation_list(item.get("observaciones")),
                "advertencias": observation_list(item.get("advertencias")),
                "curso": course_slug,
                "linea": linea,
                "modulo": modulo,
                "seccion": seccion or "protocolos",
                "source": source,
                "confidence": confidence_value,
            }
        )
    write_json(path, normalized)
    report["mejoras_aplicadas"].append("Se estandarizó protocols.json, incluyendo listas y metadatos consistentes por protocolo.")


def normalize_catalog(course_dir: Path, course_slug: str, linea: str, module_summaries: list[dict], report: dict) -> None:
    manifest_path = course_dir / "06_catalog" / "course_manifest.json"
    manifest = load_json(manifest_path)
    normalized_manifest = {
        "id": "course_manifest",
        "curso": course_slug,
        "linea": linea,
        "modulo": "",
        "seccion": "catalogo_general",
        "source": "merged",
        "confidence": "high",
        "nombre_del_curso": manifest.get("nombre_del_curso", ""),
        "archivos_fuente_usados": ensure_list(manifest.get("archivos_fuente_usados")),
        "temas_principales": ensure_list(manifest.get("temas_principales")),
        "modulos_detectados": ensure_list(manifest.get("modulos_detectados")),
        "cantidad_de_conceptos_extraidos": manifest.get("cantidad_de_conceptos_extraidos", 0),
        "cantidad_de_patrones_terapeuticos_extraidos": manifest.get("cantidad_de_patrones_terapeuticos_extraidos", 0),
        "cantidad_de_protocolos_extraidos": manifest.get("cantidad_de_protocolos_extraidos", 0),
        "ambiguedades_detectadas": ensure_list(manifest.get("ambiguedades_detectadas")),
        "vacios_detectados": ensure_list(manifest.get("vacios_detectados")),
        "nivel_de_preparacion": manifest.get("nivel_de_preparacion", {}),
        "observacion_general": manifest.get("observacion_general", ""),
    }
    write_json(manifest_path, normalized_manifest)

    module_inventory_path = course_dir / "06_catalog" / "module_inventory.json"
    write_json(
        module_inventory_path,
        [
            {
                "id": f"inventory_{item['modulo'] or item['id']}",
                "curso": course_slug,
                "linea": linea,
                "modulo": item["modulo"],
                "seccion": item["seccion"],
                "titulo": item["titulo"],
                "estado": "listo",
                "source": item["source"],
                "confidence": "high" if item["modulo"] else item["confidence"],
            }
            for item in module_summaries
        ],
    )

    transcript_inventory_path = course_dir / "06_catalog" / "transcript_inventory.json"
    transcript_raw = load_json(transcript_inventory_path)
    grouped = defaultdict(list)
    for item in transcript_raw:
        module_number = item.get("module_number")
        if module_number in (None, ""):
            modulo_value = str(item.get("modulo", ""))
            match = re.search(r"(\d+)", modulo_value)
            module_number = match.group(1) if match else ""
        if not module_number:
            continue
        grouped[str(module_number)].append(item)
    transcript_inventory = []
    for module_number, items in sorted(grouped.items(), key=lambda pair: int(pair[0])):
        for index, item in enumerate(items, start=1):
            transcript_inventory.append(
                {
                    "id": f"transcript_modulo_{module_number}_bloque_{index}",
                    "curso": course_slug,
                    "linea": linea,
                    "modulo": f"modulo_{module_number}",
                    "seccion": f"bloque_{index}",
                    "fecha_proceso": item.get("fecha_proceso", ""),
                    "chars": item.get("chars", 0),
                    "source": "transcript",
                    "confidence": "high",
                }
            )
    write_json(transcript_inventory_path, transcript_inventory)

    if any(len(items) > 1 for items in grouped.values()):
        report["ambiguedades"].append("La transcripción conserva más de un bloque para el mismo número de módulo; se mantuvieron como bloques separados en transcript_inventory.json.")
    report["mejoras_aplicadas"].append("Se limpiaron los archivos de catálogo y se eliminaron artefactos de ejecución del inventario de módulos.")


def build_validation_report(course_dir: Path, report: dict) -> None:
    if not report["errores_detectados"]:
        report["errores_detectados"] = []
    if not report["campos_faltantes"]:
        report["campos_faltantes"] = []
    if not report["ambiguedades"]:
        report["ambiguedades"] = []
    if not report["mejoras_aplicadas"]:
        report["mejoras_aplicadas"] = []
    report["estado_general"] = "listo_para_uso"
    write_json(course_dir / "07_validation_report.json", report)


def main() -> None:
    course_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_COURSE_DIR
    if not course_dir.exists():
        raise SystemExit(f"No existe el curso: {course_dir}")

    course_slug, linea = infer_course_metadata(course_dir)
    report = {
        "errores_detectados": [],
        "campos_faltantes": [],
        "ambiguedades": [],
        "mejoras_aplicadas": [],
    }
    if course_slug == "holobiomagnetismo_2021":
        report["ambiguedades"].append(
            "El material del curso está identificado como 2021, pero parte del manual disponible indica edición 2020."
        )

    concepts, concept_index = normalize_concepts(course_dir, course_slug, linea, report)
    normalize_glossary(course_dir, course_slug, linea, concepts, report)
    normalize_module_summaries(course_dir, course_slug, linea, concepts, report)
    enrich_concepts_with_modules(course_dir, report)
    module_summaries = load_json(course_dir / "03_academic" / "module_summaries.json")
    normalize_course_overview(course_dir, course_slug, linea, report)
    normalize_faq(course_dir, course_slug, linea, report)
    normalize_intake(course_dir, course_slug, linea, concept_index, report)
    normalize_reasoning_patterns(course_dir, course_slug, linea, concept_index, report)
    normalize_interpretation_guides(course_dir, course_slug, linea, report)
    normalize_observations(course_dir, course_slug, linea, concept_index)
    normalize_warnings(course_dir, course_slug, linea)
    normalize_protocols(course_dir, course_slug, linea, report)
    normalize_catalog(course_dir, course_slug, linea, module_summaries, report)
    build_validation_report(course_dir, report)


if __name__ == "__main__":
    main()
