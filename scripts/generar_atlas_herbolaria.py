#!/usr/bin/env python3
"""Genera los atlas del módulo de Herbolaria, anclados a la biblioteca en Neon.

  --tradicion bach      -> data/herb_bach.json      (38 flores + Rescue)
  --tradicion aztecas   -> data/herb_aztecas.json   (46 esencias + 15 combinados, extraídos del folleto)
  --tradicion mexicana  -> data/herb_mexicana.json  (plantas mexicanas; extrae nombres del corpus)

Reanudable. Motor propio: no cita autores/libros, sin emojis, español clínico.
Uso: python3.14 scripts/generar_atlas_herbolaria.py --tradicion bach [--limit N] [--workers 6]
"""
from __future__ import annotations
import os, sys, json, re, argparse, threading, unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from api.holos_rag import retrieve            # noqa: E402
from api.chat_service import _generar_con_sistema  # noqa: E402

DATA = os.path.join(ROOT, "data")
SYSTEM = (
    "Eres el motor de conocimiento de herbolaria, fitoterapia y terapia floral "
    "de una plataforma para terapeutas. Trabajas con el material propio que se "
    "te entrega como contexto. Reglas estrictas: no cites autores, libros, "
    "marcas ni cursos; no uses emojis; español claro y clínico. Devuelves "
    "EXCLUSIVAMENTE un objeto JSON válido, sin texto antes ni después, sin ```."
)
_lock = threading.Lock()


def _slug(t):
    t = unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:60]


def _extract_json(text: str):
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


def _ctx(query, course_ids, k=8):
    frags = retrieve(query, k=k, course_ids=course_ids)
    return ("\n\n".join(f"[{f.get('heading') or ''}] {(f.get('text') or '')[:700]}"
                        for f in frags[:k]) or "(sin material)"), len(frags)


def _save(path, data):
    tmp = path + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _load(path):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


# ─────────────────────────── FLORES DE BACH ───────────────────────────
BACH = [
    ("Heliantemo", "Rock Rose", "Miedo"), ("Mímulo", "Mimulus", "Miedo"),
    ("Cerasífera", "Cherry Plum", "Miedo"), ("Álamo temblón", "Aspen", "Miedo"),
    ("Castaño rojo", "Red Chestnut", "Miedo"),
    ("Cerato", "Cerato", "Incertidumbre"), ("Scleranthus", "Scleranthus", "Incertidumbre"),
    ("Genciana", "Gentian", "Incertidumbre"), ("Aulaga", "Gorse", "Incertidumbre"),
    ("Hojarazo", "Hornbeam", "Incertidumbre"), ("Avena silvestre", "Wild Oat", "Incertidumbre"),
    ("Clemátide", "Clematis", "Falta de interés en el presente"),
    ("Madreselva", "Honeysuckle", "Falta de interés en el presente"),
    ("Rosa silvestre", "Wild Rose", "Falta de interés en el presente"),
    ("Olivo", "Olive", "Falta de interés en el presente"),
    ("Castaño blanco", "White Chestnut", "Falta de interés en el presente"),
    ("Mostaza", "Mustard", "Falta de interés en el presente"),
    ("Brote de castaño", "Chestnut Bud", "Falta de interés en el presente"),
    ("Violeta de agua", "Water Violet", "Soledad"), ("Impaciencia", "Impatiens", "Soledad"),
    ("Brezo", "Heather", "Soledad"),
    ("Agrimonia", "Agrimony", "Hipersensibilidad"), ("Centaura", "Centaury", "Hipersensibilidad"),
    ("Nogal", "Walnut", "Hipersensibilidad"), ("Acebo", "Holly", "Hipersensibilidad"),
    ("Alerce", "Larch", "Desaliento y desesperación"), ("Pino", "Pine", "Desaliento y desesperación"),
    ("Olmo", "Elm", "Desaliento y desesperación"),
    ("Castaño dulce", "Sweet Chestnut", "Desaliento y desesperación"),
    ("Estrella de Belén", "Star of Bethlehem", "Desaliento y desesperación"),
    ("Sauce", "Willow", "Desaliento y desesperación"), ("Roble", "Oak", "Desaliento y desesperación"),
    ("Manzano silvestre", "Crab Apple", "Desaliento y desesperación"),
    ("Achicoria", "Chicory", "Preocupación excesiva por los demás"),
    ("Verbena", "Vervain", "Preocupación excesiva por los demás"),
    ("Vid", "Vine", "Preocupación excesiva por los demás"),
    ("Haya", "Beech", "Preocupación excesiva por los demás"),
    ("Agua de roca", "Rock Water", "Preocupación excesiva por los demás"),
    ("Rescate", "Rescue Remedy", "Fórmula de emergencia"),
]


