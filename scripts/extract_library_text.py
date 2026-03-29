#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader


TEXT_EXTENSIONS = {".txt", ".md", ".csv"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def relative_output_name(source_name: str) -> str:
    source_path = Path(source_name)
    safe_stem = source_path.stem.replace("/", "-").replace(" ", "_")
    return f"{safe_stem}.txt"


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


def iter_metadata_files(root: Path):
    for path in sorted(root.rglob("metadata.json")):
        if path.is_file():
            yield path


def build_course_manifest(metadata: dict, course_dir: Path, output_course_dir: Path) -> dict:
    return {
        "course_id": metadata["course_id"],
        "course_name": metadata["course_name"],
        "linea": metadata["linea"],
        "tipo": metadata["tipo"],
        "audiencia": metadata.get("audiencia", "Alumnos"),
        "idioma": metadata.get("idioma", "es"),
        "source_course_dir": str(course_dir),
        "output_course_dir": str(output_course_dir),
        "sources": [],
    }


def process_course(metadata_path: Path, output_root: Path) -> Path:
    metadata = load_json(metadata_path)
    course_dir = metadata_path.parent
    output_course_dir = output_root / metadata["linea"] / metadata["course_id"]
    sources_dir = output_course_dir / "sources"
    ensure_dir(sources_dir)

    manifest = build_course_manifest(metadata, course_dir, output_course_dir)

    for idx, source in enumerate(metadata.get("fuentes", []), start=1):
        source_file = course_dir / source["archivo"]
        if not source_file.exists():
            manifest["sources"].append(
                {
                    "source_id": f"{metadata['course_id']}-source-{idx:03d}",
                    "tipo": source["tipo"],
                    "archivo_original": source["archivo"],
                    "source_path": str(source_file),
                    "status": "missing",
                }
            )
            continue

        output_name = relative_output_name(source["archivo"])
        output_text_path = sources_dir / output_name
        result = extract_source_text(source_file, output_text_path)

        manifest["sources"].append(
            {
                "source_id": f"{metadata['course_id']}-source-{idx:03d}",
                "tipo": source["tipo"],
                "archivo_original": source["archivo"],
                "source_path": str(source_file),
                "text_path": str(output_text_path),
                "status": "ok",
                "extraction_method": result["method"],
                "chars": result["chars"],
            }
        )

    manifest_path = output_course_dir / "course_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def copy_metadata_files(input_root: Path, output_root: Path) -> None:
    catalog = []
    for metadata_path in iter_metadata_files(input_root):
        metadata = load_json(metadata_path)
        catalog.append(
            {
                "course_id": metadata["course_id"],
                "course_name": metadata["course_name"],
                "linea": metadata["linea"],
                "tipo": metadata["tipo"],
                "metadata_path": str(metadata_path),
            }
        )
    ensure_dir(output_root)
    (output_root / "catalog.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extrae PDFs y textos de la biblioteca a una salida procesada."
    )
    parser.add_argument("input_root", type=Path, help="Ruta de la biblioteca fuente")
    parser.add_argument("output_root", type=Path, help="Ruta de salida procesada")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Borra la salida previa antes de regenerar",
    )
    args = parser.parse_args()

    input_root = args.input_root.expanduser().resolve()
    output_root = args.output_root.expanduser().resolve()

    if args.clean and output_root.exists():
        shutil.rmtree(output_root)

    ensure_dir(output_root)
    copy_metadata_files(input_root, output_root)

    manifest_paths = []
    for metadata_path in iter_metadata_files(input_root):
        manifest_path = process_course(metadata_path, output_root)
        manifest_paths.append(str(manifest_path))

    print(json.dumps({"processed_courses": len(manifest_paths), "manifests": manifest_paths}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
