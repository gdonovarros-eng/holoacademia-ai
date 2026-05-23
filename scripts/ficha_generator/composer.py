"""Componedor Pillow: superpone banner azul + sidebar + footer con texto perfecto
sobre la imagen anatómica generada por la IA.

Garantiza texto 100% correcto en español, fuentes consistentes, sin alucinaciones.
"""
from __future__ import annotations
import os
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# Symbelia spec
OUTPUT_W, OUTPUT_H = 1448, 1086
BANNER_H = 90
FOOTER_H = 50
PANEL_GAP = 16
SIDEBAR_W = 500
ANATOMY_W = OUTPUT_W - SIDEBAR_W - PANEL_GAP * 3  # left panel width

# Colors (matching approved Timo-Esternón)
COLOR_BANNER     = (26, 58, 92)        # #1a3a5c
COLOR_FOOTER_TXT = (130, 130, 130)
COLOR_TEXT_DARK  = (40, 40, 40)
COLOR_LABEL      = (130, 130, 130)
COLOR_BORDER     = (230, 230, 230)
COLOR_BG         = (252, 252, 252)
COLOR_SIDEBAR_BG = (255, 255, 255)
COLOR_NORTE      = (32, 32, 32)        # Negro
COLOR_SUR        = (229, 57, 53)       # Rojo

TIPO_COLORS = {
    "Bacteria":                  "#c0392b",
    "Virus":                     "#8e44ad",
    "Hongo":                     "#27ae60",
    "Hongo en General":          "#27ae60",
    "Parásito":                  "#e67e22",
    "Disfunción":                "#3498db",
    "Especial/Disfunción":       "#3498db",
    "Emocional/Psicoemocional":  "#d35400",
    "Reservorio":                "#7f8c8d",
    "Complejo":                  "#34495e",
    "Sin clasificar":            "#aaaaaa",
    "Tóxico":                    "#16a085",
    "Universal":                 "#2c3e50",
}

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# ============================================================
# Font loading
# ============================================================
def _find_font(candidates: list[str], size: int):
    """Intenta cargar la primera fuente disponible."""
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()

def load_fonts():
    # Mac system fonts
    bold_candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    regular_candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    return {
        "title":      _find_font(bold_candidates, 44),
        "label":      _find_font(bold_candidates, 14),
        "value_lg":   _find_font(bold_candidates, 26),
        "value":      _find_font(bold_candidates, 22),
        "subtext":    _find_font(regular_candidates, 14),
        "subtext_sm": _find_font(regular_candidates, 12),
        "footer":     _find_font(regular_candidates, 14),
    }

# ============================================================
# Draw helpers
# ============================================================
def _draw_text_wrapped(draw, xy, text, font, fill, max_width, line_height=None):
    """Dibuja texto con wrap automático. Devuelve y final."""
    if not text: return xy[1]
    x, y = xy
    if line_height is None:
        bbox = font.getbbox("Ay")
        line_height = bbox[3] - bbox[1] + 4
    words = text.split()
    line = ""
    for word in words:
        test = line + (" " if line else "") + word
        w = font.getbbox(test)[2]
        if w > max_width and line:
            draw.text((x, y), line, font=font, fill=fill)
            y += line_height
            line = word
        else:
            line = test
    if line:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y

