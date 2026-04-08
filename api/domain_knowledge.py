from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


PAIR_LINE_PATTERN = re.compile(
    r"^(?P<pair>[A-ZÁÉÍÓÚÜÑ0-9 /().,]+(?:[-–][A-ZÁÉÍÓÚÜÑ0-9 /().,]+)+)\s{2,}(?P<rest>.*)$"
)


@dataclass
class PairCatalogEntry:
    pair_name: str
    normalized_pair_name: str
    related_condition: str
    pair_type: str
    source_file: str


@dataclass
class ProtocolEntry:
    title: str
    normalized_title: str
    body: str
    source_file: str


@dataclass
class CourseDigestEntry:
    course_id: str
    course_name: str
    normalized_course_name: str
    linea: str
    tipo: str
    themes: list[str]
    protocols: list[str]
    source_count: int


@dataclass
class ConceptDigestEntry:
    concept_name: str
    normalized_concept_name: str
    aliases: list[str]
    summary: str
    bullet_points: list[str]
    source_files: list[str]


class TeacherKnowledge:
    def __init__(
        self,
        pair_entries: list[PairCatalogEntry],
        protocol_entries: list[ProtocolEntry],
        course_digests: list[CourseDigestEntry],
        concept_digests: list[ConceptDigestEntry],
    ) -> None:
        self.pair_entries = pair_entries
        self._pair_by_name = {entry.normalized_pair_name: entry for entry in pair_entries}
        self.protocol_entries = protocol_entries
        self._protocol_by_title = {entry.normalized_title: entry for entry in protocol_entries}
        self.course_digests = course_digests
        self._course_by_id = {entry.course_id: entry for entry in course_digests}
        self.concept_digests = concept_digests
        self._concept_by_name = {
            entry.normalized_concept_name: entry for entry in concept_digests
        }

    @property
    def pair_count_total(self) -> int:
        return len(self.pair_entries)

    @property
    def pair_count_unique(self) -> int:
        return len(self._pair_by_name)

    @property
    def protocol_count(self) -> int:
        return len(self.protocol_entries)

    @property
    def course_count(self) -> int:
        return len(self.course_digests)

    @property
    def concept_count(self) -> int:
        return len(self.concept_digests)

    def find_pair(self, query: str) -> PairCatalogEntry | None:
        normalized_query = self._normalize_text(query)
        normalized_query = re.sub(r"\s+", " ", normalized_query).strip()
        normalized_query = re.sub(r"\s*[-–]\s*", " - ", normalized_query).strip()
        if normalized_query in self._pair_by_name:
            return self._pair_by_name[normalized_query]

        if " - " in normalized_query:
            for entry in self.pair_entries:
                if normalized_query == entry.normalized_pair_name:
                    return entry

        ranked = self.search_pairs(query, limit=1)
        return ranked[0] if ranked else None

    def search_pairs(self, query: str, limit: int = 5) -> list[PairCatalogEntry]:
        normalized_query = self._normalize_text(query)
        query_tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", normalized_query)
            if len(token) >= 3 and token not in {"para", "sirve", "par", "pares", "tipo"}
        }
        if not query_tokens:
            return []

        scored: list[tuple[float, PairCatalogEntry]] = []
        for entry in self.pair_entries:
            score = 0.0
            if normalized_query in entry.normalized_pair_name:
                score += 10.0

            name_tokens = set(re.findall(r"[a-z0-9]+", entry.normalized_pair_name))
            overlap = query_tokens & name_tokens
            if overlap:
                score += len(overlap) * 2.0

            condition_text = self._normalize_text(entry.related_condition)
            condition_tokens = set(re.findall(r"[a-z0-9]+", condition_text))
            condition_overlap = query_tokens & condition_tokens
            if condition_overlap:
                score += len(condition_overlap) * 0.5

            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda item: (item[0], item[1].pair_name), reverse=True)
        return [entry for _, entry in scored[:limit]]

    @classmethod
    def from_library(cls, library_root: Path, manual_path: Path) -> "TeacherKnowledge":
        pair_entries = _extract_pair_catalog(manual_path)
        protocol_entries = _extract_protocol_catalog(library_root)
        course_digests = _extract_course_digests(library_root, protocol_entries)
        concept_digests = _extract_concept_digests(library_root)
        return cls(
            pair_entries=pair_entries,
            protocol_entries=protocol_entries,
            course_digests=course_digests,
            concept_digests=concept_digests,
        )

    @classmethod
    def from_cache(cls, cache_path: Path) -> "TeacherKnowledge":
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return cls(
            pair_entries=[PairCatalogEntry(**item) for item in payload.get("pair_entries", [])],
            protocol_entries=[ProtocolEntry(**item) for item in payload.get("protocol_entries", [])],
            course_digests=[CourseDigestEntry(**item) for item in payload.get("course_digests", [])],
            concept_digests=[ConceptDigestEntry(**item) for item in payload.get("concept_digests", [])],
        )

    def to_cache(self, cache_path: Path) -> None:
        payload = {
            "pair_entries": [asdict(entry) for entry in self.pair_entries],
            "protocol_entries": [asdict(entry) for entry in self.protocol_entries],
            "course_digests": [asdict(entry) for entry in self.course_digests],
            "concept_digests": [asdict(entry) for entry in self.concept_digests],
        }
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def find_protocol(self, query: str) -> ProtocolEntry | None:
        normalized_query = self._normalize_text(query)
        normalized_query = re.sub(r"\s+", " ", normalized_query).strip()
        if normalized_query in self._protocol_by_title:
            return self._protocol_by_title[normalized_query]

        ranked = self.search_protocols(query, limit=1)
        return ranked[0] if ranked else None

    def search_protocols(self, query: str, limit: int = 5) -> list[ProtocolEntry]:
        normalized_query = self._normalize_text(query)
        query_tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", normalized_query)
            if len(token) >= 3 and token not in {"protocolo", "protocolos", "para", "del", "de"}
        }
        if not query_tokens:
            return []

        scored: list[tuple[float, ProtocolEntry]] = []
        for entry in self.protocol_entries:
            score = 0.0
            if normalized_query in entry.normalized_title:
                score += 10.0

            title_tokens = set(re.findall(r"[a-z0-9]+", entry.normalized_title))
            overlap = query_tokens & title_tokens
            if overlap:
                score += len(overlap) * 2.5

            body_text = self._normalize_text(entry.body)
            body_tokens = set(re.findall(r"[a-z0-9]+", body_text))
            body_overlap = query_tokens & body_tokens
            if body_overlap:
                score += len(body_overlap) * 0.6

            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda item: (item[0], item[1].title), reverse=True)
        return [entry for _, entry in scored[:limit]]

    def find_course(self, query: str) -> CourseDigestEntry | None:
        ranked = self.search_courses(query, limit=1)
        return ranked[0] if ranked else None

    def find_concept(self, query: str) -> ConceptDigestEntry | None:
        ranked = self.search_concepts(query, limit=1)
        return ranked[0] if ranked else None

    def search_courses(self, query: str, limit: int = 5) -> list[CourseDigestEntry]:
        normalized_query = self._normalize_text(query)
        query_tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", normalized_query)
            if (len(token) >= 3 or token.isdigit())
            and token
            not in {
                "dame",
                "quiero",
                "resumen",
                "resumeme",
                "resumir",
                "curso",
                "diplomado",
                "taller",
                "del",
                "de",
                "la",
                "el",
            }
        }
        if not query_tokens:
            return []

        scored: list[tuple[float, CourseDigestEntry]] = []
        for entry in self.course_digests:
            score = 0.0
            if entry.normalized_course_name in normalized_query:
                score += 8.0
            name_tokens = set(re.findall(r"[a-z0-9]+", entry.normalized_course_name))
            overlap = query_tokens & name_tokens
            if overlap:
                score += len(overlap) * 3.0

            if all(token in entry.normalized_course_name for token in query_tokens):
                score += 4.0

            theme_blob = self._normalize_text(" ".join(entry.themes))
            theme_tokens = set(re.findall(r"[a-z0-9]+", theme_blob))
            theme_overlap = query_tokens & theme_tokens
            if theme_overlap:
                score += len(theme_overlap) * 0.8

            protocol_blob = self._normalize_text(" ".join(entry.protocols))
            protocol_tokens = set(re.findall(r"[a-z0-9]+", protocol_blob))
            protocol_overlap = query_tokens & protocol_tokens
            if protocol_overlap:
                score += len(protocol_overlap) * 0.5

            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda item: (item[0], item[1].course_name), reverse=True)
        return [entry for _, entry in scored[:limit]]

    def search_concepts(self, query: str, limit: int = 5) -> list[ConceptDigestEntry]:
        normalized_query = self._normalize_text(query)
        query_tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", normalized_query)
            if len(token) >= 3
            and token
            not in {
                "hablame",
                "hablar",
                "sobre",
                "explicame",
                "explica",
                "dime",
                "quiero",
                "entender",
                "resumen",
                "resumeme",
                "que",
                "son",
                "del",
                "las",
                "los",
                "una",
                "uno",
            }
        }
        if not query_tokens:
            return []

        scored: list[tuple[float, ConceptDigestEntry]] = []
        for entry in self.concept_digests:
            score = 0.0
            if entry.normalized_concept_name in normalized_query:
                score += 8.0

            alias_blob = " ".join(entry.aliases)
            alias_tokens = set(re.findall(r"[a-z0-9]+", alias_blob))
            overlap = query_tokens & alias_tokens
            if overlap:
                score += len(overlap) * 2.5

            summary_tokens = set(re.findall(r"[a-z0-9]+", self._normalize_text(entry.summary)))
            summary_overlap = query_tokens & summary_tokens
            if summary_overlap:
                score += len(summary_overlap) * 0.6

            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda item: (item[0], item[1].concept_name), reverse=True)
        return [entry for _, entry in scored[:limit]]

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        no_accents = "".join(char for char in normalized if not unicodedata.combining(char))
        no_accents = no_accents.replace("–", "-")
        return no_accents.lower()


