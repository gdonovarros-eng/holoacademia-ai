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


def _protocol_steps(value: str) -> list[str]:
    body = _safe_text(value)
    if not body:
        return []

    normalized = body.replace("●", "\n●").replace("•", "\n•")
    lines = [re.sub(r"\s+", " ", line).strip(" .") for line in normalized.splitlines()]
    steps = [line.lstrip("●•- ").strip() for line in lines if line.strip().startswith(("●", "•", "-"))]
    if steps:
        return _dedupe_keep_order(steps[:6])

    fragments = [fragment.strip() for fragment in re.split(r"\.\s+", body) if fragment.strip()]
    return _dedupe_keep_order(fragments[:6])


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


PROTOCOL_GUIDE_LIBRARY: dict[str, dict[str, Any]] = {
    "sistemico": {
        "candidates": ["Protocolo para eliminar conflictos sistémicos"],
        "purpose": "hacer consciente el conflicto sistémico principal y descargar la emoción que lo mantiene activo",
    },
    "sentimental": {
        "candidates": ["Protocolo para rastreo sentimental", "Protocolo para eliminar conexiones sentimentales"],
        "purpose": "abrir vínculo, sentimiento continuo, anclaje afectivo o carga relacional que siga disparando el síntoma",
    },
    "transgeneracional": {
        "candidates": [
            "Protocolo para liberar conflictos de tipo transgeneracional",
            "PROTOCOLO DE RASTREO TRANSGENERACIONAL",
            "PROTOCOLO DE SUBLIMACIÓN DE CONFLICTO TRANSGENERACIONAL",
        ],
        "purpose": "rastrear duelos, repeticiones, lealtades o cargas del árbol que puedan expresarse en el cuerpo",
    },
    "estres_postraumatico": {
        "candidates": ["Protocolo para la liberación del estrés postraumático"],
        "purpose": "liberar impacto, sobresalto o evento que dejó al sistema en alarma persistente",
    },
    "emociones_bloqueadas": {
        "candidates": [
            "PROTOCOLO PARA EMOCIONES BLOQUEADAS O NEGADAS",
            "PROTOCOLO PARA EMOCIÓN-REACCIÓN",
            "Protocolo para gestión de sensaciones",
        ],
        "purpose": "bajar carga emocional activa, sensaciones retenidas o respuestas emocionales que no terminan de descargarse",
    },
    "patogenos": {
        "candidates": ["Protocolo para patógenos “ocultos”"],
        "purpose": "validar si el cuadro requiere rastreo microbiológico complementario y qué par conviene impactar primero",
    },
}


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


