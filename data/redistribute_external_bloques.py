#!/usr/bin/env python3
"""
redistribute_external_bloques.py
Distribuye todos los pares de bloques "Compilado Externo" y "PDFs Externos"
en sus bloques anatómicos correctos. Crea bloques nuevos cuando es necesario.
También realiza los pocos movimientos de zona que son evidentemente incorrectos.
"""

import json, unicodedata, re
from pathlib import Path

DB_PATH = Path(__file__).parent / "biomagnetic_pairs_db.json"

# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZACIÓN
# ─────────────────────────────────────────────────────────────────────────────
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[\s\-/]+", " ", s)
    return s.strip()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 1 — MOVIMIENTOS DE ZONA
# Pares que además de cambiar bloque deben cambiar de Zona DB.
# (region_origen, zona_origen, par_exacto, region_destino, zona_destino, bloque_destino)
# ─────────────────────────────────────────────────────────────────────────────
ZONE_MOVES = [
    # Frente Baja – estaban en Posterior porque el PDF los ponía al revés
    ("Cabeza", "Posterior", "Supraciliar - Bulbo Raquídeo",         "Cabeza",    "Frente",    "Frente Baja"),
    ("Cabeza", "Posterior", "Interciliar - Bulbo Raquídeo",         "Cabeza",    "Frente",    "Frente Baja"),
    # Amígdala cerebral (lóbulo temporal) → Lateral
    ("Cabeza", "Posterior", "Amígdala Cerebral - Timo",             "Cabeza",    "Lateral",   "Temporal"),
    # Parótida y Rama Mandibular Lateral → Lateral (no Rostro)
    ("Cabeza", "Rostro",    "Parótida - Timo",                      "Cabeza",    "Lateral",   "Parótida"),
    ("Cabeza", "Rostro",    "Parótida Izquierda - Pineal",          "Cabeza",    "Lateral",   "Parótida"),
    ("Cabeza", "Rostro",    "Rama Mandibular Lateral - Rama Mandibular Lateral", "Cabeza", "Lateral", "Mandibular"),
    # Glúteos en Delantera → Trasera
    ("Pelvis", "Delantera", "Glúteo Medio - Glúteo Medio",          "Pelvis",    "Trasera",   "Trasero"),
    ("Pelvis", "Delantera", "Glúteo - Vena Femoral",                "Pelvis",    "Trasera",   "Trasero"),
    ("Pelvis", "Delantera", "Glúteo Derecho - Hiato",               "Pelvis",    "Trasera",   "Trasero"),
    ("Pelvis", "Delantera", "Glúteo Izquierdo - Aquiles Izquierdo", "Pelvis",    "Trasera",   "Trasero"),
    ("Pelvis", "Delantera", "Glúteo Izquierdo - Aquiles",           "Pelvis",    "Trasera",   "Trasero"),
    ("Pelvis", "Delantera", "Glúteo Izquierdo - Hiato",             "Pelvis",    "Trasera",   "Trasero"),
    ("Pelvis", "Delantera", "e Glúteo - Glúteo",                    "Pelvis",    "Trasera",   "Trasero"),
    # Trompa (parseo deficiente "e +") → Sexo
    ("Pelvis", "Delantera", "e + Trompa - Trompa",                  "Pelvis",    "Sexo",      "Fémina B"),
    # Epiplón es peritoneal → Abdomen
    ("Pelvis", "Delantera", "Epiplón - Epiplón Staphylococcus",     "Tronco",    "Abdomen",   "Ombligo"),
    # Retrotensor Fascia Lata es músculo cadera/pierna → Pierna Alta
    ("Tronco", "Espalda",   "Retrotensor de la Fascia Lata - Rectoral", "Miembros", "Pierna", "Pierna Alta"),
]


# ─────────────────────────────────────────────────────────────────────────────
# FASE 2 — ASIGNACIÓN DE BLOQUE
# Para todos los pares que quedan en "Compilado Externo" / "PDFs Externos",
# se define aquí el bloque anatómico al que pertenecen.
# Formato: {(region, zona, par_norm): bloque_destino}
# ─────────────────────────────────────────────────────────────────────────────

def _k(region, zona, par):
    return (region, zona, _norm(par))


# Nuevos bloques que se crearán si no existen:
#   Cabeza > Coronilla  → "Cerebro"
#   Cabeza > Posterior  → "Mastoides"
#   Cabeza > Frente     → "Hipotálamo"
#   Cabeza > Rostro     → "Amígdalas"
#   Tronco > Abdomen    → "Riñón" , "Suprarrenal"
#   Pelvis > Delantera  → "Pubis Profundo"   (conexiones cervico-pélvicas)

BLOQUE_MAP = {}

# ────────── Cabeza > Coronilla ──────────────────────────────────────────────
C_COR = ("Cabeza", "Coronilla")
for par in [
    "Pineal - Bulbo Raquídeo", "Pineal - Útero", "Pineal - Hipófisis",
    "Pineal - Próstata", "Pineal - Duodeno", "Pineal - Puente de Varolo",
    "Post Pineal - Post Pineal", "Post Pineal - Bulbo Raquídeo",
    "Pineal - Empeine", "Pineal - Mama", "Pineal - Planta del Pie",
    "Pineal - Hígado", "Prepineal - Prepineal", "Prepolo - Bulbo Raquídeo",
    "Prepolo - Antepolo", "Bulbo Raquídeo - Pineal",
]:
    BLOQUE_MAP[_k(*C_COR, par)] = "Pineal"

for par in ["Corona - Hipófisis", "Corona Hipófisis - Depresión"]:
    BLOQUE_MAP[_k(*C_COR, par)] = "Corona"

for par in [
    "Cuerpo Calloso Derecho - Cerebelo", "Cisura Lambda - Cisura Lambda",
    "Cisura Silvio - Cisura Silvio", "Capitis - Capitis",
]:
    BLOQUE_MAP[_k(*C_COR, par)] = "Callosidad"

for par in [
    "Parietal - Riñón Contralateral",
    "Parietal Derecho Posterior - Parietal Derecho Posterior",
    "Parietales - Colon Transverso", "Tallo Parietal - Cerebelo",
]:
    BLOQUE_MAP[_k(*C_COR, par)] = "Parietal"

