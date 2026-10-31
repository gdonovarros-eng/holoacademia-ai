#!/usr/bin/env python3
"""Limpia transcripciones de clase (subtítulos) con IA → notas de estudio para el Sinodal.

Para cada lección mapeada a un curso, toma el transcript hablado (con relleno/logística)
y lo convierte, por ventanas, en apuntes limpios y fieles (solo contenido de enseñanza).
Luego trocea y escribe chunks con el esquema de library_chunks.jsonl (source_type="transcripcion").

Uso:  python3 scripts/clean_subtitle_lessons.py [LIMIT] [salida.jsonl]
  LIMIT = cuántas lecciones procesar (0 = todas las mapeadas). Útil para probar.
Requiere OPENAI_API_KEY en .env del repo.
"""
import os, re, csv, json, sys, glob, unicodedata
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
from openai import OpenAI

BASE = Path(__file__).resolve().parent.parent
CSV_PATH = BASE / "videos_runtime.csv"
SUBS = "/Users/m2/Downloads/holoacademia-tv/site/assets/subs"
MODEL = os.getenv("CLEAN_MODEL", "gpt-4o-mini")
WIN = 9000            # caracteres de transcript por llamada
CHUNK = 1500          # tamaño del chunk final

def slug(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "curso"

def limpia_vtt(txt):
    out, prev = [], None
    for raw in txt.splitlines():
        line = raw.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line or re.fullmatch(r"\d+", line):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if line == prev:
            continue
        prev = line
        out.append(line)
    return " ".join(out).strip()

def ventanas(text, n=WIN):
    partes = re.split(r"(?<=[\.\?\!])\s+", text)
    w, buf = [], ""
    for p in partes:
        if len(buf) + len(p) + 1 > n and buf:
            w.append(buf.strip()); buf = ""
        buf += (" " if buf else "") + p
    if buf.strip():
        w.append(buf.strip())
    return w

def trocea(text, n=CHUNK):
    out = ventanas(text, n)
    return out

MAP_PATH = BASE / "data" / "video_course_map.json"

def carga_mapa():
    # Mapa completo video->curso (100% cobertura) generado por el repo tv.
    m = json.load(open(MAP_PATH, encoding="utf-8"))
    return {fid: {"curso": v.get("course_name", ""), "modulo": "", "linea": v.get("linea", "")}
            for fid, v in m.items()}

SYS = ("Eres editor de contenido educativo. Recibes la TRANSCRIPCIÓN hablada de una clase "
       "(con relleno, logística, saludos, bromas, cortes). Devuelve SOLO los apuntes de estudio "
       "en español: las ideas, definiciones, técnicas, pasos y ejemplos que REALMENTE enseña, en "
       "viñetas y párrafos claros. Quita todo lo que no sea contenido (saludos, '¿me escuchan?', "
       "pausas, pagos, nombres de alumnos, logística). Sé fiel: no inventes nada que no esté. Si el "
       "fragmento no tiene contenido de enseñanza, responde exactamente: (sin contenido).")

def limpia_ia(client, fragmento):
    r = client.chat.completions.create(model=MODEL, temperature=0.2, max_tokens=1200,
        messages=[{"role": "system", "content": SYS}, {"role": "user", "content": fragmento}])
    return (r.choices[0].message.content or "").strip()

def main():
    if load_dotenv:
        load_dotenv(BASE / ".env")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("ERROR: falta OPENAI_API_KEY en .env"); sys.exit(1)
    client = OpenAI()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    out = sys.argv[2] if len(sys.argv) > 2 else str(BASE / "data" / "chunks" / "subtitle_chunks_clean.jsonl")
    mapa = carga_mapa()
    files = sorted(glob.glob(os.path.join(SUBS, "*.es.vtt")))
    hechas = n_chunks = 0
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fo = open(out, "w", encoding="utf-8")
    for p in files:
        vid = os.path.basename(p)[:-len(".es.vtt")]
        info = mapa.get(vid)
        if not info:
            continue
        crudo = limpia_vtt(open(p, encoding="utf-8", errors="ignore").read())
        if len(crudo) < 60:
            continue
        limpio_partes = []
        for frag in ventanas(crudo):
            try:
                r = limpia_ia(client, frag)
            except Exception as e:
                print("  (error IA, salto fragmento)", e); continue
            if r and "(sin contenido)" not in r.lower():
                limpio_partes.append(r)
        limpio = "\n\n".join(limpio_partes).strip()
        if len(limpio) < 60:
            continue
        curso = info["curso"] or "Curso"; cid = slug(curso); cname = curso.title()
        heading = cname + (" · Módulo " + info["modulo"] if info["modulo"] else "")
        for i, ch in enumerate(trocea(limpio)):
            rec = {"chunk_id": "%s::%s::%04d" % (cid, vid, i + 1), "course_id": cid,
                   "course_name": cname, "linea": info["linea"] or "Cursos", "tipo": "Curso",
                   "audiencia": "Alumnos", "idioma": "es", "source_id": vid,
                   "source_type": "transcripcion", "source_file": vid + ".es.vtt",
                   "heading": heading, "text": ch, "char_count": len(ch)}
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n"); n_chunks += 1
        hechas += 1
        print("  ✓ %s · %s (%d chunks limpios)" % (cname, info["modulo"], len(trocea(limpio))))
        if limit and hechas >= limit:
            break
    fo.close()
    print("\nLecciones limpiadas: %d · chunks: %d · salida: %s" % (hechas, n_chunks, out))

if __name__ == "__main__":
    main()
