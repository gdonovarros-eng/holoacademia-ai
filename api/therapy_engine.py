from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from api.domain_knowledge import TeacherKnowledge


ROOT = Path(__file__).resolve().parent.parent
CURATED_DISEASE_PROFILES_PATH = ROOT / "data" / "reference_processed" / "disease_profiles_curated_v1.json"
DISEASE_PROFILES_PATH = ROOT / "data" / "reference_processed" / "disease_profiles.json"
RAW_DISEASE_ENTRIES_PATH = ROOT / "data" / "reference_processed" / "disease_entries_raw.json"
TEACHER_KNOWLEDGE_CACHE_PATH = ROOT / "data" / "teacher_knowledge_cache.json"


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


def _first_sentence(value: str) -> str:
    text = re.sub(r"\s+", " ", _safe_text(value))
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    return parts[0].strip().strip('"')


def _compact_conflict_text(value: str) -> str:
    raw = re.sub(r"\s+", " ", _safe_text(value))
    for marker in ['" El ', ". El ", ". Esto ", ". Puede ", "; El ", "; Esto "]:
        if marker in raw:
            raw = raw.split(marker, 1)[0]
            break
    text = _first_sentence(raw)
    if len(text) > 120 and "," in text:
        text = text.split(",", 1)[0].strip()
    text = re.sub(r"^[\"'“”]+|[\"'“”]+$", "", text).strip()
    if len(text) > 160:
        text = text[:157].rstrip(" ,;:.") + "..."
    return text


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


@dataclass
class RawDiseaseEntry:
    canonical_name: str
    slug: str
    summary: str
    biodescodificacion: str
    source_title: str


@dataclass(frozen=True)
class SymptomHeuristic:
    systems: tuple[str, ...]
    conflicts: tuple[str, ...]
    questions: tuple[str, ...]
    reading_hint: str
    family_axes: tuple[str, ...] = ()
    course_routes: tuple[str, ...] = ()
    release_routes: tuple[str, ...] = ()
    reference_causes: tuple[str, ...] = ()


SYSTEM_OPENING_GUIDANCE: dict[str, dict[str, Any]] = {
    "digestivo": {
        "opening_focus": "Abrir por lo que el consultante no ha podido digerir, la irritación sostenida y la situación que se está tragando sin resolver.",
        "interview_targets": [
            "Preguntar qué persona, convivencia o situación le cae pesada.",
            "Ubicar si el ardor aparece con enojo contenido, presión o mala digestión emocional.",
            "Revisar tema materno, nutrición afectiva, hogar o sensación de no ser bien recibido.",
        ],
        "protocol_focus": [
            "Abrir rastreo conflictológico digestivo.",
            "Validar componente microbiano si hay gastritis, hiperacidez, hernia hiatal o mala digestión persistente.",
            "Si el cuadro apunta a irritación sostenida, priorizar liberación sistémica después del rastreo.",
        ],
        "pair_queries": ["gastritis", "helicobacter pylori", "parasito digestivo"],
    },
    "neurosensorial": {
        "opening_focus": "Abrir por desorientación, hipervigilancia, saturación sensorial o dificultad para sostener dirección y equilibrio.",
        "interview_targets": [
            "Preguntar qué estaba ocurriendo cuando el consultante perdió seguridad, orientación o estabilidad.",
            "Explorar si el oído, el mareo o el vértigo se activan con presión, miedo o desorganización.",
            "Revisar si existe conflicto con dirección vital, amenaza, decisiones o sobrecarga nerviosa.",
        ],
        "protocol_focus": [
            "Abrir rastreo por sistema neurosensorial.",
            "Si hay tinnitus, mareo o vértigo, validar pares de oído, mastoides, temporal, bulbo o riñón según el cuadro.",
            "Si el evento fue abrupto o traumático, considerar liberación emocional o estrés postraumático.",
        ],
        "pair_queries": ["tinnitus", "vertigo", "mareo", "oido"],
    },
    "emocional_mental": {
        "opening_focus": "Abrir por el drama dominante, la emoción que no ha sido expresada y la forma en que el consultante se está sosteniendo o rompiendo internamente.",
        "interview_targets": [
            "Pedir el evento que más pesa hoy y el primero que dejó huella similar.",
            "Preguntar qué emoción no ha podido expresar con claridad.",
            "Observar si el cuadro se organiza por miedo, culpa, rechazo, pérdida o exceso de control.",
        ],
        "protocol_focus": [
            "Priorizar entrevista emocional estructurada antes de cerrar rastreo.",
            "Si el cuerpo cambió después de un evento abrupto, considerar liberación emocional o estrés postraumático.",
        ],
        "pair_queries": [],
    },
    "dermatologico": {
        "opening_focus": "Abrir por identidad, contacto, separación, autoimagen y sensación de exposición o desprotección.",
        "interview_targets": [
            "Preguntar qué separación, roce o herida de identidad acompañó el inicio.",
            "Explorar rechazo, vergüenza, invasión o falta de reconocimiento.",
        ],
        "protocol_focus": [
            "Abrir rastreo tegumentario y sistémico.",
            "Cruzar el síntoma con estrés sostenido y valoración personal.",
        ],
        "pair_queries": [],
    },
    "respiratorio": {
        "opening_focus": "Abrir por territorio, espacio vital, miedo, asfixia emocional y conflictos con aire, libertad o presencia de otros.",
        "interview_targets": [
            "Preguntar qué situación no le deja respirar en paz.",
            "Explorar duelo, amenaza, tristeza o invasión del espacio.",
        ],
        "protocol_focus": [
            "Abrir rastreo conflictológico respiratorio.",
            "Cruzar con duelo, miedo o presión del entorno antes de ir al rastreo final.",
        ],
        "pair_queries": [],
    },
    "osteomuscular": {
        "opening_focus": "Abrir por desvalorización, carga, esfuerzo sostenido y sensación de tener que sostener más de lo que puede.",
        "interview_targets": [
            "Preguntar qué carga, exigencia o desvalorización coincide con el dolor.",
            "Explorar si el consultante se siente sin apoyo, sobrecargado o forzado.",
        ],
        "protocol_focus": [
            "Abrir rastreo osteomuscular.",
            "Cruzar el cuadro con carga física, emocional y rol de sostén dentro del sistema.",
        ],
        "pair_queries": [],
    },
}


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


