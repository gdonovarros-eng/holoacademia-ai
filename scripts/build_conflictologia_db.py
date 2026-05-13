#!/usr/bin/env python3
"""
build_conflictologia_db.py
Extrae las tablas de conflictología de los manuales del Diplomado Terapia Holística
y genera data/conflictologia_db.json para servir desde /api/conflictologia-db
"""
from __future__ import annotations
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SOURCES = BASE / "data" / "knowledge_units" / "course_terapia_holistica_1" / "01_sources"
OUT = BASE / "data" / "conflictologia_db.json"

# ── helpers ────────────────────────────────────────────────────────────────────
def clean(s: str) -> str:
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.strip('"').strip()
    return s

def read_lines(path: Path) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return f.readlines()


def extract_section(lines: list[str], start: int, end: int) -> list[str]:
    """Return stripped lines between start and end (0-based)."""
    return [l.rstrip('\n') for l in lines[start:end]]


# ── parser ────────────────────────────────────────────────────────────────────
SKIP_PATTERNS = [
    r'ALEJANDRO\s+LAV',
    r'^\s*$',
    r'^\s*\d+\s*$',            # lone page numbers
    r'RASTREO\s+(CONFLICTO|MICRO|BIO|VIBR|BIOE|ORGAN|HOLOB)',
    r'MS:\s*',
    r'NO\s*[–-]',
    r'SI\s*[–-]',
    r'MICROBIOLOG',
    r'BACTERIAS\s',
    r'VIRUS\s',
    r'HONGOS\s',
    r'PARÁSIT',
    r'DIPLOM',
    r'TERAPIA',
    r'MÉTODO LAVÍN',
    r'MÓDULO',
    r'FUNDAMENTOS',
    r'ANATOMÍA',
    r'Bloque\s',
    r'Número\s',
    r'Ubicar\s',
    r'Hay\s+algún\s+otro\s+conflicto',
    r'Repetir\s+procedimiento',
    r'SESIÓN\s+TERA',
    r'Herramienta',
    r'Recomendar',
    r'Colocar\s+imanes',
    r'RASTREO\s+ORGÁNICO',
    r'Manifiéstame',
    r'Manifiestame',
    r'Hacer\s+el\s+rastreo',
    r'conflictos$',
    r'\d+\s+bacterias',
    r'\d+\s+virus',
    r'\d+\s+hongos',
    r'\d+\s+parásitos',
]

