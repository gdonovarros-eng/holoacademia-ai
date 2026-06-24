#!/usr/bin/env python3
"""Capa curada de alto peso para el Sinodal: por cada curso genera, desde la
transcripción, un resumen + temario + conceptos clave + preguntas frecuentes,
y lo ingesta como material 'curado' (peso 1.0 en el ranking).

Reanudable por curso. Uso:
  python3.14 scripts/curar_sinodal.py --dir /tmp/sinodal/conocimiento_sinodal [--solo NOMBRE] [--workers 4]
"""
from __future__ import annotations
import os, sys, re, csv, json, argparse, unicodedata, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts"))
for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from ingerir_sinodal import _bloques, _slug, _vec, _upsert, EMBED_MODEL  # noqa: E402
from ingerir_libros import limpiar           # noqa: E402
from api.chat_service import _generar_con_sistema  # noqa: E402
from openai import OpenAI                      # noqa: E402
_emb = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
_lock = threading.Lock()

SYSTEM = (
    "Eres el Sinodal de HoloacademIA: un tutor experto que conoce a fondo los "
    "cursos. A partir de la transcripción (cruda, de video) de un curso, produces "
    "material de estudio limpio y de alta calidad. No cites autores, marcas ni "
    "plataformas; sin emojis; español claro y didáctico. Devuelves EXCLUSIVAMENTE "
    "un objeto JSON válido, sin texto antes ni después, sin ```."
)


def _extract_json(t):
    t = (t or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t); t = re.sub(r"\n?```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    try:
        return json.loads(t[i:j + 1])
    except Exception:
        return None


def _muestra(bloques, cap=13000):
    """Temario + muestra representativa (inicio de cada módulo)."""
    temario = [m for m, _ in bloques if m]
    por_mod = max(400, cap // max(1, len(bloques)))
    partes = []
    for modulo, cuerpo in bloques:
        partes.append(f"[{modulo}] {cuerpo[:por_mod]}")
    return temario, ("\n\n".join(partes))[:cap]


def curar_curso(categoria, curso, fpath):
    cslug = _slug(curso)
    cid = f"sinodal-{cslug}"
    # reanudable: ¿ya hay curado?
    import psycopg2
    c = psycopg2.connect(os.environ["KNOWLEDGE_DB_URL"]); cur = c.cursor()
    cur.execute("select 1 from holos_chunks where chunk_id=%s", (f"{cid}::curado::0000",))
    ya = cur.fetchone() is not None; cur.close(); c.close()
    if ya:
        return curso, 0
    texto = limpiar(open(fpath, encoding="utf-8", errors="ignore").read())
    bloques = _bloques(texto)
    temario, muestra = _muestra(bloques)
    prompt = (
        f"Curso: {curso} (categoría: {categoria}). Módulos: {'; '.join(temario[:40])}.\n\n"
        f"Muestra de la transcripción:\n{muestra}\n\n"
        "Genera material de estudio en JSON con EXACTAMENTE estas claves:\n"
        '{\n'
        '  "resumen": "2-3 párrafos: qué enseña el curso y para qué sirve",\n'
        '  "conceptos": [{"termino": "concepto clave", "definicion": "explicación clara en 1-3 frases"}],\n'
        '  "faq": [{"pregunta": "pregunta típica de un alumno", "respuesta": "respuesta clara y útil"}]\n'
        "}\n"
        "Incluye 10-15 conceptos y 8-12 preguntas frecuentes, fieles al contenido del curso."
    )
    res = _generar_con_sistema(SYSTEM, prompt, "curar-sinodal", temperature=0.3, max_tokens=3500)
    obj = _extract_json(res.get("answer", "")) if res.get("ok") else None
    if not isinstance(obj, dict):
        return curso, 0
    # construir textos curados
    piezas = []
    piezas.append(("Resumen del curso",
                   f"Curso: {curso}. Resumen: {obj.get('resumen','')}\nTemario: {'; '.join(temario)}"))
    for cc in obj.get("conceptos", []):
        if cc.get("termino"):
            piezas.append((f"Concepto: {cc['termino']}", f"{cc['termino']}: {cc.get('definicion','')}"))
    for q in obj.get("faq", []):
        if q.get("pregunta"):
            piezas.append((f"Pregunta frecuente", f"Pregunta: {q['pregunta']}\nRespuesta: {q.get('respuesta','')}"))
    textos = [t for _, t in piezas]
    if not textos:
        return curso, 0
    rows = []
    for s in range(0, len(textos), 256):
        part = textos[s:s + 256]
        resp = _emb.embeddings.create(model=EMBED_MODEL, input=part)
        for j, (e, (head, txt)) in enumerate(zip(resp.data, piezas[s:s + 256]), start=s):
            t2 = f"[{curso}] {txt}"
            rows.append((f"{cid}::curado::{j:04d}", cid, curso, categoria, "Material curado",
                         "Alumnos", "es", f"curso-{cslug}", "curado", "curado", head, t2, len(t2),
                         _vec(e.embedding)))
    with _lock:
        _upsert(rows)
    return curso, len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--solo", default="")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(os.path.join(a.dir, "INDICE_CURSOS.csv"), encoding="utf-8")))
    if a.solo:
        rows = [r for r in rows if a.solo.lower() in r["curso"].lower()]
    tareas = [(r["categoria"], r["curso"], os.path.join(a.dir, r["archivo"])) for r in rows
              if os.path.exists(os.path.join(a.dir, r["archivo"]))]
    print(f"cursos a curar: {len(tareas)}", flush=True)
    done = 0; total = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(curar_curso, cat, cur, fp): cur for cat, cur, fp in tareas}
        for fut in as_completed(futs):
            cur, n = fut.result(); done += 1; total += n
            print(f"  [{done}/{len(tareas)}] {cur}: +{n} curados", flush=True)
    print(f"\nLISTO. +{total} chunks curados.", flush=True)


if __name__ == "__main__":
    main()