def _load_raw_disease_entries() -> list[RawDiseaseEntry]:
    payload = json.loads(RAW_DISEASE_ENTRIES_PATH.read_text(encoding="utf-8"))
    entries = []
    for item in payload.get("entries", []):
        entries.append(
            RawDiseaseEntry(
                canonical_name=item.get("canonical_name", ""),
                slug=item.get("slug", ""),
                summary=_safe_text(item.get("summary")),
                biodescodificacion=_safe_text(item.get("biodescodificacion")),
                source_title=_safe_text(item.get("source_title")),
            )
        )
    return entries


RAW_DISEASE_ENTRIES = _load_raw_disease_entries()
TEACHER = TeacherKnowledge.from_cache(TEACHER_KNOWLEDGE_CACHE_PATH)


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
        reference_causes=(
            "La pérdida de cabello puede orientarse hacia conflicto de separación e injusticia, con falta de reconocimiento del padre y sensación de separación de las raíces.",
        ),
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
        reference_causes=(
            "La pérdida de cabello puede orientarse hacia conflicto de separación e injusticia, con falta de reconocimiento del padre y sensación de separación de las raíces.",
        ),
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
        reference_causes=(
            "La indecisión suele relacionarse con no saber a dónde ir, no saber cuál es el sitio propio o qué posición adoptar.",
        ),
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
        reference_causes=(
            "La indecisión suele relacionarse con no saber a dónde ir, no saber cuál es el sitio propio o qué posición adoptar.",
        ),
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
    "gastritis": SymptomHeuristic(
        systems=("digestivo",),
        conflicts=("indigestión emocional", "irritación sostenida", "tener que tragarse una situación"),
        questions=(
            "¿Qué situación, persona o convivencia sientes que no has podido digerir?",
            "¿Con quién estás guardando irritación, enojo o ardor contenido?",
            "¿El ardor aparece cuando tragas algo que no quieres aceptar o tolerar?",
        ),
        reading_hint="Cuando el síntoma eje es gastritis conviene abrir por irritación sostenida, mala digestión emocional y tema materno o de convivencia.",
        family_axes=("abrir línea materna y nutrición afectiva a revisar",),
        course_routes=("analisis_sistemico", "rastreo_conflictologico_digestivo"),
        release_routes=("sistemico",),
    ),
    "vertigo": SymptomHeuristic(
        systems=("neurosensorial", "emocional_mental"),
        conflicts=("confusión ante decisiones importantes", "pérdida de dirección", "desorganización o falta de punto de apoyo"),
        questions=(
            "¿Qué decisión o cambio fuerte te hizo sentir sin piso o sin dirección?",
            "¿Qué estaba pasando cuando comenzó la sensación de perder equilibrio?",
            "¿Con quién o ante qué situación te sientes desorientado o rebasado?",
        ),
        reading_hint="El vértigo suele pedir revisar orientación, decisiones, sobrecarga y sensación de no encontrar un punto estable.",
        family_axes=("abrir línea paterna, dirección y seguridad a revisar",),
        course_routes=("analisis_sistemico", "rastreo_conflictologico_neurosensorial"),
        release_routes=("sistemico", "estres_postraumatico_si_aplica"),
    ),
    "mareo": SymptomHeuristic(
        systems=("neurosensorial", "emocional_mental"),
        conflicts=("desorganización interna", "sobrecarga nerviosa", "inseguridad o inestabilidad"),
        questions=(
            "¿Qué situación te rebasa o te deja sin centro?",
            "¿Qué ocurre justo antes de que aparezca el mareo?",
        ),
        reading_hint="El mareo obliga a revisar sobrecarga, inseguridad y pérdida de centro.",
        family_axes=("abrir dirección, amenaza y seguridad básica a revisar",),
        course_routes=("analisis_sistemico", "rastreo_conflictologico_neurosensorial"),
        release_routes=("sistemico",),
    ),
    "tinnitus": SymptomHeuristic(
        systems=("neurosensorial", "emocional_mental"),
        conflicts=("hipervigilancia", "ruido interno no resuelto", "sobrecarga o alerta sostenida"),
        questions=(
            "¿Qué no has podido dejar de escuchar internamente aunque afuera ya pasó?",
            "¿Qué situación mantiene al cuerpo en alerta o tensión sostenida?",
            "¿Qué cambió en tu vida cuando comenzaron los zumbidos?",
        ),
        reading_hint="El tinnitus conviene abrirlo por alerta sostenida, saturación auditiva y conflicto no resuelto que sigue sonando por dentro.",
        family_axes=("abrir seguridad, amenaza y dirección a revisar",),
        course_routes=("analisis_sistemico", "rastreo_conflictologico_neurosensorial"),
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


COURSE_SYSTEM_LABELS = {
    "neurosensorial": "sistema neurosensorial",
    "endocrino_metabolico": "sistema endócrino-metabólico",
    "inmunologico": "sistema inmunológico",
    "cardiovascular": "sistema cardiovascular",
    "respiratorio": "sistema respiratorio",
    "digestivo": "sistema digestivo",
    "renal_excretor": "sistema renal / electrolítico-excretor",
    "renal": "sistema renal / electrolítico-excretor",
    "reproductor": "sistema reproductor",
    "osteomuscular": "sistema osteomuscular",
    "lipo_fascial": "sistema lipo-fascial",
    "dermatologico": "sistema lipo-fascial / tegumentario",
    "emocional_mental": "campo psicoemocional",
}


SYSTEM_KEYWORD_HINTS: dict[str, tuple[str, ...]] = {
    "neurosensorial": ("migraña", "migraña", "dolor de cabeza", "mareo", "vértigo", "insomnio", "vista", "oido", "oído"),
    "endocrino_metabolico": ("diabetes", "tiroid", "metab", "glucosa", "pancrea", "peso", "fatiga hormonal"),
    "inmunologico": ("alerg", "defensas", "autoinm", "inmun"),
    "cardiovascular": ("corazon", "corazón", "palpit", "presion", "presión", "pecho", "circul"),
    "respiratorio": ("asma", "tos", "bronqu", "pulmon", "pulmón", "respira", "aire", "garganta"),
    "digestivo": ("gastr", "reflujo", "colitis", "estreñ", "estren", "diarrea", "estom", "abdomen", "intestin"),
    "renal_excretor": ("riñ", "rin", "vejiga", "orina", "urin", "renal", "excret"),
    "reproductor": ("matriz", "ovario", "útero", "utero", "próstata", "prostata", "vagina", "sexual", "reproduct"),
    "osteomuscular": ("dolor", "espalda", "rodilla", "hues", "musc", "fibromial", "columna", "articul"),
    "lipo_fascial": ("piel", "cabello", "alopecia", "grasa", "fascia", "tejido"),
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
                "possible_conflicts": [
                    compacted
                    for compacted in (_compact_conflict_text(value) for value in profile.possible_origins[:5])
                    if compacted
                ],
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


def _person_summary(person: dict[str, Any], fallback_label: str) -> str:
    if not isinstance(person, dict):
        return ""
    if not any(_safe_text(value) for value in person.values() if isinstance(value, str)):
        return ""
    name = _safe_text(person.get("full_name")) or fallback_label
    birth = _safe_text(person.get("birth_date"))
    death = _safe_text(person.get("death_date"))
    details = []
    if birth:
        details.append(f"nació {birth}")
    if death:
        details.append(f"falleció {death}")
    if details:
        return f"{name} ({'; '.join(details)})"
    return name


def _detect_family_axes(case_payload: dict[str, Any]) -> list[str]:
    axes: list[str] = []
    text_fields = [
        _safe_text(case_payload.get("family_conflicts_notes")),
        _safe_text(case_payload.get("family_secrets_notes")),
        _safe_text(case_payload.get("transgenerational_patterns_notes")),
        _safe_text(case_payload.get("important_relationships_notes")),
        _safe_text(case_payload.get("current_emotional_context")),
        _safe_text(case_payload.get("emotional_context_at_onset")),
    ]
    blob = _normalize_text(" ".join(text_fields))

    parents = case_payload.get("parents") if isinstance(case_payload.get("parents"), dict) else {}
    grandparents = case_payload.get("grandparents") if isinstance(case_payload.get("grandparents"), dict) else {}
    significant_partners = _safe_list(case_payload.get("significant_partners"))
    children = _safe_list(case_payload.get("children"))
    siblings = _safe_list(case_payload.get("siblings"))

    father = parents.get("father") if isinstance(parents.get("father"), dict) else {}
    mother = parents.get("mother") if isinstance(parents.get("mother"), dict) else {}
    paternal_people = [
        _person_summary(father, "padre"),
        _person_summary(grandparents.get("paternal_grandfather") or {}, "abuelo paterno"),
        _person_summary(grandparents.get("paternal_grandmother") or {}, "abuela paterna"),
    ]
    maternal_people = [
        _person_summary(mother, "madre"),
        _person_summary(grandparents.get("maternal_grandfather") or {}, "abuelo materno"),
        _person_summary(grandparents.get("maternal_grandmother") or {}, "abuela materna"),
    ]
    paternal_people = [item for item in paternal_people if item]
    maternal_people = [item for item in maternal_people if item]

    if paternal_people:
        axes.append(
            "abrir línea paterna con "
            + ", ".join(paternal_people[:3])
            + " para revisar protección, dirección, exigencia, reconocimiento o distancia afectiva."
        )
    if maternal_people:
        axes.append(
            "abrir línea materna con "
            + ", ".join(maternal_people[:3])
            + " para revisar cuidado, nutrición afectiva, recepción, hogar o sensación de no ser bien recibido."
        )

    death_lines = []
    for label, person in [
        ("padre", father),
        ("madre", mother),
        ("abuelo paterno", grandparents.get("paternal_grandfather") or {}),
        ("abuela paterna", grandparents.get("paternal_grandmother") or {}),
        ("abuelo materno", grandparents.get("maternal_grandfather") or {}),
        ("abuela materna", grandparents.get("maternal_grandmother") or {}),
    ]:
        if isinstance(person, dict) and _safe_text(person.get("death_date")):
            name = _safe_text(person.get("full_name")) or label
            death_lines.append(f"{name} falleció {person.get('death_date')}")
    if death_lines:
        axes.append("cruzar el síntoma con estos duelos del sistema: " + "; ".join(death_lines[:4]) + ".")

    current_partner = ((case_payload.get("current_partner") or {}) if isinstance(case_payload.get("current_partner"), dict) else {})
    partner_lines = []
    if _safe_text(current_partner.get("full_name")):
        years = _safe_text(current_partner.get("relationship_years"))
        detail = f"{current_partner.get('full_name')}" + (f" ({years} años de relación)" if years else "")
        partner_lines.append(detail)
    for partner in significant_partners[:4]:
        if isinstance(partner, dict) and _safe_text(partner.get("full_name")):
            detail = _safe_text(partner.get("full_name"))
            if _safe_text(partner.get("relationship_years")):
                detail += f" ({partner.get('relationship_years')} años)"
            partner_lines.append(detail)
    if partner_lines:
        axes.append("explorar patrón de pareja con " + ", ".join(partner_lines) + " para ver si el síntoma se reactiva en vínculo, rechazo o carga afectiva.")

    if children:
        child_names = []
        for child in children[:5]:
            if isinstance(child, dict):
                name = _safe_text(child.get("full_name"))
                if not name:
                    continue
                parent_name = _safe_text(child.get("other_parent_name"))
                if parent_name:
                    name += f" con {parent_name}"
                child_names.append(name)
        if child_names:
            axes.append("revisar rol de cuidado y línea filial con " + ", ".join(child_names) + ".")

    if siblings:
        sibling_names = []
        for sibling in siblings[:5]:
            if isinstance(sibling, dict) and _safe_text(sibling.get("full_name")):
                name = _safe_text(sibling.get("full_name"))
                if _safe_text(sibling.get("death_date")):
                    name += f" (falleció {sibling.get('death_date')})"
                sibling_names.append(name)
        if sibling_names:
            axes.append("revisar lugar entre hermanos y dinámica fraterna con " + ", ".join(sibling_names) + ".")

    if any(term in blob for term in ("secreto", "injusticia", "ancestro", "transgeneracional")):
        axes.append("hay indicios de carga transgeneracional o secretos familiares que conviene abrir de manera explícita en entrevista.")
    if any(term in blob for term in ("mama", "madre", "materna")) and not maternal_people:
        axes.append("aparece tema materno en el discurso y conviene profundizar cómo se vivió ese vínculo.")
    if any(term in blob for term in ("papa", "padre", "paterno")) and not paternal_people:
        axes.append("aparece tema paterno en el discurso y conviene profundizar cómo se vivió ese vínculo.")

    return _dedupe_keep_order(axes)


def _infer_course_systems(case_payload: dict[str, Any], heuristics: list[SymptomHeuristic]) -> list[str]:
    symptom_blob = " ".join(_normalize_text(text) for text in _collect_symptom_texts(case_payload))
    systems = [system for heuristic in heuristics for system in heuristic.systems]
    for system_name, keywords in SYSTEM_KEYWORD_HINTS.items():
        if any(keyword in symptom_blob for keyword in keywords):
            systems.append(system_name)
    return _dedupe_keep_order(systems)


def _format_system_label(system_name: str) -> str:
    return COURSE_SYSTEM_LABELS.get(system_name, system_name.replace("_", " "))


def _compact_reference_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    return value[:320].rstrip(" ,;:.") + ("…" if len(value) > 320 else "")


def _compact_bullets(values: list[str], limit: int = 6) -> list[str]:
    compacted = [_compact_conflict_text(value) for value in values if _safe_text(value)]
    return _dedupe_keep_order([value for value in compacted if value])[:limit]


def _build_reference_emotional_causes(
    case_payload: dict[str, Any],
    heuristics: list[SymptomHeuristic],
) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for heuristic in heuristics:
        for cause in heuristic.reference_causes:
            key = ("heuristic", _normalize_text(cause))
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    "source": "",
                    "label": "Causa emocional probable",
                    "body": cause,
                }
            )

    symptom_names = [
        _safe_text(item.get("symptom_name"))
        for item in _safe_list(case_payload.get("current_symptoms"))
        if _safe_text(item.get("symptom_name"))
    ] + [
        _safe_text(item.get("event_name"))
        for item in _safe_list(case_payload.get("history_events"))
        if _safe_text(item.get("event_name"))
    ]
    normalized_symptoms = [_normalize_text(name) for name in symptom_names]

    for entry in RAW_DISEASE_ENTRIES:
        entry_name = _normalize_text(entry.canonical_name)
        if not entry_name:
            continue
        if not any(entry_name in symptom or symptom in entry_name for symptom in normalized_symptoms if symptom):
            continue

        body_parts = []
        if entry.summary:
            body_parts.append(_compact_reference_text(entry.summary))
        if entry.biodescodificacion:
            body_parts.append(_compact_reference_text(entry.biodescodificacion))
        body = " ".join(body_parts).strip()
        if not body:
            continue

        key = (entry.canonical_name, body)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "source": "",
                "label": entry.canonical_name,
                "body": body,
            }
        )

    return results[:6]