for par in [
    "Amígdala Cerebral - Amígdala Cerebral", "Cerebro - Riñón Mismo Lado",
    "Tálamo - Hipófisis", "Tálamo - Corteza", "Tálamo - Amígdala",
    "Hipocampo - Hipocampo",
]:
    BLOQUE_MAP[_k(*C_COR, par)] = "Cerebro"

# ────────── Cabeza > Posterior ──────────────────────────────────────────────
C_POST = ("Cabeza", "Posterior")
for par in [
    "Tallo Cerebral - Tallo Cerebral", "Cuarto Ventrículo - Bulbo",
]:
    BLOQUE_MAP[_k(*C_POST, par)] = "Bulbo"

for par in [
    "Occipital - Riñón", "Occipital - Testículo", "Base de Cráneo - Base de Cráneo",
    "Articulación Temporooccipital - Temporooccipital",
    "Cisura Temporooccipital - Cisura Temporooccipital",
]:
    BLOQUE_MAP[_k(*C_POST, par)] = "Occipital"

for par in [
    "Cerebelo - Arriba del Bulbo Raquídeo",
    "Bulbo Raquídeo - Cerebelo", "Bulbo Raquídeo - Cerebelo Conducta",
    "Cerebelo - Cola de Caballo", "Cerebelo - Hipófisis",
    "Cerebelo - Piso Orbital", "Cerebelo - Riñón",
    "Cerebelo - Supraespinoso", "Cerebelo - Yeyuno",
    "Cerebelo - Bulbo Raquídeo Newcastle", "Cerebelo Izquierdo - Cerebelo Izquierdo",
    "Articulación Temporooccipital - Temporooccipital",  # duplicado seguro en Occipital también
]:
    BLOQUE_MAP[_k(*C_POST, par)] = "Cerebelo"

for par in [
    "Apófisis Mastoides - Riñón Izquierdo", "Apófisis Mastoides - Clavícula",
    "Apófisis Mastoides Izquierda - Riñón Izquierdo",
    "Apófisis Mastoides - Bulbo", "Apófisis Mastoides - Pericardio",
    "Apófisis Mastoides - Apófisis Mastoides",
    "Apófisis Mastoides Izquierdas - Apófisis Mastoides Derecho",
]:
    BLOQUE_MAP[_k(*C_POST, par)] = "Mastoides"

# ────────── Cabeza > Lateral ────────────────────────────────────────────────
C_LAT = ("Cabeza", "Lateral")
for par in [
    "Temporal - Oído", "Temporal - Bulbo Raquídeo", "Temporal - Yugular",
    "Temporal Derecho - Temporal Derecho", "Temporal Izquierdo - Temporal Izquierdo",
    "Temporooccipital - Temporooccipital", "Cisura Silvio - Percepción",
    "Amígdala Cerebral - Timo",   # llegará aquí vía ZONE_MOVES
]:
    BLOQUE_MAP[_k(*C_LAT, par)] = "Temporal"

for par in [
    "Oído - Riñón Contralateral", "Yunque - Riñón Ipsilateral",
    "Conducto Oído - Conducto Oído", "Presín - Canal Auditivo",
]:
    BLOQUE_MAP[_k(*C_LAT, par)] = "Aurícula"

for par in [
    "Sien - Suprarrenal", "Sien - Riñón", "Sien Derecha - Sien Derecha",
    "Sien - Bulbo Raquídeo", "Ángulo Derecho - Ángulo Derecho",
]:
    BLOQUE_MAP[_k(*C_LAT, par)] = "Sien"

for par in [
    "Arco Cigomático - Arco Cigomático", "Arco Cigomático - Parietal",
    "Ángulo Gonión - Ángulo",
    "Rama Mandibular Lateral - Rama Mandibular Lateral",  # llega vía ZONE_MOVES
]:
    BLOQUE_MAP[_k(*C_LAT, par)] = "Mandibular"

for par in [
    "Parótida - Timo", "Parótida Izquierda - Pineal",   # llegan vía ZONE_MOVES
]:
    BLOQUE_MAP[_k(*C_LAT, par)] = "Parótida"

# ────────── Cabeza > Frente ─────────────────────────────────────────────────
C_FR = ("Cabeza", "Frente")
for par in [
    "Hipófisis - Suprarrenales",
    "Complejo Hipófisis Bulbo - Raquídeo Diabetes",
    "Complejo Hipófisis Suprarrenales - Misheles",
    "Adenohipofisis - Riñón Izquierdo",
    "Suprasensorial - Hipófisis",
]:
    BLOQUE_MAP[_k(*C_FR, par)] = "Hipófisis"

for par in [
    "Hipotálamo - Hipotálamo", "Hipotálamo - Tiroides",
    "Hipotálamo - Sacro",
]:
    BLOQUE_MAP[_k(*C_FR, par)] = "Hipotálamo"

for par in [
    "Ceja - Sincicial Respiratorio", "Ceja Derecha - Hígado",
    "Supraciliar - Bulbo Raquídeo", "Interciliar - Bulbo Raquídeo",  # llegan vía ZONE_MOVES
]:
    BLOQUE_MAP[_k(*C_FR, par)] = "Frente Baja"

# ────────── Cabeza > Rostro ─────────────────────────────────────────────────
C_ROS = ("Cabeza", "Rostro")
for par in [
    "Ojo Derecho - Riñón Derecho", "Ojo Izquierdo - Riñón Izquierdo",
    "Canto de Ojo - Canto de Ojo", "Unguis - Unguis",
]:
    BLOQUE_MAP[_k(*C_ROS, par)] = "Ojo"

for par in ["Malar - Malar", "Malar Derecho - Malar Izquierdo"]:
    BLOQUE_MAP[_k(*C_ROS, par)] = "Pómulo"

for par in [
    "Seno Esfenoidal - Seno Esfenoidal", "Seno Etmoidal - Seno Etmoidal",
    "Seno Paranasal - Seno Paranasal", "Retronasal - Retronasal",
    "Adenoides - Adenoides", "Maxilar - Maxilar",
]:
    BLOQUE_MAP[_k(*C_ROS, par)] = "Nariz"