SYSTEM_SWEEP_LIBRARY: dict[str, dict[str, Any]] = {
    "digestivo": {
        "title": "Barrido del sistema digestivo",
        "summary": "Se revisa como conflicto de bocado: qué entra, qué se traga, qué no se digiere, qué resulta tóxico, qué no se puede asimilar y qué no se logra eliminar.",
        "review_points": [
            "Aceptar o rechazar lo que viene del exterior.",
            "Tema materno, nutrición afectiva, hogar y sensación de ser bien recibido o no.",
            "Irritación, enojo contenido, ardor, gastritis, hiperacidez o mala digestión emocional.",
            "Tránsito, absorción, eliminación, gases, estreñimiento o diarrea como forma de resolver lo indeseado.",
        ],
        "microbial_focus": [
            "Si el cuadro es persistente, revisar componente bacteriano, parasitario, micótico o de flora intestinal.",
            "Cruzar si hay gastritis, hiperacidez, hernia hiatal, reflujo, diarrea, estreñimiento o mala absorción.",
        ],
    },
    "respiratorio": {
        "title": "Barrido del sistema respiratorio",
        "summary": "Se revisa como conflicto de peligro, invasión del espacio, miedo, duelo y necesidad de aire o libertad.",
        "review_points": [
            "Amenaza, susto, miedo o sensación de asfixia emocional.",
            "Duelo, tristeza, pérdida de espacio o invasión del territorio.",
            "Cómo entra el aire, qué no se puede inspirar o expulsar con tranquilidad.",
        ],
        "microbial_focus": [
            "Si hay tos, flemas, bronquitis, asma o sinusitis, revisar componente microbiano y reservorios respiratorios.",
        ],
    },
    "endocrino_metabolico": {
        "title": "Barrido del sistema endocrino-metabólico",
        "summary": "Se revisa como adaptación hormonal y metabólica a estrés, resistencia, impotencia, asco, supervivencia y ritmos biológicos alterados.",
        "review_points": [
            "Conflictos de resistencia, impotencia o no poder cambiar una situación.",
            "Tema de glucosa, amor tóxico, asco, metabolismo y energía disponible.",
            "Cambios de peso, tiroides, páncreas, suprarrenales, fatiga y ritmos internos.",
        ],
        "microbial_focus": [
            "Si hay páncreas comprometido o síntomas digestivos asociados, cruzar microbiota y pares pancreáticos.",
        ],
    },
    "cardiovascular": {
        "title": "Barrido del sistema cardiovascular",
        "summary": "Se revisa como territorio interno, familia sanguínea, hogar íntimo, competencia, presión vital y capacidad de sostener circulación y ritmo.",
        "review_points": [
            "Qué tan amenazado o presionado se siente el territorio interno del consultante.",
            "Competencia, exigencia, hogar, sangre, lazos familiares y sobrecarga.",
            "Corazón, vasos, circulación, hipertensión, hipotensión o arritmia como lenguaje adaptativo.",
        ],
        "microbial_focus": [
            "Si el cuadro se acompaña de inflamación o síntomas sistémicos, cruzar con reservorios vasculares y digestivos.",
        ],
    },
    "osteomuscular": {
        "title": "Barrido del sistema osteomuscular",
        "summary": "Se revisa como desvalorización, carga, estructura, soporte, rigidez, sobreesfuerzo y dificultad para moverse o sostenerse.",
        "review_points": [
            "Qué carga física o emocional está sosteniendo de más.",
            "Desvalorización, impotencia, rigidez o miedo a quebrarse.",
            "Dolor, columna, rodillas, articulaciones, músculos y postura vital.",
        ],
        "microbial_focus": [
            "Si hay dolor errático, inflamación o desgaste persistente, revisar componente microbiano y disfuncional.",
        ],
    },
    "lipo_fascial": {
        "title": "Barrido del sistema lipo-fascial",
        "summary": "Se revisa como contacto, separación, identidad, autoimagen, protección, envoltura y memoria en tejidos de recubrimiento.",
        "review_points": [
            "Separación, roce, vergüenza, invasión, protección y autoimagen.",
            "Piel, cabello, fascia, tejido subcutáneo y sensación de exposición.",
            "Cómo el cuerpo marca el límite entre adentro y afuera.",
        ],
        "microbial_focus": [
            "Si hay brotes, caída de cabello o lesiones persistentes, cruzar con hongos, parásitos o bacterias de piel.",
        ],
    },
    "dermatologico": {
        "title": "Barrido del sistema lipo-fascial",
        "summary": "Se revisa como contacto, separación, identidad, autoimagen, protección, envoltura y memoria en tejidos de recubrimiento.",
        "review_points": [
            "Separación, roce, vergüenza, invasión, protección y autoimagen.",
            "Piel, cabello, fascia, tejido subcutáneo y sensación de exposición.",
            "Cómo el cuerpo marca el límite entre adentro y afuera.",
        ],
        "microbial_focus": [
            "Si hay brotes, caída de cabello o lesiones persistentes, cruzar con hongos, parásitos o bacterias de piel.",
        ],
    },
    "reproductor": {
        "title": "Barrido del sistema reproductor",
        "summary": "Se revisa como reproducción, pareja, fertilidad, sexualidad, nido, maternaje, vínculo y continuidad de la especie.",
        "review_points": [
            "Conflictos de pareja, sexualidad, territorio íntimo, maternidad o paternidad.",
            "Pérdidas gestacionales, celos, fertilidad, deseo, rechazo y vínculo con el cuerpo sexual.",
            "Cómo se vive el nido, la pareja y la posibilidad de transmitir vida.",
        ],
        "microbial_focus": [
            "Si hay infecciones, dolor pélvico o síntomas sexuales persistentes, revisar componente microbiano local.",
        ],
    },
    "renal_excretor": {
        "title": "Barrido del sistema electrolítico-excretor",
        "summary": "Se revisa como filtración, límites, miedo, líquidos, territorialidad y capacidad de desechar o conservar.",
        "review_points": [
            "Miedo básico, seguridad, supervivencia y sensación de estar amenazado.",
            "Retención o pérdida de líquidos, riñón, vejiga y equilibrio interno.",
            "Qué no se logra soltar o qué se retiene por alarma interna.",
        ],
        "microbial_focus": [
            "Si hay infección urinaria, dolor renal o alteración persistente, revisar componente bacteriano, parasitario o disfuncional.",
        ],
    },
    "inmunologico": {
        "title": "Barrido del sistema inmunológico",
        "summary": "Se revisa como identidad, reconocimiento de lo propio y de lo extraño, defensa, alergia, reacción y memoria biológica.",
        "review_points": [
            "Quién soy y qué siento ajeno, invasivo o peligroso.",
            "Tema de identidad, pertenencia, autoagresión, alergia o defensa exagerada.",
            "Cómo reacciona el cuerpo ante lo extraño o ante lo que debería reconocer como propio.",
        ],
        "microbial_focus": [
            "Cruzar si la respuesta está disparada por infección, parásito, alergia o terreno inflamatorio.",
        ],
    },
    "neurosensorial": {
        "title": "Barrido del sistema neurosensorial",
        "summary": "Se revisa como procesamiento de realidad, orientación, control, disociación, sobrecarga sensorial, vigilancia y dirección.",
        "review_points": [
            "Confusión, pérdida de dirección, exceso de control o necesidad de mantenerse en alerta.",
            "Oído, visión, equilibrio, migraña, vértigo, mareo, tinnitus, sueño y percepción.",
            "Qué no puede dejar de escuchar, ver, pensar o controlar el consultante.",
        ],
        "microbial_focus": [
            "Si hay oído, mastoides, temporal, bulbo o síntomas vestibulares, cruzar con pares locales y componentes disfuncionales o infecciosos.",
        ],
    },
    "emocional_mental": {
        "title": "Barrido psicoemocional",
        "summary": "Se revisa el drama dominante, la emoción que sigue activa, la creencia que sostiene el síntoma y la forma de adaptación psíquica del consultante.",
        "review_points": [
            "Miedo, culpa, rechazo, abandono, pérdida, presión o hipercontrol.",
            "Momento de origen, repetición del drama y emoción dominante en el presente.",
            "Lo que el consultante expresa, lo que intenta decir y lo que no se atreve a decir.",
        ],
        "microbial_focus": [
            "Aquí el énfasis principal es conflictológico y de liberación; el rastreo microbiano se usa como apoyo cuando el cuadro corporal lo pide.",
        ],
    },
    "familiar": {
        "title": "Barrido del sistema familiar",
        "summary": "Se revisa como eco transgeneracional: historias repetidas, fechas, roles, secretos, duelos, oficios, pareja y lealtades invisibles.",
        "review_points": [
            "Repetición de historias, enfermedades, accidentes, separaciones, quiebras o muertes.",
            "Roles familiares, exclusiones, secretos, yacentes y fechas que se repiten.",
            "Qué del síntoma puede estar expresando una carga del sistema familiar.",
        ],
        "microbial_focus": [
            "Aquí primero se ordena el árbol y la repetición; lo microbiano se cruza después si el cuadro somático lo exige.",
        ],
    },
}