def _extract_microbe_queries(case_payload: dict[str, Any]) -> list[str]:
    blob = " ".join(_collect_symptom_texts(case_payload))
    normalized = _normalize_text(blob)
    queries: list[str] = []
    keyword_map = {
        "helicobacter pylori": ("helicobacter pylori", "h pylori", "helicobacter"),
        "parasito digestivo": ("parasito", "parásito", "ascaris", "tenia", "ameba", "amiba"),
        "bacteria": ("bacteria", "bacteriana"),
        "hongo": ("hongo", "candida", "micosis"),
        "virus": ("virus", "viral"),
    }
    for query, aliases in keyword_map.items():
        if any(alias in normalized for alias in aliases):
            queries.append(query)
    return queries


def _build_suggested_pairs(case_payload: dict[str, Any]) -> list[dict[str, str]]:
    queries: list[str] = []
    for item in _safe_list(case_payload.get("current_symptoms")):
        if not isinstance(item, dict):
            continue
        queries.append(_safe_text(item.get("symptom_name")))
    for item in _safe_list(case_payload.get("history_events")):
        if isinstance(item, dict):
            queries.append(_safe_text(item.get("event_name")))

    microbe_queries = _extract_microbe_queries(case_payload)
    suggestions: list[dict[str, str]] = []
    seen: set[str] = set()
    for query in queries:
        if len(_normalize_text(query)) < 4:
            continue
        query_tokens = {
            token for token in re.findall(r"[a-z0-9]+", _normalize_text(query)) if len(token) >= 4
        }
        for entry in TEACHER.search_pairs(query, limit=8):
            pair_blob = _normalize_text(f"{entry.pair_name} {entry.related_condition} {entry.pair_type}")
            pair_tokens = {token for token in re.findall(r"[a-z0-9]+", pair_blob) if len(token) >= 4}
            overlap = query_tokens & pair_tokens
            if not overlap and query_tokens:
                continue
            if entry.normalized_pair_name in seen:
                continue
            seen.add(entry.normalized_pair_name)
            suggestions.append(
                {
                    "pair_name": entry.pair_name,
                    "pair_type": entry.pair_type,
                    "related_condition": _compact_conflict_text(entry.related_condition),
                    "why": f"Conviene validarlo en rastreo si el síntoma '{query}' sostiene este patrón.",
                }
            )
    for query in microbe_queries:
        for entry in TEACHER.search_pairs(query, limit=6):
            if entry.normalized_pair_name in seen:
                continue
            seen.add(entry.normalized_pair_name)
            suggestions.append(
                {
                    "pair_name": entry.pair_name,
                    "pair_type": entry.pair_type,
                    "related_condition": _compact_conflict_text(entry.related_condition),
                    "why": f"Como el cuadro menciona {query}, conviene validar este par dentro del rastreo microbiológico.",
                }
            )
    ranked = []
    priority_tokens = ("bacteria", "hongo", "virus", "parasito", "parásito", "disfuncional", "emocional")
    for item in suggestions:
        score = 0
        blob = _normalize_text(" ".join([item["pair_type"], item["related_condition"], item["pair_name"]]))
        for token in priority_tokens:
            if token in blob:
                score += 2
        if any(token in blob for token in ("oido", "mastoides", "temporal", "rinon", "riñon", "vertigo", "mareo", "tinnitus", "tinitus")):
            score += 1
        ranked.append((score, item))
    ranked.sort(key=lambda row: (row[0], row[1]["pair_name"]), reverse=True)
    return [item for _, item in ranked[:8]]