for par in [
    "Alveolo - Alveolo", "Dental - Riñón", "Dental - Riñón Mismo Lado",
    "Dental Derecho - Riñón Derecho", "Dental Izquierdo - Riñón Izquierdo",
    "Lengua - Mandíbula", "Lengua - Timo",
    "Lengua Izquierda - Corazón", "Lengua Izquierda - Hígado",
    "Labio - Labio", "Labio Superior - Labio Inferior",
    "Hemangioma - Lengua", "Glándula Palatina - Riñón Lateral",
]:
    BLOQUE_MAP[_k(*C_ROS, par)] = "Boca"

for par in [
    "Amígdala - Amígdala", "Amígdala Derecha - Amígdala Izquierda",
    "Amígdala - Hígado",
]:
    BLOQUE_MAP[_k(*C_ROS, par)] = "Amígdalas"

# ────────── Cabeza > Cuello ─────────────────────────────────────────────────
C_CUE = ("Cabeza", "Cuello")
for par in [
    "Angina - Herpes 2", "Angina - Laringe Derecha", "Angina - Cerebelo",
    "Laringe - Tabique Nasal", "Laringe - Duodeno", "Laringe - Bordetella Pertussis",
    "Conducto Eferente - Laringe", "Conducto Eferente - Laringe Rotavirus",
    "Duodeno - Laringe", "Hioides - Hioides", "Epoglotis - Nariz",
    "Testículo - Angina", "Testículo Derecho - Angina",
    "Testículo - Garganta", "Vagina - Angina", "Vagina - Garganta",
    "Vagina - Garganta - Testículo",
]:
    BLOQUE_MAP[_k(*C_CUE, par)] = "Garganta Central"

for par in [
    "Tiroides - Timo", "Tiroides - Tallo Cerebral", "Tiroides - Bulbo Raquídeo",
    "Tiroides - Duodeno", "Tiroides - Cuádriceps Izquierdo",
    "Tiroides - Escápula Derecha", "Tiroides - Disfunción Tiroides",
    "Tiroides Derecha - Paratiroides Izquierda",
    "Tiroides Derecha - Tiroides Izquierda",
    "Tiroides - Páncreas", "Tiroides - Hígado",
    "Paratiroides Derecha - Riñón Derecho", "Paratiroides Derecho - Corazón",
    "Paratiroides Derecho - Tiroides 1ra",
    "Pómulo Derecho - Tiroides", "Pómulo - Tiroides",
    "Riñón Izquierdo - Tiroides", "Bulbo Raquídeo - Tiroides",
    "Muñeca Derecha - Tiroides", "Duodeno - Tiroides",
    "Duodeno Tiroides - Obesidad Extrema", "Vesícula - Paratiroides",
    "Garganta - Vejiga", "Cuello - Blastocystis Hominis",
    "Cuello - Pneumocystis Carini",
]:
    BLOQUE_MAP[_k(*C_CUE, par)] = "Garganta Baja"

for par in [
    "Esternocleidomastoideo Derecho - Clavícula",
    "Esternocleidomastoideo Derecho - Piloro",
    "Esternocleidomastoideo Derecho - Timo",
    "Esternocleidomastoideo Izquierdo - Esternón",
    "Esternocleidomastoideo Izquierdo - Riñón",
    "Esternocleidomastoideo Izquierdo - Clavícula",
    "Esternocleidomastoideo Derecho - Mastoides",
    "Esternocleidomastoideo Izquierdo - Hipófisis",
    "ECM Derecho - ECM Izquierdo",
    "Yugular - Temporal", "Yugular - Carótida", "Yugular - Yugular",
    "Plexo Cervical - Bulbo Raquídeo", "Plexo Cervical - Entre Clavícula y Cuello",
    "Carótica Yugular - Streptococcus Pneumoniae",
    "Subclavia - Bacilo Difteroide",
    "Esófago - Subclavia", "Estómago - Subclavia Derecha",
]:
    BLOQUE_MAP[_k(*C_CUE, par)] = "Garganta Lateral"

for par in [
    "Cervical 1 - Esternocleidomastoideo Derecho",
    "Cervical - Cisura Media",
    "Clavícula Media Derecha - Submaxilar Izquierdo",
    "Clavícula Media Izquierda - Submaxilar Derecho",
    "Plexo Cervical - Sacro", "Plexo Cervical - Útero",
    "Primera Cervical - Útero",
    "Hueco Garganta - Glúteo Izquierdo",
]:
    BLOQUE_MAP[_k(*C_CUE, par)] = "Nuca"

# ────────── Tronco > Tórax ──────────────────────────────────────────────────
T_TOR = ("Tronco", "Tórax")
for par in [
    "Costilla del Mismo Lado - Punta Baja del Corazón",
    "Costillas 1 al 12 - Riñón", "Costillas 1 a 12 - Riñón",
    "1a Costilla - 1a Costilla", "1ª Costilla - 1ª Costilla",
    "7a Costilla - 7a Costilla", "7ª Costilla - 7ª Costilla",
    "1a Costilla - Vejiga",
    "Mediastino Superior - Mediastino Inferior", "Mediastino - Pericardio",
    "Mediastino - Suprarrenales", "Mediastino Superior - Hipotálamo",
    "Mango - Mango",
    "Esternocleidomastoideo Derecho - Esternón",
    "Esternón - Suprarrenales", "Esternón - Timo",
]:
    BLOQUE_MAP[_k(*T_TOR, par)] = "Collar"

for par in [
    "Timo - Axila", "Timo - Suprarrenales", "Timo - Apéndice",
    "Timo - Cardias", "Timo - Bazo",
    "Axila - Timo", "Bazo - Timo", "ECM - Timo",
    "Estómago - Timo", "Clítoris - Timo", "Cava - Timo",
    "Recto - Timo",
]:
    BLOQUE_MAP[_k(*T_TOR, par)] = "Timo"

for par in [
    "Esófago - Colon Descendente", "Esófago - Pulmón",
    "Condral Derecho - Bronquio Derecho",
    "Bronquio - Bronquio", "Bronquio Derecho - Pericardio",
]:
    BLOQUE_MAP[_k(*T_TOR, par)] = "Anahata"

for par in [
    "Cardias - Corazón", "Cardias - Píloro", "Cardias - Testículo",
    "Cardias - Testículo Derecho", "Cardias - Apéndice",
    "Cardias - Coronarias", "Cardias - Esófago Disfunción",
    "Cardias - Suprarrenales Bacteria", "Cardias - Testículo Derecho Izquierdo",
    "Cardias - Vagina", "Cardias - Vejiga Derecha",
    "Cardias - Suprarrenales Streptococcus",
    "Peritoneo - Pleura Derecha", "Peritoneo - Pleura",
]:
    BLOQUE_MAP[_k(*T_TOR, par)] = "Pecho Bajo"

