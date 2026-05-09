from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional, Union

from .models import (
    ClinicalWarning,
    IntakeQuestion,
    InterpretationGuide,
    ReasoningPattern,
    TherapeuticKnowledgeBase,
    TherapeuticObservation,
)


DEFAULT_COURSE_SLUG = "course_holobiomagnetismo_2021"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_course_dir(course_slug: str = DEFAULT_COURSE_SLUG) -> Path:
    root = _project_root()
    direct = root / "data" / "knowledge_units" / course_slug
    if direct.exists():
        return direct
    holo_app = root / "04_holoacademia_app" / "data" / "knowledge_units" / course_slug
    if holo_app.exists():
        return holo_app
    return direct


def _safe_load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _normalize_line(raw: str) -> str:
    value = (raw or "").strip().lower()
    return value or "salud"


def load_therapeutic_course_data(course_dir: Optional[Union[str, Path]] = None) -> TherapeuticKnowledgeBase:
    explicit = Path(course_dir) if course_dir else Path(os.getenv("THERAPEUTIC_ASSISTANT_COURSE_DIR", "")) if os.getenv("THERAPEUTIC_ASSISTANT_COURSE_DIR") else default_course_dir()
    course_dir_path = explicit if explicit.is_absolute() else (Path.cwd() / explicit)

    therapeutic_dir = course_dir_path / "04_therapeutic"
    protocols_dir = course_dir_path / "05_protocols"
    catalog_dir = course_dir_path / "06_catalog"
    academic_dir = course_dir_path / "03_academic"

    intake_raw = _safe_load_json(therapeutic_dir / "intake_questions.json", [])
    reasoning_raw = _safe_load_json(therapeutic_dir / "reasoning_patterns.json", [])
    guides_raw = _safe_load_json(therapeutic_dir / "interpretation_guides.json", [])
    observations_raw = _safe_load_json(therapeutic_dir / "therapeutic_observations.json", [])
    warnings_raw = _safe_load_json(therapeutic_dir / "clinical_warnings.json", [])
    protocols_raw = _safe_load_json(protocols_dir / "protocols.json", [])
    structured_protocols_raw = _safe_load_json(protocols_dir / "structured_case_protocols.json", [])
    manifest_raw = _safe_load_json(catalog_dir / "course_manifest.json", {})
    connection_map = _safe_load_json(course_dir_path / "09_connection_map.json", {})
    overview_raw = _safe_load_json(academic_dir / "course_overview.json", {})
    module_summaries = _safe_load_json(academic_dir / "module_summaries.json", [])
    concepts = _safe_load_json(academic_dir / "concepts.json", [])

    course_id = manifest_raw.get("curso") or overview_raw.get("curso") or course_dir_path.name
    line = _normalize_line(manifest_raw.get("linea") or overview_raw.get("linea") or "salud")

    warnings: list[str] = []

    intake_questions = [IntakeQuestion.from_dict(item) for item in intake_raw if isinstance(item, dict)]
    reasoning_patterns = [ReasoningPattern.from_dict(item) for item in reasoning_raw if isinstance(item, dict)]
    interpretation_guides = [InterpretationGuide.from_dict(item) for item in guides_raw if isinstance(item, dict)]
    therapeutic_observations = [TherapeuticObservation.from_dict(item) for item in observations_raw if isinstance(item, dict)]
    clinical_warnings = [ClinicalWarning.from_dict(item) for item in warnings_raw if isinstance(item, dict)]

    for collection in (
        intake_questions,
        reasoning_patterns,
        interpretation_guides,
        therapeutic_observations,
        clinical_warnings,
    ):
        for item in collection:
            if not item.curso:
                item.curso = course_id
            if not item.linea:
                item.linea = line

    if not intake_questions:
        warnings.append("No se encontró intake_questions.json o está vacío.")
    if not reasoning_patterns:
        warnings.append("No se encontró reasoning_patterns.json o está vacío.")
    if not interpretation_guides:
        warnings.append("No se encontró interpretation_guides.json o está vacío.")

    return TherapeuticKnowledgeBase(
        course_dir=course_dir_path,
        course_id=course_id,
        line=line,
        intake_questions=intake_questions,
        reasoning_patterns=reasoning_patterns,
        interpretation_guides=interpretation_guides,
        therapeutic_observations=therapeutic_observations,
        clinical_warnings=clinical_warnings,
        course_manifest=manifest_raw if isinstance(manifest_raw, dict) else {},
        connection_map=connection_map if isinstance(connection_map, dict) else {},
        course_overview=overview_raw if isinstance(overview_raw, dict) else {},
        module_summaries=module_summaries if isinstance(module_summaries, list) else [],
        concepts=concepts if isinstance(concepts, list) else [],
        protocols=protocols_raw if isinstance(protocols_raw, list) else [],
        structured_case_protocols=structured_protocols_raw if isinstance(structured_protocols_raw, list) else [],
        warnings=warnings,
    )