def _build_opening_guidance(
    probable_systems: list[str],
    priority_symptoms: list[str],
    case_payload: dict[str, Any],
) -> dict[str, Any]:
    primary_system = probable_systems[0] if probable_systems else ""
    symptom_focus = priority_symptoms[0] if priority_symptoms else "el síntoma principal"
    guidance = SYSTEM_OPENING_GUIDANCE.get(primary_system, {})
    opening_focus = guidance.get(
        "opening_focus",
        f"Abrir la entrevista tomando {symptom_focus} como síntoma eje y ubicar el conflicto que lo activó.",
    )
    interview_targets = guidance.get(
        "interview_targets",
        [
            f"Precisar desde cuándo comenzó {symptom_focus}.",
            "Ubicar qué cambió en la vida del consultante cuando el cuadro empezó.",
            "Definir qué emoción domina cuando el síntoma aparece o empeora.",
        ],
    )
    protocol_focus = guidance.get("protocol_focus", [])
    return {
        "primary_system": primary_system,
        "primary_system_label": _format_system_label(primary_system) if primary_system else "",
        "symptom_focus": symptom_focus,
        "opening_focus": opening_focus,
        "interview_targets": interview_targets[:4],
        "protocol_focus": protocol_focus[:4],
        "pair_queries": guidance.get("pair_queries", []),
    }


