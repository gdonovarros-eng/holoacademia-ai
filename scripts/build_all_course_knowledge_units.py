from __future__ import annotations

import csv
import json
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROCESSED_LIBRARY = ROOT / "data" / "processed_library"
OUTPUT_ROOT = ROOT / "data" / "knowledge_units"
SKIP_EXISTING = {"course_holobiomagnetismo_2021"}

STOPWORDS = {
    "de",
    "del",
    "al",
    "y",
    "o",
    "en",
    "con",
    "sin",
    "por",
    "ejemplo",
    "antes",
    "despues",
    "después",
    "otro",
    "otra",
    "vez",
    "mas",
    "más",
    "para",
    "como",
    "esta",
    "este",
    "estos",
    "estas",
    "desde",
    "hasta",
    "sobre",
    "entre",
    "porque",
    "cuando",
    "donde",
    "luego",
    "manual",
    "curso",
    "modulo",
    "módulo",
    "parte",
    "diplomado",
    "taller",
    "alejandro",
    "lavin",
    "lavín",
    "clase",
    "salud",
    "mistica",
    "mística",
    "diplomados",
    "energetica",
    "energética",
    "bien",
    "pero",
    "ahora",
    "hacer",
    "hacia",
    "aqui",
    "aquí",
    "todos",
    "todo",
    "tambien",
    "también",
    "cuerpo",
    "gracias",
    "acuerdo",
    "energia",
    "energía",
    "sistema",
    "principios",
    "metodo",
    "método",
}

DOMAIN_PHRASES = [
    "medicina energética",
    "pruebas de energía",
    "bioretroalimentación",
    "meridianos",
    "r27",
    "timo",
    "chakras",
    "chakra",
    "aura",
    "triple calentador",
    "sistema inmune",
    "circuitos radiantes",
    "cinco elementos",
    "tapping",
    "wayne cook",
    "biomagnetismo",
    "holobiomagnetismo",
    "psicosomática",
    "biodescodificación",
    "genograma",
    "genogramas",
    "numerología",
    "numerhología",
    "medicina naturista",
    "flores de bach",
    "sales de schussler",
    "schüssler",
]

COMMON_NON_CONCEPT_TERMS = {
    "puedes",
    "pueden",
    "esto",
    "esta",
    "este",
    "estas",
    "estos",
    "vamos",
    "algo",
    "alguien",
    "cosa",
    "cosas",
    "forma",
    "manera",
    "momento",
    "parte",
    "puntos",
    "gracias",
    "nombre",
    "sistema",
    "persona",
    "personas",
    "cuerpo",
}

BANNED_CONCEPT_PHRASES = {
    "el triple",
    "las manos",
    "el meridiano",
    "la prueba",
    "el dolor",
    "las energias",
    "las energías",
    "de nuevo",
    "por ejemplo",
    "antes de",
    "otro lado",
    "vez mas",
    "vez más",
    "prueba de",
    "meridiano del",
    "del corazon",
    "del corazón",
    "del vaso",
}

THERAPEUTIC_KEYWORDS = (
    "paciente",
    "sintoma",
    "síntoma",
    "sintomas",
    "síntomas",
    "conflicto",
    "conflictologico",
    "emoc",
    "antecedent",
    "cronolog",
    "inicio",
    "caso",
    "consulta",
    "sesion",
    "sesión",
    "dolor",
    "historia",
    "evento",
    "ruptura",
    "cirugia",
    "cirugía",
    "pregunt",
    "observ",
    "rastre",
    "implicad",
    "territorio",
    "organo",
    "órgano",
    "biologico",
    "biológico",
)

CLINICAL_REASONING_MARKERS = (
    "paciente",
    "sintoma",
    "síntoma",
    "sintomas",
    "síntomas",
    "conflicto",
    "emoc",
    "antecedent",
    "historia",
    "organo",
    "órgano",
    "tejido",
    "dolor",
    "diagn",
    "consulta",
    "caso",
    "biologico",
    "biológico",
)

STRONG_CLINICAL_MARKERS = (
    "paciente",
    "sintoma",
    "síntoma",
    "sintomas",
    "síntomas",
    "conflicto",
    "emoc",
    "historia",
    "antecedent",
    "cronolog",
    "inicio",
    "consulta",
    "caso",
    "organo",
    "órgano",
    "tejido",
    "dolor",
    "diagn",
    "biologico",
    "biológico",
)

ABSTRACT_THERAPEUTIC_EXCLUSIONS = (
    "doble rendija",
    "electrones",
    "observador",
    "fisica cuantica",
    "física cuántica",
    "realidad es objetiva",
    "perceptibles por los cinco sentidos",
)

PROTOCOL_ACTION_TERMS = (
    "haz",
    "haga",
    "hacer",
    "pregunta",
    "preguntar",
    "identifica",
    "registra",
    "declara",
    "busca",
    "verifica",
    "coloca",
    "retira",
    "realiza",
    "aplica",
    "inhala",
    "exhala",
    "masajea",
    "toca",
    "sube",
    "baja",
    "explora",
    "anota",
    "observa",
    "cruza",
    "presiona",
    "junta",
    "levanta",
    "camina",
    "repite",
    "sedar",
    "seda",
    "fortalece",
    "limpia",
)

PROTOCOL_TITLE_HINTS = [
    ("r27", "Activación de puntos R27"),
    ("wayne cook", "Postura de Wayne Cook"),
    ("triple calentador", "Sedación del triple calentador"),
    ("limpieza del vaso", "Limpieza del vaso"),
    ("meridiano del estomago", "Conexión a tierra por meridiano del estómago"),
    ("meridiano del estómago", "Conexión a tierra por meridiano del estómago"),
    ("rastreo conflictologico", "Rastreo conflictológico"),
    ("rastreo conflictológico", "Rastreo conflictológico"),
    ("transgen", "Protocolo de solución transgeneracional"),
    ("eft", "Aplicación de EFT"),
]

GENERIC_PROTOCOL_TITLES = {
    "transcripcion modulo",
    "transcripción módulo",
    "transcripcion",
    "transcripción",
    "protocolo detectado",
}

DEFINITION_CUES = (
    " se llama ",
    " es un ",
    " es una ",
    " son el ",
    " son los ",
    " consiste en ",
    " se refiere a ",
    " corresponde a ",
    " significa ",
    " sirve para ",
)


