#!/usr/bin/env python3
"""
Rebuild biomagnetic_pairs_db.json from clean extracted PDF data
and generate PDF review document pares_limpios_revision_v5.pdf
"""

import json
import os
from collections import defaultdict

DATA_DIR = "/Users/m2/Documents/New project/data"
OUTPUT_JSON = os.path.join(DATA_DIR, "biomagnetic_pairs_db.json")
OUTPUT_PDF = os.path.join(DATA_DIR, "pares_limpios_revision_v5.pdf")

# ============================================================
# RAW DATA STRUCTURE
# Format: (region_id, region_nombre, zona_id, zona_nombre, bloque_id, bloque_nombre, pares_list)
# ============================================================

REGIONS_DATA = [
    # ────────────────────────────────────────────────────────
    # REGIÓN 1: CABEZA
    # ────────────────────────────────────────────────────────
    (1, "Cabeza", 1, "Coronilla", 1, "Pineal", [
        "Pineal - Pineal",
        "Pineal - Bulbo",
        "Pineal - Cerebelo",
        "Pineal - Próstata/Útero",
        "Pineal - Páncreas",
        "Pineal - Hipotálamo",
        "Pineal - Tiroides",
    ]),
    (1, "Cabeza", 1, "Coronilla", 2, "Corona", [
        "Prepineal - Vejiga",
        "Postpineal - Postpineal",
        "Núcleos Basales - Hipófisis",
        "Núcleos Basales - Bulbo",
    ]),
    (1, "Cabeza", 1, "Coronilla", 3, "Callosidad", [
        "Cuerpo Calloso - Cuerpo Calloso",
        "Borde Calloso DER - Borde Calloso DER",
        "Borde Calloso IZQ - Borde Calloso IZQ",
        "Cisura Media - Cisura Media",
    ]),
    (1, "Cabeza", 1, "Coronilla", 4, "Parietal", [
        "Parietal - Parietal",
        "Parietal - Bulbo",
        "Parietal (RAS) - Riñón CONTLAT",
        "Parietal IZQ - Colon Transverso",
        "Cerebro RAS - Riñón RAS",
    ]),
    (1, "Cabeza", 2, "Posterior", 1, "Bulbo", [
        "Bulbo - Bulbo",
        "Bulbo - Cerebelo",
        "Bulbo - Tiroides",
        "Bulbo - Corazón",
        "Bulbo - Vejiga",
    ]),
    (1, "Cabeza", 2, "Posterior", 2, "Occipital", [
        "Occipital - Occipital",
        "Occipital - Parótida IZQ",
        "Occipital - Timo",
        "Occipital - Testículo RAS/Vagina",
    ]),
    (1, "Cabeza", 2, "Posterior", 3, "Cerebelo", [
        "Cerebelo - Cerebelo",
        "Cerebelo - Bulbo",
        "Cerebelo - Sacro",
        "Cisura de Silvio - Cisura de Silvio",
    ]),
    (1, "Cabeza", 3, "Lateral", 1, "Temporal", [
        "Frontoparietal - Temporal IZQ",
        "Amígdala Cerebral - Suprarrenal",
        "Temporal - Temporal",
        "Temporal DER - Temporal DER",
        "Temporal IZQ - Temporal IZQ",
        "Temporal IZQ - Hipófisis",
    ]),
    (1, "Cabeza", 3, "Lateral", 2, "Aurícula", [
        "Oreja - Oreja",
        "Oído - Oído",
        "Oído - Riñón CONTLAT",
        "Oído DER - Ovario/Testículo DER",
    ]),
    (1, "Cabeza", 3, "Lateral", 3, "Posterior", [
        "Temporoccipital - Temporoccipital",
        "Retromastoides - Retromastoides",
        "Mastoides - Mastoides",
        "Mastoides - Corazón",
        "Mastoides - Hipófisis",
    ]),
    (1, "Cabeza", 3, "Lateral", 4, "Sien", [
        "Quiasma - Quiasma",
        "Sien - Sien",
        "Sien DER - Corazón",
        "Polígono de Willis - Polígono de Willis",
    ]),
    (1, "Cabeza", 3, "Lateral", 5, "Mandibular", [
        "Preauricular - Preauricular",
        "Preauricular - Vejiga",
        "Rama Mandibular - Rama Mandibular",
        "Rama Mandibular - Cola de Páncreas",
        "Ángulo Gonión - Ángulo Gonión",
    ]),
    (1, "Cabeza", 3, "Lateral", 6, "Parótida", [
        "Parótida - Parótida",
        "Parótida IZQ - Pineal",
        "Parótida DER - Ojo IZQ",
        "Parótida DER - Tiroides",
        "Parótida DER - Corazón",
    ]),
    (1, "Cabeza", 4, "Frente", 1, "Frente Alta", [
        "Tálamo - Tálamo",
        "Polo - Polo",
        "Antecuerno - Antecuerno",
        "Frontal DER - Frontal DER",
        "Frontal IZQ - Frontal IZQ",
    ]),
    (1, "Cabeza", 4, "Frente", 2, "Hipófisis", [
        "Hipófisis - Hipófisis",
        "Hipófisis - Supraciliar",
        "Hipófisis - Bulbo",
        "Hipófisis - Mastoides IZQ",
        "Hipófisis - Tiroides",
        "Hipófisis - Vejiga",
        "Hipófisis - Testículo/Ovario",
    ]),
    (1, "Cabeza", 4, "Frente", 3, "Frente Baja", [
        "Supraciliar - Bulbo",
        "Interciliar - Bulbo",
        "Interciliar - Riñón RAS",
        "Interciliar - Sacro",
        "Seno Frontal - Seno Frontal",
        "Ceja - Ceja",
    ]),
    (1, "Cabeza", 5, "Rostro", 1, "Ojo", [
        "Párpado - Párpado",
        "Ojo - Ojo",
        "Ojo - Cerebelo",
        "Ojo - Escápula RAS",
    ]),
    (1, "Cabeza", 5, "Rostro", 2, "Anillo Ocular", [
        "Piso Orbital - Piso Orbital",
        "Piso Orbital - Cerebelo",
        "Canto - Canto",
        "Craneal - Craneal",
        "Lacrimal - Lacrimal",
    ]),
    (1, "Cabeza", 5, "Rostro", 3, "Pómulo", [
        "Pómulo - Pómulo",
        "Pómulo - Riñón",
        "Pómulo DER - Tiroides",
        "Pómulo IZQ - Riñón DER",
    ]),
    (1, "Cabeza", 5, "Rostro", 4, "Nariz", [
        "Nariz - Nariz",
        "Seno Nasal - Seno Nasal",
        "Maxilar Superior DER - Cola de Páncreas",
        "Lengua - Lengua",
        "Lengua IZQ - Corazón",
        "Lengua IZQ - Hígado",
    ]),
    (1, "Cabeza", 5, "Rostro", 5, "Boca", [
        "Comisura - Comisura",
        "Dental RAS - Riñón RAS",
        "Mandíbula - Mandíbula",
        "Mentón - Mentón",
    ]),
    (1, "Cabeza", 6, "Cuello", 1, "Garganta Central", [
        "Laringe - Laringe",
        "Angina - Angina",
        "Carótida - Carótida",
        "Esternocleidomastoideo - Esternocleidomastoideo",
        "Esternocleidomastoideo IZQ - Hipófisis",
        "Esternocleidomastoideo IZQ - Riñón IZQ",
    ]),
    (1, "Cabeza", 6, "Cuello", 2, "Garganta Baja", [
        "Tiroides - Tiroides",
        "Tiroides - Bulbo",
        "Hueco de Garganta - Glúteo IZQ",
        "Paratiroides - Paratiroides",
        "Cuello - Cuello",
    ]),
    (1, "Cabeza", 6, "Cuello", 3, "Garganta Lateral", [
        "Nervio Vago - Nervio Vago",
        "Nervio Vago - Cardias",
        "Nervio Vago - Riñón RAS",
        "Nudo - Nudo",
        "Plexo Cervical - Plexo Cervical",
        "Plexo Cervical - Deltoides",
    ]),
    (1, "Cabeza", 6, "Cuello", 4, "Nuca", [
        "Atlas - Atlas",
        "Atlas IZQ - Útero",
        "Cervical 3-4 - Suprarrenal",
        "Cervical 3 - Sacro 2",
        "Cervical 7 - Dorsal 1",
        "Supraespinoso - Supraespinoso",
    ]),

    # ────────────────────────────────────────────────────────
    # REGIÓN 2: TRONCO
    # ────────────────────────────────────────────────────────
    (2, "Tronco", 1, "Tórax", 1, "Collar", [
        "Mango del Esternón - Mango del Esternón",
        "Costilla 1 - Costilla 1",
        "Subclavia - Subclavia",
        "Epiclavio - Epiclavio",
        "Mediastino - Mediastino",
        "Mediastino - Cerebelo",
    ]),
    (2, "Tronco", 1, "Tórax", 2, "Timo", [
        "Timo - Timo",
        "Timo - Hipófisis",
        "Timo - Parietal",
        "Timo - Testículo RAS/Ovario RAS",
        "Timo - Recto",
    ]),
    (2, "Tronco", 1, "Tórax", 3, "Anahata", [
        "Esternón - Suprarrenal",
        "Esternón - Bazo",
        "Tráquea - Tráquea",
        "Tráquea - Corazón",
        "Esófago - Esófago",
        "Esófago - Hiato Esofágico",
        "Esófago - Vejiga IZQ",
    ]),
    (2, "Tronco", 1, "Tórax", 4, "Pecho Bajo", [
        "Carina - Carina",
        "Hiato Esofágico - Lengua",
        "Hiato Esofágico - Esófago",
        "Hiato Esofágico - Testículo DER/Ovario DER",
        "Cardias - Suprarrenal",
    ]),
    (2, "Tronco", 1, "Tórax", 5, "Cavidad", [
        "Cardias - Esófago",
        "Cardias - Testículo/Ovario DER",
        "Condral - Condral",
    ]),
    (2, "Tronco", 1, "Tórax", 6, "Diafragma", [
        "Diafragma - Diafragma",
        "Diafragma - Riñón IZQ",
        "Costilla 7 - Costilla 7",
        "Peritoneo - Peritoneo",
    ]),
    (2, "Tronco", 1, "Tórax", 7, "Corazón", [
        "Coronarias - Pulmón IZQ",
        "Seno Auriculoventricular - Riñón IZQ",
        "Corazón - Corazón",
        "Corazón - Páncreas",
        "Corazón - Vejiga",
        "Pericardio - Pericardio",
    ]),
    (2, "Tronco", 1, "Tórax", 8, "Pecho Lateral", [
        "Pectoral Interior - Pectoral Interior",
        "Pectoral - Pectoral",
        "Pezón DER - Gemelos IZQ",
        "Axila - Axila",
    ]),
    (2, "Tronco", 1, "Tórax", 9, "Pleura", [
        "Pleura - Pleura",
        "Pleura DER - Pleura DER",
        "Pleura - Peritoneo",
        "Pleura - Apéndice",
    ]),
    (2, "Tronco", 2, "Hepatitis", 1, "Hepático 1", [
        "Colon Descendente - Hígado",
        "Hígado - Pleura",
        "Hígado - Hígado",
        "Duodeno - Hígado",
    ]),
    (2, "Tronco", 2, "Hepatitis", 2, "Hepático 2", [
        "Colon Ascendente - Hígado",
        "Costo Hepático - Hígado",
        "Colon Transverso - Hígado",
        "Cola de Páncreas - Hígado",
    ]),
    (2, "Tronco", 2, "Hepatitis", 3, "Hepático 3", [
        "Bazo - Hígado",
        "Píloro - Hígado",
        "Cabeza de Páncreas - Hígado",
        "Timo - Hígado",
    ]),
    (2, "Tronco", 3, "Abdomen", 1, "Estómago", [
        "Estómago - Estómago",
        "Estómago - Corazón",
        "Estómago - Píloro",
        "Estómago - Suprarrenal",
    ]),
    (2, "Tronco", 3, "Abdomen", 2, "Píloro", [
        "Píloro - Píloro",
        "Píloro - Lengua IZQ",
        "Píloro - Riñón IZQ",
        "Píloro - Uretero RAS",
        "Píloro - Glúteo IZQ",
    ]),
    (2, "Tronco", 3, "Abdomen", 3, "Hígado", [
        "Hígado - Corazón",
        "Hígado - Páncreas",
        "Hígado - Píloro",
        "Hígado - Riñón IZQ",
    ]),
    (2, "Tronco", 3, "Abdomen", 4, "Zona Hepática", [
        "Ligamento Hepático - Riñón DER",
        "Perihepático - Perihepático",
        "Costal - Costal",
    ]),
    (2, "Tronco", 3, "Abdomen", 5, "Vesícula", [
        "Vesícula - Vesícula",
        "Vesícula - Riñón DER",
        "Conducto de Vesícula - Riñón DER",
    ]),
    (2, "Tronco", 3, "Abdomen", 6, "Bazo", [
        "Bazo Horizontal - Bazo Horizontal",
        "Bazo Vertical - Bazo Vertical",
        "Bazo - Hipotálamo",
        "Bazo - Duodeno",
        "Bazo - Pulmón Izquierdo",
        "Costo Diafragmático - Costo Diafragmático",
    ]),
    (2, "Tronco", 3, "Abdomen", 7, "Páncreas", [
        "Cabeza de Páncreas - Suprarrenal",
        "Cuerpo de Páncreas - Cola de Páncreas",
        "Punta de Páncreas - Bazo",
        "Punta de Páncreas - Riñón IZQ",
        "Ligamento Pancreático - Bazo",
        "Ligamento Pancreático - Colon Descendente",
        "Conducto de Páncreas - Riñón IZQ",
    ]),
    (2, "Tronco", 3, "Abdomen", 8, "Ombligo", [
        "Epiplón - Epiplón",
        "Uretero - Uretero",
        "Uretero RAS - Riñón RAS",
        "Duodeno - Duodeno",
        "Duodeno - Riñón DER",
        "Duodeno - Riñón IZQ",
    ]),
    (2, "Tronco", 3, "Abdomen", 9, "Intersección", [
        "Válvula Ileocecal - Riñón DER",
        "Ciego - Ciego",
        "Ciego - Riñón DER",
        "Contraciego - Contraciego",
        "Apéndice - Timo",
        "Apéndice - Pleura IZQ",
    ]),
    (2, "Tronco", 3, "Abdomen", 10, "Colon", [
        "Colon Ascendente - Colon Descendente",
        "Colon Ascendente - Riñón DER",
        "Colon Transverso - Colon Transverso",
        "Colon Transverso - Vejiga Media",
        "Colon Transverso - Testículo RAS/Ovario RAS",
        "Colon Descendente - Colon Descendente",
        "Colon Descendente - Recto",
        "Sigmoides - Recto",
    ]),
    (2, "Tronco", 4, "Espalda", 1, "Dorsales", [
        "Dorsal 2 - Dorsal 2",
        "Dorsal 5 - Corazón",
        "Dorso 5 RAS - Lumbar 2 RAS",
        "Dorsal 6 - Dorsal 6",
    ]),
    (2, "Tronco", 4, "Espalda", 2, "Espalda Alta", [
        "Cava - Cava",
        "Suprarrenal - Suprarrenal",
        "Suprarrenal - Pulmón RAS",
        "Suprarrenal - Hígado",
        "Suprarrenal - Recto",
    ]),
    (2, "Tronco", 4, "Espalda", 3, "Homóplato", [
        "Pulmón - Pulmón",
        "Pulmón DER - Bulbo",
        "Escápula - Escápula",
    ]),
    (2, "Tronco", 4, "Espalda", 4, "Retrohepático", [
        "Lóbulo Posterior del Hígado - Riñón IZQ",
        "Flanco - Flanco",
    ]),
    (2, "Tronco", 4, "Espalda", 5, "Riñón", [
        "Cápsula Renal - Cápsula Renal",
        "Cápsula Renal - Riñón DER",
        "Riñón - Riñón",
        "Riñón IZQ - Ojo RAS",
        "Riñón IZQ - Tiroides",
        "Cáliz Renal RAS - Uretero RAS",
    ]),
    (2, "Tronco", 4, "Espalda", 6, "Espalda Baja", [
        "Lumbar 4 - Lumbar 4",
        "Cuadrado - Cuadrado",
        "Staquibraquis - Staquibraquis",
    ]),

    # ────────────────────────────────────────────────────────
    # REGIÓN 3: PELVIS
    # ────────────────────────────────────────────────────────
    (3, "Pelvis", 1, "Delantera", 1, "Pubis", [
        "Vejiga - Vejiga",
        "Suprapúbico - Suprapúbico",
        "Pudendo - Pudendo",
    ]),
    (3, "Pelvis", 1, "Delantera", 2, "Cadera", [
        "Cadera - Cadera",
        "Cresta Ilíaca - Cresta Ilíaca",
        "Nervio Inguinal - Nervio Inguinal",
        "Nervio Inguinal - Hígado",
    ]),
    (3, "Pelvis", 1, "Delantera", 3, "Fémur", [
        "Cuello de Fémur - Cuello de Fémur",
        "Trocánter Mayor - Trocánter Mayor",
        "Trocánter Mayor - Riñón HOMOLAT",
        "Trocánter Menor - Trocánter Menor",
    ]),
    (3, "Pelvis", 2, "Trasera", 1, "Sacro", [
        "Interiliaco - Sacro",
        "Iliaco - Iliaco",
        "Sacro - Sacro",
        "Saco de Douglas - Femoral",
    ]),
    (3, "Pelvis", 2, "Trasera", 2, "Coxis", [
        "Coxis - Coxis",
        "Recto - Recto",
        "Recto - Ano",
        "Ano - Ano",
    ]),
    (3, "Pelvis", 2, "Trasera", 3, "Trasero", [
        "Glúteo - Glúteo",
        "Glúteo - Femoral",
        "Rama Isquiática - Rama Isquiática",
        "Isquion - Isquion",
    ]),
    (3, "Pelvis", 3, "Sexo", 1, "Fémina A", [
        "Útero - Útero",
        "Útero - Ovario RAS",
        "Clítoris - Clítoris",
        "Clítoris - Sacro",
        "Uretra - Uretra",
    ]),
    (3, "Pelvis", 3, "Sexo", 2, "Fémina B", [
        "Vagina - Vagina",
        "Vagina - Vejiga Media",
        "Trompa RAS - Trompa",
        "Trompa RAS - Útero",
        "Ovario - Ovario",
    ]),
    (3, "Pelvis", 3, "Sexo", 3, "Macho", [
        "Cuerpo Cavernoso - Cuerpo Cavernoso",
        "Testículo - Testículo",
        "Próstata - Próstata",
        "Próstata - Recto",
    ]),

    # ────────────────────────────────────────────────────────
    # REGIÓN 4: MIEMBROS
    # ────────────────────────────────────────────────────────
    (4, "Miembros", 1, "Brazo", 1, "Brazo Alto", [
        "Deltoides - Deltoides",
        "Deltoides DER - Riñón DER",
        "Bursa - Bursa",
        "Húmero - Húmero",
    ]),
    (4, "Miembros", 1, "Brazo", 2, "Brazo Medio", [
        "Codo - Codo",
        "Braquial - Braquial",
        "Radio - Radio",
        "Cúbito - Cúbito",
    ]),
    (4, "Miembros", 1, "Brazo", 3, "Mano", [
        "Muñeca Anterior - Muñeca Anterior",
        "Muñeca Posterior - Muñeca Posterior",
        "Palma - Palma",
        "Palma RAS - Plantar RAS",
        "Dorso Mano - Dorso Mano",
        "Índice - Índice",
    ]),
    (4, "Miembros", 2, "Pierna", 1, "Pierna Alta", [
        "Aductor Menor - Aductor Menor",
        "Aductor - Aductor",
        "Cuádriceps - Cuádriceps",
        "Tensor Fascia Lata - Tensor Fascia Lata",
    ]),
    (4, "Miembros", 2, "Pierna", 2, "Pierna Media", [
        "Ligamento Externo de Rodilla - Mesenterio",
        "Rótula - Rótula",
        "Tibia - Tibia",
        "Peroné - Peroné",
    ]),
    (4, "Miembros", 2, "Pierna", 3, "Pierna Trasera", [
        "Ciático - Ciático",
        "Poplíteo - Poplíteo",
        "Aquiles Alto - Aquiles Alto",
        "Aquiles - Aquiles",
        "Aquiles Bajo - Aquiles Bajo",
    ]),
    (4, "Miembros", 2, "Pierna", 4, "Pie", [
        "Empeine - Empeine",
        "Dedo Gordo - Dedo Gordo",
        "Calcáneo - Calcáneo",
        "Plantar - Plantar",
    ]),

    # ────────────────────────────────────────────────────────
    # REGIÓN 5: EXTRAS
    # ────────────────────────────────────────────────────────
    (5, "Extras", 1, "Variables", 1, "Pares Generales", [
        "Suprarrenal - Todo el frente (A-F)",
        "Par Gen Ombligo - Órgano/Tejido/Punto RAS",
        "Nervio Inguinal DER - Articulación Dolorosa 1-13 RAS",
    ]),
    (5, "Extras", 1, "Variables", 2, "Traumatismo", [
        "Par Gen Ombligo - Órgano/Tejido/Punto RAS",
        "Nervio Inguinal DER - Articulación Dolorosa 1-13",
        "Punto Trauma - Punto Trauma",
        "Punto Trauma - Riñón HOMOLAT",
        "Punto Trauma Sedante (-)",
        "Punto Trauma Estimulante (+)",
    ]),
    (5, "Extras", 1, "Variables", 3, "Personalizados", [
        "Par Nuevo",
        "Biomagnetopuntura",
        "Par Vacuna",
    ]),
    (5, "Extras", 2, "Columna Vertebral", 1, "Predeterminados", [
        "Cervical 1 - Cervical 7",
        "Dorsal 1 - Dorsal 12",
        "Lumbar 1 - Lumbar 5",
        "Sacro 1 - Sacro 1",
        "Coxis 1 - Sacro 4",
    ]),
    (5, "Extras", 2, "Columna Vertebral", 2, "Homólogos", [
        "Cervical RAS - Cervical RAS",
        "Dorsal RAS - Dorsal RAS",
        "Lumbar RAS - Lumbar RAS",
        "Sacro RAS - Sacro RAS",
        "Coxis RAS - Coxis RAS",
    ]),
    (5, "Extras", 2, "Columna Vertebral", 3, "Rastreo Cervical", [
        "Cervical RAS - Dorsal RAS",
        "Cervical RAS - Lumbar RAS",
        "Cervical RAS - Sacro RAS",
        "Cervical RAS - Coxis RAS",
    ]),
    (5, "Extras", 2, "Columna Vertebral", 4, "Rastreo Dorsal", [
        "Dorsal RAS - Cervical RAS",
        "Dorsal RAS - Lumbar RAS",
        "Dorsal RAS - Sacro RAS",
        "Dorsal RAS - Coxis RAS",
    ]),
    (5, "Extras", 2, "Columna Vertebral", 5, "Rastreo Lumbar", [
        "Lumbar RAS - Cervical RAS",
        "Lumbar RAS - Dorsal RAS",
        "Lumbar RAS - Sacro RAS",
        "Lumbar RAS - Coxis RAS",
    ]),
    (5, "Extras", 2, "Columna Vertebral", 6, "Rastreo Sacro", [
        "Sacro RAS - Cervical RAS",
        "Sacro RAS - Dorsal RAS",
        "Sacro RAS - Lumbar RAS",
        "Sacro RAS - Coxis RAS",
    ]),
    (5, "Extras", 2, "Columna Vertebral", 7, "Rastreo Coxis", [
        "Coxis RAS - Cervical RAS",
        "Coxis RAS - Dorsal RAS",
        "Coxis RAS - Lumbar RAS",
        "Coxis RAS - Sacro RAS",
    ]),
    (5, "Extras", 3, "Ejes Corporales", 1, "Eje Vertical", [
        "Pulmón Frontal DER - Nervio Inguinal DER",
        "Pulmón Frontal IZQ - Nervio Inguinal IZQ",
    ]),
    (5, "Extras", 3, "Ejes Corporales", 2, "Eje Horizontal", [
        "Frente - Sacro",
    ]),
    (5, "Extras", 3, "Ejes Corporales", 3, "Eje Transverso", [
        "Suprarrenales - Suprarrenales",
        "Dorsal 2 - Sacro 2",
    ]),
]