ORGAN_SWEEP_LIBRARY: list[dict[str, Any]] = [
    {
        "organ_key": "estomago",
        "system_name": "digestivo",
        "keywords": ("gastritis", "estomago", "estómago", "ardor", "acidez", "agrura", "boca del estomago", "boca del estómago"),
        "title": "Barrido de estómago",
        "summary": "Tomarlo como conflicto de bocado difícil de digerir, irritación sostenida, enojo tragado y rechazo de algo que ya entró al sistema.",
        "interview_points": [
            "Precisar qué situación le cayó pesada o indigesta cuando empezó el síntoma.",
            "Preguntar con quién se irrita pero se lo traga sin expresarlo.",
            "Revisar si el ardor aparece con presión, enojo, ambiente hostil o sensación de invasión.",
        ],
        "pair_focus": ["estómago", "píloro", "helicobacter pylori", "gastritis"],
    },
    {
        "organ_key": "esofago",
        "system_name": "digestivo",
        "keywords": ("reflujo", "esofag", "esófag", "hernia hiatal", "agruras"),
        "title": "Barrido de esófago / entrada digestiva",
        "summary": "Conviene revisarlo como dificultad para dejar bajar una situación, devolver lo que no se acepta o sostener irritación en la entrada del bocado.",
        "interview_points": [
            "Preguntar qué situación no logra pasar o aceptar del todo.",
            "Explorar rechazo, defensa, regreso de enojo o sensación de invasión.",
            "Revisar si el síntoma empeora con convivencia, presión o discusiones.",
        ],
        "pair_focus": ["esófago", "hernia hiatal", "reflujo"],
    },
    {
        "organ_key": "colon_intestino",
        "system_name": "digestivo",
        "keywords": ("colitis", "colon", "colón", "intestin", "diarrea", "estren", "estreñ"),
        "title": "Barrido de intestino / colon",
        "summary": "Abrirlo como conflicto de eliminación, irritación del territorio interno y dificultad para soltar lo que ya no sirve o se percibe tóxico.",
        "interview_points": [
            "Preguntar qué quiere sacar de su vida y todavía no logra soltar.",
            "Explorar irritación cotidiana, límite invadido o convivencia que intoxica.",
            "Revisar si el cuerpo acelera o retiene según miedo, control o enojo.",
        ],
        "pair_focus": ["colon", "intestino", "parasito digestivo", "flora intestinal"],
    },
    {
        "organ_key": "oido_vestibular",
        "system_name": "neurosensorial",
        "keywords": ("tinnitus", "tinittus", "tinitus", "zumbido", "oido", "oído", "vertigo", "vértigo", "mareo", "desequilibrio"),
        "title": "Barrido de oído / sistema vestibular",
        "summary": "Tomarlo como conflicto de vigilancia, alerta, desorientación o dificultad para sostener equilibrio y dirección ante una situación que desorganiza.",
        "interview_points": [
            "Precisar qué evento hizo perder seguridad, orientación o estabilidad.",
            "Preguntar qué no puede dejar de escuchar o qué amenaza sigue sonando internamente.",
            "Revisar si el mareo aparece con miedo, presión, conflicto de dirección o saturación nerviosa.",
        ],
        "pair_focus": ["oído", "mastoides", "temporal", "vértigo", "mareo", "tinnitus"],
    },
    {
        "organ_key": "sueno_ritmo",
        "system_name": "neurosensorial",
        "keywords": ("insomnio", "sueño", "sueno", "desvelo", "despertar", "no puedo dormir", "no duerme"),
        "title": "Barrido de sueño / ritmo nervioso",
        "summary": "Abrirlo como hipervigilancia, miedo a soltar el control, conflicto no cerrado o necesidad de permanecer alerta aun cuando el cuerpo pide descanso.",
        "interview_points": [
            "Preguntar qué teme que ocurra si baja la guardia o deja de controlar.",
            "Ubicar desde cuándo el cuerpo dejó de sentirse seguro para dormir.",
            "Revisar pensamientos repetitivos, miedo nocturno, sobresalto o preocupación persistente.",
        ],
        "pair_focus": ["insomnio", "pineal", "hipófisis", "bulbo", "sistema nervioso"],
    },
    {
        "organ_key": "cabeza_migrana",
        "system_name": "neurosensorial",
        "keywords": ("migraña", "migrana", "dolor de cabeza", "cefalea"),
        "title": "Barrido de cabeza / migraña",
        "summary": "Conviene abrirlo como sobrecarga, presión interna, exceso de control o conflicto de dirección que el consultante está sosteniendo mentalmente.",
        "interview_points": [
            "Preguntar qué presión, exigencia o control coincide con el dolor.",
            "Explorar saturación sensorial, decisiones pendientes o irritación acumulada.",
            "Revisar si el cuadro se dispara con autoridad, trabajo o sobreexigencia.",
        ],
        "pair_focus": ["migraña", "temporal", "cabeza", "vascular cerebral"],
    },
    {
        "organ_key": "piel_cabello",
        "system_name": "dermatologico",
        "keywords": ("piel", "eczema", "dermat", "urtic", "alopecia", "cabello", "caida de cabello", "caída de cabello"),
        "title": "Barrido de piel / cabello",
        "summary": "Abrirlo como separación, identidad, autoimagen, exposición o pérdida de fuerza en el contacto con uno mismo y con el exterior.",
        "interview_points": [
            "Preguntar qué separación, herida de identidad o falta de reconocimiento coincide con el cuadro.",
            "Explorar vergüenza, rechazo, exposición o sensación de no ser visto.",
            "Revisar si el cuerpo está marcando un límite que la persona no ha podido poner.",
        ],
        "pair_focus": ["piel", "cabello", "hongos", "parásitos de piel"],
    },
    {
        "organ_key": "bronquios_pulmon",
        "system_name": "respiratorio",
        "keywords": ("asma", "bronqu", "pulmon", "pulmón", "respirar", "falta de aire", "tos"),
        "title": "Barrido de bronquios / pulmón",
        "summary": "Tomarlo como conflicto de espacio vital, amenaza, miedo, tristeza o presencia del otro que impide respirar libremente.",
        "interview_points": [
            "Preguntar qué o quién no le deja respirar en paz.",
            "Explorar amenaza, duelo, llanto retenido o invasión del territorio.",
            "Revisar si el síntoma aparece con ciertas personas, lugares o recuerdos.",
        ],
        "pair_focus": ["asma", "bronquios", "pulmón", "sinusitis"],
    },
    {
        "organ_key": "rinon_vejiga",
        "system_name": "renal_excretor",
        "keywords": ("riñ", "rin", "vejiga", "orina", "urinaria", "renal"),
        "title": "Barrido de riñón / vejiga",
        "summary": "Conviene revisarlo como miedo básico, amenaza, retención, necesidad de proteger territorio y dificultad para soltar alerta o líquidos.",
        "interview_points": [
            "Preguntar qué amenaza o miedo se volvió constante.",
            "Explorar sensación de inseguridad, abandono o falta de soporte.",
            "Revisar si el cuerpo retiene o descarga por alarma interna.",
        ],
        "pair_focus": ["riñón", "vejiga", "infección urinaria"],
    },
    {
        "organ_key": "utero_ovario_prostata",
        "system_name": "reproductor",
        "keywords": ("ovario", "útero", "utero", "matriz", "próstata", "prostata", "vagina", "fertilidad", "sexual"),
        "title": "Barrido de sistema reproductor íntimo",
        "summary": "Abrirlo como conflicto de nido, pareja, sexualidad, reproducción, pérdida, fertilidad o invasión del territorio íntimo.",
        "interview_points": [
            "Preguntar qué ocurre en pareja, sexualidad, maternidad/paternidad o deseo.",
            "Explorar pérdidas gestacionales, duelos, celos, rechazo o culpa sexual.",
            "Revisar si el cuerpo está hablando de nido, vínculo o continuidad.",
        ],
        "pair_focus": ["útero", "ovario", "próstata", "vagina", "infección pélvica"],
    },
]


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
    return value


