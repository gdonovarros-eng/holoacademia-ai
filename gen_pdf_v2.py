#!/usr/bin/env python3
"""
Generate pares_por_region_revision_v2.pdf
Correction: Columna Vertebral moved from Extras → Espalda
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

DB_PATH = "/Users/m2/Documents/New project/data/biomagnetic_pairs_db.json"
OUT_PATH = "/Users/m2/Documents/New project/pares_por_region_revision_v2.pdf"

# Zones to exclude (scan batches)
EXCLUDE_ZONA_PREFIXES = ["Rastreo"]
EXCLUDE_ZONA_NAMES = {"Hepatitis"}

def is_excluded(zona_nombre):
    if zona_nombre in EXCLUDE_ZONA_NAMES:
        return True
    for prefix in EXCLUDE_ZONA_PREFIXES:
        if zona_nombre.startswith(prefix):
            return True
    return False

def load_db():
    with open(DB_PATH) as f:
        return json.load(f)

def get_zona_pairs(db, region_nombre, zona_nombre):
    """Return list of (bloque_nombre, [pairs]) for a given region+zona."""
    for region in db["regiones"]:
        if region["nombre"] == region_nombre:
            for zona in region["zonas"]:
                if zona["nombre"] == zona_nombre:
                    result = []
                    for bloque in zona.get("bloques", []):
                        pares = bloque.get("pares", [])
                        result.append((bloque["nombre"], pares))
                    return result
    return []

# UI region definitions: list of (db_region, db_zona)
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
    ],
    "Espalda": [
        ("Tronco", "Espalda"),
        ("Extras", "Columna Vertebral"),   # CORRECTION applied
    ],
    "Pelvis": [
        ("Pelvis", "Delantera"),
        ("Pelvis", "Trasera"),
        ("Pelvis", "Sexo"),
    ],
    "Brazos": [
        ("Miembros", "Brazos"),
    ],
    "Piernas": [
        ("Miembros", "Piernas"),
    ],
    "Extras": [
        ("Extras", "Variables"),
        ("Extras", "Ejes Corporales"),
    ],
}

def build_region_data(db):
    """For each UI region, collect pairs by zona > bloque."""
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
    return sum(
        len(pares)
        for (_, bloques) in zonas_data
        for (_, pares) in bloques
    )

def build_pdf(db, region_data):
    doc = SimpleDocTemplate(
        OUT_PATH,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=6,
        textColor=colors.HexColor("#1a3a5c"),
    )
    style_correction = ParagraphStyle(
        "Correction",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#8b0000"),
        spaceAfter=4,
        spaceBefore=4,
        borderColor=colors.HexColor("#8b0000"),
        borderWidth=1,
        borderPadding=6,
        backColor=colors.HexColor("#fff5f5"),
    )
    style_subtitle = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#555555"),
        spaceAfter=14,
    )
    style_region_heading = ParagraphStyle(
        "RegionHeading",
        parent=styles["Heading1"],
        fontSize=14,
        textColor=colors.HexColor("#ffffff"),
        backColor=colors.HexColor("#1a3a5c"),
        borderPadding=6,
        spaceBefore=16,
        spaceAfter=8,
    )
    style_zona_heading = ParagraphStyle(
        "ZonaHeading",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=colors.HexColor("#1a3a5c"),
        spaceBefore=10,
        spaceAfter=4,
    )
    style_bloque_heading = ParagraphStyle(
        "BloqueHeading",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#555555"),
        spaceBefore=6,
        spaceAfter=2,
        fontName="Helvetica-BoldOblique",
    )
    style_pair = ParagraphStyle(
        "Pair",
        parent=styles["Normal"],
        fontSize=8.5,
        leftIndent=12,
        spaceAfter=1,
        leading=12,
    )
    style_normal = styles["Normal"]
    style_table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = []

    # ─── Title ───────────────────────────────────────────────────────────────
    story.append(Paragraph("Pares Biomagnéticos por Región — Revisión v2", style_title))
    story.append(Paragraph(
        "⚠ Corrección aplicada: Columna Vertebral movida de Extras → Espalda",
        style_correction
    ))
    story.append(Paragraph(
        "Zonas excluidas: todas las zonas «Rastreo *» y zona «Hepatitis» (lotes de escaneo, sin pares nominados).",
        style_subtitle
    ))

    # ─── Summary table ───────────────────────────────────────────────────────
    header_row = [
        Paragraph("Región", style_table_header),
        Paragraph("Zona(s) DB", style_table_header),
        Paragraph("Pares", style_table_header),
    ]
    table_rows = [header_row]
    grand_total = 0

    for ui_region, sources in UI_REGIONS.items():
        zonas_data = region_data[ui_region]
        count = count_pairs(zonas_data)
        grand_total += count
        zona_names = ", ".join(z for (_, z) in sources)
        table_rows.append([
            Paragraph(ui_region, styles["Normal"]),
            Paragraph(zona_names, styles["Normal"]),
            Paragraph(str(count), styles["Normal"]),
        ])

    table_rows.append([
        Paragraph("<b>TOTAL</b>", styles["Normal"]),
        Paragraph("", styles["Normal"]),
        Paragraph(f"<b>{grand_total}</b>", styles["Normal"]),
    ])

    summary_table = Table(
        table_rows,
        colWidths=[3.5*cm, 10*cm, 2*cm],
        repeatRows=1,
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.HexColor("#f0f4f8"), colors.white]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#d4e6f1")),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5*cm))

    # ─── Duplicate check ─────────────────────────────────────────────────────
    pair_to_regions = defaultdict(list)
    for ui_region, zonas_data in region_data.items():
        for (zona_nombre, bloques) in zonas_data:
            for (bloque_nombre, pares) in bloques:
                for par in pares:
                    pair_to_regions[par.strip()].append(ui_region)

    dupes = {p: rs for p, rs in pair_to_regions.items() if len(rs) > 1}
    if dupes:
        story.append(Paragraph(
            f"<b>⚠ Duplicados encontrados: {len(dupes)}</b>",
            ParagraphStyle("DupeTitle", parent=styles["Normal"], textColor=colors.red, fontSize=10)
        ))
        for par, regions_list in list(dupes.items())[:20]:
            story.append(Paragraph(
                f"  • {par} → {', '.join(regions_list)}",
                ParagraphStyle("DupePair", parent=styles["Normal"], fontSize=8, leftIndent=12)
            ))
        if len(dupes) > 20:
            story.append(Paragraph(f"  ... y {len(dupes)-20} más.", styles["Normal"]))
    else:
        story.append(Paragraph(
            "✓ Sin duplicados entre regiones.",
            ParagraphStyle("NoDupe", parent=styles["Normal"], textColor=colors.HexColor("#006600"), fontSize=10)
        ))
    story.append(Spacer(1, 0.3*cm))

    # ─── Per-region sections ─────────────────────────────────────────────────
    for ui_region, zonas_data in region_data.items():
        story.append(PageBreak())
        region_pair_count = count_pairs(zonas_data)
        sources = UI_REGIONS[ui_region]
        zona_label = ", ".join(f"{db_r} › {db_z}" for (db_r, db_z) in sources)

        story.append(Paragraph(
            f"  {ui_region}   ({region_pair_count} pares)",
            style_region_heading
        ))
        story.append(Paragraph(
            f"Zonas DB: {zona_label}",
            ParagraphStyle("ZonaDB", parent=styles["Normal"], fontSize=9,
                           textColor=colors.HexColor("#555555"), spaceAfter=8)
        ))

        pair_num = 1
        for (zona_nombre, bloques) in zonas_data:
            zona_pair_count = sum(len(pares) for (_, pares) in bloques)
            story.append(Paragraph(
                f"Zona: {zona_nombre}  ({zona_pair_count} pares)",
                style_zona_heading
            ))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#1a3a5c")))

            for (bloque_nombre, pares) in bloques:
                story.append(Paragraph(
                    f"[ {bloque_nombre} — {len(pares)} pares ]",
                    style_bloque_heading
                ))
                for par in pares:
                    story.append(Paragraph(
                        f"{pair_num}. {par}",
                        style_pair
                    ))
                    pair_num += 1

    # ─── Grand total footer page ──────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph(
        f"Total general de pares nominados: <b>{grand_total}</b>",
        ParagraphStyle("GrandTotal", parent=styles["Normal"], fontSize=16,
                       alignment=TA_CENTER, textColor=colors.HexColor("#1a3a5c"))
    ))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "(Excluidos: Rastreo Cabeza, Rastreo Cuello, Rastreo Tórax, Rastreo Abdomen, "
        "Rastreo Espalda, Rastreo Pelvis, Rastreo Brazos, Rastreo Piernas, "
        "Rastreo General, Hepatitis)",
        ParagraphStyle("Excluded", parent=styles["Normal"], fontSize=9,
                       alignment=TA_CENTER, textColor=colors.HexColor("#888888"))
    ))

    doc.build(story)
    print(f"PDF written to: {OUT_PATH}")

    return grand_total, {ui_r: count_pairs(region_data[ui_r]) for ui_r in UI_REGIONS}


if __name__ == "__main__":
    db = load_db()
    region_data = build_region_data(db)

    # Print region counts for verification
    print("\nRegion pair counts:")
    total_check = 0
    for ui_region, zonas_data in region_data.items():
        c = count_pairs(zonas_data)
        total_check += c
        sources = UI_REGIONS[ui_region]
        print(f"  {ui_region:12s}: {c:4d}  ({', '.join(z for _,z in sources)})")
    print(f"  {'TOTAL':12s}: {total_check}")

    grand_total, counts = build_pdf(db, region_data)
    print(f"\nDone. Grand total in PDF: {grand_total}")
