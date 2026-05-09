from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import (
    AcademicKnowledgeBase,
    Concept,
    FAQCandidate,
    GlossaryEntry,
    ModuleSummary,
)


DEFAULT_COURSE_SLUG = "course_holobiomagnetismo_2021"
DEFAULT_FALLBACK_TEXT_MAX_BYTES = 120_000


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_course_dir(course_slug: str = DEFAULT_COURSE_SLUG) -> Path:
    return _project_root() / "04_holoacademia_app" / "data" / "knowledge_units" / course_slug


def _safe_load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _safe_load_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        if path.stat().st_size > DEFAULT_FALLBACK_TEXT_MAX_BYTES:
            return ""
        with path.open("r", encoding="utf-8") as handle:
            return handle.read().strip()
    except Exception:
        return ""


def _normalize_line(raw: str) -> str:
    value = (raw or "").strip().lower()
    return value or "salud"


def _validate_concepts(concepts: list[Concept], warnings: list[str]) -> None:
    seen: set[str] = set()
    for concept in concepts:
        if not concept.id:
            warnings.append("Se detectó un concepto sin id.")
        if concept.id in seen:
            warnings.append(f"Se detectó un id de concepto duplicado: {concept.id}")
        seen.add(concept.id)
        if not (concept.definicion or concept.explicacion_simple or concept.explicacion_extendida):
            warnings.append(f"Concepto con poco contenido explicativo: {concept.id}")


def load_academic_course_data(course_dir: str | Path | None = None) -> AcademicKnowledgeBase:
    explicit = Path(course_dir) if course_dir else Path(os.getenv("ACADEMIC_ASSISTANT_COURSE_DIR", "")) if os.getenv("ACADEMIC_ASSISTANT_COURSE_DIR") else default_course_dir()
    course_dir_path = explicit if explicit.is_absolute() else (Path.cwd() / explicit)
    warnings: list[str] = []

    academic_dir = course_dir_path / "03_academic"
    catalog_dir = course_dir_path / "06_catalog"
    clean_dir = course_dir_path / "02_clean"

    concepts_raw = _safe_load_json(academic_dir / "concepts.json", [])
    glossary_raw = _safe_load_json(academic_dir / "glossary.json", [])
    modules_raw = _safe_load_json(academic_dir / "module_summaries.json", [])
    faq_raw = _safe_load_json(academic_dir / "faq_candidates.json", [])
    overview_raw = _safe_load_json(academic_dir / "course_overview.json", {})
    manifest_raw = _safe_load_json(catalog_dir / "course_manifest.json", {})
    transcript_inventory = _safe_load_json(catalog_dir / "transcript_inventory.json", [])
    module_inventory = _safe_load_json(catalog_dir / "module_inventory.json", [])

    course_id = (
        manifest_raw.get("curso")
        or overview_raw.get("curso")
        or course_dir_path.name
    )
    line = _normalize_line(manifest_raw.get("linea") or overview_raw.get("linea") or "salud")

    concepts = [Concept.from_dict(item) for item in concepts_raw if isinstance(item, dict)]
    glossary = [GlossaryEntry.from_dict(item) for item in glossary_raw if isinstance(item, dict)]
    module_summaries = [ModuleSummary.from_dict(item) for item in modules_raw if isinstance(item, dict)]
    faq_candidates = [FAQCandidate.from_dict(item) for item in faq_raw if isinstance(item, dict)]

    for collection in (concepts, glossary, module_summaries, faq_candidates):
        for item in collection:
            if hasattr(item, "curso") and not getattr(item, "curso"):
                setattr(item, "curso", course_id)
            if hasattr(item, "linea") and not getattr(item, "linea"):
                setattr(item, "linea", line)

    use_fallback_texts = os.getenv("ACADEMIC_ASSISTANT_ENABLE_FALLBACK_TEXTS", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    clean_fallback_texts: dict[str, str] = {}
    if use_fallback_texts:
        clean_fallback_texts = {
            "merged_clean_content": _safe_load_text(clean_dir / "merged_clean_content.txt"),
            "clean_transcript": _safe_load_text(clean_dir / "clean_transcript.txt"),
            "clean_manual": _safe_load_text(clean_dir / "clean_manual.txt"),
            "manual_extracted": _safe_load_text(clean_dir / "manual_extracted.txt"),
        }
        clean_fallback_texts = {key: value for key, value in clean_fallback_texts.items() if value}

    _validate_concepts(concepts, warnings)
    if not glossary:
        warnings.append("No se encontró glossary.json o está vacío.")
    if not module_summaries:
        warnings.append("No se encontró module_summaries.json o está vacío.")

    return AcademicKnowledgeBase(
        course_dir=course_dir_path,
        course_id=course_id,
        line=line,
        concepts=concepts,
        glossary=glossary,
        module_summaries=module_summaries,
        faq_candidates=faq_candidates,
        course_overview=overview_raw if isinstance(overview_raw, dict) else {},
        course_manifest=manifest_raw if isinstance(manifest_raw, dict) else {},
        transcript_inventory=transcript_inventory if isinstance(transcript_inventory, list) else [],
        module_inventory=module_inventory if isinstance(module_inventory, list) else [],
        clean_fallback_texts=clean_fallback_texts,
        warnings=warnings,
    )