def _clean_reference_body(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if not text:
        return ""
    text = re.sub(r"^[\"'“”]+|[\"'“”]+$", "", text).strip()
    text = text.replace('" En el caso', ' En el caso').replace("” En el caso", " En el caso")
    text = re.sub(r"(?i)^en el caso de [^,.:;]+[,.:;]?\s*", "", text).strip()
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if len(parts) >= 2:
        first_normalized = _normalize_text(parts[0])
        second_normalized = _normalize_text(parts[1])
        if len(parts[0]) < 110 and ("en el caso" in second_normalized or "desde la biodescodificacion" in second_normalized):
            parts = parts[1:]
    deduped_parts: list[str] = []
    seen_parts: set[str] = set()
    for part in parts:
        normalized_part = _normalize_text(part)
        if not normalized_part or normalized_part in seen_parts:
            continue
        seen_parts.add(normalized_part)
        deduped_parts.append(part)
    return " ".join(deduped_parts).strip()


def _compact_bullets(values: list[str], limit: int = 6) -> list[str]:
    compacted = [_compact_conflict_text(value) for value in values if _safe_text(value)]
    return _dedupe_keep_order([value for value in compacted if value])[:limit]


def _build_reference_emotional_causes(
    case_payload: dict[str, Any],
    heuristics: list[SymptomHeuristic],
) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    grouped_entries: dict[str, dict[str, Any]] = {}

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
            cleaned = _clean_reference_body(_compact_reference_text(entry.summary))
            if cleaned:
                body_parts.append(cleaned)
        if entry.biodescodificacion:
            cleaned = _clean_reference_body(_compact_reference_text(entry.biodescodificacion))
            if cleaned:
                body_parts.append(cleaned)
        body_parts = _dedupe_keep_order(body_parts)
        body = " ".join(body_parts).strip()
        if not body:
            continue

        label_key = _normalize_text(entry.canonical_name)
        bucket = grouped_entries.setdefault(
            label_key,
            {
                "source": "",
                "label": entry.canonical_name,
                "body_parts": [],
            },
        )
        for part in body_parts:
            key = (entry.canonical_name, _normalize_text(part))
            if key in seen:
                continue
            seen.add(key)
            bucket["body_parts"].append(part)

    for item in grouped_entries.values():
        body = " ".join(_dedupe_keep_order(item["body_parts"])).strip()
        if not body:
            continue
        results.append(
            {
                "source": item["source"],
                "label": item["label"],
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


def _find_protocol_candidate(group_key: str) -> dict[str, Any] | None:
    group = PROTOCOL_GUIDE_LIBRARY.get(group_key) or {}
    for candidate in group.get("candidates", []):
        entry = TEACHER.find_protocol(candidate)
        if entry:
            return {
                "title": entry.title,
                "body": _safe_text(entry.body),
                "purpose": group.get("purpose", ""),
            }
    return None


def _build_protocol_card(
    title: str,
    purpose: str,
    when_to_use: str,
    body: str,
    pair_focus: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "purpose": purpose,
        "when_to_use": when_to_use,
        "steps": _protocol_steps(body)[:5],
        "pair_focus": (pair_focus or [])[:5],
    }


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
    organ_sweep_summary: list[dict[str, Any]],
) -> str:
    primary_system_label = opening_guidance.get("primary_system_label") or (
        _format_system_label(probable_systems[0]) if probable_systems else "el sistema prioritario"
    )
    symptom_focus = opening_guidance.get("symptom_focus") or (
        matched_names[0] if matched_names else "el síntoma principal"
    )
    organ_title = organ_sweep_summary[0]["title"].lower() if organ_sweep_summary else ""
    parts = [
        f"La puerta de entrada del caso es {primary_system_label} y conviene tomar {symptom_focus} como síntoma eje.",
    ]
    if organ_title:
        parts.append(f"Lo primero es abrir entrevista y rastreo desde {organ_title}.")
    elif opening_guidance.get("opening_focus", ""):
        parts.append(opening_guidance.get("opening_focus", ""))
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


def _build_therapeutic_guide(
    probable_systems: list[str],
    priority_symptoms: list[str],
    family_axes: list[str],
    probable_conflicts: list[str],
    organ_sweep_summary: list[dict[str, Any]],
    opening_guidance: dict[str, Any],
    suggested_pairs: list[dict[str, Any]],
    microbe_queries: list[str],
) -> list[dict[str, Any]]:
    guide: list[dict[str, Any]] = []
    symptom_focus = priority_symptoms[0] if priority_symptoms else "el síntoma principal"
    pair_focus = [item.get("pair_name", "") for item in suggested_pairs[:4] if item.get("pair_name")]
    primary_system = probable_systems[0] if probable_systems else ""

    guide.append(
        {
            "title": "Apertura clínica del caso",
            "purpose": "ordenar la entrevista para que el síntoma deje de ser solo un dato y empiece a mostrar conflicto, sistema y puerta de rastreo",
            "when_to_use": f"Úsalo al inicio, tomando {symptom_focus} como puerta principal.",
            "steps": [
                f"Precisar cuándo comenzó {symptom_focus} y qué estaba ocurriendo en la vida del consultante.",
                "Ubicar el primer episodio claro, el detonante principal y la emoción dominante.",
                *(opening_guidance.get("interview_targets", [])[:2]),
            ],
            "pair_focus": pair_focus[:3],
        }
    )

    if organ_sweep_summary:
        top_organ = organ_sweep_summary[0]
        guide.append(
            {
                "title": top_organ["title"],
                "purpose": "abrir la entrevista por la puerta anatómica más congruente con el síntoma eje",
                "when_to_use": f"Conviene usarlo cuando {symptom_focus} domina el cuadro o marca claramente el sistema.",
                "steps": top_organ.get("interview_points", [])[:4],
                "pair_focus": top_organ.get("pair_focus", [])[:5],
            }
        )

    systemic_protocol = _find_protocol_candidate("sistemico")
    if systemic_protocol:
        guide.append(
            _build_protocol_card(
                title=systemic_protocol["title"],
                purpose=systemic_protocol["purpose"],
                when_to_use="Úsalo cuando ya identificaste el conflicto dominante y quieres volverlo consciente para empezar a descargarlo.",
                body=systemic_protocol["body"],
                pair_focus=pair_focus[:3],
            )
        )

    family_blob = " ".join(family_axes).lower()
    if any(token in family_blob for token in ("pareja", "vínculo", "sentimental")):
        sentimental_protocol = _find_protocol_candidate("sentimental")
        if sentimental_protocol:
            guide.append(
                _build_protocol_card(
                    title=sentimental_protocol["title"],
                    purpose=sentimental_protocol["purpose"],
                    when_to_use="Ábrelo cuando el síntoma se reactive con pareja, rechazo, dependencia afectiva o carga vincular.",
                    body=sentimental_protocol["body"],
                    pair_focus=pair_focus[:2],
                )
            )

    if any(token in family_blob for token in ("transgeneracional", "duelo", "falleció", "árbol", "sistema familiar")):
        trans_protocol = _find_protocol_candidate("transgeneracional")
        if trans_protocol:
            guide.append(
                _build_protocol_card(
                    title=trans_protocol["title"],
                    purpose=trans_protocol["purpose"],
                    when_to_use="Ábrelo cuando haya fechas de muerte, repeticiones, duelos o sensación de carga del árbol.",
                    body=trans_protocol["body"],
                    pair_focus=[],
                )
            )

    conflict_blob = " ".join(probable_conflicts).lower()
    if any(token in conflict_blob for token in ("trauma", "shock", "sobresalto", "terror", "miedo intenso")):
        trauma_protocol = _find_protocol_candidate("estres_postraumatico")
        if trauma_protocol:
            guide.append(
                _build_protocol_card(
                    title=trauma_protocol["title"],
                    purpose=trauma_protocol["purpose"],
                    when_to_use="Conviene abrirlo cuando el cuadro cambió después de un evento abrupto o quedó una alarma persistente.",
                    body=trauma_protocol["body"],
                    pair_focus=pair_focus[:2],
                )
            )

    if microbe_queries or (
        primary_system in {"digestivo", "respiratorio", "renal_excretor", "reproductor", "dermatologico"}
        and any(
            any(token in _normalize_text(" ".join([item.get("pair_type", ""), item.get("related_condition", ""), item.get("pair_name", "")])) for token in ("bacteria", "virus", "hongo", "parasito", "parásito"))
            for item in suggested_pairs[:6]
        )
    ):
        pathogen_protocol = _find_protocol_candidate("patogenos")
        if pathogen_protocol:
            guide.append(
                _build_protocol_card(
                    title=pathogen_protocol["title"],
                    purpose=pathogen_protocol["purpose"],
                    when_to_use="Úsalo si el cuadro apunta a componente microbiológico o si el rastreo sugiere bacteria, hongo, virus o parásito.",
                    body=pathogen_protocol["body"],
                    pair_focus=pair_focus[:4],
                )
            )

    emotional_protocol = _find_protocol_candidate("emociones_bloqueadas")
    if emotional_protocol:
        guide.append(
            _build_protocol_card(
                title=emotional_protocol["title"],
                purpose=emotional_protocol["purpose"],
                when_to_use="Sirve cuando el consultante entiende la historia, pero el cuerpo sigue cargado, negado o demasiado contenido.",
                body=emotional_protocol["body"],
                pair_focus=[],
            )
        )

    deduped: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for item in guide:
        key = _normalize_text(item.get("title", ""))
        if not key or key in seen_titles:
            continue
        seen_titles.add(key)
        deduped.append(item)
    return deduped[:6]


def _build_system_sweep_summary(probable_systems: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for system_name in probable_systems[:3]:
        sweep = SYSTEM_SWEEP_LIBRARY.get(system_name)
        if not sweep or system_name in seen:
            continue
        seen.add(system_name)
        results.append(
            {
                "system_name": system_name,
                "system_label": _format_system_label(system_name),
                "title": sweep["title"],
                "summary": sweep["summary"],
                "review_points": sweep.get("review_points", [])[:5],
                "microbial_focus": sweep.get("microbial_focus", [])[:4],
            }
        )
    return results


def _build_organ_sweep_summary(case_payload: dict[str, Any], probable_systems: list[str]) -> list[dict[str, Any]]:
    normalized_symptoms = " ".join(_normalize_text(text) for text in _collect_symptom_texts(case_payload))
    results: list[tuple[int, dict[str, Any]]] = []
    seen: set[str] = set()
    for organ in ORGAN_SWEEP_LIBRARY:
        organ_key = organ["organ_key"]
        if organ_key in seen:
            continue
        system_name = organ["system_name"]
        score = 0
        keyword_hit = False
        if system_name in probable_systems[:3]:
            score += 2
        for keyword in organ.get("keywords", ()):
            if _normalize_text(keyword) in normalized_symptoms:
                score += 3
                keyword_hit = True
        if not keyword_hit:
            continue
        if score <= 0:
            continue
        seen.add(organ_key)
        results.append(
            (
                score,
                {
                    "organ_key": organ_key,
                    "system_name": system_name,
                    "system_label": _format_system_label(system_name),
                    "title": organ["title"],
                    "summary": organ["summary"],
                    "interview_points": organ.get("interview_points", [])[:4],
                    "pair_focus": organ.get("pair_focus", [])[:5],
                },
            )
        )
    if not results and probable_systems:
        primary_system = probable_systems[0]
        for organ in ORGAN_SWEEP_LIBRARY:
            if organ["system_name"] != primary_system:
                continue
            results.append(
                (
                    1,
                    {
                        "organ_key": organ["organ_key"],
                        "system_name": organ["system_name"],
                        "system_label": _format_system_label(organ["system_name"]),
                        "title": organ["title"],
                        "summary": organ["summary"],
                        "interview_points": organ.get("interview_points", [])[:4],
                        "pair_focus": organ.get("pair_focus", [])[:5],
                    },
                )
            )
            break
    results.sort(key=lambda item: (-item[0], item[1]["title"]))
    return [item for _, item in results[:3]]


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
    microbe_queries = _extract_microbe_queries(case_payload)
    prioritized_hypotheses = _build_prioritized_hypotheses(
        priority_symptoms=priority_symptoms,
        probable_systems=probable_systems,
        probable_conflicts=probable_conflicts,
        family_axes=family_axes,
        primary_family_axis=primary_family_axis,
        suggested_pairs=suggested_pairs_to_validate,
        opening_guidance=opening_guidance,
    )
    system_sweep_summary = _build_system_sweep_summary(probable_systems)
    organ_sweep_summary = _build_organ_sweep_summary(case_payload, probable_systems)
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
        organ_sweep_summary=organ_sweep_summary,
    )
    protocol_suggestions = _build_protocol_suggestions(
        probable_systems=probable_systems,
        priority_symptoms=priority_symptoms,
        opening_guidance=opening_guidance,
    )
    therapeutic_guide = _build_therapeutic_guide(
        probable_systems=probable_systems,
        priority_symptoms=priority_symptoms,
        family_axes=family_axes,
        probable_conflicts=probable_conflicts,
        organ_sweep_summary=organ_sweep_summary,
        opening_guidance=opening_guidance,
        suggested_pairs=suggested_pairs_to_validate,
        microbe_queries=microbe_queries,
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
        "therapeutic_guide": therapeutic_guide,
        "system_sweep_summary": system_sweep_summary,
        "organ_sweep_summary": organ_sweep_summary,
        "suggested_course_routes": suggested_routes,
        "release_protocol_routes": release_routes,
    }


__all__ = ["analyze_case"]
