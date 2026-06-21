#!/usr/bin/env python3
"""Genera el Diccionario biológico de biodescodificación.

Toma el esqueleto de conflictos (data/biodesco_skeleton.json) y, para cada uno,
recupera material propio de Neon (libros de biodescodificación + NMG) y pide al
modelo una ficha estructurada en JSON estricto. Reanudable: salta los que ya
existen en data/biodesco_diccionario.json. Concurrente y con guardado periódico.

Uso:
  python3 scripts/generar_diccionario_biodesco.py            # corrida completa
  python3 scripts/generar_diccionario_biodesco.py --limit 3  # prueba 3
  python3 scripts/generar_diccionario_biodesco.py --workers 6
"""
from __future__ import annotations
import os, sys, json, re, argparse, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# cargar .env
for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from api.holos_rag import retrieve            # noqa: E402
from api.chat_service import _generar_con_sistema  # noqa: E402

SKELETON = os.path.join(ROOT, "data", "biodesco_skeleton.json")
OUT = os.path.join(ROOT, "data", "biodesco_diccionario.json")
COURSE_IDS = ["libros-biodescodificacion", "libros-nmg"]

SYSTEM = (
    "Eres el motor de conocimiento de biodescodificación y Nueva Medicina "
    "Germánica de una plataforma para terapeutas. Conoces las 5 Leyes "
    "Biológicas, las capas embrionarias y las dos fases de la enfermedad. "
    "Trabajas SOLO con el material propio que se te entrega como contexto. "
    "Reglas estrictas: no cites autores, libros, cursos ni profesores; no uses "
    "emojis; escribe en español claro y clínico. Devuelves EXCLUSIVAMENTE un "
    "objeto JSON válido, sin texto antes ni después, sin ```."
)

CAPAS = "Endodermo | Mesodermo antiguo (cerebelo) | Mesodermo nuevo (médula) | Ectodermo"

PROMPT_TMPL = (
    "Conflicto base: \"{nombre}\"\n"
    "Sistema: {sistema} — Subsistema: {subsistema}\n\n"
    "Material propio (úsalo como única fuente; si algo no está, infiérelo con "
    "criterio biológico clásico, sin inventar autores):\n{contexto}\n\n"
    "Genera la ficha del conflicto en JSON con EXACTAMENTE estas claves:\n"
    "{{\n"
    '  "organo": "órgano o tejido implicado",\n'
    '  "conflicto": "el conflicto emocional preciso, 1-2 frases",\n'
    '  "sentido_biologico": "para qué sirve el síntoma, la función biológica",\n'
    '  "capa_embrionaria": "una de: ' + CAPAS + '",\n'
    '  "tipo_conflicto": "el tipo según la capa (ej. del bocado, de desvalorización, de separación, de territorio, de miedo)",\n'
    '  "fase_activa": "qué ocurre en la fase de conflicto activo (simpaticotonía)",\n'
    '  "fase_reparacion": "qué ocurre en la fase de reparación (vagotonía)",\n'
    '  "lateralidad": "nota de lateralidad/zurdería si aplica, o \'No determinante\'",\n'
    '  "preguntas": ["3 a 5 preguntas de desprogramación para el consultante"],\n'
    '  "sintomas": ["expresiones o síntomas relacionados"]\n'
    "}}"
)

_lock = threading.Lock()


def _extract_json(text: str) -> dict | None:
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1:
        return None
    try:
        return json.loads(t[i:j + 1])
    except Exception:
        return None


def _load_out() -> dict:
    if os.path.exists(OUT):
        try:
            return json.load(open(OUT, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_out(data: dict) -> None:
    tmp = OUT + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)


def generar_uno(entry: dict) -> tuple[str, dict | None]:
    nombre = entry["nombre"]
    frags = retrieve(nombre, k=8, course_ids=COURSE_IDS)
    contexto = "\n\n".join(
        f"[{f.get('heading') or ''}] {(f.get('text') or '')[:700]}" for f in frags[:8]
    ) or "(sin material recuperado)"
    prompt = PROMPT_TMPL.format(
        nombre=nombre, sistema=entry["sistema_label"],
        subsistema=entry["subsistema_label"], contexto=contexto[:7000],
    )
    res = _generar_con_sistema(SYSTEM, prompt, "diccionario-biodesco",
                               temperature=0.3, max_tokens=1200)
    if not res.get("ok"):
        return entry["slug"], None
    ficha = _extract_json(res.get("answer", ""))
    if not isinstance(ficha, dict):
        return entry["slug"], None
    ficha.update({
        "slug": entry["slug"], "nombre": nombre,
        "sistema": entry["sistema"], "sistema_label": entry["sistema_label"],
        "subsistema": entry["subsistema"], "subsistema_label": entry["subsistema_label"],
        "fuentes": len(frags),
    })
    return entry["slug"], ficha


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    skeleton = json.load(open(SKELETON, encoding="utf-8"))
    out = _load_out()
    pendientes = [e for e in skeleton if e["slug"] not in out]
    if args.limit:
        pendientes = pendientes[:args.limit]
    print(f"total={len(skeleton)} ya_hechos={len(out)} pendientes={len(pendientes)} workers={args.workers}")

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(generar_uno, e): e for e in pendientes}
        for fut in as_completed(futs):
            slug, ficha = fut.result()
            done += 1
            if ficha:
                with _lock:
                    out[slug] = ficha
                    if done % 10 == 0:
                        _save_out(out)
                print(f"[{done}/{len(pendientes)}] OK {slug}")
            else:
                print(f"[{done}/{len(pendientes)}] FALLO {slug}")
    _save_out(out)
    print(f"LISTO. total en diccionario: {len(out)}")


if __name__ == "__main__":
    main()
