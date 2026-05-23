from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import textwrap


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "docs" / "cv"
PHOTO_PATH = OUTPUT_DIR / "gerardo_cv_photo-000.jpg"
OUTPUT_PDF = OUTPUT_DIR / "Gerardo-Donovarros-CV-Interactive.pdf"

PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0
MARGIN = 36.0
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2)

BG = "0.03 0.04 0.05"
BG_SOFT = "0.06 0.08 0.11"
BG_CARD = "0.08 0.10 0.14"
TEXT = "0.95 0.94 0.91"
TEXT_SOFT = "0.76 0.75 0.72"
MUTED = "0.58 0.60 0.62"
ACCENT = "0.89 0.75 0.55"
ACCENT_SOFT = "0.79 0.63 0.40"
TEAL = "0.52 0.69 0.66"
LINE = "0.20 0.22 0.26"


@dataclass
class ExperienceItem:
    company: str
    role: str
    period: str
    summary: str
    bullets: list[str]


@dataclass
class PageState:
    commands: list[str] = field(default_factory=list)
    annotations: list[tuple[float, float, float, float, str]] = field(default_factory=list)


DATA = {
    "full_name": "Gerardo Misael Donovarros Belderrain",
    "display_name": "Gerardo Donovarros",
    "headline": (
        "Director Comercial, estrategia de marketing, growth, storyselling, "
        "IA y automatización aplicada al negocio."
    ),
    "subheadline": (
        "Más de 15 años entrando a negocios donde hacía falta ordenar la oferta, "
        "afinar el mensaje, alinear equipos y convertir estrategia en ventas sostenibles."
    ),
    "summary": (
        "Mi trabajo no empieza en anuncios ni termina en una presentación. "
        "Empieza en entender qué está frenando el crecimiento y termina cuando "
        "la operación vende mejor, comunica mejor y ejecuta con más claridad. "
        "He hecho eso en productos digitales, educación, retail, gobierno y B2B."
    ),
    "location": "Ciudad de México",
    "email": "gdonovarros@gmail.com",
    "email_href": "mailto:gdonovarros@gmail.com",
    "phone": "442 271 1900",
    "phone_href": "tel:+524422711900",
    "web_href": "https://gdonovarros-eng.github.io/holoacademia-ai/cv/",
    "web_label": "Ver CV web",
    "result_title": "Cuando la estrategia baja a operación, el negocio responde.",
    "result_intro": (
        "Los números importan, pero más importa de dónde salen: de una oferta clara, "
        "un mensaje bien planteado y una ejecución comercial que sí sostiene crecimiento."
    ),
    "results": [
        {
            "value": "125%",
            "label": "ROI",
            "detail": "En estrategias donde oferta, mensaje, seguimiento y ejecución trabajaron alineados.",
        },
        {
            "value": "+40K",
            "label": "USD/mes",
            "detail": "Presupuestos gestionados en marketing y performance.",
        },
        {
            "value": "4X",
            "label": "Facturación",
            "detail": "Incremento en una región clave en menos de 24 meses.",
        },
        {
            "value": "30+",
            "label": "Personas",
            "detail": "Equipos dirigidos entre marketing, ventas, operación y finanzas.",
        },
    ],
    "storyselling": (
        "No veo el contenido como adorno. Lo uso para que la oferta tenga sentido, "
        "conecte mejor y haga más fácil la venta. Para mí, storyselling significa "
        "que la narrativa comercial ayuda a posicionar, diferenciar y convertir."
    ),
    "sectors": [
        "Marketplace y productos digitales",
        "Educación",
        "Salud y cuidado personal",
        "Retail y consumo masivo",
        "Gobierno, construcción y B2B",
        "Producción audiovisual orientada a venta",
    ],
    "experience": [
        ExperienceItem(
            company="Holoacademia",
            role="Director General · Socio Fundador",
            period="2019 - 2025",
            summary=(
                "Construcción desde cero de una marca educativa digital con productos escalables, "
                "membresías, certificaciones y un sistema comercial completo."
            ),
            bullets=[
                "Diseño integral de estrategia de negocio, marketing, ventas, posicionamiento y operación.",
                "Desarrollo de embudos, VSLs, automatización, CRM, email marketing y WhatsApp Business.",
                "Dirección de equipos multidisciplinarios y transformación operativa con IA.",
            ],
        ),
        ExperienceItem(
            company="Laborlegno",
            role="Dirección Comercial · Empresa Propia",
            period="2017 - 2019",
            summary=(
                "Expansión comercial en sector público y constructoras privadas, con foco en cuentas clave, "
                "licitaciones y proyectos llave en mano."
            ),
            bullets=[
                "Relación con instituciones gubernamentales y constructoras.",
                "Estrategia comercial, precios, posicionamiento y alianzas estratégicas.",
            ],
        ),
        ExperienceItem(
            company="Enlace",
            role="Director Comercial",
            period="2015 - 2017",
            summary=(
                "Dirección de estrategia comercial para sector gubernamental y gestión de negociaciones "
                "de alto nivel con visión institucional."
            ),
            bullets=[
                "Coordinación de licitaciones públicas y propuestas técnico-comerciales.",
                "Fortalecimiento de relaciones institucionales de largo plazo.",
            ],
        ),
        ExperienceItem(
            company="Tendenzza",
            role="Gerente Regional de Ventas",
            period="2013 - 2015",
            summary=(
                "Gestión comercial de una región clave con foco en expansión, fidelización e incentivos."
            ),
            bullets=[
                "Crecimiento de facturación 4X en menos de 24 meses.",
                "Liderazgo de equipo comercial regional con foco en productividad y rentabilidad.",
            ],
        ),
        ExperienceItem(
            company="Perdura",
            role="Coordinador de Marca / Asesor Comercial",
            period="2007 - 2013",
            summary=(
                "Base sólida en marca, punto de venta, distribuidores, apertura de cuentas y ejecución comercial."
            ),
            bullets=[
                "Apertura de más de 20 cuentas de alto valor.",
                "Trabajo con clientes estratégicos, canal y ejecución comercial presencial.",
            ],
        ),
    ],
    "skills": [
        "Estrategia comercial y omnicanal",
        "Storyselling y narrativa de venta",
        "Marketing digital y performance",
        "Growth y monetización de productos digitales",
        "Negociación B2B y sector gobierno",
        "CRM, automatización e IA aplicada",
        "Liderazgo de equipos y rediseño operativo",
        "Google Ads, Meta Ads y TikTok Ads",
    ],
    "tools": [
        "Wix Studio",
        "Canva",
        "Photoshop",
        "Hotmart",
        "ManyChat",
        "WhatsApp Business",
        "CRM",
        "Automatización",
    ],
    "education": [
        "Administración de Empresas · Universidad Autónoma Metropolitana · 2015 - 2019",
        "Programa de Alta Dirección (AD) · IPADE · 2015",
        "Diplomado en Desarrollo de Habilidades Gerenciales · Tec de Monterrey · 2009",
        "Finanzas para No Financieros · Tec de Monterrey · 2008",
    ],
}