def _build_prioritized_hypotheses(
    priority_symptoms: list[str],
    probable_systems: list[str],
    probable_conflicts: list[str],
    family_axes: list[str],
    primary_family_axis: str,
    suggested_pairs: list[dict[str, str]],
    opening_guidance: dict[str, Any],
) -> list[dict[str, Any]]:
    hypotheses: list[dict[str, Any]] = []
    top_symptom = priority_symptoms[0] if priority_symptoms else "el síntoma principal"
    top_system = _format_system_label(probable_systems[0]) if probable_systems else "el sistema principal"
    top_conflict = probable_conflicts[0] if probable_conflicts else ""
    family_focus = primary_family_axis or (family_axes[0] if family_axes else "")
    pair_focus = [item["pair_name"] for item in suggested_pairs[:3]]

    if top_system:
        hypotheses.append(
            {
                "title": f"Predominio en {top_system}",
                "summary": f"El caso parece abrir primero por {top_system}; toma {top_symptom} como puerta principal y abre la entrevista desde ahí.",
                "verify": [
                    *opening_guidance.get("interview_targets", [])[:3],
                ],
                "pairs_to_validate": pair_focus,
            }
        )

    if top_conflict:
        hypotheses.append(
            {
                "title": "Hipótesis conflictual principal",
                "summary": f"La carga dominante parece organizarse alrededor de {top_conflict}.",
                "verify": [
                    "Explorar qué situación no resuelta sigue activa hoy.",
                    "Preguntar qué decisión, pérdida o presión coincide con el inicio del cuadro.",
                    "Medir qué emoción se activa cuando el paciente vuelve mentalmente al origen del síntoma.",
                ],
                "pairs_to_validate": pair_focus,
            }
        )

    if family_focus:
        hypotheses.append(
            {
                "title": "Hipótesis familiar o transgeneracional",
                "summary": f"Hay un eje relacional que merece abrirse en entrevista: {family_focus}",
                "verify": [
                    "Pedir la historia breve del vínculo que más pesa hoy.",
                    "Revisar si hubo pérdidas, duelos, lealtades o repeticiones alrededor del síntoma.",
                    "Observar si el síntoma empeora al tocar temas de padre, madre, pareja o muertes del sistema.",
                ],
                "pairs_to_validate": pair_focus,
            }
        )

    return hypotheses[:3]


