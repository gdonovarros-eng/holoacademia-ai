"""
consolidate_external_pairs.py
Extrae pares visibles del Atlas Consolidado (Pares_Biomagneticos_Consolidado.pdf)
y los integra al biomagnetic_pairs_db.json eliminando duplicados.

Fuente: Atlas Consolidado de Pares Biomagnéticos
        Compilación documental de 5 fuentes especializadas — Gerardo Donovarros, mayo 2026
        20 páginas disponibles (muestra parcial de 2,036 pares totales)

Resultado:
- Se conserva íntegramente la estructura Holoacademia (v2.0, 371 pares)
- Se agregan pares nuevos extraídos de páginas visibles del Consolidado
- Pares duplicados (coincidencia normalizada) se eliminan
"""

import json
import unicodedata
import re
from pathlib import Path

DB_PATH = Path(__file__).parent / "biomagnetic_pairs_db.json"

# ─── Pares visibles extraídos del Atlas Consolidado ──────────────────────────
# Organizados por la región/zona destino del DB de Holoacademia
# Cada entrada es el string del par (mismo formato que el DB)
# OCR artifacts normalizados manualmente

EXTERNAL_PAIRS = {
    # ── CABEZA > CUELLO ───────────────────────────────────────────────────────
    # De las páginas 9-11 del Consolidado (región "Cuello", 70 pares, casi todos visibles)
    "Cabeza:Cuello": [
        # Angina / Garganta
        "Angina - Angina",
        "Angina - Herpes 2",
        "Angina - Laringe Derecha",
        "Garganta - Vejiga",
        "Laringe - Laringe",
        "Laringe - Tabique Nasal",
        "Laringe - Duodeno",
        "Laringe - Bordetella Pertussis",
        # Tiroides / Paratiroides
        "Tiroides - Tiroides",
        "Tiroides - Timo",
        "Tiroides - Tallo Cerebral",
        "Tiroides - Bulbo Raquídeo",
        "Tiroides - Duodeno",
        "Tiroides - Cuádriceps Izquierdo",
        "Tiroides - Escápula Derecha",
        "Tiroides - Disfunción Tiroides",
        "Tiroides Derecha - Paratiroides Izquierda",
        "Paratiroides Derecha - Riñón Derecho",
        "Paratiroides Derecho - Corazón",
        "Paratiroides Derecho - Tiroides 1ra",
        "Paratiroides - Paratiroides",
        "Pómulo Derecho - Tiroides",
        "Pómulo - Tiroides",
        "Riñón Izquierdo - Tiroides",
        # Esternocleidomastoideo
        "Esternocleidomastoideo Derecho - Clavícula",
        "Esternocleidomastoideo Derecho - Piloro",
        "Esternocleidomastoideo Derecho - Timo",
        "Esternocleidomastoideo Izquierdo - Esternón",
        "Esternocleidomastoideo Izquierdo - Riñón",
        "Esternocleidomastoideo Izquierdo - Clavícula",
        # Cuello de fémur
        "Cuello de Fémur - Cuello de Fémur",
        "Cuello de Fémur Derecho - Calcáneo Izquierdo",
        # Conductos
        "Bulbo Raquídeo - Tiroides",
        "Cervical 1 - Esternocleidomastoideo Derecho",
        "Conducto Eferente - Laringe",
        "Conducto Eferente - Laringe Rotavirus",
        # Otros cuello
        "Cuello - Cuello",
        "Cuello - Blastocystis Hominis",
        "Cuello - Pneumocystis Carini",
        "Duodeno - Laringe",
        "Duodeno - Tiroides",
        "Duodeno Tiroides - Obesidad Extrema",
        "Esófago - Subclavia",
        "Estómago - Subclavia Derecha",
        "Hipófisis - Tiroides",
        "Hueco Garganta - Glúteo Izquierdo",
        "Muñeca Derecha - Tiroides",
        "Subclavia - Subclavia",
        "Subclavia - Bacilo Difteroide",
        "Testículo - Angina",
        "Testículo Derecho - Angina",
        "Testículo - Garganta",
        "Vagina - Angina",
        "Vagina - Garganta",
        "Vagina - Garganta - Testículo",
        "Vesícula - Paratiroides",
        "Tráquea - Corazón",
        "Tráquea - Tráquea",
    ],

    # ── CABEZA > CORONILLA (pares de Cabeza visibles en Consolidado p.6-8) ───
    "Cabeza:Coronilla": [
        "Hemangioma - Lengua",
        "Amígdala Cerebral - Amígdala Cerebral",
        "Apófisis Mastoides - Riñón Izquierdo",
        "Apófisis Mastoides - Clavícula",
        "Apófisis Mastoides Izquierda - Riñón Izquierdo",
        "Arco Cigomático - Parietal",
        "Articulación Temporooccipital - Temporooccipital",
        "Bulbo - Cerebelo",
        "Bulbo Raquídeo - Pineal",
        "Bulbo Raquídeo - Cerebelo",
        "Bulbo Raquídeo - Cerebelo Conducta",
        "Cabeza de Páncreas - Páncreas",
        "Cabeza de Fémur - Cabeza de Fémur",
        "Capitis - Capitis",
        "Cardias - Temporal Derecho",
        "Ceja - Ceja",
        "Ceja - Sincicial Respiratorio",
        "Ceja Derecha - Hígado",
        "Cerebelo - Cerebelo",
        "Cerebelo - Cola de Caballo",
        "Cerebelo - Hipófisis",
        "Cerebelo - Piso Orbital",
        "Cerebelo - Riñón",
        "Cerebelo - Supraespinoso",
        "Cerebelo - Yeyuno",
        "Cerebelo - Bulbo Raquídeo Newcastle",
        "Cerebro - Riñón Mismo Lado",
        "Cervical - Cisura Media",
        "Cerebelo Izquierdo - Cerebelo Izquierdo",
        "Cisura de Silvio - Cisura de Silvio",
        "Cisura Lambda - Cisura Lambda",
        "Cisura Media - Cisura Media",
        "Cisura Silvio - Cisura Silvio",
        "Cisura Temporooccipital - Cisura Temporooccipital",
        "Clavícula Media Derecha - Submaxilar Izquierdo",
        "Clavícula Media Izquierda - Submaxilar Derecho",
        "Colon Transverso - Parietal",
        "Corona - Hipófisis",
        "Corona Hipófisis - Depresión",
        "Cuerpo Calloso Derecho - Cerebelo",
        "Dental - Riñón Mismo Lado",
        "Dental Derecho - Riñón Derecho",
        "Dental Izquierdo - Riñón Izquierdo",
        "Epoglotis - Nariz",
        "Esternocleidomastoideo Derecho - Mastoides",
        "Esternocleidomastoideo Izquierdo - Hipófisis",
    ],

    # ── CABEZA > LATERAL (más pares de Cabeza) ────────────────────────────────
    "Cabeza:Lateral": [
        "Cisura Silvio - Percepción",
        "Conducto Oído - Conducto Oído",
        "Cresta Iliaca Frontal Derecha - Perone Lateral",
        "Complejo Hipófisis Bulbo - Raquídeo Diabetes",
        "Complejo Hipófisis Suprarrenales - Misheles",
    ],

    # ── CABEZA > FRENTE ───────────────────────────────────────────────────────
    "Cabeza:Frente": [
        "Hipófisis - Hipófisis",
        "Hipófisis - Suprarrenales",
        "Tálamo - Tálamo",
        "Tálamo - Hipófisis",
        "Tálamo - Corteza",
        "Tálamo - Amígdala",
        "Hipotálamo - Hipotálamo",
        "Hipotálamo - Tiroides",
        "Hipotálamo - Sacro",
    ],

    # ── TRONCO > TÓRAX ────────────────────────────────────────────────────────
    # De las páginas 12-14 del Consolidado (región "Tórax", 192 pares, ~80 visibles)
    "Tronco:Tórax": [
        "Corazón - Costilla Falsa Izquierda",
        "Corazón - Estómago",
        "Corazón - Hígado",
        "Corazón - Riñón",
        "Corazón - Suprapópleo",
        "Corazón - Afín Izquierdo",
        "Corazón - Esternón",
        "Corazón - Corazón Negatividad",
        "Corazón - Páncreas",
        "Corazón - Vejiga",
        "Corazón - Escápula Izquierda",
        "Corazón - Ira Explosiva",
        "Arteria Axilar - Arteria Axilar",
        "Arteria Axilar Derecha - Arteria Axilar Izquierda",
        "Axila - Timo",
        "Bazo - Pulmón",
        "Bazo - Timo",
        "Botón Aórtico - Pericardio",
        "Bronquio - Bronquio",
        "Bronquio Derecho - Pericardio",
        "Bulbo Raquídeo - Corazón",
        "Bulbo Raquídeo - Corazón Crueldad",
        "Cardias - Corazón",
        "Cardias - Esófago",
        "Cardias - Píloro",
        "Cardias - Suprarrenal",
        "Cardias - Testículo",
        "Cardias - Testículo Derecho",
        "Cardias - Apéndice",
        "Cardias - Coronarias",
        "Cardias - Esófago Disfunción",
        "Cardias - Suprarrenales Bacteria",
        "Cardias - Testículo Derecho Izquierdo",
        "Cardias - Vagina",
        "Cardias - Vejiga Derecha",
        "Cardias - Suprarrenales Streptococcus",
        "Carótida - Aorta",
        "Cava - Cava",
        "Cava - Timo",
        "Cava - Cava Ansiedad",
        "Cava Derecha - Plexo Cervical Izquierdo",
        "Cava Izquierda - Plexo Cervical Derecho",
        "Clítoris - Timo",
        "Colón Descendente - Pulmón Izquierdo",
        "Condral Derecho - Bronquio Derecho",
        "Corazón - Afín Izquierdo",
        "Coronaria - Pulmón",
        "Coronaria - Tendón Pectoral",
        "Coronarias - Pulmón",
        "Coronarias - Pulmón Streptococcus",
        "Coronarias Pulmón - Streptococcus Alfa",
        "Costillas 1 al 12 - Riñón",
        "Cuerpo de Páncreas - Corazón",
        "ECM - Timo",
        "Escápula Derecha - Pulmón",
        "Esófago - Pulmón",
        "Esternocleidomastoideo Derecho - Esternón",
        "Esternón - Bazo",
        "Esternón - Suprarrenal",
        "Esternón - Suprarrenales",
        "Esternón - Timo",
        "Estómago - Corazón",
        "Estómago - Timo",
        "Apéndice - Pleura",
        "Apéndice - Timo",
        "Apéndice - Pleura Complejo",
        "Apéndice Pleura - Staphylococcus Aureus",
        "Aorta - Aorta",
        "1a Costilla - 1a Costilla",
        "7a Costilla - 7a Costilla",
        "1a Costilla - Vejiga",
        "Corazón - Corazón Amargura",
        "CORON ARIA - Tendón Pectoral",
    ],

    # ── TRONCO > ABDOMEN ──────────────────────────────────────────────────────
    # De las páginas 15-17 del Consolidado (región "Abdomen", 563 pares, ~80 visibles)
    "Tronco:Abdomen": [
        "Bazo - Bazo",
        "Bazo - Duodeno",
        "Bazo - Hígado",
        "Bazo - Riñón",
        "Bazo - Suprarrenales",
        "Bazo - Vejiga",
        "Bazo Bazo - Yersinia Pestis",
        "Bazo Bazo - Leucemia",
        "Bazo Hígado - Brucella Abortus",
        "Bazo Punta del Páncreas - Verruga",
        "Borde Costal - Hígado",
        "Bulbo Raquídeo - Colon Descendente",
        "Cápsula Glisson - Píloro",
        "Cápsula Renal - Cápsula Renal",
        "Cápsula Renal Derecha - Riñón Derecho",
        "Cápsula Renal Derecha - Riñón Izquierdo",
        "Cápsula Renal Derecha - Vejiga",
        "Cápsula Renal Derecha - Vesícula",
        "Ciego - Hígado",
        "Ciego - Riñón",
        "Ciego - Riñón Derecho",
        "Ciego Riñón Derecho - Trichomonas",
        "Cirrosis Hepática - Hígado Riñón",
        "Clítoris - Ano",
        "Cola de Páncreas - Colon Descendente",
        "Cola de Páncreas - Hígado",
        "Cola de Páncreas - Hígado Hepatitis",
        "Cola de Páncreas - Punta de Páncreas",
        "Cola de Páncreas - Riñón Ipsilateral",
        "Cola de Páncreas - Riñón Izquierdo",
        "Cola de Páncreas - Hígado Complejo",
        "Ano - Ano",
        "Ano - Colon Ascendente",
        "Ano - Próstata",
        "Ano - Píloro",
        "Ano - Testículo",
        "Ano Ano - Papiloma",
        "Ano Píloro - Levadura",
        "Ano Testículo - Izquierdo Ecuador",
        "Apéndice - Testículo Bilateral",
        "Apéndice - Testículo Derecho",
        "Apéndice - Uretra",
        "Apéndice - Vagina",
        "Apéndice - Testículo Hongo",
        "Apófisis Mastoides - Duodeno",
        "Apófisis Mastoides - Riñón Ipsilateral",
        "Apófisis Mastoides Izquierda - Riñón Izquierdo",
        "Área Visual - Riñón",
        "Articulación - Riñón Derecho",
        "Ascendente - Hígado",
        "Ascendente - Riñón Derecho",
        "Atlas - Píloro",
        "Atlas Píloro - Plasmodium Falciparum",
        "Auriculoventricular - Riñón Izquierdo",
        "Bazo - Bazo Horizontal Yersinia",
        "Bazo - Bazo Vertical Leucemia",
        "Cabeza de Páncreas - Estómago",
        "Cabeza de Páncreas - Hígado",
        "Cabeza de Páncreas - Hígado Hepatitis",
        "Cabeza de Páncreas - Pleura",
        "Cabeza de Páncreas - Punta de Páncreas",
        "Cabeza de Páncreas - Píloro",
        "Cabeza de Páncreas - Suprarrenales",
        "Cabeza de Páncreas - Vejiga Izquierda",
        "Cabeza Páncreas - Suprarrenales Staphylococcus",
        "Capsula Renal - Riñón Mismo Lado",
        "Capsula Renal Derecha - Riñón Izquierdo Reservorio",
        "Carina - Ano",
        "Cervical 1 - Píloro",
        "Cervical 1 - Píloro Plasmodium",
        "Cervical 1 - Piloro",
        "Cervical 78 Dorsal - Pasciano",
        "Cervical - Cápsula Renal",
        "Cervicales - Riñón Derecho Izquierdo",
        "Cervicales - Riñones",
        "Cervicales - Suprarrenales",
        "CICATRIZ - Riñón",
    ],

    # ── PELVIS ────────────────────────────────────────────────────────────────
    # De las páginas 18-20 del Consolidado (región "Pelvis", 187 pares, ~80 visibles)
    "Pelvis:Delantera": [
        "Atlas - Testículo",
        "Atlas - Útero",
        "Atlas Útero - Linda Celos",
        "Articulación Sacroilíaca - Articulación Sacroilíaca",
        "Articulación - Nervio Inguinal",
        "Bulbo Raquídeo - Vejiga",
        "Bulbo Raquídeo - Vejiga Dengue",
        "Cáliz Renal - Uretero",
        "Cáliz Renal - Uretero Herpes",
        "Cáliz Renal - Uretero ADNpatógeno",
        "Carótica Yugular - Streptococcus Pneumoniae",
        "Cervical 1 - Coxis",
        "Cervical 3 - Sacro Parasimpático",
        "Cervical - Sacro Contralateral",
        "Cervicales - Sacro",
        "Cervicales - Utero",
        "Ciático Derecho - Útero",
        "Clítoris - Uretra",
        "Clítoris - Pelvis Hueso Pélvico",
        "Clítoris - Sacro",
        "Colón Transverso - Vejiga",
        "Conducto Eferente - Sacro",
        "Coxis - Ciática",
        "Coxis - Ciático",
        "Coxis - Coxis Vertical",
        "Coxis - Plexo Cervical",
        "Coxis Ciático - Calambres Piernas",
        "Coxis Plexo - Cervical Ácido",
        "Cérvico - Útero",
        "Cérvico Cérvico - Útero Insomnio",
        "Cérvico Útero - Infección Vaginal",
        "Dorsal 6 - Sacro",
        "e + Trompa - Trompa",
        "e Glúteo - Glúteo",
        "Epiplón - Epiplón Staphylococcus",
        "Esfínter Uretral - Esfínter Uretral",
        "Esfínter de la Uretra - Esfínter",
        "Esfínter Uretra - Esfínter Uretra",
        "Estómago - Próstata o Vagina",
        "Esófago - Vejiga Izquierda",
        "Gen - Vejiga",
        "Glúteo - Glúteo",
        "Glúteo - Vena Femoral",
        "Glúteo Derecho - Hiato",
        "Glúteo Izquierdo - Aquiles Izquierdo",
        "Glúteo Izquierdo - Aquiles",
        "Glúteo Izquierdo - Hiato",
        "Glúteo Medio - Glúteo Medio",
    ],
    "Pelvis:Trasera": [
        "Glúteo Medio - Vena Femoral",
        "Glúteo Menor Derecho - Sacro",
        "Glúteo - Ganglios Mesentéricos",
        "Glúteo - Glúteo Bacteria",
        "Glúteo - Hiato",
        "Glúteo Vena - Femoral Babesia",
        "Hiato - Testículo Izquierdo",
        "Hiato - Testículo",
        "Hiato - Testículo Derecho",
        "Hiato - Vagina",
        "HIATO ESOFÁGICO - Vagina",
        "Hiato Esofágico - Testículo Derecho",
        "Hiporasis - Útero",
        "Hipotálamo - Sacro",
        "HIPÓFISIS - Útero",
        "Hoyuelo del Glúteo Derecho - Lumbar 2",
        "Hoyuelo del Glúteo Izquierdo - Lumbar 2",
        "Hoyuelo del Glúteo - Lumbar 2",
        "Hueco - Glúteo Izquierdo",
        "154 + Sacro - Sacro",
        "5 + Cáliz - Uretra",
        "Braquial Derecho - Braquial Izquierdo",
    ],
    "Pelvis:Sexo": [
        "Apéndice - Testículo Derecho",
        "Apéndice - Vagina",
        "Apéndice - Uretra",
        "Cervical - Útero",
        "Cervical 1 - Coxis",
        "Clítoris - Uretra",
        "Colón Transverso - Vejiga",
        "Esfínter Uretra - Esfínter Uretra",
        "Estómago - Próstata",
        "Gen - Vejiga",
        "Glúteo Izquierdo - Tendón Aquiles Derecho",
        "Hiato - Testículo",
        "Hiato - Vagina",
        "HIATO ESOFÁGICO - Vagina",
        "HIPÓFISIS - Útero",
    ],
}


