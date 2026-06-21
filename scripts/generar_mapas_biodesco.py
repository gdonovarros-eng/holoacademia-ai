#!/usr/bin/env python3
"""Genera los 'Mapas especiales' de biodescodificación, anclados a la biblioteca:
  - dientes: los 32 dientes (FDI) con su conflicto, órgano y significado
  - lateralidad: decodificador diestro/zurdo, derecha/izquierda
  - ciclos: ciclos biológicos celulares memorizados (proyecto de autonomía)
  - proyecto_sentido: etapas desde el deseo/concepción hasta la primera infancia

Salida: data/biodesco_mapas.json. Reanudable (salta dientes ya hechos).
Uso: python3.14 scripts/generar_mapas_biodesco.py [--solo dientes|lateralidad|ciclos|proyecto]
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

POS = {1: "Incisivo central", 2: "Incisivo lateral", 3: "Canino",
       4: "Primer premolar", 5: "Segundo premolar", 6: "Primer molar",
       7: "Segundo molar", 8: "Tercer molar (muela del juicio)"}
CUAD = {1: ("Superior", "Derecho"), 2: ("Superior", "Izquierdo"),
        3: ("Inferior", "Izquierdo"), 4: ("Inferior", "Derecho")}


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


def gen_diente(num: int):
    arcada, lado = CUAD[num // 10]
    nombre = POS[num % 10]
    etq = f"{nombre} {arcada.lower()} {lado.lower()}"
    ctx, nf = _ctx(f"diente {etq} {nombre} descodificación dental conflicto significado órgano")
    prompt = (
        f"Diente FDI {num}: {nombre} {arcada} {lado}.\n\n"
        f"Material propio:\n{ctx[:6500]}\n\n"
        "Devuelve JSON con EXACTAMENTE estas claves:\n"
        '{\n'
        '  "organo": "órgano o meridiano asociado a este diente",\n'
        '  "conflicto": "el conflicto emocional que codifica este diente, 1-2 frases",\n'
        '  "significado": "su significado simbólico segun el tipo de diente (incisivos: identidad y lugar en el clan; caninos: poder y agresividad; premolares: deseos y proyectos; molares: decisiones y realización material)",\n'
        '  "tema_relacional": "a qué ámbito o persona del sistema apunta segun su posición (superior/inferior, derecha/izquierda)",\n'
        '  "sintomas": ["problemas dentales asociados: caries, dolor, fractura, bruxismo, etc."]\n'
        "}"
    )
    res = _generar_con_sistema(SYSTEM, prompt, "mapa-dental", temperature=0.3, max_tokens=900)
    ficha = _extract_json(res.get("answer", "")) if res.get("ok") else None
    if not isinstance(ficha, dict):
        return num, None
    ficha.update({"numero": num, "nombre": nombre, "tipo": nombre.split(" (")[0].split()[0],
                  "arcada": arcada, "lado": lado, "fuentes": nf})
    return num, ficha


def gen_concepto(clave: str):
    if clave == "lateralidad":
        ctx, _ = _ctx("lateralidad biológica diestro zurdo derecha izquierda a quién representa madre hijos pareja", 10)
        esquema = (
            '{\n'
            '  "intro": "qué es la lateralidad biológica y por qué es clave al descodificar",\n'
            '  "como_determinar": "cómo se determina la lateralidad biológica de la persona",\n'
            '  "diestro": {"derecha": "qué representa el lado derecho en un diestro", "izquierda": "qué representa el lado izquierdo en un diestro"},\n'
            '  "zurdo": {"derecha": "qué representa el lado derecho en un zurdo", "izquierda": "qué representa el lado izquierdo en un zurdo"},\n'
            '  "claves": ["3 a 5 claves prácticas para el terapeuta"]\n'
            '}'
        )
    elif clave == "ciclos":
        ctx, _ = _ctx("ciclos biológicos celulares memorizados proyecto de autonomía fechas que se repiten", 10)
        esquema = (
            '{\n'
            '  "intro": "qué son los ciclos biológicos celulares memorizados",\n'
            '  "principio": "el principio de repetición de fechas y edades",\n'
            '  "como_calcular": "cómo se calcula el ciclo o la fecha de repetición de un evento",\n'
            '  "ejemplo": "un ejemplo clínico breve",\n'
            '  "claves": ["3 a 5 claves prácticas para el terapeuta"]\n'
            '}'
        )
    elif clave == "proyecto_sentido":
        ctx, _ = _ctx("proyecto sentido gestacional deseo de embarazo trimestres parto primera infancia qué se programa", 10)
        esquema = (
            '{\n'
            '  "intro": "qué es el proyecto sentido y el periodo que abarca",\n'
            '  "etapas": [{"etapa": "nombre de la etapa", "periodo": "el momento que abarca", "que_se_programa": "qué se inscribe en el niño en esa etapa"}],\n'
            '  "claves": ["3 a 5 claves prácticas para el terapeuta"]\n'
            '}'
        )
    else:
        return clave, None
    prompt = f"Material propio:\n{ctx[:7500]}\n\nDevuelve JSON con esta forma:\n{esquema}"
    res = _generar_con_sistema(SYSTEM, prompt, f"mapa-{clave}", temperature=0.35, max_tokens=1600)
    obj = _extract_json(res.get("answer", "")) if res.get("ok") else None
    return clave, (obj if isinstance(obj, dict) else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", default="")
    args = ap.parse_args()
    data = {}
    if os.path.exists(OUT):
        try:
            data = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            data = {}
    data.setdefault("dientes", {})

    quiere = (lambda x: (not args.solo) or args.solo == x)

    if quiere("dientes"):
        nums = [q * 10 + p for q in (1, 2, 3, 4) for p in range(1, 9)]
        pend = [n for n in nums if str(n) not in data["dientes"]]
        print(f"dientes pendientes: {len(pend)}")
        with ThreadPoolExecutor(max_workers=6) as ex:
            for fut in as_completed({ex.submit(gen_diente, n): n for n in pend}):
                num, ficha = fut.result()
                if ficha:
                    data["dientes"][str(num)] = ficha
                    print(f"  diente {num} OK")
                else:
                    print(f"  diente {num} FALLO")
        json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    for clave in ("lateralidad", "ciclos", "proyecto_sentido"):
        if quiere(clave):
            _, obj = gen_concepto(clave)
            if obj:
                data[clave] = obj
                print(f"{clave} OK")
            else:
                print(f"{clave} FALLO")
            json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"LISTO. dientes={len(data.get('dientes',{}))} conceptos="
          f"{[k for k in ('lateralidad','ciclos','proyecto_sentido') if k in data]}")


if __name__ == "__main__":
    main()