def _select_primary_family_axis(probable_systems: list[str], family_axes: list[str]) -> str:
    if not family_axes:
        return ""
    priority_order: list[str] = []
    if probable_systems:
        first_system = probable_systems[0]
        if first_system == "digestivo":
            priority_order = ["materna", "madre", "duelos", "pareja", "paterna", "padre"]
        elif first_system in {"neurosensorial", "emocional_mental"}:
            priority_order = ["paterna", "padre", "duelos", "pareja", "materna", "madre"]
        elif first_system in {"respiratorio", "dermatologico"}:
            priority_order = ["duelos", "pareja", "materna", "madre", "paterna", "padre"]
    normalized_axes = [(_normalize_text(axis), axis) for axis in family_axes]
    for token in priority_order:
        for normalized, axis in normalized_axes:
            if token in normalized:
                return axis
    return family_axes[0]


def _build_course_guiding_questions(
    case_payload: dict[str, Any],
    probable_systems: list[str],
    family_axes: list[str],
    heuristic_questions: list[str],
) -> list[str]:
    questions: list[str] = []
    priority_symptoms = [
        _safe_text(item.get("symptom_name"))
        for item in _safe_list(case_payload.get("current_symptoms"))
        if _safe_text(item.get("symptom_name"))
    ]
    first_symptom = priority_symptoms[0] if priority_symptoms else "este síntoma"

    questions.extend(
        [
            f"¿Cuál fue el origen de {first_symptom} y qué estaba ocurriendo en la vida del consultante en ese momento?",
            "¿Qué detalles significativos rodearon el inicio: personas, lugar, pérdida, presión, cambio o impacto emocional?",
            "¿Cuál fue el conflicto crítico o el momento más intenso asociado al síntoma?",
            "¿Cómo cambió la vida del consultante después de ese conflicto o desde que apareció el síntoma?",
            "¿Cuál es la duración, frecuencia y relación de este síntoma con otros síntomas del cuadro?",
            "¿Qué emoción principal sostiene hoy este conflicto y en qué parte del cuerpo se siente con más fuerza?",
        ]
    )

    if any("paterna" in axis.lower() or "paterno" in axis.lower() or "padre" in axis.lower() for axis in family_axes):
        questions.append("¿Qué tema de protección, reconocimiento, autoridad o dirección se está moviendo con la línea paterna?")
    if any("materna" in axis.lower() or "madre" in axis.lower() for axis in family_axes):
        questions.append("¿Qué tema de cuidado, nutrición afectiva, hogar o recepción se está moviendo con la línea materna?")
    if any("pareja" in axis.lower() for axis in family_axes):
        questions.append("¿Qué patrón de pareja se repite y qué busca reparar el consultante a través de ese vínculo?")
    if any("transgeneracional" in axis.lower() or "duelos" in axis.lower() or "fallecio" in _normalize_text(axis) for axis in family_axes):
        questions.append("¿Hay carga transgeneracional, duelo o memoria familiar implicada en este síntoma, ciclo o drama?")
    for axis in family_axes:
        normalized_axis = _normalize_text(axis)
        if "fallecio" in normalized_axis:
            questions.append(f"¿Qué efecto dejó en el consultante este antecedente del sistema familiar: {axis}")
            break

    if probable_systems:
        first_system = _format_system_label(probable_systems[0])
        questions.append(f"Si abres análisis sistémico, ¿qué porcentaje de armonía muestra primero {first_system}?")

    questions.extend(heuristic_questions)
    return _dedupe_keep_order(questions)[:10]


