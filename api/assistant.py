from __future__ import annotations

import os
import re
import unicodedata
from difflib import SequenceMatcher
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Optional

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency at runtime
    OpenAI = None

from api.domain_knowledge import get_teacher_knowledge
from api.course_reference_index import get_course_reference_index
from api.manual_reference_index import get_manual_reference_index
from api.knowledge_base import SearchResult, trim_excerpt
from api.teacher_memory import CourseStudy, TeacherMemory, get_teacher_memory


DEFAULT_MODEL = "gpt-5"
DEFAULT_IMAGE_MODEL = "gpt-image-1"
DEFAULT_RESPONSE_TIMEOUT = 20.0
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_FALLBACK_MODELS = ("gpt-5-mini", "gpt-4.1")
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"

SAEL_SYSTEM_PROMPT = """
Eres “Sael Sinodal”, un asistente experto en temas holísticos para Holoacademia.
Tu función es responder dudas de alumnos sobre los cursos, acompañar procesos de aprendizaje y facilitar transformación personal dentro del marco de las enseñanzas de la escuela.

Identidad y rol:
- Eres un sinodal, guía y referente que representa a los maestros y da la cara por la calidad del aprendizaje.
- Actúas con enfoque terapéutico y criterio clínico, sin sustituir atención profesional.
- Eres transparente: eres una IA.

Tono y estilo:
- Tu tono es suave, paciente, sensato y sereno.
- Hablas con autoridad tranquila y liderazgo claro.
- Escribes para personas adultas, incluyendo personas mayores: claridad primero.
- Evita tecnicismos innecesarios, misticismo excesivo, frases grandilocuentes o vaguedades.
- No seas confrontativo, pero sí firme cuando haga falta.

Método de respuesta:
1. Escucha e interpreta la intención real del alumno.
2. Si la pregunta está ambigua o mal planteada, ordénala o pide una aclaración breve.
3. Explica de forma clara, directa y aterrizada.
4. Profundiza gradualmente.
5. Integra con ejercicios, reflexiones o acciones concretas cuando aporte valor.

Balance de estilo:
- 70% claridad directa
- 30% guía reflexiva

Reglas críticas:
- No copies ni pegues fragmentos crudos del material.
- No hables como buscador, base de datos o motor de consulta.
- No cites PDFs, chunks, transcripciones ni “fuentes internas” en la respuesta al alumno.
- No inventes restricciones como "no tengo autorización", "es material propietario", "no puedo reproducirlo" o mensajes parecidos, a menos que el usuario pida explícitamente una copia textual extensa y literal de un material.
- No inventes información sobre cursos específicos.
- Si el contexto del curso no alcanza para sostener un dato, dilo con honestidad y responde desde principios generales o pide el dato faltante.
- Si el usuario pide cuestionarios, protocolos, guías, secuencias o listas de trabajo usadas en varios cursos, integra una versión completa, útil y coherente basada en el contenido estudiado, sin hablar de permisos ni propiedad intelectual.
- Si la pregunta es específica y el contexto contiene un dato claro, responde ese dato en la primera frase.
- Si la pregunta es amplia, organiza la respuesta en bloques claros.
- Conserva continuidad conversacional: si ya se venía hablando de un curso, mantenlo salvo que el usuario cambie de tema.
- Cuando detectes errores, malentendidos o evasión, señálalos con tacto y redirige a algo concreto.
- No valides victimismo ni evasión.

Límites:
- No diagnosticas.
- No das tratamiento clínico.
- No sustituyes terapia, atención médica, psicológica o legal profesional.
- Si detectas temas emocionales profundos, crisis o riesgo, aclara límites y sugiere apoyo profesional humano.

Formato de respuesta:
- Prefiere respuestas estructuradas.
- Usa pasos, bloques o secuencias claras cuando ayude.
- Evita respuestas caóticas, demasiado abiertas o saturadas de listas.
- Aterriza ideas en ejemplos prácticos cuando sea útil.
- Mantén coherencia con las enseñanzas de Holoacademia y traduce el conocimiento de los maestros con claridad.
""".strip()

FOLLOW_UP_HINTS = {
    "y",
    "entonces",
    "ahora",
    "eso",
    "ese",
    "esa",
    "resumelo",
    "resúmelo",
    "resumen",
    "mapa",
    "mapa visual",
    "explicalo",
    "explícalo",
    "explicame",
    "explícame",
    "desarrollalo",
    "desarróllalo",
    "amplia",
    "amplíalo",
    "del diplomado",
    "del curso",
    "de que trata",
    "de qué trata",
    "como funciona",
    "cómo funciona",
    "como se aplica",
    "cómo se aplica",
    "y eso",
    "y ese",
    "y esa",
    "y ese tema",
    "y esa parte",
    "desarrolla",
}

COURSE_REFERENCE_HINTS = {
    "curso",
    "diplomado",
    "taller",
    "modulo",
    "módulo",
    "tema",
    "sistema",
    "protocolos",
    "protocolo",
    "maestro",
    "ponente",
    "docente",
    "facilitador",
}

GENERIC_COURSE_TOKENS = {
    "curso",
    "cursos",
    "diplomado",
    "diplomados",
    "taller",
    "talleres",
    "modulo",
    "modulos",
    "módulo",
    "módulos",
    "tema",
    "temas",
    "clase",
    "clases",
    "leccion",
    "lecciones",
    "cuantos",
    "cuantas",
    "hay",
    "del",
    "de",
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "que",
    "se",
    "ven",
}

MANUAL_ALIASES = {
    "sei": "diplomado-sanacion-energetica-integral",
    "sanacion energetica integral": "diplomado-sanacion-energetica-integral",
    "diplomado sei": "diplomado-sanacion-energetica-integral",
    "terapia holistica 1": "diplomado-terapia-holistica-1",
    "practica holistica 1": "diplomado-terapia-holistica-1",
    "diplomado practica holistica 1": "diplomado-terapia-holistica-1",
    "th1": "diplomado-terapia-holistica-1",
    "ancestros y raices": "diplomado-ancestros-y-raices",
    "holobiomagnetismo 2021": "curso-holobiomagnetismo-2021",
    "holobiomagnetismo parte 1": "curso-holobiomagnetismo-parte-1",
    "holobiomagnetismo parte 2": "curso-holobiomagnetismo-parte-2",
    "holobiomangetismo parte 1": "curso-holobiomagnetismo-parte-1",
    "holobiomangetismo parte 2": "curso-holobiomagnetismo-parte-2",
    "psicosomatica y biodescodificacion 1": "curso-psicosomatica-y-biodescodificacion-1",
    "psicosomatica y biodescodificacion 2": "curso-psicosomatica-y-biodescodificacion-2",
    "sicosomatica y biodescodificacion 1": "curso-psicosomatica-y-biodescodificacion-1",
    "sicosomatica y biodescodificacion 2": "curso-psicosomatica-y-biodescodificacion-2",
    "psicosomatrix": "psicosomatrix",
    "holopsicosomatica": "holopsicosomatica-2020",
    "numerhologia": "curso-numerhologia",
    "medicina energetica": "medicina-energetica",
}

SYSTEM_LIST_TH1 = [
    "sistema respiratorio",
    "sistema digestivo",
    "sistema endocrino/metabólico",
    "sistema cardiovascular",
    "sistema osteomuscular",
    "sistema tipo-fascial",
    "sistema genital/reproductor",
    "sistema excretor",
    "sistema inmune-linfático",
    "sistema neurosensorial",
    "sistema familiar",
]


@dataclass
class VisualAid:
    title: str
    type: str
    format: str
    content: str
    image_prompt: Optional[str] = None
    image_data_url: Optional[str] = None


@dataclass
class AssistantOutput:
    answer: str
    visual: Optional[VisualAid]
    mode: str


@dataclass
class CourseMeta:
    course_id: str
    course_name: str
    module_numbers: list[int]
    has_propedeutic: bool