@dataclass
class SourceFile:
    source_id: str
    tipo: str
    original_name: str
    source_path: str
    local_path: Path | None


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_value).strip("_").lower()
    return cleaned


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    stripped = stripped.lower().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", stripped).strip()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compact(text: str, limit: int = 500) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[:limit]
    for marker in (". ", "; ", ": "):
        idx = cut.rfind(marker)
        if idx >= int(limit * 0.6):
            return cut[: idx + 1].strip()
    return cut.rstrip(" ,;:") + "…"


def split_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[\.\?\!])\s+|\n+", text or "")
    sentences = []
    for sentence in raw:
        cleaned = " ".join(sentence.split()).strip(" -•\t")
        if len(cleaned) < 40:
            continue
        sentences.append(cleaned)
    return sentences


def sentence_fragments(text: str) -> list[str]:
    raw = re.split(r"(?<=[\.\?\!])\s+|\n+", text or "")
    return [" ".join(fragment.split()).strip(" -•\t") for fragment in raw if fragment.strip()]


def tokenize_text(text: str) -> list[str]:
    return [normalize_text(token) for token in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+", text or "")]


def canonicalize_term(term: str) -> str:
    candidate = " ".join(str(term).split()).strip(" -:_")
    candidate = re.sub(r"^(el|la|los|las|un|una)\s+", "", candidate, flags=re.IGNORECASE)
    return " ".join(candidate.split()).strip()


def term_regex(term: str) -> re.Pattern[str]:
    normalized = normalize_text(term)
    escaped = re.escape(normalized).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)")


def acceptable_single_token(token: str) -> bool:
    lowered = normalize_text(token)
    if not lowered or lowered in STOPWORDS or lowered in COMMON_NON_CONCEPT_TERMS:
        return False
    if lowered in {"r27", "eft", "pnl", "timo", "aura", "chakra", "chakras", "meridianos"}:
        return True
    if len(lowered) < 5:
        return False
    suffixes = (
        "cion",
        "sion",
        "ismo",
        "logia",
        "terapia",
        "patia",
        "algia",
        "itis",
        "osis",
        "emia",
        "geno",
        "gena",
        "miento",
    )
    return any(lowered.endswith(suffix) for suffix in suffixes)


def is_good_concept_term(term: str) -> bool:
    normalized = normalize_text(canonicalize_term(term))
    if not normalized:
        return False
    if normalized in {normalize_text(item) for item in BANNED_CONCEPT_PHRASES}:
        return False
    if normalized in STOPWORDS or normalized in COMMON_NON_CONCEPT_TERMS:
        return False
    parts = [part for part in re.findall(r"[a-z0-9]+", normalized) if part]
    if not parts:
        return False
    edge_banned = STOPWORDS | COMMON_NON_CONCEPT_TERMS
    if len(parts) == 1:
        return acceptable_single_token(parts[0])
    if len(parts) > 6:
        return False
    if parts[0] in edge_banned or parts[-1] in edge_banned:
        return False
    if sum(1 for part in parts if part in STOPWORDS or part in COMMON_NON_CONCEPT_TERMS) >= len(parts) - 1:
        return False
    return True


def dedupe_terms(terms: list[str], limit: int = 20) -> list[str]:
    cleaned = []
    seen = set()
    for term in terms:
        candidate = canonicalize_term(term)
        normalized = normalize_text(candidate)
        if not candidate or normalized in seen:
            continue
        if not is_good_concept_term(candidate):
            continue
        seen.add(normalized)
        cleaned.append(candidate)
        if len(cleaned) >= limit:
            break
    return cleaned


def extract_candidate_phrases_from_texts(texts: list[str], limit: int = 20) -> list[str]:
    phrase_frequencies: dict[str, int] = {}
    single_frequencies: dict[str, int] = {}
    for text in texts:
        tokens = [token for token in tokenize_text(text) if token]
        filtered = [token for token in tokens if token not in STOPWORDS and token not in COMMON_NON_CONCEPT_TERMS]
        for size in (2, 3, 4):
            for idx in range(0, len(filtered) - size + 1):
                phrase_tokens = filtered[idx : idx + size]
                if any(token.isdigit() for token in phrase_tokens):
                    continue
                phrase = " ".join(phrase_tokens)
                if len(phrase) < 8:
                    continue
                phrase_frequencies[phrase] = phrase_frequencies.get(phrase, 0) + 1
        for token in filtered:
            if acceptable_single_token(token):
                single_frequencies[token] = single_frequencies.get(token, 0) + 1
    ranked_phrases = [phrase.title() for phrase, _ in sorted(phrase_frequencies.items(), key=lambda item: (-item[1], item[0]))]
    ranked_singles = [token.title() for token, _ in sorted(single_frequencies.items(), key=lambda item: (-item[1], item[0]))]
    return dedupe_terms(ranked_phrases + ranked_singles, limit=limit)