def _build_course_reading(
    case_payload: dict[str, Any],
    probable_systems: list[str],
    probable_conflicts: list[str],
    family_axes: list[str],
    primary_family_axis: str,
    heuristic_hints: list[str],
    matched_names: list[str],
    prioritized_hypotheses: list[dict[str, Any]],
    opening_guidance: dict[str, Any],
) -> str:
    primary_system_label = opening_guidance.get("primary_system_label") or (
        _format_system_label(probable_systems[0]) if probable_systems else "el sistema prioritario"
    )
    symptom_focus = opening_guidance.get("symptom_focus") or (
        matched_names[0] if matched_names else "el síntoma principal"
    )
    parts = [
        f"La puerta de entrada del caso es {primary_system_label} y conviene tomar {symptom_focus} como síntoma eje.",
        opening_guidance.get("opening_focus", ""),
    ]
    if probable_conflicts:
        parts.append("La masa conflictual provisional apunta a " + ", ".join(probable_conflicts[:2]) + ".")
    if primary_family_axis:
        parts.append("En la entrevista conviene " + primary_family_axis.rstrip(".") + ".")
    if prioritized_hypotheses:
        top_hypothesis = prioritized_hypotheses[0]
        verify = top_hypothesis.get("verify") or []
        if verify:
            parts.append("Lo primero que conviene verificar es " + "; ".join(verify[:2]) + ".")
    parts.append("Antes del rastreo final, ubica primer episodio, detonante principal, emoción dominante y qué cambió en la vida del consultante después de ese momento.")
    return " ".join(part for part in parts if part)


