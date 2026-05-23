"""Matriz de análisis maestra Symbelia - decisión visual por par.

Determina automáticamente:
- ¿Misma vista funciona o requiere diagonal?
- ¿Es bilateral, doble, o mismo punto repetido?
- ¿Es zona sensible (requiere licra/top negro)?
- ¿Qué vista anatómica usar?
- ¿Qué documento es la fuente principal?
- TIPO DE IMÁN: bipolar (1 imán) vs doble (2 imanes negro+rojo)
"""
from __future__ import annotations
import re
import unicodedata

# ============================================================
# PUNTOS ANATÓMICOS CENTRALES (sin lateralidad natural)
# Cuando A == B y A está aquí → BIPOLAR (1 imán de doble polaridad)
# Cuando A == B y A NO está aquí → 2 IMANES (negro DER + rojo IZQ)
# ============================================================
CENTRAL_POINTS = {
    # Cabeza - estructuras centrales del cráneo
    "pineal", "prepineal", "postpineal", "post pineal",
    "polo", "antepolo", "prepolo",
    "antecuerno",
    "nucleos basales", "núcleos basales",
    "cuerpo calloso",
    "cisura media", "cisura lambda",
    "cisura silvio", "cisura de silvio",
    "cisura temporooccipital",
    "talamo", "tálamo",
    "hipotalamo", "hipótalamo",
    "hipofisis", "hipófisis", "adenohipofisis", "adenohipófisis",
    "bulbo", "bulbo raquideo", "bulbo raquídeo",
    "puente de varolo", "puente de variolo",
    "cerebelo",
    "tallo cerebral", "tallo parietal",
    "cerebro",
    "tercer ventriculo", "tercer ventrículo",
    "cuarto ventriculo", "cuarto ventrículo",
    "hipocampo",
    "amigdala cerebral", "amígdala cerebral",
    "lunar",
    "quiasma",
    "poligono de willis", "polígono de willis",
    "corona", "corona hipofisis", "corona hipófisis",
    # Cuello centrales
    "atlas", "axis",
    "laringe", "traquea", "tráquea",
    "tiroides", "paratiroides",
    "hueco de garganta",
    "nuca",
    # Tronco centrales
    "esternon", "esternón",
    "mango", "mango del esternon", "mango del esternón",
    "ombligo",
    "esofago", "esófago",
    "estomago", "estómago",
    "duodeno",
    "diafragma",
    "mediastino", "mediastino superior", "mediastino inferior",
    "corazon", "corazón",
    "carina",
    "timo",
    "epiplon", "epiplón",
    "cardias",
    "piloro", "píloro",
    "agujero diafragmatico", "agujero diafragmático",
    "hiato esofagico", "hiato esofágico",
    "vena porta", "vena cava", "cava",
    "coronaria", "coronarias",
    "seno auriculo", "seno auriculo-ventricular", "seno auriculoventricular",
    # Abdomen centrales
    "intestino delgado", "intestino grueso", "intestinos",
    "colon transverso",
    "uretero", "urétero",
    "epiplon", "epiplón",
    "linea arcuata", "línea arcuata",
    "musculo recto anterior", "músculo recto anterior",
    "ligamento hepatico", "ligamento hepático",
    "ligamento pancreatico", "ligamento pancreático",
    "punta de pancreas", "punta de páncreas",
    "cabeza de pancreas", "cabeza de páncreas",
    "cola de pancreas", "cola de páncreas",
    "cuerpo de pancreas", "cuerpo de páncreas",
    "conducto de pancreas", "conducto de páncreas",
    "conducto de vesicula", "conducto de vesícula",
    "supraumbilical",
    "perihepatico", "perihepático",
    "peripancreatico", "peripancreático",
    "supracuerpo", "suprapiloro", "suprapíloro",
    "infracarina", "infratimo",
    "ganglios mesentericos", "gánglios mesentéricos", "mesenterio",
    "colon descendente",  # mayormente izquierdo pero linear
    "colon ascendente",   # mayormente derecho pero linear
    "sigmoides",
    "valvula ileocecal", "válvula ileocecal",
    # Pelvis centrales
    "pubis", "suprapubico", "suprapúbico",
    "vejiga", "vejiga media",
    "uretra",
    "vagina", "utero", "útero",
    "clitoris", "clítoris",
    "prostata", "próstata",
    "pene",
    "ano", "recto",
    "interuretral", "inter-uretral",
    "interiliaco", "interilíaco",
    "pudendo",
    "perineo", "perineo",
    "saco de douglas",
    # Trasera centrales
    "sacro", "coxis",
    "rama isquiatica", "rama isquiática",
    "isquion", "isquión",
    # Vertebras y costillas centrales
    "cervical 1", "cervical 2", "cervical 3", "cervical 4",
    "cervical 5", "cervical 6", "cervical 7",
    "dorsal 1", "dorsal 2", "dorsal 3", "dorsal 4", "dorsal 5",
    "dorsal 6", "dorsal 7", "dorsal 8", "dorsal 9", "dorsal 10",
    "dorsal 11", "dorsal 12",
    "lumbar 1", "lumbar 2", "lumbar 3", "lumbar 4", "lumbar 5",
    "sacro 1", "sacro 2", "sacro 3", "sacro 4",
    "coxis 1", "coxis 2", "coxis 3",
    "costilla 1", "costilla 2", "costilla 3", "costilla 4", "costilla 5",
    "costilla 6", "costilla 7", "1ra costilla", "1ª costilla", "7ª costilla",
    "1a costilla", "7a costilla",
    # Centro de la espalda
    "borde calloso",  # cuando se nombra sin lado es central
    # Rostro centrales
    "nariz", "boca", "lengua",
    "labio", "labio superior", "labio inferior",
    "comisura",
    "menton", "mentón", "inframentón", "inframenton",
    "mandibula", "mandíbula",
    "submaxilar",
    "seno frontal", "seno nasal", "retronasal",
    "punta de nariz",
    "dental ras", "dental",
}