def pdf_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", "")
        .replace("\n", " ")
    )


def wrap_text(text: str, width_chars: int) -> list[str]:
    return textwrap.wrap(text, width=width_chars, break_long_words=False, break_on_hyphens=False)


def jpeg_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:2] != b"\xff\xd8":
        raise ValueError("La foto no es un JPEG válido")
    i = 2
    while i < len(data):
        while i < len(data) and data[i] == 0xFF:
            i += 1
        if i >= len(data):
            break
        marker = data[i]
        i += 1
        if marker in {0xD8, 0xD9}:
            continue
        if i + 2 > len(data):
            break
        seg_len = int.from_bytes(data[i : i + 2], "big")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(data[i + 3 : i + 5], "big")
            width = int.from_bytes(data[i + 5 : i + 7], "big")
            return width, height
        i += seg_len
    raise ValueError("No se pudieron leer las dimensiones del JPEG")


class PdfBuilder:
    def __init__(self) -> None:
        self.pages: list[PageState] = []
        self.current = PageState()

    def start_page(self) -> None:
        if self.current.commands:
            self.pages.append(self.current)
        self.current = PageState()
        self.background()

    def finish(self) -> None:
        if self.current.commands:
            self.pages.append(self.current)

    def add(self, command: str) -> None:
        self.current.commands.append(command)

    def background(self) -> None:
        self.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=BG)
        self.rect(0, PAGE_HEIGHT - 110, PAGE_WIDTH, 110, fill="0.05 0.06 0.08")

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: str | None = None,
        stroke: str | None = None,
        line_width: float = 1.0,
    ) -> None:
        pieces = ["q"]
        if fill:
            pieces.append(f"{fill} rg")
        if stroke:
            pieces.append(f"{stroke} RG {line_width:.2f} w")
        pieces.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re")
        if fill and stroke:
            pieces.append("B")
        elif fill:
            pieces.append("f")
        else:
            pieces.append("S")
        pieces.append("Q")
        self.add(" ".join(pieces))

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = LINE, width: float = 1.0) -> None:
        self.add(f"q {color} RG {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S Q")

    def text(self, x: float, y: float, text: str, *, font: str = "F1", size: float = 11.0, color: str = TEXT) -> None:
        safe = pdf_escape(text)
        self.add(f"BT {color} rg /{font} {size:.2f} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ({safe}) Tj ET")

    def image_jpeg(self, x: float, y: float, w: float, h: float) -> None:
        self.add(f"q {w:.2f} 0 0 {h:.2f} {x:.2f} {y:.2f} cm /Im1 Do Q")

    def link(self, x: float, y: float, w: float, h: float, uri: str) -> None:
        self.current.annotations.append((x, y, x + w, y + h, uri))

    def button(self, x: float, y: float, w: float, h: float, label: str, uri: str, *, primary: bool = False) -> None:
        fill = ACCENT_SOFT if primary else BG_CARD
        stroke = ACCENT_SOFT if primary else LINE
        text_color = "0.08 0.09 0.11" if primary else TEXT
        self.rect(x, y, w, h, fill=fill, stroke=stroke, line_width=1.0)
        self.text(x + 14, y + (h / 2) - 4, label, font="F2", size=10.0, color=text_color)
        self.link(x, y, w, h, uri)

    def block_title(self, x: float, y: float, kicker: str, title: str, *, title_size: float = 17.0) -> float:
        self.text(x, y, kicker.upper(), font="F2", size=8.6, color=ACCENT)
        y -= 16
        for line in wrap_text(title, 34):
            self.text(x, y, line, font="F2", size=title_size, color=TEXT)
            y -= title_size + 4
        return y

    def paragraph(self, x: float, y: float, text: str, width_chars: int, *, size: float = 10.6, color: str = TEXT_SOFT, leading: float = 14.0) -> float:
        for line in wrap_text(text, width_chars):
            self.text(x, y, line, font="F1", size=size, color=color)
            y -= leading
        return y

    def bullets(self, x: float, y: float, items: list[str], width_chars: int, *, size: float = 10.0, color: str = TEXT_SOFT, leading: float = 13.2) -> float:
        for item in items:
            lines = wrap_text(item, width_chars)
            self.text(x, y, "-", font="F2", size=size, color=ACCENT)
            self.text(x + 12, y, lines[0], font="F1", size=size, color=color)
            for line in lines[1:]:
                y -= leading
                self.text(x + 12, y, line, font="F1", size=size, color=color)
            y -= leading
        return y


