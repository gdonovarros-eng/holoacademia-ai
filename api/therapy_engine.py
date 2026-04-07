from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CURATED_DISEASE_PROFILES_PATH = ROOT / "data" / "reference_processed" / "disease_profiles_curated_v1.json"
DISEASE_PROFILES_PATH = ROOT / "data" / "reference_processed" / "disease_profiles.json"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_value = re.sub(r"\s+", " ", ascii_value).strip()
    return ascii_value


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = _normalize_text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


@dataclass
class DiseaseProfile:
    canonical_name: str
    slug: str
    system_name: str
    priority_group: str
    orientation_summary: str
    possible_conflicts: list[str]
    guiding_questions: list[str]
    suggested_course_routes: list[str]
    release_protocol_routes: list[str]
    aliases: list[str]


@dataclass
class BroadDiseaseProfile:
    canonical_name: str
    slug: str
    system_name: str
    summary: str
    possible_origins: list[str]
    symptom_notes: list[str]
    support_methods: list[str]
    aliases: list[str]


@dataclass(frozen=True)
class SymptomHeuristic:
    systems: tuple[str, ...]
    conflicts: tuple[str, ...]
    questions: tuple[str, ...]
    reading_hint: str
    family_axes: tuple[str, ...] = ()
    course_routes: tuple[str, ...] = ()
    release_routes: tuple[str, ...] = ()


def _load_curated_profiles() -> list[DiseaseProfile]:
    payload = json.loads(CURATED_DISEASE_PROFILES_PATH.read_text(encoding="utf-8"))
    profiles = []
    for item in payload.get("profiles", []):
        aliases = item.get("aliases") or [item["canonical_name"]]
        profiles.append(
            DiseaseProfile(
                canonical_name=item["canonical_name"],
                slug=item["slug"],
                system_name=item["system_name"],
                priority_group=item["priority_group"],
                orientation_summary=item["orientation_summary"],
                possible_conflicts=item.get("possible_conflicts", []),
                guiding_questions=item.get("guiding_questions", []),
                suggested_course_routes=item.get("suggested_course_routes", []),
                release_protocol_routes=item.get("release_protocol_routes", []),
                aliases=aliases,
            )
        )
    return profiles


CURATED_PROFILES = _load_curated_profiles()


def _load_broad_profiles() -> list[BroadDiseaseProfile]:
    payload = json.loads(DISEASE_PROFILES_PATH.read_text(encoding="utf-8"))
    profiles = []
    for item in payload.get("profiles", []):
        profiles.append(
            BroadDiseaseProfile(
                canonical_name=item["canonical_name"],
                slug=item["slug"],
                system_name=item.get("system_name", ""),
                summary=_safe_text(item.get("summary")),
                possible_origins=[_safe_text(value) for value in item.get("possible_origins", []) if _safe_text(value)],
                symptom_notes=[_safe_text(value) for value in item.get("symptom_notes", []) if _safe_text(value)],
                support_methods=[_safe_text(value) for value in item.get("support_methods", []) if _safe_text(value)],
                aliases=[_safe_text(value) for value in item.get("aliases", []) if _safe_text(value)] or [item["canonical_name"]],
            )
        )
    return profiles


BROAD_PROFILES = _load_broad_profiles()