def _build_protocol_suggestions(
    probable_systems: list[str],
    priority_symptoms: list[str],
    opening_guidance: dict[str, Any],
) -> list[dict[str, str]]:
    queries = []
    if priority_symptoms:
        queries.extend(priority_symptoms[:2])
    queries.extend(opening_guidance.get("pair_queries", []))
    suggestions: list[dict[str, str]] = []
    seen: set[str] = set()
    for query in queries:
        for entry in TEACHER.search_protocols(query, limit=3):
            if entry.normalized_title in seen:
                continue
            normalized_title = _normalize_text(entry.title)
            if any(
                blocked in normalized_title
                for blocked in (
                    "trabajar el sistema energetico",
                    "armonia biodinamica",
                    "chakras terciarios",
                )
            ):
                continue
            seen.add(entry.normalized_title)
            suggestions.append(
                {
                    "title": entry.title,
                    "reason": f"Puede servir como apoyo si al abrir por {query.lower()} el cuadro confirma ese patrón.",
                }
            )
    for bullet in opening_guidance.get("protocol_focus", []):
        if bullet not in seen:
            seen.add(bullet)
            suggestions.append({"title": bullet, "reason": "Conviene tenerlo presente desde la primera entrevista y el rastreo."})
    return suggestions[:6]


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

    probable_systems = _dedupe_keep_order(
        [item["system_name"] for item in top_matches] + _infer_course_systems(case_payload, heuristics)
    )[:6]
    probable_conflicts = _compact_bullets(_dedupe_keep_order(
        [conflict for heuristic in heuristics for conflict in heuristic.conflicts]
        + [conflict for item in top_matches for conflict in item.get("possible_conflicts", [])]
    ), limit=8)
    heuristic_questions = _dedupe_keep_order(
        [question for item in top_matches for question in item.get("guiding_questions", [])]
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
    primary_family_axis = _select_primary_family_axis(probable_systems, family_axes)

    matched_names = [item["canonical_name"] for item in top_matches]
    heuristic_hints = _dedupe_keep_order([heuristic.reading_hint for heuristic in heuristics])[:2]
    opening_guidance = _build_opening_guidance(
        probable_systems=probable_systems,
        priority_symptoms=priority_symptoms,
        case_payload=case_payload,
    )
    reference_emotional_causes = _build_reference_emotional_causes(
        case_payload=case_payload,
        heuristics=heuristics,
    )
    suggested_pairs_to_validate = _build_suggested_pairs(case_payload)
    prioritized_hypotheses = _build_prioritized_hypotheses(
        priority_symptoms=priority_symptoms,
        probable_systems=probable_systems,
        probable_conflicts=probable_conflicts,
        family_axes=family_axes,
        primary_family_axis=primary_family_axis,
        suggested_pairs=suggested_pairs_to_validate,
        opening_guidance=opening_guidance,
    )
    reading = _build_course_reading(
        case_payload=case_payload,
        probable_systems=probable_systems,
        probable_conflicts=probable_conflicts,
        family_axes=family_axes,
        primary_family_axis=primary_family_axis,
        heuristic_hints=heuristic_hints,
        matched_names=matched_names,
        prioritized_hypotheses=prioritized_hypotheses,
        opening_guidance=opening_guidance,
    )
    protocol_suggestions = _build_protocol_suggestions(
        probable_systems=probable_systems,
        priority_symptoms=priority_symptoms,
        opening_guidance=opening_guidance,
    )

    mass_conflict_hypothesis = ""
    if probable_conflicts:
        mass_conflict_hypothesis = (
            "Posible masa conflictual a explorar: " + "; ".join(probable_conflicts[:2]) + "."
        )
    elif probable_systems:
        mass_conflict_hypothesis = (
            "Todavía no se define una masa conflictual cerrada, pero conviene abrir rastreo por "
            + ", ".join(probable_systems[:3])
            + "."
        )

    guiding_questions = _build_course_guiding_questions(
        case_payload=case_payload,
        probable_systems=probable_systems,
        family_axes=family_axes,
        heuristic_questions=heuristic_questions,
    )

    return {
        "reading": reading,
        "priority_symptoms": priority_symptoms,
        "matched_profiles": top_matches,
        "probable_systems": probable_systems,
        "probable_system_labels": [_format_system_label(system) for system in probable_systems],
        "probable_conflicts": probable_conflicts,
        "opening_guidance": opening_guidance,
        "reference_emotional_causes": reference_emotional_causes,
        "family_axes": family_axes,
        "primary_family_axis": primary_family_axis,
        "mass_conflict_hypothesis": mass_conflict_hypothesis,
        "guiding_questions": guiding_questions,
        "suggested_pairs_to_validate": suggested_pairs_to_validate,
        "prioritized_hypotheses": prioritized_hypotheses,
        "suggested_protocols": protocol_suggestions,
        "suggested_course_routes": suggested_routes,
        "release_protocol_routes": release_routes,
    }


__all__ = ["analyze_case"]