for par in [
    "Corazón - Costilla Falsa Izquierda", "Corazón - Estómago",
    "Corazón - Hígado", "Corazón - Riñón", "Corazón - Suprapópleo",
    "Corazón - Afín Izquierdo", "Corazón - Esternón",
    "Corazón - Corazón Negatividad", "Corazón - Escápula Izquierda",
    "Corazón - Ira Explosiva", "Corazón - Corazón Amargura",
    "Corazón - Paratiroides Derecho",
    "Bulbo Raquídeo - Corazón", "Bulbo Raquídeo - Corazón Crueldad",
    "Botón Aórtico - Pericardio", "Carótida - Aorta",
    "Cava - Cava Ansiedad",
    "Cava Derecha - Plexo Cervical Izquierdo",
    "Cava Izquierda - Plexo Cervical Derecho",
    "Coronaria - Pulmón", "Coronaria - Tendón Pectoral",
    "Coronarias - Pulmón", "Coronarias - Pulmón Streptococcus",
    "Coronarias Pulmón - Streptococcus Alfa",
    "CORON ARIA - Tendón Pectoral",
    "Cuerpo de Páncreas - Corazón",
    "Aurículo Ventricular - Riñón Izquierdo",
    "Seno Aurículo Ventricular - Riñón Izquierdo",
    "Aorta - Aorta",
    "Pericardio - Mastoides", "Pericardio - Temporal Derecho",
    "Pulmón Derecho - Corazón", "Pulmón Izquierdo - Corazón",
]:
    BLOQUE_MAP[_k(*T_TOR, par)] = "Corazón"

for par in [
    "Arteria Axilar - Arteria Axilar",
    "Arteria Axilar Derecha - Arteria Axilar Izquierda",
    "Infraaxilar - Infraaxilar",
    "Plexo Axilar - Supraespinoso",
    "Pecho - Pecho", "Pectoral Mayor - Pectoral Mayor",
    "Pectoral Mayor - Pulmón Contralateral",
    "Pectoral Izquierdo - Tendón Cuádriceps Izquierdo",
    "Escápula - Pulmón", "Escápula Derecha - Pulmón",
]:
    BLOQUE_MAP[_k(*T_TOR, par)] = "Pecho Lateral"

for par in [
    "Bazo - Pulmón",
    "Colón Descendente - Pulmón Izquierdo",
    "Pleura - Hígado", "Pleura Derecha - Apéndice",
    "Pleura Derecha - Pulmón Derecho", "Pleura Derecha - Peritoneo",
    "Apéndice - Pleura", "Apéndice - Pleura Complejo",
    "Apéndice Pleura - Staphylococcus Aureus",
    "Pulmón - Riñón Izquierdo", "Pulmón Derecho - Bulbo Raquídeo",
]:
    BLOQUE_MAP[_k(*T_TOR, par)] = "Pleura"

# ────────── Tronco > Abdomen ────────────────────────────────────────────────
T_ABD = ("Tronco", "Abdomen")
for par in [
    "Estómago - Colon Transverso", "Estómago - Hígado",
    "Estómago - Bazo", "Estómago - Duodeno", "Estómago - Suprarrenales",
    "Estómago - Cola de Páncreas", "Estómago - Vejiga",
    "Estómago - Próstata",
    "Cardias - Cardias", "Cardias - Nervio Vago",
    "Cardias - Temporal Derecho",
]:
    BLOQUE_MAP[_k(*T_ABD, par)] = "Estómago"

for par in [
    "Piloro - Estómago", "Piloro - Ano", "Piloro - Riñones",
    "Piloro - Colon Ascendente", "Piloro - Ureteros",
    "Piloro - Lengua Contralateral", "Piloro - Colon Transverso",
    "Piloro - Cardias", "Piloro - Glúteo", "Piloro - Riñón Izquierdo",
    "Atlas - Píloro",
    "Cabeza de Páncreas - Píloro", "Cabeza de Páncreas - Estómago",
    "Cápsula Glisson - Píloro",
    "Cervical 1 - Píloro", "Cervical 1 - Píloro Plasmodium",
    "Ano - Píloro", "Atlas Píloro - Plasmodium Falciparum",
    "Esófago - Píloro",
]:
    BLOQUE_MAP[_k(*T_ABD, par)] = "Píloro"

for par in [
    "Hígado - Riñón Izquierdo", "Hígado - Suprarrenales",
    "Hígado - Cola de Páncreas", "Hígado - Riñón Derecho",
    "Hígado Lóbulo Posterior - Riñón Derecho",
    "Hígado Lóbulo Posterior - Riñón Izquierdo",
    "Lóbulo Hepático Izquierdo - Riñón Izquierdo",
    "Cirrosis Hepática - Hígado Riñón",
    "Borde Costal - Hígado",
    "Ascendente - Hígado",
    "Ciego - Hígado",
    "Cola de Páncreas - Hígado Hepatitis", "Cola de Páncreas - Hígado Complejo",
    "Cabeza de Páncreas - Hígado Hepatitis",
    "Vena Porta - Colon Transverso", "Vena Porta - Hígado",
    "Vena Porta - Tendón Pectoral", "Vena Porta - Páncreas",
    "Vena Porta - Vena Porta",
    "Auriculoventricular - Riñón Izquierdo",
]:
    BLOQUE_MAP[_k(*T_ABD, par)] = "Hígado"

for par in [
    "Ligamento Hepático - Costohepático", "Ligamento Hepático - Riñón Derecho",
    "Retrohepático - Retrohepático", "Retrohepático - Riñón Derecho",
    "Suprahepático - Suprahepático", "Peripancreático - Peripancreático",
    "Subdiafragma - Subdiafragma", "Subdiafragma - Riñón Lateral",
    "Conducto Central Hepático - Mucosa del Colon Descendente",
]:
    BLOQUE_MAP[_k(*T_ABD, par)] = "Zona Hepática"

for par in [
    "Vesícula - Riñón Derecho", "Vesícula - Riñón",
    "Vesícula - Cápsula Renal", "Vesícula - Escápula", "Vesícula - Uretra",
]:
    BLOQUE_MAP[_k(*T_ABD, par)] = "Vesícula"

