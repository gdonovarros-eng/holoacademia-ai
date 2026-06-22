#!/usr/bin/env python3
"""Genera el RECETARIO por padecimiento: para cada dolencia, una ficha de
tratamiento con fórmula concreta (plantas + preparación + dosis + duración),
flores de apoyo, opción mexicana, estilo de vida y precauciones.

Anclado a toda la biblioteca herbal en Neon. Reanudable.
Uso: python3.14 scripts/generar_recetario_herbolaria.py [--limit N] [--workers 5] [--rehacer]
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

OUT = os.path.join(ROOT, "data", "herb_recetario.json")
COURSE_IDS = ["libros-fitoterapia", "libros-herbolaria-mexicana",
              "libros-flores-bach", "libros-elixires-aztecas"]
_lock = threading.Lock()

SYSTEM = (
    "Eres el Motor de Herbolaria clínica de una plataforma para terapeutas "
    "holísticos. Tu trabajo es dar FÓRMULAS Y RECETAS CONCRETAS para sanar, no "
    "teoría académica. Trabajas con el material propio que se te entrega. "
    "Reglas: no cites autores, libros, marcas ni cursos; no uses emojis; español "
    "claro, práctico y clínico, como una receta para un terapeuta. Devuelves "
    "EXCLUSIVAMENTE un objeto JSON válido, sin texto antes ni después, sin ```."
)

# ── Padecimientos por sistema/área ──────────────────────────────────────────
PADECIMIENTOS = {
    "Digestivo": ["Gastritis", "Reflujo y acidez", "Colon irritable", "Estreñimiento",
                  "Diarrea", "Indigestión y gases", "Hígado graso", "Náuseas y vómito",
                  "Parásitos intestinales", "Úlcera gástrica", "Hemorroides", "Colitis"],
    "Sistema nervioso y emocional": ["Ansiedad", "Insomnio", "Estrés", "Depresión leve",
                  "Ataques de pánico", "Fatiga y agotamiento", "Migraña", "Dolor de cabeza",
                  "Falta de concentración", "Duelo y tristeza"],
    "Respiratorio": ["Resfriado y gripe", "Tos", "Bronquitis", "Asma", "Sinusitis",
                  "Rinitis alérgica", "Faringitis y dolor de garganta", "Mucosidad y flemas"],
    "Circulatorio": ["Hipertensión", "Colesterol alto", "Mala circulación", "Várices",
                  "Palpitaciones", "Anemia"],
    "Hormonal y salud femenina": ["Síndrome premenstrual", "Menopausia", "Menstruación dolorosa",
                  "Ovario poliquístico", "Candidiasis", "Infección urinaria", "Fertilidad",
                  "Lactancia (producir leche)"],
    "Salud masculina": ["Próstata inflamada", "Disfunción eréctil"],
    "Metabólico y endocrino": ["Diabetes y azúcar alta", "Sobrepeso", "Hipotiroidismo",
                  "Hipertiroidismo", "Retención de líquidos", "Gota y ácido úrico"],
    "Dolor y aparato locomotor": ["Artritis y artrosis", "Dolor articular", "Dolor muscular",
                  "Lumbalgia y dolor de espalda", "Fibromialgia", "Calambres"],
    "Piel y cabello": ["Acné", "Eczema y dermatitis", "Psoriasis", "Heridas y llagas",
                  "Herpes", "Hongos en la piel", "Caída del cabello", "Quemaduras leves"],
    "Inmunidad y defensas": ["Defensas bajas", "Infecciones recurrentes", "Alergias",
                  "Convalecencia y recuperación"],
    "Urinario y renal": ["Cálculos renales", "Cistitis", "Retención urinaria"],
    "Otros": ["Vértigo y mareo", "Dolor de oído", "Salud ocular", "Salud bucal y encías",
              "Resaca", "Desintoxicación general"],
}


def _slug(t):
    t = unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:60]


def _extract_json(text):
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t); t = re.sub(r"\n?```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1:
        return None
    try:
        return json.loads(t[i:j + 1])
    except Exception:
        return None


def gen(padecimiento, sistema):
    frags = retrieve(f"{padecimiento} tratamiento herbal plantas fórmula preparación dosis",
                     k=12, course_ids=COURSE_IDS)
    ctx = "\n\n".join(f"[{f.get('heading') or ''}] {(f.get('text') or '')[:650]}" for f in frags[:12]) or "(sin material)"
    prompt = (
        f"Padecimiento: {padecimiento} (área: {sistema}).\n\n"
        f"Material propio:\n{ctx[:8500]}\n\n"
        "Da una receta herbal concreta y accionable para un terapeuta. Devuelve JSON con EXACTAMENTE estas claves:\n"
        '{\n'
        '  "descripcion": "qué es el padecimiento, 1-2 frases",\n'
        '  "plantas": [{"nombre": "planta (común y científico)", "accion": "su acción terapéutica", "para_que": "por qué se usa aquí"}],\n'
        '  "formula": "una fórmula/mezcla concreta con proporciones (ej. partes iguales de X, Y, Z; o 2 partes de X y 1 de Y)",\n'
        '  "preparacion": "forma de preparación (infusión, decocción, tintura), dosis, frecuencia y duración del tratamiento",\n'
        '  "flores": "flores de Bach o esencias de apoyo emocional para este caso",\n'
        '  "mexicana": "opción con planta mexicana tradicional si aplica",\n'
        '  "estilo_vida": "dieta y hábitos de apoyo",\n'
        '  "precauciones": "contraindicaciones, interacciones y cuándo derivar a un médico"\n'
        "}"
    )
    res = _generar_con_sistema(SYSTEM, prompt, "recetario", temperature=0.4, max_tokens=1600)
    f = _extract_json(res.get("answer", "")) if res.get("ok") else None
    if not isinstance(f, dict):
        return None
    f.update({"slug": _slug(padecimiento), "padecimiento": padecimiento, "sistema": sistema, "fuentes": len(frags)})
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--rehacer", action="store_true")
    a = ap.parse_args()
    out = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    items = [(p, s) for s, ps in PADECIMIENTOS.items() for p in ps]
    pend = items if a.rehacer else [(p, s) for p, s in items if _slug(p) not in out]
    if a.limit:
        pend = pend[:a.limit]
    print(f"total={len(items)} hechos={len(out)} pendientes={len(pend)}")
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(gen, p, s): p for p, s in pend}
        done = 0
        for fut in as_completed(futs):
            f = fut.result(); done += 1
            if f:
                with _lock:
                    out[f["slug"]] = f
                    if done % 8 == 0:
                        json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print(f"  [{done}/{len(pend)}] {f['padecimiento']} OK ({f['fuentes']} fuentes)")
            else:
                print(f"  [{done}/{len(pend)}] FALLO")
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"LISTO recetario: {len(out)} padecimientos")


if __name__ == "__main__":
    main()
