from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path("/Users/m2/Documents/New project")
DEFAULT_COURSE_DIR = ROOT / "data/knowledge_units/course_holobiomagnetismo_2021"


def load_json(path: Path):
    return json.loads(path.read_text())


def dump_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def index_by_id(items: list[dict]) -> dict[str, dict]:
    return {str(item.get("id", "")): item for item in items}


def merge_unique(values: list[str], additions: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in [*(values or []), *(additions or [])]:
        text = str(value).strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        merged.append(text)
    return merged


def upsert_concept(concepts: list[dict], spec: dict, report: dict) -> None:
    by_id = index_by_id(concepts)
    current = by_id.get(spec["id"])
    if current is None:
        concepts.append(deepcopy(spec))
        report["concepts_added"].append(spec["id"])
        report["aliases_added"].extend(
            {"concept_id": spec["id"], "alias": alias} for alias in spec.get("aliases", [])
        )
        return

    before_aliases = set(str(x).strip().lower() for x in current.get("aliases", []))
    current["termino"] = spec["termino"]
    current["aliases"] = merge_unique(current.get("aliases", []), spec.get("aliases", []))
    current["definicion"] = spec["definicion"]
    current["explicacion_simple"] = spec["explicacion_simple"]
    current["explicacion_extendida"] = spec["explicacion_extendida"]
    current["modulo"] = spec["modulo"]
    current["curso"] = spec["curso"]
    current["linea"] = spec["linea"]
    current["source"] = spec["source"]
    current["confidence"] = spec["confidence"]
    current["relacionado_conceptos"] = merge_unique(
        current.get("relacionado_conceptos", []),
        spec.get("relacionado_conceptos", []),
    )
    current["relacionado_protocolos"] = merge_unique(
        current.get("relacionado_protocolos", []),
        spec.get("relacionado_protocolos", []),
    )
    current["relacionado_reasoning"] = merge_unique(
        current.get("relacionado_reasoning", []),
        spec.get("relacionado_reasoning", []),
    )
    if spec["id"] not in report["concepts_strengthened"]:
        report["concepts_strengthened"].append(spec["id"])
    after_aliases = set(str(x).strip().lower() for x in current.get("aliases", []))
    for alias in current.get("aliases", []):
        if str(alias).strip().lower() not in before_aliases:
            report["aliases_added"].append({"concept_id": spec["id"], "alias": alias})


def upsert_glossary(glossary: list[dict], spec: dict, report: dict) -> None:
    by_id = index_by_id(glossary)
    current = by_id.get(spec["id"])
    if current is None:
        glossary.append(deepcopy(spec))
        report["glossary_entries_added"].append(spec["id"])
        return
    current.update(spec)


def strengthen_module_summary(summaries: list[dict], module_id: str, temas: list[str], extra_sentence: str = "") -> None:
    for summary in summaries:
        if summary.get("id") != module_id:
            continue
        summary["temas_clave"] = merge_unique(summary.get("temas_clave", []), temas)
        if extra_sentence and extra_sentence not in summary.get("resumen", ""):
            resumen = str(summary.get("resumen", "")).strip()
            summary["resumen"] = f"{resumen} {extra_sentence}".strip()
        break


def strengthen_existing_entries(concepts: list[dict], report: dict) -> None:
    by_id = index_by_id(concepts)
    updates = {
        "entrevista_de_rastreo": {
            "aliases": ["Entrevista inicial", "Ficha de rastreo", "Inicio del síntoma"],
            "relacionado_conceptos": ["cronologia_clinica", "recurrencia", "par_biomagnetico"],
        },
        "holobiomagnetismo": {
            "relacionado_conceptos": ["entrevista_de_rastreo", "par_biomagnetico", "cibertelepatia", "cinco_elementos"],
        },
        "molde_energetico": {
            "relacionado_conceptos": ["polaridad", "holobiomagnetismo"],
        },
    }
    for concept_id, update in updates.items():
        concept = by_id.get(concept_id)
        if not concept:
            continue
        before_aliases = set(str(x).strip().lower() for x in concept.get("aliases", []))
        concept["aliases"] = merge_unique(concept.get("aliases", []), update.get("aliases", []))
        concept["relacionado_conceptos"] = merge_unique(
            concept.get("relacionado_conceptos", []),
            update.get("relacionado_conceptos", []),
        )
        if concept_id not in report["concepts_strengthened"]:
            report["concepts_strengthened"].append(concept_id)
        for alias in concept.get("aliases", []):
            if str(alias).strip().lower() not in before_aliases:
                report["aliases_added"].append({"concept_id": concept_id, "alias": alias})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--course-dir", default=str(DEFAULT_COURSE_DIR))
    args = parser.parse_args()

    course_dir = Path(args.course_dir)
    academic_dir = course_dir / "03_academic"
    report_path = course_dir / "10_academic_enrichment_report.json"

    concepts_path = academic_dir / "concepts.json"
    glossary_path = academic_dir / "glossary.json"
    summaries_path = academic_dir / "module_summaries.json"

    concepts = load_json(concepts_path)
    glossary = load_json(glossary_path)
    summaries = load_json(summaries_path)

    report = {
        "concepts_added": [],
        "concepts_strengthened": [],
        "glossary_entries_added": [],
        "aliases_added": [],
        "weak_points_remaining": [
            "La taxonomía específica de microbios y listados de pares sigue viviendo más como contenido modular que como conceptos atómicos independientes.",
            "Algunos comandos de búsqueda siguen mejor representados en FAQ, resúmenes y material operativo que en una definición académica aislada.",
        ],
        "ready_for_academic_v1_close": True,
    }

    concept_specs = [
        {
            "id": "par_biomagnetico",
            "termino": "Par biomagnético",
            "aliases": ["Par biomagnetico", "Pares biomagnéticos", "Pares biomagneticos", "Pares", "Los pares"],
            "definicion": "Unidad operativa del curso formada por dos puntos que se rastrean juntos dentro de la búsqueda biomagnética.",
            "explicacion_simple": "Es la dupla de puntos que el alumno aprende a buscar cuando el curso pasa de microbiología a rastreo ordenado.",
            "explicacion_extendida": "En Holobiomagnetismo 2021, los pares biomagnéticos aparecen como parte de la secuencia de búsqueda del módulo 6. No se presentan solo como una lista, sino como una forma de organizar el rastreo por regiones, zonas, bloques y número de par dentro de una lógica clínica más amplia.",
            "modulo": "modulo_6",
            "curso": "holobiomagnetismo_2021",
            "linea": "salud",
            "source": "merged",
            "confidence": "high",
            "relacionado_conceptos": ["polaridad", "entrevista_de_rastreo", "holobiomagnetismo"],
            "relacionado_protocolos": ["rastreo_de_microorganismos_y_pares_biomagneticos"],
            "relacionado_reasoning": [],
        },
        {
            "id": "polaridad",
            "termino": "Polaridad",
            "aliases": ["Polaridad magnética", "Polaridad magnetica", "Positivo y negativo", "Campo bipolar", "Bipolaridad"],
            "definicion": "Condición bipolar del campo magnético con la que el curso interpreta la acción de los imanes durante el rastreo.",
            "explicacion_simple": "Sirve para entender que el imán no se trabaja como si tuviera un solo polo, sino como una relación de positivo y negativo.",
            "explicacion_extendida": "En la transcripción del curso se explica que todo imán genera un campo bipolar y que la práctica del curso se apoya en esa polaridad. Esta idea sostiene la lectura de campos magnéticos, toroides y la forma en que el imán interactúa con el molde energético del cuerpo.",
            "modulo": "modulo_4",
            "curso": "holobiomagnetismo_2021",
            "linea": "salud",
            "source": "merged",
            "confidence": "high",
            "relacionado_conceptos": ["par_biomagnetico", "molde_energetico", "yin_yang"],
            "relacionado_protocolos": [],
            "relacionado_reasoning": [],
        },
        {
            "id": "cronologia_clinica",
            "termino": "Cronología clínica",
            "aliases": ["Cronologia clínica", "Cronología", "Cronologia", "Inicio del síntoma", "Desde cuándo", "Desde cuando"],
            "definicion": "Ubicación temporal del inicio y evolución del síntoma dentro de la entrevista inicial del curso.",
            "explicacion_simple": "Es preguntar desde cuándo empezó algo y cómo ha ido apareciendo con el tiempo.",
            "explicacion_extendida": "La base académica del curso insiste en no quedarse en el síntoma aislado. La entrevista clínica orientada al rastreo pide registrar fecha aproximada de origen, evolución, frecuencia y factores que agravan o inhiben, para convertir la queja del paciente en información usable.",
            "modulo": "modulo_1",
            "curso": "holobiomagnetismo_2021",
            "linea": "salud",
            "source": "merged",
            "confidence": "high",
            "relacionado_conceptos": ["entrevista_de_rastreo", "recurrencia", "holobiomagnetismo"],
            "relacionado_protocolos": ["entrevista_inicial_de_rastreo"],
            "relacionado_reasoning": [],
        },
        {
            "id": "recurrencia",
            "termino": "Recurrencia",
            "aliases": ["Reaparición del síntoma", "Reaparicion del sintoma", "Frecuencia del síntoma", "Frecuencia del sintoma", "Cada cuánto", "Cada cuanto"],
            "definicion": "Patrón de repetición con el que un síntoma vuelve a aparecer y que el curso pide registrar como parte de la entrevista.",
            "explicacion_simple": "Es notar si algo vuelve cada día, cada semana, por temporadas o en ciertos momentos del año.",
            "explicacion_extendida": "En el material limpio se indica que la frecuencia del síntoma debe registrarse por día, semana o recurrencia anual cuando aplique. El curso usa esa recurrencia para pensar patrones y no quedarse solo con un episodio suelto.",
            "modulo": "modulo_1",
            "curso": "holobiomagnetismo_2021",
            "linea": "salud",
            "source": "merged",
            "confidence": "medium",
            "relacionado_conceptos": ["cronologia_clinica", "entrevista_de_rastreo"],
            "relacionado_protocolos": ["entrevista_inicial_de_rastreo"],
            "relacionado_reasoning": [],
        },
    ]

    glossary_specs = [
        {
            "id": "glosario_par_biomagnetico",
            "termino": "Par biomagnético",
            "definicion_corta": "Dupla de puntos que el curso rastrea como unidad operativa.",
            "curso": "holobiomagnetismo_2021",
            "linea": "salud",
            "modulo": "modulo_6",
            "seccion": "",
            "source": "merged",
            "confidence": "high",
            "referencia_concepto": "par_biomagnetico",
            "uso": "rápido",
        },
        {
            "id": "glosario_polaridad",
            "termino": "Polaridad",
            "definicion_corta": "Condición bipolar con la que se interpreta la acción del imán.",
            "curso": "holobiomagnetismo_2021",
            "linea": "salud",
            "modulo": "modulo_4",
            "seccion": "",
            "source": "merged",
            "confidence": "high",
            "referencia_concepto": "polaridad",
            "uso": "rápido",
        },
        {
            "id": "glosario_cronologia_clinica",
            "termino": "Cronología clínica",
            "definicion_corta": "Orden temporal del síntoma: cuándo empezó, cómo evoluciona y con qué frecuencia aparece.",
            "curso": "holobiomagnetismo_2021",
            "linea": "salud",
            "modulo": "modulo_1",
            "seccion": "",
            "source": "merged",
            "confidence": "high",
            "referencia_concepto": "cronologia_clinica",
            "uso": "rápido",
        },
        {
            "id": "glosario_recurrencia",
            "termino": "Recurrencia",
            "definicion_corta": "Forma repetitiva con la que vuelve un síntoma a lo largo del tiempo.",
            "curso": "holobiomagnetismo_2021",
            "linea": "salud",
            "modulo": "modulo_1",
            "seccion": "",
            "source": "merged",
            "confidence": "medium",
            "referencia_concepto": "recurrencia",
            "uso": "rápido",
        },
    ]

    for spec in concept_specs:
        upsert_concept(concepts, spec, report)
    for spec in glossary_specs:
        upsert_glossary(glossary, spec, report)

    strengthen_existing_entries(concepts, report)

    strengthen_module_summary(
        summaries,
        "modulo_1",
        ["Cronología clínica", "Recurrencia", "Entrevista de rastreo"],
        "Este bloque deja más clara la importancia de la cronología clínica, la recurrencia y la entrevista inicial como base académica del curso.",
    )
    strengthen_module_summary(
        summaries,
        "modulo_4",
        ["Polaridad", "Campos magnéticos", "Molde energético"],
        "También refuerza la idea de polaridad como base para entender el trabajo con imanes.",
    )
    strengthen_module_summary(
        summaries,
        "modulo_5",
        ["Entrevista de rastreo", "Ficha de control", "Área de rastreo"],
        "Se apoya en ficha de control, entrevista de rastreo y organización del área clínica.",
    )
    strengthen_module_summary(
        summaries,
        "modulo_6",
        ["Par biomagnético", "Pares biomagnéticos", "Secuencia de búsqueda", "Microbios"],
        "Aquí queda más visible el par biomagnético como nodo académico central del curso.",
    )

    concepts.sort(key=lambda item: str(item.get("id", "")))
    glossary.sort(key=lambda item: str(item.get("id", "")))
    summaries.sort(key=lambda item: str(item.get("id", "")))
    report["aliases_added"] = sorted(
        report["aliases_added"],
        key=lambda item: (item["concept_id"], item["alias"].lower()),
    )

    dump_json(concepts_path, concepts)
    dump_json(glossary_path, glossary)
    dump_json(summaries_path, summaries)
    dump_json(report_path, report)


if __name__ == "__main__":
    main()
