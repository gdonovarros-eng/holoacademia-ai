#!/usr/bin/env python3
"""Genera chunks de conocimiento a partir de los subtítulos ES de los cursos.

Mapea cada subtítulo (archivo <video_id>.es.vtt del repo holoacademia-tv) a su curso
usando videos_runtime.csv (CURSO;MODULO;URL;LINEA, el video_id va en la URL de wixstatic),
limpia el VTT, lo trocea en ~1500 caracteres y escribe chunks con el MISMO esquema que
data/chunks/library_chunks.jsonl (source_type="transcripcion").

Por defecto escribe a data/chunks/subtitle_chunks.jsonl (staging). Revisa la cobertura
antes de anexarlo al corpus vivo y regenerar embeddings.

Uso:  python3 scripts/build_subtitle_chunks.py [subs_dir] [salida.jsonl]
"""
import os, re, csv, json, sys, glob, unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE, "videos_runtime.csv")
DEFAULT_SUBS = "/Users/m2/Downloads/holoacademia-tv/site/assets/subs"
DEFAULT_OUT = os.path.join(BASE, "data", "chunks", "subtitle_chunks.jsonl")
CHUNK = 1500

def slug(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "curso"

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

def trocea(text, n=CHUNK):
    # corta en límites de oración, acumulando hasta ~n caracteres
    partes = re.split(r"(?<=[\.\?\!])\s+", text)
    chunks, buf = [], ""
    for p in partes:
        if len(buf) + len(p) + 1 > n and buf:
            chunks.append(buf.strip()); buf = ""
        buf += (" " if buf else "") + p
    if buf.strip():
        chunks.append(buf.strip())
    return chunks

def carga_mapa():
    mapa = {}
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            url = (row.get("URL") or "").strip()
            m = re.search(r"/video/([0-9a-fA-F]+_[0-9a-fA-F]+)/", url)
            if not m:
                continue
            vid = m.group(1)
            mapa[vid] = {
                "curso": (row.get("CURSO") or "").strip(),
                "modulo": (row.get("MODULO") or "").strip(),
                "linea": (row.get("LINEA") or "").strip().title(),
            }
    return mapa

def main():
    subs_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SUBS
    out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT
    mapa = carga_mapa()
    files = sorted(glob.glob(os.path.join(subs_dir, "*.es.vtt")))
    n_lecc = n_chunks = sin_mapa = 0
    cursos = {}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fo:
        for p in files:
            vid = os.path.basename(p)[:-len(".es.vtt")]
            info = mapa.get(vid)
            if not info:
                sin_mapa += 1
                continue
            text = limpia_vtt(open(p, encoding="utf-8", errors="ignore").read())
            if len(text) < 40:
                continue
            curso = info["curso"] or "Curso"
            cid = slug(curso)
            cname = curso.title()
            linea = info["linea"] or "Cursos"
            heading = cname + (" · Módulo " + info["modulo"] if info["modulo"] else "")
            partes = trocea(text)
            for i, ch in enumerate(partes):
                rec = {
                    "chunk_id": "%s::%s::%04d" % (cid, vid, i + 1),
                    "course_id": cid,
                    "course_name": cname,
                    "linea": linea,
                    "tipo": "Curso",
                    "audiencia": "Alumnos",
                    "idioma": "es",
                    "source_id": vid,
                    "source_type": "transcripcion",
                    "source_file": vid + ".es.vtt",
                    "heading": heading,
                    "text": ch,
                    "char_count": len(ch),
                }
                fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n_chunks += 1
            n_lecc += 1
            cursos[cname] = cursos.get(cname, 0) + 1
    print("Subtítulos con curso mapeado: %d lecciones" % n_lecc)
    print("Subtítulos SIN mapa (se omiten): %d" % sin_mapa)
    print("Chunks generados:             %d" % n_chunks)
    print("Cursos distintos:             %d" % len(cursos))
    print("Salida:                       %s" % out)
    print("\nTop cursos por lecciones:")
    for c, k in sorted(cursos.items(), key=lambda x: -x[1])[:15]:
        print("  %4d  %s" % (k, c))

if __name__ == "__main__":
    main()
