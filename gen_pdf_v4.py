#!/usr/bin/env python3
"""
Generate pares_biomagnéticos_v4.pdf  — base de datos v4.3 (1404 pares)
"""
import json
from collections import defaultdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, Image
)
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_LEFT, TA_CENTER

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(_HERE, "data", "biomagnetic_pairs_db.json")
CLAS_PATH = os.path.join(_HERE, "data", "pares_clasificacion.json")
MAPS_DIR = os.path.join(_HERE, "data", "mapas_anatomicos")
OUT_PATH = os.path.join(_HERE, "pares_biomagnéticos_v4.pdf")

def get_zone_image(zona_nombre):
    """Return absolute path to the anatomical map for a zone, or None if not available."""
    candidate = os.path.join(MAPS_DIR, f"{zona_nombre}.png")
    if os.path.exists(candidate):
        return candidate
    return None

EXCLUDE_ZONA_NAMES = set()  # ninguna zona excluida en v4.1

def load_db():
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)

def load_classifications():
    """Load per-pair tipo/patogeno classifications from references."""
    if not os.path.exists(CLAS_PATH):
        return {}
    with open(CLAS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    # Index by (region, zona, bloque, par) for exact lookup
    lookup = {}
    for c in data.get("clasificaciones", []):
        key = (c["region"], c["zona"], c["bloque"], c["par"])
        lookup[key] = {
            "tipo": c.get("tipo"),
            "patogeno": c.get("patogeno"),
            "patogeno_canonico": c.get("patogeno_canonico"),
            "enfermedades_reales": c.get("enfermedades_reales"),
            "transmision": c.get("transmision"),
            "descripcion": c.get("descripcion"),
            "fuentes_count": c.get("fuentes_count", 0),
            "fuentes": c.get("fuentes", []),
        }
    return lookup

def load_pair_thumbnails():
    """Load per-pair thumbnail lookup."""
    path = os.path.join(_HERE, "data", "pair_thumbnails_map.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return data.get("thumbnails", {})

# Color map per tipo (for visual differentiation)
TIPO_COLORS = {
    "Bacteria":                "#c0392b",   # red
    "Virus":                   "#8e44ad",   # purple
    "Hongo":                   "#27ae60",   # green
    "Hongo en General":        "#27ae60",
    "Parásito":                "#e67e22",   # orange
    "Disfunción":              "#3498db",   # blue
    "Especial/Disfunción":     "#3498db",
    "Emocional/Psicoemocional":"#d35400",   # dark orange
    "Reservorio":              "#7f8c8d",   # gray
    "Complejo":                "#34495e",   # dark blue-gray
    "Sin clasificar":          "#aaaaaa",
    "Tóxico":                  "#16a085",
    "Universal":               "#2c3e50",
}

def get_zona_pairs(db, region_nombre, zona_nombre):
    for region in db["regiones"]:
        if region["nombre"] == region_nombre:
            for zona in region["zonas"]:
                if zona["nombre"] == zona_nombre:
                    return [(b["nombre"], b.get("pares", [])) for b in zona.get("bloques", [])]
    return []

# UI regions — zona names must match DB exactly
UI_REGIONS = {
    "Cabeza": [
        ("Cabeza", "Coronilla"),
        ("Cabeza", "Posterior"),
        ("Cabeza", "Lateral"),
        ("Cabeza", "Frente"),
        ("Cabeza", "Rostro"),
    ],
    "Cuello": [
        ("Cabeza", "Cuello"),
    ],
    "Pecho": [
        ("Tronco", "Tórax"),
    ],
    "Abdomen": [
        ("Tronco", "Abdomen"),
        ("Tronco", "Hepatitis"),
    ],
    "Espalda": [
        ("Tronco", "Espalda"),
        ("Extras", "Columna Vertebral"),
    ],
    "Pelvis": [
        ("Pelvis", "Delantera"),
        ("Pelvis", "Trasera"),
        ("Pelvis", "Sexo"),
    ],
    "Brazos": [
        ("Miembros", "Brazo"),
    ],
    "Piernas": [
        ("Miembros", "Pierna"),
    ],
    "Extras": [
        ("Extras", "Variables"),
        ("Extras", "Ejes Corporales"),
        # Columna Vertebral → incluida bajo Espalda
    ],
}

def build_region_data(db):
    region_data = {}
    for ui_region, sources in UI_REGIONS.items():
        zonas_data = []
        for (db_region, db_zona) in sources:
            bloques = get_zona_pairs(db, db_region, db_zona)
            if bloques:
                zonas_data.append((db_zona, bloques))
        region_data[ui_region] = zonas_data
    return region_data

def count_pairs(zonas_data):
    return sum(len(pares) for (_, bloques) in zonas_data for (_, pares) in bloques)

def build_pdf(db, region_data):
    classifications = load_classifications()
    pair_thumbs = load_pair_thumbnails()

    doc = SimpleDocTemplate(
        OUT_PATH,
        pagesize=landscape(A4),
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm,   bottomMargin=1.5*cm,
    )

    styles = getSampleStyleSheet()

    s_title = ParagraphStyle("DocTitle", parent=styles["Title"],
        fontSize=18, spaceAfter=4, textColor=colors.HexColor("#1a3a5c"))
    s_subtitle = ParagraphStyle("Subtitle", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#555555"), spaceAfter=14)
    s_meta = ParagraphStyle("Meta", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#2e7d32"),
        borderColor=colors.HexColor("#2e7d32"), borderWidth=1,
        borderPadding=6, backColor=colors.HexColor("#f1f8f1"), spaceAfter=10)
    s_region = ParagraphStyle("RegionHeading", parent=styles["Heading1"],
        fontSize=14, textColor=colors.white,
        backColor=colors.HexColor("#1a3a5c"),
        borderPadding=6, spaceBefore=16, spaceAfter=8)
    s_zona = ParagraphStyle("ZonaHeading", parent=styles["Heading2"],
        fontSize=11, textColor=colors.HexColor("#1a3a5c"),
        spaceBefore=10, spaceAfter=4)
    s_bloque = ParagraphStyle("BloqueHeading", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#555555"),
        spaceBefore=6, spaceAfter=2, fontName="Helvetica-BoldOblique")
    s_pair = ParagraphStyle("Pair", parent=styles["Normal"],
        fontSize=8.5, leftIndent=12, spaceAfter=1, leading=12)
    s_th = ParagraphStyle("TH", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold", textColor=colors.white)

    story = []

    # ── Portada ───────────────────────────────────────────────────────────────
    story.append(Paragraph("Pares Biomagnéticos por Región", s_title))
    story.append(Paragraph("Base de datos v4.3 — Revisión y validación", s_subtitle))

    consol = db.get("consolidacion", {})
    meta_lines = [
        f"<b>Total de pares v4.3:</b> {db.get('total', '—')}",
        f"Holoacademia base: {consol.get('pares_holoacademia_base','—')} &nbsp;|&nbsp; "
        f"Atlas Consolidado (v3): {consol.get('pares_compilado_externo_v3','—')} &nbsp;|&nbsp; "
        f"PDFs nuevos (v4): {consol.get('pares_pdfs_nuevos_v4','—')}",
        f"Duplicados eliminados: {consol.get('duplicados_eliminados','—')}",
        "Fuentes: Tablas Holoacademia · Atlas Donovarros · Biomagnetismo Cuántico · "
        "Biomagnetismo Lista General · Manual 2021",
        "Hepatitis incluida en Abdomen · Columna Vertebral incluida en Espalda",
    ]
    story.append(Paragraph("<br/>".join(meta_lines), s_meta))

    # ── Tabla resumen ─────────────────────────────────────────────────────────
    hdr = [Paragraph(t, s_th) for t in ["Región UI", "Zonas DB", "Pares"]]
    rows = [hdr]
    grand_total = 0
    for ui_region, sources in UI_REGIONS.items():
        zonas_data = region_data[ui_region]
        c = count_pairs(zonas_data)
        grand_total += c
        zona_names = ", ".join(z for (_, z) in sources)
        rows.append([
            Paragraph(ui_region, styles["Normal"]),
            Paragraph(zona_names, styles["Normal"]),
            Paragraph(str(c), styles["Normal"]),
        ])
    rows.append([
        Paragraph("<b>TOTAL</b>", styles["Normal"]),
        Paragraph("", styles["Normal"]),
        Paragraph(f"<b>{grand_total}</b>", styles["Normal"]),
    ])

    tbl = Table(rows, colWidths=[3.5*cm, 10*cm, 2*cm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),  (-1,0),  colors.HexColor("#1a3a5c")),
        ("ROWBACKGROUNDS",(0,1),  (-1,-2), [colors.HexColor("#f0f4f8"), colors.white]),
        ("BACKGROUND",    (0,-1), (-1,-1), colors.HexColor("#d4e6f1")),
        ("FONT",          (0,-1), (-1,-1), "Helvetica-Bold"),
        ("GRID",          (0,0),  (-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN",        (0,0),  (-1,-1), "MIDDLE"),
        ("ALIGN",         (2,0),  (2,-1),  "CENTER"),
        ("TOPPADDING",    (0,0),  (-1,-1), 4),
        ("BOTTOMPADDING", (0,0),  (-1,-1), 4),
        ("LEFTPADDING",   (0,0),  (-1,-1), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Leyenda de tipos / patógenos ──────────────────────────────────────────
    legend_items = []
    for tipo, color in TIPO_COLORS.items():
        legend_items.append(f'<font color="{color}"><b>{tipo}</b></font>')
    legend_html = (
        '<b>Leyenda de clasificación:</b> ' + ' · '.join(legend_items) +
        '<br/><br/>Junto a cada par se muestra el tipo y el patógeno o condición asociada '
        '(extraído de Atlas Consolidado, Tapia Márquez, Biomagnetismo Cuántico y Enciclopedia Lavín 2024).'
    )
    story.append(Paragraph(
        legend_html,
        ParagraphStyle("Legend", parent=styles["Normal"], fontSize=8,
                       leading=11, backColor=colors.HexColor("#f8f8f8"),
                       borderColor=colors.HexColor("#cccccc"), borderWidth=0.5,
                       borderPadding=6, spaceAfter=8)
    ))
    story.append(Spacer(1, 0.3*cm))

    # ── Duplicados entre regiones UI ──────────────────────────────────────────
    pair_to_regions = defaultdict(set)
    for ui_region, zonas_data in region_data.items():
        for (zona_nombre, bloques) in zonas_data:
            for (bloque_nombre, pares) in bloques:
                for par in pares:
                    pair_to_regions[par.strip()].add(ui_region)

    dupes = {p: sorted(rs) for p, rs in pair_to_regions.items() if len(rs) > 1}
    if dupes:
        story.append(Paragraph(
            f"<b>⚠ Duplicados entre regiones UI: {len(dupes)}</b>",
            ParagraphStyle("DupeTitle", parent=styles["Normal"],
                           textColor=colors.red, fontSize=10)
        ))
        for par, rlist in list(dupes.items())[:30]:
            story.append(Paragraph(
                f"  • {par} → {', '.join(rlist)}",
                ParagraphStyle("DP", parent=styles["Normal"], fontSize=8, leftIndent=12)
            ))
        if len(dupes) > 30:
            story.append(Paragraph(f"  … y {len(dupes)-30} más.", styles["Normal"]))
    else:
        story.append(Paragraph(
            "✓ Sin duplicados entre regiones UI.",
            ParagraphStyle("ND", parent=styles["Normal"],
                           textColor=colors.HexColor("#006600"), fontSize=10)
        ))

    # ── Estilos para tabla de pares ───────────────────────────────────────────
    s_table_header = ParagraphStyle("TableHeader", parent=styles["Normal"],
        fontSize=8.5, fontName="Helvetica-Bold", textColor=colors.white,
        alignment=TA_CENTER)
    s_table_cell = ParagraphStyle("TableCell", parent=styles["Normal"],
        fontSize=8, leading=10)
    s_table_cell_small = ParagraphStyle("TableCellSmall", parent=styles["Normal"],
        fontSize=7.5, leading=9, textColor=colors.HexColor("#444444"))
    s_table_par = ParagraphStyle("TablePar", parent=styles["Normal"],
        fontSize=8.5, leading=10, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a3a5c"))

    # ── Secciones por región ──────────────────────────────────────────────────
    for ui_region, zonas_data in region_data.items():
        story.append(PageBreak())
        rc = count_pairs(zonas_data)
        sources = UI_REGIONS[ui_region]
        zona_label = ", ".join(f"{dr} › {dz}" for (dr, dz) in sources)

        story.append(Paragraph(f"  {ui_region}   ({rc} pares)", s_region))
        story.append(Paragraph(
            f"Zonas DB: {zona_label}",
            ParagraphStyle("ZDB", parent=styles["Normal"], fontSize=9,
                           textColor=colors.HexColor("#555555"), spaceAfter=8)
        ))

        pair_num = 1
        for (zona_nombre, bloques) in zonas_data:
            zc = sum(len(p) for (_, p) in bloques)
            story.append(Paragraph(f"Zona: {zona_nombre}  ({zc} pares)", s_zona))

            # ── Mapa anatómico de la zona ──────────────────────────────────────
            img_path = get_zone_image(zona_nombre)
            if img_path:
                try:
                    # Determine image dimensions to fit max 8cm width, max 6cm height
                    from reportlab.lib.utils import ImageReader
                    ir = ImageReader(img_path)
                    iw, ih = ir.getSize()
                    max_w_cm = 9.0
                    max_h_cm = 5.5
                    aspect = ih / iw
                    if aspect <= max_h_cm / max_w_cm:
                        w_cm = max_w_cm
                        h_cm = max_w_cm * aspect
                    else:
                        h_cm = max_h_cm
                        w_cm = max_h_cm / aspect
                    img = Image(img_path, width=w_cm*cm, height=h_cm*cm)
                    # Wrap image in a small caption table
                    caption = Paragraph(
                        f'<font size="7" color="#888888">📍 Mapa anatómico — Zona {zona_nombre} '
                        f'(fuente: Mapas Anatómicos Originales — A. Lavín / Holoacademia)</font>',
                        styles["Normal"]
                    )
                    img_block = Table(
                        [[img], [caption]],
                        colWidths=[w_cm*cm],
                    )
                    img_block.setStyle(TableStyle([
                        ("ALIGN",   (0,0), (-1,-1), "CENTER"),
                        ("VALIGN",  (0,0), (-1,-1), "MIDDLE"),
                        ("BOX",     (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
                        ("TOPPADDING",   (0,0), (-1,-1), 4),
                        ("BOTTOMPADDING",(0,0), (-1,-1), 2),
                    ]))
                    story.append(img_block)
                    story.append(Spacer(1, 0.25*cm))
                except Exception as e:
                    print(f"⚠ No se pudo cargar imagen {img_path}: {e}")

            # Find the DB region for this zona
            db_region_for_zona = None
            for (dr, dz) in UI_REGIONS[ui_region]:
                if dz == zona_nombre:
                    db_region_for_zona = dr
                    break

            for (bloque_nombre, pares) in bloques:
                story.append(Paragraph(
                    f"[ {bloque_nombre} — {len(pares)} pares ]", s_bloque
                ))

                # Build table for this bloque (6 columns: # | UBICACIÓN | PAR | TIPO | PATÓGENO | INFO)
                header_row = [
                    Paragraph("#", s_table_header),
                    Paragraph("UBICACIÓN", s_table_header),
                    Paragraph("PAR BIOMAGNÉTICO", s_table_header),
                    Paragraph("TIPO", s_table_header),
                    Paragraph("PATÓGENO", s_table_header),
                    Paragraph("ENFERMEDADES · SÍNTOMAS · TRANSMISIÓN", s_table_header),
                ]
                rows = [header_row]
                row_colors_per_tipo = []
                row_heights = [0.8*cm]  # header row

                for par in pares:
                    clf = classifications.get((db_region_for_zona, zona_nombre, bloque_nombre, par)) or {}
                    tipo = clf.get("tipo") or ""
                    pat  = clf.get("patogeno_canonico") or clf.get("patogeno") or ""
                    enf  = clf.get("enfermedades_reales") or ""
                    desc = clf.get("descripcion") or ""
                    trans = clf.get("transmision") or ""
                    fuentes_n = clf.get("fuentes_count", 0)
                    tipo_color = TIPO_COLORS.get(tipo, "#888888") if tipo else "#dddddd"

                    # Image cell (UBICACIÓN) - smaller to fit per row
                    thumb_key = f"{db_region_for_zona}|{zona_nombre}|{bloque_nombre}|{par}"
                    thumb_path = pair_thumbs.get(thumb_key)
                    if thumb_path and os.path.exists(thumb_path):
                        try:
                            from reportlab.lib.utils import ImageReader
                            ir = ImageReader(thumb_path)
                            iw, ih = ir.getSize()
                            max_w = 2.6*cm
                            max_h = 1.6*cm
                            aspect = ih / iw
                            if aspect <= max_h / max_w:
                                w = max_w
                                h = max_w * aspect
                            else:
                                h = max_h
                                w = max_h / aspect
                            img_cell = Image(thumb_path, width=w, height=h)
                        except Exception:
                            img_cell = Paragraph('<font color="#cccccc">—</font>', s_table_cell)
                    else:
                        img_cell = Paragraph('<font color="#cccccc">—</font>', s_table_cell)

                    # Helper to truncate long text
                    def _trunc(s, maxlen):
                        if not s: return s
                        return s if len(s) <= maxlen else s[:maxlen-1] + '…'

                    # Build info column - limit total length to prevent layout errors
                    info_parts = []
                    if enf:
                        info_parts.append(f'<b>Enf:</b> {_trunc(enf, 220)}')
                    if desc and desc != enf:
                        info_parts.append(f'<b>Sínt:</b> {_trunc(desc, 200)}')
                    if trans:
                        info_parts.append(f'<b>Trans:</b> {_trunc(trans, 100)}')
                    if fuentes_n:
                        info_parts.append(f'<font color="#999999" size="6"><i>{fuentes_n} fuentes</i></font>')
                    info_html = '<br/>'.join(info_parts) if info_parts else '<font color="#cccccc">—</font>'

                    # Cell paragraphs
                    num_cell = Paragraph(f"<b>{pair_num}</b>", s_table_cell)
                    par_cell = Paragraph(par, s_table_par)
                    tipo_cell = Paragraph(
                        f'<font color="{tipo_color}"><b>{tipo}</b></font>' if tipo else
                        '<font color="#bbbbbb"><i>—</i></font>',
                        s_table_cell
                    )
                    pat_cell = Paragraph(pat if pat else '<font color="#bbbbbb">—</font>', s_table_cell)
                    info_cell = Paragraph(info_html, s_table_cell_small)

                    rows.append([num_cell, img_cell, par_cell, tipo_cell, pat_cell, info_cell])
                    row_colors_per_tipo.append(tipo_color)
                    row_heights.append(None)  # auto-size based on content
                    pair_num += 1

                # Column widths for 6 cols (landscape A4 ~25.7cm usable)
                tbl = Table(
                    rows,
                    colWidths=[0.7*cm, 3*cm, 4.5*cm, 2.2*cm, 3.5*cm, 11.8*cm],
                    repeatRows=1,
                )
                style_cmds = [
                    ("BACKGROUND",     (0,0),   (-1,0),    colors.HexColor("#1a3a5c")),
                    ("TEXTCOLOR",      (0,0),   (-1,0),    colors.white),
                    ("VALIGN",         (0,0),   (-1,-1),   "MIDDLE"),
                    ("ALIGN",          (1,0),   (1,-1),    "CENTER"),  # image column centered
                    ("ALIGN",          (0,0),   (0,-1),    "CENTER"),  # # column centered
                    ("GRID",           (0,0),   (-1,-1),   0.25, colors.HexColor("#cccccc")),
                    ("TOPPADDING",     (0,0),   (-1,-1),   3),
                    ("BOTTOMPADDING",  (0,0),   (-1,-1),   3),
                    ("LEFTPADDING",    (0,0),   (-1,-1),   3),
                    ("RIGHTPADDING",   (0,0),   (-1,-1),   3),
                    ("BACKGROUND",     (0,1),   (-1,-1),   colors.HexColor("#fafafa")),
                    ("ROWBACKGROUNDS", (0,1),   (-1,-1),   [colors.white, colors.HexColor("#f5f7fa")]),
                ]
                # Left-color stripe per row based on tipo
                for i, tc in enumerate(row_colors_per_tipo, start=1):
                    style_cmds.append(("LINEBEFORE", (0,i), (0,i), 3, colors.HexColor(tc)))
                tbl.setStyle(TableStyle(style_cmds))

                story.append(tbl)
                story.append(Spacer(1, 0.25*cm))

    # ── Sección Atlas Visual: Fichas Individuales por Par ───────────────────
    fichas_path = os.path.join(_HERE, "data", "fichas_mapping.json")
    if os.path.exists(fichas_path):
        with open(fichas_path) as f:
            fichas_data = json.load(f)
        mappings = fichas_data.get("mappings", [])
        # Sort by region (UI order) and ficha number
        UI_ORDER = ["Cabeza", "Cuello", "Pecho", "Abdomen", "Espalda", "Pelvis", "Brazos", "Piernas", "Extras"]
        def ui_region_for(reg_db, zona_db):
            for ui_reg, sources in UI_REGIONS.items():
                if (reg_db, zona_db) in sources:
                    return ui_reg
            return "Sin UI"
        mappings.sort(key=lambda m: (
            UI_ORDER.index(ui_region_for(m["db_region"], m["db_zona"])) if ui_region_for(m["db_region"], m["db_zona"]) in UI_ORDER else 99,
            m["db_region"], m["db_zona"], m["ficha_number"]
        ))

        # Cover page for atlas section
        story.append(PageBreak())
        story.append(Spacer(1, 4*cm))
        story.append(Paragraph(
            "ATLAS VISUAL",
            ParagraphStyle("AtlasTitle", parent=styles["Title"],
                           fontSize=32, alignment=TA_CENTER,
                           textColor=colors.HexColor("#1a3a5c"))
        ))
        story.append(Paragraph(
            "Fichas Individuales por Par Biomagnético",
            ParagraphStyle("AtlasSubtitle", parent=styles["Title"],
                           fontSize=18, alignment=TA_CENTER,
                           textColor=colors.HexColor("#888888"))
        ))
        story.append(Spacer(1, 2*cm))
        story.append(Paragraph(
            f"<b>{len(mappings)}</b> fichas aprobadas · Símbolo: Norte = negro · Sur = rojo",
            ParagraphStyle("AtlasInfo", parent=styles["Normal"],
                           fontSize=12, alignment=TA_CENTER,
                           textColor=colors.HexColor("#555555"))
        ))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(
            "<i>Las fichas restantes ({} pares pendientes) serán generadas con IA generativa.</i>".format(grand_total - len(mappings)),
            ParagraphStyle("AtlasNote", parent=styles["Normal"],
                           fontSize=10, alignment=TA_CENTER,
                           textColor=colors.HexColor("#999999"))
        ))

        # Render each ficha on its own page with metadata below
        FICHAS_DIR = os.path.join(_HERE, "data", "fichas_pares")
        for m in mappings:
            ficha_file = os.path.join(FICHAS_DIR, m["ficha_file"])
            if not os.path.exists(ficha_file):
                continue

            story.append(PageBreak())

            # Lookup classification for this pair
            clf = classifications.get((m["db_region"], m["db_zona"], m["db_bloque"], m["db_par"])) or {}
            tipo = clf.get("tipo")
            pat = clf.get("patogeno_canonico") or clf.get("patogeno")
            enf = clf.get("enfermedades_reales")

            # Header bar with par name
            story.append(Paragraph(
                f"<font color='white'><b>{m['db_par']}</b></font>",
                ParagraphStyle("FichaTitle", parent=styles["Normal"],
                    fontSize=18, alignment=TA_CENTER,
                    textColor=colors.white,
                    backColor=colors.HexColor("#1a3a5c"),
                    borderPadding=10, spaceAfter=6)
            ))
            ui_reg = ui_region_for(m["db_region"], m["db_zona"])
            story.append(Paragraph(
                f"<font size='9' color='#666666'>Ficha #{m['ficha_number']:03d}  ·  "
                f"Región UI: <b>{ui_reg}</b>  ·  DB: {m['db_region']} › {m['db_zona']} › {m['db_bloque']}</font>",
                ParagraphStyle("FichaMeta", parent=styles["Normal"],
                    fontSize=9, alignment=TA_CENTER, spaceAfter=10)
            ))

            # Render the ficha image (large size)
            ir = ImageReader(ficha_file)
            iw, ih = ir.getSize()
            max_w_cm = 18.0  # landscape A4 width ~25.7cm
            max_h_cm = 11.0  # leave space for metadata
            aspect = ih / iw
            if aspect <= max_h_cm / max_w_cm:
                w_cm = max_w_cm
                h_cm = max_w_cm * aspect
            else:
                h_cm = max_h_cm
                w_cm = max_h_cm / aspect
            img = Image(ficha_file, width=w_cm*cm, height=h_cm*cm)

            # Metadata block beside or below image
            tipo_color = TIPO_COLORS.get(tipo, "#666666") if tipo else "#bbbbbb"
            meta_html_parts = []
            if tipo:
                meta_html_parts.append(f"<b>TIPO:</b> <font color='{tipo_color}'><b>{tipo}</b></font>")
            if pat:
                meta_html_parts.append(f"<b>PATÓGENO:</b> <i>{pat}</i>")
            if enf:
                meta_html_parts.append(f"<b>ENFERMEDADES REALES:</b> {enf}")
            if not meta_html_parts:
                meta_html_parts.append("<font color='#999999'><i>Sin información médica registrada para este par.</i></font>")

            meta_para = Paragraph(
                "<br/><br/>".join(meta_html_parts),
                ParagraphStyle("FichaMetaBlock", parent=styles["Normal"],
                    fontSize=10, leading=14,
                    backColor=colors.HexColor("#f8f9fb"),
                    borderColor=colors.HexColor("#dddddd"), borderWidth=0.5,
                    borderPadding=10)
            )

            # Layout: image on left, metadata on right (since landscape)
            content_table = Table(
                [[img, meta_para]],
                colWidths=[w_cm*cm + 0.2*cm, 25.7*cm - (w_cm*cm + 0.5*cm)]
            )
            content_table.setStyle(TableStyle([
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 0),
                ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ]))
            story.append(content_table)
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph(
                f"<font size='7' color='#aaaaaa'>Fuente: Atlas Symbelia · Plantilla aprobada Holoacademia</font>",
                ParagraphStyle("FichaFooter", parent=styles["Normal"],
                    fontSize=7, alignment=TA_CENTER, textColor=colors.HexColor("#aaaaaa"))
            ))

    # ── Página final ──────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph(
        f"Total general de pares: <b>{grand_total}</b>",
        ParagraphStyle("GT", parent=styles["Normal"], fontSize=16,
                       alignment=TA_CENTER, textColor=colors.HexColor("#1a3a5c"))
    ))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        "Base de datos v4.3  ·  Holoacademia",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=9,
                       alignment=TA_CENTER, textColor=colors.HexColor("#888888"))
    ))

    doc.build(story)
    print(f"\nPDF generado: {OUT_PATH}")
    return grand_total

if __name__ == "__main__":
    db = load_db()
    region_data = build_region_data(db)

    print("\nConteo por región UI:")
    total_check = 0
    for ui_region, zonas_data in region_data.items():
        c = count_pairs(zonas_data)
        total_check += c
        sources = UI_REGIONS[ui_region]
        print(f"  {ui_region:10s}: {c:4d}  ({', '.join(z for _,z in sources)})")
    print(f"  {'TOTAL':10s}: {total_check}")

    build_pdf(db, region_data)
