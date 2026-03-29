#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path


LINE_NAMES = {
    "Desarrollo Personal": "Desarrollo Personal",
    "Diplomados": "Diplomados",
    "Mística": "Mística",
    "Mística": "Mística",
    "Salud": "Salud",
    "Wellnes": "Wellnes",
}

COURSE_OVERRIDES = {
    "ANCESTROS_Y_RAICES": {
        "course_name": "Diplomado Ancestros y Raíces",
        "tipo": "Diplomado",
    },
    "SANACION_ENERGETICA_INTEGRAL": {
        "course_name": "Diplomado Sanación Energética Integral",
        "tipo": "Diplomado",
    },
    "TERAPIA_HOLISTICA_1": {
        "course_name": "Diplomado Terapia Holística 1",
        "tipo": "Diplomado",
    },
    "TERAPIA_HOLISTICA_2": {
        "course_name": "Diplomado Terapia Holística 2",
        "tipo": "Diplomado",
    },
    "NUMERHOLOGIA": {
        "course_name": "Curso Numerhología",
        "tipo": "Curso",
    },
    "TALLER_NUMEROLOGIA": {
        "course_name": "Taller Numerología",
        "tipo": "Taller",
    },
    "HOLOBIOMAGNETISMO_2021": {
        "course_name": "Curso Holobiomagnetismo 2021",
        "tipo": "Curso",
    },
    "HOLOBIOMAGNETISMO_PARTE_1": {
        "course_name": "Curso Holobiomagnetismo Parte 1",
        "tipo": "Curso",
    },
    "HOLOBIOMAGNETISMO_PARTE_2": {
        "course_name": "Curso Holobiomagnetismo Parte 2",
        "tipo": "Curso",
    },
    "HOLOPSICOSOMATICA_2020": {
        "course_name": "Holopsicosomática 2020",
        "tipo": "Curso",
    },
    "MEDICINA_ENERGÉTICA": {
        "course_name": "Medicina Energética",
        "tipo": "Curso",
    },
    "PSICOSOMATICA_Y_BIODESCODIFICACIÓN_1": {
        "course_name": "Curso Psicosomática y Biodescodificación 1",
        "tipo": "Curso",
    },
    "PSICOSOMATICA_Y_BIODESCODIFICACIÓN_2": {
        "course_name": "Curso Psicosomática y Biodescodificación 2",
        "tipo": "Curso",
    },
    "PSICOSOMATRIX": {
        "course_name": "Psicosomatrix",
        "tipo": "Curso",
    },
    "TALLER_MEDICINA_NATURISTA": {
        "course_name": "Taller Medicina Naturista",
        "tipo": "Taller",
    },
}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = ascii_value.lower().replace("&", " y ")
    cleaned = []
    previous_dash = False
    for char in slug:
        if char.isalnum():
            cleaned.append(char)
            previous_dash = False
        else:
            if not previous_dash:
                cleaned.append("-")
                previous_dash = True
    return "".join(cleaned).strip("-")


def infer_source_type(file_path: Path) -> str:
    lower_name = file_path.name.casefold()
    if "transcripcion" in lower_name:
        return "transcripcion"
    if file_path.suffix.lower() == ".csv":
        return "indice"
    if "guia" in lower_name:
        return "guia"
    if "protocolo" in lower_name or "protocolos" in lower_name:
        return "protocolo"
    return "manual"


def infer_course_info(line_name: str, course_dir_name: str) -> dict[str, str]:
    if course_dir_name in COURSE_OVERRIDES:
        override = COURSE_OVERRIDES[course_dir_name]
        return {
            "course_name": override["course_name"],
            "tipo": override["tipo"],
            "linea": line_name,
            "course_id": slugify(override["course_name"]),
        }

    pretty_name = course_dir_name.replace("_", " ").title()
    return {
        "course_name": pretty_name,
        "tipo": "Curso",
        "linea": line_name,
        "course_id": slugify(pretty_name),
    }


def build_metadata(course_dir: Path) -> dict:
    line_name = LINE_NAMES.get(course_dir.parent.name, course_dir.parent.name)
    course_info = infer_course_info(line_name, course_dir.name)

    sources = []
    for file_path in sorted(course_dir.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.name in {".DS_Store", "metadata.json"}:
            continue
        sources.append(
            {
                "tipo": infer_source_type(file_path),
                "archivo": file_path.name,
            }
        )

    return {
        "course_id": course_info["course_id"],
        "course_name": course_info["course_name"],
        "linea": course_info["linea"],
        "tipo": course_info["tipo"],
        "audiencia": "Alumnos",
        "idioma": "es",
        "fuentes": sources,
    }


def iter_course_dirs(root: Path):
    for line_dir in sorted(root.iterdir()):
        if not line_dir.is_dir():
            continue
        for course_dir in sorted(line_dir.iterdir()):
            if course_dir.is_dir():
                yield course_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera metadata.json para cada curso dentro de una biblioteca."
    )
    parser.add_argument("root", type=Path, help="Ruta raíz de la biblioteca")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Imprime el plan sin escribir archivos",
    )
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"No existe la ruta: {root}")

    generated = []
    for course_dir in iter_course_dirs(root):
        metadata = build_metadata(course_dir)
        target_path = course_dir / "metadata.json"
        if args.dry_run:
            generated.append({"path": str(target_path), "metadata": metadata})
            continue

        target_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        generated.append(str(target_path))

    if args.dry_run:
        print(json.dumps(generated, indent=2, ensure_ascii=False))
    else:
        for item in generated:
            print(item)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
