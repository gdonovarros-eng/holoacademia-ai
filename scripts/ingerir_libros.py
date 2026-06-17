#!/usr/bin/env python3
"""Ingiere libros de referencia (PDF / txt / md) al índice del Library KB.

Pensado para reforzar disciplinas concretas (p. ej. Biodescodificación) con
libros específicos. Los libros son texto limpio, así que NO pasan por la
curación con IA: solo extracción -> troceo -> embeddings -> índice.

Se marcan con source_type 'libro' (fuente prioritaria en la recuperación).

Uso:
  python3.14 scripts/ingerir_libros.py \
      --dir "/ruta/a/carpeta_de_libros" \
      --coleccion "Biodescodificación" \
      --linea "Libros de referencia"

  # o un solo archivo:
  python3.14 scripts/ingerir_libros.py --file "/ruta/libro.pdf" --coleccion "Biodescodificación"

  # opcional: --curar  (limpia con IA; útil solo si el PDF es escaneo sucio)
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys, unicodedata
import numpy as np

ROOT = "/Users/m2/Projects/holoacademia-ai"
CHUNKS = f"{ROOT}/data/chunks/library_chunks.jsonl"
VECTORS = f"{ROOT}/data/embeddings/library_vectors.npy"
EMBED_MODEL = "text-embedding-3-small"
CHUNK_TARGET = 1400

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
    if ext == "pdf":
        import fitz
        doc = fitz.open(path)
        return "\n".join(p.get_text() for p in doc)
    if ext in ("txt", "md"):
        return open(path, encoding="utf-8", errors="ignore").read()
    return ""


def limpiar(t):
    # une cortes de línea de palabras, quita números de página sueltos y espacios
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)          # palabra cortada por salto de línea
    t = re.sub(r"\n\s*\d+\s*\n", "\n", t)            # números de página solos
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n\n", t)
    return t.strip()


def trozos(t, target=CHUNK_TARGET, overlap=150):
    out, cur = [], ""
    for frase in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", t)):
        if len(cur) + len(frase) + 1 <= target:
            cur = f"{cur} {frase}".strip()
        else:
            if cur: out.append(cur)
            cur = (cur[-overlap:] + " " + frase) if cur else frase
    if cur: out.append(cur)
    return [c for c in out if len(c) > 120]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--file")
    ap.add_argument("--coleccion", required=True, help="Etiqueta de colección, p. ej. 'Biodescodificación'")
    ap.add_argument("--linea", default="Libros de referencia")
    ap.add_argument("--curar", action="store_true", help="Limpiar con IA (solo si el PDF es escaneo sucio)")
    a = ap.parse_args()

    if a.file:
        files = [a.file]
    elif a.dir:
        files = sorted([p for p in glob.glob(os.path.join(a.dir, "**", "*"), recursive=True)
                        if p.lower().rsplit(".", 1)[-1] in ("pdf", "txt", "md")])
    else:
        sys.exit("Da --dir o --file")
    if not files:
        sys.exit("Sin libros (.pdf/.txt/.md) en la ruta")

    col_id = _slug(a.coleccion)
    existentes = set()
    for ln in open(CHUNKS):
        try: existentes.add(json.loads(ln)["chunk_id"])
        except Exception: pass

    registros = []
    for fpath in files:
        titulo = os.path.splitext(os.path.basename(fpath))[0]
        print(f"extrayendo: {titulo}", flush=True)
        texto = limpiar(extraer(fpath))
        if a.curar:
            texto = _curar_ia(texto)
        chunks = trozos(texto)
        bid = _slug(titulo)
        for idx, ch in enumerate(chunks):
            cid = f"libro-{col_id}::{bid}::{idx:04d}"
            if cid in existentes:
                continue
            registros.append({
                "chunk_id": cid, "course_id": f"libros-{col_id}", "course_name": a.coleccion,
                "linea": a.linea, "tipo": "Libro", "audiencia": "Terapeutas", "idioma": "es",
                "source_id": f"libro-{bid}", "source_type": "libro",
                "source_file": os.path.basename(fpath), "heading": titulo,
                "text": ch, "char_count": len(ch),
            })
        print(f"  {titulo}: {len(chunks)} chunks", flush=True)

    if not registros:
        print("nada nuevo que agregar (ya estaba)."); return
    print(f"embebiendo {len(registros)} chunks de {len(files)} libro(s)…", flush=True)

    vecs = []
    for s in range(0, len(registros), 256):
        batch = registros[s:s+256]
        r = _emb.embeddings.create(model=EMBED_MODEL, input=[x["text"] for x in batch])
        for e in r.data:
            v = np.array(e.embedding, dtype=np.float32); v = v / (np.linalg.norm(v) or 1.0)
            vecs.append(v)
        print(f"  embebidos {min(s+256, len(registros))}/{len(registros)}…", flush=True)
    nuevos = np.vstack(vecs).astype(np.float32)

    viejos = np.load(VECTORS)
    combinado = np.vstack([viejos, nuevos]).astype(np.float32)
    tmp = VECTORS + ".tmp.npy"
    np.save(tmp, combinado); os.replace(tmp, VECTORS)
    with open(CHUNKS, "a") as fh:
        for reg in registros:
            fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
    print(f"LISTO: +{len(registros)} chunks de libros. Índice ahora: {combinado.shape[0]} vectores.", flush=True)


def _curar_ia(texto):
    llm = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")
    model = os.getenv("HOLOS_MODEL", "google/gemini-2.5-flash")
    out = []
    for i in range(0, len(texto), 5000):
        v = texto[i:i+5000]
        try:
            r = llm.chat.completions.create(model=model, temperature=0.1, max_tokens=1400, messages=[
                {"role": "system", "content": "Limpia este fragmento de un libro: corrige errores de escaneo/OCR, une frases partidas, quita encabezados, pies y números de página. Devuelve solo el texto limpio, sin comentarios."},
                {"role": "user", "content": v}])
            out.append((r.choices[0].message.content or "").strip())
        except Exception:
            out.append(v)
    return "\n\n".join(out)


if __name__ == "__main__":
    main()