def _strip_central(s: str) -> str:
    """Normaliza un punto para checar contra CENTRAL_POINTS."""
    s = unicodedata.normalize("NFKC", s).strip().lower()
    s = re.sub(r'\s+', ' ', s)
    # Strip lateral suffixes
    s = re.sub(r'\s*\(?(der|izq|derech[oa]|izquierd[oa]|ras|contralateral|contralat|homolat|homo lat|homolateral|ipsilateral|mismo lado|del mismo lado)\)?\s*$', '', s, flags=re.IGNORECASE).strip()
    return s

def is_central_point(point: str) -> bool:
    """¿El punto es anatómicamente central (sin lateralidad natural)?"""
    p = _strip_central(point)
    # Strip parens like "(RAS)"
    p = re.sub(r'\s*\([^)]*\)\s*', '', p).strip()
    return p in CENTRAL_POINTS

# ============================================================
# Zonas sensibles (requieren licra/top negro, sin desnudez)
# ============================================================
SENSITIVE_TERMS = {
    "vagina", "clitoris", "clítoris", "pubis", "pubico", "púbico", "uretra",
    "recto", "ano", "anal", "testiculo", "testículo", "ovario", "trompa",
    "utero", "útero", "vulva", "perine", "perineo", "perineum",
    "macho", "femina", "fémina", "sexo", "pelvis", "ingle", "inguinal",
    "femoral", "sacro", "coxis", "gluteo", "glúteo",
    "cuerpo cavernoso", "prostata", "próstata",
}

# Body parts that need ropa interior cubriendo
PELVIC_REGIONS = {"Pelvis", "pelvis"}

# ============================================================
# Region/Zona → vista anatómica a renderizar
# ============================================================
REGION_TO_VIEW = {
    ("Cabeza", "Coronilla"):   "vista superior del cráneo (top-down) mostrando el techo de la cabeza",
    ("Cabeza", "Posterior"):   "vista posterior del cráneo (nuca) desde atrás",
    ("Cabeza", "Lateral"):     "vista lateral del cráneo en perfil derecho",
    ("Cabeza", "Frente"):      "vista frontal de la cara enfocada en frente y entrecejo",
    ("Cabeza", "Rostro"):      "vista frontal del rostro completo",
    ("Cabeza", "Cuello"):      "vista frontal del cuello y garganta",
    ("Tronco", "Tórax"):       "vista frontal del torso masculino (sin camisa) mostrando tórax",
    ("Tronco", "Hepatitis"):   "vista frontal del abdomen superior enfocado en zona hepática",
    ("Tronco", "Abdomen"):     "vista frontal del abdomen mostrando órganos viscerales superpuestos",
    ("Tronco", "Espalda"):     "vista posterior de la espalda masculina sin camisa",
    ("Pelvis", "Delantera"):   "vista médica anatómica de cadera y muslo superior, sujeto con pantalón corto deportivo oscuro",
    ("Pelvis", "Trasera"):     "vista médica posterior de la región lumbar baja y cadera, con pantalón corto oscuro",
    ("Pelvis", "Sexo"):        "vista médica anatómica de la región inferior del abdomen, con pantalón corto oscuro cubriendo",
    ("Miembros", "Brazo"):     "vista frontal de los brazos extendidos a los lados",
    ("Miembros", "Pierna"):    "vista frontal de las piernas con muslos, rodillas, pantorrillas y pies",
    ("Extras", "Variables"):           "vista frontal completa del cuerpo (cuerpo entero) con ropa interior",
    ("Extras", "Columna Vertebral"):  "vista posterior de la columna vertebral con vértebras numeradas (C1-C7, D1-D12, L1-L5, S1, Cx1)",
    ("Extras", "Ejes Corporales"):    "vista frontal completa del cuerpo con líneas de ejes anatómicos marcadas",
}

