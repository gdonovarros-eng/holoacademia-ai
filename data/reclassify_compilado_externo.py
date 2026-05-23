#!/usr/bin/env python3
"""
reclassify_compilado_externo.py
Mueve pares mal zonificados del bloque "Compilado Externo" a su zona correcta.
"""

import json, unicodedata, re
from pathlib import Path

DB_PATH = Path(__file__).parent / "biomagnetic_pairs_db.json"

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[\s\-/]+", " ", s)
    return s.strip()

# ── Movimientos: (region_origen, zona_origen, par_exacto, region_destino, zona_destino)
MOVES = [
    # ── Cabeza > Coronilla → Cabeza > Posterior ──────────────────────────────
    ("Cabeza", "Coronilla", "Apófisis Mastoides - Riñón Izquierdo",         "Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Apófisis Mastoides - Clavícula",                "Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Apófisis Mastoides Izquierda - Riñón Izquierdo","Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Articulación Temporooccipital - Temporooccipital","Cabeza","Posterior"),
    ("Cabeza", "Coronilla", "Bulbo Raquídeo - Cerebelo",                     "Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Bulbo Raquídeo - Cerebelo Conducta",            "Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Cerebelo - Cola de Caballo",                    "Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Cerebelo - Hipófisis",                          "Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Cerebelo - Piso Orbital",                       "Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Cerebelo - Riñón",                              "Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Cerebelo - Supraespinoso",                      "Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Cerebelo - Yeyuno",                             "Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Cerebelo - Bulbo Raquídeo Newcastle",           "Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Cerebelo Izquierdo - Cerebelo Izquierdo",       "Cabeza", "Posterior"),
    ("Cabeza", "Coronilla", "Cisura Temporooccipital - Cisura Temporooccipital","Cabeza","Posterior"),

    # ── Cabeza > Coronilla → Cabeza > Lateral ────────────────────────────────
    ("Cabeza", "Coronilla", "Arco Cigomático - Parietal",                    "Cabeza", "Lateral"),

    # ── Cabeza > Coronilla → Cabeza > Frente ─────────────────────────────────
    ("Cabeza", "Coronilla", "Ceja - Sincicial Respiratorio",                 "Cabeza", "Frente"),
    ("Cabeza", "Coronilla", "Ceja Derecha - Hígado",                         "Cabeza", "Frente"),

    # ── Cabeza > Coronilla → Cabeza > Rostro ─────────────────────────────────
    ("Cabeza", "Coronilla", "Hemangioma - Lengua",                           "Cabeza", "Rostro"),
    ("Cabeza", "Coronilla", "Dental - Riñón Mismo Lado",                     "Cabeza", "Rostro"),
    ("Cabeza", "Coronilla", "Dental Derecho - Riñón Derecho",                "Cabeza", "Rostro"),
    ("Cabeza", "Coronilla", "Dental Izquierdo - Riñón Izquierdo",            "Cabeza", "Rostro"),

    # ── Cabeza > Coronilla → Cabeza > Cuello ─────────────────────────────────
    ("Cabeza", "Coronilla", "Cervical - Cisura Media",                       "Cabeza", "Cuello"),
    ("Cabeza", "Coronilla", "Clavícula Media Derecha - Submaxilar Izquierdo","Cabeza", "Cuello"),
    ("Cabeza", "Coronilla", "Clavícula Media Izquierda - Submaxilar Derecho","Cabeza", "Cuello"),
    ("Cabeza", "Coronilla", "Epoglotis - Nariz",                             "Cabeza", "Cuello"),
    ("Cabeza", "Coronilla", "Esternocleidomastoideo Derecho - Mastoides",    "Cabeza", "Cuello"),
    ("Cabeza", "Coronilla", "Esternocleidomastoideo Izquierdo - Hipófisis",  "Cabeza", "Cuello"),

    # ── Cabeza > Coronilla → Tronco > Abdomen ────────────────────────────────
    ("Cabeza", "Coronilla", "Cabeza de Páncreas - Páncreas",                 "Tronco", "Abdomen"),
    ("Cabeza", "Coronilla", "Colon Transverso - Parietal",                   "Tronco", "Abdomen"),
    ("Cabeza", "Coronilla", "Cardias - Temporal Derecho",                    "Tronco", "Abdomen"),

    # ── Cabeza > Coronilla → Pelvis > Delantera ──────────────────────────────
    ("Cabeza", "Coronilla", "Cabeza de Fémur - Cabeza de Fémur",             "Pelvis", "Delantera"),

    # ── Cabeza > Lateral → Cabeza > Frente ───────────────────────────────────
    ("Cabeza", "Lateral",   "Complejo Hipófisis Bulbo - Raquídeo Diabetes",  "Cabeza", "Frente"),
    ("Cabeza", "Lateral",   "Complejo Hipófisis Suprarrenales - Misheles",   "Cabeza", "Frente"),

    # ── Cabeza > Lateral → Pelvis > Delantera ────────────────────────────────
    ("Cabeza", "Lateral",   "Cresta Iliaca Frontal Derecha - Perone Lateral","Pelvis", "Delantera"),

    # ── Cabeza > Frente → Cabeza > Coronilla ─────────────────────────────────
    ("Cabeza", "Frente",    "Tálamo - Hipófisis",                            "Cabeza", "Coronilla"),
    ("Cabeza", "Frente",    "Tálamo - Corteza",                              "Cabeza", "Coronilla"),
    ("Cabeza", "Frente",    "Tálamo - Amígdala",                             "Cabeza", "Coronilla"),

    # ── Cabeza > Cuello → Pelvis > Delantera ─────────────────────────────────
    ("Cabeza", "Cuello",    "Cuello de Fémur Derecho - Calcáneo Izquierdo",  "Pelvis", "Delantera"),

    # ── Pelvis > Delantera → Cabeza > Cuello ─────────────────────────────────
    ("Pelvis", "Delantera", "Carótica Yugular - Streptococcus Pneumoniae",   "Cabeza", "Cuello"),

    # ── Pelvis > Trasera → Miembros > Brazo ──────────────────────────────────
    ("Pelvis", "Trasera",   "Braquial Derecho - Braquial Izquierdo",         "Miembros","Brazo"),

    # ── Pelvis > Sexo → otras zonas ──────────────────────────────────────────
    ("Pelvis", "Sexo",      "Cervical - Útero",                              "Pelvis", "Delantera"),
    ("Pelvis", "Sexo",      "Estómago - Próstata",                           "Tronco", "Abdomen"),
    ("Pelvis", "Sexo",      "Glúteo Izquierdo - Tendón Aquiles Derecho",     "Pelvis", "Trasera"),
]


