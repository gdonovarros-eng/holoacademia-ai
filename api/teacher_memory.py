from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ]{2,}")
STOPWORDS = {
    "a",
    "al",
    "ante",
    "como",
    "con",
    "cual",
    "cuales",
    "de",
    "del",
    "donde",
    "el",
    "ella",
    "ellas",
    "ellos",
    "en",
    "entre",
    "era",
    "es",
    "esa",
    "ese",
    "eso",
    "esta",
    "este",
    "esto",
    "fue",
    "ha",
    "hay",
    "la",
    "las",
    "lo",
    "los",
    "mi",
    "mis",
    "para",
    "por",
    "que",
    "qué",
    "se",
    "ser",
    "sin",
    "sobre",
    "su",
    "sus",
    "te",
    "tu",
    "tus",
    "un",
    "una",
    "uno",
    "unas",
    "unos",
    "ya",
    "yo",
}


@dataclass
class SourceStudy:
    course_id: str
    course_name: str
    source_file: str
    source_title: str
    summary: str
    key_points: list[str]
    key_concepts: list[str]
    protocols: list[str]
    glossary: list[str]


@dataclass
class CourseStudy:
    course_id: str
    course_name: str
    linea: str
    tipo: str
    summary: str
    teacher_summary: str
    core_themes: list[str]
    key_concepts: list[str]
    protocols: list[str]
    study_guide: list[str]
    common_questions: list[str]


@dataclass
class MemoryHit:
    kind: str
    course_id: str
    course_name: str
    title: str
    text: str
    source_file: str
    score: float