SYMPTOM_HEURISTICS: dict[str, SymptomHeuristic] = {
    "cabello": SymptomHeuristic(
        systems=("dermatologico", "emocional_mental"),
        conflicts=(
            "identidad y autoimagen a revisar",
            "estrés sostenido o sensación de pérdida",
            "inseguridad respecto al propio valor o dirección",
        ),
        questions=(
            "¿Desde cuándo comenzó la caída y qué estaba ocurriendo en tu vida en ese periodo?",
            "¿Has vivido pérdida de seguridad, cambio de imagen, presión o desgaste sostenido?",
            "¿Qué parte de tu identidad o confianza sientes debilitada hoy?",
        ),
        reading_hint="La caída de cabello invita a revisar desgaste, identidad, autoimagen y momentos de estrés prolongado.",
        family_axes=("línea paterna y valoración personal a revisar",),
        course_routes=("analisis_sistemico", "rastreo_conflictologico_tegumentario", "rastreo_de_masa_conflictual"),
        release_routes=("sistemico",),
    ),
    "alopecia": SymptomHeuristic(
        systems=("dermatologico", "emocional_mental"),
        conflicts=(
            "identidad y autoimagen a revisar",
            "estrés sostenido o sensación de pérdida",
            "inseguridad respecto al propio valor o dirección",
        ),
        questions=(
            "¿Qué cambio fuerte viviste antes de notar la pérdida de cabello?",
            "¿Qué parte de tu identidad o seguridad sientes comprometida?",
        ),
        reading_hint="La alopecia invita a revisar estrés, identidad y sensación de vulnerabilidad personal.",
        family_axes=("línea paterna y valoración personal a revisar",),
        course_routes=("analisis_sistemico", "rastreo_conflictologico_tegumentario"),
        release_routes=("sistemico",),
    ),
    "decision": SymptomHeuristic(
        systems=("emocional_mental", "neurosensorial"),
        conflicts=(
            "indecisión o pérdida de dirección",
            "miedo a elegir y sostener una postura",
            "inseguridad frente a consecuencias",
        ),
        questions=(
            "¿Qué elección importante te está costando sostener en este momento?",
            "¿Qué sientes que puedes perder si decides con claridad?",
            "¿Hay una figura cuya aprobación estás buscando antes de elegir?",
        ),
        reading_hint="La dificultad para elegir sugiere revisar dirección vital, miedo a equivocarse y dependencia de validación.",
        family_axes=("vínculo con autoridad o aprobación a revisar", "línea paterna a revisar"),
        course_routes=("analisis_sistemico", "rastreo_de_masa_conflictual", "analisis_madre_padre_si_aplica"),
        release_routes=("sistemico", "sentimental_si_aplica"),
    ),
    "eleccion": SymptomHeuristic(
        systems=("emocional_mental", "neurosensorial"),
        conflicts=(
            "indecisión o pérdida de dirección",
            "miedo a elegir y sostener una postura",
            "inseguridad frente a consecuencias",
        ),
        questions=(
            "¿Qué decisión sientes que has pospuesto?",
            "¿Qué costo emocional asocias con elegir?",
            "¿Quién podría reaccionar si tomas tu propia dirección?",
        ),
        reading_hint="La pérdida de firmeza en la elección apunta a revisar seguridad interna, autonomía y permiso para decidir.",
        family_axes=("vínculo con autoridad o aprobación a revisar", "línea paterna a revisar"),
        course_routes=("analisis_sistemico", "rastreo_de_masa_conflictual"),
        release_routes=("sistemico",),
    ),
    "ansiedad": SymptomHeuristic(
        systems=("emocional_mental",),
        conflicts=("hipervigilancia", "miedo anticipatorio", "pérdida de control"),
        questions=(
            "¿Qué escenario futuro te mantiene en alerta constante?",
            "¿Qué necesitas controlar para sentir seguridad?",
        ),
        reading_hint="La ansiedad sugiere revisar alarma interna, hipervigilancia y temor a perder control.",
        course_routes=("analisis_sistemico", "rastreo_de_masa_conflictual"),
        release_routes=("sistemico", "estres_postraumatico_si_aplica"),
    ),
    "insomnio": SymptomHeuristic(
        systems=("emocional_mental", "neurosensorial"),
        conflicts=("hiperalerta", "preocupación persistente", "dificultad para soltar"),
        questions=(
            "¿Qué pensamiento o preocupación se activa al llegar la noche?",
            "¿Qué sientes que no puedes soltar o bajar de intensidad?",
        ),
        reading_hint="El insomnio suele invitar a revisar hiperalerta, pensamientos repetitivos y dificultad para soltar control.",
        course_routes=("analisis_sistemico", "rastreo_de_masa_conflictual"),
        release_routes=("sistemico",),
    ),
}


