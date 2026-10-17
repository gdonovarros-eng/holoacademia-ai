"""
PDF "carta antigua" para la entrega del consumidor (Método Holos).

Genera un documento con aspecto de pergamino: fondo crema, borde doble sepia,
ornamentos en las esquinas, tipografía serif (Times) y sello al cierre. Parsea
el markdown de la entrega (## / ### / listas / **negritas**).

build_carta_pdf(content, nombre="", lang="es", title="") -> bytes (PDF)
"""
from __future__ import annotations

import io
import re
import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, HRFlowable, Flowable,
)

# ── Paleta pergamino ────────────────────────────────────────────────────────────
PARCHMENT = HexColor("#f4ead0")   # fondo crema
PARCH_EDGE = HexColor("#e7d7b0")  # sombreado de bordes
INK = HexColor("#3b2f1c")         # tinta sepia oscura
ACCENT = HexColor("#7a5a2e")      # marrón para títulos y bordes
FAINT = HexColor("#9a7b4a")

_MESES = {
    "es": ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "pt": ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
           "agosto", "setembro", "outubro", "novembro", "dezembro"],
    "en": ["", "January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
}
_LABELS = {
    "es": {"prep": "Preparado especialmente para", "foot": "Holoacademia · holoacademia.tv",
           "sello": "HOLOACADEMIA", "cierre": "Con cariño,"},
    "pt": {"prep": "Preparado especialmente para", "foot": "Holoacademia · holoacademia.tv",
           "sello": "HOLOACADEMIA", "cierre": "Com carinho,"},
    "en": {"prep": "Prepared especially for", "foot": "Holoacademia · holoacademia.tv",
           "sello": "HOLOACADEMIA", "cierre": "With care,"},
}


def _fecha(lang: str) -> str:
    hoy = datetime.date.today()
    meses = _MESES.get(lang, _MESES["es"])
    if lang == "en":
        return f"{meses[hoy.month]} {hoy.day}, {hoy.year}"
    return f"{hoy.day} de {meses[hoy.month]} de {hoy.year}"


def _fmt_fecha(iso: str, lang: str) -> str:
    try:
        parts = [int(x) for x in str(iso).split("T")[0].split("-")[:3]]
        y, m, d = parts[0], parts[1], parts[2]
        meses = _MESES.get(lang, _MESES["es"])
        if lang == "en":
            return f"{meses[m]} {d}, {y}"
        return f"{d} de {meses[m]} de {y}"
    except Exception:
        return str(iso or "")


def _inline(s: str) -> str:
    s = (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])", r"<i>\1</i>", s)
    s = s.replace("[pausa]", "<font color='#9a7b4a'>· pausa ·</font>")
    return s


# ── Ornamento de página (fondo + borde + esquinas + pie) ────────────────────────
def _decorate(canvas, doc):
    w, h = A4
    canvas.saveState()
    # Fondo pergamino
    canvas.setFillColor(PARCHMENT)
    canvas.rect(0, 0, w, h, stroke=0, fill=1)
    # Sombreado sutil en los bordes (viñeta)
    canvas.setFillColor(PARCH_EDGE)
    for i in range(8):
        a = 0.06 - i * 0.006
        if a <= 0:
            break
        canvas.setFillAlpha(a)
        m = 6 + i * 3
        canvas.rect(m, m, w - 2 * m, h - 2 * m, stroke=0, fill=1)
    canvas.setFillAlpha(1)
    # Borde doble
    mo = 16 * mm
    mi = 19 * mm
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(1.6)
    canvas.rect(mo, mo, w - 2 * mo, h - 2 * mo, stroke=1, fill=0)
    canvas.setLineWidth(0.6)
    canvas.rect(mi, mi, w - 2 * mi, h - 2 * mi, stroke=1, fill=0)
    # Ornamentos en las esquinas (rombo + trazos)
    canvas.setFillColor(ACCENT)
    for (cx, cy) in [(mi, mi), (w - mi, mi), (mi, h - mi), (w - mi, h - mi)]:
        canvas.saveState(); canvas.translate(cx, cy); canvas.rotate(45)
        canvas.rect(-2.2, -2.2, 4.4, 4.4, stroke=0, fill=1)
        canvas.restoreState()
    # Pie: filete + folio (sin marca)
    canvas.setStrokeColor(FAINT); canvas.setLineWidth(0.5)
    canvas.line(mi + 26 * mm, mo + 7 * mm, w - mi - 26 * mm, mo + 7 * mm)
    canvas.setFont("Times-Italic", 9); canvas.setFillColor(FAINT)
    canvas.drawCentredString(w / 2, mo + 2.6 * mm, str(doc.page))
    canvas.restoreState()


class Seal(Flowable):
    """Pequeño sello circular de cierre."""
    def __init__(self, lang="es"):
        super().__init__()
        self.width = 42; self.height = 42; self.lang = lang
    def draw(self):
        c = self.canv
        c.saveState()
        c.translate(21, 18)
        c.setFillColor(HexColor("#8a3b2e")); c.setFillAlpha(0.92)
        c.circle(0, 0, 18, stroke=0, fill=1)
        c.setFillAlpha(1); c.setStrokeColor(HexColor("#5e271d")); c.setLineWidth(1)
        c.circle(0, 0, 18, stroke=1, fill=0)
        c.circle(0, 0, 14, stroke=1, fill=0)
        c.setFillColor(HexColor("#f4ead0")); c.setFont("Times-Bold", 17)
        c.drawCentredString(0, -6, "H")
        c.restoreState()