# ─── Normalización para deduplicación ────────────────────────────────────────

def _normalize(s: str) -> str:
    """Convierte a minúsculas, elimina acentos y normaliza espacios."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[\s\-/]+", " ", s)
    s = s.strip()
    return s


def _all_existing_pairs(db: dict) -> set[str]:
    """Devuelve un set de pares normalizados ya en el DB."""
    pairs = set()
    for reg in db["regiones"]:
        for zona in reg["zonas"]:
            for bloque in zona["bloques"]:
                for par in bloque["pares"]:
                    pairs.add(_normalize(par))
    return pairs


# ─── Función principal ───────────────────────────────────────────────────────

def consolidate():
    with open(DB_PATH) as f:
        db = json.load(f)

    existing = _all_existing_pairs(db)
    added = 0
    skipped_dup = 0

    # Índice rápido: region_nombre → zona_nombre → zona_objeto
    region_idx: dict[str, dict] = {}
    for reg in db["regiones"]:
        region_idx[reg["nombre"]] = {}
        for zona in reg["zonas"]:
            region_idx[reg["nombre"]][zona["nombre"]] = zona

    def get_or_create_bloque(zona_obj, bloque_nombre: str) -> dict:
        for b in zona_obj["bloques"]:
            if b["nombre"] == bloque_nombre:
                return b
        # Crear nuevo bloque
        new_b = {
            "id": f"{zona_obj['id']}.{len(zona_obj['bloques']) + 1}",
            "nombre": bloque_nombre,
            "pares": []
        }
        zona_obj["bloques"].append(new_b)
        return new_b

    for dest_key, pairs_list in EXTERNAL_PAIRS.items():
        region_nombre, zona_nombre = dest_key.split(":")

        if region_nombre not in region_idx:
            print(f"  ⚠ Región no encontrada: {region_nombre}")
            continue

        region_zones = region_idx[region_nombre]
        if zona_nombre not in region_zones:
            print(f"  ⚠ Zona no encontrada: {region_nombre} > {zona_nombre}")
            continue

        zona_obj = region_zones[zona_nombre]
        bloque = get_or_create_bloque(zona_obj, "Compilado Externo")

        for par in pairs_list:
            norm = _normalize(par)
            if norm in existing:
                skipped_dup += 1
                continue
            # Verificar también dentro del bloque que estamos construyendo
            if norm in {_normalize(p) for p in bloque["pares"]}:
                skipped_dup += 1
                continue
            bloque["pares"].append(par)
            existing.add(norm)
            added += 1

    # Recalcular total
    total = sum(
        len(b["pares"])
        for reg in db["regiones"]
        for zona in reg["zonas"]
        for b in zona["bloques"]
    )

    # Limpiar bloques "Compilado Externo" vacíos
    for reg in db["regiones"]:
        for zona in reg["zonas"]:
            zona["bloques"] = [
                b for b in zona["bloques"]
                if not (b["nombre"] == "Compilado Externo" and len(b["pares"]) == 0)
            ]

    db["total"] = total
    db["version"] = "3.0"
    db["fuentes"] = [
        "Tablas Holoacademia - Alejandro Lavín (fuente primaria)",
        "Atlas Consolidado de Pares Biomagnéticos - Gerardo Donovarros (muestra parcial, 5 fuentes externas)",
    ]
    db["consolidacion"] = {
        "pares_holoacademia": 371,
        "pares_externos_agregados": added,
        "duplicados_eliminados": skipped_dup,
        "total_consolidado": total,
    }

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Consolidación completada:")
    print(f"   Pares Holoacademia base : 371")
    print(f"   Pares externos agregados: {added}")
    print(f"   Duplicados saltados     : {skipped_dup}")
    print(f"   TOTAL FINAL             : {total}")


if __name__ == "__main__":
    consolidate()