def gen_bach(nombre, eng, grupo):
    ctx, nf = _ctx(f"flor de Bach {nombre} {eng} estado emocional indicación", ["libros-flores-bach"])
    prompt = (
        f"Flor de Bach: {nombre} ({eng}). Grupo emocional: {grupo}.\n\n"
        f"Material propio:\n{ctx[:6000]}\n\n"
        "Devuelve JSON con EXACTAMENTE estas claves:\n"
        '{\n'
        '  "estado_negativo": "el estado mental o emocional que indica esta flor (lo que se transforma)",\n'
        '  "estado_positivo": "la virtud o estado al que conduce",\n'
        '  "indicacion": "cuándo usarla, en 1-2 frases clínicas",\n'
        '  "palabras_clave": ["4 a 6 palabras clave del estado"],\n'
        '  "senales": ["señales o frases típicas de quien la necesita"]\n'
        "}"
    )
    res = _generar_con_sistema(SYSTEM, prompt, "atlas-bach", temperature=0.3, max_tokens=900)
    f = _extract_json(res.get("answer", "")) if res.get("ok") else None
    if not isinstance(f, dict):
        return None
    f.update({"slug": _slug(nombre), "nombre": nombre, "nombre_en": eng, "grupo": grupo, "fuentes": nf})
    return f


def run_bach(limit, workers):
    path = os.path.join(DATA, "herb_bach.json")
    out = _load(path)
    pend = [b for b in BACH if _slug(b[0]) not in out]
    if limit:
        pend = pend[:limit]
    print(f"bach: {len(out)} hechas, {len(pend)} pendientes")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(gen_bach, n, e, g): n for n, e, g in pend}
        done = 0
        for fut in as_completed(futs):
            f = fut.result(); done += 1
            if f:
                with _lock:
                    out[f["slug"]] = f
                    if done % 6 == 0:
                        _save(path, out)
                print(f"  [{done}/{len(pend)}] {f['nombre']} OK")
            else:
                print(f"  [{done}/{len(pend)}] FALLO")
    _save(path, out)
    print(f"LISTO bach: {len(out)}")