def _clean_line(line: str) -> str:
    line = line.replace("\t", " ")
    line = re.sub(r"\s+", " ", line).strip()
    return line


def _looks_like_footer(line: str) -> bool:
    lowered = line.lower()
    if not lowered:
        return True
    if "alejandro lavin" in lowered:
        return True
    if "www." in lowered:
        return True
    if "para información de cursos" in lowered or "para informacion de cursos" in lowered:
        return True
    if line.isdigit():
        return True
    if "par biomagnetico" in lowered and "padecimiento relacionado" in lowered:
        return True
    if "relacion de par / padecimiento" in lowered:
        return True
    return False


def _extract_type_and_seed(rest: str) -> tuple[str, str]:
    fragments = [fragment.strip() for fragment in re.split(r"\s{2,}", rest) if fragment.strip()]
    if not fragments:
        return "", ""
    if len(fragments) == 1:
        return fragments[0], ""
    return fragments[-1], " ".join(fragments[:-1])


def _extract_pair_catalog(manual_path: Path) -> list[PairCatalogEntry]:
    text = manual_path.read_text(encoding="utf-8", errors="ignore").replace("\f", "\n")
    start = text.find("Relación de Par / Padecimiento.")
    end = text.find("PROTOCOLO DE GEOPATÍAS", start)
    if start == -1 or end == -1:
        return []

    section = text[start:end]
    raw_lines = section.splitlines()
    cleaned_lines = [_clean_line(raw_line) for raw_line in raw_lines]
    pair_positions = []
    for idx, raw_line in enumerate(raw_lines):
        cleaned = cleaned_lines[idx]
        if _looks_like_footer(cleaned):
            continue
        match = PAIR_LINE_PATTERN.match(raw_line)
        if match:
            pair_positions.append((idx, match))

    entries: list[PairCatalogEntry] = []

    for index, match in pair_positions:
        pair_name = _clean_line(match.group("pair")).replace(" – ", " - ").replace("–", "-")
        pair_type, seed_description = _extract_type_and_seed(match.group("rest"))
        context_lines: list[str] = []

        if not seed_description:
            for offset in (2, 1):
                previous_index = index - offset
                if previous_index < 0:
                    continue
                candidate = cleaned_lines[previous_index]
                if not candidate or _looks_like_footer(candidate):
                    continue
                if PAIR_LINE_PATTERN.match(raw_lines[previous_index]):
                    continue
                context_lines.append(candidate)

            for offset in (1, 2):
                next_index = index + offset
                if next_index >= len(raw_lines):
                    continue
                candidate = cleaned_lines[next_index]
                if not candidate or _looks_like_footer(candidate):
                    continue
                if PAIR_LINE_PATTERN.match(raw_lines[next_index]):
                    continue
                context_lines.append(candidate)

        description_parts = []
        if seed_description:
            description_parts.append(seed_description)
        description_parts.extend(context_lines)
        description = " ".join(part for part in description_parts if part).strip(" .")
        description = re.sub(r"\s+", " ", description)
        if not description:
            description = "Sin descripción clara en la tabla."

        entries.append(
            PairCatalogEntry(
                pair_name=pair_name,
                normalized_pair_name=TeacherKnowledge._normalize_text(pair_name).replace(" - ", " - ").strip(),
                related_condition=description,
                pair_type=pair_type or "Sin tipo claro",
                source_file=str(manual_path),
            )
        )
    return entries


