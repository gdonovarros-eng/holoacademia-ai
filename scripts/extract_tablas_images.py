"""
Extrae SOLO las páginas de tablas de rastreo de los manuales clave.
Organiza por categoría en data/tablas_images/{categoria}/

Uso: .venv/bin/python3.14 scripts/extract_tablas_images.py
"""
import pymupdf as fitz
from pathlib import Path
import json, shutil

MANUALES_DIR = Path("/Users/m2/Desktop/holo_pipeline/MANUALES/Manuales")
OUTPUT_DIR   = Path(__file__).resolve().parent.parent / "data" / "tablas_images"
DPI = 150

# ── Mapeo exacto: categoría → páginas específicas de cada manual ─────────────
# Páginas 1-indexed tal como aparecen en el PDF.
TABLAS_MAP = {

    "pares_biomagneticos": {
        "label": "Pares Biomagnéticos",
        "icon":  "🧲",
        "color": "#10b981",
        "fuentes": [
            # Menú global de pares + regiones
            {"manual": "HOLOBIOMAGNETISMO PARTE 1.pdf", "paginas": list(range(32, 112))},
        ],
    },

    "microbios": {
        "label": "Microbios (Bacterias / Virus / Hongos / Parásitos)",
        "icon":  "🦠",
        "color": "#ef4444",
        "fuentes": [
            {"manual": "HOLOBIOMAGNETISMO PARTE 1.pdf", "paginas": list(range(25, 32))},
        ],
    },

    "holobiomag": {
        "label": "Holobiomagnético",
        "icon":  "✨",
        "color": "#8b5cf6",
        "fuentes": [
            # Rastreo holobiomagnético - protocolos con tablas de pares emocionales
            {"manual": "HOLOBIOMAGNETISMO PARTE 1.pdf", "paginas": list(range(112, 160))},
        ],
    },

    "flores_bach": {
        "label": "Flores de Bach",
        "icon":  "🌸",
        "color": "#f472b6",
        "fuentes": [
            # Páginas con tablas de flores (identificadas por keyword)
            {"manual": "FLORES DE BACH.pdf",          "paginas": list(range(1, 30))},
            {"manual": "FLORES DE BACH MODULO 3.pdf", "paginas": list(range(1, 20))},
        ],
    },

    "sales": {
        "label": "Sales de Schüssler",
        "icon":  "🧂",
        "color": "#f59e0b",
        "fuentes": [
            {"manual": "HOLOBIOMAGNETISMO PARTE 1.pdf", "paginas": [89, 98, 199, 203, 222, 229]},
            {"manual": "PSICOSOMATRIX.pdf",             "paginas": list(range(14, 20))},
        ],
    },

    "vitaminas": {
        "label": "Vitaminas & Minerales",
        "icon":  "💊",
        "color": "#06b6d4",
        "fuentes": [
            {"manual": "HOLOBIOMAGNETISMO PARTE 1.pdf", "paginas": [13, 79, 387, 460, 584]},
        ],
    },

    "homeopatia": {
        "label": "Homeopatía",
        "icon":  "⚗️",
        "color": "#84cc16",
        "fuentes": [
            {"manual": "HOLOBIOMAGNETISMO PARTE 1.pdf",
             "paginas": [13, 16, 19, 22, 24, 300, 302, 303, 304, 305, 307, 309, 310, 311, 312, 313]},
        ],
    },

    "creencias": {
        "label": "Creencias",
        "icon":  "🧠",
        "color": "#a78bfa",
        "fuentes": [
            {"manual": "PSICOSOMATRIX.pdf", "paginas": [14, 15, 16, 17]},
        ],
    },

    "miedos": {
        "label": "Miedos & Fobias",
        "icon":  "😨",
        "color": "#fb923c",
        "fuentes": [
            {"manual": "PSICOSOMATRIX.pdf", "paginas": [11, 25, 26]},
        ],
    },

    "chakras": {
        "label": "Chakras & Centros Energéticos",
        "icon":  "🔮",
        "color": "#e879f9",
        "fuentes": [
            {"manual": "HOLOBIOMAGNETISMO PARTE 1.pdf",
             "paginas": [138, 144, 157, 158, 160, 161, 162]},
        ],
    },

    "cinco_elementos": {
        "label": "5 Elementos MTC",
        "icon":  "☯️",
        "color": "#34d399",
        "fuentes": [
            {"manual": "MANUAL MTC1.pdf", "paginas": list(range(1, 11))},
            {"manual": "CURSO MTC 1.pdf", "paginas": list(range(1, 15))},
        ],
    },

    "aminoacidos": {
        "label": "Aminoácidos & Enzimas",
        "icon":  "🔬",
        "color": "#60a5fa",
        "fuentes": [
            {"manual": "HOLOBIOMAGNETISMO PARTE 1.pdf", "paginas": [387, 485]},
        ],
    },

    "sei": {
        "label": "SEI (Sanación Energética Integral)",
        "icon":  "⚡",
        "color": "#fbbf24",
        "fuentes": [
            {"manual": "DIPLOMADO SEI 1.pdf", "paginas": list(range(1, 20))},
            {"manual": "DIPLOMADO SEI 2.pdf", "paginas": list(range(1, 20))},
        ],
    },
}


def extraer_paginas(manual_path: Path, paginas: list, out_dir: Path, prefijo: str) -> list:
    if not manual_path.exists():
        print(f"  ⚠️  No encontrado: {manual_path.name}")
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    doc   = fitz.open(str(manual_path))
    total = len(doc)

    archivos = []
    for pg in paginas:
        idx = pg - 1           # 0-indexed
        if idx < 0 or idx >= total:
            continue
        page   = doc[idx]
        mat    = fitz.Matrix(DPI / 72, DPI / 72)
        pix    = page.get_pixmap(matrix=mat, alpha=False)
        nombre = f"{prefijo}_p{pg:04d}.jpg"
        dest   = out_dir / nombre
        if not dest.exists():
            pix.save(str(dest), jpg_quality=88)
        archivos.append(nombre)

    doc.close()
    print(f"  ✅ {manual_path.name}: {len(archivos)} páginas")
    return archivos


def main():
    # Limpiar extracción anterior (que tenía todas las páginas)
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    manifest = {}

    for cat_key, cat_info in TABLAS_MAP.items():
        print(f"\n📂 {cat_info['label']}")
        cat_dir  = OUTPUT_DIR / cat_key
        archivos = []

        for fuente in cat_info["fuentes"]:
            path    = MANUALES_DIR / fuente["manual"]
            prefijo = fuente["manual"].replace(".pdf", "")[:25].replace(" ", "_")
            found   = extraer_paginas(path, fuente["paginas"], cat_dir, prefijo)
            archivos.extend(found)

        manifest[cat_key] = {
            "label":    cat_info["label"],
            "icon":     cat_info["icon"],
            "color":    cat_info["color"],
            "dir":      cat_key,
            "paginas":  len(archivos),
            "archivos": sorted(set(archivos)),
        }

    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    total = sum(v["paginas"] for v in manifest.values())
    print(f"\n✅ Listo — {total} imágenes en {len(manifest)} categorías")
    print(f"   Manifest: {manifest_path}")

    for k, v in manifest.items():
        print(f"   {v['icon']} {v['label']}: {v['paginas']} páginas")


if __name__ == "__main__":
    main()