# Region prefix mapping
REGION_PREFIX = {
    1: "C",  # Cabeza
    2: "T",  # Tronco
    3: "P",  # Pelvis
    4: "M",  # Miembros
    5: "E",  # Extras
}


def normalize_pair(pair_str):
    """Normalize a pair string for dedup comparison."""
    return pair_str.strip().lower().replace("  ", " ")


def split_pair(pair_str):
    """Split 'Polo1 - Polo2' into (polo1, polo2). Handle edge cases."""
    parts = pair_str.split(" - ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    # Single term (no dash) — treat as self-pair
    return pair_str.strip(), pair_str.strip()


def build_json():
    """Build the JSON structure from REGIONS_DATA."""
    # Gather all pairs first for dedup
    # key = (region_id, zona_id, bloque_id, pair_normalized)
    seen_global = {}   # normalized_pair -> first_occurrence_id
    duplicates = []

    # Organize into nested structure
    regions_map = {}   # region_id -> region_dict
    zonas_map = {}     # (region_id, zona_id) -> zona_dict
    bloques_map = {}   # (region_id, zona_id, bloque_id) -> bloque_dict

    global_pair_counter = 0

    for (rid, rname, zid, zname, bid, bname, pares) in REGIONS_DATA:
        rkey = rid
        zkey = (rid, zid)
        bkey = (rid, zid, bid)

        if rkey not in regions_map:
            regions_map[rkey] = {
                "id": rid,
                "nombre": rname,
                "zonas": [],
                "_zona_keys": []
            }

        if zkey not in zonas_map:
            zonas_map[zkey] = {
                "id": f"{rid}.{zid}",
                "nombre": zname,
                "bloques": [],
                "_bloque_keys": []
            }
            regions_map[rkey]["_zona_keys"].append(zkey)
            regions_map[rkey]["zonas"].append(zonas_map[zkey])

        if bkey not in bloques_map:
            bloques_map[bkey] = {
                "id": f"{rid}.{zid}.{bid}",
                "nombre": bname,
                "pares": []
            }
            zonas_map[zkey]["_bloque_keys"].append(bkey)
            zonas_map[zkey]["bloques"].append(bloques_map[bkey])

        for pair_str in pares:
            bloques_map[bkey]["pares"].append(pair_str)

    # Now build the flat pairs list with dedup
    pairs_list = []
    all_pair_entries = []  # (rid, zid, bid, bloque_nombre, zona_nombre, region_nombre, pair_str, idx_in_bloque)

    for (rid, rname, zid, zname, bid, bname, pares) in REGIONS_DATA:
        for i, pair_str in enumerate(pares):
            all_pair_entries.append((rid, zid, bid, bname, zname, rname, pair_str, i + 1))

    pair_id_counter = defaultdict(int)

    for (rid, zid, bid, bname, zname, rname, pair_str, idx) in all_pair_entries:
        norm = normalize_pair(pair_str)
        prefix = REGION_PREFIX[rid]
        pair_id = f"{prefix}{rid}.{zid}.{bid}.{idx}"

        polo1, polo2 = split_pair(pair_str)
        tipo = "bilateral" if polo1.lower() == polo2.lower() else "cruzado"

        if norm in seen_global:
            duplicates.append({
                "par": pair_str,
                "original_id": seen_global[norm],
                "duplicado_en": f"{rname} > {zname} > {bname}"
            })
        else:
            seen_global[norm] = pair_id
            pairs_list.append({
                "id": pair_id,
                "nombre": pair_str,
                "region": rname,
                "zona": zname,
                "bloque": bname,
                "polo1": polo1,
                "polo2": polo2,
                "tipo": tipo
            })

    # Clean internal helper keys from structure
    regions_output = []
    for rid in sorted(regions_map.keys()):
        rdict = regions_map[rid]
        zonas_clean = []
        for zdict in rdict["zonas"]:
            bloques_clean = [b for b in zdict["bloques"]]
            zonas_clean.append({
                "id": zdict["id"],
                "nombre": zdict["nombre"],
                "bloques": bloques_clean
            })
        regions_output.append({
            "id": rid,
            "nombre": rdict["nombre"],
            "zonas": zonas_clean
        })

    output = {
        "version": "2.0",
        "fuente": "Tablas Holoacademia - Alejandro Lavín",
        "total": len(pairs_list),
        "duplicados_eliminados": len(duplicates),
        "regiones": regions_output,
        "pairs": pairs_list
    }

    return output, duplicates


def count_by_region(pairs):
    counts = defaultdict(int)
    for p in pairs:
        counts[p["region"]] += 1
    return counts


def build_pdf(output_data, duplicates, pdf_path):
    """Generate PDF review document using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=0.6*inch,
        leftMargin=0.6*inch,
        topMargin=0.7*inch,
        bottomMargin=0.7*inch,
        title="Pares Biomagnéticos - Revisión v5"
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#1a3a5c"),
        spaceAfter=8,
        alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleCustom",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#3d6ea8"),
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    region_style = ParagraphStyle(
        "RegionHeader",
        parent=styles["Heading1"],
        fontSize=13,
        textColor=colors.white,
        backColor=colors.HexColor("#1a3a5c"),
        spaceBefore=12,
        spaceAfter=6,
        leftIndent=-4,
        rightIndent=-4,
        borderPad=4,
    )
    zona_style = ParagraphStyle(
        "ZonaHeader",
        parent=styles["Heading2"],
        fontSize=10,
        textColor=colors.HexColor("#1a3a5c"),
        spaceBefore=8,
        spaceAfter=3,
        borderColor=colors.HexColor("#3d6ea8"),
        borderWidth=0,
        borderPad=2,
    )
    bloque_style = ParagraphStyle(
        "BloqueHeader",
        parent=styles["Normal"],
        fontSize=8.5,
        textColor=colors.HexColor("#555555"),
        fontName="Helvetica-Bold",
        spaceBefore=4,
        spaceAfter=2,
    )
    pair_style = ParagraphStyle(
        "PairLine",
        parent=styles["Normal"],
        fontSize=7.5,
        textColor=colors.HexColor("#222222"),
        leftIndent=10,
        spaceBefore=0,
        spaceAfter=1,
    )
    normal_small = ParagraphStyle(
        "NormalSmall",
        parent=styles["Normal"],
        fontSize=8.5,
        spaceAfter=3,
    )

    story = []

    # ── PORTADA ──
    story.append(Spacer(1, 0.4*inch))
    story.append(Paragraph("Pares Biomagnéticos", title_style))
    story.append(Paragraph("Tablas Holoacademia — Alejandro Lavín", subtitle_style))
    story.append(Paragraph("Revisión v5 — Documento generado automáticamente", subtitle_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a3a5c")))
    story.append(Spacer(1, 0.15*inch))

    # Summary table
    region_counts = count_by_region(output_data["pairs"])
    total = output_data["total"]
    dups = output_data["duplicados_eliminados"]

    summary_data = [["Región", "Pares"]]
    for region_name in ["Cabeza", "Tronco", "Pelvis", "Miembros", "Extras"]:
        summary_data.append([region_name, str(region_counts.get(region_name, 0))])
    summary_data.append(["", ""])
    summary_data.append(["TOTAL PARES (limpios)", str(total)])
    summary_data.append(["Duplicados eliminados", str(dups)])

    t = Table(summary_data, colWidths=[2.5*inch, 1*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4fa"), colors.white]),
        ("FONTNAME", (0, -2), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -2), (-1, -1), colors.HexColor("#1a3a5c")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    story.append(t)
    story.append(Spacer(1, 0.2*inch))

    if duplicates:
        story.append(Paragraph(f"<b>Duplicados eliminados ({len(duplicates)}):</b>", normal_small))
        for d in duplicates:
            story.append(Paragraph(
                f"&nbsp;&nbsp;• {d['par']} <font color='#888888'>(en {d['duplicado_en']})</font>",
                pair_style
            ))
        story.append(Spacer(1, 0.1*inch))

    story.append(PageBreak())

    # ── CONTENT ──
    # Build pair lookup by bloque id
    pair_by_bloque = defaultdict(list)
    for p in output_data["pairs"]:
        key = (p["region"], p["zona"], p["bloque"])
        pair_by_bloque[key].append(p)

    for region in output_data["regiones"]:
        rname = region["nombre"]
        rcount = region_counts.get(rname, 0)
        story.append(Paragraph(f"  REGIÓN: {rname.upper()}  ({rcount} pares)", region_style))

        for zona in region["zonas"]:
            zname = zona["nombre"]
            story.append(Paragraph(f"Zona: {zname}", zona_style))

            for bloque in zona["bloques"]:
                bname = bloque["nombre"]
                pairs_in_bloque = pair_by_bloque.get((rname, zname, bname), [])
                story.append(Paragraph(f"▸ {bname}", bloque_style))

                # 2-column table for pairs
                if pairs_in_bloque:
                    # Split into left/right columns
                    mid = (len(pairs_in_bloque) + 1) // 2
                    left_col = pairs_in_bloque[:mid]
                    right_col = pairs_in_bloque[mid:]

                    col_rows = []
                    for i in range(mid):
                        lp = left_col[i]
                        rp = right_col[i] if i < len(right_col) else None
                        l_text = f"<font color='#888888'>{i+1}.</font> {lp['nombre']}"
                        r_text = (
                            f"<font color='#888888'>{mid+i+1}.</font> {rp['nombre']}"
                            if rp else ""
                        )
                        col_rows.append([
                            Paragraph(l_text, pair_style),
                            Paragraph(r_text, pair_style),
                        ])

                    pair_table = Table(col_rows, colWidths=[3.5*inch, 3.5*inch])
                    pair_table.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 1),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                        ("LEFTPADDING", (0, 0), (-1, -1), 2),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ]))
                    story.append(pair_table)
                else:
                    # Show raw pares from the bloque definition (Extras/Variables may have no pair object)
                    for i, p in enumerate(bloque["pares"]):
                        story.append(Paragraph(f"&nbsp;&nbsp;{i+1}. {p}", pair_style))

            story.append(Spacer(1, 0.05*inch))

    doc.build(story)
    print(f"PDF generado: {pdf_path}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Reconstruyendo biomagnetic_pairs_db.json v2.0")
    print("=" * 60)

    output_data, duplicates = build_json()

    # Save JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\nJSON guardado: {OUTPUT_JSON}")

    # Print summary
    region_counts = count_by_region(output_data["pairs"])
    print("\n--- RESUMEN POR REGIÓN ---")
    for region_name in ["Cabeza", "Tronco", "Pelvis", "Miembros", "Extras"]:
        print(f"  {region_name:20s}: {region_counts.get(region_name, 0):4d} pares")
    print(f"  {'TOTAL':20s}: {output_data['total']:4d} pares")
    print(f"  {'Duplicados eliminados':20s}: {output_data['duplicados_eliminados']:4d}")

    if duplicates:
        print("\n--- DUPLICADOS ELIMINADOS ---")
        for d in duplicates:
            print(f"  • '{d['par']}' → en {d['duplicado_en']} (original: {d['original_id']})")

    # Build PDF
    print("\nGenerando PDF de revisión...")
    build_pdf(output_data, duplicates, OUTPUT_PDF)

    print("\n" + "=" * 60)
    print("¡Proceso completado!")
    print(f"  JSON: {OUTPUT_JSON}")
    print(f"  PDF:  {OUTPUT_PDF}")
    print("=" * 60)