class TeacherMemory:
    def __init__(self, course_studies: list[CourseStudy], source_studies: list[SourceStudy]) -> None:
        self.course_studies = course_studies
        self.source_studies = source_studies
        self._course_by_id = {study.course_id: study for study in course_studies}
        self._docs = self._build_docs(course_studies, source_studies)

    @property
    def ready(self) -> bool:
        return bool(self.course_studies or self.source_studies)

    @property
    def course_count(self) -> int:
        return len(self.course_studies)

    @property
    def source_count(self) -> int:
        return len(self.source_studies)

    @classmethod
    def from_file(cls, path: Path) -> "TeacherMemory":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            course_studies=[CourseStudy(**item) for item in payload.get("course_studies", [])],
            source_studies=[SourceStudy(**item) for item in payload.get("source_studies", [])],
        )

    def search(self, question: str, limit: int = 5) -> list[MemoryHit]:
        question_tokens = self._tokenize(question)
        if not question_tokens:
            return []

        hits: list[MemoryHit] = []
        normalized_question = self._normalize_text(question)
        for doc in self._docs:
            score = 0.0
            overlap = question_tokens & doc["_tokens"]
            if not overlap:
                continue

            score += len(overlap) * 1.8
            if any(token in doc["_title_lower"] for token in question_tokens):
                score += 1.5
            if normalized_question in doc["_text_lower"]:
                score += 2.5
            if question_tokens <= doc["_tokens"]:
                score += 1.0

            hits.append(
                MemoryHit(
                    kind=doc["kind"],
                    course_id=doc["course_id"],
                    course_name=doc["course_name"],
                    title=doc["title"],
                    text=doc["text"],
                    source_file=doc["source_file"],
                    score=score,
                )
            )

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:limit]

    def find_course(self, query: str) -> Optional[CourseStudy]:
        normalized_query = self._normalize_text(query)
        ranked: list[tuple[float, CourseStudy]] = []
        query_tokens = self._tokenize(query)
        for study in self.course_studies:
            score = 0.0
            name_lower = self._normalize_text(study.course_name)
            if normalized_query and normalized_query in name_lower:
                score += 8.0
            name_tokens = self._tokenize(study.course_name)
            overlap = query_tokens & name_tokens
            if overlap:
                score += len(overlap) * 2.5
                coverage = len(overlap) / max(len(query_tokens), 1)
                score += coverage * 2.0
            if "diplomado" in query_tokens and "diplomado" in name_tokens:
                score += 1.5
            if "curso" in query_tokens and "curso" in name_tokens:
                score += 1.0
            if "taller" in query_tokens and "taller" in name_tokens:
                score += 1.0
            if score > 0:
                ranked.append((score, study))
        ranked.sort(key=lambda item: item[0], reverse=True)
        if not ranked:
            return None
        best_score, best_study = ranked[0]
        if normalized_query and normalized_query in self._normalize_text(best_study.course_name):
            return best_study
        if len(query_tokens) >= 2:
            overlap = len(query_tokens & self._tokenize(best_study.course_name))
            if overlap / max(len(query_tokens), 1) < 0.5:
                return None
        return best_study if best_score >= 4.0 else None

    def get_course(self, course_id: str) -> Optional[CourseStudy]:
        return self._course_by_id.get(course_id)

    def render_context(self, question: str, limit: int = 4) -> str:
        blocks = []
        for index, hit in enumerate(self.search(question, limit=limit), start=1):
            blocks.append(
                "\n".join(
                    [
                        f"[Memoria {index}]",
                        f"Tipo: {hit.kind}",
                        f"Curso: {hit.course_name}",
                        f"Tema: {hit.title}",
                        f"Contenido: {self._compact_text(hit.text)}",
                    ]
                )
            )
        return "\n\n".join(blocks)

    def _build_docs(
        self,
        course_studies: list[CourseStudy],
        source_studies: list[SourceStudy],
    ) -> list[dict]:
        docs: list[dict] = []

        for course in course_studies:
            text = " ".join(
                part
                for part in [
                    course.teacher_summary,
                    course.summary,
                    " ".join(course.core_themes[:6]),
                    " ".join(course.key_concepts[:8]),
                    " ".join(course.protocols[:6]),
                    " ".join(course.study_guide[:4]),
                ]
                if part
            )
            docs.append(
                self._make_doc(
                    kind="course",
                    course_id=course.course_id,
                    course_name=course.course_name,
                    title=course.course_name,
                    text=text,
                    source_file="",
                )
            )

        for source in source_studies:
            text = " ".join(
                part
                for part in [
                    source.summary,
                    " ".join(source.key_points[:4]),
                    " ".join(source.key_concepts[:8]),
                    " ".join(source.protocols[:5]),
                    " ".join(source.glossary[:6]),
                ]
                if part
            )
            docs.append(
                self._make_doc(
                    kind="source",
                    course_id=source.course_id,
                    course_name=source.course_name,
                    title=source.source_title,
                    text=text,
                    source_file=source.source_file,
                )
            )

        return docs

    def _make_doc(
        self,
        kind: str,
        course_id: str,
        course_name: str,
        title: str,
        text: str,
        source_file: str,
    ) -> dict:
        normalized_title = self._normalize_text(title)
        normalized_text = self._normalize_text(text)
        return {
            "kind": kind,
            "course_id": course_id,
            "course_name": course_name,
            "title": title,
            "text": text,
            "source_file": source_file,
            "_title_lower": normalized_title,
            "_text_lower": normalized_text,
            "_tokens": self._tokenize(f"{title} {text}"),
        }

    def _compact_text(self, text: str, max_chars: int = 850) -> str:
        clean = re.sub(r"\s+", " ", text).strip()
        if len(clean) <= max_chars:
            return clean
        return clean[: max_chars - 1].rstrip() + "…"

    def _tokenize(self, text: str) -> set[str]:
        normalized_text = self._normalize_text(text)
        return {
            token
            for token in (match.group(0).lower() for match in TOKEN_PATTERN.finditer(normalized_text))
            if token not in STOPWORDS
        }

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


@lru_cache
def get_teacher_memory() -> Optional[TeacherMemory]:
    base_dir = Path(__file__).resolve().parent.parent
    memory_path = base_dir / "data" / "teacher_memory.json"
    partial_path = base_dir / "data" / "teacher_memory.partial.json"

    for path in (memory_path, partial_path):
        if not path.exists():
            continue
        try:
            memory = TeacherMemory.from_file(path)
        except Exception:
            continue
        if memory.ready:
            return memory
    return None
