#!/usr/bin/env python3
"""Extract emails or domains from CSV/XLSX files and split them into small files."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile


EMAIL_PATTERN = re.compile(r"(?i)\b[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}\b")
DOMAIN_PATTERN = re.compile(r"(?i)\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b")
EMAIL_HEADER_ALIASES = {
    "email",
    "email address",
    "emailaddress",
    "e-mail",
    "mail",
    "correo",
    "correo electronico",
    "correo electrónico",
    "direccion de correo",
    "dirección de correo",
    "dirección de correo electrónico",
}
XML_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def normalize_header(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def clean_cell_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def extract_matches(text: str, allow_domains: bool) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    for email in EMAIL_PATTERN.findall(text):
        normalized = email.lower()
        if normalized not in seen:
            seen.add(normalized)
            found.append(normalized)

    if allow_domains:
        for domain in DOMAIN_PATTERN.findall(text):
            normalized = domain.lower()
            if "@" in normalized or normalized in seen:
                continue
            seen.add(normalized)
            found.append(normalized)

    return found


def find_email_column(headers: list[str], requested: str | None) -> int | None:
    normalized_headers = [normalize_header(header) for header in headers]

    if requested:
        target = normalize_header(requested)
        for index, header in enumerate(normalized_headers):
            if header == target:
                return index
        return None

    for index, header in enumerate(normalized_headers):
        if header in EMAIL_HEADER_ALIASES:
            return index

    return None


def iter_contacts_from_csv(path: Path, requested_column: str | None, allow_domains: bool) -> Iterable[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        if sample:
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
        else:
            dialect = csv.excel
        reader = csv.reader(handle, dialect)
        rows = iter(reader)
        headers = next(rows, [])
        email_col = find_email_column(headers, requested_column)

        for row in rows:
            cells = [clean_cell_text(cell) for cell in row]
            if email_col is not None and email_col < len(cells):
                sources = [cells[email_col]]
            else:
                sources = cells
            for source in sources:
                for contact in extract_matches(source, allow_domains):
                    yield contact


def read_shared_strings(book: ZipFile) -> list[str]:
    try:
        raw = book.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    root = ET.fromstring(raw)
    values: list[str] = []
    for item in root.findall("main:si", XML_NS):
        text_parts = [node.text or "" for node in item.findall(".//main:t", XML_NS)]
        values.append("".join(text_parts))
    return values


def workbook_sheet_targets(book: ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(book.read("xl/workbook.xml"))
    rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        node.attrib["Id"]: node.attrib["Target"]
        for node in rels.findall("pkg:Relationship", XML_NS)
        if "Id" in node.attrib and "Target" in node.attrib
    }

    targets: list[tuple[str, str]] = []
    for sheet in workbook.findall("main:sheets/main:sheet", XML_NS):
        name = sheet.attrib.get("name", "Sheet")
        rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        if not rel_id or rel_id not in rel_map:
            continue
        target = rel_map[rel_id].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        targets.append((name, target))
    return targets


def read_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", XML_NS))

    value_node = cell.find("main:v", XML_NS)
    if value_node is None or value_node.text is None:
        return ""

    raw_value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (ValueError, IndexError):
            return ""
    return raw_value


def column_index_from_ref(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha()).upper()
    index = 0
    for char in letters:
        index = (index * 26) + (ord(char) - ord("A") + 1)
    return max(index - 1, 0)


def iter_sheet_rows(book: ZipFile, sheet_target: str, shared_strings: list[str]) -> Iterable[list[str]]:
    sheet = ET.fromstring(book.read(sheet_target))
    for row in sheet.findall("main:sheetData/main:row", XML_NS):
        values: list[str] = []
        for cell in row.findall("main:c", XML_NS):
            cell_ref = cell.attrib.get("r", "")
            col_index = column_index_from_ref(cell_ref) if cell_ref else len(values)
            while len(values) < col_index:
                values.append("")
            values.append(clean_cell_text(read_cell_value(cell, shared_strings)))
        if any(values):
            yield values


def resolve_sheet(path: Path, sheet_selector: str | None) -> tuple[str, list[list[str]]]:
    with ZipFile(path) as book:
        shared_strings = read_shared_strings(book)
        sheets = workbook_sheet_targets(book)
        if not sheets:
            raise ValueError("No se encontraron hojas en el archivo Excel.")

        selected_name: str
        selected_target: str
        if sheet_selector is None:
            selected_name, selected_target = sheets[0]
        elif sheet_selector.isdigit():
            index = int(sheet_selector) - 1
            if index < 0 or index >= len(sheets):
                raise ValueError(f"La hoja {sheet_selector} no existe. Hay {len(sheets)} hoja(s).")
            selected_name, selected_target = sheets[index]
        else:
            matches = [sheet for sheet in sheets if normalize_header(sheet[0]) == normalize_header(sheet_selector)]
            if not matches:
                names = ", ".join(name for name, _ in sheets)
                raise ValueError(f"No encontré la hoja '{sheet_selector}'. Hojas disponibles: {names}")
            selected_name, selected_target = matches[0]

        rows = list(iter_sheet_rows(book, selected_target, shared_strings))
        return selected_name, rows


def iter_contacts_from_xlsx(
    path: Path,
    requested_column: str | None,
    allow_domains: bool,
    sheet_selector: str | None,
) -> Iterable[str]:
    sheet_name, rows = resolve_sheet(path, sheet_selector)
    if not rows:
        raise ValueError(f"La hoja '{sheet_name}' está vacía.")

    headers = rows[0]
    email_col = find_email_column(headers, requested_column)

    for row in rows[1:]:
        if email_col is not None and email_col < len(row):
            sources = [row[email_col]]
        else:
            sources = row
        for source in sources:
            for contact in extract_matches(source, allow_domains):
                yield contact


def unique_preserving_order(values: Iterable[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            results.append(value)
    return results


def chunk_for_csv(contacts: list[str], base_name: str, output_dir: Path, max_bytes: int) -> list[Path]:
    files: list[Path] = []
    part = 1
    header = "email\n".encode("utf-8")
    current_size = len(header)
    current_rows: list[str] = []

    def flush() -> None:
        nonlocal files, part, current_size, current_rows
        if not current_rows:
            return
        out_path = output_dir / f"{base_name}_part{part:03d}.csv"
        with out_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["email"])
            for contact in current_rows:
                writer.writerow([contact])
        files.append(out_path)
        part += 1
        current_rows = []
        current_size = len(header)

    for contact in contacts:
        row_size = len(f"{contact}\n".encode("utf-8"))
        if current_rows and current_size + row_size > max_bytes:
            flush()
        current_rows.append(contact)
        current_size += row_size

    flush()
    return files


def chunk_for_json(contacts: list[str], base_name: str, output_dir: Path, max_bytes: int) -> list[Path]:
    files: list[Path] = []
    chunk: list[str] = []
    part = 1

    def payload_size(items: list[str]) -> int:
        return len(json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"))

    for contact in contacts:
        candidate = chunk + [contact]
        if chunk and payload_size(candidate) > max_bytes:
            out_path = output_dir / f"{base_name}_part{part:03d}.json"
            out_path.write_text(json.dumps(chunk, ensure_ascii=False, indent=2), encoding="utf-8")
            files.append(out_path)
            part += 1
            chunk = [contact]
        else:
            chunk = candidate

    if chunk:
        out_path = output_dir / f"{base_name}_part{part:03d}.json"
        out_path.write_text(json.dumps(chunk, ensure_ascii=False, indent=2), encoding="utf-8")
        files.append(out_path)

    return files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convierte un archivo CSV/XLSX a varios archivos CSV o JSON pequenos para Amazon SES."
    )
    parser.add_argument("input_file", help="Ruta al archivo .xlsx o .csv")
    parser.add_argument(
        "--output-dir",
        default="tmp/contact_chunks",
        help="Carpeta donde se guardaran los archivos divididos",
    )
    parser.add_argument(
        "--format",
        choices=("csv", "json"),
        default="csv",
        help="Formato de salida",
    )
    parser.add_argument(
        "--sheet",
        help="Nombre de la hoja o numero (1, 2, 3...) si el origen es Excel",
    )
    parser.add_argument(
        "--email-column",
        help="Nombre exacto de la columna que contiene los correos, por ejemplo 'Email' o 'Correo'",
    )
    parser.add_argument(
        "--max-mb",
        type=float,
        default=9.5,
        help="Tamano maximo por archivo de salida. Default: 9.5 MB",
    )
    parser.add_argument(
        "--allow-domains",
        action="store_true",
        help="Tambien extrae dominios sueltos, no solo correos",
    )
    return parser.parse_args()


def load_contacts(args: argparse.Namespace) -> list[str]:
    path = Path(args.input_file)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        values = iter_contacts_from_csv(path, args.email_column, args.allow_domains)
    elif suffix == ".xlsx":
        values = iter_contacts_from_xlsx(path, args.email_column, args.allow_domains, args.sheet)
    else:
        raise ValueError("Formato no soportado. Usa .csv o .xlsx")

    contacts = unique_preserving_order(values)
    if not contacts:
        raise ValueError("No encontré correos en el archivo. Revisa la hoja o el nombre de la columna.")
    return contacts


def main() -> int:
    args = parse_args()

    try:
        contacts = load_contacts(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    max_bytes = int(args.max_mb * 1024 * 1024)
    base_name = Path(args.input_file).stem

    if args.format == "csv":
        files = chunk_for_csv(contacts, base_name, output_dir, max_bytes)
    else:
        files = chunk_for_json(contacts, base_name, output_dir, max_bytes)

    print(f"Contactos unicos encontrados: {len(contacts)}")
    print(f"Archivos generados: {len(files)}")
    for out_path in files:
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"- {out_path} ({size_mb:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