def _looks_like_protocol_heading(line: str) -> bool:
    normalized = _clean_line(line.replace("\f", " "))
    if not normalized:
        return False
    lowered = TeacherKnowledge._normalize_text(normalized)
    if lowered in {"protocolo", "protocolos"}:
        return False
    return lowered.startswith("protocolo ")


def _extract_protocol_catalog(library_root: Path) -> list[ProtocolEntry]:
    entries: list[ProtocolEntry] = []
    seen: set[tuple[str, str]] = set()

    for txt_path in sorted(library_root.rglob("*.txt")):
        text = txt_path.read_text(encoding="utf-8", errors="ignore").replace("\f", "\n")
        raw_lines = text.splitlines()
        cleaned_lines = [_clean_line(raw_line) for raw_line in raw_lines]

        for index, heading in enumerate(cleaned_lines):
            if not _looks_like_protocol_heading(heading):
                continue

            body_lines: list[str] = []
            blank_run = 0
            for next_index in range(index + 1, min(len(cleaned_lines), index + 40)):
                candidate = cleaned_lines[next_index]
                if _looks_like_protocol_heading(candidate):
                    break
                if _looks_like_footer(candidate):
                    continue
                if not candidate:
                    blank_run += 1
                    if blank_run >= 2 and body_lines:
                        break
                    continue
                blank_run = 0
                if candidate.lower() in {"objetivo", "objetivos", "paso", "pasos"}:
                    continue
                if len(candidate) < 4:
                    continue
                body_lines.append(candidate)
                if len(body_lines) >= 12:
                    break

            body = " ".join(body_lines).strip()
            body = re.sub(r"\s+", " ", body)
            if not body:
                continue

            title = heading
            normalized_title = TeacherKnowledge._normalize_text(title)
            dedupe_key = (normalized_title, body[:160])
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            entries.append(
                ProtocolEntry(
                    title=title,
                    normalized_title=normalized_title,
                    body=body,
                    source_file=str(txt_path),
                )
            )

    return entries


