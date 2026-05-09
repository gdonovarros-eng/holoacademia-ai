"""
Build biomagnetic pairs database from course manuals.

PDF extraction format (Holobiomagnetismo_2021.txt):
  - Pair header line: 4-22 leading spaces + CAPS_NAME - CAPS_NAME + (conditions) + TYPE
  - Pre-condition line: 25+ leading spaces, appears BEFORE the pair header
  - Post-condition line: 25+ leading spaces, appears AFTER the pair header
  - Type appears at the far right of the pair header line

Output: data/biomagnetic_pairs_db.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LIBRARY = DATA / "processed_library" / "Salud"

MANUAL_2021 = LIBRARY / "curso-holobiomagnetismo-2021" / "sources" / "Holobiomagnetismo_2021.txt"
MANUAL_P2 = (
    LIBRARY
    / "curso-holobiomagnetismo-parte-2"
    / "sources"
    / "HoloBiomagnetismo_Parte_2_(Psicosomática)_-_Actualizado_-_Alejandro_Lavín.txt"
)

# ── helpers ──────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


NOISE_RE = re.compile(
    r"www\.\S+|ALEJANDRO LAVÍN|alejandrolavin\.com|altermeds\.mx|\+52\s*[\d ]{6,}|"
    r"Para información.*?cursos|^\d{1,3}$",
    re.IGNORECASE,
)

def _strip_noise(text: str) -> str:
    text = NOISE_RE.sub("", text)
    return _clean(text)


TYPE_KEYWORDS = [
    ("hongo", "hongo"),
    ("cándida", "hongo"),
    ("candida", "hongo"),
    ("micello", "hongo"),
    ("bacteria", "bacteria"),
    ("streptococcus", "bacteria"),
    ("staphylococcus", "bacteria"),
    ("mycobacterium", "bacteria"),
    ("clostridium", "bacteria"),
    ("bacilo", "bacteria"),
    ("salmonella", "bacteria"),
    ("helicobacter", "bacteria"),
    ("listeria", "bacteria"),
    ("virus", "virus"),
    ("herpes", "virus"),
    ("papiloma", "virus"),
    ("retrovirus", "virus"),
    ("v.i.h", "virus"),
    ("vih", "virus"),
    ("parasito", "parasito"),
    ("parásito", "parasito"),
    ("giardia", "parasito"),
    ("ameba", "parasito"),
    ("lodamoeba", "parasito"),
    ("disfuncional", "disfuncional"),
    ("emocional", "emocional"),
    ("reservorio", "reservorio"),
    ("especial", "especial"),
]

def _classify_type(raw: str) -> str:
    low = raw.lower()
    for kw, cat in TYPE_KEYWORDS:
        if kw in low:
            return cat
    return "desconocido"


def _make_id(name: str) -> str:
    n = name.lower()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n"),("ü","u")]:
        n = n.replace(a, b)
    n = re.sub(r"[^a-z0-9]+", "_", n).strip("_")
    return n


# ── find type at far right of a line ─────────────────────────────────────────

TYPE_LINE_RE = re.compile(
    r"(?:Hongo.*?|Bacteria.*?|Virus.*?|Parás?ito.*?|ESPECIAL|DISFUNCIONAL|EMOCIONAL|RESERVORIO"
    r"|V\.I\.H|Cándida.*?|Mycobacterium.*?|Streptococcus.*?|Staphylococcus.*?"
    r"|Salmonella.*?|Helicobacter.*?|Giardia.*?|Listeria.*?|Lodamoeba.*?"
    r"|Enterobacter.*?|Enterococcus.*?|Clostridium.*?|Bacilo.*?|Zoster.*?"
    r"|Vaccinia.*?|Parvovirus.*?|Polyoma.*?|Sincitial.*?|Paramox.*?|Retrovirus.*?)$",
    re.IGNORECASE,
)

def _extract_type(line: str) -> tuple[str, str]:
    """Return (type_raw, line_without_type)."""
    m = TYPE_LINE_RE.search(line)
    if not m:
        return "", line
    type_raw = m.group(0).strip()
    line_clean = line[:m.start()].strip()
    return type_raw, line_clean


# ── pair header detection ─────────────────────────────────────────────────────

PAIR_HEADER_RE = re.compile(
    r"^(?P<indent>[ \t]{4,22})"
    r"(?P<name>[A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ0-9 .()]{1,}(?:\s*[-–]\s*[A-ZÁÉÍÓÚÑÜ0-9 .()]+){1,})"
    r"(?P<rest>[ \t]{3,}.*)?"
    r"$"
)

EXCLUDE_NAMES = {
    "PAR BIOMAGNETICO", "PADECIMIENTO RELACIONADO", "TIPO",
    "A", "B", "C", "D", "E", "F", "G", "H",
}

def _is_pair_header(line: str) -> tuple[str, str, str] | None:
    """
    Returns (name, inline_condition, type_raw) or None.
    Criteria:
    - Leading spaces 4-22
    - CAPS words with ' - ' or ' – ' separator (pair name)
    - At least 75% uppercase letters in the name
    - Name length 5-100
    """
    m = PAIR_HEADER_RE.match(line)
    if not m:
        return None
    name = _clean(m.group("name"))
    # Check uppercase ratio
    letters = re.sub(r"[^a-zA-ZÁÉÍÓÚÑÜáéíóúñü]", "", name)
    if not letters or len(letters) < 4:
        return None
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if upper_ratio < 0.75:
        return None
    # Must actually contain a dash separator between two organ names
    if not re.search(r"[A-ZÁÉÍÓÚÑÜ]{2,}\s*[-–]\s*[A-ZÁÉÍÓÚÑÜ]{2,}", name):
        return None
    if name in EXCLUDE_NAMES or len(name) < 5 or len(name) > 110:
        return None
    rest = m.group("rest") or ""
    type_raw, inline_cond = _extract_type(rest)
    inline_cond = _strip_noise(inline_cond)
    return name, inline_cond, type_raw


# ── main parser ───────────────────────────────────────────────────────────────

def parse_2021_pairs() -> list[dict]:
    text = MANUAL_2021.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # Find table header (PAR BIOMAGNETICO ... PADECIMIENTO RELACIONADO)
    table_start = 0
    for i, line in enumerate(lines):
        if "PAR BIOMAGNETICO" in line and "PADECIMIENTO" in line:
            table_start = i + 1
            break
    if not table_start:
        raise RuntimeError("No encontré la tabla de pares en el manual.")

    # The table ends roughly 6000 lines after start (before anatomy section)
    table_end = min(len(lines), table_start + 6500)

    # ---- First pass: identify all pair header positions ----
    pair_positions: list[tuple[int, str, str, str]] = []  # (line_idx, name, inline_cond, type_raw)
    for i in range(table_start, table_end):
        result = _is_pair_header(lines[i])
        if result:
            name, inline_cond, type_raw = result
            pair_positions.append((i, name, inline_cond, type_raw))

    # ---- Second pass: for each pair, collect conditions ----
    #
    # For pair at position P:
    #   - Pre-conditions: lines with 25+ leading spaces between previous pair and P
    #   - Inline condition: text on P itself
    #   - Post-conditions: lines with 25+ leading spaces between P and next pair
    #
    # Lines with leading spaces < 25 that are NOT pair headers are noise (page numbers, etc.)

    def leading_spaces(line: str) -> int:
        return len(line) - len(line.lstrip())

    def is_condition_line(line: str) -> bool:
        ls = leading_spaces(line)
        stripped = line.strip()
        if not stripped:
            return False
        if ls < 25:
            return False
        # Skip noise
        if NOISE_RE.search(stripped):
            return False
        if re.match(r"^\d{1,3}$", stripped):
            return False
        return True

    def collect_condition_lines(start: int, end: int) -> list[str]:
        result = []
        for i in range(start, end):
            line = lines[i]
            result2 = _is_pair_header(line)
            if result2 is not None:
                break
            if is_condition_line(line):
                t, cond = _extract_type(line)
                cond = _strip_noise(cond)
                if cond:
                    result.append(cond)
                if t and not cond:
                    # type-only continuation (shouldn't happen but just in case)
                    pass
        return result

    pairs: list[dict] = []

    for idx, (pos, name, inline_cond, type_raw) in enumerate(pair_positions):
        # Determine previous boundary
        prev_pos = pair_positions[idx - 1][0] if idx > 0 else table_start
        # Determine next boundary
        next_pos = pair_positions[idx + 1][0] if idx + 1 < len(pair_positions) else table_end

        # Pre-conditions: between previous pair header and this header
        pre_conditions = collect_condition_lines(prev_pos + 1, pos)

        # Post-conditions: between this header and next pair header
        post_conditions = collect_condition_lines(pos + 1, next_pos)

        # If type_raw not found on pair line, look in post-conditions
        if not type_raw:
            for line in lines[pos + 1:min(pos + 5, next_pos)]:
                t, _ = _extract_type(line)
                if t:
                    type_raw = t
                    break

        all_conditions = pre_conditions + ([inline_cond] if inline_cond else []) + post_conditions
        conditions = _clean(" ".join(all_conditions))
        # Final noise removal
        conditions = _strip_noise(conditions)

        pairs.append({
            "id": _make_id(name),
            "nombre": name,
            "tipo_raw": _clean(type_raw),
            "tipo": _classify_type(type_raw),
            "condiciones": conditions,
            "conflicto_tipico": "",
            "significado_emocional": "",
            "sistemas_afectados": [],
            "pregunta_clave": "",
            "linea_genograma": "",
            "protocolo_sugerido": "",
        })

    return pairs


# ── psychosomatic context from Parte 2 ───────────────────────────────────────

CONFLICT_RE = re.compile(r"Conflicto de\s+[^.\"]{5,80}", re.IGNORECASE)
QUOTE_RE = re.compile(r'"([^"]{5,120})"')

ORGAN_SYSTEMS = {
    "digestivo": ["estomago", "estómago", "hígado", "higado", "intestino", "colón", "colon", "páncreas", "pancreas", "vesícula", "vesicula", "duodeno", "yeyuno", "íleon", "ileon", "recto", "sigmoide"],
    "respiratorio": ["pulmón", "pulmon", "bronquio", "tráquea", "traquea", "laringe", "faringe", "seno", "pleura", "nariz"],
    "cardiovascular": ["corazón", "corazon", "aorta", "arteria", "vena", "sangre", "miocardio", "cardiaco"],
    "renal_urinario": ["riñón", "riñon", "vejiga", "uréter", "uretra", "nefr"],
    "osteomuscular": ["hueso", "músculo", "musculo", "articulación", "articulacion", "columna", "lumbar", "cervical", "tendón", "tendon", "ligamento", "cartílago"],
    "endócrino": ["tiroides", "suprarrenal", "hipófisis", "hipofisis", "páncreas", "pancreas", "hormona", "tiroxina", "insulina", "cortisol"],
    "genital": ["útero", "utero", "ovario", "testículo", "testiculo", "próstata", "prostata", "vagina", "endometrio", "trompas", "mama", "pecho"],
    "neurológico": ["cerebro", "nervio", "médula", "medula", "hipotálamo", "hipotalamo", "hipocampo", "neurona", "encéfalo", "encefalo"],
    "piel": ["piel", "dermis", "epidermis", "queratina"],
    "linfático": ["linfa", "timo", "bazo", "amígdala", "amigdala", "ganglio", "linfocito"],
}

def _infer_systems(text: str) -> list[str]:
    low = text.lower()
    return [sys for sys, kws in ORGAN_SYSTEMS.items() if any(kw in low for kw in kws)]


def extract_psychosomatic_context() -> dict[str, list[str]]:
    """Extract conflict phrases and associate them with body systems/organs."""
    text = MANUAL_P2.read_text(encoding="utf-8", errors="replace")

    # Extract conflict phrases with surrounding context (organ reference)
    context: dict[str, list[str]] = {sys: [] for sys in ORGAN_SYSTEMS}

    # Sliding window: look at chunks of 3 lines
    lines = text.splitlines()
    for i, line in enumerate(lines):
        conflicts = CONFLICT_RE.findall(line)
        quotes = QUOTE_RE.findall(line)
        if not conflicts and not quotes:
            continue
        # Look at surrounding lines for organ reference
        window = "\n".join(lines[max(0, i-2):min(len(lines), i+5)])
        for sys, kws in ORGAN_SYSTEMS.items():
            if any(kw in window.lower() for kw in kws):
                for c in conflicts:
                    phrase = _clean(c)
                    if phrase not in context[sys]:
                        context[sys].append(phrase)
                for q in quotes:
                    phrase = f'"{_clean(q)}"'
                    if phrase not in context[sys]:
                        context[sys].append(phrase)

    return context


# ── enrich pairs ──────────────────────────────────────────────────────────────

def enrich_pairs(pairs: list[dict], psych_context: dict[str, list[str]]) -> list[dict]:
    for pair in pairs:
        name_low = pair["nombre"].lower()
        cond_low = pair["condiciones"].lower()
        combined = f"{name_low} {cond_low}"

        pair["sistemas_afectados"] = _infer_systems(combined)

        # Match conflicts from psychosomatic context
        matched: list[str] = []
        for sys in pair["sistemas_afectados"]:
            matched.extend(psych_context.get(sys, []))
        matched = list(dict.fromkeys(matched))[:5]  # deduplicate, take top 5

        if matched:
            pair["conflicto_tipico"] = matched[0]
            pair["significado_emocional"] = "; ".join(matched[:3])

        if pair["tipo"] == "emocional" and pair["condiciones"]:
            pair["significado_emocional"] = pair["condiciones"]
            if not pair["conflicto_tipico"]:
                pair["conflicto_tipico"] = pair["condiciones"]

        # Genogram line inference
        comb = combined
        if any(h in comb for h in ["útero", "utero", "ovario", "mama", "estrógeno", "cervix", "endometrio"]):
            pair["linea_genograma"] = "materna"
        elif any(h in comb for h in ["próstata", "prostata", "testículo", "testiculo"]):
            pair["linea_genograma"] = "paterna"

    return pairs


# ── deduplicate ───────────────────────────────────────────────────────────────

def deduplicate(pairs: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique = []
    for p in pairs:
        base = p["id"]
        if base not in seen:
            seen.add(base)
            unique.append(p)
        else:
            suffix = 2
            while f"{base}_{suffix}" in seen:
                suffix += 1
            new_id = f"{base}_{suffix}"
            seen.add(new_id)
            p["id"] = new_id
            unique.append(p)
    return unique


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print("Parseando pares del manual 2021...")
    pairs = parse_2021_pairs()
    print(f"  → {len(pairs)} pares encontrados")

    print("Extrayendo contexto psicosomático de Parte 2...")
    psych_ctx = extract_psychosomatic_context()
    total_conflicts = sum(len(v) for v in psych_ctx.values())
    print(f"  → {total_conflicts} frases de conflicto en {len(psych_ctx)} sistemas")

    print("Enriqueciendo pares con contexto psicosomático...")
    pairs = enrich_pairs(pairs, psych_ctx)

    pairs.sort(key=lambda p: p["nombre"])
    pairs = deduplicate(pairs)

    output = DATA / "biomagnetic_pairs_db.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump({"version": "1.1", "total": len(pairs), "pairs": pairs}, f, ensure_ascii=False, indent=2)

    print(f"\nListo → {output}")
    print(f"Total pares: {len(pairs)}")

    by_type: dict[str, int] = {}
    for p in pairs:
        by_type[p["tipo"]] = by_type.get(p["tipo"], 0) + 1
    print("\nPor tipo:")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t}: {n}")

    with_conflict = sum(1 for p in pairs if p["conflicto_tipico"])
    with_systems = sum(1 for p in pairs if p["sistemas_afectados"])
    empty_cond = sum(1 for p in pairs if not p["condiciones"])
    print(f"\nCon conflicto típico: {with_conflict} / {len(pairs)}")
    print(f"Con sistema inferido: {with_systems} / {len(pairs)}")
    print(f"Sin condiciones:      {empty_cond} / {len(pairs)}")

    # Sample: show 5 well-populated pairs
    print("\n── Muestra de 5 pares ──")
    samples = [p for p in pairs if p["condiciones"] and p["conflicto_tipico"]][:5]
    for p in samples:
        print(f"\n{p['nombre']} [{p['tipo']}]")
        print(f"  Condiciones: {p['condiciones'][:120]}...")
        print(f"  Conflicto:   {p['conflicto_tipico'][:100]}")
        print(f"  Sistemas:    {p['sistemas_afectados']}")


if __name__ == "__main__":
    main()