def _collect_symptom_texts(case_payload: dict[str, Any]) -> list[str]:
    symptoms = []
    for item in _safe_list(case_payload.get("current_symptoms")):
        fields = [
            _safe_text(item.get("symptom_name")),
            _safe_text(item.get("approximate_age_onset")),
            _safe_text(item.get("symptom_characteristics")),
            _safe_text(item.get("symptom_frequency")),
            _safe_text(item.get("therapist_notes")),
        ]
        text = " ".join(part for part in fields if part).strip()
        if text:
            symptoms.append(text)

    for item in _safe_list(case_payload.get("history_events")):
        fields = [
            _safe_text(item.get("event_name")),
            _safe_text(item.get("approximate_age_onset")),
            _safe_text(item.get("event_characteristics")),
            _safe_text(item.get("event_frequency")),
            _safe_text(item.get("event_notes")),
        ]
        text = " ".join(part for part in fields if part).strip()
        if text:
            symptoms.append(text)

    free_fields = [
        _safe_text(case_payload.get("consultation_reason")),
        _safe_text(case_payload.get("session_goal")),
        _safe_text(case_payload.get("main_emotion")),
        _safe_text(case_payload.get("recent_trigger")),
        _safe_text(case_payload.get("current_emotional_context")),
        _safe_text(case_payload.get("emotional_context_at_onset")),
        _safe_text(case_payload.get("what_bothers_today")),
        _safe_text(case_payload.get("perceived_impediments")),
        _safe_text(case_payload.get("family_conflicts_notes")),
        _safe_text(case_payload.get("transgenerational_patterns_notes")),
        _safe_text(case_payload.get("free_case_notes")),
    ]
    symptoms.extend([field for field in free_fields if field])
    return symptoms


def _collect_context_texts(case_payload: dict[str, Any]) -> list[str]:
    texts: list[str] = []

    consultant = case_payload.get("consultant") if isinstance(case_payload.get("consultant"), dict) else {}
    current_partner = case_payload.get("current_partner") if isinstance(case_payload.get("current_partner"), dict) else {}
    parents = case_payload.get("parents") if isinstance(case_payload.get("parents"), dict) else {}
    grandparents = case_payload.get("grandparents") if isinstance(case_payload.get("grandparents"), dict) else {}

    texts.extend([_safe_text(consultant.get("full_name")), _safe_text(current_partner.get("full_name"))])

    for group in (parents, grandparents):
        for item in group.values():
            if isinstance(item, dict):
                texts.append(_safe_text(item.get("full_name")))

    for collection_name in ("significant_partners", "children", "siblings"):
        for item in _safe_list(case_payload.get(collection_name)):
            if isinstance(item, dict):
                texts.extend(_safe_text(value) for value in item.values() if isinstance(value, str))

    return [text for text in texts if text]


def _match_profiles(case_payload: dict[str, Any]) -> list[dict[str, Any]]:
    haystacks = [_normalize_text(text) for text in _collect_symptom_texts(case_payload)]
    combined = "\n".join(haystacks)
    matches: list[dict[str, Any]] = []

    for profile in CURATED_PROFILES:
        aliases = profile.aliases or [profile.canonical_name]
        match_terms = [_normalize_text(alias) for alias in aliases if alias]
        score = 0
        for term in match_terms:
            if len(term) < 4:
                continue
            if term in combined:
                score += 5
        for conflict in profile.possible_conflicts:
            term = _normalize_text(conflict)
            if len(term) < 5:
                continue
            if term in combined:
                score += 1
        if score <= 0:
            continue
        matches.append(
            {
                "canonical_name": profile.canonical_name,
                "slug": profile.slug,
                "system_name": profile.system_name,
                "priority_group": profile.priority_group,
                "score": score,
                "orientation_summary": profile.orientation_summary,
                "possible_conflicts": profile.possible_conflicts,
                "guiding_questions": profile.guiding_questions,
                "suggested_course_routes": profile.suggested_course_routes,
                "release_protocol_routes": profile.release_protocol_routes,
            }
        )

    matches.sort(key=lambda item: (-item["score"], item["canonical_name"]))
    return matches