def should_skip(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    for pat in SKIP_PATTERNS:
        if re.search(pat, stripped, re.IGNORECASE):
            return True
    return False


def parse_conflicts(raw_lines: list[str]) -> list[dict]:
    """
    Parse a block of text into conflict entries.
    Format expected (varies):
      Nombre del conflicto
    1
      "Descripción"
    or
    1   Nombre del conflicto
        "Descripción"
    or
      Nombre del conflicto
    1 "Descripción"
    """
    conflicts = []
    i = 0
    current_nombre = None
    current_desc_parts = []

    def flush():
        nonlocal current_nombre, current_desc_parts
        if current_nombre:
            desc = ' '.join(current_desc_parts).strip().strip('"')
            conflicts.append({
                "nombre": current_nombre,
                "desc": desc or current_nombre
            })
        current_nombre = None
        current_desc_parts = []

    lines = [l for l in raw_lines if l.strip()]

    for line in lines:
        stripped = line.strip()

        # Skip unwanted lines
        if should_skip(stripped):
            continue

        # Detect numbered prefix: "1 text", "2 text", or lone "1"
        m = re.match(r'^(\d)\s+(.*)', stripped)
        if m and int(m.group(1)) in range(1, 6):
            num_text = m.group(2).strip()
            if current_nombre is None:
                # Number before name — this is the description
                current_nombre = num_text if num_text else None
                current_desc_parts = []
            else:
                # Number after name — flush previous, this IS the separator
                if num_text:
                    # Might be a new conflict name
                    flush()
                    current_nombre = num_text
                    current_desc_parts = []
                # else lone number → keep
            continue

        # Lone number
        if re.match(r'^(\d)\s*$', stripped) and int(stripped[0]) in range(1, 6):
            # separator — nothing to do
            continue

        # Subsystem header (all caps, long) → flush
        if re.match(r'^[A-ZÁÉÍÓÚÑ\s]{8,}$', stripped) and not stripped.startswith('"'):
            flush()
            continue

        # Regular text line
        if current_nombre is None:
            current_nombre = stripped.strip('"')
        else:
            current_desc_parts.append(stripped.strip('"'))

    flush()
    return conflicts


# ── section extractor ──────────────────────────────────────────────────────────
def find_subsystem_blocks(lines: list[str], start: int, end: int) -> list[tuple[str, int, int]]:
    """
    Returns list of (subsystem_label, start_line, end_line) within the section.
    Subsystem headers look like 'Conflictología XXXX' or 'CONFLICTOLOGÍA XXXX'.
    """
    blocks: list[tuple[str, int, int]] = []
    header_re = re.compile(
        r'Conflictolog[ií]a\s+(.+)|CONFLICTOLOG[IÍ]A\s+(.+)',
        re.IGNORECASE
    )

    current_label: str | None = None
    current_start: int | None = None

    for i, line in enumerate(lines[start:end], start=start):
        m = header_re.search(line.strip())
        if m:
            if current_label is not None:
                blocks.append((current_label, current_start, i))
            current_label = (m.group(1) or m.group(2)).strip().rstrip('.')
            current_start = i + 1

    if current_label is not None:
        blocks.append((current_label, current_start, end))

    return blocks


# ── module definitions ─────────────────────────────────────────────────────────
# Each entry: (key, system_title, filename, conflicto_start_line, conflicto_end_line)
# Lines are 1-based as seen in grep, converted to 0-based for Python.
MODULES = [
    # key, title, file, start(1-based), end(1-based)
    ("respiratorio", "Sistema Respiratorio",
     "Protocolos_de_Rastreo_-_Módulo_1.txt", 1, 380),
    ("digestivo", "Sistema Digestivo",
     "Protocolos_de_Rastreo_-_Módulo_2.txt", 1, 600),
    ("endocrino", "Sistema Endócrino-Metabólico",
     "Manual_del_Módulo_4.txt", 2352, 2850),
    ("cardiovascular", "Sistema Cardiovascular",
     "Manual_del_Módulo_5.txt", 2966, 3460),
    ("locomotor", "Sistema Locomotor / Osteomuscular",
     "Manual_del_Módulo_6.txt", 2352, 3100),
    ("piel", "Sistema Lipofascial / Dermatológico",
     "Manual_del_Módulo_7.txt", 3194, 3700),
    ("genital", "Sistema Reproductor",
     "Manual_del_Módulo_8.txt", 5035, 5700),
    ("urinario", "Sistema Urinario / Renal",
     "Manual_del_Módulo_9.txt", 937, 1230),
    ("inmunologico", "Sistema Inmunológico / Linfático",
     "Manual_del_Módulo_10.txt", 1146, 1550),
    ("neurosensorial", "Sistema Neurosensorial",
     "Manual_del_Módulo_11.txt", 2467, 3200),
]

# ── MANUAL DATA for Respiratory and Digestive (already clean protocol files) ──
# Rather than relying on auto-parsing (which may miss nuance for these two
# well-structured systems), we partially hardcode the subsystem structure
# and let the generic extractor handle the rest.

RESPIRATORY_SUBSYSTEMS = [
    "Nasal", "Laríngea", "Traqueal", "Bronquial", "Alveolar",
    "Diafragmática", "Gripal", "De la Tos", "Asmática",
    "De Apnea", "Tabaquista", "Transgeneracional"
]

DIGESTIVE_SUBSYSTEMS = [
    "Bucal", "Estomacal", "Intestinal Delgada", "Hepática", "Biliar",
    "Intestinal Gruesa", "Anal", "Peritoneal", "Del Quimo"
]


# ── main builder ───────────────────────────────────────────────────────────────
def build_system(key: str, title: str, filepath: str, start1: int, end1: int) -> dict:
    path = SOURCES / filepath
    if not path.exists():
        print(f"  ⚠ Not found: {path}")
        return {"title": title, "subsystems": {}}

    lines = read_lines(path)
    total = len(lines)
    start0 = max(0, start1 - 1)
    end0 = min(total, end1)

    section = lines[start0:end0]

    # Find subsystem headers within section
    header_re = re.compile(
        r'(?:Conflictolog[ií]a|CONFLICTOLOG[IÍ]A)\s+(.+)',
        re.IGNORECASE
    )
    # Also look for ALL CAPS single-word section headers in protocol files
    # e.g. "CONFLICTOLOGÍA NASAL" but also "NASAL" alone after the main header
    simple_header_re = re.compile(
        r'^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s/]{4,}\s*$'
    )

    subsystems = {}
    blocks: list[tuple[str, list[str]]] = []

    current_label = None
    current_block = []

    for line in section:
        stripped = line.strip()

        # Main conflictología header → subsystem
        m = header_re.search(stripped)
        if m:
            if current_label:
                blocks.append((current_label, current_block))
            current_label = m.group(1).strip()
            current_block = []
            continue

        # Try short all-caps header
        if simple_header_re.match(stripped) and len(stripped) < 50 and not should_skip(stripped):
            # Could be a subsystem name inside a block
            if current_label:
                blocks.append((current_label, current_block))
            # clean up
            label = stripped.strip('.')
            # Only treat as new subsystem if meaningful
            if label and len(label) > 3 and label not in {'ALEJANDRO', 'LAVÍN', 'DIPLOMADO',
                                                            'TERAPIA', 'MÉTODO', 'MÓDULO',
                                                            'FUNDAMENTOS', 'ANATOMÍA',
                                                            'MICROBIOLOGÍA', 'BACTERIAS',
                                                            'VIRUS', 'HONGOS', 'PARÁSITOS',
                                                            'ALEJANDRO LAVÍN'}:
                current_label = label.title()
                current_block = []
                continue

        if current_label is not None:
            current_block.append(stripped)

    if current_label:
        blocks.append((current_label, current_block))

    # Build subsystems dict
    for label, raw in blocks:
        conflicts = parse_conflicts(raw)
        if conflicts:
            slug = re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')
            subsystems[slug] = {
                "label": label,
                "conflicts": conflicts
            }

    print(f"  ✓ {title}: {len(subsystems)} subsystems, "
          f"{sum(len(v['conflicts']) for v in subsystems.values())} conflicts")

    return {
        "title": title,
        "subsystems": subsystems
    }


def is_junk_conflict(c: dict) -> bool:
    """Remove auto-parsed conflicts that are just header/count lines."""
    n = c.get("nombre", "")
    # Count summary lines like "Nasal 5 5 5 5 1" or "Miocardial 5 5" or "Tumoral 5 4"
    if re.search(r'\d\s+\d', n):
        return True
    # Very short non-descriptive entries
    if len(n) < 5:
        return True
    # Pure number sequences
    if re.match(r'^[\d\s]+$', n):
        return True
    # Lines that are just the system count overview ("200 conflictos")
    if re.search(r'conflictos$', n, re.IGNORECASE):
        return True
    return False


def clean_subsystem_label(label: str) -> str:
    """Clean up merged two-column labels."""
    # If the label contains 'CONFLICTOLOGÍA' it's a merge artefact — take first part
    if 'CONFLICTOLOG' in label.upper():
        label = label.split('CONFLICTOLOG')[0].strip()
    # Strip trailing numbers / colons
    label = re.sub(r'[\d\s:]+$', '', label).strip()
    return label.title() if label else label


def post_clean(db: dict) -> dict:
    """Remove junk entries and clean labels."""
    for sys in db.values():
        clean_subs = {}
        for slug, sub in sys['subsystems'].items():
            # Clean label
            label = clean_subsystem_label(sub['label'])
            if not label or len(label) < 3:
                continue
            # Filter junk conflicts
            good = [c for c in sub['conflicts'] if not is_junk_conflict(c)]
            if not good:
                continue
            clean_subs[slug] = {
                "label": label,
                "conflicts": good
            }
        sys['subsystems'] = clean_subs
    return db


def main():
    db = {}
    for key, title, filepath, start1, end1 in MODULES:
        print(f"Building: {title}…")
        db[key] = build_system(key, title, filepath, start1, end1)

    db = post_clean(db)

    # Write output
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({"version": "1.0", "systems": db}, f, ensure_ascii=False, indent=2)

    total_conflicts = sum(
        len(s['conflicts'])
        for sys in db.values()
        for s in sys['subsystems'].values()
    )
    print(f"\n✅ Written {OUT}")
    print(f"   Systems: {len(db)}")
    print(f"   Total conflicts: {total_conflicts}")


if __name__ == "__main__":
    main()
