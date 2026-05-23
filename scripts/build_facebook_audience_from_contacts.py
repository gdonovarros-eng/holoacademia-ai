#!/usr/bin/env python3
"""Build a Facebook custom audience CSV from many CSV/XLSX contact files."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from split_contact_list import iter_contacts_from_csv, iter_contacts_from_xlsx, unique_preserving_order


SUPPORTED_SUFFIXES = {".csv", ".xlsx"}
SKIP_NAMES = {
    ".ds_store",
    "sample-file.csv",
    "example_value_based_messaging_contacts_file.csv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Une bases de datos, deduplica correos y las exporta al formato CSV de ejemplo de Facebook."
    )
    parser.add_argument(
        "input_paths",
        nargs="+",
        help="Archivos o carpetas con listas CSV/XLSX",
    )
    parser.add_argument(
        "--sample-file",
        required=True,
        help="CSV de ejemplo de Facebook para tomar encabezados",
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Ruta del CSV final listo para subir a Facebook",
    )
    return parser.parse_args()


def should_skip(path: Path) -> bool:
    name = path.name.lower()
    if name.startswith("~$"):
        return True
    return name in SKIP_NAMES


def gather_files(inputs: list[str]) -> list[Path]:
    discovered: list[Path] = []
    seen: set[Path] = set()

    for raw_path in inputs:
        path = Path(raw_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"No existe la ruta: {path}")

        if path.is_file():
            candidates = [path]
        else:
            candidates = sorted(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES
            )

        for candidate in candidates:
            if should_skip(candidate):
                continue
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                discovered.append(candidate)

    if not discovered:
        raise ValueError("No encontre archivos CSV/XLSX utiles en las rutas indicadas.")

    return discovered


def iter_contacts(files: list[Path]):
    for path in files:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            yield from iter_contacts_from_csv(path, requested_column=None, allow_domains=False)
        elif suffix == ".xlsx":
            yield from iter_contacts_from_xlsx(
                path,
                requested_column=None,
                allow_domains=False,
                sheet_selector=None,
            )


def load_sample_headers(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        headers = next(reader, [])
    if not headers:
        raise ValueError(f"El archivo de ejemplo no tiene encabezados: {path}")
    normalized = [header.strip() for header in headers]
    if "email" not in {header.lower() for header in normalized}:
        raise ValueError("El archivo de ejemplo de Facebook no contiene la columna email.")
    return normalized


def write_output(path: Path, headers: list[str], emails: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for email in emails:
            row = {header: "" for header in headers}
            row["email"] = email
            writer.writerow(row)


def main() -> int:
    args = parse_args()

    sample_path = Path(args.sample_file).expanduser()
    output_path = Path(args.output_file).expanduser()

    try:
        files = gather_files(args.input_paths)
        headers = load_sample_headers(sample_path)
        emails = unique_preserving_order(iter_contacts(files))
        if not emails:
            raise ValueError("No se encontraron correos al revisar los archivos indicados.")
        write_output(output_path, headers, emails)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Archivos procesados: {len(files)}")
    print(f"Correos unicos: {len(emails)}")
    print(f"Salida: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
