#!/usr/bin/env python3
"""Genera pares_biomagnéticos_v4_lite.pdf — SIN imágenes, solo tablas con texto.
Columnas: # | ✓ | IMÁN NEGRO (N+) | IMÁN ROJO (S−) | TIPO IMÁN | TIPO | PATÓGENO | ENF
"""
import json, os, sys
from collections import defaultdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Importar matriz de análisis para detectar bipolar vs 2 imanes
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "scripts", "ficha_generator"))
from pair_analysis import analyze_pair

DB_PATH  = os.path.join(_HERE, "data", "biomagnetic_pairs_db.json")
CLAS_PATH = os.path.join(_HERE, "data", "pares_clasificacion.json")
MAPPING_PATH = os.path.join(_HERE, "data", "fichas_mapping.json")
OUT_PATH = os.path.join(_HERE, "pares_biomagnéticos_v4_lite.pdf")

# 9 UI Regions con sus zonas DB
UI_REGIONS = [
    ("Cabeza",  [("Cabeza",   "Coronilla"),
                 ("Cabeza",   "Posterior"),
                 ("Cabeza",   "Lateral"),
                 ("Cabeza",   "Frente"),
                 ("Cabeza",   "Rostro")]),
    ("Cuello",  [("Cabeza",   "Cuello")]),
    ("Pecho",   [("Tronco",   "Tórax")]),
    ("Abdomen", [("Tronco",   "Abdomen"),
                 ("Tronco",   "Hepatitis")]),
    ("Espalda", [("Tronco",   "Espalda"),
                 ("Extras",   "Columna Vertebral")]),
    ("Pelvis",  [("Pelvis",   "Delantera"),
                 ("Pelvis",   "Trasera"),
                 ("Pelvis",   "Sexo")]),
    ("Brazos",  [("Miembros", "Brazo")]),
    ("Piernas", [("Miembros", "Pierna")]),
    ("Extras",  [("Extras",   "Variables"),
                 ("Extras",   "Ejes Corporales")]),
]

TIPO_COLORS = {
    "Bacteria": "#c0392b", "Virus": "#8e44ad", "Hongo": "#27ae60",
    "Hongo en General": "#27ae60", "Parásito": "#e67e22",
    "Disfunción": "#3498db", "Especial/Disfunción": "#3498db",
    "Emocional/Psicoemocional": "#d35400", "Reservorio": "#7f8c8d",
    "Complejo": "#34495e", "Sin clasificar": "#aaaaaa",
    "Tóxico": "#16a085", "Universal": "#2c3e50",
}

def load_data():
    with open(DB_PATH) as f:
        db = json.load(f)
    classifications = {}
    if os.path.exists(CLAS_PATH):
        with open(CLAS_PATH) as f:
            data = json.load(f)
        for c in data.get("clasificaciones", []):
            classifications[(c["region"], c["zona"], c["bloque"], c["par"])] = c
    ficha_pares = set()
    if os.path.exists(MAPPING_PATH):
        with open(MAPPING_PATH) as f:
            data = json.load(f)
        for m in data.get("mappings", []):
            ficha_pares.add((m["db_region"], m["db_zona"], m["db_bloque"], m["db_par"]))
    return db, classifications, ficha_pares

def get_zona_bloques(db, region_nombre, zona_nombre):
    for r in db["regiones"]:
        if r["nombre"] == region_nombre:
            for z in r["zonas"]:
                if z["nombre"] == zona_nombre:
                    return [(b["nombre"], b.get("pares", [])) for b in z.get("bloques", [])]
    return []