# ─────────────────────────── ELIXIRES AZTECAS ───────────────────────────
def run_aztecas(limit, workers):
    path = os.path.join(DATA, "herb_aztecas.json")
    out = _load(path)
    # 1) extraer el catálogo (nombres) del folleto si aún no se tiene
    cat_path = os.path.join(DATA, "herb_aztecas_catalogo.json")
    if os.path.exists(cat_path):
        catalogo = json.load(open(cat_path, encoding="utf-8"))
    else:
        frags = retrieve("esencias individuales remedios combinados nombre lista catálogo",
                         k=20, course_ids=["libros-elixires-aztecas"])
        texto = "\n\n".join((f.get("text") or "") for f in frags)[:14000]
        prompt = (
            "Del siguiente material del set de Elixires Aztecas, extrae el catálogo "
            "completo de esencias. Devuelve JSON:\n"
            '{"individuales": ["nombre de cada esencia individual"], '
            '"combinados": ["nombre de cada remedio combinado"]}\n\n' + texto
        )
        res = _generar_con_sistema(SYSTEM, prompt, "aztecas-catalogo", temperature=0.1, max_tokens=2000)
        cat = _extract_json(res.get("answer", "")) or {"individuales": [], "combinados": []}
        json.dump(cat, open(cat_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        catalogo = cat
    items = [("individual", n) for n in catalogo.get("individuales", [])] + \
            [("combinado", n) for n in catalogo.get("combinados", [])]
    print(f"aztecas catálogo: {len(catalogo.get('individuales',[]))} individuales + "
          f"{len(catalogo.get('combinados',[]))} combinados")
    pend = [(t, n) for t, n in items if _slug(n) not in out]
    if limit:
        pend = pend[:limit]

    def gen_az(tipo, nombre):
        ctx, nf = _ctx(f"elixir azteca {nombre} cualidad aptitud emoción", ["libros-elixires-aztecas"])
        prompt = (
            f"Esencia azteca ({tipo}): {nombre}.\n\nMaterial propio:\n{ctx[:5500]}\n\n"
            "Devuelve JSON con EXACTAMENTE estas claves:\n"
            '{\n'
            '  "origen": "flor, hongo, planta o mineral del que proviene (si aparece)",\n'
            '  "cualidad": "la aptitud o cualidad positiva que ayuda a aflorar",\n'
            '  "armoniza": "qué emoción o comportamiento equilibra",\n'
            '  "indicacion": "cuándo usarla, 1-2 frases",\n'
            '  "palabras_clave": ["3 a 5 palabras clave"]\n'
            "}"
        )
        res = _generar_con_sistema(SYSTEM, prompt, "atlas-aztecas", temperature=0.3, max_tokens=800)
        f = _extract_json(res.get("answer", "")) if res.get("ok") else None
        if not isinstance(f, dict):
            return None
        f.update({"slug": _slug(nombre), "nombre": nombre, "tipo": tipo, "fuentes": nf})
        return f

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(gen_az, t, n): n for t, n in pend}
        done = 0
        for fut in as_completed(futs):
            f = fut.result(); done += 1
            if f:
                with _lock:
                    out[f["slug"]] = f
                    if done % 6 == 0:
                        _save(path, out)
                print(f"  [{done}/{len(pend)}] {f['nombre']} OK")
            else:
                print(f"  [{done}/{len(pend)}] FALLO")
    _save(path, out)
    print(f"LISTO aztecas: {len(out)}")


# ─────────────────────────── HERBOLARIA MEXICANA ───────────────────────────
def run_mexicana(limit, workers):
    path = os.path.join(DATA, "herb_mexicana.json")
    out = _load(path)
    lst_path = os.path.join(DATA, "herb_mexicana_lista.json")
    if os.path.exists(lst_path):
        plantas = json.load(open(lst_path, encoding="utf-8"))
    else:
        # extraer nombres de plantas en varias pasadas temáticas
        nombres = {}
        for q in ["plantas medicinales mexicanas nombre náhuatl uso",
                  "hierbas curativas tradicionales de México",
                  "plantas del códice remedios nueva españa",
                  "plantas medicinales indígenas mexicanas"]:
            frags = retrieve(q, k=14, course_ids=["libros-herbolaria-mexicana"])
            texto = "\n\n".join((f.get("text") or "") for f in frags)[:13000]
            res = _generar_con_sistema(SYSTEM,
                "Extrae del material una lista de plantas medicinales mexicanas. Devuelve JSON: "
                '{"plantas": [{"comun": "nombre común", "nahuatl": "nombre náhuatl si aparece o vacío", '
                '"cientifico": "nombre científico si aparece o vacío"}]}\n\n' + texto,
                "mexicana-lista", temperature=0.2, max_tokens=2000)
            obj = _extract_json(res.get("answer", "")) or {}
            for p in obj.get("plantas", []):
                key = _slug(p.get("comun") or p.get("cientifico") or "")
                if key and key not in nombres:
                    nombres[key] = p
        plantas = list(nombres.values())
        json.dump(plantas, open(lst_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"mexicana: lista de {len(plantas)} plantas")
    pend = [p for p in plantas if _slug(p.get("comun") or p.get("cientifico") or "") not in out]
    if limit:
        pend = pend[:limit]

    def gen_mex(p):
        nombre = p.get("comun") or p.get("cientifico") or ""
        if not nombre:
            return None
        ctx, nf = _ctx(f"planta medicinal mexicana {nombre} {p.get('nahuatl','')} uso preparación",
                       ["libros-herbolaria-mexicana"])
        prompt = (
            f"Planta medicinal mexicana: {nombre} "
            f"(náhuatl: {p.get('nahuatl') or 'n/d'}; científico: {p.get('cientifico') or 'n/d'}).\n\n"
            f"Material propio:\n{ctx[:6000]}\n\n"
            "Devuelve JSON con EXACTAMENTE estas claves:\n"
            '{\n'
            '  "cientifico": "nombre científico si se conoce",\n'
            '  "nahuatl": "nombre náhuatl u otro indígena si aparece",\n'
            '  "parte_usada": "parte de la planta que se usa",\n'
            '  "usos": ["usos tradicionales y dolencias que atiende"],\n'
            '  "preparacion": "cómo se prepara y administra tradicionalmente",\n'
            '  "precaucion": "precaución, toxicidad o contraindicación si aplica, o \'Sin datos\'"\n'
            "}"
        )
        res = _generar_con_sistema(SYSTEM, prompt, "atlas-mexicana", temperature=0.3, max_tokens=900)
        f = _extract_json(res.get("answer", "")) if res.get("ok") else None
        if not isinstance(f, dict):
            return None
        f.update({"slug": _slug(nombre), "nombre": nombre, "fuentes": nf})
        if not f.get("nahuatl"):
            f["nahuatl"] = p.get("nahuatl", "")
        return f

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(gen_mex, p): p for p in pend}
        done = 0
        for fut in as_completed(futs):
            f = fut.result(); done += 1
            if f:
                with _lock:
                    out[f["slug"]] = f
                    if done % 10 == 0:
                        _save(path, out)
                print(f"  [{done}/{len(pend)}] {f['nombre']} OK")
            else:
                print(f"  [{done}/{len(pend)}] FALLO")
    _save(path, out)
    print(f"LISTO mexicana: {len(out)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tradicion", required=True, choices=["bach", "aztecas", "mexicana"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    {"bach": run_bach, "aztecas": run_aztecas, "mexicana": run_mexicana}[a.tradicion](a.limit, a.workers)


if __name__ == "__main__":
    main()
