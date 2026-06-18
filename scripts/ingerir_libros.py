#!/usr/bin/env python3
"""Ingiere libros de referencia (PDF / txt / md) al índice del Library KB.

Para reforzar disciplinas concretas (p. ej. Biodescodificación) con libros
específicos. Extrae -> (OCR si el PDF es escaneado) -> trocea -> embebe ->
anexa al índice con source_type 'libro' (fuente prioritaria).

Guardado POR LIBRO: incremental y reanudable (si se corta, re-correr salta los
libros ya hechos). Idempotente.

Uso:
  python3.14 scripts/ingerir_libros.py --dir "/ruta/libros" --coleccion "Biodescodificación"
  python3.14 scripts/ingerir_libros.py --file "/ruta/libro.pdf" --coleccion "Biodescodificación"
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys, unicodedata
import numpy as np

ROOT = "/Users/m2/Projects/holoacademia-ai"
CHUNKS = f"{ROOT}/data/chunks/library_chunks.jsonl"
VECTORS = f"{ROOT}/data/embeddings/library_vectors.npy"
EMBED_MODEL = "text-embedding-3-small"
CHUNK_TARGET = 1400
HARD_MAX = 3500          # tope duro por chunk (chars) — seguro bajo 8192 tokens
OCR_LANG = "spa"
os.environ.setdefault("TESSDATA_PREFIX", "/opt/homebrew/share/tessdata")

for line in open(f"{ROOT}/.env"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip()
from openai import OpenAI
_emb = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def _slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def extraer(path):
    ext = path.lower().rsplit(".", 1)[-1]
    if ext in ("txt", "md"):
        return open(path, encoding="utf-8", errors="ignore").read()
    if ext == "pdf":
        import fitz
        doc = fitz.open(path)
        partes, ocr_paginas = [], 0
        for page in doc:
            t = page.get_text()
            if len(t.strip()) < 40:           # página sin capa de texto -> OCR
                try:
                    tp = page.get_textpage_ocr(language=OCR_LANG, dpi=200, full=True)
                    t = page.get_text(textpage=tp)
                    ocr_paginas += 1
                except Exception:
                    pass
            partes.append(t)
        if ocr_paginas:
            print(f"    (OCR aplicado a {ocr_paginas} páginas)", flush=True)
        return "\n".join(partes)
    return ""


def limpiar(t):
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
    t = re.sub(r"\n\s*\d+\s*\n", "\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n\n", t)
    return t.strip()


def trozos(t, target=CHUNK_TARGET, overlap=150, hard_max=HARD_MAX):
    t = re.sub(r"\s+", " ", t)
    # partir en frases; las frases gigantes (índices, tablas sin puntos) se cortan duro
    frases = []
    for f in re.split(r"(?<=[.!?])\s+", t):
        while len(f) > hard_max:
            frases.append(f[:hard_max]); f = f[hard_max - overlap:]
        if f:
            frases.append(f)
    out, cur = [], ""
    for f in frases:
        if len(cur) + len(f) + 1 <= target:
            cur = f"{cur} {f}".strip()
        else:
            if cur:
                out.append(cur)
            cur = f
    if cur:
        out.append(cur)
    return [c for c in out if len(c) > 120]


def _append(registros):
    vecs = []
    for s in range(0, len(registros), 256):
        batch = registros[s:s+256]
        r = _emb.embeddings.create(model=EMBED_MODEL, input=[x["text"] for x in batch])
        for e in r.data:
            v = np.array(e.embedding, dtype=np.float32); v = v / (np.linalg.norm(v) or 1.0)
            vecs.append(v)
    nuevos = np.vstack(vecs).astype(np.float32)
    viejos = np.load(VECTORS)
    combinado = np.vstack([viejos, nuevos]).astype(np.float32)
    tmp = VECTORS + ".tmp.npy"
    np.save(tmp, combinado); os.replace(tmp, VECTORS)
    with open(CHUNKS, "a") as fh:
        for reg in registros:
            fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
    return combinado.shape[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--file")
    ap.add_argument("--coleccion", required=True)
    ap.add_argument("--linea", default="Libros de referencia")
    a = ap.parse_args()

    if a.file:
        files = [a.file]
    elif a.dir:
        files = sorted([p for p in glob.glob(os.path.join(a.dir, "**", "*"), recursive=True)
                        if p.lower().rsplit(".", 1)[-1] in ("pdf", "txt", "md")])
    else:
        sys.exit("Da --dir o --file")
    if not files:
        sys.exit("Sin libros (.pdf/.txt/.md)")

    col_id = _slug(a.coleccion)
    existentes = set()
    for ln in open(CHUNKS):
        try: existentes.add(json.loads(ln)["chunk_id"])
        except Exception: pass

    total_chunks, hechos, vacios = 0, 0, []
    for fpath in files:
        titulo = os.path.splitext(os.path.basename(fpath))[0]
        bid = _slug(titulo)
        if f"libro-{col_id}::{bid}::0000" in existentes:
            print(f"= ya estaba, salto: {titulo}", flush=True); continue
        print(f"extrayendo: {titulo}", flush=True)
        try:
            chunks = trozos(limpiar(extraer(fpath)))
        except Exception as e:
            print(f"  ! error extrayendo {titulo}: {e}", flush=True); continue
        if not chunks:
            vacios.append(titulo); print(f"  sin texto (¿imagen sin OCR?): {titulo}", flush=True); continue
        registros = [{
            "chunk_id": f"libro-{col_id}::{bid}::{i:04d}", "course_id": f"libros-{col_id}",
            "course_name": a.coleccion, "linea": a.linea, "tipo": "Libro",
            "audiencia": "Terapeutas", "idioma": "es", "source_id": f"libro-{bid}",
            "source_type": "libro", "source_file": os.path.basename(fpath),
            "heading": titulo, "text": ch, "char_count": len(ch),
        } for i, ch in enumerate(chunks)]
        idx_total = _append(registros)
        total_chunks += len(registros); hechos += 1
        print(f"  + {titulo}: {len(registros)} chunks (índice: {idx_total})", flush=True)

    print(f"\nLISTO: {hechos} libros, +{total_chunks} chunks.", flush=True)
    if vacios:
        print(f"Sin texto extraíble ({len(vacios)}): " + "; ".join(vacios), flush=True)


if __name__ == "__main__":
    main()