for par in [
    "Bazo - Bazo", "Bazo - Riñón", "Bazo - Suprarrenales", "Bazo - Vejiga",
    "Bazo Bazo - Yersinia Pestis", "Bazo Bazo - Leucemia",
    "Bazo Hígado - Brucella Abortus",
    "Bazo Punta del Páncreas - Verruga",
    "Bazo - Bazo Horizontal Yersinia", "Bazo - Bazo Vertical Leucemia",
    "Bazo - Punta de Páncreas", "Bazo - Páncreas",
    "Duodeno - Bazo", "Estómago - Bazo", "Páncreas - Bazo",
]:
    BLOQUE_MAP[_k(*T_ABD, par)] = "Bazo"

for par in [
    "Páncreas - Estómago", "Páncreas - Páncreas",
    "Páncreas - Duodeno", "Páncreas - Hígado", "Páncreas - Suprarrenales",
    "Cabeza de Páncreas - Páncreas", "Cabeza de Páncreas - Suprarrenales",
    "Cabeza de Páncreas - Pleura", "Cabeza de Páncreas - Punta de Páncreas",
    "Cabeza de Páncreas - Vejiga Izquierda",
    "Cabeza Páncreas - Suprarrenales Staphylococcus",
    "Cola de Páncreas - Colon Descendente",
    "Cola de Páncreas - Punta de Páncreas",
    "Cola de Páncreas - Riñón Ipsilateral", "Cola de Páncreas - Riñón Izquierdo",
    "Punta de Páncreas - Riñón Izquierdo",
    "Cabeza de Páncreas - Cabeza de Fémur",  # moved from Pelvis originally
    "Suprarrenal - Páncreas",
]:
    BLOQUE_MAP[_k(*T_ABD, par)] = "Páncreas"

for par in [
    "Duodeno - Esófago", "Duodeno - Riñón Izquierdo", "Duodeno - Riñón Derecho",
    "Duodeno - Vaso",
    "Apófisis Mastoides - Duodeno", "Apófisis Mastoides - Riñón Ipsilateral",
    "Ombligo - Ombligo", "Ombligo Derecho - Izquierdo",
    "Epiplón - Epiplón", "Uretero - Uretero", "Uretero - Recto",
    "Uretero - Vejiga", "Uretero - Cáliz Renal",
    "Uretero - Riñón Ipsilateral", "Uretero - Riñón Mismo Lado",
    "Uréter - Trompa", "Uréter Izquierdo - Recto",
    "Uretero - Trompa de Falopio",
    "Xifoides - Xifoides",
    "Gen - Vejiga",  # del Delantera (queda en Abdomen)
    "Epiplón - Epiplón Staphylococcus",  # llega vía ZONE_MOVES
    "Línea Arcuata - Vena Mesentérica",
    "Agujero - Agujero",
]:
    BLOQUE_MAP[_k(*T_ABD, par)] = "Ombligo"

for par in [
    "Apéndice - Contraciego", "Apéndice - Apéndice Xifoides",
    "Apéndice - Peritoneo", "Apéndice - Lengua Izquierda",
    "Apéndice - Testículo Bilateral", "Apéndice - Testículo Derecho",
    "Apéndice - Uretra", "Apéndice - Vagina",
    "Apéndice - Testículo Hongo",
    "Apéndice - Nervio Femoral", "Apéndice - Gracilis Superior",
    "Apéndice - Cabeza de Fémur Derecha",
    "Apéndice - Ovario Derecho",
    "Ciego - Riñón", "Ciego - Riñón Derecho",
    "Ciego Riñón Derecho - Trichomonas",
    "Válvula Ileocecal - Válvula Ileocecal",
    "Válvula Ileocecal - Estómago",
    "Válvula Ileocecal - Riñón Derecho",
    "Válvula Ileocecal - Prominencia Occipital",
    "Intestino Delgado - Intestino Delgado",
    "Intestino Delgado - Intestino Grueso",
    "Intestino Grueso - Intestino Grueso",
    "Micelio Intestinal - Micelio Intestinal",
    "Peritoneo - Apéndice", "Peritoneo - Peroné",
]:
    BLOQUE_MAP[_k(*T_ABD, par)] = "Intersección"

for par in [
    "Colon Ascendente - Colon Ascendente",
    "Colon Ascendente - Riñón Derecho",
    "Colon Ascendente - Colon Transverso",
    "Colon Descendente - Vejiga", "Colon Descendente - Riñón Izquierdo",
    "Colon Sigmoides - Colon Sigmoides", "Colon Sigmoides - Recto",
    "Estómago - Colon Transverso",
    "Yeyuno - Yeyuno", "Yeyuno - Riñón",
    "Ano - Colon Ascendente", "Ano - Próstata", "Ano - Testículo",
    "Ano Ano - Papiloma", "Ano Píloro - Levadura",
    "Ano Testículo - Izquierdo Ecuador",
    "Ano - Lengua",
    "Clítoris - Ano", "Carina - Ano",
    "Bulbo Raquídeo - Colon Descendente",
    "Cervical 78 Dorsal - Pasciano",
]:
    BLOQUE_MAP[_k(*T_ABD, par)] = "Colon"

# Nuevos bloques en Abdomen
for par in [
    "Cápsula Renal - Riñón", "Cápsula Renal Derecha - Riñón Derecho",
    "Cápsula Renal Derecha - Riñón Izquierdo",
    "Cápsula Renal Derecha - Vejiga", "Cápsula Renal Derecha - Vesícula",
    "Capsula Renal - Riñón Mismo Lado",
    "Capsula Renal Derecha - Riñón Izquierdo Reservorio",
    "Cáliz Renal - Uretero Herpes", "Cáliz Renal - Uretero ADNpatógeno",
    "Riñón - Escápula", "Riñón - Deltoides",
    "Riñón - Sacro Contralateral", "Riñón - Riñón Inferior",
    "Riñón Derecho - Hígado", "Riñón Derecho - Duodeno",
    "Riñón Izquierdo - Mastoides", "Riñón Izquierdo - Ojo",
    "Riñón Izquierdo - Conducto del Páncreas", "Riñón Izquierdo - Útero",
    "Riñones - Interiliaco",
    "Área Visual - Riñón", "Articulación - Riñón Derecho",
    "CICATRIZ - Riñón", "Cervical - Cápsula Renal",
    "Cervicales - Riñón Derecho Izquierdo",
    "Cervicales - Riñones", "Cervicales - Suprarrenales",
    "Ascendente - Riñón Derecho",
]:
    BLOQUE_MAP[_k(*T_ABD, par)] = "Riñón"