def _match_broad_profiles(case_payload: dict[str, Any]) -> list[dict[str, Any]]:
    haystacks = [_normalize_text(text) for text in _collect_symptom_texts(case_payload)]
    combined = "\n".join(haystacks)
    matches: list[dict[str, Any]] = []

    for profile in BROAD_PROFILES:
        score = 0
        for term in [_normalize_text(alias) for alias in profile.aliases if alias]:
            if len(term) < 4:
                continue
            if term in combined:
                score += 4

        if score <= 0:
            continue

        matches.append(
            {
                "canonical_name": profile.canonical_name,
                "slug": profile.slug,
                "system_name": profile.system_name,
                "priority_group": "amplio",
                "score": score,
                "orientation_summary": profile.summary,
                "possible_conflicts": profile.possible_origins[:5],
                "guiding_questions": [],
                "suggested_course_routes": ["analisis_sistemico", "rastreo_de_masa_conflictual"],
                "release_protocol_routes": ["sistemico"],
            }
        )

    matches.sort(key=lambda item: (-item["score"], item["canonical_name"]))
    return matches


def _detect_symptom_heuristics(case_payload: dict[str, Any]) -> list[SymptomHeuristic]:
    combined = " ".join(_normalize_text(text) for text in _collect_symptom_texts(case_payload))
    found: list[SymptomHeuristic] = []
    for term, heuristic in SYMPTOM_HEURISTICS.items():
        if term in combined:
            found.append(heuristic)
    return found


def _detect_family_axes(case_payload: dict[str, Any]) -> list[str]:
    axes = []
    text_fields = [
        _safe_text(case_payload.get("family_conflicts_notes")),
        _safe_text(case_payload.get("family_secrets_notes")),
        _safe_text(case_payload.get("transgenerational_patterns_notes")),
        _safe_text(case_payload.get("important_relationships_notes")),
        _safe_text(case_payload.get("current_emotional_context")),
        _safe_text(case_payload.get("emotional_context_at_onset")),
    ]
    blob = _normalize_text(" ".join(text_fields))
    if any(term in blob for term in ("mama", "madre", "materna")):
        axes.append("vínculo materno a revisar")
    if any(term in blob for term in ("papa", "padre", "paterno")):
        axes.append("vínculo paterno a revisar")
    if any(term in blob for term in ("pareja", "relacion", "relación", "ex")):
        axes.append("vínculos de pareja a revisar")
    if any(term in blob for term in ("secreto", "injusticia", "abuelo", "abuela", "ancestro", "transgeneracional")):
        axes.append("línea transgeneracional a revisar")

    parents = case_payload.get("parents") if isinstance(case_payload.get("parents"), dict) else {}
    grandparents = case_payload.get("grandparents") if isinstance(case_payload.get("grandparents"), dict) else {}
    significant_partners = _safe_list(case_payload.get("significant_partners"))
    children = _safe_list(case_payload.get("children"))
    siblings = _safe_list(case_payload.get("siblings"))

    father = parents.get("father") if isinstance(parents.get("father"), dict) else {}
    mother = parents.get("mother") if isinstance(parents.get("mother"), dict) else {}

    if _safe_text(father.get("full_name")) or any(
        _safe_text((grandparents.get(key) or {}).get("full_name"))
        for key in ("paternal_grandfather", "paternal_grandmother")
    ):
        axes.append("línea paterna a revisar")

    if _safe_text(mother.get("full_name")) or any(
        _safe_text((grandparents.get(key) or {}).get("full_name"))
        for key in ("maternal_grandfather", "maternal_grandmother")
    ):
        axes.append("línea materna a revisar")

    if any(
        _safe_text((person or {}).get("death_date"))
        for person in list(parents.values()) + list(grandparents.values())
        if isinstance(person, dict)
    ):
        axes.append("duelos o muertes del sistema familiar a revisar")

    if significant_partners or _safe_text(((case_payload.get("current_partner") or {}) if isinstance(case_payload.get("current_partner"), dict) else {}).get("full_name")):
        axes.append("vínculos de pareja a revisar")

    if children:
        axes.append("línea filial y rol de cuidado a revisar")

    if siblings:
        axes.append("lugar entre hermanos y dinámica fraterna a revisar")

    return _dedupe_keep_order(axes)


