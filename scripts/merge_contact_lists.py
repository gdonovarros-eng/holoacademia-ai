#!/usr/bin/env python3
"""Merge many contact files into deduplicated CSV or JSON chunks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from split_contact_list import (
    chunk_for_csv,
    chunk_for_json,
    iter_contacts_from_csv,
    iter_contacts_from_xlsx,
    unique_preserving_order,
)


SUPPORTED_SUFFIXES = {".csv", ".xlsx"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fusiona multiples archivos de contactos y genera lotes deduplicados."
    )
    parser.add_argument(
        "input_paths",
        nargs="+",
        help="Archivos o carpetas que contienen listas .csv o .xlsx",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Carpeta donde se guardaran los lotes finales",
    )
    parser.add_argument(
        "--base-name",
        default="lista",
        help="Prefijo de los archivos de salida, por ejemplo lista",
    )
    parser.add_argument(
        "--format",
        choices=("csv", "json"),
        default="csv",
        help="Formato de salida",
    )
    parser.add_argument(
        "--max-mb",
        type=float,
        default=9.0,
        help="Tamano maximo por archivo de salida. Default: 9.0 MB",
    )
    parser.add_argument(
        "--allow-domains",
        action="store_true",
        help="Tambien extrae dominios sueltos, no solo correos",
    )
    return parser.parse_args()


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
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                discovered.append(candidate)

    if not discovered:
        raise ValueError("No encontré archivos .csv o .xlsx en las rutas indicadas.")

    return discovered


def iter_contacts(files: list[Path], allow_domains: bool):
    for path in files:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            yield from iter_contacts_from_csv(path, requested_column=None, allow_domains=allow_domains)
        elif suffix == ".xlsx":
            yield from iter_contacts_from_xlsx(
                path,
                requested_column=None,
                allow_domains=allow_domains,
                sheet_selector=None,
            )


def rename_sequential(files: list[Path], output_dir: Path, base_name: str, fmt: str) -> list[Path]:
    renamed: list[Path] = []
    for index, path in enumerate(sorted(files), start=1):
        target = output_dir / f"{base_name}{index}.{fmt}"
        if path != target:
            path.rename(target)
        renamed.append(target)
    return renamed


def main() -> int:
    args = parse_args()

    try:
        files = gather_files(args.input_paths)
        contacts = unique_preserving_order(iter_contacts(files, allow_domains=args.allow_domains))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not contacts:
        print("Error: No encontré correos en los archivos indicados.", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    max_bytes = int(args.max_mb * 1024 * 1024)

    if args.format == "csv":
        generated = chunk_for_csv(contacts, args.base_name, output_dir, max_bytes)
    else:
        generated = chunk_for_json(contacts, args.base_name, output_dir, max_bytes)

    final_files = rename_sequential(generated, output_dir, args.base_name, args.format)

    print(f"Archivos procesados: {len(files)}")
    print(f"Contactos unicos totales: {len(contacts)}")
    print(f"Lotes generados: {len(final_files)}")
    for out_path in final_files:
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"- {out_path} ({size_mb:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