for par in [
    "Suprarrenal - Pulmón Bilateral", "Suprarrenal - Frente del Cuerpo",
    "Suprarrenal - Suprarrenales",
    "Zona Suprarrenal - Riñón Opuesto",
]:
    BLOQUE_MAP[_k(*T_ABD, par)] = "Suprarrenal"

# ────────── Tronco > Espalda ────────────────────────────────────────────────
T_ESP = ("Tronco", "Espalda")
for par in [
    "Supraespinoso - Cerebelo", "Espina de la Escápula - Espina de la Escápula",
    "Retro Axilar - Retro Axilar",
]:
    BLOQUE_MAP[_k(*T_ESP, par)] = "Homóplato"

for par in [
    "Dorsal 10ª - Dorsal 11ª", "Dorsal - Lumbar",
    "Plexo Dorsal - Plexo Dorsal",
]:
    BLOQUE_MAP[_k(*T_ESP, par)] = "Dorsales"

# ────────── Pelvis > Delantera ───────────────────────────────────────────────
P_DEL = ("Pelvis", "Delantera")
for par in [
    "Vejiga - Hipófisis", "Vejiga - Bulbo", "Vejiga - Ano",
    "Vejiga - Timo", "Vejiga - Riñón", "Vejiga - Cadera",
    "Vejiga - Colon Transverso", "Vejiga - Vagina",
    "Bulbo Raquídeo - Vejiga", "Bulbo Raquídeo - Vejiga Dengue",
    "Esófago - Vejiga Izquierda",
    "Colón Transverso - Vejiga",
    "Esfínter Uretral - Esfínter Uretral",
    "Esfínter de la Uretra - Esfínter",
    "Esfínter Uretra - Esfínter Uretra",
    "Esfínter de la Uretra - Esfínter de la Uretra",
    "Clítoris - Uretra", "Clítoris - Pelvis Hueso Pélvico",
    "Gen - Vejiga",  # también está en Ombligo, se resolverá como duplicado
    "Gen-Ombligo - Órgano",
    "Vejiga - Sacro",
]:
    BLOQUE_MAP[_k(*P_DEL, par)] = "Pubis"

for par in [
    "Articulación Sacroilíaca - Articulación Sacroilíaca",
    "Articulación - Nervio Inguinal",
    "Nervio Inguinal - Articulaciones",
    "Nervio Inguinal Derecho - Hígado",
    "Nervio Inguinal - Articulaciones",
    "Nervio Femoral - Nervio Femoral",
    "Nervio Vago - Riñón Contralateral",
    "Nervio Vago - Suprarrenal",
    "Ingle - Ingle",
    "Iliaco - Cápsula Renal Izquierda",
    "Coxis Derecho - Coxis Izquierdo",
    "Glúteo Medio - Vena Femoral",
    "Saco de Douglas - Vena Femoral",
    "Plexo Lumbar - Plexo Lumbar",
]:
    BLOQUE_MAP[_k(*P_DEL, par)] = "Cadera"

for par in [
    "Cabeza de Fémur - Cabeza de Fémur",
    "Cresta Iliaca Frontal Derecha - Perone Lateral",
    "Cuello de Fémur Derecho - Calcáneo Izquierdo",
    "Cervical 3ª - Supraespinoso",
]:
    BLOQUE_MAP[_k(*P_DEL, par)] = "Fémur"

# Conexiones sistémicas cervico-pélvicas (nuevo bloque)
for par in [
    "Atlas - Testículo", "Atlas - Útero", "Atlas Útero - Linda Celos",
    "Cervical 1 - Coxis",
    "Cervical 3 - Sacro Parasimpático", "Cervical 3ª - Sacro Contrario",
    "Cervical - Sacro Contralateral", "Cervicales - Sacro",
    "Cervicales - Utero",
    "Ciático Derecho - Útero",
    "Conducto Eferente - Sacro",
    "Coxis - Ciática", "Coxis - Ciático", "Coxis - Coxis Vertical",
    "Coxis - Plexo Cervical", "Coxis Ciático - Calambres Piernas",
    "Coxis Plexo - Cervical Ácido",
    "Cérvico - Útero", "Cérvico Cérvico - Útero Insomnio",
    "Cérvico Útero - Infección Vaginal",
    "Dorsal 6 - Sacro",
    "Cáliz Renal - Uretero", "Cáliz Renal - Uretero Herpes",  # puede ya estar en Riñón
    "Estómago - Próstata o Vagina",
    "Hiporasis - Útero", "HIPÓFISIS - Útero",
    "Plexo Cervical - Sacro", "Plexo Cervical - Útero",  # (también en Cuello)
    "Primera Cervical - Primera Cervical",
    "Útero - Sacro",
    "Uretra - Sacro",
    "Cervical - Útero",
]:
    BLOQUE_MAP[_k(*P_DEL, par)] = "Conexiones Sistémicas"

# ────────── Pelvis > Trasera ────────────────────────────────────────────────
P_TRA = ("Pelvis", "Trasera")
for par in [
    "Articulación Sacro-Ilíaca - Articulación Sacro-Ilíaca",
    "Sacro - Coxis", "Sacro - Riñón Contralateral",
    "Sacro - Ciático", "Sacro - Cervical",
    "Sacro - Útero", "Sacro - Vejiga", "Sacro - Femoral",
    "154 + Sacro - Sacro",
]:
    BLOQUE_MAP[_k(*P_TRA, par)] = "Sacro"

for par in [
    "Coccígeo - Coccígeo",
    "5 + Cáliz - Uretra",
]:
    BLOQUE_MAP[_k(*P_TRA, par)] = "Coxis"