def _extract_course_digests(
    library_root: Path,
    protocol_entries: list[ProtocolEntry],
) -> list[CourseDigestEntry]:
    entries: list[CourseDigestEntry] = []
    protocol_index: dict[str, list[ProtocolEntry]] = {}
    for protocol in protocol_entries:
        course_key = _course_key_from_path(Path(protocol.source_file))
        if course_key:
            protocol_index.setdefault(course_key, []).append(protocol)

    for manifest_path in sorted(library_root.rglob("course_manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        course_dir = manifest_path.parent
        sources_dir = course_dir / "sources"
        txt_paths = sorted(sources_dir.glob("*.txt"))
        themes = _extract_course_theme_candidates(txt_paths)
        course_protocols = [
            protocol.title
            for protocol in protocol_index.get(_course_key_from_path(course_dir), [])
        ]
        course_protocols = _dedupe_keep_order(course_protocols)[:10]

        entries.append(
            CourseDigestEntry(
                course_id=manifest["course_id"],
                course_name=manifest["course_name"],
                normalized_course_name=TeacherKnowledge._normalize_text(manifest["course_name"]),
                linea=manifest.get("linea", ""),
                tipo=manifest.get("tipo", ""),
                themes=themes[:12],
                protocols=course_protocols,
                source_count=len(manifest.get("sources", [])),
            )
        )

    return entries


def _extract_course_theme_candidates(txt_paths: list[Path]) -> list[str]:
    collected: list[str] = []
    prioritized_paths = sorted(txt_paths, key=_course_theme_path_priority)
    for txt_path in prioritized_paths[:8]:
        try:
            text = txt_path.read_text(encoding="utf-8", errors="ignore").replace("\f", "\n")
        except OSError:
            continue
        lines = [_clean_line(line) for line in text.splitlines()]

        for line in lines[:80]:
            if _looks_like_theme_bullet(line):
                collected.append(_normalize_theme_text(line))

        for line in lines:
            if _looks_like_pairs_heading(line):
                collected.append(_normalize_theme_text(line))
            if len(collected) >= 20:
                break
        if len(collected) >= 20:
            break

    deduped = _dedupe_keep_order([item for item in collected if item])[:15]
    if deduped:
        return deduped

    return _extract_course_intro_sentences(prioritized_paths)


def _course_key_from_path(path: Path) -> str:
    parts = path.parts
    if "processed_library" not in parts:
        return ""
    index = parts.index("processed_library")
    relevant = parts[index + 1 : index + 3]
    return "/".join(relevant)


def _looks_like_theme_bullet(line: str) -> bool:
    if not line:
        return False
    if not any(marker in line for marker in ("●", "•")):
        return False
    normalized = TeacherKnowledge._normalize_text(line)
    if any(
        fragment in normalized
        for fragment in [
            "preguntas",
            "cierre",
            "ponente",
            "modulo",
            "módulo",
            "no preguntar",
            "subconsciente es automata",
            "basado en nuestras creencias",
        ]
    ):
        return False
    return len(_clean_line(line)) >= 6


def _looks_like_pairs_heading(line: str) -> bool:
    normalized = TeacherKnowledge._normalize_text(line)
    return normalized.startswith("pares de ")


def _normalize_theme_text(text: str) -> str:
    cleaned = _clean_line(text)
    cleaned = cleaned.replace("●", "").replace("•", "").strip(" -")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        normalized = TeacherKnowledge._normalize_text(item)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item)
    return deduped


def _extract_course_intro_sentences(txt_paths: list[Path]) -> list[str]:
    for txt_path in txt_paths:
        try:
            text = txt_path.read_text(encoding="utf-8", errors="ignore").replace("\f", "\n")
        except OSError:
            continue
        if "transcripcion_completa" not in TeacherKnowledge._normalize_text(txt_path.name):
            continue

        lines = []
        for raw_line in text.splitlines():
            cleaned = _clean_line(raw_line)
            if not cleaned:
                continue
            normalized = TeacherKnowledge._normalize_text(cleaned)
            if any(
                fragment in normalized
                for fragment in [
                    "linea:",
                    "curso:",
                    "modulo:",
                    "fecha de proceso:",
                    "====",
                ]
            ):
                continue
            lines.append(cleaned)
            if len(lines) >= 40:
                break

        blob = " ".join(lines)
        parts = [
            segment.strip()
            for segment in re.split(r"(?<=[\.\!\?])\s+", blob)
            if len(segment.strip()) >= 50
        ]
        return parts[:6]

    return []


def _course_theme_path_priority(path: Path) -> tuple[int, str]:
    normalized = TeacherKnowledge._normalize_text(path.name)
    penalty = 0
    if "cierre" in normalized:
        penalty += 10
    if "transcripcion_completa" in normalized:
        penalty += 8
    if "index" in normalized:
        penalty += 6
    if "modulo" in normalized:
        penalty -= 2
    return (penalty, normalized)


CONCEPT_SEEDS: dict[str, dict[str, object]] = {
    "chakras": {
        "display": "chakras",
        "aliases": [
            "chakra",
            "chakras",
            "chakras primarios",
            "chakras secundarios",
            "chakras terciarios",
            "centros energeticos",
            "centros energéticos",
            "puentes energeticos",
        ],
    },
    "mente subconsciente": {
        "display": "mente subconsciente",
        "aliases": [
            "mente subconsciente",
            "subconsciente",
            "supraconsciente",
            "mente supraconsciente",
        ],
    },
    "psicosomatica": {
        "display": "psicosomática",
        "aliases": [
            "psicosomatica",
            "psicosomática",
            "biodescodificacion",
            "biodescodificación",
            "holopsicosomatica",
            "holopsicosomática",
        ],
    },
    "puentes energeticos": {
        "display": "puentes energéticos",
        "aliases": [
            "puentes energeticos",
            "puentes energéticos",
            "puente energetico",
            "puente energético",
            "normotonia",
            "normotonia",
        ],
    },
    "intencionalidad negativa": {
        "display": "intencionalidad negativa",
        "aliases": [
            "intencionalidad negativa",
            "intencionalidades negativas",
        ],
    },
    "maldiciones": {
        "display": "maldiciones",
        "aliases": ["maldicion", "maldición", "maldiciones"],
    },
    "mal de ojo": {
        "display": "mal de ojo",
        "aliases": ["mal de ojo"],
    },
    "larvas energeticas": {
        "display": "larvas energéticas",
        "aliases": ["larvas energeticas", "larvas energéticas", "larvas astrales"],
    },
    "proyecto sentido": {
        "display": "proyecto sentido",
        "aliases": ["proyecto sentido", "proyecto-sentido"],
    },
    "conflicto sistemico": {
        "display": "conflicto sistémico",
        "aliases": [
            "conflicto sistemico",
            "conflicto sistémico",
            "conflicto",
            "holograma",
        ],
    },
}


def _extract_concept_digests(library_root: Path) -> list[ConceptDigestEntry]:
    txt_paths = sorted(library_root.rglob("*.txt"))
    entries: list[ConceptDigestEntry] = []

    for seed_name, seed in CONCEPT_SEEDS.items():
        aliases = [TeacherKnowledge._normalize_text(alias) for alias in seed["aliases"]]
        snippets: list[str] = []
        source_files: list[str] = []

        for txt_path in txt_paths:
            try:
                text = txt_path.read_text(encoding="utf-8", errors="ignore").replace("\f", "\n")
            except OSError:
                continue

            concept_snippets = _extract_concept_snippets_from_text(text, aliases)
            if not concept_snippets:
                continue

            snippets.extend(concept_snippets[:6])
            source_files.append(str(txt_path))

        snippets = _dedupe_keep_order(snippets)
        if not snippets:
            continue

        summary = _build_concept_summary(seed_name, snippets)
        if not summary:
            continue

        entries.append(
            ConceptDigestEntry(
                concept_name=str(seed["display"]),
                normalized_concept_name=TeacherKnowledge._normalize_text(seed_name),
                aliases=aliases,
                summary=summary,
                bullet_points=snippets[:6],
                source_files=_dedupe_keep_order(source_files)[:8],
            )
        )

    return entries


def _extract_concept_snippets_from_text(text: str, aliases: list[str]) -> list[str]:
    snippets: list[str] = []
    lines = [_clean_line(line) for line in text.splitlines()]

    for index, line in enumerate(lines):
        if not line:
            continue
        normalized_line = TeacherKnowledge._normalize_text(line)
        if not any(alias in normalized_line for alias in aliases):
            continue
        if _looks_like_footer(line):
            continue
        if _looks_noisy_concept_line(line):
            continue

        snippet = line
        if len(snippet) < 60:
            tail_parts: list[str] = [snippet]
            for next_index in range(index + 1, min(index + 4, len(lines))):
                candidate = lines[next_index]
                if not candidate or _looks_like_footer(candidate):
                    continue
                if _looks_noisy_concept_line(candidate):
                    continue
                tail_parts.append(candidate)
                if len(" ".join(tail_parts)) >= 90:
                    break
            snippet = " ".join(tail_parts)

        snippet = re.sub(r"\s+", " ", snippet).strip(" -")
        if 50 <= len(snippet) <= 260 and not _looks_noisy_concept_line(snippet):
            snippets.append(snippet)

    return _dedupe_keep_order(snippets)


def _build_concept_summary(seed_name: str, snippets: list[str]) -> str:
    if seed_name == "chakras":
        return (
            "En esta biblioteca, los chakras se explican como centros de procesamiento y distribucion energetica. "
            "Los chakras primarios almacenan y procesan la energia, los secundarios la distribuyen, "
            "y en la practica se estudian junto con meridianos, puntos energeticos y puentes biomagneticos para restaurar la normotonia."
        )
    if seed_name == "mente subconsciente":
        return (
            "En el material, la mente subconsciente se presenta como la capa profunda que guarda informacion, "
            "sostiene programas y puede mantener conflictos, sintomas o incluso cargas energeticas hasta que se hagan conscientes y se reordenen."
        )
    if seed_name == "psicosomatica":
        return (
            "La psicosomatica se trabaja aqui como la relacion entre lo que la persona vive, siente y registra, "
            "y la manera en que eso se manifiesta despues en la conducta, la energia o el cuerpo."
        )
    if seed_name == "puentes energeticos":
        return (
            "Los puentes energeticos se explican como conexiones entre chakras o entre chakras y puntos energéticos, "
            "utilizadas para ayudar a restaurar la normotonia cuando un conflicto o una carga emocional ha dejado alterada la respuesta del cuerpo."
        )

    cleaned = [snippet for snippet in snippets if not _looks_noisy_concept_line(snippet)]
    if not cleaned:
        return ""

    top = cleaned[0]
    if top[-1] not in ".!?":
        top += "."
    return top


def _looks_noisy_concept_line(text: str) -> bool:
    normalized = TeacherKnowledge._normalize_text(text)
    if len(text) < 15:
        return True
    if sum(char.isdigit() for char in text) > 6:
        return True
    if any(
        fragment in normalized
        for fragment in [
            "alejandro lavin",
            "modulo",
            "preguntas",
            "gracias",
            "aplauso",
            "hotmail",
            "google meet",
            "instagram",
            "curso a mi me vale",
            "que pase la desgracia",
        ]
    ):
        return True
    if text.count("¿") >= 1 or text.count("?") >= 2:
        return True
    if text.count("...") >= 1:
        return True
    return False


@lru_cache
def get_teacher_knowledge() -> TeacherKnowledge:
    base_dir = Path(__file__).resolve().parent.parent
    library_root = base_dir / "data" / "processed_library"
    cache_path = base_dir / "data" / "teacher_knowledge_cache.json"
    manual_path = (
        base_dir
        / "data"
        / "processed_library"
        / "Salud"
        / "curso-holobiomagnetismo-parte-1"
        / "sources"
        / "HoloBiomagnetismo_Parte_1_(Bioenergética)_versión_2024_-_Alejandro_Lavín_.txt"
    )
    if cache_path.exists():
        try:
            cached = TeacherKnowledge.from_cache(cache_path)
            if cached.concept_count > 0:
                return cached
        except Exception:
            pass

    knowledge = TeacherKnowledge.from_library(library_root=library_root, manual_path=manual_path)
    try:
        knowledge.to_cache(cache_path)
    except Exception:
        pass
    return knowledge
