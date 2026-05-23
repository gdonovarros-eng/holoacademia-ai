from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrae texto de una carpeta de PDFs y genera respaldos en TXT."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Carpeta que contiene los archivos PDF.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Carpeta de salida para los TXT individuales. Default: <input-dir>/txt_backup",
    )
    parser.add_argument(
        "--combined-output",
        type=Path,
        default=None,
        help="Ruta del TXT consolidado. Default: <input-dir>/respaldo_pdfs.txt",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Omite PDFs que ya tengan TXT individual generado.",
    )
    parser.add_argument(
        "--ocr-fallback",
        action="store_true",
        default=True,
        help="Usa OCR cuando la extracción nativa salga demasiado pobre. Default: activado.",
    )
    parser.add_argument(
        "--ocr-languages",
        default="eng+spa+ita+por+ron",
        help="Idiomas para tesseract cuando se use OCR. Default: eng+spa+ita+por+ron",
    )
    return parser.parse_args()


def sanitize_stem(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', " ", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "documento"


def discover_pdfs(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.glob("*.pdf") if path.is_file())


def extract_pdf_text_with_pypdf(pdf_path: Path) -> tuple[str, int]:
    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages.append(page_text.strip())
    text = "\n\n".join(part for part in pages if part)
    return text.strip(), len(reader.pages)


def extract_pdf_text_with_pdftotext(pdf_path: Path) -> tuple[str, int]:
    pdftotext_bin = shutil.which("pdftotext")
    pdfinfo_bin = shutil.which("pdfinfo")
    if not pdftotext_bin or not pdfinfo_bin:
        raise RuntimeError("pdftotext o pdfinfo no están disponibles.")

    completed = subprocess.run(
        [pdftotext_bin, str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "pdftotext falló.")

    info = subprocess.run(
        [pdfinfo_bin, str(pdf_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if info.returncode != 0:
        raise RuntimeError(info.stderr.strip() or "pdfinfo falló.")

    page_count = 0
    for line in info.stdout.splitlines():
        if line.startswith("Pages:"):
            page_count = int(line.split(":", 1)[1].strip())
            break
    return completed.stdout.strip(), page_count


def extract_pdf_text(pdf_path: Path) -> tuple[str, int, str]:
    errors: list[str] = []

    try:
        text, page_count = extract_pdf_text_with_pdftotext(pdf_path)
        return text, page_count, "pdftotext"
    except Exception as exc:
        errors.append(f"pdftotext: {exc}")

    try:
        text, page_count = extract_pdf_text_with_pypdf(pdf_path)
        return text, page_count, "pypdf"
    except Exception as exc:
        errors.append(f"pypdf: {exc}")

    raise RuntimeError("; ".join(errors))


def needs_ocr(text: str, page_count: int) -> bool:
    normalized = re.sub(r"[\s\f]+", "", text)
    if not normalized:
        return True

    chars_per_page = len(normalized) / max(page_count, 1)
    return len(normalized) < 80 or chars_per_page < 25


def extract_pdf_text_with_ocr(pdf_path: Path, ocr_languages: str) -> tuple[str, int]:
    pdftoppm_bin = shutil.which("pdftoppm")
    tesseract_bin = shutil.which("tesseract")
    if not pdftoppm_bin or not tesseract_bin:
        raise RuntimeError("pdftoppm o tesseract no están disponibles.")

    reader = PdfReader(str(pdf_path))
    page_count = len(reader.pages)
    pages_text: list[str] = []

    with tempfile.TemporaryDirectory(prefix="pdf_ocr_") as temp_dir:
        temp_path = Path(temp_dir)
        image_prefix = temp_path / "page"
        render = subprocess.run(
            [pdftoppm_bin, "-r", "200", "-gray", "-jpeg", str(pdf_path), str(image_prefix)],
            capture_output=True,
            text=True,
            check=False,
        )
        if render.returncode != 0:
            raise RuntimeError(render.stderr.strip() or "pdftoppm falló.")

        for image_path in sorted(temp_path.glob("page-*.jpg")):
            ocr = subprocess.run(
                [tesseract_bin, str(image_path), "stdout", "-l", ocr_languages, "--psm", "6"],
                capture_output=True,
                text=True,
                check=False,
            )
            if ocr.returncode != 0:
                raise RuntimeError(ocr.stderr.strip() or f"Tesseract falló en {image_path.name}.")
            pages_text.append(ocr.stdout.strip())

    text = "\n\n".join(part for part in pages_text if part)
    return text.strip(), page_count


def build_combined_section(pdf_path: Path, text: str, page_count: int) -> str:
    header = [
        "=" * 80,
        f"ARCHIVO: {pdf_path.name}",
        f"PAGINAS: {page_count}",
        "=" * 80,
    ]
    body = text if text else "[Sin texto extraible]"
    return "\n".join(header) + "\n\n" + body + "\n"


def main() -> None:
    args = parse_args()

    if not args.input_dir.exists():
        raise SystemExit(f"No existe la carpeta de entrada: {args.input_dir}")

    output_dir = args.output_dir or (args.input_dir / "txt_backup")
    combined_output = args.combined_output or (args.input_dir / "respaldo_pdfs.txt")

    output_dir.mkdir(parents=True, exist_ok=True)
    combined_output.parent.mkdir(parents=True, exist_ok=True)

    pdf_files = discover_pdfs(args.input_dir)
    if not pdf_files:
        raise SystemExit(f"No encontré PDFs en: {args.input_dir}")

    summary_path = output_dir / "manifest.json"
    summary: list[dict] = []
    combined_sections: list[str] = []

    for index, pdf_path in enumerate(pdf_files, start=1):
        txt_path = output_dir / f"{sanitize_stem(pdf_path.stem)}.txt"
        print(f"[{index}/{len(pdf_files)}] {pdf_path.name}")

        if args.resume and txt_path.exists():
            text = txt_path.read_text(encoding="utf-8")
            page_count = None
            extractor = "existing"
            status = "skipped"
        else:
            try:
                text, page_count, extractor = extract_pdf_text(pdf_path)
                if args.ocr_fallback and needs_ocr(text, page_count):
                    ocr_text, ocr_page_count = extract_pdf_text_with_ocr(pdf_path, args.ocr_languages)
                    if ocr_text:
                        text = ocr_text
                        page_count = ocr_page_count
                        extractor = "ocr"
                txt_path.write_text(text if text else "[Sin texto extraible]\n", encoding="utf-8")
                status = "ok"
            except Exception as exc:
                summary.append(
                    {
                        "pdf": str(pdf_path),
                        "txt": "",
                        "status": "error",
                        "error": str(exc),
                    }
                )
                print(f"  ERROR -> {exc}")
                continue

        combined_sections.append(
            build_combined_section(pdf_path, text, page_count if page_count is not None else 0)
        )
        summary.append(
            {
                "pdf": str(pdf_path),
                "txt": str(txt_path),
                "pages": page_count,
                "extractor": extractor,
                "status": status,
            }
        )
        print(f"  OK ({extractor}) -> {txt_path}")

    combined_output.write_text("\n\n".join(combined_sections).strip() + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    ok_count = sum(1 for item in summary if item["status"] == "ok")
    skipped_count = sum(1 for item in summary if item["status"] == "skipped")
    error_count = sum(1 for item in summary if item["status"] == "error")

    print("\nResumen")
    print(f"  OK: {ok_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Error: {error_count}")
    print(f"  TXT individuales: {output_dir}")
    print(f"  TXT consolidado: {combined_output}")


if __name__ == "__main__":
    main()
