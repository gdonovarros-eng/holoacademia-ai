#!/usr/bin/env python3
"""
Generate pares_biomagnéticos_v4.pdf  — base de datos v4.0 (1058 pares)
"""
import json
from collections import defaultdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

DB_PATH  = "/Users/m2/Documents/New project/data/biomagnetic_pairs_db.json"
OUT_PATH = "/Users/m2/Documents/New project/pares_biomagnéticos_v4.pdf"

EXCLUDE_ZONA_NAMES = set()  # ninguna zona excluida en v4.1

def load_db():
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)

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
    doc = SimpleDocTemplate(
        OUT_PATH,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm,   bottomMargin=2*cm,
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
    story.append(Paragraph("Base de datos v4.0 — Revisión y validación", s_subtitle))

    consol = db.get("consolidacion", {})
    meta_lines = [
        f"<b>Total de pares v4.0:</b> {db.get('total', '—')}",
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
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#1a3a5c")))
            for (bloque_nombre, pares) in bloques:
                story.append(Paragraph(
                    f"[ {bloque_nombre} — {len(pares)} pares ]", s_bloque
                ))
                for par in pares:
                    story.append(Paragraph(f"{pair_num}. {par}", s_pair))
                    pair_num += 1

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
        "Base de datos v4.0  ·  Holoacademia",
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
