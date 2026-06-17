#!/usr/bin/env python3
"""Cura transcripciones .whisper con IA e ingiere al índice del Library KB.

Pipeline: extraer .whisper -> CURAR con IA (destila solo la enseñanza) ->
trocear -> embeber -> anexar a library_chunks.jsonl + library_vectors.npy.

Idempotente (salta chunk_ids existentes) y reanudable (cachea la curación por
ventana en /tmp, para no re-pagar si se interrumpe).

Uso:
  python scripts/curar_e_ingestar.py \
      --src "/Volumes/.../02_transcripts" --pattern "*practica_mistica_2*" \
      --course-id diplomado-practica-mistica-2 \
      --course-name "Diplomado Práctica Mística 2" \
      --linea Diplomados --tipo Diplomado
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys, zipfile, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

ROOT = "/Users/m2/Projects/holoacademia-ai"
CHUNKS = f"{ROOT}/data/chunks/library_chunks.jsonl"
VECTORS = f"{ROOT}/data/embeddings/library_vectors.npy"
CACHE_DIR = "/tmp/curacion_cache"
EMBED_MODEL = "text-embedding-3-small"
WINDOW = 4500
CHUNK_TARGET = 1400
CURA_WORKERS = 8

for line in open(f"{ROOT}/.env"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip()
from openai import OpenAI
_emb = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
_llm = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")
CURA_MODEL = os.getenv("HOLOS_MODEL", "google/gemini-2.5-flash")

SYS_CURAR = (
    "Eres editor de contenido educativo de un método terapéutico holístico. "
    "Te doy la transcripción CRUDA de una clase grabada. Devuelve SOLO el contenido "
    "de enseñanza, reescrito en prosa clara y profesional en español. "
    "ELIMINA por completo: bromas, groserías, charla casual, nombres de personas, "
    "logística (horarios, comidas, pausas), muletillas, repeticiones, y cualquier "
    "texto sin sentido o en otro idioma (errores del transcriptor). "
    "No inventes nada que no esté. No menciones que es una transcripción ni cites "
    "autores, maestros ni cursos. Si el fragmento NO contiene enseñanza real, "
    "responde únicamente: SIN CONTENIDO."
)


def texto_whisper(p):
    try:
        z = zipfile.ZipFile(p); md = json.loads(z.read("metadata.json"))
        return " ".join((s.get("text") or "").strip() for s in (md.get("transcripts") or []))
    except Exception:
        return ""


def curar(texto):
    for intento in range(3):
        try:
            r = _llm.chat.completions.create(
                model=CURA_MODEL, temperature=0.2, max_tokens=1400,
                messages=[{"role": "system", "content": SYS_CURAR}, {"role": "user", "content": texto}],
            )
            return (r.choices[0].message.content or "").strip()
        except Exception as e:
            if intento == 2:
                print(f"  ! fallo curando ventana: {e}", flush=True)
                return ""
    return ""


def trocear(t, target=CHUNK_TARGET, overlap=150):
    out, cur = [], ""
    for frase in re.split(r"(?<=[.!?])\s+", t):
        if len(cur) + len(frase) + 1 <= target:
            cur = f"{cur} {frase}".strip()
        else:
            if cur: out.append(cur)
            cur = (cur[-overlap:] + " " + frase) if cur else frase
    if cur: out.append(cur)
    return [c for c in out if len(c) > 120]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--pattern", required=True)
    ap.add_argument("--course-id", required=True, dest="course_id")
    ap.add_argument("--course-name", required=True, dest="course_name")
    ap.add_argument("--linea", default="Diplomados")
    ap.add_argument("--tipo", default="Diplomado")
    a = ap.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = f"{CACHE_DIR}/{a.course_id}.jsonl"
    cache = {}
    if os.path.exists(cache_path):
        for ln in open(cache_path):
            d = json.loads(ln); cache[d["h"]] = d["c"]
    print(f"[{a.course_id}] caché de curación: {len(cache)} ventanas previas", flush=True)

    files = sorted(glob.glob(os.path.join(a.src, a.pattern)))
    if not files:
        sys.exit(f"sin archivos para {a.pattern}")
    texto = re.sub(r"\s+", " ", " ".join(texto_whisper(f) for f in files)).strip()
    ventanas = [texto[i:i+WINDOW] for i in range(0, len(texto), WINDOW)]
    print(f"[{a.course_id}] {len(files)} archivos · {len(texto):,} chars · {len(ventanas)} ventanas", flush=True)

    # curar ventanas faltantes en paralelo, escribiendo al caché
    pendientes = [(i, v) for i, v in enumerate(ventanas) if hashlib.md5(v.encode()).hexdigest() not in cache]
    print(f"[{a.course_id}] curando {len(pendientes)} ventanas nuevas…", flush=True)
    done = 0
    with open(cache_path, "a") as cf, ThreadPoolExecutor(max_workers=CURA_WORKERS) as ex:
        futs = {ex.submit(curar, v): (i, v) for i, v in pendientes}
        for fut in as_completed(futs):
            i, v = futs[fut]
            out = fut.result()
            h = hashlib.md5(v.encode()).hexdigest()
            cache[h] = out
            cf.write(json.dumps({"h": h, "c": out}) + "\n"); cf.flush()
            done += 1
            if done % 25 == 0:
                print(f"  curadas {done}/{len(pendientes)}…", flush=True)

    # reconstruir el texto curado en orden, descartando SIN CONTENIDO
    curado = []
    for v in ventanas:
        c = cache.get(hashlib.md5(v.encode()).hexdigest(), "")
        if c and "SIN CONTENIDO" not in c.upper()[:40]:
            curado.append(c)
    texto_curado = "\n\n".join(curado)
    chunks = trocear(texto_curado)
    print(f"[{a.course_id}] texto curado: {len(texto_curado):,} chars · {len(chunks)} chunks", flush=True)

    # saltar chunk_ids ya existentes
    existentes = set()
    for ln in open(CHUNKS):
        try: existentes.add(json.loads(ln)["chunk_id"])
        except Exception: pass
    registros = []
    for idx, ch in enumerate(chunks):
        cid = f"{a.course_id}::curado::{idx:04d}"
        if cid in existentes:
            continue
        registros.append({
            "chunk_id": cid, "course_id": a.course_id, "course_name": a.course_name,
            "linea": a.linea, "tipo": a.tipo, "audiencia": "Alumnos", "idioma": "es",
            "source_id": f"{a.course_id}-curado", "source_type": "curado",
            "source_file": f"{a.course_name} (curado)", "heading": a.course_name,
            "text": ch, "char_count": len(ch),
        })
    if not registros:
        print(f"[{a.course_id}] nada nuevo que agregar (ya estaba)."); return
    print(f"[{a.course_id}] embebiendo {len(registros)} chunks nuevos…", flush=True)

    vecs = []
    for s in range(0, len(registros), 256):
        batch = registros[s:s+256]
        r = _emb.embeddings.create(model=EMBED_MODEL, input=[x["text"] for x in batch])
        for e in r.data:
            v = np.array(e.embedding, dtype=np.float32)
            v = v / (np.linalg.norm(v) or 1.0)
            vecs.append(v)
        print(f"  embebidos {min(s+256, len(registros))}/{len(registros)}…", flush=True)
    nuevos = np.vstack(vecs).astype(np.float32)

    # anexar de forma atómica, manteniendo alineación jsonl<->npy
    viejos = np.load(VECTORS)
    combinado = np.vstack([viejos, nuevos]).astype(np.float32)
    tmp = VECTORS + ".tmp.npy"     # termina en .npy para que np.save no lo renombre
    np.save(tmp, combinado)
    os.replace(tmp, VECTORS)
    with open(CHUNKS, "a") as fh:
        for reg in registros:
            fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
    print(f"[{a.course_id}] LISTO: +{len(registros)} chunks. Índice ahora: {combinado.shape[0]} vectores.", flush=True)


if __name__ == "__main__":
    main()
