from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional dependency at runtime
    np = None


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
    "par",
    "pares",
    "punto",
    "puntos",
}


@dataclass
class SearchResult:
    chunk_id: str
    course_id: str
    course_name: str
    linea: str
    source_file: str
    heading: str
    text: str
    score: float


class KnowledgeBase:
    def __init__(self, chunks_path: Path):
        self.chunks_path = chunks_path
        self.records = self._load_records(chunks_path)
        self.catalog = self._build_catalog(self.records)
        self.embedding_vectors = self._load_embedding_vectors(chunks_path, len(self.records))

    def _load_records(self, chunks_path: Path) -> list[dict]:
        records = []
        with chunks_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                record["_course_name_lower"] = self._normalize_text(record.get("course_name", ""))
                record["_heading_lower"] = self._normalize_text(record.get("heading", ""))
                record["_text_lower"] = self._normalize_text(record.get("text", ""))
                record["_course_name_tokens"] = self._tokenize(record.get("course_name", ""))
                record["_tokens"] = self._tokenize(
                    " ".join(
                        filter(
                            None,
                            [
                                record.get("course_name", ""),
                                record.get("heading", ""),
                                record.get("text", ""),
                            ],
                        )
                    )
                )
                records.append(record)
        return records

    def _build_catalog(self, records: list[dict]) -> list[dict]:
        by_course = {}
        for record in records:
            by_course.setdefault(
                record["course_id"],
                {
                    "course_id": record["course_id"],
                    "course_name": record["course_name"],
                    "linea": record["linea"],
                },
            )
        return sorted(by_course.values(), key=lambda item: (item["linea"], item["course_name"]))

    def _load_embedding_vectors(self, chunks_path: Path, expected_count: int):
        if np is None:
            return None

        default_path = chunks_path.parent.parent / "embeddings" / "library_vectors.npy"
        vectors_path = Path(os.getenv("EMBEDDINGS_VECTORS_PATH", default_path)).expanduser()
        if not vectors_path.exists():
            return None

        try:
            vectors = np.load(vectors_path, mmap_mode="r")
        except Exception:
            return None

        if len(vectors.shape) != 2 or vectors.shape[0] != expected_count:
            return None
        return vectors

    @property
    def semantic_ready(self) -> bool:
        return self.embedding_vectors is not None

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
        return without_accents.lower()

    def _tokenize(self, text: str) -> set[str]:
        normalized_text = self._normalize_text(text)
        return {
            token
            for token in (match.group(0).lower() for match in TOKEN_PATTERN.finditer(normalized_text))
            if token not in STOPWORDS
        }

    def _score_record(self, question_tokens: set[str], question: str, record: dict) -> float:
        if not question_tokens:
            return 0.0

        overlap = question_tokens & record["_tokens"]
        if not overlap:
            return 0.0

        significant_tokens = {token for token in question_tokens if len(token) >= 5}
        if significant_tokens and not (significant_tokens & overlap):
            return 0.0

        overlap_score = len(overlap) / math.sqrt(len(record["_tokens"]) + 1)
        density_score = 0.0
        for token in overlap:
            density_score += record["_course_name_lower"].count(token) * 2.5
            density_score += record["_heading_lower"].count(token) * 2.0
            density_score += record["_text_lower"].count(token) * 1.0
        density_score = density_score / math.sqrt(len(record["_text_lower"]) / 120 + 1)

        phrase_bonus = 0.0
        lowered_question = self._normalize_text(question)
        if lowered_question in record["_text_lower"]:
            phrase_bonus += 0.75
        if any(token in record["_heading_lower"] for token in question_tokens):
            phrase_bonus += 0.25

        title_match_bonus = 0.0
        title_overlap = question_tokens & record["_course_name_tokens"]
        if title_overlap:
            title_match_bonus += len(title_overlap) * 1.2
        if question_tokens <= record["_course_name_tokens"]:
            title_match_bonus += 1.5

        score = overlap_score + density_score + phrase_bonus + title_match_bonus

        source_type = record.get("source_type", "")
        if source_type == "indice":
            score *= 0.35
        elif source_type == "manual":
            score *= 1.1

        return score

    def search(
        self,
        question: str,
        course_id: Optional[str] = None,
        linea: Optional[str] = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        question_tokens = self._tokenize(question)
        candidates = self.records

        if course_id:
            candidates = [record for record in candidates if record["course_id"] == course_id]
        if linea:
            candidates = [record for record in candidates if record["linea"].lower() == linea.lower()]

        scored = []
        for record in candidates:
            score = self._score_record(question_tokens, question, record)
            if score <= 0:
                continue
            scored.append(
                SearchResult(
                    chunk_id=record["chunk_id"],
                    course_id=record["course_id"],
                    course_name=record["course_name"],
                    linea=record["linea"],
                    source_file=record["source_file"],
                    heading=record.get("heading", ""),
                    text=record["text"],
                    score=score,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    def semantic_search_by_vector(
        self,
        query_vector,
        course_id: Optional[str] = None,
        linea: Optional[str] = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        if self.embedding_vectors is None or np is None:
            return []

        vector = np.asarray(query_vector, dtype=np.float32)
        if vector.ndim != 1:
            return []
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            return []
        vector = vector / norm

        similarities = self.embedding_vectors @ vector
        scored: list[SearchResult] = []
        for idx, record in enumerate(self.records):
            if course_id and record["course_id"] != course_id:
                continue
            if linea and record["linea"].lower() != linea.lower():
                continue
            score = float(similarities[idx])
            if score <= 0:
                continue
            scored.append(
                SearchResult(
                    chunk_id=record["chunk_id"],
                    course_id=record["course_id"],
                    course_name=record["course_name"],
                    linea=record["linea"],
                    source_file=record["source_file"],
                    heading=record.get("heading", ""),
                    text=record["text"],
                    score=score,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]


def trim_excerpt(text: str, max_chars: int = 420) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"