def render_page_one(builder: PdfBuilder) -> None:
    builder.start_page()

    left_x = MARGIN
    hero_width = 326
    photo_card_x = PAGE_WIDTH - MARGIN - 152
    photo_card_y = 588
    photo_card_w = 152
    photo_card_h = 210

    builder.text(left_x, 786, "PERFIL EJECUTIVO", font="F2", size=9.0, color=ACCENT)

    name_y = 758
    for line in ["Gerardo Misael", "Donovarros Belderrain"]:
        builder.text(left_x, name_y, line, font="F3", size=24.0, color=TEXT)
        name_y -= 26

    headline_y = 700
    for line in wrap_text(DATA["headline"], 42):
        builder.text(left_x, headline_y, line, font="F2", size=14.2, color=ACCENT)
        headline_y -= 19

    subtitle_y = headline_y - 6
    subtitle_y = builder.paragraph(left_x, subtitle_y, DATA["subheadline"], 62, size=10.8, leading=14.6)
    body_y = builder.paragraph(left_x, subtitle_y - 6, DATA["summary"], 64, size=10.3, leading=13.8)

    button_y = body_y - 28
    builder.button(left_x, button_y, 126, 34, "Correo", DATA["email_href"], primary=True)
    builder.button(left_x + 136, button_y, 110, 34, "Teléfono", DATA["phone_href"])
    builder.button(left_x + 256, button_y, 124, 34, DATA["web_label"], DATA["web_href"])

    builder.rect(photo_card_x, photo_card_y, photo_card_w, photo_card_h, fill=BG_CARD, stroke=LINE)
    builder.text(photo_card_x + 16, photo_card_y + photo_card_h - 22, "Perfil ejecutivo", font="F2", size=8.0, color=MUTED)
    builder.text(photo_card_x + 16, photo_card_y + photo_card_h - 38, DATA["location"], font="F2", size=10.0, color=TEXT)
    builder.rect(photo_card_x + 14, photo_card_y + 18, photo_card_w - 28, 150, fill=BG_SOFT, stroke=LINE)
    builder.image_jpeg(photo_card_x + 16, photo_card_y + 20, photo_card_w - 32, 146)

    results_y = 468
    builder.text(left_x, results_y, "RESULTADOS", font="F2", size=8.6, color=ACCENT)
    builder.text(left_x, results_y - 18, DATA["result_title"], font="F2", size=17.0, color=TEXT)
    builder.paragraph(left_x, results_y - 42, DATA["result_intro"], 70, size=9.8, leading=13.2)

    card_w = (CONTENT_WIDTH - 14) / 2
    card_h = 96
    first_row_y = 304
    second_row_y = 194
    positions = [
        (left_x, first_row_y),
        (left_x + card_w + 14, first_row_y),
        (left_x, second_row_y),
        (left_x + card_w + 14, second_row_y),
    ]

    for item, (x, y) in zip(DATA["results"], positions):
        builder.rect(x, y, card_w, card_h, fill=BG_CARD, stroke=LINE)
        builder.text(x + 16, y + 66, item["value"], font="F3", size=22.0, color=TEXT)
        builder.text(x + 92, y + 68, item["label"], font="F2", size=9.0, color=ACCENT)
        builder.paragraph(x + 16, y + 42, item["detail"], 36, size=9.2, leading=12.4)

    bottom_y = 62
    bottom_h = 104
    left_card_w = 252
    right_card_x = left_x + left_card_w + 18
    right_card_w = CONTENT_WIDTH - left_card_w - 18

    builder.rect(left_x, bottom_y, left_card_w, bottom_h, fill=BG_CARD, stroke=LINE)
    title_y = builder.block_title(left_x + 16, bottom_y + bottom_h - 20, "Storyselling", "Narrativa que sí ayuda a vender.", title_size=14.0)
    builder.paragraph(left_x + 16, title_y - 4, DATA["storyselling"], 34, size=9.2, leading=12.2)

    builder.rect(right_card_x, bottom_y, right_card_w, bottom_h, fill=BG_CARD, stroke=LINE)
    title_y = builder.block_title(right_card_x + 16, bottom_y + bottom_h - 20, "Sectores", "Experiencia multisectorial.", title_size=14.0)
    builder.bullets(right_card_x + 16, title_y - 2, DATA["sectors"][:4], 30, size=9.0, leading=11.8)