def get_zona(db, region_nombre, zona_nombre):
    for reg in db["regiones"]:
        if reg["nombre"] == region_nombre:
            for zona in reg["zonas"]:
                if zona["nombre"] == zona_nombre:
                    return zona
    return None


def get_or_create_bloque(zona_obj, bloque_nombre):
    for b in zona_obj["bloques"]:
        if b["nombre"] == bloque_nombre:
            return b
    new_b = {
        "id": f"{zona_obj['id']}.{len(zona_obj['bloques']) + 1}",
        "nombre": bloque_nombre,
        "pares": []
    }
    zona_obj["bloques"].append(new_b)
    return new_b


def all_norms_in_zona(zona_obj):
    norms = set()
    for b in zona_obj["bloques"]:
        for p in b["pares"]:
            norms.add(_norm(p))
    return norms


def main():
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)

    moved   = 0
    skipped_dup   = 0
    skipped_notfound = 0

    for (src_reg, src_zona, par, dst_reg, dst_zona) in MOVES:
        # Buscar en bloque "Compilado Externo" de la zona origen
        zona_src = get_zona(db, src_reg, src_zona)
        if not zona_src:
            print(f"  ⚠ Zona origen no encontrada: {src_reg} > {src_zona}")
            skipped_notfound += 1
            continue

        bloque_src = None
        for b in zona_src["bloques"]:
            if b["nombre"] == "Compilado Externo":
                bloque_src = b
                break

        if not bloque_src:
            print(f"  ⚠ Sin bloque 'Compilado Externo' en {src_reg} > {src_zona}")
            skipped_notfound += 1
            continue

        # Buscar el par exacto (o normalizado)
        par_norm = _norm(par)
        found_par = None
        for p in bloque_src["pares"]:
            if _norm(p) == par_norm:
                found_par = p
                break

        if not found_par:
            print(f"  ⚠ Par no encontrado en {src_reg} > {src_zona}: «{par}»")
            skipped_notfound += 1
            continue

        # Verificar si el par ya existe en zona destino
        zona_dst = get_zona(db, dst_reg, dst_zona)
        if not zona_dst:
            print(f"  ⚠ Zona destino no encontrada: {dst_reg} > {dst_zona}")
            skipped_notfound += 1
            continue

        norms_dst = all_norms_in_zona(zona_dst)
        if par_norm in norms_dst:
            # Ya existe en destino → solo eliminar del origen
            bloque_src["pares"].remove(found_par)
            print(f"  🗑  Duplicado eliminado de origen: «{found_par}» ({src_reg}>{src_zona})")
            moved += 1
            continue

        # Mover: quitar del origen, añadir al destino
        bloque_src["pares"].remove(found_par)
        bloque_dst = get_or_create_bloque(zona_dst, "Compilado Externo")
        bloque_dst["pares"].append(found_par)
        print(f"  ✔ {src_reg}>{src_zona} → {dst_reg}>{dst_zona}  «{found_par}»")
        moved += 1

    # Limpiar bloques "Compilado Externo" vacíos
    for reg in db["regiones"]:
        for zona in reg["zonas"]:
            zona["bloques"] = [
                b for b in zona["bloques"]
                if not (b["nombre"] == "Compilado Externo" and len(b["pares"]) == 0)
            ]

    # Recalcular total
    total = sum(
        len(b["pares"])
        for reg in db["regiones"]
        for zona in reg["zonas"]
        for b in zona["bloques"]
    )
    db["total"] = total

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Reclasificación completada:")
    print(f"   Pares movidos/limpiados : {moved}")
    print(f"   No encontrados          : {skipped_notfound}")
    print(f"   Total DB                : {total}")


if __name__ == "__main__":
    main()