def _styles():
    return {
        "brand": ParagraphStyle("brand", fontName="Times-Bold", fontSize=11, leading=14,
                                textColor=ACCENT, alignment=TA_CENTER, spaceAfter=2),
        "title": ParagraphStyle("title", fontName="Times-Bold", fontSize=23, leading=27,
                                textColor=INK, alignment=TA_CENTER, spaceBefore=4, spaceAfter=4),
        "prep": ParagraphStyle("prep", fontName="Times-Italic", fontSize=11.5, leading=15,
                               textColor=FAINT, alignment=TA_CENTER, spaceAfter=2),
        "name": ParagraphStyle("name", fontName="Times-Bold", fontSize=14, leading=18,
                               textColor=ACCENT, alignment=TA_CENTER, spaceAfter=1),
        "date": ParagraphStyle("date", fontName="Times-Italic", fontSize=10, leading=13,
                               textColor=FAINT, alignment=TA_CENTER, spaceAfter=8),
        "birth": ParagraphStyle("birth", fontName="Times-Italic", fontSize=10.5, leading=14,
                                textColor=FAINT, alignment=TA_CENTER, spaceBefore=1, spaceAfter=2),
        "h1": ParagraphStyle("h1", fontName="Times-Bold", fontSize=15.5, leading=19,
                             textColor=ACCENT, alignment=TA_CENTER, spaceBefore=18, spaceAfter=9),
        "h2": ParagraphStyle("h2", fontName="Times-Bold", fontSize=12.5, leading=16,
                             textColor=INK, spaceBefore=11, spaceAfter=3),
        "h3": ParagraphStyle("h3", fontName="Times-BoldItalic", fontSize=11.5, leading=15,
                             textColor=ACCENT, spaceBefore=8, spaceAfter=2),
        "body": ParagraphStyle("body", fontName="Times-Roman", fontSize=11, leading=16.5,
                               textColor=INK, alignment=TA_JUSTIFY, spaceAfter=5),
        "li": ParagraphStyle("li", fontName="Times-Roman", fontSize=11, leading=16,
                             textColor=INK, alignment=TA_JUSTIFY, leftIndent=14,
                             bulletIndent=2, spaceAfter=3),
        "cierre": ParagraphStyle("cierre", fontName="Times-Italic", fontSize=11, leading=15,
                                 textColor=INK, alignment=TA_CENTER, spaceBefore=14, spaceAfter=2),
    }


def _flowables(content: str, nombre: str, lang: str, title: str, fecha_nac: str = ""):
    S = _styles()
    out = []
    # Encabezado: nombre completo + fecha de nacimiento (sin marca)
    cabecera = (nombre or "").strip() or (title or "")
    out.append(Spacer(1, 4))
    out.append(Paragraph(_inline(cabecera), S["title"]))
    if fecha_nac:
        out.append(Paragraph(_fmt_fecha(fecha_nac, lang), S["birth"]))
    out.append(HRFlowable(width="52%", thickness=0.7, color=ACCENT, spaceBefore=8, spaceAfter=13,
                          hAlign="CENTER"))

    for raw in (content or "").split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("# "):
            out.append(Paragraph(_inline(line[2:].strip()).upper(), S["h1"]))
            out.append(HRFlowable(width="26%", thickness=0.6, color=FAINT, spaceBefore=0,
                                  spaceAfter=9, hAlign="CENTER"))
        elif line.startswith("### "):
            out.append(Paragraph(_inline(line[4:].strip()), S["h3"]))
        elif line.startswith("## "):
            out.append(Paragraph(_inline(line[3:].strip()), S["h2"]))
        else:
            m = re.match(r"^\s*(?:[-*•]|(\d+)[.)])\s+(.*)$", line)
            if m:
                num = m.group(1)
                bullet = (num + ".") if num else "•"
                out.append(Paragraph(_inline(m.group(2)), S["li"], bulletText=bullet))
            else:
                out.append(Paragraph(_inline(line), S["body"]))

    out.append(Spacer(1, 14))
    out.append(HRFlowable(width="20%", thickness=0.6, color=FAINT, spaceBefore=2, spaceAfter=2,
                          hAlign="CENTER"))
    return out


def build_carta_pdf(content: str, nombre: str = "", lang: str = "es", title: str = "",
                    fecha_nac: str = "") -> bytes:
    lang = lang if lang in ("es", "en", "pt") else "es"
    buf = io.BytesIO()
    w, h = A4
    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=26 * mm, rightMargin=26 * mm, topMargin=28 * mm, bottomMargin=26 * mm,
        title=((nombre or "").strip() or title or "Informe"), author="",
    )
    doc.lang = lang
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  w - doc.leftMargin - doc.rightMargin,
                  h - doc.topMargin - doc.bottomMargin, id="body")
    doc.addPageTemplates([PageTemplate(id="carta", frames=[frame], onPage=_decorate)])
    doc.build(_flowables(content, nombre, lang, title, fecha_nac))
    return buf.getvalue()
