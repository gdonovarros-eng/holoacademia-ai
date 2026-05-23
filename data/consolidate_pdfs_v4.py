"""
consolidate_pdfs_v4.py
Integra pares biomagnéticos extraídos de los tres PDFs al biomagnetic_pairs_db.json
actualizando de v3.0 (675 pares) a v4.0.

Fuentes procesadas:
1. BIOMAGNETISMO-CUANTICO.pdf  (266 pp, catálogo alfabético ~1056 entradas)
2. BIOMAGNETISMO.pdf           (180 pp, por-enfermedad + Lista General ~350 entradas)
3. Manual-de-Biomagnetismo-2021-Mod-2-1.pdf (24 pp, ya incluido en v3.0)

Resultado esperado: v4.0 con ~900-1100 pares únicos totales.
"""

import json
import unicodedata
import re
from pathlib import Path

DB_PATH = Path(__file__).parent / "biomagnetic_pairs_db.json"

# ─── Pares extraídos de los PDFs ─────────────────────────────────────────────
# Formato "Region:Zona": [lista de pares]
# La deduplicación normalizada elimina automáticamente los que ya existen en v3.0

NEW_PDF_PAIRS = {

    # ══════════════════════════════════════════════════════════════════════════
    # CABEZA › CORONILLA
    # ══════════════════════════════════════════════════════════════════════════
    "Cabeza:Coronilla": [
        # Pineal (PDF2 Lista General)
        "Pineal - Bulbo Raquídeo",
        "Pineal - Útero",
        "Pineal - Cerebelo",
        "Pineal - Hipófisis",
        "Pineal - Próstata",
        "Pineal - Duodeno",
        "Pineal - Puente de Varolo",
        "Post Pineal - Post Pineal",
        "Post Pineal - Bulbo Raquídeo",
        "Pineal - Empeine",
        "Pineal - Mama",
        "Pineal - Planta del Pie",
        "Pineal - Hígado",
        # Prepineal
        "Prepineal - Vejiga",
        "Prepineal - Prepineal",
        # Polo / Prepolo
        "Prepolo - Bulbo Raquídeo",
        "Prepolo - Antepolo",
        "Polo - Polo",
        # Parietal (PDF2 LG)
        "Parietal - Riñón Contralateral",
        "Parietal Derecho Posterior - Parietal Derecho Posterior",
        "Parietales - Colon Transverso",
        # Polígono / Craneal
        "Polígono de Willis - Polígono de Willis",
        "Craneal - Craneal",
        # Tallo parietal
        "Tallo Parietal - Cerebelo",
        # Antecuerno (PDF1 #22)
        "Antecuerno - Antecuerno",
        # Cisura (PDF1 / Atlas)
        "Cisura Silvio - Cisura Silvio",
        "Cisura Lambda - Cisura Lambda",
        "Cisura Temporooccipital - Cisura Temporooccipital",
        "Cuerpo Calloso Derecho - Cerebelo",
        "Tálamo - Tálamo",
        "Tálamo - Hipófisis",
        "Tálamo - Corteza",
        "Tálamo - Amígdala",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # CABEZA › POSTERIOR  (bulbo, occipital, cerebelo, mastoides)
    # ══════════════════════════════════════════════════════════════════════════
    "Cabeza:Posterior": [
        # Occipital (PDF2 LG)
        "Occipital - Occipital",
        "Occipital - Riñón",
        "Occipital - Testículo",
        # Base de cráneo (PDF1 #68)
        "Base de Cráneo - Base de Cráneo",
        # Cerebelo
        "Cerebelo - Cerebelo",
        "Cerebelo - Arriba del Bulbo Raquídeo",
        "Cerebelo - Riñón",
        "Cerebelo - Yeyuno",
        "Cerebelo - Supraespinoso",
        # Cuarto ventrículo
        "Cuarto Ventrículo - Bulbo",
        # Bulbo Raquídeo / Bulbo
        "Bulbo Raquídeo - Tiroides",
        "Bulbo Raquídeo - Corazón",
        "Bulbo Raquídeo - Colon Descendente",
        "Bulbo Raquídeo - Vejiga",
        "Bulbo Raquídeo - Pineal",
        # Tallo cerebral
        "Tallo Cerebral - Tallo Cerebral",
        # Amígdala Cerebral (PDF1 #8)
        "Amígdala Cerebral - Timo",
        # Apófisis mastoides (PDF1 #37-43)
        "Apófisis Mastoides - Bulbo",
        "Apófisis Mastoides - Pericardio",
        "Apófisis Mastoides - Duodeno",
        "Apófisis Mastoides - Riñón Ipsilateral",
        "Apófisis Mastoides - Apófisis Mastoides",
        "Apófisis Mastoides Izquierda - Riñón Izquierdo",
        "Apófisis Mastoides Izquierdas - Apófisis Mastoides Derecho",
        # Piso orbital
        "Piso Orbital - Cerebelo",
        "Piso Orbital - Piso Orbital",
        # Supraciliar / Interciliar
        "Supraciliar - Bulbo Raquídeo",
        "Interciliar - Bulbo Raquídeo",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # CABEZA › LATERAL  (temporal, sien, mastoides, arco cigomático)
    # ══════════════════════════════════════════════════════════════════════════
    "Cabeza:Lateral": [
        # Temporal (PDF2 LG #271-276)
        "Temporal - Oído",
        "Temporal - Bulbo Raquídeo",
        "Temporal - Yugular",
        "Temporal Derecho - Temporal Derecho",
        "Temporal Izquierdo - Temporal Izquierdo",
        "Temporooccipital - Temporooccipital",
        # Sien (PDF2 LG #245-248)
        "Sien - Suprarrenal",
        "Sien - Riñón",
        "Sien Derecha - Sien Derecha",
        "Sien - Bulbo Raquídeo",
        # Arco cigomático (PDF1 #51-52)
        "Arco Cigomático - Arco Cigomático",
        "Arco Cigomático - Parietal",
        # Preauricular
        "Preauricular - Vejiga",
        "Preauricular - Preauricular",
        # Ángulo mandibular / gonión (PDF1 #14-15)
        "Ángulo Derecho - Ángulo Derecho",
        "Ángulo Gonión - Ángulo",
        # Aurículo Ventricular (PDF1 #65)
        "Aurículo Ventricular - Riñón Izquierdo",
        # Presín
        "Presín - Canal Auditivo",
        # Radio temporal
        "Radio - Radio",
        # Quiasma
        "Quiasma - Quiasma",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # CABEZA › FRENTE  (hipófisis, frente, adenohipofisis, área visual)
    # ══════════════════════════════════════════════════════════════════════════
    "Cabeza:Frente": [
        # Adenohipofisis (PDF1 #2)
        "Adenohipofisis - Riñón Izquierdo",
        # Área visual (PDF1 #55)
        "Área Visual - Riñón",
        # Suprasensorial
        "Suprasensorial - Hipófisis",
        # Timo - Hipófisis (Timo lleva hipófisis al frente)
        "Timo - Hipófisis",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # CABEZA › ROSTRO  (ojo, nariz, boca, dental, adenoides, senos)
    # ══════════════════════════════════════════════════════════════════════════
    "Cabeza:Rostro": [
        # Adenoides (PDF1 #3, PDF2 LG #2)
        "Adenoides - Adenoides",
        # Amígdala (PDF2 LG #5-7)
        "Amígdala - Amígdala",
        "Amígdala Derecha - Amígdala Izquierda",
        "Amígdala - Hígado",
        # Alveolo
        "Alveolo - Alveolo",
        # Dental (PDF2 LG #57)
        "Dental - Riñón",
        "Dental Derecho - Riñón Derecho",
        "Dental Izquierdo - Riñón Izquierdo",
        # Lengua
        "Lengua - Mandíbula",
        "Lengua - Timo",
        "Lengua - Lengua",
        "Lengua Izquierda - Corazón",
        "Lengua Izquierda - Hígado",
        # Maxilar / Mandíbula
        "Maxilar - Maxilar",
        "Mandíbula - Mandíbula",
        "Mentón - Mentón",
        "Labio - Labio",
        "Labio Superior - Labio Inferior",
        "Comisura - Comisura",
        # Oído / Yunque / Unguis (PDF2 LG #97-98, PDF1 #1055)
        "Oído - Oído",
        "Oído - Riñón Contralateral",
        "Yunque - Riñón Ipsilateral",
        "Unguis - Unguis",
        # Parótida (PDF2 LG #115-116)
        "Parótida - Timo",
        "Parótida Izquierda - Pineal",
        # Párpado
        "Párpado - Párpado",
        # Nariz / Senos paranasales (PDF2 LG #241-244)
        "Nariz - Nariz",
        "Seno Aurículo Ventricular - Riñón Izquierdo",
        "Seno Esfenoidal - Seno Esfenoidal",
        "Seno Etmoidal - Seno Etmoidal",
        "Seno Frontal - Seno Frontal",
        "Seno Nasal - Seno Nasal",
        "Seno Paranasal - Seno Paranasal",
        # Retronasal
        "Retronasal - Retronasal",
        # Hioides
        "Hioides - Hioides",
        # Malar / Pómulo
        "Malar - Malar",
        "Malar Derecho - Malar Izquierdo",
        # Ojo / lacrimal / canto
        "Ojo - Ojo",
        "Ojo Derecho - Riñón Derecho",
        "Ojo Izquierdo - Riñón Izquierdo",
        "Lacrimal - Lacrimal",
        "Canto - Canto",
        "Canto de Ojo - Canto de Ojo",
        # Rama mandibular
        "Rama Mandibular - Rama Mandibular",
        "Rama Mandibular - Cola de Páncreas",
        "Rama Mandibular Lateral - Rama Mandibular Lateral",
        # Mango del estómago (sensación en garganta)
        "Mango - Mango",
        # Rama isquion
        "Rama Isquion - Rama Isquion",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # CABEZA › CUELLO  (tiroides, tráquea, laringe, subclavia, ECM)
    # ══════════════════════════════════════════════════════════════════════════
    "Cabeza:Cuello": [
        # Angina (PDF1 #12-13)
        "Angina - Cerebelo",
        "Angina - Angina",
        # Tiroides (PDF2 LG #299-303)
        "Tiroides - Tiroides",
        "Tiroides - Bulbo Raquídeo",
        "Tiroides - Duodeno",
        "Tiroides - Páncreas",
        "Tiroides - Hígado",
        "Tiroides - Escápula Derecha",
        "Tiroides Derecha - Tiroides Izquierda",
        # Paratiroides
        "Paratiroides - Paratiroides",
        "Paratiroides Derecha - Riñón Derecho",
        "Paratiroides Derecho - Corazón",
        # Laringe (PDF2 LG #83)
        "Laringe - Laringe",
        "Laringe - Tabique Nasal",
        "Laringe - Duodeno",
        # Tráquea (PDF1, PDF2 LG #305-306)
        "Tráquea - Corazón",
        "Tráquea - Tráquea",
        # Subclavia (PDF2 LG #250-251)
        "Subclavia - Esófago",
        "Subclavia - Subclavia",
        # ECM
        "ECM Derecho - ECM Izquierdo",
        "ECM - Timo",
        # Yugular (PDF2 LG #350)
        "Yugular - Temporal",
        "Yugular - Carótida",
        "Yugular - Yugular",
        # Cuello
        "Cuello - Cuello",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # TRONCO › TÓRAX  (corazón, pulmón, pericardio, timo, pleura, aorta…)
    # ══════════════════════════════════════════════════════════════════════════
    "Tronco:Tórax": [
        # Aorta (PDF1 #23)
        "Aorta - Aorta",
        # Arteria axilar (PDF1 #56)
        "Arteria Axilar - Arteria Axilar",
        # Axila (PDF1 #66-67)
        "Axila - Timo",
        "Axila - Axila",
        # Bazo - Pulmón (PDF1 #73)
        "Bazo - Pulmón",
        # Botón aórtico
        "Botón Aórtico - Pericardio",
        # Bronquio
        "Bronquio - Bronquio",
        "Bronquio Derecho - Pericardio",
        # Cava
        "Cava - Cava",
        "Cava - Timo",
        # Cardias (Tórax bajo)
        "Cardias - Cardias",
        "Cardias - Nervio Vago",
        "Cardias - Esófago",
        "Cardias - Píloro",
        "Cardias - Suprarrenal",
        "Cardias - Testículo",
        "Cardias - Apéndice",
        "Cardias - Coronarias",
        "Cardias - Vagina",
        # Corazón (PDF2 LG #44-45)
        "Corazón - Corazón",
        "Corazón - Paratiroides Derecho",
        "Corazón - Estómago",
        "Corazón - Hígado",
        "Corazón - Riñón",
        "Corazón - Vejiga",
        "Corazón - Escápula Izquierda",
        "Corazón - Páncreas",
        "Corazón - Esternón",
        # Coronaria / Coronarias
        "Coronaria - Pulmón",
        "Coronaria - Tendón Pectoral",
        "Coronarias - Pulmón",
        # Costilla
        "Costilla del Mismo Lado - Punta Baja del Corazón",
        "Costillas 1 a 12 - Riñón",
        "1ª Costilla - 1ª Costilla",
        "7ª Costilla - 7ª Costilla",
        # Condral
        "Condral - Condral",
        "Condral Derecho - Bronquio Derecho",
        # ECM - Timo (ya en cuello pero también tórax)
        # Escápula (tronco torácico)
        "Escápula - Escápula",
        "Escápula - Pulmón",
        "Escápula Derecha - Pulmón",
        # Esternón
        "Esternón - Bazo",
        "Esternón - Suprarrenal",
        "Esternón - Suprarrenales",
        "Esternón - Timo",
        # Esófago
        "Esófago - Pulmón",
        "Esófago - Subclavia",
        "Esófago - Esófago",
        "Esófago - Colon Descendente",
        # Mediastino
        "Mediastino - Mediastino",
        "Mediastino Superior - Mediastino Inferior",
        "Mediastino Superior - Hipotálamo",
        "Mediastino - Cerebelo",
        "Mediastino - Pericardio",
        "Mediastino - Suprarrenales",
        # Pecho
        "Pecho - Pecho",
        "Pectoral Mayor - Pectoral Mayor",
        "Pectoral Mayor - Pulmón Contralateral",
        # Pericardio (PDF2 LG #122-124)
        "Pericardio - Mastoides",
        "Pericardio - Pericardio",
        "Pericardio - Temporal Derecho",
        # Peritoneo - Pleura
        "Peritoneo - Pleura Derecha",
        # Pleura (PDF2 LG #156-161)
        "Pleura - Pleura",
        "Pleura - Hígado",
        "Pleura Derecha - Apéndice",
        "Pleura Derecha - Pulmón Derecho",
        "Pleura - Peritoneo",
        "Pleura Derecha - Peritoneo",
        # Plexo axilar
        "Plexo Axilar - Supraespinoso",
        # Plexo cervical
        "Plexo Cervical - Plexo Cervical",
        "Plexo Cervical - Bulbo Raquídeo",
        # Pulmón (PDF2 LG #194-197)
        "Pulmón - Pulmón",
        "Pulmón - Riñón Izquierdo",
        "Pulmón Derecho - Corazón",
        "Pulmón Derecho - Bulbo Raquídeo",
        "Pulmón Izquierdo - Corazón",
        # Apéndice - Pleura (PDF1 #25)
        "Apéndice - Pleura",
        # Timo (PDF2 LG #286-298)
        "Timo - Axila",
        "Timo - Timo",
        "Timo - Suprarrenales",
        "Timo - Apéndice",
        "Timo - Cardias",
        "Timo - Bazo",
        "Timo - Hígado",
        "Timo - Parietal",
        # Vena Porta (PDF1 #1035-1039, PDF2 LG #342-344)
        "Vena Porta - Colon Transverso",
        "Vena Porta - Hígado",
        "Vena Porta - Tendón Pectoral",
        "Vena Porta - Páncreas",
        "Vena Porta - Vena Porta",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # TRONCO › ABDOMEN  (riñón, hígado, bazo, páncreas, colon, vejiga sup…)
    # ══════════════════════════════════════════════════════════════════════════
    "Tronco:Abdomen": [
        # Agujero = zona xifoides/cardias (PDF1 #7)
        "Agujero - Agujero",
        # Ano (tronco)
        "Ano - Colon Ascendente",
        "Ano - Piloro",
        "Ano - Lengua",
        # Apéndice (abdomen)
        "Apéndice - Contraciego",
        "Apéndice - Apéndice Xifoides",
        "Apéndice - Peritoneo",
        "Apéndice - Lengua Izquierda",
        # Bazo (PDF1 #69-75, PDF2 LG #15-17)
        "Bazo - Bazo",
        "Bazo - Riñón",
        "Bazo - Vejiga",
        "Bazo - Duodeno",
        "Bazo - Suprarrenales",
        "Bazo - Punta de Páncreas",
        "Bazo - Páncreas",
        "Bazo - Hígado",
        "Bazo Horizontal - Bazo Horizontal",
        "Bazo Vertical - Bazo Vertical",
        # Borde costal
        "Borde Costal - Hígado",
        # Bulbo raquídeo – intestinal
        "Bulbo Raquídeo - Colon Descendente",
        # Cabeza de Páncreas (PDF2 LG #111)
        "Cabeza de Páncreas - Punta de Páncreas",
        "Cabeza de Páncreas - Estómago",
        "Cabeza de Páncreas - Hígado",
        "Cabeza de Páncreas - Suprarrenales",
        "Cabeza de Páncreas - Píloro",
        "Cabeza de Páncreas - Pleura",
        # Cáliz renal (PDF2 LG #21)
        "Cáliz Renal - Uretero",
        # Cápsula renal (PDF2 LG #23)
        "Cápsula Renal - Riñón",
        "Cápsula Renal - Cápsula Renal",
        "Cápsula Renal Derecha - Riñón Derecho",
        "Cápsula Renal Derecha - Riñón Izquierdo",
        "Cápsula Renal Derecha - Vejiga",
        "Cápsula Renal Derecha - Vesícula",
        # Ciego
        "Ciego - Ciego",
        "Ciego - Hígado",
        "Ciego - Riñón",
        "Ciego - Riñón Derecho",
        # Cola de páncreas (PDF2 LG #34-35)
        "Cola de Páncreas - Hígado",
        "Cola de Páncreas - Colon Descendente",
        "Cola de Páncreas - Riñón Ipsilateral",
        "Cola de Páncreas - Riñón Izquierdo",
        "Cola de Páncreas - Punta de Páncreas",
        # Colon (PDF2 LG #36-40)
        "Colon Ascendente - Colon Ascendente",
        "Colon Ascendente - Colon Descendente",
        "Colon Ascendente - Riñón Derecho",
        "Colon Ascendente - Colon Transverso",
        "Colon Descendente - Vejiga",
        "Colon Descendente - Riñón Izquierdo",
        "Colon Descendente - Recto",
        "Colon Descendente - Hígado",
        "Colon Sigmoides - Colon Sigmoides",
        "Colon Sigmoides - Recto",
        "Colon Transverso - Vejiga",
        "Colon Transverso - Hígado",
        "Colon Transverso - Colon Transverso",
        # Conducto central hepático
        "Conducto Central Hepático - Mucosa del Colon Descendente",
        # Contraciego
        "Contraciego - Contraciego",
        # Diafragma
        "Diafragma - Diafragma",
        # Duodeno (PDF2 LG #60)
        "Duodeno - Duodeno",
        "Duodeno - Hígado",
        "Duodeno - Laringe",
        "Duodeno - Esófago",
        "Duodeno - Riñón Izquierdo",
        "Duodeno - Riñón Derecho",
        "Duodeno - Bazo",
        "Duodeno - Vaso",
        # Epiplón
        "Epiplón - Epiplón",
        # Esófago (abdomen bajo)
        "Esófago - Píloro",
        # Estómago (PDF2 LG #66)
        "Estómago - Colon Transverso",
        "Estómago - Estómago",
        "Estómago - Corazón",
        "Estómago - Hígado",
        "Estómago - Bazo",
        "Estómago - Duodeno",
        "Estómago - Piloro",
        "Estómago - Suprarrenales",
        "Estómago - Subclavia Derecha",
        "Estómago - Cola de Páncreas",
        "Estómago - Vejiga",
        # Hígado (PDF2 LG #71-72)
        "Hígado - Hígado",
        "Hígado - Páncreas",
        "Hígado - Riñón Izquierdo",
        "Hígado - Suprarrenales",
        "Hígado - Corazón",
        "Hígado - Cola de Páncreas",
        "Hígado - Piloro",
        "Hígado - Riñón Derecho",
        "Hígado Lóbulo Posterior - Riñón Derecho",
        "Hígado Lóbulo Posterior - Riñón Izquierdo",
        "Lóbulo Hepático Izquierdo - Riñón Izquierdo",
        # Hipocampo
        "Hipocampo - Hipocampo",
        # Intestino
        "Intestino Delgado - Intestino Delgado",
        "Intestino Delgado - Intestino Grueso",
        "Intestino Grueso - Intestino Grueso",
        # Ligamento hepático
        "Ligamento Hepático - Costohepático",
        "Ligamento Hepático - Riñón Derecho",
        "Ligamento Pancreático - Bazo",
        "Ligamento Pancreático - Colon Descendente",
        # Línea arcuata
        "Línea Arcuata - Vena Mesentérica",
        # Micelio intestinal
        "Micelio Intestinal - Micelio Intestinal",
        # Ombligo
        "Ombligo - Ombligo",
        "Ombligo Derecho - Izquierdo",
        # Páncreas (PDF2 LG #106-111)
        "Páncreas - Estómago",
        "Páncreas - Páncreas",
        "Páncreas - Duodeno",
        "Páncreas - Bazo",
        "Páncreas - Hígado",
        "Páncreas - Suprarrenales",
        # Perihepático
        "Perihepático - Perihepático",
        "Retrohepático - Retrohepático",
        "Retrohepático - Riñón Derecho",
        # Peripancreático
        "Peripancreático - Peripancreático",
        # Peritoneo
        "Peritoneo - Peritoneo",
        "Peritoneo - Apéndice",
        "Peritoneo - Peroné",
        # Piloro (PDF2 LG #131-140)
        "Piloro - Estómago",
        "Piloro - Ano",
        "Piloro - Piloro",
        "Piloro - Riñones",
        "Piloro - Colon Ascendente",
        "Piloro - Hígado",
        "Piloro - Ureteros",
        "Piloro - Lengua Contralateral",
        "Piloro - Colon Transverso",
        "Piloro - Cardias",
        "Piloro - Glúteo",
        "Piloro - Riñón Izquierdo",
        # Punta de páncreas
        "Punta de Páncreas - Riñón Izquierdo",
        "Punta de Páncreas - Bazo",
        # Riñón (PDF2 LG #215-227)
        "Riñón - Riñón",
        "Riñón - Escápula",
        "Riñón - Deltoides",
        "Riñón - Sacro Contralateral",
        "Riñón - Riñón Inferior",
        "Riñón Derecho - Hígado",
        "Riñón Derecho - Duodeno",
        "Riñón Izquierdo - Mastoides",
        "Riñón Izquierdo - Ojo",
        "Riñón Izquierdo - Tiroides",
        "Riñón Izquierdo - Conducto del Páncreas",
        "Riñón Izquierdo - Útero",
        "Riñones - Interiliaco",
        "Cápsula Renal - Riñón Mismo Lado",
        # Sigmoide
        "Sigmoides - Recto",
        # Subdiafragma
        "Subdiafragma - Subdiafragma",
        "Subdiafragma - Riñón Lateral",
        # Suprarrenal / Suprarrenales
        "Suprarrenal - Páncreas",
        "Suprarrenal - Hígado",
        "Suprarrenal - Pulmón Bilateral",
        "Suprarrenal - Frente del Cuerpo",
        "Suprarrenal - Suprarrenales",
        "Suprarrenal - Recto",
        # Suprahepático
        "Suprahepático - Suprahepático",
        # Uretero (PDF1 #990-996)
        "Uretero - Recto",
        "Uretero - Vejiga",
        "Uretero - Cáliz Renal",
        "Uretero - Riñón Ipsilateral",
        "Uretero - Riñón Mismo Lado",
        "Uretero - Uretero",
        # Válvula ileocecal (PDF1 #1019-1022, PDF2 LG #337)
        "Válvula Ileocecal - Válvula Ileocecal",
        "Válvula Ileocecal - Estómago",
        "Válvula Ileocecal - Riñón Derecho",
        "Válvula Ileocecal - Prominencia Occipital",
        # Vesícula (PDF1 #1043-1049, PDF2 LG #345-346)
        "Vesícula - Vesícula",
        "Vesícula - Riñón Derecho",
        "Vesícula - Riñón",
        "Vesícula - Cápsula Renal",
        "Vesícula - Escápula",
        "Vesícula - Paratiroides",
        "Vesícula - Uretra",
        # Xifoides (PDF1 #1050, PDF2 LG #347)
        "Xifoides - Xifoides",
        # Yeyuno (PDF1 #1051-1052, PDF2 LG #348-349)
        "Yeyuno - Yeyuno",
        "Yeyuno - Riñón",
        # Zona suprarrenal (PDF1 #1056)
        "Zona Suprarrenal - Riñón Opuesto",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # TRONCO › ESPALDA  (dorsales, escápula, supraespinoso, retrohepático)
    # ══════════════════════════════════════════════════════════════════════════
    "Tronco:Espalda": [
        # Supraespinoso
        "Supraespinoso - Supraespinoso",
        "Supraespinoso - Cerebelo",
        # Espina escápula
        "Espina de la Escápula - Espina de la Escápula",
        # Retro axilar
        "Retro Axilar - Retro Axilar",
        # Retrotensor
        "Retrotensor de la Fascia Lata - Rectoral",
        # Dorsales
        "Dorsal 10ª - Dorsal 11ª",
        "Dorsal - Lumbar",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # PELVIS › DELANTERA  (vejiga, útero, próstata, ilíaco, pubis…)
    # ══════════════════════════════════════════════════════════════════════════
    "Pelvis:Delantera": [
        # Bulbo raquídeo - vejiga
        "Bulbo Raquídeo - Vejiga",
        # Cadera (PDF2 LG #19)
        "Cadera - Cadera",
        # Articulación - nervio inguinal (PDF1 #59)
        "Articulación - Nervio Inguinal",
        # Cervical 3ª (PDF2 LG #29)
        "Cervical 3ª - Sacro Contrario",
        "Cervical 3ª - Supraespinoso",
        # Ciático
        "Ciático - Ciático",
        # Coxis
        "Coxis - Ciático",
        "Coxis - Plexo Cervical",
        "Coxis Derecho - Coxis Izquierdo",
        # Esfínter
        "Esfínter Uretral - Esfínter Uretral",
        "Esfínter de la Uretra - Esfínter de la Uretra",
        # Gen - Ombligo
        "Gen - Vejiga",
        "Gen-Ombligo - Órgano",
        # Glándula palatina
        "Glándula Palatina - Riñón Lateral",
        # Hoyuelo del glúteo
        "Hoyuelo del Glúteo - Lumbar 2",
        # Iliaco
        "Iliaco - Iliaco",
        "Iliaco - Cápsula Renal Izquierda",
        # Infraaxilar
        "Infraaxilar - Infraaxilar",
        # Ingle / isquion
        "Ingle - Ingle",
        "Isquion - Isquion",
        # Nervio femoral
        "Nervio Femoral - Nervio Femoral",
        # Nervio inguinal
        "Nervio Inguinal - Nervio Inguinal",
        "Nervio Inguinal - Articulaciones",
        "Nervio Inguinal - Hígado",
        "Nervio Inguinal Derecho - Hígado",
        # Nervio vago
        "Nervio Vago - Riñón Contralateral",
        "Nervio Vago - Suprarrenal",
        "Nervio Vago - Nervio Vago",
        # Plexo
        "Plexo Cervical - Entre Clavícula y Cuello",
        "Plexo Cervical - Sacro",
        "Plexo Cervical - Útero",
        "Plexo Dorsal - Plexo Dorsal",
        "Plexo Lumbar - Plexo Lumbar",
        "Plexo Rodilla - Plexo Rodilla",
        # Primera cervical
        "Primera Cervical - Primera Cervical",
        "Primera Cervical - Útero",
        # Suprapúbico
        "Suprapúbico - Suprapúbico",
        # Vejiga (PDF1 #1023-1034)
        "Vejiga - Hipófisis",
        "Vejiga - Bulbo",
        "Vejiga - Vejiga",
        "Vejiga - Ano",
        "Vejiga - Timo",
        "Vejiga - Riñón",
        "Vejiga - Cadera",
        "Vejiga - Colon Transverso",
        "Vejiga - Vagina",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # PELVIS › TRASERA  (sacro, coxis, glúteo, coxis)
    # ══════════════════════════════════════════════════════════════════════════
    "Pelvis:Trasera": [
        # Articulación sacroilíaca (PDF1 #57)
        "Articulación Sacro-Ilíaca - Articulación Sacro-Ilíaca",
        # Coccígeo
        "Coccígeo - Coccígeo",
        # Glúteo
        "Glúteo - Glúteo",
        "Glúteo - Vena Femoral",
        "Glúteo Izquierdo - Tendón Aquiles Derecho",
        "Glúteo Izquierdo - Hiato",
        "Glúteo Izquierdo - Aquiles",
        "Glúteo Medio - Glúteo Medio",
        "Glúteo Medio - Vena Femoral",
        "Glúteo Menor Derecho - Sacro",
        # Hoyuelo del glúteo
        "Hoyuelo del Glúteo Derecho - Lumbar 2",
        "Hoyuelo del Glúteo Izquierdo - Lumbar 2",
        # Sacro (PDF2 LG #231-238)
        "Sacro - Coxis",
        "Sacro - Sacro",
        "Sacro - Riñón Contralateral",
        "Sacro - Ciático",
        "Sacro - Cervical",
        "Sacro - Útero",
        "Sacro - Vejiga",
        "Sacro - Femoral",
        # Semimembranoso
        "Semimembranoso - Semimembranoso",
        # Utero - Sacro (también aquí)
        "Útero - Sacro",
        # Vejiga - Sacro
        "Vejiga - Sacro",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # PELVIS › SEXO  (vagina, testículo, ovario, trompa, uretra, ano, recto…)
    # ══════════════════════════════════════════════════════════════════════════
    "Pelvis:Sexo": [
        # Anexo (PDF1 #9-11)
        "Anexo - Anexo",
        "Anexo - Ano",
        "Anexo - Riñón del Mismo Lado",
        # Ano (PDF1 #16-21)
        "Ano - Ano",
        "Ano - Lengua",
        "Ano - Testículo",
        "Ano - Próstata",
        "Ano - Testículo Izquierdo",
        # Apéndice (sexo)
        "Apéndice - Testículo Derecho",
        "Apéndice - Vagina",
        "Apéndice - Uretra",
        "Apéndice - Testículo Bilateral",
        "Apéndice - Ovario Derecho",
        # Clítoris
        "Clítoris - Timo",
        "Clítoris - Ano",
        "Clítoris - Uretra",
        "Clítoris - Sacro",
        # Ovario (PDF2 LG #101-104)
        "Ovario - Ovario",
        "Ovario - Suprarrenales",
        "Ovario - Riñón",
        "Ovario - Útero",
        # Pene
        "Pene - Pene",
        "Timo - Pene",
        # Próstata (PDF2 LG #190-191)
        "Próstata - Próstata",
        "Próstata - Recto",
        # Pudendo
        "Pudendo - Pudendo",
        # Recto (PDF2 LG #207-210)
        "Recto - Ano",
        "Recto - Timo",
        "Recto - Recto",
        "Timo - Recto",
        "Timo - Testículos",
        "Timo - Ovarios",
        # Saco de Douglas
        "Saco de Douglas - Vena Femoral",
        # Testículo (PDF1 #1057... but captured, PDF2 LG #279-282)
        "Testículo - Próstata",
        "Testículo - Recto",
        "Testículo - Angina",
        "Testículo - Testículo",
        # Trompa (PDF1 #985, PDF2 LG #311-312)
        "Trompa de Falopio - Trompa de Falopio",
        "Trompa - Ovario del Mismo Lado",
        "Uréter - Trompa",
        # Uréter (PDF1 #988-989)
        "Uréter - Trompa",
        "Uréter Izquierdo - Recto",
        "Uretero - Trompa de Falopio",
        # Uretra (PDF1 #997-1001, PDF2 LG #321-323)
        "Uretra - Pelvis",
        "Uretra - Uretero",
        "Uretra - Vagina",
        "Uretra - Clítoris",
        "Uretra - Uretra",
        "Uretra - Sacro",
        "Uretra - Ureteros",
        # Útero (PDF1 #1003-1009, PDF2 LG #324-329)
        "Útero - Útero",
        "Útero - Atlas",
        "Útero - Riñón",
        "Útero - Recto",
        "Útero - Ovario",
        "Útero - Hígado",
        # Vagina (PDF1 #1010-1016, PDF2 LG #331-336)
        "Vagina - Ovario",
        "Vagina - Útero",
        "Vagina - Recto",
        "Vagina - Vagina",
        "Vagina - Garganta",
        "Vagina - Riñón Izquierdo",
        "Vagina - Riñón Derecho",
        # Vesícula - Uretra
        "Vesícula - Uretra",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # MIEMBROS › BRAZO  (hombro, deltoides, codo, muñeca, mano)
    # ══════════════════════════════════════════════════════════════════════════
    "Miembros:Brazo": [
        # Acromion / Acromium (PDF1 #1, PDF2 LG #1)
        "Acromion - Acromion",
        "Acromium - Acromium",
        # Brazo
        "Braquial - Braquial",
        "Braquial Derecho - Braquial Izquierdo",
        "Bursa - Bursa",
        "Bursa - Codo",
        # Deltoides
        "Deltoides - Riñón Lateral",
        "Deltoides - Deltoides",
        "Deltoides Derecho - Deltoides Izquierdo",
        # Escápula (brazo)
        "Escápula MI - Centro del Omóplato",
        "Omóplato - Omóplato",
        # Mano
        "Palma Mano - Palma Mano",
        "Dedo Pulgar - Dedo Pulgar",
        "Dedo Anular - Dedo Anular",
        "Dedo Meñique - Dedo Meñique",
        "Dedo Medio - Dedo Medio",
        "Dedo Gordo - Dedo Gordo",
        "Índice - Índice",
        # Húmero
        "Húmero - Húmero",
        # Latísimus
        "Latísimus - Latísimus",
        # Muñeca
        "Muñeca - Muñeca",
        "Muñeca Derecha - Rodilla Externa",
        # Pectoral
        "Pectoral Mayor - Pectoral Mayor",
        "Pectoral Izquierdo - Tendón Cuádriceps Izquierdo",
        # Radio
        "Radio - Radio",
        # Ulna / Cúbito
        "Ulna - Ulna",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # MIEMBROS › PIERNA  (cadera, fémur, rodilla, pierna, pie, aquiles, talón)
    # ══════════════════════════════════════════════════════════════════════════
    "Miembros:Pierna": [
        # Apéndice (pierna)
        "Apéndice - Nervio Femoral",
        "Apéndice - Gracilis Superior",
        "Apéndice - Cabeza de Fémur Derecha",
        # Aquiles (PDF1 #44-50)
        "Aquiles Superior - Aquiles Superior",
        "Aquiles - Aquiles",
        "Aquiles Derecho - Aquiles Derecho",
        "Aquiles - Triceps Derecho",
        "Aquiles Derecho - Punta Escápula Izquierda",
        "Aquiles Inferior - Aquiles Inferior",
        "Aquiles Medio - Aquiles Medio",
        # Arco del pie (PDF1 #53)
        "Arco del Pie - Arco del Pie",
        # Calcáneo
        "Calcáneo - Calcáneo",
        # Canal medular
        "Canal Medular - Canal Medular",
        # Cuello de fémur
        "Cuello de Fémur - Cuello de Fémur",
        "Cuello de Fémur Derecho - Calcáneo Izquierdo",
        # Fémur
        "Fémur - Fémur",
        "Fémur Posterior - Fémur Posterior",
        # Metatarso
        "Metatarso - Metatarso",
        # Músculo Psoasilíaco
        "Músculo Psoasilíaco - Músculo Psoasilíaco",
        # Peroné
        "Peroné - Peroné",
        # Planta del pie
        "Planta del Pie - Planta del Pie",
        # Poplíteo
        "Poplíteo - Región Inguinal",
        "Poplíteo - Poplíteo",
        # Rodilla / Rótula
        "Rodilla - Rodilla",
        "Rótula - Rótula",
        # Sartorio
        "Tensor Fascia Lata - Sartorio",
        "Tensor Fascia Lata - Tensor Fascia Lata",
        "Tensor Fascia Lata - Cuádriceps",
        "Tensor Fascia Lata - Espina Ilíaca Posterior",
        "Tensor Fascia Lata - Gracilis Superior",
        # Talón / Tarso
        "Talón - Talón",
        "Tarso - Tarso",
        # Tibia
        "Tibia - Tibia",
        "Tibia Inferior - Tibia Inferior",
        "Tibia Media - Tibia Media",
        # Tobillo
        "Tobillo - Tobillo",
        # Trocánter
        "Trocánter Mayor - Trocánter Mayor",
        "Trocánter Menor - Trocánter Menor",
        "Trocánter Mayor - Riñón Lateral",
        "Trocánter Mayor - Tensor Fascia Lata",
        "Trocánter Mayor - Trocánter Menor",
        # Triángulo de Scarpa
        "Triángulo de Scarpa - Triángulo de Scarpa",
        # Úlcera varicosa
        "Úlcera Varicosa - Úlcera Varicosa",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # EXTRAS › VARIABLES  (pares especiales, funcionales, afin, área dolor)
    # ══════════════════════════════════════════════════════════════════════════
    "Extras:Variables": [
        # Aductor (PDF1 #4-5)
        "Aductor - Aductor",
        # Afin (PDF1 #6)
        "Afin - Afin",
        # Área de dolor
        "Área de Dolor - Riñón Mismo Lado",
        # Articulación general
        "Articulación - Riñón Derecho",
        "Articulación - Riñón Izquierdo",
        # Nervio vago (general)
        "Nervio Vago - Cardias",
        # Pulso radial
        "Pulso Radial - Bazo",
        # V-8
        "V-8 - V-8",
        # Vago
        "Vago - Riñón",
        "Vago - Riñón Contralateral",
        # Epíclavia
        "Espíclavia - Espíclavia",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # EXTRAS › COLUMNA VERTEBRAL  (atlas, cervical, lumbar, sacro, vertebras)
    # ══════════════════════════════════════════════════════════════════════════
    "Extras:Columna Vertebral": [
        # Atlas (PDF1 #61-64)
        "Atlas - Atlas",
        "Atlas - Útero",
        "Atlas - Píloro",
        "Atlas - Testículo",
        # Cervicales
        "Cervical 1ª - Piloro",
        "Cervical 1ª - Coxis",
        # Lumbar
        "Lumbar 4ª - Lumbar 4ª",
        "4ª Lumbar Derecha - Izquierda",
        "Lumbar 2 - Lumbar 2",
        # Vértebra lumbar
        "Vértebra Lumbar - Riñón Izquierdo",
        # Sacro - columna
        "Cervicales - Sacro",
        "Cervical - Sacro Contralateral",
        # Dorsal / Lumbar
        "Dorsal - Lumbar",
        "Dorsales - Lumbares",
    ],
}


# ─── Normalización ───────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[\s\-/]+", " ", s)
    s = s.strip()
    return s


def _all_existing_pairs(db: dict) -> set[str]:
    pairs = set()
    for reg in db["regiones"]:
        for zona in reg["zonas"]:
            for bloque in zona["bloques"]:
                for par in bloque["pares"]:
                    pairs.add(_normalize(par))
    return pairs


# ─── Consolidación ───────────────────────────────────────────────────────────

def consolidate():
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)

    existing = _all_existing_pairs(db)
    added = 0
    skipped_dup = 0
    skipped_zone = 0

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
        new_b = {
            "id": f"{zona_obj['id']}.{len(zona_obj['bloques']) + 1}",
            "nombre": bloque_nombre,
            "pares": []
        }
        zona_obj["bloques"].append(new_b)
        return new_b

    for dest_key, pairs_list in NEW_PDF_PAIRS.items():
        region_nombre, zona_nombre = dest_key.split(":")

        if region_nombre not in region_idx:
            print(f"  ⚠ Región no encontrada: {region_nombre}")
            skipped_zone += len(pairs_list)
            continue

        region_zones = region_idx[region_nombre]
        if zona_nombre not in region_zones:
            print(f"  ⚠ Zona no encontrada: {region_nombre} > {zona_nombre}")
            skipped_zone += len(pairs_list)
            continue

        zona_obj = region_zones[zona_nombre]
        bloque = get_or_create_bloque(zona_obj, "PDFs Externos")

        for par in pairs_list:
            norm = _normalize(par)
            if norm in existing:
                skipped_dup += 1
                continue
            if norm in {_normalize(p) for p in bloque["pares"]}:
                skipped_dup += 1
                continue
            bloque["pares"].append(par)
            existing.add(norm)
            added += 1

    # Limpiar bloques vacíos
    for reg in db["regiones"]:
        for zona in reg["zonas"]:
            zona["bloques"] = [
                b for b in zona["bloques"]
                if not (b["nombre"] == "PDFs Externos" and len(b["pares"]) == 0)
            ]

    # Recalcular total
    total = sum(
        len(b["pares"])
        for reg in db["regiones"]
        for zona in reg["zonas"]
        for b in zona["bloques"]
    )

    db["version"] = "4.0"
    db["total"] = total
    db["fuentes"] = [
        "Tablas Holoacademia - Alejandro Lavín (fuente primaria)",
        "Atlas Consolidado de Pares Biomagnéticos - Gerardo Donovarros",
        "Biomagnetismo Cuántico - Catálogo alfabético ~1056 pares (BIOMAGNETISMO-CUANTICO.pdf)",
        "Biomagnetismo - Lista General + enfermedades ~350 pares (BIOMAGNETISMO.pdf)",
        "Manual de Biomagnetismo 2021 Mod.2 (Manual-Biomagnetismo-2021.pdf)",
    ]
    db["consolidacion"] = {
        "pares_holoacademia_base": 371,
        "pares_compilado_externo_v3": 303,
        "pares_pdfs_nuevos_v4": added,
        "duplicados_eliminados": skipped_dup,
        "zonas_no_encontradas": skipped_zone,
        "total_v4": total,
    }

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Consolidación v4.0 completada:")
    print(f"   Pares v3.0 base           : 675")
    print(f"   Pares nuevos de PDFs      : {added}")
    print(f"   Duplicados saltados       : {skipped_dup}")
    if skipped_zone:
        print(f"   ⚠ Zonas no encontradas   : {skipped_zone}")
    print(f"   ─────────────────────────────────")
    print(f"   TOTAL v4.0                : {total}")


if __name__ == "__main__":
    consolidate()
