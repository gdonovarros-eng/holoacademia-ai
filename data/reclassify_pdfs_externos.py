#!/usr/bin/env python3
"""
reclassify_pdfs_externos.py
Mueve pares mal zonificados del bloque "PDFs Externos" a su zona correcta.
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
# usar None como destino = eliminar (duplicado)
MOVES = [
    # ── Cabeza > Lateral ──────────────────────────────────────────────────────
    ("Cabeza",    "Lateral",    "Aurículo Ventricular - Riñón Izquierdo",         "Tronco",  "Tórax"),

    # ── Cabeza > Rostro ───────────────────────────────────────────────────────
    ("Cabeza",    "Rostro",     "Oído - Riñón Contralateral",                      "Cabeza",  "Lateral"),
    ("Cabeza",    "Rostro",     "Yunque - Riñón Ipsilateral",                      "Cabeza",  "Lateral"),
    ("Cabeza",    "Rostro",     "Seno Aurículo Ventricular - Riñón Izquierdo",     "Tronco",  "Tórax"),
    ("Cabeza",    "Rostro",     "Hioides - Hioides",                               "Cabeza",  "Cuello"),
    ("Cabeza",    "Rostro",     "Mango - Mango",                                   "Tronco",  "Tórax"),
    ("Cabeza",    "Rostro",     "Rama Isquion - Rama Isquion",                     "Pelvis",  "Delantera"),

    # ── Tronco > Tórax ────────────────────────────────────────────────────────
    ("Tronco",    "Tórax",      "Cardias - Cardias",                               "Tronco",  "Abdomen"),
    ("Tronco",    "Tórax",      "Cardias - Nervio Vago",                           "Tronco",  "Abdomen"),
    ("Tronco",    "Tórax",      "Vena Porta - Colon Transverso",                   "Tronco",  "Abdomen"),
    ("Tronco",    "Tórax",      "Vena Porta - Hígado",                             "Tronco",  "Abdomen"),
    ("Tronco",    "Tórax",      "Vena Porta - Tendón Pectoral",                    "Tronco",  "Abdomen"),
    ("Tronco",    "Tórax",      "Vena Porta - Páncreas",                           "Tronco",  "Abdomen"),
    ("Tronco",    "Tórax",      "Vena Porta - Vena Porta",                         "Tronco",  "Abdomen"),
    ("Tronco",    "Tórax",      "Plexo Cervical - Bulbo Raquídeo",                 "Cabeza",  "Cuello"),

    # ── Tronco > Abdomen ──────────────────────────────────────────────────────
    ("Tronco",    "Abdomen",    "Hipocampo - Hipocampo",                           "Cabeza",  "Coronilla"),

    # ── Pelvis > Delantera ────────────────────────────────────────────────────
    ("Pelvis",    "Delantera",  "Glándula Palatina - Riñón Lateral",               "Cabeza",  "Rostro"),
    ("Pelvis",    "Delantera",  "Infraaxilar - Infraaxilar",                       "Tronco",  "Tórax"),
    ("Pelvis",    "Delantera",  "Plexo Cervical - Entre Clavícula y Cuello",       "Cabeza",  "Cuello"),
    ("Pelvis",    "Delantera",  "Plexo Cervical - Sacro",                          "Cabeza",  "Cuello"),
    ("Pelvis",    "Delantera",  "Plexo Cervical - Útero",                          "Cabeza",  "Cuello"),
    ("Pelvis",    "Delantera",  "Plexo Dorsal - Plexo Dorsal",                     "Tronco",  "Espalda"),
    ("Pelvis",    "Delantera",  "Plexo Rodilla - Plexo Rodilla",                   "Miembros","Pierna"),
    ("Pelvis",    "Delantera",  "Primera Cervical - Primera Cervical",             "Extras",  "Columna Vertebral"),
    ("Pelvis",    "Delantera",  "Primera Cervical - Útero",                        "Cabeza",  "Cuello"),

    # ── Pelvis > Trasera ──────────────────────────────────────────────────────
    ("Pelvis",    "Trasera",    "Semimembranoso - Semimembranoso",                 "Miembros","Pierna"),
    ("Pelvis",    "Trasera",    "Útero - Sacro",                                   "Pelvis",  "Delantera"),
    ("Pelvis",    "Trasera",    "Vejiga - Sacro",                                  "Pelvis",  "Delantera"),

    # ── Pelvis > Sexo ─────────────────────────────────────────────────────────
    ("Pelvis",    "Sexo",       "Apéndice - Ovario Derecho",                       "Tronco",  "Abdomen"),
    ("Pelvis",    "Sexo",       "Uréter - Trompa",                                 "Tronco",  "Abdomen"),
    ("Pelvis",    "Sexo",       "Uréter Izquierdo - Recto",                        "Tronco",  "Abdomen"),
    ("Pelvis",    "Sexo",       "Uretero - Trompa de Falopio",                     "Tronco",  "Abdomen"),
    ("Pelvis",    "Sexo",       "Útero - Atlas",                                   "Pelvis",  "Delantera"),
    ("Pelvis",    "Sexo",       "Uretra - Sacro",                                  "Pelvis",  "Delantera"),

    # ── Miembros > Brazo ──────────────────────────────────────────────────────
    ("Miembros",  "Brazo",      "Pectoral Izquierdo - Tendón Cuádriceps Izquierdo","Tronco",  "Tórax"),

    # ── Miembros > Pierna ─────────────────────────────────────────────────────
    ("Miembros",  "Pierna",     "Apéndice - Nervio Femoral",                       "Tronco",  "Abdomen"),
    ("Miembros",  "Pierna",     "Apéndice - Gracilis Superior",                    "Tronco",  "Abdomen"),
    ("Miembros",  "Pierna",     "Apéndice - Cabeza de Fémur Derecha",              "Tronco",  "Abdomen"),
    ("Miembros",  "Pierna",     "Canal Medular - Canal Medular",                   "Extras",  "Columna Vertebral"),
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

    moved = 0
    skipped_dup = 0
    skipped_notfound = 0

    for (src_reg, src_zona, par, dst_reg, dst_zona) in MOVES:
        zona_src = get_zona(db, src_reg, src_zona)
        if not zona_src:
            print(f"  ⚠ Zona origen no encontrada: {src_reg} > {src_zona}")
            skipped_notfound += 1
            continue

        bloque_src = None
        for b in zona_src["bloques"]:
            if b["nombre"] == "PDFs Externos":
                bloque_src = b
                break

        if not bloque_src:
            print(f"  ⚠ Sin bloque 'PDFs Externos' en {src_reg} > {src_zona}")
            skipped_notfound += 1
            continue

        par_norm = _norm(par)
        found_par = None
        for p in bloque_src["pares"]:
            if _norm(p) == par_norm:
                found_par = p
                break

        if not found_par:
            print(f"  ⚠ Par no encontrado: «{par}» en {src_reg} > {src_zona}")
            skipped_notfound += 1
            continue

        zona_dst = get_zona(db, dst_reg, dst_zona)
        if not zona_dst:
            print(f"  ⚠ Zona destino no encontrada: {dst_reg} > {dst_zona}")
            skipped_notfound += 1
            continue

        norms_dst = all_norms_in_zona(zona_dst)
        if par_norm in norms_dst:
            bloque_src["pares"].remove(found_par)
            print(f"  🗑  Dup eliminado: «{found_par}» ({src_reg}>{src_zona})")
            moved += 1
            continue

        bloque_src["pares"].remove(found_par)
        bloque_dst = get_or_create_bloque(zona_dst, "PDFs Externos")
        bloque_dst["pares"].append(found_par)
        print(f"  ✔ {src_reg}>{src_zona} → {dst_reg}>{dst_zona}  «{found_par}»")
        moved += 1

    # Limpiar bloques "PDFs Externos" vacíos
    for reg in db["regiones"]:
        for zona in reg["zonas"]:
            zona["bloques"] = [
                b for b in zona["bloques"]
                if not (b["nombre"] == "PDFs Externos" and len(b["pares"]) == 0)
            ]

    total = sum(
        len(b["pares"])
        for reg in db["regiones"]
        for zona in reg["zonas"]
        for b in zona["bloques"]
    )
    db["total"] = total

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Reclasificación PDFs Externos completada:")
    print(f"   Pares movidos/limpiados : {moved}")
    print(f"   No encontrados          : {skipped_notfound}")
    print(f"   Total DB                : {total}")


if __name__ == "__main__":
    main()
