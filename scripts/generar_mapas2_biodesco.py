#!/usr/bin/env python3
"""Añade más 'Mapas especiales' a data/biodesco_mapas.json, anclados a la biblioteca:
  - dedos: dedos de la mano y del pie (conflicto por dedo)
  - piel: la piel y los lunares (capas, zonas, significado de manchas/nevus)
  - peso: sentido biológico del peso y la grasa (por zona)
  - duelos: embarazos y duelos no resueltos
  - homonimos: yacente, homónimo y doble (transgeneracional)

Reanudable: no regenera la clave si ya existe (usa --rehacer para forzar).
Uso: python3.14 scripts/generar_mapas2_biodesco.py [--solo dedos|piel|peso|duelos|homonimos] [--rehacer]
"""
from __future__ import annotations
import os, sys, json, re, argparse
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

OUT = os.path.join(ROOT, "data", "biodesco_mapas.json")
COURSE_IDS = ["libros-biodescodificacion", "libros-nmg"]
SYSTEM = (
    "Eres el motor de conocimiento de biodescodificación y Nueva Medicina "
    "Germánica de una plataforma para terapeutas. Trabajas con el material "
    "propio que se te entrega. Reglas: no cites autores, libros, cursos ni "
    "profesores; no uses emojis; español claro y clínico. Devuelves "
    "EXCLUSIVAMENTE un objeto JSON válido, sin texto antes ni después, sin ```."
)


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


def _ctx(query, k=8):
    frags = retrieve(query, k=k, course_ids=COURSE_IDS)
    return "\n\n".join(f"[{f.get('heading') or ''}] {(f.get('text') or '')[:700]}"
                       for f in frags[:k]) or "(sin material)", len(frags)


def _gen(query, esquema, etq, max_tokens=1600):
    ctx, _ = _ctx(query, 10)
    prompt = f"Material propio:\n{ctx[:7500]}\n\nDevuelve JSON con esta forma:\n{esquema}"
    res = _generar_con_sistema(SYSTEM, prompt, etq, temperature=0.35, max_tokens=max_tokens)
    obj = _extract_json(res.get("answer", "")) if res.get("ok") else None
    return obj if isinstance(obj, dict) else None


DEDOS = [
    ("mano", "Pulgar"), ("mano", "Índice"), ("mano", "Medio (corazón)"),
    ("mano", "Anular"), ("mano", "Meñique"),
    ("pie", "Dedo gordo (hallux)"), ("pie", "Segundo dedo"), ("pie", "Tercer dedo"),
    ("pie", "Cuarto dedo"), ("pie", "Quinto dedo"),
]