for par in [
    "Glúteo Medio - Vena Femoral",
    "Glúteo Menor Derecho - Sacro",
    "Glúteo - Ganglios Mesentéricos",
    "Glúteo - Glúteo Bacteria", "Glúteo - Hiato",
    "Glúteo Vena - Femoral Babesia",
    "Hiato - Testículo Izquierdo", "Hiato - Testículo",
    "Hiato - Testículo Derecho", "Hiato - Vagina",
    "HIATO ESOFÁGICO - Vagina",
    "Hiato Esofágico - Testículo Derecho",
    "Hoyuelo del Glúteo Derecho - Lumbar 2",
    "Hoyuelo del Glúteo Izquierdo - Lumbar 2",
    "Hoyuelo del Glúteo - Lumbar 2",
    "Hueco - Glúteo Izquierdo",
    "Glúteo Izquierdo - Tendón Aquiles Derecho",
    # llegan vía ZONE_MOVES:
    "Glúteo Medio - Glúteo Medio", "Glúteo - Vena Femoral",
    "Glúteo Derecho - Hiato", "Glúteo Izquierdo - Aquiles Izquierdo",
    "Glúteo Izquierdo - Aquiles", "Glúteo Izquierdo - Hiato",
    "e Glúteo - Glúteo",
    "Semimembranoso - Semimembranoso",
    "Braquial Derecho - Braquial Izquierdo",  # fue movido a Brazo en script anterior...
    "Retrotensor de la Fascia Lata - Rectoral",  # llega vía ZONE_MOVES
]:
    BLOQUE_MAP[_k(*P_TRA, par)] = "Trasero"

# ────────── Pelvis > Sexo ────────────────────────────────────────────────────
P_SEX = ("Pelvis", "Sexo")
for par in [
    "Ovario - Suprarrenales", "Ovario - Riñón", "Ovario - Útero",
    "Trompa de Falopio - Trompa de Falopio",
    "Trompa - Ovario del Mismo Lado",
    "Útero - Riñón", "Útero - Recto", "Útero - Ovario", "Útero - Hígado",
    "Vagina - Ovario", "Vagina - Útero", "Vagina - Recto",
    "Vagina - Riñón Izquierdo", "Vagina - Riñón Derecho",
    "Anexo - Anexo", "Anexo - Ano", "Anexo - Riñón del Mismo Lado",
    "Saco de Douglas - Vena Femoral",  # puede ser Cadera también
    "e + Trompa - Trompa",  # llega vía ZONE_MOVES
    "Cervical - Útero",  # (también en Cuello/Delantera como conexión sistémica)
    "Estómago - Próstata",
]:
    BLOQUE_MAP[_k(*P_SEX, par)] = "Fémina B"

for par in [
    "Uretra - Pelvis", "Uretra - Uretero", "Uretra - Vagina",
    "Uretra - Clítoris", "Uretra - Ureteros",
    "Clítoris - Clítoris",  # quizá ya existe en base
]:
    BLOQUE_MAP[_k(*P_SEX, par)] = "Fémina A"

for par in [
    "Pene - Pene", "Timo - Pene",
    "Timo - Testículos", "Timo - Ovarios",
    "Recto - Timo",
    "Testículo - Próstata", "Testículo - Recto",
    "Ano - Testículo Izquierdo",
]:
    BLOQUE_MAP[_k(*P_SEX, par)] = "Macho"

# ────────── Miembros > Brazo ────────────────────────────────────────────────
M_BRZ = ("Miembros", "Brazo")
for par in [
    "Acromion - Acromion", "Acromium - Acromium",
    "Deltoides - Riñón Lateral",
    "Deltoides Derecho - Deltoides Izquierdo",
    "Escápula MI - Centro del Omóplato",
    "Omóplato - Omóplato", "Latísimus - Latísimus",
    "Braquial Derecho - Braquial Izquierdo",
]:
    BLOQUE_MAP[_k(*M_BRZ, par)] = "Brazo Alto"

for par in [
    "Bursa - Codo", "Ulna - Ulna",
]:
    BLOQUE_MAP[_k(*M_BRZ, par)] = "Brazo Medio"

for par in [
    "Palma Mano - Palma Mano",
    "Dedo Pulgar - Dedo Pulgar",
    "Dedo Anular - Dedo Anular",
    "Dedo Meñique - Dedo Meñique",
    "Dedo Medio - Dedo Medio",
    "Muñeca - Muñeca",
    "Muñeca Derecha - Rodilla Externa",
]:
    BLOQUE_MAP[_k(*M_BRZ, par)] = "Mano"

# ────────── Miembros > Pierna ────────────────────────────────────────────────
M_PIE = ("Miembros", "Pierna")
for par in [
    "Fémur - Fémur", "Fémur Posterior - Fémur Posterior",
    "Músculo Psoasilíaco - Músculo Psoasilíaco",
    "Tensor Fascia Lata - Sartorio",
    "Tensor Fascia Lata - Cuádriceps",
    "Tensor Fascia Lata - Espina Ilíaca Posterior",
    "Tensor Fascia Lata - Gracilis Superior",
    "Trocánter Mayor - Riñón Lateral",
    "Trocánter Mayor - Tensor Fascia Lata",
    "Trocánter Mayor - Trocánter Menor",
    "Triángulo de Scarpa - Triángulo de Scarpa",
    "Poplíteo - Región Inguinal",
    "Retrotensor de la Fascia Lata - Rectoral",  # llega vía ZONE_MOVES
]:
    BLOQUE_MAP[_k(*M_PIE, par)] = "Pierna Alta"

for par in [
    "Rodilla - Rodilla",
    "Tibia Inferior - Tibia Inferior",
    "Tibia Media - Tibia Media",
    "Tobillo - Tobillo",
    "Úlcera Varicosa - Úlcera Varicosa",
    "Plexo Rodilla - Plexo Rodilla",
    "Semimembranoso - Semimembranoso",
]:
    BLOQUE_MAP[_k(*M_PIE, par)] = "Pierna Media"

for par in [
    "Aquiles Superior - Aquiles Superior",
    "Aquiles Derecho - Aquiles Derecho",
    "Aquiles - Triceps Derecho",
    "Aquiles Derecho - Punta Escápula Izquierda",
    "Aquiles Inferior - Aquiles Inferior",
    "Aquiles Medio - Aquiles Medio",
]:
    BLOQUE_MAP[_k(*M_PIE, par)] = "Pierna Trasera"

for par in [
    "Arco del Pie - Arco del Pie",
    "Metatarso - Metatarso",
    "Planta del Pie - Planta del Pie",
    "Talón - Talón", "Tarso - Tarso",
]:
    BLOQUE_MAP[_k(*M_PIE, par)] = "Pie"