def likely_heading(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < 4 or len(stripped) > 90:
        return False
    if re.fullmatch(r"[\d\W_]+", stripped):
        return False
    if stripped.lower().startswith(("http", "www")):
        return False
    if stripped.count(",") > 4:
        return False
    letters = sum(ch.isalpha() for ch in stripped)
    if letters < 3:
        return False
    lowered = normalize_text(stripped)
    if "alejandro lavin" in lowered:
        return False
    if re.fullmatch(r"(modulo|módulo)\s+\d+", lowered):
        return False
    generic_bits = {"curso", "diplomado", "taller", "modulo", "módulo", "metodo", "método"}
    lowered_tokens = [token for token in re.findall(r"[a-z0-9]+", lowered) if token]
    if lowered_tokens and all(token in generic_bits for token in lowered_tokens):
        return False
    words = stripped.split()
    if len(words) > 10:
        return False
    is_upper = stripped == stripped.upper()
    title_ratio = sum(1 for w in words if w[:1].isupper()) / max(len(words), 1)
    if is_upper or title_ratio >= 0.7:
        return True
    return False


def clean_block_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.fullmatch(r"[=\-]{4,}", line):
            continue
        if line.startswith(("BLOQUE:", "LÍNEA:", "CURSO:", "MÓDULO:", "FECHA DE PROCESO:")):
            continue
        if re.fullmatch(r"\d+", line):
            continue
        lines.append(line)
    merged = "\n".join(lines)
    merged = re.sub(r"[ \t]+", " ", merged)
    merged = re.sub(r"\n{3,}", "\n\n", merged)
    return merged.strip()


def split_transcript_modules(text: str) -> list[dict]:
    patterns = [
        re.compile(
            r"\n=+\nBLOQUE: .*?\nLÍNEA: .*?\nCURSO: .*?\nMÓDULO: ([^\n]+)\nFECHA DE PROCESO: ([^\n]+)\n=+\n",
            flags=re.DOTALL,
        ),
        re.compile(
            r"\n=+\nLÍNEA: .*?\nCURSO: .*?\nMÓDULO: ([^\n]+)\nFECHA DE PROCESO: ([^\n]+)\n=+\n",
            flags=re.DOTALL,
        ),
    ]
    matches = []
    pattern_used = None
    for pattern in patterns:
        found = list(pattern.finditer(text))
        if found:
            matches = found
            pattern_used = pattern
            break
    if not matches or pattern_used is None:
        return []

    modules = []
    for idx, match in enumerate(matches):
        raw_number = match.group(1).strip()
        try:
            module_number = int(re.sub(r"[^\d]", "", raw_number))
        except ValueError:
            module_number = idx + 1
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = clean_block_text(text[start:end])
        modules.append(
            {
                "module_number": module_number,
                "fecha_proceso": match.group(2).strip(),
                "raw_text": body,
            }
        )
    return modules


def extractive_summary(text: str, keywords: list[str], max_sentences: int = 5) -> list[str]:
    sentences = split_sentences(text)
    if not sentences:
        return []
    ranked = []
    normalized_keywords = [normalize_text(keyword) for keyword in keywords if keyword]
    for idx, sentence in enumerate(sentences[:120]):
        lowered = normalize_text(sentence)
        score = 0
        for keyword in normalized_keywords:
            if keyword and keyword in lowered:
                score += 4
        if any(term in lowered for term in ("protocolo", "rastreo", "terapia", "síntoma", "sintoma", "energ", "paciente", "emoc")):
            score += 2
        if 60 <= len(sentence) <= 220:
            score += 1
        ranked.append((score, idx, sentence))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    picked = sorted(ranked[:max_sentences], key=lambda item: item[1])
    return [item[2] for item in picked]


def parse_index_text(index_text: str) -> list[int]:
    rows = []
    cleaned = index_text.strip()
    if not cleaned:
        return rows
    try:
        reader = csv.DictReader(cleaned.splitlines())
        for row in reader:
            modulo = row.get("modulo")
            if modulo and modulo.isdigit():
                rows.append(int(modulo))
    except Exception:
        pass
    return sorted(set(rows))


def load_sources(course_dir: Path, manifest: dict) -> list[SourceFile]:
    sources = []
    for idx, source in enumerate(manifest.get("sources", []), start=1):
        text_path = source.get("text_path")
        local_path = Path(text_path) if text_path else None
        if local_path and not local_path.exists():
            local_path = None
        sources.append(
            SourceFile(
                source_id=source.get("source_id", f"{manifest['course_id']}-source-{idx:03d}"),
                tipo=source.get("tipo", "manual"),
                original_name=source.get("archivo_original", local_path.name if local_path else f"source_{idx}"),
                source_path=source.get("source_path", ""),
                local_path=local_path,
            )
        )
    if sources:
        return sources

    fallback_sources = []
    source_dir = course_dir / "sources"
    for idx, path in enumerate(sorted(source_dir.glob("*")), start=1):
        if not path.is_file():
            continue
        tipo = "transcripcion" if "transcripcion" in path.name.lower() else "indice" if "index" in path.name.lower() else "manual"
        fallback_sources.append(
            SourceFile(
                source_id=f"{manifest['course_id']}-source-{idx:03d}",
                tipo=tipo,
                original_name=path.name,
                source_path=str(path),
                local_path=path,
            )
        )
    return fallback_sources


def derive_output_slug(course_name: str) -> str:
    stripped = re.sub(r"^(Curso|Diplomado|Taller)\s+", "", course_name, flags=re.IGNORECASE).strip()
    return f"course_{slugify(stripped)}"


def copy_sources(out_dir: Path, sources: list[SourceFile], course_manifest: Path) -> dict:
    source_dir = out_dir / "01_sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    copied_files = []
    external_refs = []
    for source in sources:
        if source.local_path and source.local_path.exists():
            target = source_dir / source.local_path.name
            shutil.copy2(source.local_path, target)
            copied_files.append(target.name)
        external_refs.append(
            {
                "source_id": source.source_id,
                "tipo": source.tipo,
                "archivo_original": source.original_name,
                "source_path": source.source_path,
                "local_text_available": bool(source.local_path and source.local_path.exists()),
            }
        )
    shutil.copy2(course_manifest, source_dir / "course_manifest_source.json")
    write_json(source_dir / "external_source_refs.json", external_refs)
    return {"copied_files": copied_files, "external_refs": external_refs}


def collect_manual_headings(manual_texts: list[str]) -> list[str]:
    headings = []
    seen = set()
    for text in manual_texts:
        for line in text.splitlines():
            if likely_heading(line):
                normalized = normalize_text(line)
                if normalized in seen:
                    continue
                seen.add(normalized)
                headings.append(line.strip())
                if len(headings) >= 25:
                    return headings
    return headings


def extract_terms_from_headings(headings: list[str], file_names: list[str]) -> list[str]:
    candidates = []
    for heading in headings:
        cleaned = re.sub(r"^\d+\s*", "", heading).strip(" -:_")
        if cleaned and is_good_concept_term(cleaned) and normalize_text(cleaned) not in {normalize_text(item) for item in candidates}:
            candidates.append(cleaned)
    for name in file_names:
        stem = Path(name).stem.replace("_", " ").replace("-", " ")
        stem = re.sub(r"\s+", " ", stem).strip()
        if len(stem) < 6:
            continue
        if any(token in normalize_text(stem) for token in ("manual", "transcripcion", "index", "modulo", "módulo")):
            continue
        if is_good_concept_term(stem) and normalize_text(stem) not in {normalize_text(item) for item in candidates}:
            candidates.append(stem)
    return dedupe_terms(candidates, limit=20)


def extract_fallback_terms_from_texts(texts: list[str]) -> list[str]:
    prioritized = []
    joined = "\n".join(texts)
    lowered_joined = normalize_text(joined)
    for phrase in DOMAIN_PHRASES:
        normalized_phrase = normalize_text(phrase)
        if normalized_phrase in lowered_joined and phrase.title() not in prioritized:
            prioritized.append(phrase.title())
    candidates = extract_candidate_phrases_from_texts(texts, limit=30)
    return dedupe_terms(prioritized + candidates, limit=20)


def find_snippet(term: str, texts: list[tuple[str, str]]) -> str:
    pattern = term_regex(term)
    for label, text in texts:
        lowered = normalize_text(text)
        match = pattern.search(lowered)
        if not match:
            continue
        idx = match.start()
        approx_start = max(0, idx - 250)
        approx_end = min(len(text), idx + 700)
        snippet = text[approx_start:approx_end]
        return compact(snippet, 650)
    return ""


def find_term_context(term: str, texts: list[tuple[str, str]]) -> tuple[str, list[str]]:
    pattern = term_regex(term)
    best_label = ""
    best_sentences: list[str] = []
    best_score = -1
    for label, text in texts:
        sentences = split_sentences(text)
        matched = [sentence for sentence in sentences if pattern.search(normalize_text(sentence))]
        if not matched:
            continue
        score = len(matched)
        if score > best_score:
            best_score = score
            best_label = label
            best_sentences = matched[:4]
    return best_label, best_sentences


def derive_definition_from_context(term: str, sentences: list[str], fallback: str) -> str:
    lowered_term = normalize_text(term)
    for sentence in sentences:
        lowered = normalize_text(sentence)
        if lowered_term in lowered and any(cue in lowered for cue in DEFINITION_CUES):
            return compact(sentence, 220)
    for sentence in sentences:
        lowered = normalize_text(sentence)
        if lowered.startswith(lowered_term):
            return compact(sentence, 220)
    if sentences:
        return compact(sentences[0], 220)
    return compact(fallback, 220)


def infer_module_for_term(term: str, modules: list[dict]) -> str:
    pattern = term_regex(term)
    if not modules:
        return "Tema general del curso"
    ranked = []
    for module in modules:
        raw_text = module.get("raw_text", "")
        count = len(pattern.findall(normalize_text(raw_text)))
        if count > 0:
            ranked.append((count, module["module_number"]))
    if ranked:
        ranked.sort(reverse=True)
        return f"Módulo {ranked[0][1]}"
    return "Tema general del curso"


def build_concepts(
    course_name: str,
    headings: list[str],
    file_names: list[str],
    source_texts: list[tuple[str, str]],
    modules: list[dict],
) -> list[dict]:
    terms = extract_terms_from_headings(headings, file_names)
    if len(terms) < 6:
        fallback_terms = extract_fallback_terms_from_texts([text for _, text in source_texts])
        for term in fallback_terms:
            if normalize_text(term) not in {normalize_text(item) for item in terms}:
                terms.append(canonicalize_term(term).title())
            if len(terms) >= 20:
                break
    terms = dedupe_terms(terms, limit=20)
    concepts = []
    for idx, term in enumerate(terms, start=1):
        snippet = find_snippet(term, source_texts)
        if not snippet:
            continue
        source_label, context_sentences = find_term_context(term, source_texts)
        explanation_sentences = context_sentences[:3] if context_sentences else split_sentences(snippet)[:3]
        definition = derive_definition_from_context(term, explanation_sentences, snippet)
        extended = " ".join(explanation_sentences) if explanation_sentences else snippet
        concepts.append(
            {
                "id": f"concept_{idx:03d}",
                "termino": term,
                "aliases": [],
                "definicion": compact(definition, 220),
                "explicacion_simple": compact(extended, 300),
                "explicacion_extendida": compact(extended, 650),
                "modulo_o_tema": infer_module_for_term(term, modules),
                "fuente_principal": source_label or (source_texts[0][0] if source_texts else course_name),
                "fuente_secundaria": source_texts[1][0] if len(source_texts) > 1 else "",
            }
        )
    return concepts


def build_glossary(concepts: list[dict]) -> list[dict]:
    return [
        {
            "termino": concept["termino"],
            "definicion_corta": compact(concept["definicion"], 160),
        }
        for concept in concepts
    ]


def build_faq(concepts: list[dict], module_summaries: list[dict]) -> list[dict]:
    faq = []
    for concept in concepts[:8]:
        faq.append(
            {
                "pregunta": f"¿Qué es {concept['termino']}?",
                "respuesta_breve": compact(concept["explicacion_simple"], 220),
                "fuente": concept["fuente_principal"],
            }
        )
    for module in module_summaries[:4]:
        faq.append(
            {
                "pregunta": f"¿Qué se trabaja en el módulo {module['module_number']}?",
                "respuesta_breve": compact(" ".join(module["summary_points"]), 220),
                "fuente": module["fuente"],
            }
        )
    return faq[:12]


def build_module_summaries(modules: list[dict], headings: list[str]) -> list[dict]:
    keyword_seed = headings[:8]
    summaries = []
    for module in modules:
        summary_points = extractive_summary(module["raw_text"], keyword_seed, max_sentences=5)
        summaries.append(
            {
                "module_number": module["module_number"],
                "title": f"Módulo {module['module_number']}",
                "summary_points": summary_points,
                "summary_text": " ".join(summary_points),
                "fuente": f"transcripción módulo {module['module_number']}",
            }
        )
    return summaries


def build_overview(manifest: dict, module_numbers: list[int], headings: list[str], concepts: list[dict], modules: list[dict]) -> dict:
    all_keywords = []
    for heading in headings:
        normalized = normalize_text(heading)
        tokens = [token for token in re.findall(r"[a-z0-9]+", normalized) if token]
        if not tokens:
            continue
        if len(tokens) == 1 and tokens[0] in STOPWORDS:
            continue
        if len(tokens) == 1:
            continue
        all_keywords.append(heading)
        if len(all_keywords) >= 10:
            break
    if not all_keywords:
        for concept in concepts:
            normalized = normalize_text(concept["termino"])
            if normalized in STOPWORDS:
                continue
            all_keywords.append(concept["termino"])
            if len(all_keywords) >= 10:
                break
    return {
        "course_id": manifest["course_id"],
        "course_name": manifest["course_name"],
        "linea": manifest["linea"],
        "tipo": manifest["tipo"],
        "description": (
            f"{manifest['course_name']} organizado como unidad de conocimiento para asistentes académicos, terapéuticos y guías de protocolos. "
            "La descripción se construyó automáticamente a partir de transcripciones, manuales e índices disponibles."
        ),
        "main_axes": all_keywords[:8],
        "detected_modules": module_numbers,
        "notes": [
            "Salida generada con extracción heurística automática.",
            "Conviene revisar manualmente conceptos, protocolos y ambigüedades antes de usarlo como versión final de alta precisión.",
        ],
        "module_preview": [
            {
                "module_number": module["module_number"],
                "summary_text": compact(" ".join(module.get("summary_points", [])), 240),
            }
            for module in modules[:12]
        ],
    }


def unique_entries(items: list[dict], key_fields: tuple[str, ...]) -> list[dict]:
    seen = set()
    result = []
    for item in items:
        key = tuple(item.get(field, "") for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = normalize_text(text)
    return any(term in lowered for term in terms)


def has_clinical_signal(text: str) -> bool:
    lowered = normalize_text(text)
    if any(term in lowered for term in ABSTRACT_THERAPEUTIC_EXCLUSIONS) and not any(
        marker in lowered for marker in STRONG_CLINICAL_MARKERS
    ):
        return False
    return any(marker in lowered for marker in STRONG_CLINICAL_MARKERS)


def collect_relevant_sentences(texts: list[tuple[str, str]], include_terms: tuple[str, ...], max_items: int = 20) -> list[dict]:
    results = []
    for source_label, text in texts:
        for sentence in split_sentences(text):
            lowered = normalize_text(sentence)
            if any(term in lowered for term in include_terms):
                results.append({"source": source_label, "sentence": compact(sentence, 320)})
            if len(results) >= max_items:
                return results
    return results


def build_intake_questions(texts: list[tuple[str, str]]) -> list[dict]:
    questions = []
    idx = 0
    for source_label, text in texts:
        for sentence in sentence_fragments(text):
            lowered = normalize_text(sentence)
            if not contains_any(sentence, ("pregunt", "desde cuando", "desde cuándo", "inicio", "antecedent", "sintoma", "síntoma", "emocion", "emoción")):
                continue
            if "?" in sentence:
                prompt = compact(sentence, 220)
            elif "pregunt" in lowered:
                prompt = compact(sentence, 220)
            elif "desde cuando" in lowered or "desde cuándo" in lowered:
                prompt = "¿Desde cuándo comenzó o se hizo evidente este cuadro?"
            elif "antecedent" in lowered:
                prompt = "¿Qué antecedentes relevantes conviene explorar antes de interpretar el caso?"
            elif "inicio" in lowered or "evento" in lowered:
                prompt = "¿Con qué evento o momento de inicio se relaciona el síntoma o conflicto?"
            else:
                continue
            idx += 1
            questions.append(
                {
                    "id": f"intake_{idx:03d}",
                    "pregunta": prompt,
                    "para_que_sirve": "Pregunta inferida directamente del material para orientar entrevista, cronología o rastreo.",
                    "fuente": source_label,
                }
            )
            if len(questions) >= 18:
                return unique_entries(questions, ("pregunta",))
    return unique_entries(questions, ("pregunta",))


def build_reasoning_patterns(texts: list[tuple[str, str]]) -> list[dict]:
    patterns = []
    idx = 0
    for source_label, text in texts:
        for sentence in split_sentences(text):
            lowered = normalize_text(sentence)
            if not contains_any(sentence, THERAPEUTIC_KEYWORDS):
                continue
            if not has_clinical_signal(sentence):
                continue
            if not any(term in lowered for term in ("si ", "si hay", "cuando", "consider", "indica", "orienta", "relacion", "asocia", "cronolog", "inicio")):
                continue
            idx += 1
            observe = "Observar síntoma, cronología, conflicto asociado y contexto del caso."
            if "cronolog" in lowered or "inicio" in lowered:
                observe = "Observar especialmente el inicio del cuadro y su relación temporal con eventos relevantes."
            elif "emoc" in lowered:
                observe = "Observar la emoción asociada y el contexto en que se activó."
            elif "territorio" in lowered:
                observe = "Observar la relación con territorio, vínculos o amenazas percibidas."
            patterns.append(
                {
                    "id": f"pattern_{idx:03d}",
                    "si_aparece": compact(sentence, 200),
                    "observar": observe,
                    "considerar": compact(sentence, 260),
                    "source": source_label,
                }
            )
            if len(patterns) >= 18:
                return unique_entries(patterns[:15], ("si_aparece",))
    return unique_entries(patterns[:15], ("si_aparece",))


def build_interpretation_guides(texts: list[tuple[str, str]]) -> list[dict]:
    guides = []
    idx = 0
    for source_label, text in texts:
        for sentence in split_sentences(text):
            lowered = normalize_text(sentence)
            if not contains_any(sentence, THERAPEUTIC_KEYWORDS):
                continue
            if not has_clinical_signal(sentence):
                continue
            if not any(term in lowered for term in ("significa", "se interpreta", "indica", "se asocia", "corresponde", "relaciona")):
                continue
            idx += 1
            guides.append(
                {
                    "id": f"guide_{idx:03d}",
                    "hallazgo_o_situacion": compact(sentence, 180),
                    "guia_de_interpretacion": compact(sentence, 260),
                    "limite": "Lectura extraída automáticamente; conviene validar contexto completo en la fuente.",
                    "fuente": source_label,
                }
            )
            if len(guides) >= 12:
                return unique_entries(guides[:12], ("hallazgo_o_situacion",))
    return unique_entries(guides[:12], ("hallazgo_o_situacion",))


def build_observations(texts: list[tuple[str, str]]) -> list[dict]:
    raw = collect_relevant_sentences(
        texts,
        ("observ", "explor", "síntoma", "sintoma", "antecedent", "cronolog", "emoc"),
        max_items=18,
    )
    observations = []
    for idx, item in enumerate(raw, start=1):
        observations.append(
            {
                "id": f"obs_{idx:03d}",
                "observacion": compact(item["sentence"], 220),
                "uso_terapeutico": "Apoya entrevista, análisis de caso o seguimiento clínico.",
                "fuente": item["source"],
            }
        )
    return unique_entries(observations[:15], ("observacion",))


def build_warnings(texts: list[tuple[str, str]]) -> list[dict]:
    raw = collect_relevant_sentences(
        texts,
        ("advert", "consent", "no ", "evitar", "marcapasos", "embarazo", "control", "urgencia"),
        max_items=20,
    )
    warnings = []
    for idx, item in enumerate(raw, start=1):
        lowered = normalize_text(item["sentence"])
        level = "revisar"
        if any(term in lowered for term in ("urgencia", "marcapasos", "embarazo", "shock", "anafil", "asma")):
            level = "alto"
        warnings.append(
            {
                "id": f"warning_{idx:03d}",
                "warning": compact(item["sentence"], 220),
                "nivel": level,
                "fuente": item["source"],
            }
        )
    return unique_entries(warnings[:15], ("warning",))


def imperative_lines(text: str) -> list[str]:
    steps = []
    seen = set()
    candidates = list(text.splitlines()) + sentence_fragments(text)
    for raw_line in candidates:
        line = " ".join(raw_line.split()).strip(" -•\t")
        if len(line) < 12 or len(line) > 180:
            continue
        lowered = normalize_text(line)
        if re.match(r"^\d+[\.\)]", line):
            if lowered not in seen:
                seen.add(lowered)
                steps.append(line)
            continue
        if lowered.startswith(("si -", "si –", "no -", "no –", "ms:")) or any(lowered.startswith(verb) for verb in PROTOCOL_ACTION_TERMS):
            if lowered not in seen:
                seen.add(lowered)
                steps.append(line)
    return steps


def clean_protocol_label(label: str) -> str:
    cleaned = Path(label).stem.replace("_", " ").replace("-", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\balejandro\s+lavin\b", "", normalize_text(cleaned), flags=0)
    return " ".join(cleaned.split()).strip().title()


def detect_protocol_title(label: str, text: str) -> str:
    lowered = normalize_text(text)
    for hint, title in PROTOCOL_TITLE_HINTS:
        if hint in lowered or hint in normalize_text(label):
            return title
    for line in text.splitlines()[:40]:
        candidate = " ".join(line.split()).strip(" -•\t")
        normalized = normalize_text(candidate)
        if not candidate:
            continue
        if "alejandro lavin" in normalized:
            continue
        if likely_heading(candidate) and len(candidate.split()) <= 10 and any(
            marker in normalized
            for marker in ("protocolo", "rastreo", "solucion", "solución", "sedacion", "sedación", "activacion", "activación", "ejercicio", "tapping", "cook", "limpieza")
        ):
            return candidate.title()
    if any(term in normalize_text(label) for term in ("protocolo", "protocolos", "rastreo", "rutina", "ejercicio")):
        return clean_protocol_label(label) or "Protocolo detectado"
    first_step = imperative_lines(text)
    if first_step:
        action = compact(re.sub(r"^\d+[\.\)]\s*", "", first_step[0]), 80)
        if len(action.split()) >= 3:
            return f"Secuencia: {action}"
    return "Protocolo detectado"


def excerpt_around_hint(sentences: list[str], start_index: int, current_hint: str) -> str:
    window = []
    other_hints = [hint for hint, _ in PROTOCOL_TITLE_HINTS if hint != current_hint]
    for sentence in sentences[start_index : min(len(sentences), start_index + 8)]:
        lowered = normalize_text(sentence)
        if window and any(other_hint in lowered for other_hint in other_hints):
            break
        window.append(sentence)
        if len(imperative_lines(" ".join(window))) >= 6:
            break
    return " ".join(window)


def find_protocol_trigger(text: str) -> str:
    for sentence in split_sentences(text):
        lowered = normalize_text(sentence)
        if any(term in lowered for term in ("cuando", "si ", "si hay", "en caso", "si estas", "si estás", "ante ")) and any(
            keyword in lowered for keyword in ("estres", "estrés", "dolor", "cans", "agot", "shock", "sintoma", "síntoma", "desconect", "preocup", "corazon", "corazón")
        ):
            return compact(sentence, 220)
    for sentence in split_sentences(text):
        lowered = normalize_text(sentence)
        if any(term in lowered for term in ("para ", "ayuda", "sirve", "te ayudara", "te ayudará")) and any(
            keyword in lowered for keyword in ("conect", "respira", "masaje", "tapping", "triple calentador", "r27", "vaso")
        ):
            return compact(sentence, 220)
    return "Usar cuando el material fuente indique esta secuencia o ejercicio."


def protocol_candidates_from_modules(modules: list[dict]) -> list[tuple[str, str, float]]:
    candidates = []
    for module in modules:
        raw_text = module.get("raw_text", "")
        if not raw_text:
            continue
        lowered = normalize_text(raw_text)
        sentence_list = split_sentences(raw_text)
        added = False
        for hint, title in PROTOCOL_TITLE_HINTS:
            if hint not in lowered:
                continue
            for index, sentence in enumerate(sentence_list):
                if hint in normalize_text(sentence):
                    excerpt = excerpt_around_hint(sentence_list, max(0, index - 1), hint)
                    if len(imperative_lines(excerpt)) >= 3:
                        candidates.append((title, excerpt, 0.62))
                        added = True
                    break
        if added:
            continue
        steps = imperative_lines(raw_text)
        if len(steps) >= 4 and any(term in lowered for term in ("ejercicio", "rutina", "rastreo", "tapping", "masajea", "respira", "sedar", "seda")):
            candidates.append((f"Transcripción módulo {module['module_number']}", raw_text, 0.56))
    return candidates


def build_protocol_steps(step_candidates: list[str]) -> list[dict]:
    steps = []
    seen = set()
    for step_index, line in enumerate(step_candidates, start=1):
        instruction = compact(re.sub(r"^\d+[\.\)]\s*", "", line), 180)
        normalized = normalize_text(instruction)
        if normalized in seen:
            continue
        seen.add(normalized)
        steps.append(
            {
                "orden": len(steps) + 1,
                "titulo": f"Paso {len(steps) + 1}",
                "instruccion": instruction,
                "objetivo_del_paso": "Ejecutar la acción operacional descrita en la fuente.",
                "que_observar": "Respuesta del paciente, continuidad de la secuencia y señales relevantes del caso.",
                "que_registrar": "Resultado del paso y observaciones relevantes.",
                "notas": "Paso extraído automáticamente.",
            }
        )
        if len(steps) >= 10:
            break
    return steps


def anchored_protocol_steps(title: str, step_candidates: list[str]) -> list[str]:
    lowered_title = normalize_text(title)
    anchors = []
    for hint, protocol_title in PROTOCOL_TITLE_HINTS:
        if normalize_text(protocol_title) == lowered_title:
            anchors.append(hint)
    if "r27" in lowered_title:
        anchors.append("r27")
    if "triple calentador" in lowered_title:
        anchors.append("triple calentador")
    if "wayne cook" in lowered_title:
        anchors.extend(["wayne cook", "cruza", "sienes"])
    if "vaso" in lowered_title:
        anchors.append("vaso")
    if "eft" in lowered_title:
        anchors.extend(["tapping", "eft"])
    if not anchors:
        return step_candidates
    for idx, line in enumerate(step_candidates):
        lowered = normalize_text(line)
        if any(anchor in lowered for anchor in anchors):
            return step_candidates[idx:]
    return step_candidates


def build_protocols(protocol_sources: list[tuple[str, str]], modules: list[dict]) -> list[dict]:
    protocols = []
    candidates = [(label, text, 0.78) for label, text in protocol_sources]
    candidates.extend(protocol_candidates_from_modules(modules))
    seen_names = set()
    for idx, (label, text, confidence) in enumerate(candidates, start=1):
        steps_raw = imperative_lines(text)
        if len(steps_raw) < 3:
            continue
        title = detect_protocol_title(label, text)
        normalized_title = normalize_text(title)
        if (
            normalized_title in GENERIC_PROTOCOL_TITLES
            or normalized_title.startswith("transcripcion modulo")
            or normalized_title.startswith("transcripción módulo")
        ) and confidence < 0.7:
            continue
        if normalized_title in seen_names:
            continue
        seen_names.add(normalized_title)
        description_lines = extractive_summary(text, [title, "protocolo", "rutina", "rastreo", "ejercicio"], max_sentences=4)
        steps = build_protocol_steps(anchored_protocol_steps(title, steps_raw))
        if not steps:
            continue
        protocols.append(
            {
                "id": f"protocol_{idx:03d}",
                "nombre": title,
                "objetivo": f"Ejecutar la secuencia operativa asociada a {title.lower()}.",
                "descripcion": " ".join(description_lines) if description_lines else f"Protocolo extraído desde {label}.",
                "cuando_usarlo": [find_protocol_trigger(text)],
                "cuando_no_usarlo_si_aplica": ["No se detectaron exclusiones explícitas suficientemente claras en la extracción automática."],
                "prerequisitos": ["Revisar la fuente original antes de usar clínicamente.", "Confirmar que el contexto del caso corresponde al procedimiento."],
                "pasos": steps,
                "que_registrar": ["Pasos realizados", "respuesta observada", "notas de sesión"],
                "observaciones": ["Protocolo detectado heurísticamente a partir de manuales, guías o secuencias docentes en transcripción."],
                "advertencias": ["Validar contra la fuente original antes de integrarlo en operación clínica final."],
                "fuente": [label],
                "confianza_extraccion": confidence,
            }
        )
    return protocols


def build_clean_manual(manual_sources: list[tuple[str, str]], headings: list[str]) -> str:
    lines = [
        "DOCUMENTO: manual_extracted.txt",
        "",
        "Compilación ordenada de fuentes manuales, guías y protocolos en texto plano.",
        "",
        "TEMAS Y ENCABEZADOS DETECTADOS",
    ]
    for heading in headings[:20]:
        lines.append(f"- {heading}")
    lines.append("")
    for label, text in manual_sources:
        lines.append(label.upper())
        summary = extractive_summary(text, headings[:8], max_sentences=5)
        for bullet in summary:
            lines.append(f"- {bullet}")
        lines.append("")
    return "\n".join(lines)


def build_clean_transcript_text(modules: list[dict]) -> str:
    if not modules:
        return ""
    lines = [
        "DOCUMENTO: clean_transcript.txt",
        "",
        "Versión limpiada automáticamente de la transcripción.",
        "Se removieron encabezados técnicos, delimitadores y ruido evidente de exportación.",
        "",
    ]
    for module in modules:
        lines.append(f"MÓDULO {module['module_number']}")
        kept = []
        for sentence in split_sentences(module["raw_text"]):
            lowered = normalize_text(sentence)
            if len(sentence) < 50:
                continue
            if lowered in {"gracias", "buenas tardes", "buenos dias", "buenos días"}:
                continue
            if sum(1 for filler in ("gracias", "ok", "bueno", "listo", "perfecto") if filler in lowered) >= 2 and len(sentence) < 90:
                continue
            kept.append(sentence)
            if len(kept) >= 40:
                break
        for paragraph in kept:
            lines.append(paragraph)
        lines.append("")
    return "\n".join(lines)


def merged_clean_transcript_text(modules: list[dict], fallback_text: str) -> str:
    if modules:
        return "\n\n".join(item["raw_text"] for item in modules if item["raw_text"]).strip()
    return clean_block_text(fallback_text)


def build_merged_content(overview: dict, module_summaries: list[dict], manual_headings: list[str]) -> str:
    lines = [
        "DOCUMENTO: merged_clean_content.txt",
        "",
        overview["description"],
        "",
        "EJES PRINCIPALES",
    ]
    for item in overview["main_axes"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("MÓDULOS DETECTADOS")
    for module in module_summaries:
        lines.append(f"- Módulo {module['module_number']}: {compact(module['summary_text'], 220)}")
    lines.append("")
    lines.append("TEMAS DETECTADOS EN MANUALES Y GUÍAS")
    for heading in manual_headings[:20]:
        lines.append(f"- {heading}")
    return "\n".join(lines)


def build_ambiguities(manifest: dict, modules: list[dict], sources: list[SourceFile], protocols: list[dict]) -> list[str]:
    ambiguities = []
    module_numbers = [item["module_number"] for item in modules]
    if len(module_numbers) != len(set(module_numbers)):
        ambiguities.append("La transcripción presenta módulos repetidos o numeración duplicada.")
    if not any(source.tipo == "manual" for source in sources):
        ambiguities.append("No se encontró manual textual local; la unidad depende principalmente de la transcripción y del índice.")
    if not protocols:
        ambiguities.append("No se detectaron protocolos suficientemente estructurados de forma automática.")
    if manifest["tipo"].lower() == "diplomado":
        ambiguities.append("Al tratarse de un diplomado, algunas fuentes mezclan módulo, manual complementario y material de apoyo; puede haber superposición conceptual.")
    return ambiguities


def build_gaps(sources: list[SourceFile], concepts: list[dict], intake_questions: list[dict]) -> list[str]:
    gaps = []
    if not any(source.tipo == "transcripcion" for source in sources):
        gaps.append("No hay transcripción local para nutrir razonamiento clínico y preguntas terapéuticas.")
    if len(concepts) < 6:
        gaps.append("La extracción automática detectó pocos conceptos explícitos; conviene revisión manual.")
    if len(intake_questions) < 3:
        gaps.append("La capa terapéutica quedó con pocas preguntas de intake claramente inferibles del material.")
    return gaps


def process_course(course_dir: Path) -> str:
    manifest_path = course_dir / "course_manifest.json"
    if not manifest_path.exists():
        return f"skip {course_dir}: no_manifest"

    manifest = json.loads(read_text(manifest_path))
    output_slug = derive_output_slug(manifest["course_name"])
    output_dir = OUTPUT_ROOT / output_slug
    if output_slug in SKIP_EXISTING and output_dir.exists():
        return f"skip {output_slug}: preserved_existing"

    sources = load_sources(course_dir, manifest)
    copied = copy_sources(output_dir, sources, manifest_path)

    transcript_sources_raw = [(source.local_path.name, read_text(source.local_path)) for source in sources if source.local_path and source.tipo == "transcripcion"]
    index_sources = [(source.local_path.name, read_text(source.local_path)) for source in sources if source.local_path and source.tipo == "indice"]
    manual_sources = [(source.local_path.name, read_text(source.local_path)) for source in sources if source.local_path and source.tipo in {"manual", "guia", "protocolo"}]

    transcript_text = transcript_sources_raw[0][1] if transcript_sources_raw else ""
    modules = split_transcript_modules(transcript_text) if transcript_text else []
    transcript_sources = []
    for label, raw_text in transcript_sources_raw:
        transcript_sources.append((label, merged_clean_transcript_text(modules, raw_text)))
    all_source_texts = transcript_sources + manual_sources
    module_numbers = sorted(set(item["module_number"] for item in modules))
    if not module_numbers:
        for _, index_text in index_sources:
            module_numbers.extend(parse_index_text(index_text))
        module_numbers = sorted(set(module_numbers))
        modules = [{"module_number": number, "fecha_proceso": "", "raw_text": ""} for number in module_numbers]

    headings = collect_manual_headings([text for _, text in manual_sources])
    concepts = build_concepts(
        manifest["course_name"],
        headings,
        copied["copied_files"],
        all_source_texts,
        modules,
    )
    module_summaries = build_module_summaries(modules, headings or [concept["termino"] for concept in concepts[:8]])
    overview = build_overview(manifest, module_numbers, headings, concepts, module_summaries)
    glossary = build_glossary(concepts)
    faq = build_faq(concepts, module_summaries)

    intake_questions = build_intake_questions(all_source_texts)
    reasoning_patterns = build_reasoning_patterns(all_source_texts)
    interpretation_guides = build_interpretation_guides(all_source_texts)
    therapeutic_observations = build_observations(all_source_texts)
    clinical_warnings = build_warnings(all_source_texts)

    protocol_source_texts = []
    for source in sources:
        if not source.local_path:
            continue
        if source.tipo == "protocolo" or any(term in normalize_text(source.local_path.name) for term in ("protocolo", "protocolos", "rutina", "rastreo")):
            protocol_source_texts.append((source.local_path.name, read_text(source.local_path)))
    protocols = build_protocols(protocol_source_texts, modules)

    ambiguities = build_ambiguities(manifest, modules, sources, protocols)
    gaps = build_gaps(sources, concepts, intake_questions)

    clean_transcript = build_clean_transcript_text(modules)
    clean_manual = build_clean_manual(manual_sources, headings)
    merged_clean = build_merged_content(overview, module_summaries, headings)

    write_text(output_dir / "02_clean" / "clean_transcript.txt", clean_transcript or "No se encontró transcripción utilizable.\n")
    write_text(output_dir / "02_clean" / "manual_extracted.txt", clean_manual or "No se encontraron manuales o guías locales.\n")
    write_text(output_dir / "02_clean" / "merged_clean_content.txt", merged_clean)

    write_json(output_dir / "03_academic" / "course_overview.json", overview)
    write_json(output_dir / "03_academic" / "concepts.json", concepts)
    write_json(output_dir / "03_academic" / "glossary.json", glossary)
    write_json(output_dir / "03_academic" / "module_summaries.json", module_summaries)
    write_json(output_dir / "03_academic" / "faq_candidates.json", faq)

    write_json(output_dir / "04_therapeutic" / "intake_questions.json", intake_questions)
    write_json(output_dir / "04_therapeutic" / "reasoning_patterns.json", reasoning_patterns)
    write_json(output_dir / "04_therapeutic" / "interpretation_guides.json", interpretation_guides)
    write_json(output_dir / "04_therapeutic" / "therapeutic_observations.json", therapeutic_observations)
    write_json(output_dir / "04_therapeutic" / "clinical_warnings.json", clinical_warnings)

    write_json(output_dir / "05_protocols" / "protocols.json", protocols)

    write_json(
        output_dir / "06_catalog" / "transcript_inventory.json",
        [
            {
                "module_number": item["module_number"],
                "fecha_proceso": item["fecha_proceso"],
                "chars": len(item["raw_text"]),
            }
            for item in modules
        ],
    )
    write_json(
        output_dir / "06_catalog" / "module_inventory.json",
        [
            {
                "module_number": item["module_number"],
                "summary_text": compact(item["summary_text"], 220),
            }
            for item in module_summaries
        ],
    )
    write_json(
        output_dir / "06_catalog" / "course_manifest.json",
        {
            "nombre_del_curso": manifest["course_name"],
            "linea": manifest["linea"],
            "tipo": manifest["tipo"],
            "archivos_fuente_usados": [ref["archivo_original"] for ref in copied["external_refs"]],
            "temas_principales": overview["main_axes"],
            "modulos_detectados": module_numbers,
            "cantidad_de_conceptos_extraidos": len(concepts),
            "cantidad_de_patrones_terapeuticos_extraidos": len(reasoning_patterns),
            "cantidad_de_protocolos_extraidos": len(protocols),
            "ambiguedades_detectadas": ambiguities,
            "vacios_detectados": gaps,
            "nivel_de_preparacion": {
                "academic": "medio-alto" if concepts else "medio",
                "therapeutic": "medio" if intake_questions or reasoning_patterns else "bajo-medio",
                "protocols": "medio" if protocols else "bajo",
            },
            "observacion_general": "Unidad generada automáticamente para estandarizar la base de conocimiento del curso. Conviene revisión humana para usos clínicos o docentes de máxima precisión.",
        },
    )
    write_json(
        output_dir / "01_sources" / "metadata.json",
        {
            "course_id": manifest["course_id"],
            "course_name": manifest["course_name"],
            "linea": manifest["linea"],
            "tipo": manifest["tipo"],
            "idioma": manifest.get("idioma", "es"),
            "fuentes": copied["external_refs"],
        },
    )

    return f"ok {output_slug}"


def iter_courses():
    for line_dir in sorted(PROCESSED_LIBRARY.iterdir()):
        if not line_dir.is_dir():
            continue
        for course_dir in sorted(line_dir.iterdir()):
            if course_dir.is_dir():
                yield course_dir


def main() -> None:
    results = []
    for course_dir in iter_courses():
        results.append(process_course(course_dir))
    print("\n".join(results))


if __name__ == "__main__":
    main()