def gen_dedo(parte, dedo):
    ctx, nf = _ctx(f"{dedo} de la {parte} biodescodificación conflicto significado meridiano")
    prompt = (
        f"Dedo: {dedo} de la {parte}.\n\nMaterial propio:\n{ctx[:6000]}\n\n"
        "Devuelve JSON con EXACTAMENTE estas claves:\n"
        '{\n'
        '  "organo": "órgano o meridiano asociado a este dedo",\n'
        '  "conflicto": "el conflicto que codifica este dedo, 1-2 frases",\n'
        '  "significado": "su significado simbólico/relacional",\n'
        '  "sintomas": ["problemas asociados: artrosis, fractura, dolor, hongos, etc."]\n'
        "}"
    )
    res = _generar_con_sistema(SYSTEM, prompt, "mapa-dedos", temperature=0.3, max_tokens=800)
    f = _extract_json(res.get("answer", "")) if res.get("ok") else None
    if not isinstance(f, dict):
        return None
    f.update({"parte": parte, "dedo": dedo, "fuentes": nf})
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", default="")
    ap.add_argument("--rehacer", action="store_true")
    args = ap.parse_args()
    data = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    quiere = lambda x: (not args.solo) or args.solo == x
    falta = lambda x: args.rehacer or x not in data or not data.get(x)

    if quiere("dedos") and falta("dedos"):
        print("generando dedos…")
        out = []
        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = {ex.submit(gen_dedo, p, d): (p, d) for p, d in DEDOS}
            for fut in as_completed(futs):
                f = fut.result()
                if f:
                    out.append(f); print("  ", f["parte"], f["dedo"], "OK")
        # ordenar mano luego pie, en el orden anatómico
        order = {(p, d): i for i, (p, d) in enumerate(DEDOS)}
        out.sort(key=lambda f: order.get((f["parte"], f["dedo"]), 99))
        data["dedos"] = out
        json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"dedos: {len(out)}")

    if quiere("piel") and falta("piel"):
        obj = _gen(
            "la piel epidermis dermis lunares nevus manchas separación contacto conflicto biodescodificación",
            '{\n'
            '  "intro": "qué expresa la piel en biodescodificación y por qué",\n'
            '  "capas": [{"capa": "Epidermis o Dermis", "conflicto": "el tipo de conflicto que le corresponde", "ejemplos": "afecciones típicas"}],\n'
            '  "lunares": "qué significan los lunares y las manchas y cómo leerlos",\n'
            '  "zonas": [{"zona": "zona del cuerpo", "significado": "a qué tipo de contacto o relación apunta"}],\n'
            '  "claves": ["3 a 5 claves para el terapeuta"]\n'
            '}', "mapa-piel")
        if obj:
            data["piel"] = obj; print("piel OK")
            json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if quiere("peso") and falta("peso"):
        obj = _gen(
            "sentido biológico del peso grasa sobrepeso kilos de más protección abandono reserva conflicto",
            '{\n'
            '  "intro": "el sentido biológico del peso y la grasa",\n'
            '  "principio": "por qué el cuerpo retiene peso como solución biológica",\n'
            '  "por_zona": [{"zona": "zona del cuerpo", "significado": "el conflicto que suele expresar esa zona"}],  // INCLUYE de 5 a 7 zonas: vientre/abdomen, caderas y muslos, vientre bajo, brazos, espalda, cara y papada, todo el cuerpo\n'
            '  "claves": ["3 a 5 claves para el terapeuta"]\n'
            '}', "mapa-peso")
        if obj:
            data["peso"] = obj; print("peso OK")
            json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if quiere("duelos") and falta("duelos"):
        obj = _gen(
            "aborto interrupción pérdida de embarazo niño fallecido duelo no resuelto efecto en los hijos biodescodificación",
            '{\n'
            '  "intro": "cómo afectan los embarazos interrumpidos y los duelos no resueltos",\n'
            '  "tipos": [{"tipo": "aborto espontáneo, IVE, niño fallecido, duelo congelado, etc.", "descripcion": "qué es", "efecto": "qué programa puede dejar en el sistema o en los hijos siguientes"}],\n'
            '  "claves": ["3 a 5 claves para acompañar el duelo en terapia"]\n'
            '}', "mapa-duelos")
        if obj:
            data["duelos"] = obj; print("duelos OK")
            json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if quiere("homonimos") and falta("homonimos"):
        obj = _gen(
            "yacente niño de reemplazo homónimo doble transgeneracional llevar el nombre de un ancestro fechas",
            '{\n'
            '  "intro": "qué son las figuras transgeneracionales que cargan un programa ajeno",\n'
            '  "figuras": [{"figura": "Yacente, Homónimo, Doble, etc.", "descripcion": "qué es y cómo se forma", "senal": "señales o síntomas de que la persona la carga"}],\n'
            '  "claves": ["3 a 5 claves para detectarlas y liberarlas en terapia"]\n'
            '}', "mapa-homonimos")
        if obj:
            data["homonimos"] = obj; print("homonimos OK")
            json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("LISTO. claves:", [k for k in ("dedos", "piel", "peso", "duelos", "homonimos") if k in data])


if __name__ == "__main__":
    main()
