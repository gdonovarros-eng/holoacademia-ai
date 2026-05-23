#!/usr/bin/env python3
"""Construye la cola de pares que necesitan enriquecimiento web.
Prioriza pares sin tipo/patógeno/descripción."""
import json, os
from datetime import datetime

PROJECT = "/Users/highdata/Desktop/New Project"

with open(f"{PROJECT}/data/pares_clasificacion.json") as f:
    data = json.load(f)

queue = []
for c in data["clasificaciones"]:
    tiene_tipo = bool(c.get("tipo"))
    tiene_pat = bool(c.get("patogeno"))
    tiene_desc = bool(c.get("descripcion") or c.get("enfermedades_reales"))

    # Prioridad: cuántos campos le faltan
    falta = sum([not tiene_tipo, not tiene_pat, not tiene_desc])
    if falta == 0:
        continue  # ya tiene todo

    queue.append({
        "region": c["region"],
        "zona": c["zona"],
        "bloque": c["bloque"],
        "par": c["par"],
        "tipo_actual": c.get("tipo"),
        "patogeno_actual": c.get("patogeno"),
        "descripcion_actual": c.get("descripcion"),
        "campos_faltantes": [
            f for f, t in [("tipo", tiene_tipo), ("patogeno", tiene_pat), ("descripcion", tiene_desc)]
            if not t
        ],
        "prioridad": falta,  # 1-3, mayor = más falta
        "enriquecido": False,
    })

# Ordenar: primero los que más les falta (3 = todo), luego los de menos
queue.sort(key=lambda x: (-x["prioridad"], x["region"], x["par"]))

out = {
    "version": "1.0",
    "generado": datetime.now().isoformat(),
    "total": len(queue),
    "por_prioridad": {
        "p3_sin_nada": sum(1 for q in queue if q["prioridad"]==3),
        "p2_falta_2":  sum(1 for q in queue if q["prioridad"]==2),
        "p1_falta_1":  sum(1 for q in queue if q["prioridad"]==1),
    },
    "queue": queue,
}

with open(f"{PROJECT}/data/web_enrichment_queue.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"Cola creada: {len(queue)} pares pendientes")
print(f"  Sin tipo, patógeno NI descripción: {out['por_prioridad']['p3_sin_nada']}")
print(f"  Faltan 2 campos: {out['por_prioridad']['p2_falta_2']}")
print(f"  Falta 1 campo:  {out['por_prioridad']['p1_falta_1']}")
print(f"\nGuardado en: data/web_enrichment_queue.json")

# Mostrar primeros 5
print("\nPrimeros 5 a enriquecer:")
for q in queue[:5]:
    faltan = ", ".join(q["campos_faltantes"])
    print(f"  [{q['region']}>{q['zona']}>{q['bloque']}] {q['par']!r}  (falta: {faltan})")