def build_pdf():
    db, classifications, ficha_pares = load_data()
    total = db.get("total", "—")
    version = db.get("version", "v4.3")

    doc = SimpleDocTemplate(
        OUT_PATH, pagesize=landscape(A4),
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    styles = getSampleStyleSheet()

    s_title = ParagraphStyle("DocTitle", parent=styles["Normal"],
        fontSize=22, leading=38, spaceAfter=2, textColor=colors.white,
        backColor=colors.HexColor("#1a3a5c"),
        borderPadding=(8, 14, 8, 14), alignment=TA_CENTER,
        fontName="Helvetica-Bold")
    s_subtitle = ParagraphStyle("Subtitle", parent=styles["Normal"],
        fontSize=10.5, leading=18, textColor=colors.white,
        backColor=colors.HexColor("#34495e"),
        borderPadding=(4, 14, 4, 14), alignment=TA_CENTER, spaceAfter=14)
    s_meta = ParagraphStyle("Meta", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#2e7d32"),
        borderColor=colors.HexColor("#2e7d32"), borderWidth=1,
        borderPadding=6, backColor=colors.HexColor("#f1f8f1"), spaceAfter=10)
    s_region = ParagraphStyle("RegionHeading", parent=styles["Heading1"],
        fontSize=16, textColor=colors.white,
        backColor=colors.HexColor("#1a3a5c"),
        borderPadding=8, spaceBefore=16, spaceAfter=10)
    s_zona = ParagraphStyle("ZonaHeading", parent=styles["Heading2"],
        fontSize=12, textColor=colors.HexColor("#1a3a5c"),
        spaceBefore=12, spaceAfter=4)
    s_bloque = ParagraphStyle("BloqueHeading", parent=styles["Normal"],
        fontSize=9.5, textColor=colors.HexColor("#555555"),
        spaceBefore=8, spaceAfter=4, fontName="Helvetica-BoldOblique")
    s_th = ParagraphStyle("TH", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold", textColor=colors.white,
        alignment=TA_CENTER)
    s_cell = ParagraphStyle("Cell", parent=styles["Normal"],
        fontSize=8.5, leading=11)
    s_cell_par = ParagraphStyle("CellPar", parent=styles["Normal"],
        fontSize=9, leading=11, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a3a5c"))
    s_cell_small = ParagraphStyle("CellSmall", parent=styles["Normal"],
        fontSize=7.5, leading=9, textColor=colors.HexColor("#444"))

    story = []

    # ── Portada ──────────────────────────────────────────────────
    story.append(Paragraph("Pares Biomagnéticos por Región", s_title))
    story.append(Paragraph(
        f"Base de datos {version} — Lista de trabajo (sin imágenes)", s_subtitle))

    # Tabla resumen
    rows = [[Paragraph("Región UI", s_th), Paragraph("Zonas DB", s_th),
             Paragraph("Pares", s_th), Paragraph("Con ficha", s_th),
             Paragraph("Pendientes", s_th)]]
    grand_total = 0
    grand_fichas = 0
    for ui_reg, sources in UI_REGIONS:
        ui_total = 0
        ui_con_ficha = 0
        for (db_r, db_z) in sources:
            for bn, pares in get_zona_bloques(db, db_r, db_z):
                for p in pares:
                    ui_total += 1
                    if (db_r, db_z, bn, p) in ficha_pares:
                        ui_con_ficha += 1
        ui_pendientes = ui_total - ui_con_ficha
        grand_total += ui_total
        grand_fichas += ui_con_ficha
        zonas_label = ", ".join(z for _, z in sources)
        rows.append([
            Paragraph(f"<b>{ui_reg}</b>", styles["Normal"]),
            Paragraph(zonas_label, styles["Normal"]),
            Paragraph(str(ui_total), styles["Normal"]),
            Paragraph(f'<font color="#2e7d32">{ui_con_ficha}</font>', styles["Normal"]),
            Paragraph(f'<font color="#c0392b">{ui_pendientes}</font>', styles["Normal"]),
        ])
    rows.append([
        Paragraph("<b>TOTAL</b>", styles["Normal"]),
        Paragraph("", styles["Normal"]),
        Paragraph(f"<b>{grand_total}</b>", styles["Normal"]),
        Paragraph(f'<b><font color="#2e7d32">{grand_fichas}</font></b>', styles["Normal"]),
        Paragraph(f'<b><font color="#c0392b">{grand_total - grand_fichas}</font></b>', styles["Normal"]),
    ])
    tbl = Table(rows, colWidths=[3*cm, 10*cm, 2.5*cm, 3*cm, 3*cm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),  (-1,0),  colors.HexColor("#1a3a5c")),
        ("ROWBACKGROUNDS",(0,1),  (-1,-2), [colors.HexColor("#f0f4f8"), colors.white]),
        ("BACKGROUND",    (0,-1), (-1,-1), colors.HexColor("#d4e6f1")),
        ("GRID",          (0,0),  (-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN",        (0,0),  (-1,-1), "MIDDLE"),
        ("ALIGN",         (2,0),  (-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0),  (-1,-1), 5),
        ("BOTTOMPADDING", (0,0),  (-1,-1), 5),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.5*cm))

    # Meta info
    story.append(Paragraph(
        f"<b>Total: {grand_total} pares</b> · "
        f"✅ {grand_fichas} con ficha aprobada · "
        f"⏳ {grand_total - grand_fichas} pendientes de generar<br/>"
        f"<b>Polaridad:</b> 1er punto del par = <b>Imán NEGRO</b> = Polaridad <b>Negativa (−)</b> · "
        f"2do punto del par = <b>Imán ROJO</b> = Polaridad <b>Positiva (+)</b> · "
        f"Mismo punto central repetido = <b>Imán BIPOLAR</b> (1 imán doble polaridad)",
        s_meta
    ))

    # ── Secciones por región ──────────────────────────────────────
    for ui_reg, sources in UI_REGIONS:
        story.append(PageBreak())
        # contador región
        rc = 0
        for (db_r, db_z) in sources:
            for bn, pares in get_zona_bloques(db, db_r, db_z):
                rc += len(pares)
        story.append(Paragraph(f"  {ui_reg}   ({rc} pares)", s_region))

        # Por zona
        for (db_r, db_z) in sources:
            bloques = get_zona_bloques(db, db_r, db_z)
            zc = sum(len(p) for _, p in bloques)
            if zc == 0: continue
            story.append(Paragraph(f"Zona: {db_z}  ({zc} pares)", s_zona))

            # Por bloque
            for bloque_nombre, pares in bloques:
                story.append(Paragraph(
                    f"[ {bloque_nombre} — {len(pares)} pares ]", s_bloque
                ))

                # Tabla con header de 2 niveles
                # Fila 0: # | ✓ | PAR BIOMAGNÉTICO (span 2) | TIPO IMÁN | TIPO | PATÓGENO | ENF
                # Fila 1: # | ✓ | IMÁN NEGRO (N+) | IMÁN ROJO (S−) | TIPO IMÁN | TIPO | PATÓGENO | ENF
                # Estilos específicos para sub-headers (blanco fuerte)
                s_th_sub = ParagraphStyle("THSub", parent=styles["Normal"],
                    fontSize=11, fontName="Helvetica-Bold",
                    textColor=colors.white,
                    alignment=TA_CENTER, leading=14)
                s_th_sub_polaridad = ParagraphStyle("THSubPol", parent=styles["Normal"],
                    fontSize=9, fontName="Helvetica-Bold",
                    textColor=colors.white,
                    alignment=TA_CENTER, leading=12)

                header_row_1 = [
                    Paragraph("#", s_th),
                    Paragraph("✓", s_th),
                    Paragraph("PAR BIOMAGNÉTICO", s_th),
                    "",  # span con la anterior
                    Paragraph("TIPO<br/>IMÁN", s_th),
                    Paragraph("TIPO", s_th),
                    Paragraph("PATÓGENO", s_th),
                    Paragraph("ENFERMEDADES · SÍNTOMAS · TRANSMISIÓN", s_th),
                ]
                # Header row 2: sub-columnas con IMÁN NEGRO / IMÁN ROJO en BLANCO grande
                header_row_2 = [
                    "",  # span
                    "",  # span
                    Paragraph(
                        '<font color="#FFFFFF"><b>IMÁN NEGRO</b></font><br/>'
                        '<font color="#FFFFFF" size="8">Polaridad Negativa (−)</font>',
                        s_th_sub),
                    Paragraph(
                        '<font color="#FFFFFF"><b>IMÁN ROJO</b></font><br/>'
                        '<font color="#FFFFFF" size="8">Polaridad Positiva (+)</font>',
                        s_th_sub),
                    "", "", "", "",  # spans
                ]
                rows = [header_row_1, header_row_2]
                row_colors = []
                pair_num = 1

                for par in pares:
                    key = (db_r, db_z, bloque_nombre, par)
                    clf = classifications.get(key, {})
                    tipo = clf.get("tipo")
                    pat = clf.get("patogeno_canonico") or clf.get("patogeno")
                    enf = clf.get("enfermedades_reales")
                    desc = clf.get("descripcion")
                    trans = clf.get("transmision")
                    fuentes_n = clf.get("fuentes_count", 0)
                    has_ficha = key in ficha_pares
                    tipo_color = TIPO_COLORS.get(tipo, "#888888") if tipo else "#dddddd"

                    # Análisis del par: ¿bipolar o 2 imanes?
                    matrix = analyze_pair(par, db_r, db_z, bloque_nombre,
                                          tipo=tipo, patogeno=pat,
                                          enfermedades=enf, descripcion=desc)
                    pa = matrix["iman_negro_punto"]
                    pb = matrix["iman_rojo_punto"]
                    lado_n = matrix["iman_negro_lado"]   # "DER" o None
                    lado_r = matrix["iman_rojo_lado"]    # "IZQ" o None
                    es_bipolar = matrix["es_bipolar"]
                    tipo_iman_corto = matrix["tipo_iman_corto"]

                    def _trunc(s, n):
                        if not s: return ""
                        return s if len(s) <= n else s[:n-1] + '…'

                    # Celda IMÁN NEGRO
                    if es_bipolar:
                        cell_negro = Paragraph(
                            f'<font color="#27ae60"><b>● {pa}</b></font><br/>'
                            f'<font size="6" color="#888">imán bipolar (+/−)</font>',
                            s_cell)
                    else:
                        lado_str = f' <font color="#1a3a5c" size="7"><i>{lado_n}</i></font>' if lado_n else ''
                        cell_negro = Paragraph(
                            f'<font color="#1a1a1a"><b>● {pa}</b></font>{lado_str}<br/>'
                            f'<font size="6" color="#888">Negativo (−)</font>',
                            s_cell)

                    # Celda IMÁN ROJO
                    if es_bipolar:
                        cell_rojo = Paragraph(
                            f'<font color="#27ae60"><b>← mismo imán</b></font><br/>'
                            f'<font size="6" color="#888">no aplica (bipolar)</font>',
                            s_cell)
                    else:
                        lado_str = f' <font color="#c0392b" size="7"><i>{lado_r}</i></font>' if lado_r else ''
                        cell_rojo = Paragraph(
                            f'<font color="#c0392b"><b>● {pb}</b></font>{lado_str}<br/>'
                            f'<font size="6" color="#888">Positivo (+)</font>',
                            s_cell)

                    # Celda TIPO IMÁN
                    if es_bipolar:
                        cell_tipo_iman = Paragraph(
                            '<font color="#27ae60"><b>BIPOLAR</b></font><br/>'
                            '<font size="6" color="#888">1 imán</font>', s_cell)
                    else:
                        cell_tipo_iman = Paragraph(
                            '<font color="#34495e"><b>2 imanes</b></font>'
                            + ('<br/><font size="6" color="#888">bilateral</font>' if lado_n else ''),
                            s_cell)

                    info_parts = []
                    if enf:   info_parts.append(f'<b>Enf:</b> {_trunc(enf, 230)}')
                    if desc and desc != enf:
                        info_parts.append(f'<b>Sínt:</b> {_trunc(desc, 180)}')
                    if trans: info_parts.append(f'<b>Trans:</b> {_trunc(trans, 100)}')
                    if fuentes_n:
                        info_parts.append(f'<font color="#999" size="6"><i>{fuentes_n} fuentes</i></font>')
                    info_html = '<br/>'.join(info_parts) if info_parts else '<font color="#ccc">—</font>'

                    rows.append([
                        Paragraph(f"<b>{pair_num}</b>", s_cell),
                        Paragraph('<font color="#27ae60"><b>✓</b></font>' if has_ficha
                                  else '<font color="#aaa">⏳</font>', s_cell),
                        cell_negro,
                        cell_rojo,
                        cell_tipo_iman,
                        Paragraph(
                            f'<font color="{tipo_color}"><b>{tipo}</b></font>' if tipo
                            else '<font color="#bbb"><i>—</i></font>', s_cell),
                        Paragraph(pat if pat else '<font color="#bbb">—</font>', s_cell),
                        Paragraph(info_html, s_cell_small),
                    ])
                    row_colors.append(tipo_color)
                    pair_num += 1

                # Anchos: # ✓ NEGRO ROJO TIPO_IMAN TIPO PATÓG ENF
                t = Table(rows,
                          colWidths=[0.6*cm, 0.6*cm, 3.5*cm, 3.5*cm, 1.7*cm, 2.0*cm, 3.5*cm, 10.0*cm],
                          repeatRows=2)
                style_cmds = [
                    # Header row 1 background (azul oscuro)
                    ("BACKGROUND",     (0,0),  (-1,0),  colors.HexColor("#1a3a5c")),
                    ("TEXTCOLOR",      (0,0),  (-1,0),  colors.white),
                    # Header row 2 IMÁN NEGRO bg negro (alto contraste)
                    ("BACKGROUND",     (2,1),  (2,1),  colors.HexColor("#1a1a1a")),
                    # Header row 2 IMÁN ROJO bg rojo (alto contraste)
                    ("BACKGROUND",     (3,1),  (3,1),  colors.HexColor("#c0392b")),
                    ("TEXTCOLOR",      (2,1),  (3,1),  colors.white),
                    # SPANs del header de dos niveles
                    ("SPAN", (0,0), (0,1)),   # # → vertical span
                    ("SPAN", (1,0), (1,1)),   # ✓ → vertical span
                    ("SPAN", (2,0), (3,0)),   # PAR BIOMAGNÉTICO → horizontal span
                    ("SPAN", (4,0), (4,1)),   # TIPO IMÁN
                    ("SPAN", (5,0), (5,1)),   # TIPO
                    ("SPAN", (6,0), (6,1)),   # PATÓGENO
                    ("SPAN", (7,0), (7,1)),   # ENF
                    # Backgrounds spanned cells (#, ✓, etc.) en azul oscuro
                    ("BACKGROUND",     (0,0),  (1,1),  colors.HexColor("#1a3a5c")),
                    ("BACKGROUND",     (4,0),  (7,1),  colors.HexColor("#1a3a5c")),
                    ("TEXTCOLOR",      (4,0),  (7,1),  colors.white),
                    # Separador entre headers
                    ("LINEBELOW", (2,0), (3,0), 1, colors.HexColor("#fff")),
                    # General
                    ("VALIGN",         (0,0),  (-1,-1), "MIDDLE"),
                    ("ALIGN",          (0,0),  (1,-1),  "CENTER"),
                    ("ALIGN",          (4,0),  (4,-1),  "CENTER"),
                    ("GRID",           (0,0),  (-1,-1), 0.25, colors.HexColor("#ccc")),
                    ("TOPPADDING",     (0,0),  (-1,-1), 3),
                    ("BOTTOMPADDING",  (0,0),  (-1,-1), 3),
                    ("LEFTPADDING",    (0,0),  (-1,-1), 4),
                    ("RIGHTPADDING",   (0,0),  (-1,-1), 4),
                    ("ROWBACKGROUNDS", (0,2),  (-1,-1), [colors.white, colors.HexColor("#f5f7fa")]),
                ]
                # Color stripe per row (starts at row 2 because of 2-row header)
                for i, tc in enumerate(row_colors, start=2):
                    style_cmds.append(("LINEBEFORE", (0,i), (0,i), 3, colors.HexColor(tc)))
                t.setStyle(TableStyle(style_cmds))
                story.append(t)
                story.append(Spacer(1, 0.25*cm))

    # Final
    story.append(PageBreak())
    story.append(Spacer(1, 4*cm))
    story.append(Paragraph(
        f"Base de datos {version} · {grand_total} pares · Holoacademia / Symbelia",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=10,
                       alignment=TA_CENTER, textColor=colors.HexColor("#888"))
    ))

    doc.build(story)
    print(f"✅ PDF generado: {OUT_PATH}")
    print(f"   Total: {grand_total} pares · {grand_fichas} con ficha · {grand_total - grand_fichas} pendientes")
    return grand_total

if __name__ == "__main__":
    build_pdf()