def analyze_case(case_payload: dict[str, Any]) -> dict[str, Any]:
    matches = _match_profiles(case_payload)
    broad_matches = _match_broad_profiles(case_payload)
    heuristics = _detect_symptom_heuristics(case_payload)

    top_matches = matches[:5]
    if not top_matches:
        top_matches = broad_matches[:5]

    priority_symptoms = [
        _safe_text(item.get("symptom_name"))
        for item in _safe_list(case_payload.get("current_symptoms"))
        if _safe_text(item.get("symptom_name"))
    ]
    priority_symptoms = _dedupe_keep_order(priority_symptoms)[:6]

    probable_systems = _dedupe_keep_order([item["system_name"] for item in top_matches])[:5]
    probable_systems = _dedupe_keep_order(
        probable_systems + [system for heuristic in heuristics for system in heuristic.systems]
    )[:6]
    probable_conflicts = _dedupe_keep_order(
        [conflict for item in top_matches for conflict in item.get("possible_conflicts", [])]
        + [conflict for heuristic in heuristics for conflict in heuristic.conflicts]
    )[:10]
    guiding_questions = _dedupe_keep_order(
        [question for item in top_matches for question in item.get("guiding_questions", [])]
        + [question for heuristic in heuristics for question in heuristic.questions]
    )[:10]
    suggested_routes = _dedupe_keep_order(
        [route for item in top_matches for route in item.get("suggested_course_routes", [])]
        + [route for heuristic in heuristics for route in heuristic.course_routes]
    )[:8]
    release_routes = _dedupe_keep_order(
        [route for item in top_matches for route in item.get("release_protocol_routes", [])]
        + [route for heuristic in heuristics for route in heuristic.release_routes]
    )[:6]
    family_axes = _dedupe_keep_order(
        _detect_family_axes(case_payload) + [axis for heuristic in heuristics for axis in heuristic.family_axes]
    )

    matched_names = [item["canonical_name"] for item in top_matches]
    if matched_names:
        reading = (
            "La lectura inicial del caso sugiere priorizar "
            + ", ".join(matched_names)
            + " como ejes de observación, integrando síntomas, contexto emocional y antecedentes relacionales."
        )
    else:
        symptom_blob = _collect_symptom_texts(case_payload)
        symptom_phrase = ", ".join(symptom_blob[:2]) if symptom_blob else "los síntomas capturados"
        heuristic_hints = _dedupe_keep_order([heuristic.reading_hint for heuristic in heuristics])[:2]
        reading = (
            f"El caso sugiere comenzar la lectura a partir de {symptom_phrase}, revisando su temporalidad, "
            "el contexto relacional y la forma en que el paciente lo está sosteniendo hoy."
        )
        if heuristic_hints:
            reading += " " + " ".join(heuristic_hints)

    mass_conflict_hypothesis = ""
    if probable_conflicts:
        mass_conflict_hypothesis = (
            "Posible masa conflictual a explorar: "
            + "; ".join(probable_conflicts[:3])
            + "."
        )
    elif probable_systems:
        mass_conflict_hypothesis = (
            "Todavía no se define una masa conflictual cerrada, pero conviene abrir rastreo por "
            + ", ".join(probable_systems[:3])
            + "."
        )

    if not guiding_questions:
        guiding_questions = [
            "¿Cuándo comenzó exactamente el síntoma o cuándo se hizo más evidente?",
            "¿Qué situación importante estaba viviendo el paciente en ese periodo?",
            "¿Qué cambia, empeora o alivia el síntoma en la vida cotidiana?",
            "¿Qué vínculo, decisión o presión emocional acompaña hoy este malestar?",
        ]

    return {
        "reading": reading,
        "priority_symptoms": priority_symptoms,
        "matched_profiles": top_matches,
        "probable_systems": probable_systems,
        "probable_conflicts": probable_conflicts,
        "family_axes": family_axes,
        "mass_conflict_hypothesis": mass_conflict_hypothesis,
        "guiding_questions": guiding_questions,
        "suggested_course_routes": suggested_routes,
        "release_protocol_routes": release_routes,
    }


__all__ = ["analyze_case"]