def _round_rect(draw, xy, radius, fill=None, outline=None, width=1):
    """Dibuja rectángulo redondeado."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill,
                           outline=outline, width=width)

# ============================================================
# Composición principal
# ============================================================
def compose_ficha(anatomy_image: Image.Image,
                  par_name: str,
                  tipo: str | None,
                  punto_a: str,
                  punto_a_desc: str | None,
                  punto_b: str,
                  punto_b_desc: str | None,
                  region: str,
                  descripcion: str | None,
                  url: str = "www.symbelia.com") -> Image.Image:
    """Compone la ficha completa: banner + anatomía + sidebar + footer."""

    fonts = load_fonts()
    canvas = Image.new("RGB", (OUTPUT_W, OUTPUT_H), COLOR_BG)
    draw = ImageDraw.Draw(canvas)

    # ──── BANNER SUPERIOR ────
    draw.rectangle([0, 0, OUTPUT_W, BANNER_H], fill=COLOR_BANNER)
    title = par_name.upper()
    title_bbox = fonts["title"].getbbox(title)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    title_y = (BANNER_H - title_h) // 2 - 4
    draw.text((40, title_y), title, font=fonts["title"], fill="white")

    # ──── PANEL ANATÓMICO (izquierda) ────
    anat_x0 = PANEL_GAP
    anat_y0 = BANNER_H + PANEL_GAP
    anat_x1 = OUTPUT_W - SIDEBAR_W - PANEL_GAP * 2
    anat_y1 = OUTPUT_H - FOOTER_H - PANEL_GAP

    # Fondo del panel anatómico
    _round_rect(draw, (anat_x0, anat_y0, anat_x1, anat_y1),
                radius=10, fill="white", outline=COLOR_BORDER, width=1)

    # Insertar imagen anatómica
    anat_w = anat_x1 - anat_x0 - 16
    anat_h = anat_y1 - anat_y0 - 16
    # Resize preserving aspect
    iw, ih = anatomy_image.size
    scale = min(anat_w / iw, anat_h / ih)
    new_w = int(iw * scale)
    new_h = int(ih * scale)
    anat_resized = anatomy_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    # Center
    paste_x = anat_x0 + 8 + (anat_w - new_w) // 2
    paste_y = anat_y0 + 8 + (anat_h - new_h) // 2
    canvas.paste(anat_resized, (paste_x, paste_y))

    # ──── SIDEBAR DERECHA ────
    sb_x0 = OUTPUT_W - SIDEBAR_W - PANEL_GAP
    sb_y0 = BANNER_H + PANEL_GAP
    sb_x1 = OUTPUT_W - PANEL_GAP
    sb_y1 = OUTPUT_H - FOOTER_H - PANEL_GAP
    _round_rect(draw, (sb_x0, sb_y0, sb_x1, sb_y1),
                radius=10, fill=COLOR_SIDEBAR_BG, outline=COLOR_BORDER, width=1)

    inner_x = sb_x0 + 30
    inner_w = (sb_x1 - sb_x0) - 60
    y = sb_y0 + 30

    # 1. TIPO
    tipo_str = tipo or "—"
    tipo_color_hex = TIPO_COLORS.get(tipo, "#1a3a5c") if tipo else "#888888"
    tipo_color_rgb = hex_to_rgb(tipo_color_hex)
    draw.text((inner_x, y), "TIPO", font=fonts["label"], fill=COLOR_LABEL)
    y += 22
    draw.text((inner_x, y), tipo_str, font=fonts["value_lg"], fill=tipo_color_rgb)
    y += 42
    # Separator
    draw.line([(inner_x, y), (inner_x + inner_w, y)], fill=COLOR_BORDER, width=1)
    y += 18

    # 2. PUNTO A (Norte) — círculo NEGRO
    bullet_r = 11
    draw.ellipse([inner_x, y+3, inner_x + bullet_r*2, y+3 + bullet_r*2],
                 fill=COLOR_NORTE)
    draw.text((inner_x + bullet_r*2 + 10, y), "PUNTO A (Norte)",
              font=fonts["label"], fill=COLOR_LABEL)
    y += 24
    draw.text((inner_x, y), punto_a, font=fonts["value"], fill=COLOR_TEXT_DARK)
    y += 30
    if punto_a_desc:
        y = _draw_text_wrapped(draw, (inner_x, y), punto_a_desc,
                                fonts["subtext_sm"], COLOR_LABEL, inner_w, line_height=18)
    y += 12
    draw.line([(inner_x, y), (inner_x + inner_w, y)], fill=COLOR_BORDER, width=1)
    y += 16

    # 3. PUNTO B (Sur) — círculo ROJO
    draw.ellipse([inner_x, y+3, inner_x + bullet_r*2, y+3 + bullet_r*2],
                 fill=COLOR_SUR)
    draw.text((inner_x + bullet_r*2 + 10, y), "PUNTO B (Sur)",
              font=fonts["label"], fill=COLOR_LABEL)
    y += 24
    draw.text((inner_x, y), punto_b, font=fonts["value"], fill=COLOR_TEXT_DARK)
    y += 30
    if punto_b_desc:
        y = _draw_text_wrapped(draw, (inner_x, y), punto_b_desc,
                                fonts["subtext_sm"], COLOR_LABEL, inner_w, line_height=18)
    y += 12
    draw.line([(inner_x, y), (inner_x + inner_w, y)], fill=COLOR_BORDER, width=1)
    y += 16

    # 4. REGIÓN
    draw.text((inner_x, y), "REGIÓN", font=fonts["label"], fill=COLOR_LABEL)
    y += 22
    draw.text((inner_x, y), region or "—", font=fonts["value"], fill=COLOR_TEXT_DARK)
    y += 36
    draw.line([(inner_x, y), (inner_x + inner_w, y)], fill=COLOR_BORDER, width=1)
    y += 16

    # 5. DESCRIPCIÓN
    draw.text((inner_x, y), "DESCRIPCIÓN", font=fonts["label"], fill=COLOR_LABEL)
    y += 22
    if descripcion:
        _draw_text_wrapped(draw, (inner_x, y), descripcion,
                          fonts["subtext"], COLOR_TEXT_DARK, inner_w, line_height=20)

    # ──── FOOTER ────
    footer_y = OUTPUT_H - FOOTER_H
    footer_txt = f"Vista de {region} · {url}"
    fbbox = fonts["footer"].getbbox(footer_txt)
    fw = fbbox[2] - fbbox[0]
    draw.text(((OUTPUT_W - fw) // 2, footer_y + 16),
              footer_txt, font=fonts["footer"], fill=COLOR_FOOTER_TXT)

    return canvas

def compose_from_bytes(anatomy_png_bytes: bytes, **kwargs) -> bytes:
    """Compone ficha desde bytes PNG de la anatomía y devuelve bytes PNG."""
    anat_img = Image.open(BytesIO(anatomy_png_bytes)).convert("RGB")
    result = compose_ficha(anat_img, **kwargs)
    out = BytesIO()
    result.save(out, format="PNG", optimize=True)
    return out.getvalue()