def render_page_two(builder: PdfBuilder) -> None:
    builder.start_page()

    builder.text(MARGIN, 786, DATA["display_name"], font="F3", size=18.0, color=TEXT)
    builder.text(MARGIN, 768, "TRAYECTORIA, CAPACIDADES Y FORMACIÓN", font="F2", size=8.4, color=ACCENT)

    left_x = MARGIN
    right_x = 372
    timeline_w = 300
    side_w = PAGE_WIDTH - MARGIN - right_x

    builder.rect(left_x, 76, timeline_w, 664, fill=BG_CARD, stroke=LINE)
    y = builder.block_title(left_x + 16, 718, "Trayectoria", "Experiencia construyendo crecimiento real.", title_size=16.0)
    y -= 6

    for item in DATA["experience"]:
        builder.line(left_x + 22, y + 6, left_x + 22, y - 78, color=ACCENT_SOFT, width=1.4)
        builder.rect(left_x + 19, y - 1, 6, 6, fill=ACCENT_SOFT, stroke=ACCENT_SOFT)
        builder.text(left_x + 36, y, item.role, font="F2", size=11.2, color=TEXT)
        builder.text(left_x + 208, y, item.period, font="F2", size=8.6, color=MUTED)
        y -= 13
        builder.text(left_x + 36, y, item.company, font="F2", size=9.6, color=ACCENT)
        y -= 16
        y = builder.paragraph(left_x + 36, y, item.summary, 40, size=9.1, leading=11.8)
        y = builder.bullets(left_x + 36, y - 2, item.bullets, 39, size=8.8, leading=11.4)
        y -= 4

    top_card_y = 532
    card_gap = 14
    small_card_h = 94
    medium_card_h = 142
    bottom_card_h = 134

    builder.rect(right_x, top_card_y, side_w, small_card_h, fill=BG_CARD, stroke=LINE)
    y = builder.block_title(right_x + 14, top_card_y + small_card_h - 18, "Capacidades", "Lo que conecto para mover negocio.", title_size=13.0)
    builder.bullets(right_x + 14, y - 4, DATA["skills"][:4], 22, size=8.9, leading=11.2)

    second_y = top_card_y - card_gap - medium_card_h
    builder.rect(right_x, second_y, side_w, medium_card_h, fill=BG_CARD, stroke=LINE)
    y = builder.block_title(right_x + 14, second_y + medium_card_h - 18, "Herramientas", "Tecnología útil para vender y operar mejor.", title_size=13.0)
    builder.bullets(right_x + 14, y - 4, DATA["tools"], 20, size=8.9, leading=11.0)

    third_y = second_y - card_gap - bottom_card_h
    builder.rect(right_x, third_y, side_w, bottom_card_h, fill=BG_CARD, stroke=LINE)
    y = builder.block_title(right_x + 14, third_y + bottom_card_h - 18, "Formación", "Base académica y ejecutiva.", title_size=13.0)
    builder.bullets(right_x + 14, y - 4, DATA["education"], 22, size=8.6, leading=10.8)

    footer_y = 78
    builder.rect(right_x, footer_y, side_w, 96, fill=BG_CARD, stroke=LINE)
    builder.text(right_x + 14, footer_y + 68, "CONTACTO", font="F2", size=8.6, color=ACCENT)
    builder.text(right_x + 14, footer_y + 48, DATA["full_name"], font="F2", size=11.0, color=TEXT)
    builder.text(right_x + 14, footer_y + 31, DATA["location"], font="F1", size=9.2, color=TEXT_SOFT)
    builder.text(right_x + 14, footer_y + 17, DATA["email"], font="F1", size=9.2, color=TEXT_SOFT)
    builder.text(right_x + 14, footer_y + 3, DATA["phone"], font="F1", size=9.2, color=TEXT_SOFT)
    builder.link(right_x + 14, footer_y + 12, 120, 12, DATA["email_href"])
    builder.link(right_x + 14, footer_y - 2, 88, 12, DATA["phone_href"])

    builder.button(MARGIN, 20, 150, 28, DATA["web_label"], DATA["web_href"], primary=True)
    builder.button(MARGIN + 160, 20, 126, 28, "Enviar correo", DATA["email_href"])