def _strip_accent(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def _norm(s: str) -> str:
    return _strip_accent(s).lower().strip()

# ============================================================
# Parsing del nombre del par
# ============================================================
def split_pair(par_name: str) -> tuple[str, str]:
    """Divide 'X - Y' en (X, Y). Si es 'X - X', devuelve (X, X)."""
    sep_re = r'\s*[-–—]\s*'
    parts = [p.strip() for p in re.split(sep_re, par_name) if p.strip()]
    if not parts:
        return (par_name, par_name)
    if len(parts) == 1:
        return (parts[0], parts[0])
    return (parts[0], parts[1])

def is_same_point(punto_a: str, punto_b: str) -> bool:
    """¿Los dos puntos son anatómicamente el mismo?"""
    a, b = _norm(punto_a), _norm(punto_b)
    if a == b:
        return True
    # Quitar laterality y comparar
    a_no_lat = re.sub(r'\b(der|izq|derech[oa]|izquierd[oa]|ras)\b', '', a).strip()
    b_no_lat = re.sub(r'\b(der|izq|derech[oa]|izquierd[oa]|ras)\b', '', b).strip()
    return a_no_lat == b_no_lat and a_no_lat != ''

def has_explicit_laterality(punto: str) -> str | None:
    """Returns 'DER', 'IZQ', or None."""
    p = _norm(punto)
    if re.search(r'\b(der|derech[oa])\b', p): return 'DER'
    if re.search(r'\b(izq|izquierd[oa])\b', p): return 'IZQ'
    return None

# ============================================================
# Detección de tipo de par (bilateral, doble, normal)
# ============================================================
def determine_pair_type(par_name: str, tipo: str | None = None,
                        bloque: str | None = None) -> dict:
    """Devuelve análisis del par + TIPO DE IMÁN.

    Variantes:
    - bipolar:            1 imán de doble polaridad (punto central repetido)
    - bilateral_2_imanes: 2 imanes en lados opuestos (negro DER + rojo IZQ)
    - normal_2_imanes:    2 imanes en puntos distintos
    """
    a, b = split_pair(par_name)
    same = is_same_point(a, b)
    lat_a = has_explicit_laterality(a)
    lat_b = has_explicit_laterality(b)

    # CASO 1: mismo punto + lateralidad explícita opuesta → 2 imanes bilaterales
    if same and lat_a and lat_b and lat_a != lat_b:
        return {
            "variante":        "bilateral_2_imanes",
            "tipo_iman":       "2 imanes",
            "tipo_iman_corto": "2 imanes",
            "iman_negro_lado": "DER",
            "iman_rojo_lado":  "IZQ",
            "desc": "Bilateral con lateralidad explícita: 2 imanes. "
                    "NEGRO en lado derecho, ROJO en lado izquierdo.",
        }

    # CASO 2: mismo punto SIN lateralidad explícita
    if same:
        if is_central_point(a):
            # Punto central (Pineal, Bulbo, Esternón…) → 1 imán BIPOLAR
            return {
                "variante":        "bipolar",
                "tipo_iman":       "1 imán bipolar",
                "tipo_iman_corto": "Bipolar",
                "iman_negro_lado": None,
                "iman_rojo_lado":  None,
                "desc": "Punto central sin lateralidad: 1 imán de DOBLE POLARIDAD (bipolar).",
            }
        else:
            # Punto con lados naturales (Riñón, Oreja, etc.) → 2 imanes
            return {
                "variante":        "bilateral_2_imanes",
                "tipo_iman":       "2 imanes",
                "tipo_iman_corto": "2 imanes",
                "iman_negro_lado": "DER",
                "iman_rojo_lado":  "IZQ",
                "desc": "Punto bilateral natural: 2 imanes. NEGRO derecho, ROJO izquierdo.",
            }

    # CASO 3: par doble (clasificación especial)
    if tipo and "doble" in tipo.lower():
        return {
            "variante":        "bipolar",
            "tipo_iman":       "1 imán bipolar",
            "tipo_iman_corto": "Bipolar",
            "iman_negro_lado": None,
            "iman_rojo_lado":  None,
            "desc": "Par doble: 1 imán bipolar dividido.",
        }

    # CASO 4: puntos distintos → 2 imanes normal
    return {
        "variante":        "normal_2_imanes",
        "tipo_iman":       "2 imanes",
        "tipo_iman_corto": "2 imanes",
        "iman_negro_lado": None,
        "iman_rojo_lado":  None,
        "desc": "Par estándar: 2 imanes. NEGRO en primer punto, ROJO en segundo punto.",
    }

# ============================================================
# Zona sensible
# ============================================================
def is_sensitive(region: str, zona: str, par_name: str) -> bool:
    """¿La ficha requiere licra/top negro?"""
    if region in PELVIC_REGIONS:
        return True
    par_n = _norm(par_name)
    for term in SENSITIVE_TERMS:
        if term in par_n:
            return True
    if _norm(zona) in {"sexo", "delantera", "trasera"}:
        return True
    return False

# ============================================================
# ¿Requiere división diagonal del panel anatómico?
# ============================================================
def requires_diagonal(par_name: str, region: str, zona: str) -> bool:
    """¿Los dos puntos del par están en regiones tan distantes que requieren diagonal split?"""
    a, b = split_pair(par_name)

    # Mapeo punto → región anatómica gruesa
    REGION_KEYWORDS = {
        "cabeza":  {"pineal","corona","frontal","occipital","cerebelo","bulbo","temporal",
                    "parietal","callosidad","hipofisis","hipotalamo","amigdala","oreja",
                    "oido","mastoides","sien","quiasma","mandibular","parotida","ojo",
                    "nariz","boca","comisura","labio","mejilla","craneo","cuello",
                    "garganta","laringe","tiroides","atlas","cervical"},
        "torax":   {"timo","esternon","mango","subclavia","epiclavia","mediastino",
                    "carina","corazon","coronaria","pulmon","pleura","pectoral","axila",
                    "costilla","traquea","esofago","diafragma","cardias","hiato"},
        "abdomen": {"estomago","piloro","higado","vesicula","bazo","pancreas","epiplon",
                    "duodeno","colon","ciego","apendice","intestino","yeyuno","sigmoides",
                    "uretero","ombligo","ileocecal","mesenterio","perihepatico"},
        "espalda": {"dorsal","lumbar","escapula","homoplato","supraespinoso","retrohepatico",
                    "rinon","suprarrenal","caliz","cuadrado","staquibraquis"},
        "pelvis":  {"pubis","cadera","femur","trocanter","cresta","iliaca","ilion",
                    "sacro","coxis","gluteo","trasero","interiliaco","interuretral",
                    "vejiga","utero","ovario","clitoris","uretra","vagina","trompa",
                    "testiculo","prostata","recto","ano","macho","femina","cuerpo cavernoso"},
        "brazo":   {"deltoides","bursa","humero","braquial","codo","radio","cubito",
                    "muneca","palma","dorso mano","indice","mano"},
        "pierna":  {"aductor","cuadriceps","tensor","rotula","tibia","perone","ciatico",
                    "aquiles","empeine","popliteo","gemelo","soleo","tobillo","talon",
                    "plantar","dedo gordo","calcaneo","fascia","arco"},
    }

    def classify(point: str) -> str | None:
        p = _norm(point)
        for region_name, keywords in REGION_KEYWORDS.items():
            for kw in keywords:
                if kw in p:
                    return region_name
        return None

    region_a = classify(a)
    region_b = classify(b)

    if region_a is None or region_b is None:
        return False  # not sure, default to single view
    if region_a == region_b:
        return False

    # Definir distancia anatómica (regiones adyacentes vs distantes)
    adjacent = {
        ("cabeza","torax"): False,  # adjacent (cuello)
        ("torax","abdomen"): True,  # frontal works
        ("abdomen","pelvis"): True, # frontal works
        ("torax","espalda"): False, # opposite sides → need diagonal
        ("abdomen","espalda"): False,
        ("pelvis","espalda"): True, # both can show in posterior
        ("pierna","brazo"): False,
        ("cabeza","abdomen"): False,
        ("cabeza","pelvis"): False,
        ("cabeza","pierna"): False,
        ("brazo","pierna"): False,
    }
    key = tuple(sorted([region_a, region_b]))
    can_same_view = adjacent.get(key, False)
    return not can_same_view  # if cannot show together → diagonal

# ============================================================
# Documento fuente recomendado
# ============================================================
def recommended_source(region: str, zona: str) -> dict:
    """Cuál es el documento principal y secundario para este par."""
    if region == "Cabeza":
        return {"principal": "Tablas Holoacademia (Lavín) - Sección Cabeza",
                "secundaria": "Manual Biomagnetismo Mod.2 - Cabeza/Cuello"}
    if region == "Tronco":
        return {"principal": "Manual Biomagnetismo - Tórax/Abdomen/Espalda",
                "secundaria": "Tablas Holoacademia - Tronco"}
    if region == "Pelvis":
        return {"principal": "Tablas Holoacademia - Pelvis",
                "secundaria": "Manual Biomagnetismo - Pelvis"}
    if region == "Miembros":
        return {"principal": "Tablas Holoacademia - Miembros",
                "secundaria": "Manual Biomagnetismo - Extremidades"}
    if region == "Extras":
        return {"principal": "Pares de Traumatismo Lavín / Variables",
                "secundaria": "Manual Biomagnetismo - Especiales"}
    return {"principal": "Atlas Symbelia", "secundaria": "Manual Biomagnetismo"}

# ============================================================
# Función maestra: analizar un par
# ============================================================
def analyze_pair(par_name: str, region: str, zona: str, bloque: str,
                 tipo: str = None, patogeno: str = None,
                 enfermedades: str = None, descripcion: str = None) -> dict:
    """Devuelve la matriz de análisis completa para el par."""
    a, b = split_pair(par_name)
    pair_type = determine_pair_type(par_name, tipo=tipo, bloque=bloque)
    sensitive = is_sensitive(region, zona, par_name)
    diagonal = requires_diagonal(par_name, region, zona)
    view = REGION_TO_VIEW.get((region, zona), f"vista anatómica de {region} > {zona}")
    sources = recommended_source(region, zona)

    # Cobertura corporal
    if sensitive:
        cobertura = "Licra negra ajustada + top negro si aplica · Sin desnudez · Estilo médico sobrio"
    elif region == "Tronco" or region == "Cabeza" or region == "Miembros":
        cobertura = "Torso sin camisa OK · No genitales visibles · Ropa interior en zona pélvica si aparece"
    else:
        cobertura = "Estilo médico sobrio · Cobertura anatómica conservadora"

    # Texto clínico para descripción
    texto_clinico_parts = []
    if patogeno:
        texto_clinico_parts.append(f"Asociado con {patogeno}.")
    if enfermedades:
        texto_clinico_parts.append(enfermedades[:180])
    elif descripcion:
        texto_clinico_parts.append(descripcion[:180])
    else:
        texto_clinico_parts.append(f"Par anatómico de la zona {zona}.")
    texto_clinico = " ".join(texto_clinico_parts)[:280]

    return {
        "nombre_par": par_name,
        "punto_a": a,
        "punto_b": b,
        # === Polaridad / Imanes ===
        "iman_negro_punto": a,                  # primer punto siempre va al negro
        "iman_rojo_punto": b,                   # segundo punto siempre va al rojo
        "iman_negro_polaridad": "Negativo",     # negro = Negativo (−)
        "iman_negro_signo": "−",
        "iman_rojo_polaridad": "Positivo",      # rojo = Positivo (+)
        "iman_rojo_signo": "+",
        "iman_negro_lado": pair_type.get("iman_negro_lado"),  # "DER" si bilateral
        "iman_rojo_lado": pair_type.get("iman_rojo_lado"),    # "IZQ" si bilateral
        "tipo_iman": pair_type.get("tipo_iman"),
        "tipo_iman_corto": pair_type.get("tipo_iman_corto"),
        "es_bipolar": pair_type["variante"] == "bipolar",
        "es_bilateral_2_imanes": pair_type["variante"] == "bilateral_2_imanes",
        "es_normal_2_imanes": pair_type["variante"] == "normal_2_imanes",
        # === Otros ===
        "polaridad": "Punto A (NEGRO, N+, Norte) + Punto B (ROJO, S−, Sur)",
        "region": region,
        "subregion": zona,
        "bloque": bloque,
        "tipo": tipo or "(determinar)",
        "patogeno": patogeno,
        "vista_anatomica": view,
        "variante_visual": pair_type["variante"],
        "variante_descripcion": pair_type["desc"],
        "misma_vista_funciona": not diagonal,
        "requiere_diagonal": diagonal,
        "es_zona_sensible": sensitive,
        "cobertura_anatomica": cobertura,
        "fuente_principal": sources["principal"],
        "fuente_secundaria": sources["secundaria"],
        "texto_clinico": texto_clinico,
    }