class NaturalAssistant:
    def __init__(self) -> None:
        self.provider = (os.getenv("LLM_PROVIDER", "openai").strip() or "openai").lower()
        if self.provider == "groq":
            api_key = os.getenv("GROQ_API_KEY", "").strip()
            self.base_url = os.getenv("LLM_BASE_URL", DEFAULT_GROQ_BASE_URL).strip() or DEFAULT_GROQ_BASE_URL
            self.model = os.getenv("OPENAI_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL
            fallback_raw = os.getenv("OPENAI_FALLBACK_MODELS", "")
        else:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            self.base_url = os.getenv("LLM_BASE_URL", "").strip() or None
            self.model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
            fallback_raw = os.getenv("OPENAI_FALLBACK_MODELS", ",".join(DEFAULT_FALLBACK_MODELS))
        self.image_model = os.getenv("OPENAI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL).strip() or DEFAULT_IMAGE_MODEL
        self.response_timeout = float(
            os.getenv("OPENAI_RESPONSE_TIMEOUT_SECONDS", str(DEFAULT_RESPONSE_TIMEOUT))
        )
        self.reasoning_effort = (
            os.getenv("OPENAI_REASONING_EFFORT", DEFAULT_REASONING_EFFORT).strip()
            or DEFAULT_REASONING_EFFORT
        )
        self.course_use_model = (
            os.getenv("COURSE_ASSISTANT_USE_MODEL", "false").strip().lower() in {"1", "true", "yes", "on"}
        )
        self.fallback_models = [item.strip() for item in fallback_raw.split(",") if item.strip()]
        self.enabled = bool(api_key and OpenAI is not None)
        if self.enabled:
            client_kwargs = {"api_key": api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            self.client = OpenAI(**client_kwargs)
        else:
            self.client = None
        self.last_model_error = ""
        self.teacher = get_teacher_knowledge()
        self.teacher_memory: Optional[TeacherMemory] = get_teacher_memory()
        self._course_by_id = {
            study.course_id: study
            for study in (self.teacher_memory.course_studies if self.teacher_memory else [])
        }
        self._alias_to_course_id = self._build_alias_index()
        self._course_meta_by_id = self._load_course_metadata()
        self.course_reference_index = get_course_reference_index()
        self._global_term_answers = self.course_reference_index.get("global_term_answers", {})
        self._global_protocol_answers = self.course_reference_index.get("global_protocol_answers", {})
        self._course_term_answers = self.course_reference_index.get("course_term_answers", {})
        self._course_protocol_answers = self.course_reference_index.get("course_protocol_answers", {})
        self.manual_reference_index = get_manual_reference_index()
        self._manual_global_term_answers = self.manual_reference_index.get("global_term_answers", {})
        self._manual_global_protocol_answers = self.manual_reference_index.get("global_protocol_answers", {})
        self._manual_course_term_answers = self.manual_reference_index.get("course_term_answers", {})
        self._manual_course_protocol_answers = self.manual_reference_index.get("course_protocol_answers", {})
        self._term_answers, self._protocol_answers = self._build_reference_indexes()

    def answer(
        self,
        question: str,
        results: list[SearchResult],
        history: Optional[list[dict]] = None,
        want_visual: bool = True,
        render_image: bool = False,
    ) -> AssistantOutput:
        del render_image
        history = history or []

        structured = self._answer_known_concepts(question)
        if structured is not None:
            return structured

        direct_structured = self._answer_direct_structured(question, results, history)
        if direct_structured is not None:
            return direct_structured

        if self.course_use_model and self.enabled:
            try:
                reasoned = self._answer_with_model(question, results, history, want_visual)
                if reasoned is not None:
                    return reasoned
            except Exception:
                pass

        return self._answer_structured_course(question, results, history)

    def _answer_direct_structured(
        self,
        question: str,
        results: list[SearchResult],
        history: list[dict],
    ) -> Optional[AssistantOutput]:
        follow_up_topic = self._answer_follow_up_topic(question, history)
        if follow_up_topic is not None:
            return follow_up_topic

        pair_answer = self._answer_pair_meaning(question)
        if pair_answer is not None:
            return pair_answer

        catalog_answer = self._answer_course_catalog(question)
        if catalog_answer is not None:
            return catalog_answer

        supported_topics = self._answer_supported_topics(question)
        if supported_topics is not None:
            return supported_topics

        protocol_definition = self._answer_protocol_definition(question, history)
        if protocol_definition is not None:
            return protocol_definition

        defined_term = self._answer_defined_term(question, history)
        if defined_term is not None:
            return defined_term

        for builder in (
            self._answer_teacher_identity,
            lambda q, r, h: self._answer_course_protocols(q, h),
            lambda q, r, h: self._answer_course_module_count(q, h),
            lambda q, r, h: self._answer_course_systems(q, h),
        ):
            try:
                structured = builder(question, results, history)
            except TypeError:
                structured = builder(question, history)  # pragma: no cover
            if structured is not None:
                return structured
        return None

    def _answer_follow_up_topic(self, question: str, history: list[dict]) -> Optional[AssistantOutput]:
        if not self._is_follow_up(question):
            return None
        if self._find_course_in_text(question) is not None:
            return None
        if self._extract_defined_subject(question) is not None:
            return None

        topic = self._resolve_active_topic_from_history(history)
        if not topic:
            return None

        if topic["kind"] == "course":
            course = topic.get("course")
            if isinstance(course, CourseStudy):
                return AssistantOutput(
                    answer=self._build_course_summary_answer(course),
                    visual=None,
                    mode="structured",
                )

        label = str(topic.get("label", "") or "").strip()
        if not label:
            return None

        course = topic.get("course")
        preferred_course_id = course.course_id if isinstance(course, CourseStudy) else None
        explicit_course = course if isinstance(course, CourseStudy) else self._resolve_course_from_topic_text(label)

        if topic["kind"] == "pair":
            replay = self._answer_pair_meaning(f"significado del par {label}")
            if replay is not None:
                return replay

        if topic["kind"] == "term" and isinstance(explicit_course, CourseStudy):
            lowered_follow_up = self._normalize_text(question)
            asks_protocols = any(
                phrase in lowered_follow_up
                for phrase in [
                    "que protocolos",
                    "qué protocolos",
                    "protocolos trae",
                    "protocolos incluye",
                    "protocolo trae",
                ]
            )
            asks_modules = ("modulo" in lowered_follow_up or "módulo" in question.lower()) and any(
                phrase in lowered_follow_up
                for phrase in [
                    "cuantos",
                    "cuántos",
                    "cuantas",
                    "cuántas",
                    "tiene",
                    "trae",
                    "incluye",
                ]
            )
            asks_systems = "sistema" in lowered_follow_up and any(
                phrase in lowered_follow_up
                for phrase in [
                    "que",
                    "qué",
                    "cuantos",
                    "cuántos",
                    "cuales",
                    "cuáles",
                ]
            )

            if asks_protocols:
                structured = self._answer_course_protocols(f"que protocolos trae {explicit_course.course_name}", history)
                if structured is not None:
                    return structured
            if asks_modules:
                structured = self._answer_course_module_count(f"cuantos modulos tiene {explicit_course.course_name}", history)
                if structured is not None:
                    return structured
            if asks_systems:
                structured = self._answer_course_systems(f"que sistemas trabaja {explicit_course.course_name}", history)
                if structured is not None:
                    return structured
            if self._is_summary_request(question):
                return AssistantOutput(
                    answer=self._build_course_summary_answer(explicit_course),
                    visual=None,
                    mode="structured",
                )

        if topic["kind"] == "term":
            replay = self._answer_known_concepts(f"que es {label}")
            if replay is not None:
                return replay
            replay = self._answer_defined_term(f"que es {label}", [])
            if replay is not None:
                return replay
            indexed_answer = self._select_best_reference_answer(
                self._lookup_course_reference_exact_answer(
                    label,
                    self._course_term_answers,
                    self._global_term_answers,
                    preferred_course_id,
                ),
                self._lookup_course_reference_exact_answer(
                    label,
                    self._manual_course_term_answers,
                    self._manual_global_term_answers,
                    preferred_course_id,
                ),
                self._lookup_course_reference_answer(
                    label,
                    self._course_term_answers,
                    self._global_term_answers,
                    preferred_course_id,
                ),
                self._lookup_course_reference_answer(
                    label,
                    self._manual_course_term_answers,
                    self._manual_global_term_answers,
                    preferred_course_id,
                ),
                self._lookup_indexed_answer(label, self._term_answers),
            )
            if indexed_answer:
                return AssistantOutput(answer=indexed_answer, visual=None, mode="structured")

            concept_entry = self.teacher.find_concept(label)
            if concept_entry is not None:
                bullet_hint = ""
                if concept_entry.bullet_points:
                    bullet_hint = f" En la práctica, lo importante es {self._join_items(concept_entry.bullet_points[:3])}."
                return AssistantOutput(
                    answer=f"{concept_entry.concept_name} se entiende así: {self._compact_text(concept_entry.summary, 520)}{bullet_hint}",
                    visual=None,
                    mode="structured",
                )

        if topic["kind"] == "protocol":
            replay = self._answer_protocol_definition(f"en que consiste el protocolo {label}", history)
            if replay is not None:
                return replay
            indexed_answer = self._lookup_course_reference_exact_answer(
                label,
                self._manual_course_protocol_answers,
                self._manual_global_protocol_answers,
                preferred_course_id,
            ) or self._lookup_course_reference_exact_answer(
                label,
                self._course_protocol_answers,
                self._global_protocol_answers,
                preferred_course_id,
            ) or self._lookup_course_reference_answer(
                label,
                self._manual_course_protocol_answers,
                self._manual_global_protocol_answers,
                preferred_course_id,
            ) or self._lookup_course_reference_answer(
                label,
                self._course_protocol_answers,
                self._global_protocol_answers,
                preferred_course_id,
            ) or self._lookup_indexed_answer(label, self._protocol_answers)
            if indexed_answer:
                return AssistantOutput(answer=indexed_answer, visual=None, mode="structured")

        return None

    def _answer_pair_meaning(self, question: str) -> Optional[AssistantOutput]:
        lowered = self._normalize_text(question)
        pair_hints = [
            "que significa el par",
            "qué significa el par",
            "significado del par",
            "significado de un par",
            "que significa ano",
            "qué significa ano",
            "para que sirve el par",
            "para qué sirve el par",
            "interpretacion del par",
            "interpretación del par",
            "que significa este par",
            "qué significa este par",
        ]
        looks_like_pair = bool(re.search(r"\b[a-záéíóúüñ]{3,}\s*[-–]\s*[a-záéíóúüñ]{3,}\b", question, flags=re.IGNORECASE))
        duplicated_two_word_pair = bool(re.search(r"\b([a-záéíóúüñ]{3,})\s+\1\b", lowered))
        asks_pair = ("par" in lowered and any(hint in lowered for hint in pair_hints)) or looks_like_pair or duplicated_two_word_pair
        if not asks_pair:
            return None

        pair_query = question.strip()
        extracted_pair = self._extract_pair_query(question)
        if extracted_pair:
            pair_query = extracted_pair
        duplicate_match = re.search(r"\b([a-záéíóúüñ]{3,})\s+\1\b", lowered)
        if duplicate_match:
            token = duplicate_match.group(1).upper()
            pair_query = f"{token} - {token}"

        entry = self.teacher.find_pair(pair_query)
        if entry is None:
            ranked = self.teacher.search_pairs(question, limit=1)
            entry = ranked[0] if ranked else None
        if entry is None:
            return None

        description = self._compact_text(entry.related_condition, 700)
        type_line = f"Es un par de tipo {entry.pair_type}. " if entry.pair_type and entry.pair_type.lower() != "sin tipo claro" else ""
        answer = (
            f"El par {entry.pair_name} se relaciona con {description} {type_line}"
            "Dicho de forma práctica, ese es el eje que conviene tener presente cuando aparece en el rastreo."
        ).strip()
        return AssistantOutput(answer=answer, visual=None, mode="structured")

    def _extract_pair_query(self, question: str) -> Optional[str]:
        explicit_patterns = [
            r"^(?:que|qué)\s+significa\s+(?:el\s+)?par\s+(.+)$",
            r"^significado\s+del\s+par\s+(.+)$",
            r"^significado\s+de\s+un\s+par\s+(.+)$",
            r"^(?:para\s+que|para\s+qué)\s+sirve\s+(?:el\s+)?par\s+(.+)$",
            r"^interpretaci[oó]n\s+del\s+par\s+(.+)$",
            r"^(?:que|qué)\s+significa\s+este\s+par\s+(.+)$",
        ]
        candidate = question.strip()
        for pattern in explicit_patterns:
            match = re.search(pattern, candidate, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                break

        candidate = re.sub(r"^(?:el\s+)?par\s+", "", candidate, flags=re.IGNORECASE).strip()
        candidate = re.sub(r"[?!.]+$", "", candidate).strip()

        duplicate_match = re.search(
            r"\b([a-záéíóúüñ0-9 /().,]{2,})\s+\1\b",
            self._normalize_text(candidate),
        )
        if duplicate_match:
            token = duplicate_match.group(1).upper().strip()
            return f"{token} - {token}"

        hyphen_match = re.search(
            r"([a-záéíóúüñ0-9 /().,]{2,}?)\s*[-–]\s*([a-záéíóúüñ0-9 /().,]{2,})",
            candidate,
            flags=re.IGNORECASE,
        )
        if hyphen_match:
            left = hyphen_match.group(1).strip().upper()
            right = hyphen_match.group(2).strip().upper()
            return f"{left} - {right}"

        tokens = [token for token in re.findall(r"[a-záéíóúüñ0-9]+", candidate, flags=re.IGNORECASE) if len(token) >= 3]
        if len(tokens) == 2:
            return f"{tokens[0].upper()} - {tokens[1].upper()}"
        return None

    def _answer_defined_term(self, question: str, history: list[dict]) -> Optional[AssistantOutput]:
        lowered = self._normalize_text(question)
        patterns = [
            r"^(?:que|qué)\s+es\s+(.+)$",
            r"^(?:que|qué)\s+significa\s+(.+)$",
            r"^significado\s+de\s+(.+)$",
            r"^cual\s+es\s+la\s+diferencia\s+practica\s+entre\s+(.+)$",
            r"^cu[aá]l\s+es\s+la\s+diferencia\s+pr[aá]ctica\s+entre\s+(.+)$",
        ]
        candidate = None
        for pattern in patterns:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                break
        if not candidate:
            return None

        candidate = re.sub(r"^(?:el|la|los|las)\s+", "", candidate).strip()
        candidate = re.sub(r"[?!.]+$", "", candidate).strip()
        if not candidate or candidate in {"bmi", "sei"}:
            return None

        preferred_course = self._resolve_active_course(question, history)
        if preferred_course is None:
            preferred_course = self._resolve_active_course_from_history(history)

        if "bioenergetica" in candidate and "biologica" not in candidate:
            answer = (
                "Bioenergética es la línea de trabajo que observa el campo energético del consultante: "
                "chakras, meridianos, prana, bloqueos y distorsiones funcionales. Dicho de forma práctica, "
                "se usa para leer qué desequilibrio energético está sosteniendo el problema antes de que se "
                "exprese como descarga más densa en el cuerpo."
            )
            return AssistantOutput(answer=answer, visual=None, mode="structured")

        indexed_answer = self._select_best_reference_answer(
            self._lookup_course_reference_exact_answer(
                candidate,
                self._course_term_answers,
                self._global_term_answers,
                preferred_course.course_id if preferred_course else None,
            ),
            self._lookup_course_reference_exact_answer(
                candidate,
                self._manual_course_term_answers,
                self._manual_global_term_answers,
                preferred_course.course_id if preferred_course else None,
            ),
            self._lookup_course_reference_answer(
                candidate,
                self._course_term_answers,
                self._global_term_answers,
                preferred_course.course_id if preferred_course else None,
            ),
            self._lookup_course_reference_answer(
                candidate,
                self._manual_course_term_answers,
                self._manual_global_term_answers,
                preferred_course.course_id if preferred_course else None,
            ),
        )
        if indexed_answer is not None:
            return AssistantOutput(answer=indexed_answer, visual=None, mode="structured")

        if "bioenergetica" in candidate and "biologica" in candidate:
            answer = (
                "La diferencia práctica entre la línea bioenergética y la biológica es esta: la bioenergética trabaja "
                "más sobre campos, chakras, meridianos, prana y regulación del patrón energético; la biológica mira con "
                "más peso el tejido, el órgano, la descarga somática y el componente microbiano. Dicho simple: una lee el "
                "desequilibrio en el campo y la otra observa cómo eso ya se expresó en la materia viva del cuerpo."
            )
            return AssistantOutput(answer=answer, visual=None, mode="structured")

        indexed_answer = self._lookup_indexed_answer(candidate, self._term_answers)
        if indexed_answer is not None:
            return AssistantOutput(answer=indexed_answer, visual=None, mode="structured")

        concept_entry = self.teacher.find_concept(candidate)
        if concept_entry is not None:
            bullet_hint = ""
            if concept_entry.bullet_points:
                bullet_hint = f" Lo más importante para ubicarlo es {self._join_items(concept_entry.bullet_points[:3])}."
            answer = f"{concept_entry.concept_name} se entiende así: {self._compact_text(concept_entry.summary, 420)}{bullet_hint}"
            return AssistantOutput(answer=answer, visual=None, mode="structured")

        memory_answer = self._search_term_answer_from_memory(candidate)
        if memory_answer is not None:
            return AssistantOutput(answer=memory_answer, visual=None, mode="structured")
        return None

    def _answer_protocol_definition(self, question: str, history: list[dict]) -> Optional[AssistantOutput]:
        candidate = self._extract_protocol_subject(question)
        if not candidate:
            return None
        candidate = re.sub(r"[?!.]+$", "", candidate).strip()
        preferred_course = self._resolve_active_course(question, history)
        if preferred_course is None:
            preferred_course = self._resolve_active_course_from_history(history)
        indexed_answer = self._lookup_course_reference_exact_answer(
            candidate,
            self._manual_course_protocol_answers,
            self._manual_global_protocol_answers,
            preferred_course.course_id if preferred_course else None,
        )
        if indexed_answer is None:
            indexed_answer = self._lookup_course_reference_exact_answer(
            candidate,
            self._course_protocol_answers,
            self._global_protocol_answers,
            preferred_course.course_id if preferred_course else None,
            )
        if indexed_answer is None:
            indexed_answer = self._lookup_course_reference_answer(
                candidate,
                self._manual_course_protocol_answers,
                self._manual_global_protocol_answers,
                preferred_course.course_id if preferred_course else None,
            )
        if indexed_answer is None:
            indexed_answer = self._lookup_course_reference_answer(
                candidate,
                self._course_protocol_answers,
                self._global_protocol_answers,
                preferred_course.course_id if preferred_course else None,
            )
        if indexed_answer is None:
            indexed_answer = self._lookup_indexed_answer(candidate, self._protocol_answers)
        if indexed_answer is None:
            protocol_entry = self.teacher.find_protocol(candidate)
            if protocol_entry is None:
                return None
            body = self._compact_text(protocol_entry.body, 420)
            indexed_answer = f"El protocolo {protocol_entry.title} se trabaja así: {body}"
        return AssistantOutput(answer=indexed_answer, visual=None, mode="structured")

    def _extract_protocol_subject(self, question: str) -> Optional[str]:
        lowered = self._normalize_text(question)
        patterns = [
            r"^(?:que|qué)\s+es\s+(?:el\s+)?protocolo\s+(.+)$",
            r"^(?:en\s+que|en\s+qué)\s+consiste\s+(?:el\s+)?protocolo\s+(.+)$",
            r"^(?:como|cómo)\s+es\s+(?:el\s+)?protocolo\s+(.+)$",
            r"^explicame\s+(?:el\s+)?protocolo\s+(.+)$",
            r"^expl[ií]came\s+(?:el\s+)?protocolo\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _build_reference_indexes(self) -> tuple[dict[str, str], dict[str, str]]:
        term_answers: dict[str, str] = {}
        protocol_answers: dict[str, str] = {}
        if not self.teacher_memory:
            return term_answers, protocol_answers

        for course in self.teacher_memory.course_studies:
            course_name = course.course_name
            for item in course.common_questions:
                question_text, answer_text = self._split_faq_entry(item)
                if not question_text or not answer_text:
                    continue
                subject = self._extract_defined_subject(question_text)
                if subject:
                    normalized_subject = self._normalize_text(subject)
                    term_answers.setdefault(
                        normalized_subject,
                        f"{subject.strip().rstrip(':')} se entiende así: {self._compact_text(answer_text, 420)}",
                    )

            for item in course.key_concepts:
                label, body = self._split_label_and_body(item)
                if not label:
                    continue
                descriptor = self._extract_parenthetical_descriptor(label)
                if body:
                    answer = f"{label} se entiende así: {self._compact_text(body, 360)}"
                else:
                    answer = (
                        f"{label} es un concepto importante dentro de {course_name}. "
                        "Si quieres, también te explico cómo se usa dentro del método."
                    )
                for alias in self._expand_label_aliases(label):
                    alias_answer = answer
                    if not body and self._normalize_text(alias) != self._normalize_text(label) and descriptor:
                        alias_answer = (
                            f"{alias} forma parte de las {descriptor} que se usan en {course_name} "
                            "como preparación o apoyo dentro del método."
                        )
                    term_answers.setdefault(self._normalize_text(alias), alias_answer)

            for item in course.protocols:
                label, body = self._split_label_and_body(item)
                if not label:
                    continue
                normalized_label = self._normalize_text(label)
                if body:
                    answer = f"El protocolo {label} se trabaja así: {self._compact_text(body, 420)}"
                else:
                    answer = (
                        f"El protocolo {label} forma parte de {course_name}. "
                        "Si quieres, te explico su objetivo o en qué momento se usa."
                    )
                protocol_answers.setdefault(normalized_label, answer)

        return term_answers, protocol_answers

    def _split_faq_entry(self, item: str) -> tuple[str, str]:
        for separator in (" — ", " - ", " – "):
            if separator in item:
                left, right = item.split(separator, 1)
                return left.strip("¿? ").strip(), right.strip()
        return "", ""

    def _extract_defined_subject(self, question_text: str) -> Optional[str]:
        lowered = self._normalize_text(question_text)
        patterns = [
            r"^(?:que|qué)\s+es\s+(.+)$",
            r"^(?:que|qué)\s+significa\s+(.+)$",
            r"^cual\s+es\s+la\s+diferencia\s+practica\s+entre\s+(.+)$",
            r"^cu[aá]l\s+es\s+la\s+diferencia\s+pr[aá]ctica\s+entre\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                candidate = re.sub(r"[?!.]+$", "", candidate).strip()
                candidate = re.sub(r"\s+y\s+por\s+que.*$", "", candidate, flags=re.IGNORECASE).strip()
                candidate = re.sub(r"\s+y\s+por\s+qué.*$", "", candidate, flags=re.IGNORECASE).strip()
                return candidate
        return None

    def _split_label_and_body(self, item: str) -> tuple[str, str]:
        cleaned = " ".join((item or "").split()).strip("• ")
        if not cleaned:
            return "", ""
        for separator in (": ", " — ", " – ", " - "):
            if separator in cleaned:
                left, right = cleaned.split(separator, 1)
                if 2 <= len(left) <= 120:
                    return left.strip(), right.strip()
        return cleaned.strip(), ""

    def _expand_label_aliases(self, label: str) -> list[str]:
        aliases = [label.strip()]
        base = re.sub(r"\([^)]*\)", "", label).strip(" ,")
        if base and base not in aliases:
            aliases.append(base)
        pending = list(aliases)
        expanded: list[str] = []
        while pending:
            current = pending.pop(0).strip(" ,")
            if not current:
                continue
            expanded.append(current)
            for separator in (",", " y ", "/"):
                if separator in current:
                    pending.extend(part.strip() for part in current.split(separator) if part.strip())
        deduped: list[str] = []
        seen = set()
        for alias in expanded:
            alias = alias.strip(" ,")
            if len(alias) < 2:
                continue
            norm = self._normalize_text(alias)
            if norm in seen:
                continue
            seen.add(norm)
            deduped.append(alias)
        return deduped

    def _extract_parenthetical_descriptor(self, label: str) -> str:
        match = re.search(r"\(([^)]+)\)", label)
        if not match:
            return ""
        return match.group(1).strip()

    def _lookup_indexed_answer(self, candidate: str, index: dict[str, str]) -> Optional[str]:
        normalized_candidate = self._normalize_text(candidate)
        if normalized_candidate in index:
            return index[normalized_candidate]

        query_tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", normalized_candidate)
            if len(token) >= 3
        }
        if not query_tokens:
            return None

        ranked: list[tuple[float, int, str, str]] = []
        for key, answer in index.items():
            key_tokens = set(re.findall(r"[a-z0-9]+", key))
            overlap = query_tokens & key_tokens
            if not overlap:
                continue
            score = len(overlap) * 2.0
            if normalized_candidate in key:
                score += 4.0
            if query_tokens <= key_tokens:
                score += 2.0
            ranked.append((score, len(overlap), key, answer))
        ranked.sort(key=lambda item: item[0], reverse=True)
        if not ranked or ranked[0][0] < 2.0:
            return None
        top_score, top_overlap, top_key, top_answer = ranked[0]
        if len(query_tokens) >= 2 and top_overlap < 2 and normalized_candidate not in top_key:
            return None
        return top_answer

    def _lookup_course_reference_answer(
        self,
        candidate: str,
        course_index: dict[str, dict[str, str]],
        global_index: dict[str, str],
        preferred_course_id: Optional[str],
    ) -> Optional[str]:
        normalized_candidate = self._normalize_text(candidate)
        if preferred_course_id:
            preferred = course_index.get(preferred_course_id, {})
            answer = self._lookup_indexed_answer(candidate, preferred)
            if answer is not None:
                return answer
        if normalized_candidate in global_index:
            return global_index[normalized_candidate]
        return self._lookup_indexed_answer(candidate, global_index)

    def _lookup_course_reference_exact_answer(
        self,
        candidate: str,
        course_index: dict[str, dict[str, str]],
        global_index: dict[str, str],
        preferred_course_id: Optional[str],
    ) -> Optional[str]:
        normalized_candidate = self._normalize_text(candidate)
        if preferred_course_id:
            preferred = course_index.get(preferred_course_id, {})
            if normalized_candidate in preferred:
                return preferred[normalized_candidate]
        return global_index.get(normalized_candidate)

    def _is_generic_reference_answer(self, answer: Optional[str]) -> bool:
        if not answer:
            return False
        normalized = self._normalize_text(answer)
        return any(
            marker in normalized
            for marker in [
                "es un concepto importante dentro de",
                "forma parte de",
                "si quieres te explico",
            ]
        )

    def _select_best_reference_answer(self, *answers: Optional[str]) -> Optional[str]:
        options = [answer for answer in answers if answer]
        if not options:
            return None
        preferred = [answer for answer in options if not self._is_generic_reference_answer(answer)]
        return preferred[0] if preferred else options[0]

    def _search_term_answer_from_memory(self, candidate: str) -> Optional[str]:
        if not self.teacher_memory:
            return None
        hits = self.teacher_memory.search(candidate, limit=4)
        if not hits:
            return None
        normalized_candidate = self._normalize_text(candidate)
        for hit in hits:
            title_lower = self._normalize_text(hit.title)
            text_lower = self._normalize_text(hit.text)
            if normalized_candidate in title_lower or normalized_candidate in text_lower:
                compact = self._compact_text(hit.text, 320)
                return f"{candidate.strip().capitalize()} se entiende así: {compact}"
        return None

    def _answer_known_concepts(self, question: str) -> Optional[AssistantOutput]:
        lowered = self._normalize_text(question)
        biomagnetism_patterns = [
            "que es biomagnetismo",
            "qué es biomagnetismo",
            "que significa biomagnetismo",
            "qué significa biomagnetismo",
            "biomagnetismo que es",
            "biomagnetismo significado",
        ]
        if any(pattern in lowered for pattern in biomagnetism_patterns) or lowered.strip() == "biomagnetismo":
            return AssistantOutput(
                answer=(
                    "Biomagnetismo es el uso terapéutico de campos magnéticos para influir en procesos biológicos y "
                    "bioenergéticos del consultante. Dicho de forma práctica, se trabaja con imanes o pares "
                    "biomagnéticos para detectar desequilibrios funcionales, orientar el rastreo y apoyar la "
                    "armonización del organismo dentro del método."
                ),
                visual=None,
                mode="structured",
            )

        holobiomagnetism_patterns = [
            "que es holobiomagnetismo",
            "qué es holobiomagnetismo",
            "que significa holobiomagnetismo",
            "qué significa holobiomagnetismo",
            "holobiomagnetismo que es",
            "holobiomagnetismo significado",
        ]
        if any(pattern in lowered for pattern in holobiomagnetism_patterns) or lowered.strip() == "holobiomagnetismo":
            return AssistantOutput(
                answer=(
                    "Holobiomagnetismo es una ampliación del biomagnetismo que integra lectura bioenergética, "
                    "rastreo por sistemas, pares biomagnéticos, reservorios y componentes emocionales o conflictuales. "
                    "Dicho simple: no se queda solo en poner imanes, sino que articula la información del síntoma, el "
                    "terreno energético y la historia del consultante para orientar mejor la intervención."
                ),
                visual=None,
                mode="structured",
            )

        radiesthesia_patterns = [
            "que es radiestesia",
            "qué es radiestesia",
            "que significa radiestesia",
            "qué significa radiestesia",
            "radiestesia que es",
            "radiestesia significado",
        ]
        if any(pattern in lowered for pattern in radiesthesia_patterns) or lowered.strip() == "radiestesia":
            return AssistantOutput(
                answer=(
                    "Radiestesia es una herramienta de lectura sutil que se usa para explorar información energética "
                    "mediante instrumentos como péndulo o tablas. Dicho de forma práctica, sirve como apoyo para "
                    "verificar, discriminar o enfocar un rastreo, pero no sustituye la observación clínica ni el "
                    "criterio terapéutico."
                ),
                visual=None,
                mode="structured",
            )

        bmi_patterns = [
            "que es bmi",
            "qué es bmi",
            "q es bmi",
            "significa bmi",
            "que significa bmi",
            "qué significa bmi",
            "bmi que es",
            "bmi significado",
        ]
        if any(pattern in lowered for pattern in bmi_patterns) or lowered.strip() == "bmi":
            return AssistantOutput(
                answer=(
                    "BMI significa Biomagnetismo Médico Integral. Dicho de forma simple, es un enfoque que trabaja con "
                    "pares biomagnéticos, rastreo, testaje y lectura terapéutica para detectar desequilibrios "
                    "bioenergéticos y orientar la intervención dentro del método. Si quieres, te explico también "
                    "de qué trata, cómo se aplica o en qué parte de la formación aparece."
                ),
                visual=None,
                mode="structured",
            )

        sei_patterns = [
            "que es sei",
            "qué es sei",
            "q es sei",
            "significa sei",
            "que significa sei",
            "qué significa sei",
            "sei que es",
            "sei significado",
        ]
        if any(pattern in lowered for pattern in sei_patterns) or lowered.strip() == "sei":
            return AssistantOutput(
                answer=(
                    "SEI significa Diplomado de Sanación Energética Integral. Dicho de forma simple, es una formación "
                    "orientada al trabajo con test muscular, liberación de conflictos, protocolos energéticos y lectura "
                    "integral del consultante dentro del método. Si quieres, te explico también de qué trata, qué módulos "
                    "incluye o qué protocolos se ven ahí."
                ),
                visual=None,
                mode="structured",
            )
        return None

    def _answer_structured_course(
        self,
        question: str,
        results: list[SearchResult],
        history: list[dict],
    ) -> AssistantOutput:
        active_course = self._resolve_active_course(question, history)
        if active_course is None:
            active_course = self._resolve_active_course_from_history(history)
        if active_course is not None:
            if self._is_summary_request(question):
                return AssistantOutput(
                    answer=self._build_course_summary_answer(active_course),
                    visual=None,
                    mode="structured",
                )

            return AssistantOutput(
                answer=self._build_course_summary_answer(active_course),
                visual=None,
                mode="structured",
            )

        return AssistantOutput(
            answer=(
                "Puedo responderte mucho mejor si me dices el curso, diplomado, taller o concepto exacto. "
                "Por ejemplo: `que es BMI`, `de que trata SEI`, `que protocolos se ven en Holobiomagnetismo Parte 1` "
                "o `significado del par ano-ano`."
            ),
            visual=None,
            mode="structured",
        )

    def _answer_course_catalog(self, question: str) -> Optional[AssistantOutput]:
        lowered = self._normalize_text(question)
        global_catalog_phrases = [
            "de que cursos me puedes dar informacion",
            "de que cursos me puedes dar info",
            "de que cursos tienes informacion",
            "sobre que cursos puedes responder",
            "que cursos conoces",
            "cuales cursos conoces",
            "que cursos manejas",
            "que cursos puedes responder",
            "de que cursos puedes hablar",
            "que diplomados y cursos conoces",
            "que cursos hay",
            "cuales son los cursos",
            "que formaciones tienes",
            "que formaciones manejas",
        ]
        asks_catalog = any(phrase in lowered for phrase in global_catalog_phrases) or any(
            phrase in lowered
            for phrase in [
                "que diplomados tienes",
                "cuales diplomados tienes",
                "que talleres tienes",
                "cuales talleres tienes",
                "que cursos de salud tienes",
                "que cursos de mistica tienes",
                "que cursos de mística tienes",
            ]
        )
        if not asks_catalog or not self.teacher_memory:
            return None

        studies = list(self.teacher_memory.course_studies)

        if any(phrase in lowered for phrase in global_catalog_phrases):
            intro = "Puedo darte información sobre estas formaciones de Holoacademia: "
        elif "diplomado" in lowered or "diplomados" in lowered:
            studies = [study for study in studies if self._normalize_text(study.tipo) == "diplomado"]
            intro = "Puedo darte información sobre estos diplomados de Holoacademia: "
        elif "taller" in lowered or "talleres" in lowered:
            studies = [study for study in studies if self._normalize_text(study.tipo) == "taller"]
            intro = "Puedo darte información sobre estos talleres de Holoacademia: "
        elif "curso" in lowered or "cursos" in lowered:
            if "salud" in lowered:
                studies = [study for study in studies if self._normalize_text(study.linea) == "salud" and self._normalize_text(study.tipo) == "curso"]
                intro = "Dentro de la línea de Salud, puedo darte información sobre estos cursos: "
            elif "mistica" in lowered or "mística" in question.lower():
                studies = [study for study in studies if self._normalize_text(study.linea) == "mistica"]
                intro = "Dentro de la línea de Mística, puedo darte información sobre estas formaciones: "
            else:
                studies = [study for study in studies if self._normalize_text(study.tipo) == "curso"]
                intro = "Puedo darte información sobre estos cursos de Holoacademia: "
        elif "salud" in lowered:
            studies = [study for study in studies if self._normalize_text(study.linea) == "salud"]
            intro = "Dentro de la línea de Salud, puedo darte información sobre estas formaciones: "
        elif "mistica" in lowered or "mística" in question.lower():
            studies = [study for study in studies if self._normalize_text(study.linea) == "mistica"]
            intro = "Dentro de la línea de Mística, puedo darte información sobre estas formaciones: "
        else:
            intro = "Puedo darte información sobre estos cursos y diplomados de Holoacademia: "

        course_names = [study.course_name for study in studies]
        if not course_names:
            return None

        answer = (
            f"{intro}{self._join_items(course_names)}. "
            "Si quieres, también puedo orientarte por tema; por ejemplo, protocolos, módulos, maestros, sistemas, "
            "pares biomagnéticos, cuestionarios o de qué trata cada formación."
        )
        return AssistantOutput(answer=answer, visual=None, mode="structured")

    def _answer_supported_topics(self, question: str) -> Optional[AssistantOutput]:
        lowered = self._normalize_text(question)
        asks_scope = any(
            phrase in lowered
            for phrase in [
                "que me puedes explicar",
                "qué me puedes explicar",
                "en que me puedes ayudar",
                "en qué me puedes ayudar",
                "que me puedes decir",
                "qué me puedes decir",
                "que tipo de preguntas puedo hacerte",
                "qué tipo de preguntas puedo hacerte",
                "para que sirves",
                "para qué sirves",
                "que cosas puedes responder",
                "qué cosas puedes responder",
            ]
        )
        if not asks_scope:
            return None

        return AssistantOutput(
            answer=(
                "Puedo ayudarte con dudas sobre cursos, diplomados y talleres; por ejemplo, de qué trata una formación, "
                "qué módulos incluye, qué protocolos se ven, quién la imparte, qué sistemas trabaja, qué conceptos clave "
                "conviene estudiar y cómo se relaciona un curso con otro. También puedo seguir la conversación si primero "
                "hablamos de un curso y luego haces una pregunta corta como 'de qué trata' o 'qué protocolos trae'."
            ),
            visual=None,
            mode="structured",
        )

    def should_skip_search(self, question: str, history: Optional[list[dict]] = None) -> bool:
        history = history or []
        if self._answer_known_concepts(question) is not None:
            return True
        if self._answer_direct_structured(question, [], history) is not None:
            return True
        return False

    def _is_summary_request(self, question: str) -> bool:
        lowered = self._normalize_text(question)
        return any(
            phrase in lowered
            for phrase in [
                "de que trata",
                "de qué trata",
                "hablame",
                "háblame",
                "dame un resumen",
                "resumen del curso",
                "resumen del diplomado",
                "que se ve",
                "qué se ve",
                "que incluye",
                "qué incluye",
                "de que va",
                "de qué va",
            ]
        )

    def _build_course_summary_answer(self, course: CourseStudy) -> str:
        summary = self._clean_course_summary_seed(course.teacher_summary or course.summary)
        themes = self._join_items(course.core_themes[:4])
        concepts = self._join_items(course.key_concepts[:4])
        protocols = self._join_items([self._protocol_label(item) for item in course.protocols[:4]])
        parts = [f"{course.course_name} es una formación orientada a {summary}"]
        if themes:
            parts.append(f"Sus ejes principales son {themes}.")
        if concepts:
            parts.append(f"Los conceptos que más conviene ubicar son {concepts}.")
        if protocols:
            parts.append(f"También aparecen secuencias o protocolos como {protocols}.")
        return " ".join(parts)

    def _clean_course_summary_seed(self, text: str) -> str:
        cleaned = " ".join((text or "").split())
        cleaned = re.sub(
            r"^(como\s+(?:facilitador|maestro|docente)\s*(?:diria|diría)?[:,]?\s*)",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"^te\s+diria\s+que\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^te\s+diría\s+que\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"^(el\s+corazon|el\s+corazón)\s+del\s+(?:curso|diplomado|taller)\s+es\s+",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"^aprender\s+a\s+", "aprender a ", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned[:1].lower() + cleaned[1:] if cleaned else cleaned
        return self._compact_text(cleaned, 280)

    def _build_memory_hit_answer(self, question: str, hit) -> str:
        lowered = self._normalize_text(question)
        if any(phrase in lowered for phrase in ["que es", "qué es", "significa", "de que trata", "de qué trata"]):
            return (
                f"{hit.title} se entiende así dentro de la formación: "
                f"{self._compact_text(hit.text, 900)}"
            )
        return (
            f"Lo más claro que encuentro sobre eso es lo siguiente: "
            f"{self._compact_text(hit.text, 900)}"
        )

    def resolve_search_queries(
        self,
        question: str,
        history: Optional[list[dict]] = None,
    ) -> list[str]:
        history = history or []
        active_course = self._resolve_active_course(question, history)
        mentioned_courses = self._find_courses_in_text(question)
        queries = [question.strip()]

        last_user_question = self._last_user_question(history)
        if self._is_follow_up(question) and last_user_question:
            queries.append(f"{last_user_question}. Seguimiento: {question}")

        for course in mentioned_courses[:4]:
            course_name = course.course_name
            if self._normalize_text(course_name) not in self._normalize_text(question):
                queries.append(f"{course_name}. {question}")

        if active_course is not None:
            course_name = active_course.course_name
            if self._normalize_text(course_name) not in self._normalize_text(question):
                queries.append(f"{course_name}. {question}")

        cleaned: list[str] = []
        seen = set()
        for item in queries:
            normalized = " ".join(item.split()).strip()
            if not normalized:
                continue
            key = self._normalize_text(normalized)
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(normalized)
        max_queries = 3 if len(mentioned_courses) > 1 else 2
        return (cleaned or [question])[:max_queries]

    def should_focus_primary_course(self, question: str) -> bool:
        lowered = self._normalize_text(question)
        if len(self._find_courses_in_text(question)) > 1:
            return False
        broad_terms = ["compara", "compar", "diferencia", "todos los cursos", "varios cursos", "saga", "segun la saga"]
        return not any(term in lowered for term in broad_terms)

    def embed_query(self, text: str):
        if self.client is None:
            raise RuntimeError("OpenAI client is not configured")
        response = self.client.embeddings.create(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip() or "text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding

    def _answer_with_model(
        self,
        question: str,
        results: list[SearchResult],
        history: list[dict],
        want_visual: bool,
    ) -> Optional[AssistantOutput]:
        active_course = self._resolve_active_course(question, history)
        context_courses = self._resolve_context_courses(question, history, active_course)
        context = self._build_context(question, results, history, active_course, context_courses)
        if not context.strip():
            return None
        is_complex_cross_course = len(context_courses) > 1 or len(context) > 7000

        instructions = SAEL_SYSTEM_PROMPT
        if want_visual and self._is_visual_request(question):
            instructions += (
                " Si el usuario pide explícitamente un mapa o esquema, incluye al final una sección breve titulada "
                "'Mapa visual' con viñetas claras e indentadas."
            )
        else:
            instructions += (
                " Estructura normalmente la respuesta en 2 a 5 bloques claros cuando la pregunta lo amerite, "
                "pero sin volverla pesada."
            )
        if is_complex_cross_course:
            instructions += (
                " Si la pregunta integra varios cursos o pide un protocolo/cuestionario largo, responde de forma compacta, "
                "con pasos claros y sin explicación excesiva."
            )

        prompt = (
            f"Pregunta del usuario:\n{question}\n\n"
            f"Historial reciente:\n{self._format_history(history)}\n\n"
            f"Curso activo detectado:\n{active_course.course_name if active_course else 'Ninguno'}\n"
            f"Cursos integrados para responder:\n{self._format_course_list(context_courses)}\n\n"
            f"Contexto docente integrado:\n{context}\n\n"
            "Responde solo con la respuesta final para el alumno."
        )

        response = self._create_response(
            model=self.model,
            instructions=instructions,
            input=prompt,
            timeout=self.response_timeout,
            max_output_tokens=700 if is_complex_cross_course else 900,
        )
        last_prompt_used = prompt
        answer = self._polish_text(self._response_text(response))
        if not answer and self._response_incomplete_max_tokens(response):
            response = self._create_response(
                model=self.model,
                instructions=instructions,
                input=prompt,
                timeout=self.response_timeout,
                max_output_tokens=1000 if is_complex_cross_course else 1400,
            )
            answer = self._polish_text(self._response_text(response))
        if not answer and len(context_courses) > 1:
            focused_multi_context = "\n\n".join(self._build_course_block(course) for course in context_courses[:4])
            focused_multi_prompt = (
                f"Pregunta del usuario:\n{question}\n\n"
                f"Cursos integrados para responder:\n{self._format_course_list(context_courses)}\n\n"
                f"Contexto docente resumido por curso:\n{focused_multi_context}\n\n"
                "El usuario está pidiendo una síntesis transversal de la saga completa. "
                "Integra los cursos en una sola secuencia práctica, clara y ordenada. "
                "Responde solo con la respuesta final para el alumno."
            )
            response = self._create_response(
                model=self.model,
                instructions=instructions,
                input=focused_multi_prompt,
                timeout=self.response_timeout,
                max_output_tokens=800,
            )
            last_prompt_used = focused_multi_prompt
            answer = self._polish_text(self._response_text(response))
            if not answer and self._response_incomplete_max_tokens(response):
                response = self._create_response(
                    model=self.model,
                    instructions=instructions,
                    input=focused_multi_prompt,
                    timeout=self.response_timeout,
                    max_output_tokens=1100,
                )
                answer = self._polish_text(self._response_text(response))
        if not answer and active_course is not None:
            focused_context = self._build_course_block(active_course)
            focused_prompt = (
                f"Pregunta del usuario:\n{question}\n\n"
                f"Historial reciente:\n{self._format_history(history)}\n\n"
                f"Curso activo detectado:\n{active_course.course_name}\n\n"
                f"Contexto docente resumido:\n{focused_context}\n\n"
                "Responde solo con la respuesta final para el alumno."
            )
            response = self._create_response(
                model=self.model,
                instructions=instructions,
                input=focused_prompt,
                timeout=self.response_timeout,
                max_output_tokens=900,
            )
            last_prompt_used = focused_prompt
            answer = self._polish_text(self._response_text(response))
            if not answer and self._response_incomplete_max_tokens(response):
                response = self._create_response(
                    model=self.model,
                    instructions=instructions,
                    input=focused_prompt,
                    timeout=self.response_timeout,
                    max_output_tokens=1400,
                )
                answer = self._polish_text(self._response_text(response))
        if not answer:
            answer = self._try_text_model_fallback(instructions, last_prompt_used)
        if not answer:
            return None
        return AssistantOutput(answer=answer, visual=None, mode="reasoned_teacher")

    def _answer_without_model(
        self,
        question: str,
        results: list[SearchResult],
        history: list[dict],
    ) -> AssistantOutput:
        active_course = self._resolve_active_course(question, history)
        if active_course is not None:
            summary = self._compact_text(active_course.teacher_summary or active_course.summary, 900)
            return AssistantOutput(
                answer=(
                    f"No tengo disponible el razonamiento del modelo en este momento. "
                    f"Lo mas solido que puedo darte sin inventar, dentro de {active_course.course_name}, es esto: {summary}"
                ),
                visual=None,
                mode="teacher_memory",
            )

        best_hit = self._best_memory_hit_for_question(question)
        if best_hit is not None:
            anchor = best_hit.course_name
            if best_hit.kind == "source":
                answer = (
                    f"No tengo disponible el razonamiento del modelo en este momento. "
                    f"Lo mas solido que puedo darte sin inventar, dentro de {anchor}, es esto: "
                    f"{self._compact_text(best_hit.text, 900)}"
                )
            else:
                answer = (
                    f"No tengo disponible el razonamiento del modelo en este momento. "
                    f"Lo mas solido que puedo darte sin inventar, dentro de {anchor}, es esto: "
                    f"{self._compact_text(best_hit.text, 900)}"
                )
            return AssistantOutput(answer=answer, visual=None, mode="teacher_memory")

        if results:
            top = results[0]
            return AssistantOutput(
                answer=(
                    "No tengo disponible el razonamiento del modelo en este momento. "
                    f"Lo mas cercano que puedo ubicar con claridad pertenece a {top.course_name}: "
                    f"{self._compact_text(top.text, 800)}"
                ),
                visual=None,
                mode="fallback",
            )

        return AssistantOutput(
            answer=(
                "No tengo suficiente contexto claro para responder eso con criterio. "
                "Intenta mencionar el curso, diplomado, módulo o concepto central."
            ),
            visual=None,
            mode="fallback",
        )

    def _best_memory_hit_for_question(self, question: str):
        if not self.teacher_memory:
            return None

        normalized_question = self._normalize_text(question)
        question_tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", normalized_question)
            if len(token) >= 4 and token not in GENERIC_COURSE_TOKENS
        }
        hits = self.teacher_memory.search(question, limit=8)
        if not hits:
            return None

        ranked = []
        for hit in hits:
            score = hit.score
            title_lower = self._normalize_text(hit.title)
            text_lower = self._normalize_text(hit.text)
            if normalized_question and normalized_question in title_lower:
                score += 8.0
            if normalized_question and normalized_question in text_lower:
                score += 4.0
            overlap_title = len(question_tokens & set(re.findall(r"[a-z0-9]+", title_lower)))
            overlap_text = len(question_tokens & set(re.findall(r"[a-z0-9]+", text_lower)))
            score += overlap_title * 2.5
            score += overlap_text * 0.5
            ranked.append((score, hit))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked[0][1]

    def _answer_teacher_identity(
        self,
        question: str,
        results: list[SearchResult],
        history: list[dict],
    ) -> Optional[AssistantOutput]:
        if not self._is_teacher_identity_question(question):
            return None

        active_course = self._resolve_active_course(question, history)
        filtered = results
        if active_course is not None:
            same_course = [item for item in results if item.course_id == active_course.course_id]
            filtered = same_course or results

        names: list[str] = []
        seen = set()
        pattern = r"(?:impartido por|ponente|docente|facilitador(?:a)?)(?:\s*:|\s+)\s*([A-ZÁÉÍÓÚÜÑ][^\n]{3,120})"
        for item in filtered[:8]:
            text = " ".join(item.text.split())
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                candidate = self._clean_teacher_name(match.group(1))
                if len(candidate) < 5:
                    continue
                key = self._normalize_text(candidate)
                if key in seen:
                    continue
                seen.add(key)
                names.append(candidate)
            if names:
                break

        if not names:
            return None

        course_name = active_course.course_name if active_course is not None else filtered[0].course_name
        return AssistantOutput(
            answer=f"El maestro o ponente que aparece con mas claridad para {course_name} es {names[0]}.",
            visual=None,
            mode="structured",
        )

    def _answer_course_protocols(
        self,
        question: str,
        history: list[dict],
    ) -> Optional[AssistantOutput]:
        lowered = self._normalize_text(question)
        if "protocolo" not in lowered:
            return None
        asks_catalog = any(
            phrase in lowered
            for phrase in [
                "que protocolos se ven",
                "que protocolos incluye",
                "cuales son los protocolos",
                "que protocolos trae",
                "que protocolos lleva",
            ]
        )
        if not asks_catalog:
            return None

        course = self._resolve_active_course(question, history)
        if course is None or not course.protocols:
            return None

        protocol_names = [self._protocol_label(item) for item in course.protocols[:8]]
        answer = (
            f"En {course.course_name} no se trabaja un solo protocolo aislado, sino varias familias de intervención. "
            f"Los protocolos que aparecen con mas claridad son {self._join_items(protocol_names)}. "
            "Dicho como maestro: lo importante no es memorizar una lista suelta, sino entender cuándo usar cada secuencia dentro del proceso clínico-energético del curso."
        )
        return AssistantOutput(answer=answer, visual=None, mode="structured")

    def _answer_course_module_count(
        self,
        question: str,
        history: list[dict],
    ) -> Optional[AssistantOutput]:
        lowered = self._normalize_text(question)
        asks_modules = "modulo" in lowered or "modulos" in lowered or "módulos" in question.lower()
        asks_count = any(
            phrase in lowered
            for phrase in [
                "cuantos modulos",
                "cuantos módulos",
                "cuantas clases",
                "cuantas lecciones",
                "cuantos temas",
            ]
        )
        if not (asks_modules and asks_count):
            return None

        course = self._resolve_active_course(question, history)
        if course is None:
            return None

        meta = self._course_meta_by_id.get(course.course_id)
        if meta is None or not meta.module_numbers:
            return None

        module_count = len(meta.module_numbers)
        first_module = min(meta.module_numbers)
        last_module = max(meta.module_numbers)

        if meta.has_propedeutic and course.course_id == "diplomado-terapia-holistica-1":
            answer = (
                f"En {course.course_name}, el material compilado muestra un propedéutico y {module_count} módulos numerados "
                f"(del {first_module} al {last_module}). Dicho de forma práctica: se estudia un bloque propedéutico inicial "
                f"más {module_count} módulos de contenido."
            )
        elif module_count == 1:
            answer = (
                f"En {course.course_name}, el material compilado muestra 1 módulo principal."
            )
        else:
            answer = (
                f"En {course.course_name}, el material compilado muestra {module_count} módulos numerados "
                f"(del {first_module} al {last_module})."
            )
        return AssistantOutput(answer=answer, visual=None, mode="structured")

    def _answer_course_systems(
        self,
        question: str,
        history: list[dict],
    ) -> Optional[AssistantOutput]:
        lowered = self._normalize_text(question)
        if "sistemas" not in lowered:
            return None

        asks_count = any(
            phrase in lowered
            for phrase in [
                "cuantos sistemas",
                "que sistemas",
                "cuales son los sistemas",
            ]
        )
        if not asks_count:
            return None

        course = self._resolve_active_course(question, history)
        if course is None:
            return None

        if course.course_id == "diplomado-terapia-holistica-1":
            answer = (
                "En Terapia Holística 1, después del propedéutico, el programa se mueve sobre 11 sistemas principales: "
                f"{self._join_items(SYSTEM_LIST_TH1)}. Además, incluye un módulo transversal de problemas alimenticios. "
                "Dicho de forma simple: son 11 sistemas troncales más 1 módulo clínico complementario."
            )
            return AssistantOutput(answer=answer, visual=None, mode="structured")

        return None

    def _build_context(
        self,
        question: str,
        results: list[SearchResult],
        history: list[dict],
        active_course: Optional[CourseStudy],
        context_courses: Optional[list[CourseStudy]] = None,
    ) -> str:
        blocks: list[str] = []
        context_courses = context_courses or []
        if len(context_courses) > 1:
            context_courses = context_courses[:3]
        anchored_course = active_course or (context_courses[0] if context_courses else self._infer_course_from_memory(question))

        if context_courses:
            for course in context_courses[:4]:
                blocks.append(self._build_course_block(course))
        elif anchored_course is not None:
            blocks.append(self._build_course_block(anchored_course))

        fact_hints = self._extract_factual_hints(question, results, anchored_course)
        if fact_hints:
            blocks.append("[Hechos relevantes]\n" + "\n".join(f"- {item}" for item in fact_hints))

        history_course = self._resolve_active_course_from_history(history)
        if anchored_course is None and history_course is not None:
            blocks.append(
                "[Continuidad conversacional]\n"
                f"En el historial reciente el curso activo mas probable era: {history_course.course_name}."
            )

        return "\n\n".join(block for block in blocks if block.strip())

    def _build_course_block(self, course: CourseStudy) -> str:
        themes = self._join_items(course.core_themes[:4])
        concepts = self._join_items(course.key_concepts[:5])
        protocols = self._join_items([self._protocol_label(item) for item in course.protocols[:4]])
        study_guide = self._join_items(course.study_guide[:2])
        return "\n".join(
            [
                "[Curso activo]",
                f"Curso: {course.course_name}",
                f"Línea: {course.linea}",
                f"Tipo: {course.tipo}",
                f"Resumen docente: {self._compact_text(course.teacher_summary or course.summary, 420)}",
                f"Temas centrales: {themes}",
                f"Conceptos clave: {concepts}",
                f"Protocolos o secuencias destacadas: {protocols}",
                f"Orientación de estudio: {study_guide}",
            ]
        )

    def _select_memory_hits(self, question: str, active_course: Optional[CourseStudy]):
        if not self.teacher_memory:
            return []
        query = question
        if active_course is not None:
            query = f"{active_course.course_name}. {question}"
        hits = self.teacher_memory.search(query, limit=4)
        if active_course is not None:
            same_course = [hit for hit in hits if hit.course_id == active_course.course_id]
            hits = same_course or hits
        return hits[:2]

    def _infer_course_from_memory(self, question: str) -> Optional[CourseStudy]:
        best_hit = self._best_memory_hit_for_question(question)
        if best_hit is None:
            return None
        return self._course_by_id.get(best_hit.course_id)

    def _select_results(
        self,
        results: list[SearchResult],
        active_course: Optional[CourseStudy],
    ) -> list[SearchResult]:
        filtered = results
        if active_course is not None:
            same_course = [item for item in results if item.course_id == active_course.course_id]
            filtered = same_course or results
        useful = [
            item
            for item in filtered
            if "index_modulos" not in item.source_file.lower()
        ]
        return useful[:2]

    def _extract_factual_hints(
        self,
        question: str,
        results: list[SearchResult],
        active_course: Optional[CourseStudy],
    ) -> list[str]:
        hints: list[str] = []
        if self._is_teacher_identity_question(question):
            names = []
            seen = set()
            pattern = r"(?:impartido por|ponente|docente|facilitador(?:a)?)(?:\s*:|\s+)\s*([A-ZÁÉÍÓÚÜÑ][^\n]{3,120})"
            filtered = results
            if active_course is not None:
                same_course = [item for item in results if item.course_id == active_course.course_id]
                filtered = same_course or results
            for item in filtered[:6]:
                text = " ".join(item.text.split())
                for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                    candidate = self._clean_teacher_name(match.group(1))
                    key = self._normalize_text(candidate)
                    if candidate and key not in seen:
                        seen.add(key)
                        names.append(candidate)
            if names:
                hints.append(f"Docente o ponente detectado con mayor claridad: {names[0]}.")

        if active_course is not None:
            meta = self._course_meta_by_id.get(active_course.course_id)
            if meta is not None and meta.module_numbers:
                hints.append(
                    f"Módulos detectados para {active_course.course_name}: {len(meta.module_numbers)} "
                    f"(del {min(meta.module_numbers)} al {max(meta.module_numbers)})."
                )
                if meta.has_propedeutic:
                    hints.append(f"{active_course.course_name} incluye además un propedéutico.")

            if active_course.protocols:
                hints.append(
                    f"Protocolos o secuencias destacadas de {active_course.course_name}: "
                    f"{self._join_items([self._protocol_label(item) for item in active_course.protocols[:8]])}."
                )

            if active_course.course_id == "diplomado-terapia-holistica-1":
                hints.append(
                    "Sistemas principales de Terapia Holística 1: "
                    f"{self._join_items(SYSTEM_LIST_TH1)}. Además incluye un módulo de problemas alimenticios."
                )
        return hints

    def _resolve_active_course(
        self,
        question: str,
        history: list[dict],
    ) -> Optional[CourseStudy]:
        current = self._find_course_in_text(question)
        if current is not None:
            return current

        if not self._question_refers_to_prior_course(question):
            return None

        return self._resolve_active_course_from_history(history)

    def _resolve_active_course_from_history(self, history: list[dict]) -> Optional[CourseStudy]:
        recent = history[-10:]
        for item in reversed(recent):
            if str(item.get("role", "")).lower() != "user":
                continue
            content = str(item.get("content", "") or "")
            course = self._find_course_in_text(content)
            if course is not None:
                return course
            topic_course = self._resolve_course_from_topic_text(content)
            if topic_course is not None:
                return topic_course
        for item in reversed(recent):
            if str(item.get("role", "")).lower() == "user":
                continue
            content = str(item.get("content", "") or "")
            course = self._find_course_in_text(content)
            if course is not None:
                return course
            topic_course = self._resolve_course_from_topic_text(content)
            if topic_course is not None:
                return topic_course
        return None

    def _resolve_active_topic_from_history(self, history: list[dict]) -> Optional[dict]:
        recent = history[-12:]
        user_items = [item for item in recent if str(item.get("role", "")).lower() == "user"]
        assistant_items = [item for item in recent if str(item.get("role", "")).lower() != "user"]
        for bucket in (list(reversed(user_items)), list(reversed(assistant_items))):
            topic = self._scan_topic_bucket(bucket)
            if topic is not None:
                return topic
        return None

    def _scan_topic_bucket(self, items: list[dict]) -> Optional[dict]:
        for item in items:
            content = str(item.get("content", "") or "").strip()
            if not content:
                continue

            protocol = self._extract_protocol_subject(content)
            if protocol:
                return {
                    "kind": "protocol",
                    "label": protocol,
                    "course": self._resolve_course_for_reference_label(protocol),
                }

            subject = self._extract_defined_subject(content)
            if subject:
                return {
                    "kind": "term",
                    "label": subject,
                    "course": self._resolve_course_from_topic_text(subject),
                }

            course = self._find_course_in_text(content)
            if course is not None:
                return {"kind": "course", "course": course, "label": course.course_name}

            topic_course = self._resolve_course_from_topic_text(content)
            if topic_course is not None:
                return {"kind": "course", "course": topic_course, "label": topic_course.course_name}
        return None

    def _resolve_course_from_topic_text(self, text: str) -> Optional[CourseStudy]:
        normalized = self._normalize_text(text)
        if not normalized:
            return None
        if normalized in {"bmi", "biomagnetismo medico integral"}:
            return None
        for candidate in (normalized, normalized.replace(" de ", " ")):
            course_id = self._alias_to_course_id.get(candidate)
            if course_id:
                study = self._course_by_id.get(course_id)
                if study is not None:
                    return study

        subject = self._extract_defined_subject(text)
        if subject:
            normalized_subject = self._normalize_text(subject)
            if normalized_subject in {"bmi", "biomagnetismo medico integral"}:
                return None
            for candidate in (normalized_subject, normalized_subject.replace(" de ", " ")):
                course_id = self._alias_to_course_id.get(candidate)
                if course_id:
                    study = self._course_by_id.get(course_id)
                    if study is not None:
                        return study
        return None

    def _resolve_course_for_reference_label(self, label: str) -> Optional[CourseStudy]:
        normalized = self._normalize_text(label)
        if normalized in {"bmi", "biomagnetismo medico integral"}:
            return None
        matches: list[CourseStudy] = []
        for mapping in (
            self._manual_course_term_answers,
            self._course_term_answers,
            self._manual_course_protocol_answers,
            self._course_protocol_answers,
        ):
            for course_id, answers in mapping.items():
                if normalized in answers:
                    study = self._course_by_id.get(course_id)
                    if study is not None:
                        matches.append(study)
        deduped: list[CourseStudy] = []
        seen = set()
        for study in matches:
            if study.course_id not in seen:
                seen.add(study.course_id)
                deduped.append(study)
        return deduped[0] if len(deduped) == 1 else None

    def _find_course_in_text(self, text: str) -> Optional[CourseStudy]:
        courses = self._find_courses_in_text(text)
        if courses:
            return courses[0]

        if not self.teacher_memory:
            return None

        if not self._has_specific_course_reference(text):
            return None

        return self.teacher_memory.find_course(text)

    def _find_courses_in_text(self, text: str) -> list[CourseStudy]:
        if not self.teacher_memory:
            return []

        normalized = self._normalize_text(text)
        if normalized in {"bmi", "biomagnetismo medico integral"}:
            return []
        found: list[CourseStudy] = []
        seen = set()
        for course_id in self._expand_group_course_references(normalized):
            study = self._course_by_id.get(course_id)
            if study is not None and study.course_id not in seen:
                seen.add(study.course_id)
                found.append(study)

        for alias, course_id in self._alias_to_course_id.items():
            if not alias:
                continue
            if alias in {"bmi", "biomagnetismo medico integral"}:
                continue
            if len(alias) <= 4:
                pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
                matched = bool(re.search(pattern, normalized))
            else:
                matched = alias in normalized or self._contains_fuzzy_phrase(normalized, alias)
            if matched:
                study = self._course_by_id.get(course_id)
                if study is not None and study.course_id not in seen:
                    seen.add(study.course_id)
                    found.append(study)

        return found

    def _expand_group_course_references(self, normalized_text: str) -> list[str]:
        expanded: list[str] = []
        if (
            ("holobiomagnetismo parte 1 y 2" in normalized_text)
            or ("holobiomangetismo parte 1 y 2" in normalized_text)
        ):
            expanded.extend(
                [
                    "curso-holobiomagnetismo-parte-1",
                    "curso-holobiomagnetismo-parte-2",
                ]
            )
        if (
            ("psicosomatica y biodescodificacion 1 y 2" in normalized_text)
            or ("sicosomatica y biodescodificacion 1 y 2" in normalized_text)
        ):
            expanded.extend(
                [
                    "curso-psicosomatica-y-biodescodificacion-1",
                    "curso-psicosomatica-y-biodescodificacion-2",
                ]
            )
        return expanded

    def _contains_fuzzy_phrase(self, haystack: str, needle: str, threshold: float = 0.84) -> bool:
        haystack_tokens = re.findall(r"[a-z0-9]+", haystack)
        needle_tokens = re.findall(r"[a-z0-9]+", needle)
        if not haystack_tokens or not needle_tokens:
            return False
        window = len(needle_tokens)
        if len(haystack_tokens) < window:
            return False
        needle_text = " ".join(needle_tokens)
        for index in range(0, len(haystack_tokens) - window + 1):
            candidate = " ".join(haystack_tokens[index : index + window])
            if SequenceMatcher(None, candidate, needle_text).ratio() >= threshold:
                return True
        return False

    def _resolve_context_courses(
        self,
        question: str,
        history: list[dict],
        active_course: Optional[CourseStudy],
    ) -> list[CourseStudy]:
        current_courses = self._find_courses_in_text(question)
        if current_courses:
            return current_courses[:4]
        if active_course is not None:
            return [active_course]
        history_course = self._resolve_active_course_from_history(history)
        if history_course is not None:
            return [history_course]
        return []

    def _format_course_list(self, courses: list[CourseStudy]) -> str:
        if not courses:
            return "Ninguno"
        return ", ".join(course.course_name for course in courses[:4])

    def _has_specific_course_reference(self, text: str) -> bool:
        normalized = self._normalize_text(text)
        tokens = re.findall(r"[a-z0-9]+", normalized)
        meaningful = [token for token in tokens if token not in GENERIC_COURSE_TOKENS]
        return len(meaningful) >= 2

    def _build_alias_index(self) -> dict[str, str]:
        aliases = dict(MANUAL_ALIASES)
        if not self.teacher_memory:
            return aliases

        for study in self.teacher_memory.course_studies:
            normalized_name = self._normalize_text(study.course_name)
            aliases.setdefault(normalized_name, study.course_id)
            aliases.setdefault(normalized_name.replace(" de ", " "), study.course_id)

            stripped = normalized_name
            for prefix in ("diplomado ", "curso ", "taller "):
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix) :].strip()
            aliases.setdefault(stripped, study.course_id)
            aliases.setdefault(stripped.replace(" de ", " "), study.course_id)

            words = [token for token in re.findall(r"[a-z0-9]+", stripped) if token not in {"parte"}]
            if words:
                acronym = "".join(word[0] for word in words if not word.isdigit())
                digits = "".join(word for word in words if word.isdigit())
                if len(acronym) >= 2:
                    aliases.setdefault(f"{acronym}{digits}", study.course_id)
                    aliases.setdefault(acronym, study.course_id)
        return aliases

    def _load_course_metadata(self) -> dict[str, CourseMeta]:
        manifests = {}
        base_dir = Path(__file__).resolve().parent.parent / "data" / "processed_library"
        if not base_dir.exists():
            return manifests

        for manifest_path in base_dir.rglob("course_manifest.json"):
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            course_id = payload.get("course_id")
            course_name = payload.get("course_name")
            if not course_id or not course_name:
                continue

            module_numbers = set()
            has_propedeutic = False
            for source in payload.get("sources", []):
                original = str(source.get("archivo_original", "") or "")
                lowered = self._normalize_text(original)
                if "propedeutic" in lowered or "propedeutico" in lowered:
                    has_propedeutic = True
                for match in re.finditer(r"\bmodulo\s*(\d+)\b", lowered):
                    try:
                        module_numbers.add(int(match.group(1)))
                    except ValueError:
                        continue

            manifests[course_id] = CourseMeta(
                course_id=course_id,
                course_name=course_name,
                module_numbers=sorted(module_numbers),
                has_propedeutic=has_propedeutic,
            )

        return manifests

    def _question_refers_to_prior_course(self, question: str) -> bool:
        lowered = self._normalize_text(question)
        if any(hint in lowered for hint in FOLLOW_UP_HINTS):
            return True
        return any(hint in lowered for hint in COURSE_REFERENCE_HINTS)

    def _is_follow_up(self, question: str) -> bool:
        lowered = self._normalize_text(question)
        return any(hint in lowered for hint in FOLLOW_UP_HINTS)

    def _is_visual_request(self, question: str) -> bool:
        lowered = self._normalize_text(question)
        return any(term in lowered for term in ["mapa", "visual", "esquema", "diagrama"])

    def _is_teacher_identity_question(self, question: str) -> bool:
        lowered = self._normalize_text(question)
        return any(
            phrase in lowered
            for phrase in [
                "quien es el maestro",
                "quien es la maestra",
                "quien imparte",
                "quien da el diplomado",
                "quien da el curso",
                "quien es el docente",
                "quien es la docente",
                "quien es el ponente",
                "quien es el facilitador",
                "quien es la facilitadora",
            ]
        )

    def _clean_teacher_name(self, raw: str) -> str:
        candidate = re.sub(r"\s+", " ", raw).strip(" .,:;")
        stop_markers = [
            r"\bCIERRE\b",
            r"\bCONTACTO\b",
            r"\bBIOMAGNETISMO\b",
            r"\bMEDICO\b",
            r"\bM[EÉ]DICO\b",
            r"\bSUR\b",
            r"\bEL PODER\b",
            r"\bMODULO\b",
            r"\bM[ÓO]DULO\b",
            r"\bCURSO\b",
            r"\bDIPLOMADO\b",
            r"@",
            r"\bOUTLOOK\b",
            r"\bGMAIL\b",
            r"\bHOTMAIL\b",
        ]
        for marker in stop_markers:
            candidate = re.split(marker, candidate, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .,:;")
        candidate = re.sub(r"\s{2,}", " ", candidate).strip(" .,:;")
        tokens = candidate.split()
        if len(tokens) > 6:
            tokens = tokens[:6]
        candidate = " ".join(tokens).strip(" .,:;")
        if not candidate:
            return ""
        has_person_hint = bool(
            re.search(r"\b(dr|dra|mtro|mtra|maestro|maestra|lic|ing)\.?\b", candidate, flags=re.IGNORECASE)
        )
        capitalized = re.findall(r"\b[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ.]+\b", candidate)
        if not has_person_hint and len(capitalized) < 2:
            return ""
        return candidate

    def _create_response(self, **kwargs):
        if self.client is None:
            raise RuntimeError("OpenAI client is not configured")

        requested_model = str(kwargs.get("model", "") or self.model)
        candidates = [requested_model]
        for fallback in self.fallback_models:
            if fallback and fallback not in candidates:
                candidates.append(fallback)

        last_error = None
        for model_name in candidates:
            call_kwargs = dict(kwargs)
            call_kwargs["model"] = model_name
            if model_name.startswith("gpt-5"):
                call_kwargs.setdefault("reasoning", {"effort": self.reasoning_effort})
            else:
                call_kwargs.pop("reasoning", None)
            try:
                response = self.client.responses.create(**call_kwargs)
                self.last_model_error = ""
                self.model = model_name
                return response
            except Exception as exc:
                last_error = exc
                self.last_model_error = f"{type(exc).__name__}: {exc}"

        if last_error is not None:
            raise last_error
        raise RuntimeError("No se pudo completar la llamada al modelo")

    def _response_text(self, response) -> str:
        text = getattr(response, "output_text", "") or ""
        if text.strip():
            return text.strip()

        output = getattr(response, "output", None) or []
        parts: list[str] = []
        for item in output:
            for content in getattr(item, "content", []) or []:
                value = getattr(content, "text", None)
                if value:
                    parts.append(value)
                elif isinstance(content, dict):
                    maybe_text = content.get("text")
                    if maybe_text:
                        parts.append(str(maybe_text))
        return "\n".join(part.strip() for part in parts if part and part.strip()).strip()

    def _response_incomplete_max_tokens(self, response) -> bool:
        incomplete_details = getattr(response, "incomplete_details", None)
        if incomplete_details is None and hasattr(response, "model_dump"):
            try:
                incomplete_details = response.model_dump().get("incomplete_details")
            except Exception:
                incomplete_details = None
        if isinstance(incomplete_details, dict):
            return incomplete_details.get("reason") == "max_output_tokens"
        return False

    def _try_text_model_fallback(self, instructions: str, prompt: str) -> str:
        fallback_model = next(
            (model_name for model_name in self.fallback_models if not model_name.startswith("gpt-5")),
            None,
        )
        if not fallback_model:
            return ""
        try:
            response = self._create_response(
                model=fallback_model,
                instructions=instructions,
                input=prompt,
                timeout=self.response_timeout,
                max_output_tokens=1200,
            )
        except Exception:
            return ""
        return self._polish_text(self._response_text(response))

    def _format_history(self, history: list[dict]) -> str:
        if not history:
            return "Sin historial relevante."
        lines = []
        for item in history[-6:]:
            role = str(item.get("role", "user")).strip() or "user"
            content = self._compact_text(str(item.get("content", "") or ""), 260)
            if not content:
                continue
            lines.append(f"{role}: {content}")
        return "\n".join(lines) if lines else "Sin historial relevante."

    def _last_user_question(self, history: list[dict]) -> str:
        for item in reversed(history):
            if str(item.get("role", "")).lower() == "user":
                content = str(item.get("content", "") or "").strip()
                if content:
                    return content
        return ""

    def _protocol_label(self, raw: str) -> str:
        text = re.sub(r"\s+", " ", raw).strip()
        if ":" in text:
            text = text.split(":", 1)[0].strip()
        if len(text) > 80:
            text = text[:79].rstrip(" ,.;:") + "…"
        return text

    def _join_items(self, items: list[str]) -> str:
        clean = [item.strip() for item in items if item and item.strip()]
        if not clean:
            return ""
        if len(clean) == 1:
            return clean[0]
        if len(clean) == 2:
            return f"{clean[0]} y {clean[1]}"
        return f"{', '.join(clean[:-1])} y {clean[-1]}"

    def _compact_text(self, text: str, limit: int = 420) -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1].rstrip(" ,.;:") + "…"

    def _polish_text(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        cleaned = cleaned.replace(" ,", ",").replace(" .", ".")
        cleaned = cleaned.replace("..", ".")
        return cleaned

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text or "")
        without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
        return without_accents.lower()