def build_pdf_bytes(pages: list[PageState], image_data: bytes, image_w: int, image_h: int) -> bytes:
    objects: list[bytes] = []

    def add_object(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    font_regular = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font_bold = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    font_heavy = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    image_obj = add_object(
        (
            f"<< /Type /XObject /Subtype /Image /Width {image_w} /Height {image_h} "
            f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(image_data)} >>\nstream\n"
        ).encode("cp1252")
        + image_data
        + b"\nendstream"
    )

    content_ids: list[int] = []
    page_ids: list[int] = [0] * len(pages)
    annot_id_lists: list[list[int]] = []

    for page in pages:
        stream = "\n".join(page.commands)
        stream_bytes = stream.encode("cp1252", errors="replace")
        content_ids.append(
            add_object(f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("cp1252") + stream_bytes + b"\nendstream")
        )

    for page in pages:
        current_annots: list[int] = []
        for x1, y1, x2, y2, uri in page.annotations:
            annot = (
                f"<< /Type /Annot /Subtype /Link /Rect [{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f}] "
                f"/Border [0 0 0] /A << /S /URI /URI ({pdf_escape(uri)}) >> >>"
            ).encode("cp1252", errors="replace")
            current_annots.append(add_object(annot))
        annot_id_lists.append(current_annots)

    pages_id = add_object(b"")

    for index, content_id in enumerate(content_ids):
        annots = annot_id_lists[index]
        annots_part = ""
        if annots:
            annots_part = "/Annots [" + " ".join(f"{annot_id} 0 R" for annot_id in annots) + "] "
        page_obj = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_WIDTH:.0f} {PAGE_HEIGHT:.0f}] "
            f"/Resources << /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R /F3 {font_heavy} 0 R >> "
            f"/XObject << /Im1 {image_obj} 0 R >> >> {annots_part}/Contents {content_id} 0 R >>"
        ).encode("cp1252")
        page_ids[index] = add_object(page_obj)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("cp1252")
    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("cp1252"))

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("cp1252"))
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("cp1252"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("cp1252"))

    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("cp1252")
    )
    return bytes(output)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not PHOTO_PATH.exists():
        raise FileNotFoundError(f"No encontré la foto en {PHOTO_PATH}")

    builder = PdfBuilder()
    render_page_one(builder)
    render_page_two(builder)
    builder.finish()

    image_data = PHOTO_PATH.read_bytes()
    image_w, image_h = jpeg_dimensions(PHOTO_PATH)
    pdf_bytes = build_pdf_bytes(builder.pages, image_data, image_w, image_h)
    OUTPUT_PDF.write_bytes(pdf_bytes)
    print(OUTPUT_PDF)


if __name__ == "__main__":
    main()
