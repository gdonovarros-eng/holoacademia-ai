#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

from pypdf import PdfReader


TEXT_EXTENSIONS = {".txt", ".md", ".csv"}

CATEGORY_RULES = [
    ("disease_dictionary", ["diccionario", "enfermedad", "biodescodificacion", "psicodescodificacion", "descodificacion", "mi cuerpo para curarme"]),
    ("transgenerational", ["antepasados", "yaciente", "amores", "hellinger", "constelaciones", "ordenes_del_amor", "órdenes_del_amor"]),
    ("trauma_emotion_release", ["tapping", "emocion", "emoción", "trauma", "corte de cordones", "cordones energeticos", "cordones energéticos"]),
    ("belief_consciousness", ["biologia de la creencia", "biología de la creencia", "observador", "memoria en las celulas", "memoria en las células", "doble"]),
    ("complementary_misc", ["tarot", "grabovoi"]),
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = ascii_value.lower().replace("&", " y ")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def normalize_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", ascii_value).strip()


def classify_category(filename: str) -> str:
    lowered = normalize_name(filename)
    for category, needles in CATEGORY_RULES:
        if any(needle in lowered for needle in needles):
            return category
    return "uncategorized"


def extract_pdf_with_pdftotext(source_path: Path, target_path: Path) -> bool:
    command = ["pdftotext", "-layout", str(source_path), str(target_path)]
    completed = subprocess.run(command, capture_output=True, text=True)
    return completed.returncode == 0 and target_path.exists()


def extract_pdf_with_pypdf(source_path: Path, target_path: Path) -> None:
    reader = PdfReader(str(source_path))
    pages = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages.append(page_text.strip())
    target_path.write_text("\n\n".join(filter(None, pages)) + "\n", encoding="utf-8")


def extract_source_text(source_path: Path, target_path: Path) -> dict:
    suffix = source_path.suffix.lower()
    ensure_dir(target_path.parent)

    if suffix in TEXT_EXTENSIONS:
        text = source_path.read_text(encoding="utf-8", errors="ignore")
        target_path.write_text(text, encoding="utf-8")
        return {"method": "copy_text", "chars": len(text)}

    if suffix == ".pdf":
        if not extract_pdf_with_pdftotext(source_path, target_path):
            extract_pdf_with_pypdf(source_path, target_path)
            method = "pypdf"
        else:
            method = "pdftotext"
        text = target_path.read_text(encoding="utf-8", errors="ignore")
        return {"method": method, "chars": len(text)}

    raise ValueError(f"Formato no soportado: {source_path.suffix}")


def infer_source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf_book"
    if suffix in TEXT_EXTENSIONS:
        return "text_reference"
    return "other"


def iter_reference_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != ".DS_Store":
            yield path


def process_reference_library(input_root: Path, output_root: Path) -> dict:
    ensure_dir(output_root)
    text_root = output_root / "texts"
    ensure_dir(text_root)

    catalog = []
    counts_by_category: dict[str, int] = {}

    for idx, source_path in enumerate(iter_reference_files(input_root), start=1):
        category = classify_category(source_path.name)
        counts_by_category[category] = counts_by_category.get(category, 0) + 1

        source_slug = slugify(source_path.stem)
        target_text_path = text_root / category / f"{source_slug}.txt"
        result = extract_source_text(source_path, target_text_path)

        catalog.append(
            {
                "reference_id": f"reference-{idx:03d}",
                "title": source_path.stem,
                "category": category,
                "source_type": infer_source_type(source_path),
                "source_path": str(source_path),
                "text_path": str(target_text_path),
                "extraction_method": result["method"],
                "chars": result["chars"],
            }
        )

    catalog_path = output_root / "catalog.json"
    catalog_path.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    summary = {
        "input_root": str(input_root),
        "output_root": str(output_root),
        "references_processed": len(catalog),
        "counts_by_category": counts_by_category,
        "catalog_path": str(catalog_path),
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extrae y clasifica la biblioteca de referencia a texto procesado."
    )
    parser.add_argument("input_root", type=Path, help="Ruta de la biblioteca de referencia")
    parser.add_argument("output_root", type=Path, help="Ruta de salida procesada")
    parser.add_argument("--clean", action="store_true", help="Borra la salida previa")
    args = parser.parse_args()

    input_root = args.input_root.expanduser().resolve()
    output_root = args.output_root.expanduser().resolve()

    if args.clean and output_root.exists():
        shutil.rmtree(output_root)

    summary = process_reference_library(input_root, output_root)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