# ────────── Extras > Variables ───────────────────────────────────────────────
E_VAR = ("Extras", "Variables")
for par in [
    "Afin - Afin",
    "Área de Dolor - Riñón Mismo Lado",
    "Articulación - Riñón Izquierdo",
    "Pulso Radial - Bazo",
    "V-8 - V-8",
    "Vago - Riñón",
    "Vago - Riñón Contralateral",
    "Espíclavia - Espíclavia",
]:
    BLOQUE_MAP[_k(*E_VAR, par)] = "Pares Generales"

# ────────── Extras > Columna Vertebral ──────────────────────────────────────
E_COL = ("Extras", "Columna Vertebral")
for par in [
    "Cervical 1ª - Piloro", "Cervical 1ª - Coxis",
    "Lumbar 4ª - Lumbar 4ª", "4ª Lumbar Derecha - Izquierda",
    "Lumbar 2 - Lumbar 2",
    "Vértebra Lumbar - Riñón Izquierdo",
    "Dorsales - Lumbares",
    "Primera Cervical - Primera Cervical",
    "Canal Medular - Canal Medular",
]:
    BLOQUE_MAP[_k(*E_COL, par)] = "Predeterminados"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
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
    return {_norm(p) for b in zona_obj["bloques"] for p in b["pares"]}


def all_norms_in_bloque(bloque_obj):
    return {_norm(p) for p in bloque_obj["pares"]}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)

    moved_zone = 0
    moved_bloque = 0
    duplicates_removed = 0
    unclassified = []

    # ── FASE 1: Movimientos de zona ──────────────────────────────────────────
    print("=== FASE 1: Movimientos de zona ===")
    for (src_reg, src_zona, par, dst_reg, dst_zona, dst_bloque) in ZONE_MOVES:
        zona_src = get_zona(db, src_reg, src_zona)
        if not zona_src:
            print(f"  ⚠ Zona origen no encontrada: {src_reg} > {src_zona}")
            continue

        found_par = None
        src_bloque_obj = None
        for b in zona_src["bloques"]:
            for p in b["pares"]:
                if _norm(p) == _norm(par):
                    found_par = p
                    src_bloque_obj = b
                    break
            if found_par:
                break

        if not found_par:
            print(f"  ⚠ Par no encontrado: «{par}» en {src_reg}>{src_zona}")
            continue

        zona_dst = get_zona(db, dst_reg, dst_zona)
        if not zona_dst:
            print(f"  ⚠ Zona destino no encontrada: {dst_reg} > {dst_zona}")
            continue

        norms_dst = all_norms_in_zona(zona_dst)
        if _norm(par) in norms_dst:
            src_bloque_obj["pares"].remove(found_par)
            print(f"  🗑  Dup eliminado: «{found_par}» ({src_reg}>{src_zona})")
            duplicates_removed += 1
            continue

        src_bloque_obj["pares"].remove(found_par)
        bloque_dst = get_or_create_bloque(zona_dst, dst_bloque)
        bloque_dst["pares"].append(found_par)
        print(f"  ✔ ZONA  {src_reg}>{src_zona} → {dst_reg}>{dst_zona} [{dst_bloque}]  «{found_par}»")
        moved_zone += 1

    # ── FASE 2: Reclasificación de bloques ───────────────────────────────────
    print("\n=== FASE 2: Asignación de bloques ===")
    for reg in db["regiones"]:
        for zona in reg["zonas"]:
            for b in zona["bloques"]:
                if b["nombre"] not in ("Compilado Externo", "PDFs Externos"):
                    continue
                pares_restantes = []
                for par in list(b["pares"]):
                    key = _k(reg["nombre"], zona["nombre"], par)
                    bloque_target = BLOQUE_MAP.get(key)

                    if bloque_target is None:
                        pares_restantes.append(par)
                        unclassified.append(
                            f'{reg["nombre"]}>{zona["nombre"]}>{b["nombre"]}: «{par}»'
                        )
                        continue

                    zona_obj = zona
                    bloque_dst = get_or_create_bloque(zona_obj, bloque_target)

                    # Verificar duplicado en bloque destino
                    if _norm(par) in all_norms_in_bloque(bloque_dst):
                        print(f"  🗑  Dup en bloque: «{par}» → ya existe en [{bloque_target}]")
                        duplicates_removed += 1
                        continue

                    bloque_dst["pares"].append(par)
                    print(f"  ✔ BLOQUE [{b['nombre']}] → [{bloque_target}]  «{par}»")
                    moved_bloque += 1

                b["pares"] = pares_restantes

    # ── Limpiar bloques externos vacíos ──────────────────────────────────────
    for reg in db["regiones"]:
        for zona in reg["zonas"]:
            zona["bloques"] = [
                b for b in zona["bloques"]
                if not (b["nombre"] in ("Compilado Externo", "PDFs Externos")
                        and len(b["pares"]) == 0)
            ]

    # ── Recalcular total ──────────────────────────────────────────────────────
    total = sum(
        len(b["pares"])
        for reg in db["regiones"]
        for zona in reg["zonas"]
        for b in zona["bloques"]
    )
    db["total"] = total

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("✅ Redistribución completada:")
    print(f"   Movimientos de zona      : {moved_zone}")
    print(f"   Asignaciones de bloque   : {moved_bloque}")
    print(f"   Duplicados eliminados    : {duplicates_removed}")
    print(f"   Sin clasificar           : {len(unclassified)}")
    print(f"   Total DB                 : {total}")

    if unclassified:
        print("\n⚠  PARES SIN CLASIFICAR (revisar manualmente):")
        for u in unclassified:
            print(f"   {u}")

    # Resumen de zonas/bloques externos restantes
    remaining_ext = [
        (reg["nombre"], zona["nombre"], b["nombre"], len(b["pares"]))
        for reg in db["regiones"]
        for zona in reg["zonas"]
        for b in zona["bloques"]
        if b["nombre"] in ("Compilado Externo", "PDFs Externos") and b["pares"]
    ]
    if remaining_ext:
        print("\n📋 Bloques externos con pares restantes:")
        for r, z, bn, c in remaining_ext:
            print(f"   {r}>{z}>{bn}: {c} pares")
    else:
        print("\n🎉 Todos los bloques externos han sido distribuidos.")


if __name__ == "__main__":
    main()
