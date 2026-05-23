from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
COURSE_SLUG = "course_holobiomagnetismo_2021"
SOURCE_BASE = ROOT / "data" / "processed_library" / "Salud" / "curso-holobiomagnetismo-2021"
SOURCE_DIR = SOURCE_BASE / "sources"
OUTPUT_BASE = ROOT / "data" / "knowledge_units" / COURSE_SLUG
MANUAL_PDF = ROOT / "data" / "manuals_raws" / "HOLOBIOMAGNETISMO.pdf"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_pdf_page(text: str) -> str:
    text = text.replace("\u00a0", " ")
    lines = [line.strip() for line in text.splitlines()]
    cleaned: list[str] = []
    for line in lines:
        if not line:
            continue
        if re.fullmatch(r"ALEJANDRO LAV[IÍ]N\s+\d+", line, flags=re.IGNORECASE):
            continue
        if re.fullmatch(r"\d+", line):
            continue
        cleaned.append(line)
    merged = "\n".join(cleaned)
    merged = re.sub(r"[ \t]+", " ", merged)
    merged = re.sub(r"\n{3,}", "\n\n", merged)
    return merged.strip()


def extract_pages(pages: list[str], start: int, end: int) -> str:
    chunks = []
    for page_number in range(start, end + 1):
        idx = page_number - 1
        if idx < 0 or idx >= len(pages):
            continue
        page_text = clean_pdf_page(pages[idx])
        if page_text:
            chunks.append(f"[Página {page_number}]\n{page_text}")
    return "\n\n".join(chunks).strip()


def split_transcript_modules(text: str) -> list[dict]:
    pattern = re.compile(
        r"\n=+\nLÍNEA: .*?\nCURSO: .*?\nMÓDULO: (\d+)\nFECHA DE PROCESO: (.*?)\n=+\n",
        flags=re.DOTALL,
    )
    matches = list(pattern.finditer(text))
    modules = []
    for index, match in enumerate(matches):
        module_number = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        modules.append(
            {
                "module_number": module_number,
                "fecha_proceso": match.group(2).strip(),
                "raw_text": body,
            }
        )
    return modules


def normalize_space(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def copy_source(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def build_clean_transcript(module_summaries: list[dict], ambiguities: list[str]) -> str:
    lines = [
        "CURSO: Holobiomagnetismo 2021",
        "DOCUMENTO: clean_transcript.txt",
        "",
        "Esta es una versión depurada y condensada de la transcripción.",
        "Se eliminaron saludos sociales, bromas irrelevantes, repeticiones, muletillas, indicaciones técnicas de cámara y ruido de clase en vivo.",
        "Se conservaron las ideas académicas, la lógica terapéutica, los ejemplos clínicos y la parte procedural útil.",
        "",
    ]
    for item in module_summaries:
        lines.append(f"MÓDULO {item['module_number']}: {item['title']}")
        lines.append(f"Foco principal: {item['focus']}")
        lines.append("Contenido depurado:")
        for bullet in item["clean_notes"]:
            lines.append(f"- {bullet}")
        lines.append("")
    lines.append("AMBIGÜEDADES DE LA TRANSCRIPCIÓN")
    for ambiguity in ambiguities:
        lines.append(f"- {ambiguity}")
    return "\n".join(lines)


def build_manual_extracted(sections: list[dict]) -> str:
    lines = [
        "CURSO: Holobiomagnetismo 2021",
        "DOCUMENTO: manual_extracted.txt",
        "",
        "Versión estructurada del manual extraído desde PDF.",
        "Se organizaron únicamente los apartados que aportan valor académico, terapéutico o procedural al curso.",
        "",
    ]
    for section in sections:
        lines.append(section["title"].upper())
        lines.append(f"Fuentes: {', '.join(section['source_pages'])}")
        lines.append(section["summary"])
        lines.append("")
        if section.get("highlights"):
            lines.append("Puntos útiles:")
            for bullet in section["highlights"]:
                lines.append(f"- {bullet}")
            lines.append("")
    return "\n".join(lines)


def build_merged_clean_content(overview: dict, module_summaries: list[dict], sections: list[dict]) -> str:
    lines = [
        "CURSO: Holobiomagnetismo 2021",
        "DOCUMENTO: merged_clean_content.txt",
        "",
        "Versión unificada y depurada del curso a partir de manual + transcripción.",
        "",
        "PANORAMA GENERAL",
        overview["description"],
        "",
        "EJES PRINCIPALES",
    ]
    for axis in overview["main_axes"]:
        lines.append(f"- {axis}")
    lines.append("")
    lines.append("DESARROLLO DIDÁCTICO POR MÓDULO")
    for item in module_summaries:
        lines.append(f"- Módulo {item['module_number']}: {item['title']} | {item['focus']}")
    lines.append("")
    lines.append("CONSOLIDACIÓN TEMÁTICA")
    for section in sections:
        lines.append(f"{section['title']}: {section['summary']}")
    lines.append("")
    lines.append("PRINCIPIOS OPERATIVOS CONSOLIDADOS")
    consolidated = [
        "La entrevista inicial se organiza por síntomas físicos y psicoemocionales, con características, frecuencia, fecha aproximada de origen y factores que agravan o inhiben.",
        "El curso propone no quedarse en el síntoma aislado: el terapeuta debe buscar un estado energético subyacente, patrones, recurrencias y cronología clínica.",
        "El rastreo puede hacerse de manera presencial o por sustitución temporal, usando comandos claros de búsqueda y verificación.",
        "La lógica clínica integra biomagnetismo, medicina tradicional china, lectura de 5 elementos, frecuencias biomagnéticas, homeopatía, flores de Bach, sales de Schüssler y protocolos emocionales.",
        "La intervención emocional más explícita del manual es EFT Pro, con entrevista, trance, viaje temporal, sintonización del conflicto, tapping, cierre y recalibración.",
        "El curso distingue entre conocimiento enseñable, criterio terapéutico y secuencias operativas condensadas para la práctica.",
    ]
    for bullet in consolidated:
        lines.append(f"- {bullet}")
    return "\n".join(lines)


def main() -> None:
    transcript_text = read_text(SOURCE_DIR / "transcripcion_completa.txt")
    manual_text = read_text(SOURCE_DIR / "Holobiomagnetismo_2021.txt")
    manifest = json.loads(read_text(SOURCE_BASE / "course_manifest.json"))
    pages = manual_text.split("\f")
    transcript_modules = split_transcript_modules(transcript_text)

    module_summaries = [
        {
            "module_number": 1,
            "title": "Apertura clínica del curso y entrevista base",
            "focus": "Presentación del enfoque holobiomagnético mediante una demostración y la estructura de la entrevista inicial.",
            "clean_notes": [
                "El curso se presenta como una expansión del biomagnetismo puro hacia una lectura bioenergética, mental y emocional del paciente.",
                "El docente plantea que el terapeuta debe preguntar primero qué síntomas desea trabajar la persona y diferenciar entre síntomas físicos y psicoemocionales.",
                "A cada síntoma se le piden características concretas: tipo de dolor o sensación, localización exacta y forma en que se manifiesta.",
                "La frecuencia debe registrarse por día, semana o recurrencia anual cuando aplique.",
                "La fecha aproximada de origen se busca por rangos de vida si la persona no recuerda una fecha exacta.",
                "El curso insiste en que esta investigación ya forma parte de la terapia porque activa introspección y memoria clínica.",
                "Se muestra un ejemplo de lectura energética donde un síntoma actual puede ser solo el producto visible de un desequilibrio energético más profundo.",
                "El caso ejemplifica que aunque un órgano haya sido retirado físicamente, su molde energético puede seguir siendo evaluable.",
            ],
            "sources": ["transcripción módulo 1", "manual páginas 44-45", "manual páginas 160-165"],
        },
        {
            "module_number": 2,
            "title": "Teletransmisión y práctica a distancia",
            "focus": "Demostración del trabajo a distancia y del concepto de transmisión de información terapéutica.",
            "clean_notes": [
                "Se introduce una segunda práctica orientada a transmitir información a distancia.",
                "El docente presenta la idea de teletransmisión como una operación cibernética y mental, no como simple imaginación informal.",
                "La práctica refuerza que el curso opera con comandos de búsqueda y verificación antes de instalar información.",
                "La sesión sirve de puente entre la demostración clínica inicial y la teoría de cibertelepatía del manual.",
            ],
            "sources": ["transcripción módulo 2", "manual páginas 26-29", "manual página 64"],
        },
        {
            "module_number": 3,
            "title": "Definición de holobiomagnetismo y capas del cuerpo",
            "focus": "Fundamentos del curso y diferencia entre biomagnetismo puro y holobiomagnetismo.",
            "clean_notes": [
                "Holobiomagnetismo se presenta como una integración donde el campo magnético dialoga no solo con el cuerpo físico sino con dimensiones más sutiles o informacionales.",
                "Se retoma el biomagnetismo previo, pero se amplía hacia una comprensión de cuerpos, campos y niveles no reducibles al tejido orgánico.",
                "La palabra 'holo' se usa para señalar totalidad e integración.",
                "El curso busca que el terapeuta piense al paciente como un sistema físico, psicológico y bioenergético al mismo tiempo.",
            ],
            "sources": ["transcripción módulo 3", "manual páginas 9-13", "manual páginas 26-29"],
        },
        {
            "module_number": 4,
            "title": "Campos magnéticos, toroides y molde energético",
            "focus": "Explicación del magnetismo bipolar y de cómo los imanes interactúan con el molde sutil del cuerpo.",
            "clean_notes": [
                "Se explica que todo imán genera un campo bipolar y que el curso trabaja con esa polaridad en vez de asumir monopolos operativos.",
                "El docente vincula el campo magnético con la modificación del proceso bioenergético o molde sutil del cuerpo.",
                "El toroide aparece como figura clave para imaginar la dinámica del campo alrededor del organismo o de los puntos tratados.",
                "El campo magnético se plantea como medio de organización e influencia sobre patrones de información corporal.",
            ],
            "sources": ["transcripción módulo 4", "manual páginas 28-29"],
        },
        {
            "module_number": 5,
            "title": "Anatomía básica, área de rastreo y ficha de control",
            "focus": "Uso del manual, revisión anatómica y formato de entrevista/consentimiento.",
            "clean_notes": [
                "Se corrige el uso de versiones antiguas del manual y se pide trabajar con la versión vigente.",
                "El curso utiliza referencias anatómicas básicas para orientar el rastreo y la ubicación posterior de pares o puntos.",
                "El área de rastreo incorpora autorización informada y una ficha de preguntas de control.",
                "La ficha distingue entre síntomas físicos y psicoemocionales y solicita características, origen, frecuencia y factores inhibidores o estresores.",
                "El formato de control registra además embarazo, marcapasos, quimio/radioterapia, transfusiones, trasplantes y cirugías.",
            ],
            "sources": ["transcripción módulo 5", "manual páginas 36-45"],
        },
        {
            "module_number": 6,
            "title": "Microbios, pares biomagnéticos y secuencia de búsqueda",
            "focus": "Transición desde microbiología y pares hacia un rastreo ordenado.",
            "clean_notes": [
                "Se cierra el bloque de microbios y se pasa a imanes y pares biomagnéticos.",
                "El docente explica cómo programar la búsqueda para que el supraconsciente manifieste los agentes o pares necesarios.",
                "La búsqueda se organiza por categorías: bacterias, parásitos, hongos, virus y priones; después por pares biomagnéticos.",
                "El rastreo de pares se recorre por región, zona, bloque y número de par.",
                "La secuencia operativa básica concluye con la colocación de imanes durante 20 minutos y su retiro.",
            ],
            "sources": ["transcripción módulo 6", "manual páginas 46-64", "manual página 63"],
        },
        {
            "module_number": 7,
            "title": "Filosofía de medicina tradicional china",
            "focus": "Bases filosóficas y energéticas que sostienen la lectura terapéutica del curso.",
            "clean_notes": [
                "El docente presenta la medicina tradicional china como una filosofía de vida además de una medicina energética.",
                "Se enfatiza el Qi como fuerza vital organizada que estructura y dinamiza la materia viva.",
                "Aparecen los '7 dragones' o pasiones como perturbadores del sistema energético.",
                "Se plantea que la terapia no busca solo un alivio local, sino un reordenamiento de la fuerza vital y sus leyes.",
                "La práctica con agujas no es central aquí; el curso traduce esa lógica a un trabajo con imanes y biomagnetopuntura.",
            ],
            "sources": ["transcripción módulo 7", "manual páginas 160-162"],
        },
        {
            "module_number": 8,
            "title": "Mecánicas del Qi y emoción",
            "focus": "Cómo las emociones modifican el flujo energético y preparan la lectura de los 5 elementos.",
            "clean_notes": [
                "El miedo hace descender el Qi y suele sentirse corporalmente como contracción, sequedad o urgencia urinaria.",
                "El enojo hace ascender el Qi hacia la cabeza y se asocia con calor, tensión y enrojecimiento.",
                "La tristeza dispersa el Qi; la reflexión lo concentra; la alegría lo armoniza; la ansiedad lo distorsiona.",
                "El curso usa estas dinámicas como guía de observación clínica para relacionar emoción, sensación corporal y sistema energético.",
            ],
            "sources": ["transcripción módulo 8", "manual página 162"],
        },
        {
            "module_number": 9,
            "title": "Cinco elementos I: agua y madera",
            "focus": "Correspondencias clínicas y simbólicas de agua y madera.",
            "clean_notes": [
                "El elemento agua se vincula con riñón, vejiga, ancestros, vida intrauterina, oído, huesos y médula.",
                "El elemento madera se vincula con dirección, decisión y movimiento hacia lo que la persona quiere.",
                "El docente utiliza el rastreo de 5 elementos para leer estados globales y no solo síntomas superficiales.",
                "Las correspondencias elementales sirven para orientar preguntas y comprender la emoción predominante detrás del caso.",
            ],
            "sources": ["transcripción módulo 9", "manual páginas 163-190"],
        },
        {
            "module_number": 10,
            "title": "Cinco elementos II: fuego, tierra y metal",
            "focus": "Expresión, vínculo y relaciones sociales dentro de la lectura energética.",
            "clean_notes": [
                "El fuego se vincula con corazón, mente consciente, ideas, expresión y espíritu (Shen).",
                "La tierra se asocia al vínculo, la reflexión y la centralidad organizativa del sistema.",
                "El metal se relaciona con conexión social, círculos elegidos y la figura del padre.",
                "El curso integra estas asociaciones como criterios interpretativos, no como equivalencias aisladas o automáticas.",
            ],
            "sources": ["transcripción módulo 10", "manual páginas 163-190"],
        },
        {
            "module_number": 11,
            "title": "Caso guiado: miomas, sustitución y lectura remota",
            "focus": "Demostración clínica aplicada con sustituto temporal y rastreo de puntos.",
            "clean_notes": [
                "Se trabaja un caso real de miomas por vía remota.",
                "El docente inicia con preguntas clínicas antes de entrar al rastreo para no convertir la técnica en una secuencia ciega.",
                "Se utiliza sustituto temporal para representar a la consultante a distancia.",
                "El caso muestra cómo integrar comandos de búsqueda, lectura de puntos y criterio terapéutico sobre el caso.",
            ],
            "sources": ["transcripción módulo 11", "manual página 513"],
        },
        {
            "module_number": 12,
            "title": "Continuación de la práctica remota y cierre operativo",
            "focus": "Continuidad del trabajo con sustitución y comandos de búsqueda en caso real.",
            "clean_notes": [
                "La última parte continúa el trabajo de sustitución temporal y ubicación de puntos.",
                "Consolida el uso de comandos de búsqueda y de instalación de información durante 30 minutos.",
                "Funciona como cierre práctico del curso y como aplicación final de los bloques teóricos anteriores.",
            ],
            "sources": ["transcripción módulo 12", "manual página 513"],
        },
    ]

    overview = {
        "course_id": "curso-holobiomagnetismo-2021",
        "course_name": "Holobiomagnetismo 2021",
        "linea": "Salud",
        "tipo": "Curso",
        "edition_note": "El curso está catalogado como 2021, pero el manual disponible indica '1era Edición, 2020'.",
        "description": (
            "Curso terapéutico que amplía el biomagnetismo puro hacia una integración bioenergética, "
            "mental y emocional. Enseña entrevista clínica orientada al rastreo, lectura por 5 elementos, "
            "uso de sustitución temporal, trabajo con meridianos, frecuencias complementarias y protocolos "
            "emocionales como EFT Pro."
        ),
        "main_axes": [
            "Holobiomagnetismo como integración físico-psicoemocional-bioenergética.",
            "Entrevista clínica orientada por síntomas, cronología y factores relevantes.",
            "Cibertelepatía, sustitución temporal y trabajo terapéutico a distancia.",
            "Medicina tradicional china: Qi, 5 elementos, meridianos y puntos.",
            "Frecuencias biomagnéticas, bioenergéticas y apoyos complementarios.",
            "Protocolos emocionales y desarticulación de impactos emocionales.",
        ],
        "detected_modules": [item["module_number"] for item in module_summaries],
        "source_files_used": [
            "sources/transcripcion_completa.txt",
            "sources/Holobiomagnetismo_2021.txt",
            "sources/index_modulos.txt",
            "data/manuals_raws/HOLOBIOMAGNETISMO.pdf",
        ],
    }

    concepts = [
        {
            "id": "concept_holobiomagnetismo",
            "termino": "Holobiomagnetismo",
            "aliases": ["Holo biomagnetismo", "curso holobiomagnético"],
            "definicion": "Integración del biomagnetismo con una lectura bioenergética, mental y emocional del paciente.",
            "explicacion_simple": "No se queda solo en microbios y pH; mira al cuerpo como un sistema físico, psicológico y energético.",
            "explicacion_extendida": "En el curso, holobiomagnetismo se presenta como una expansión del biomagnetismo puro. Los campos magnéticos no solo dialogan con el tejido orgánico, sino con moldes energéticos, meridianos, emociones y procesos de información corporal.",
            "modulo o tema": "Módulos 1, 3 y 4",
            "fuente_principal": "transcripción módulos 1, 3 y 4",
            "fuente_secundaria": "manual páginas 9-13",
        },
        {
            "id": "concept_biomagnetopuntura",
            "termino": "Biomagnetopuntura",
            "aliases": ["Biomagneto puntura"],
            "definicion": "Uso de imanes a manera de agujas para estimular corrientes energéticas en el cuerpo.",
            "explicacion_simple": "Es aplicar la lógica de la acupuntura con imanes en lugar de agujas.",
            "explicacion_extendida": "El docente la presenta como una forma de integrar medicina tradicional china al biomagnetismo. En vez de trabajar solo con agujas o plantas, se usan imanes para influir sobre el flujo energético y modular estados emocionales y corporales.",
            "modulo o tema": "Módulo 1; medicina tradicional china",
            "fuente_principal": "transcripción módulo 1",
            "fuente_secundaria": "manual páginas 160-214",
        },
        {
            "id": "concept_cibertelepatia",
            "termino": "Cibertelepatía",
            "aliases": ["Ciber-telepatía", "Teletransmisión"],
            "definicion": "Marco mental y cibernético para recibir o transmitir información entre mente universal y mente local.",
            "explicacion_simple": "Es la base conceptual del trabajo terapéutico a distancia y del uso de sustitutos.",
            "explicacion_extendida": "El manual la vincula con capas mentales, retroalimentación y recepción/emisión psíquica de información. En el curso se convierte en una justificación práctica del rastreo remoto y de la instalación de información sin contacto físico directo.",
            "modulo o tema": "Módulo 2; Cibertelepatía",
            "fuente_principal": "manual páginas 26-29",
            "fuente_secundaria": "transcripción módulo 2",
        },
        {
            "id": "concept_sustituto_temporal",
            "termino": "Sustituto temporal",
            "aliases": ["Programa de sustitución", "Sustitución a distancia"],
            "definicion": "Procedimiento por el cual una persona representa temporalmente a otra para manifestar respuestas en el rastreo.",
            "explicacion_simple": "Permite trabajar a distancia usando a otra persona como testigo o representante.",
            "explicacion_extendida": "El manual ofrece una fórmula verbal de aceptación y una comprobación de identidad. El curso lo usa en casos remotos para verificar respuestas musculares o energéticas y después aplicar búsquedas, puntos o instalación de información.",
            "modulo o tema": "Módulos 2, 11 y 12",
            "fuente_principal": "manual páginas 64 y 513",
            "fuente_secundaria": "transcripción módulos 11 y 12",
        },
        {
            "id": "concept_entrevista_rastreo",
            "termino": "Entrevista de rastreo",
            "aliases": ["Historia clínica de rastreo", "Ficha de control"],
            "definicion": "Secuencia de preguntas iniciales para convertir síntomas vagos en datos clínicos operables.",
            "explicacion_simple": "Sirve para traducir 'me siento mal' en información que se puede rastrear y pensar terapéuticamente.",
            "explicacion_extendida": "El curso pide distinguir entre síntomas físicos y psicoemocionales, registrar características, frecuencia, fecha aproximada de origen y factores estresores o inhibidores. Esta entrevista no es un trámite: es el inicio de la labor terapéutica.",
            "modulo o tema": "Módulos 1 y 5",
            "fuente_principal": "transcripción módulo 1",
            "fuente_secundaria": "manual páginas 44-45",
        },
        {
            "id": "concept_molde_energetico",
            "termino": "Molde energético",
            "aliases": ["Molde sutil", "Campo del órgano"],
            "definicion": "Estructura energética que se mantiene aunque la parte física del órgano ya no esté presente.",
            "explicacion_simple": "Un órgano puede faltar físicamente y aun así seguir teniendo un patrón energético evaluable.",
            "explicacion_extendida": "El docente lo explica con el caso de la vesícula extirpada: aunque el órgano ya no esté, el molde energético sigue mostrando frío o desequilibrio. Esto permite rastrear estados subyacentes más allá del cuerpo anatómico visible.",
            "modulo o tema": "Módulos 1 y 4",
            "fuente_principal": "transcripción módulo 1",
            "fuente_secundaria": "transcripción módulo 4",
        },
        {
            "id": "concept_qi",
            "termino": "Qi",
            "aliases": ["Chi"],
            "definicion": "Fuerza vital organizada que da movimiento, forma y dinamismo a la materia viva.",
            "explicacion_simple": "Es la energía funcional que sostiene procesos, forma y movimiento en el organismo.",
            "explicacion_extendida": "El manual presenta el Qi como fuerza que polariza Yin-Yang, sostiene el macroverso y microverso y da leyes al movimiento. La transcripción lo vuelve clínico al describir cómo sube, baja, se concentra, se dispersa o se distorsiona según la emoción.",
            "modulo o tema": "Módulos 7 y 8",
            "fuente_principal": "manual páginas 161-162",
            "fuente_secundaria": "transcripción módulo 8",
        },
        {
            "id": "concept_cinco_elementos",
            "termino": "Cinco elementos",
            "aliases": ["5 elementos", "Wu Xing"],
            "definicion": "Modelo de relación entre órganos, emociones, funciones y dinámicas de generación y control.",
            "explicacion_simple": "Sirve para leer patrones energéticos, emocionales y corporales dentro de un mismo mapa.",
            "explicacion_extendida": "En el curso, los cinco elementos no se enseñan solo como tabla simbólica, sino como una herramienta de interpretación. Agua, madera, fuego, tierra y metal se conectan con órganos, emociones, relaciones, decisiones, expresión y ancestros.",
            "modulo o tema": "Módulos 8, 9 y 10",
            "fuente_principal": "manual páginas 163-190",
            "fuente_secundaria": "transcripción módulos 8, 9 y 10",
        },
        {
            "id": "concept_yin_yang",
            "termino": "Yin / Yang",
            "aliases": ["Yin Yang"],
            "definicion": "Polaridades complementarias cuya relación explica equilibrio, exceso, deficiencia y profundidad del desequilibrio.",
            "explicacion_simple": "Ayuda a distinguir si algo está en exceso, insuficiencia, calor o frío.",
            "explicacion_extendida": "El manual relaciona Yin/Yang con las fases de la enfermedad, calor por insuficiencia y equilibrio funcional. Esto sirve de base para el rastreo específico de órganos y del Qi de los meridianos.",
            "modulo o tema": "Cinco elementos y principios energéticos",
            "fuente_principal": "manual página 165",
            "fuente_secundaria": "transcripción módulo 1",
        },
        {
            "id": "concept_meridianos",
            "termino": "Meridianos",
            "aliases": ["Canales", "14 meridianos"],
            "definicion": "Circuitos por donde circula el Qi y cuya alteración se lee como exceso, deficiencia, estasis, calor o frío.",
            "explicacion_simple": "Son rutas energéticas que ayudan a localizar y entender el desequilibrio.",
            "explicacion_extendida": "El curso trabaja los 14 meridianos y después los 362 puntos. La transcripción usa esta lógica para leer chi de vesícula biliar, corazón, pulmón e intestino grueso y vincularlo con un estado energético global.",
            "modulo o tema": "Módulos 8-10; meridianos",
            "fuente_principal": "manual páginas 191-326",
            "fuente_secundaria": "transcripción módulo 1",
        },
        {
            "id": "concept_homologacion_puntos",
            "termino": "Homologación de puntos",
            "aliases": ["Puntos equivalentes", "Mapa de puntos"],
            "definicion": "Relación operativa entre la nomenclatura de biomagnetismo y la de medicina tradicional china.",
            "explicacion_simple": "Permite pasar del lenguaje de puntos biomagnéticos al lenguaje de puntos MTC.",
            "explicacion_extendida": "El manual dedica una sección a homologar puntos y a ordenar puntos yuan, luo, tonificación, sedación y cruces. Esta capa hace posible el uso terapéutico de biomagnetopuntura y del rastreo de puntos remotos.",
            "modulo o tema": "Los 362 puntos y homologación",
            "fuente_principal": "manual páginas 214-326",
            "fuente_secundaria": "transcripción módulos 11 y 12",
        },
        {
            "id": "concept_frecuencias_biomagneticas",
            "termino": "Frecuencias biomagnéticas",
            "aliases": ["Campos magnéticos pulsantes", "CMP", "Bio Vortex"],
            "definicion": "Uso de campos magnéticos pulsantes como herramienta complementaria para modular dolor, inflamación y regeneración.",
            "explicacion_simple": "Son frecuencias magnéticas usadas como apoyo físico y regulador.",
            "explicacion_extendida": "El manual introduce el uso de CMP y un dispositivo en forma de vórtice para producir un campo electromagnético pulsante con fines de equilibrio corporal y apoyo regenerativo.",
            "modulo o tema": "Frecuencias biomagnéticas",
            "fuente_principal": "manual páginas 327-329",
            "fuente_secundaria": "manual página 512",
        },
        {
            "id": "concept_frecuencias_bioenergeticas",
            "termino": "Frecuencias bioenergéticas",
            "aliases": ["Patrones vibratorios"],
            "definicion": "Rastreo e instalación de remedios vibratorios como homeopatía, flores de Bach o sales de Schüssler.",
            "explicacion_simple": "Amplían el trabajo del curso con soportes vibratorios y no solo con pares e imanes.",
            "explicacion_extendida": "El curso incluye un rastreo estructurado para decidir si se necesita un policresto, un semipolicresto, una flor o una sal, con potencia, duración y validación de gestión.",
            "modulo o tema": "Frecuencias bioenergéticas",
            "fuente_principal": "manual páginas 363-365",
            "fuente_secundaria": "manual página 512",
        },
        {
            "id": "concept_homeopatia",
            "termino": "Farmacopea homeopática",
            "aliases": ["Policrestos", "Semipolicrestos"],
            "definicion": "Catálogo de remedios homeopáticos que el curso usa como soporte vibratorio complementario.",
            "explicacion_simple": "No se prescribe por repertorización clásica, sino por rastreo dentro del sistema del curso.",
            "explicacion_extendida": "El manual detalla remedios y sugiere una lógica de rastreo por bloques, potencia y tiempo. En la estructura del curso funciona como herramienta complementaria, no como eje único del tratamiento.",
            "modulo o tema": "Farmacopea homeopática",
            "fuente_principal": "manual páginas 375-452",
            "fuente_secundaria": "manual página 512",
        },
        {
            "id": "concept_flores_bach",
            "termino": "Flores de Bach",
            "aliases": ["Remedios florales de Bach"],
            "definicion": "Sistema floral orientado a desequilibrios psicoemocionales y de carácter.",
            "explicacion_simple": "En el curso se incorporan como apoyo emocional complementario elegido por rastreo.",
            "explicacion_extendida": "El manual explica su origen, sus categorías y la intención de aliviar miedo, impaciencia, angustia, incertidumbre, ira o confusión. Se integran a la ecuación terapéutica como soporte vibratorio.",
            "modulo o tema": "Flores de Bach",
            "fuente_principal": "manual páginas 453-494",
            "fuente_secundaria": "transcripción módulo 1",
        },
        {
            "id": "concept_sales_schussler",
            "termino": "Sales de Schüssler",
            "aliases": ["Sales de Schussler", "Sales tisulares"],
            "definicion": "Preparados homeopáticos derivados de sales minerales orientados al equilibrio funcional del organismo.",
            "explicacion_simple": "Se usan como apoyo para compensar desequilibrios funcionales detectados por rastreo.",
            "explicacion_extendida": "El manual describe 12 sales y las vincula con funciones orgánicas y síntomas. Dentro del curso, se integran al rastreo de frecuencias bioenergéticas como recurso complementario.",
            "modulo o tema": "Sales de Schüssler",
            "fuente_principal": "manual páginas 495-499",
            "fuente_secundaria": "manual página 512",
        },
        {
            "id": "concept_eft_pro",
            "termino": "EFT Pro",
            "aliases": ["EFT PRO", "Emotional Freedom Techniques Pro"],
            "definicion": "Protocolo de liberación emocional que integra EFT, hipnosis, PNL, biodescodificación y meridianos.",
            "explicacion_simple": "Es la principal secuencia emocional operativa del curso.",
            "explicacion_extendida": "EFT Pro organiza una entrevista detallada, inducción al trance, viaje temporal, sintonización del conflicto, tapping de ida y vuelta, cierre y recalibración. Busca liberar cuerpo mental y emocional con un acuerdo neurolingüístico y reencuadre constructivo.",
            "modulo o tema": "Protocolos emocionales",
            "fuente_principal": "manual páginas 501-505",
            "fuente_secundaria": "transcripción módulo 1",
        },
        {
            "id": "concept_holograma_impacto",
            "termino": "Holograma / impacto emocional",
            "aliases": ["Impacto emocional", "Conflicto emocional"],
            "definicion": "Evento o patrón emocional que debe rastrearse y desarticularse para restaurar armonía biodinámica.",
            "explicacion_simple": "Es la unidad de conflicto que el curso intenta localizar y desmontar.",
            "explicacion_extendida": "El condensado propone rastrear hologramas o impactos emocionales y luego precisar datos como recesión de edad, emoción-reacción, persona implicada, capa embrionaria, cromosoma, microbio, par biomagnético, chakra o meridiano.",
            "modulo o tema": "Protocolos emocionales y condensados",
            "fuente_principal": "manual páginas 508 y 511",
            "fuente_secundaria": "transcripción módulos 1 y 11",
        },
        {
            "id": "concept_comandos_busqueda",
            "termino": "Comandos de búsqueda",
            "aliases": ["Establecer búsqueda", "MS"],
            "definicion": "Fórmulas verbales para abrir el circuito bioenergético, definir la búsqueda y comprobar si el sistema sabe qué se está buscando.",
            "explicacion_simple": "Son frases operativas que estructuran cada rastreo del curso.",
            "explicacion_extendida": "El curso no rastrea de forma improvisada. Cada búsqueda inicia con una declaración del tipo 'Voy a hacer un rastreo…', seguida por una comprobación explícita. Esa disciplina aparece en rastreo de microbios, pares, frecuencias, impactos emocionales y sustitución.",
            "modulo o tema": "Rastreo operativo",
            "fuente_principal": "manual páginas 63, 511, 512 y 513",
            "fuente_secundaria": "transcripción módulos 1, 6, 11 y 12",
        },
        {
            "id": "concept_factor_psicoemocional",
            "termino": "Factor psicoemocional",
            "aliases": ["Síntoma psicoemocional", "Conflicto crítico"],
            "definicion": "Dimensión emocional o mental que acompaña, origina o sostiene un cuadro físico.",
            "explicacion_simple": "El curso trata lo psicoemocional como un dato clínico obligatorio, no opcional.",
            "explicacion_extendida": "La ficha de control separa síntomas físicos y psicoemocionales. El docente insiste en revisar origen, conflicto crítico, vida post-conflicto y emociones principales para entender la lógica del caso y liberar lo que está reprimido.",
            "modulo o tema": "Entrevista, EFT Pro y razonamiento terapéutico",
            "fuente_principal": "manual páginas 45 y 501-505",
            "fuente_secundaria": "transcripción módulos 1 y 11",
        },
    ]

    glossary = [
        {"termino": "Holobiomagnetismo", "definicion_corta": "Integración de biomagnetismo con lectura bioenergética, mental y emocional."},
        {"termino": "Biomagnetopuntura", "definicion_corta": "Uso de imanes como equivalente funcional de agujas sobre flujos energéticos."},
        {"termino": "Cibertelepatía", "definicion_corta": "Recepción y emisión psíquica de información dentro de un sistema de retroalimentación mental."},
        {"termino": "Sustituto temporal", "definicion_corta": "Persona que representa a otra para rastreo o tratamiento a distancia."},
        {"termino": "Qi", "definicion_corta": "Fuerza vital organizada que dinamiza el organismo."},
        {"termino": "Yin", "definicion_corta": "Polo de profundidad, sustancia o contención dentro del sistema energético."},
        {"termino": "Yang", "definicion_corta": "Polo de actividad, función o exteriorización dentro del sistema energético."},
        {"termino": "Cinco elementos", "definicion_corta": "Mapa relacional de órganos, emociones y funciones energéticas."},
        {"termino": "Meridiano", "definicion_corta": "Canal de circulación del Qi."},
        {"termino": "Exceso", "definicion_corta": "Demasiada actividad o flujo en un órgano o canal."},
        {"termino": "Deficiencia", "definicion_corta": "Insuficiencia funcional o energética."},
        {"termino": "Estasis", "definicion_corta": "Estancamiento del flujo."},
        {"termino": "Frío", "definicion_corta": "Estado de baja actividad o insuficiencia energética."},
        {"termino": "Calor", "definicion_corta": "Estado de hiperactividad o sobrecarga del sistema."},
        {"termino": "Frecuencias biomagnéticas", "definicion_corta": "Campos magnéticos pulsantes usados como apoyo terapéutico."},
        {"termino": "Frecuencias bioenergéticas", "definicion_corta": "Patrones vibratorios como homeopatía, flores o sales."},
        {"termino": "Policresto", "definicion_corta": "Remedio homeopático amplio dentro del rastreo del curso."},
        {"termino": "Flores de Bach", "definicion_corta": "Remedios florales orientados al desequilibrio psicoemocional."},
        {"termino": "Sales de Schüssler", "definicion_corta": "Preparados minerales homeopáticos para apoyo funcional."},
        {"termino": "EFT Pro", "definicion_corta": "Secuencia de liberación emocional con tapping, trance y reencuadre."},
        {"termino": "Holograma emocional", "definicion_corta": "Conflicto o impacto emocional a desarticular."},
        {"termino": "Comando de búsqueda", "definicion_corta": "Fórmula verbal para abrir, definir y comprobar el rastreo."},
    ]

    faq_candidates = [
        {
            "question": "¿Qué diferencia a holobiomagnetismo del biomagnetismo puro?",
            "answer": "Holobiomagnetismo amplía el biomagnetismo puro al integrar lectura bioenergética, emociones, medicina china, frecuencias complementarias y protocolos emocionales.",
            "source": ["transcripción módulos 1 y 3", "manual páginas 9-13"],
        },
        {
            "question": "¿El curso trabaja solo síntomas físicos?",
            "answer": "No. Pide revisar tanto síntomas físicos como psicoemocionales y convertirlos en información concreta para la entrevista y el rastreo.",
            "source": ["transcripción módulo 1", "manual página 45"],
        },
        {
            "question": "¿Se puede trabajar a distancia?",
            "answer": "Sí. El curso enseña sustitución temporal y prácticas de teletransmisión o rastreo remoto.",
            "source": ["transcripción módulos 2, 11 y 12", "manual páginas 64 y 513"],
        },
        {
            "question": "¿Para qué sirven los 5 elementos dentro del curso?",
            "answer": "Sirven para leer estados energéticos globales, asociar emociones, órganos y funciones, y orientar la interpretación del caso.",
            "source": ["transcripción módulos 8, 9 y 10", "manual páginas 163-190"],
        },
        {
            "question": "¿Qué se registra de un síntoma al iniciar?",
            "answer": "Características, frecuencia, fecha aproximada de origen y factores que lo inhiben o estresan, además de si es físico o psicoemocional.",
            "source": ["transcripción módulo 1", "manual página 45"],
        },
        {
            "question": "¿El curso incluye medicina tradicional china completa?",
            "answer": "No como formación completa, sino como una integración práctica centrada en Qi, 5 elementos, meridianos, puntos y lectura energética útil al biomagnetismo.",
            "source": ["transcripción módulo 7", "manual páginas 160-326"],
        },
        {
            "question": "¿Qué herramientas complementarias incorpora el curso?",
            "answer": "Campos magnéticos pulsantes, homeopatía, flores de Bach, sales de Schüssler y protocolos emocionales como EFT Pro.",
            "source": ["transcripción módulo 1", "manual páginas 327-505"],
        },
        {
            "question": "¿Qué es EFT Pro dentro de este curso?",
            "answer": "Es un protocolo de liberación emocional que combina entrevista, trance, viaje temporal, tapping, reencuadre y recalibración.",
            "source": ["manual páginas 501-505"],
        },
        {
            "question": "¿El curso entrega comandos de búsqueda concretos?",
            "answer": "Sí. Los condensados incluyen fórmulas específicas para rastreo holobiomagnético, impactos emocionales, frecuencias y sustitución.",
            "source": ["manual páginas 511-513"],
        },
        {
            "question": "¿El manual deja listo todo el diagnóstico?",
            "answer": "No. El propio curso recalca que la labor del terapeuta consiste en investigar, preguntar e interpretar, no solo seguir listas automáticas.",
            "source": ["transcripción módulo 1", "manual página 44"],
        },
    ]

    intake_questions = [
        {
            "id": "intake_sintoma_principal",
            "question": "¿Qué síntomas quiere trabajar hoy?",
            "category": "motivo_consulta",
            "why_it_matters": "Abre la búsqueda sobre lo que el paciente desea atender y ayuda a priorizar el rastreo.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "intake_tipo_sintoma",
            "question": "¿Lo que trae es físico, psicoemocional o de ambos tipos?",
            "category": "clasificacion",
            "why_it_matters": "El curso pide distinguir desde el inicio entre cuerpo y mente para no mezclar planos de forma imprecisa.",
            "source": "transcripción módulo 1; manual página 45",
        },
        {
            "id": "intake_caracteristicas",
            "question": "¿Cómo es exactamente el síntoma: dónde está, cómo duele o cómo se siente?",
            "category": "caracterizacion",
            "why_it_matters": "Transforma etiquetas vagas como 'gastritis' en sensaciones rastreables y clínicamente útiles.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "intake_frecuencia",
            "question": "¿Con qué frecuencia aparece: diario, varias veces por semana o en recurrencias por periodos?",
            "category": "cronologia",
            "why_it_matters": "Permite medir intensidad de repetición y diferenciar un evento agudo de un patrón recurrente.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "intake_origen",
            "question": "¿Desde cuándo empezó, aunque sea de forma aproximada?",
            "category": "cronologia",
            "why_it_matters": "El curso usa la fecha aproximada de origen para ubicar la etapa vital y buscar conflicto o patrón asociado.",
            "source": "transcripción módulo 1; manual página 45",
        },
        {
            "id": "intake_factores",
            "question": "¿Qué factores lo inhiben, lo agravan o lo disparan?",
            "category": "moduladores",
            "why_it_matters": "Ayuda a ubicar el contexto funcional o emocional que sostiene el cuadro.",
            "source": "manual página 45",
        },
        {
            "id": "intake_conflicto_critico",
            "question": "¿Cuál fue el evento o punto crítico asociado al inicio o empeoramiento del problema?",
            "category": "conflicto",
            "why_it_matters": "Prepara el trabajo terapéutico y el viaje temporal de protocolos emocionales.",
            "source": "manual página 501; transcripción módulo 11",
        },
        {
            "id": "intake_vida_post_conflicto",
            "question": "¿Qué pasó después del evento y cómo ha seguido su vida desde entonces?",
            "category": "seguimiento",
            "why_it_matters": "Permite entender la cronificación y cómo el conflicto siguió activo.",
            "source": "manual página 501",
        },
        {
            "id": "intake_antecedentes_control",
            "question": "¿Hay embarazo, marcapasos, quimio/radioterapia, transfusiones, trasplantes o cirugías relevantes?",
            "category": "seguridad",
            "why_it_matters": "La ficha de control del curso pide registrarlo antes de iniciar.",
            "source": "manual página 45",
        },
        {
            "id": "intake_emocion_actual",
            "question": "¿Qué emoción pesa más hoy y en qué parte del cuerpo la siente?",
            "category": "emocional",
            "why_it_matters": "Conecta entrevista clínica con protocolos emocionales y con lectura energética.",
            "source": "manual páginas 501-505; transcripción módulo 8",
        },
        {
            "id": "intake_recurrencia",
            "question": "¿Le ha pasado antes algo parecido y cada cuánto vuelve?",
            "category": "patrones",
            "why_it_matters": "El curso pone atención en recurrencias para distinguir patrones sistémicos o repetitivos.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "intake_relacion_elemental",
            "question": "¿El cuadro se siente más ligado a miedo, enojo, tristeza, reflexión o ansiedad?",
            "category": "lectura_energetica",
            "why_it_matters": "Ayuda a orientar una lectura por 5 elementos y dinámica del Qi.",
            "source": "transcripción módulo 8; manual página 162",
        },
    ]

    reasoning_patterns = [
        {
            "id": "pattern_vaguedad_sintoma",
            "si_aparece": "Un paciente usa una etiqueta general como 'gastritis' o 'migraña'.",
            "observar": "Qué siente realmente, dónde, cómo y con qué cualidad.",
            "considerar": "No trabajar la palabra como diagnóstico sino la sensación concreta y su localización.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "pattern_recurrencia",
            "si_aparece": "El problema no es diario pero vuelve cíclicamente.",
            "observar": "Frecuencia semanal, mensual o anual y episodios previos similares.",
            "considerar": "Puede haber un patrón recurrente más profundo que el cuadro actual.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "pattern_origen_aproximado",
            "si_aparece": "La persona no recuerda una fecha exacta.",
            "observar": "Etapa de vida, años de referencia, periodos académicos o familiares.",
            "considerar": "Ubicar cronología aproximada sigue siendo clínicamente útil.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "pattern_terapia_empieza_en_entrevista",
            "si_aparece": "El paciente empieza a recordar o conectar datos mientras habla.",
            "observar": "Cambios de conciencia, memoria y emoción durante la entrevista.",
            "considerar": "La intervención ya empezó; no separar investigación y terapia de manera rígida.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "pattern_subyacente_vs_sintoma",
            "si_aparece": "Los síntomas recientes parecen menores frente al desorden energético global.",
            "observar": "Señales de exceso, calor, frío o estasis más allá del motivo puntual de consulta.",
            "considerar": "Tratar primero el estado energético subyacente puede modificar los síntomas visibles.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "pattern_molde_organico",
            "si_aparece": "Un órgano fue retirado quirúrgicamente.",
            "observar": "Si el rastreo sigue mostrando actividad energética asociada a ese órgano.",
            "considerar": "El molde energético puede seguir activo aunque la estructura física ya no esté.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "pattern_qi_miedo",
            "si_aparece": "Predomina miedo, pánico o contracción.",
            "observar": "Descenso del Qi, sequedad, ganas de orinar, repliegue corporal.",
            "considerar": "El miedo puede estar alterando agua/riñón o la dinámica descendente del Qi.",
            "source": "transcripción módulo 8; manual página 162",
        },
        {
            "id": "pattern_qi_enojo",
            "si_aparece": "Predomina enojo o rabia.",
            "observar": "Calor en cabeza, tensión, rubor, elevación energética.",
            "considerar": "El enojo hace ascender el Qi y puede orientar hacia madera/hígado/vesícula.",
            "source": "transcripción módulo 8; manual página 162",
        },
        {
            "id": "pattern_qi_tristeza",
            "si_aparece": "Predomina tristeza o melancolía.",
            "observar": "Dispersión, vacío, desconexión del foco.",
            "considerar": "La tristeza dispersa el Qi y puede alterar metal/pulmón/intestino grueso.",
            "source": "transcripción módulo 8; manual página 162",
        },
        {
            "id": "pattern_metal_social",
            "si_aparece": "Hay alteración en metal.",
            "observar": "Padre, vínculos sociales, círculos elegidos, forma de conectarse con otros.",
            "considerar": "Metal no se limita a pulmón-intestino grueso: también habla de lazos y elección social.",
            "source": "transcripción módulo 1 y 10",
        },
        {
            "id": "pattern_madera_direccion",
            "si_aparece": "Hay alteración en madera.",
            "observar": "Dirección vital, decisiones, enojo presente o resentido.",
            "considerar": "La madera se relaciona con orientación, movimiento y decisión sobre lo que se quiere.",
            "source": "transcripción módulo 1 y 9",
        },
        {
            "id": "pattern_fuego_expresion",
            "si_aparece": "Hay alteración en fuego.",
            "observar": "Expresión de ideas, espíritu, proyectos, mente consciente.",
            "considerar": "Fuego se interpreta como expresión del ser y del Shen, más que solo como órgano cardíaco.",
            "source": "transcripción módulo 10",
        },
        {
            "id": "pattern_canal_exceso",
            "si_aparece": "Varios meridianos aparecen en exceso.",
            "observar": "Si el regulador general también muestra calor o sobrecarga.",
            "considerar": "Puede haber una crisis energética global y no solo un punto local afectado.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "pattern_busqueda_ordenada",
            "si_aparece": "Se va a rastrear patógenos, pares o frecuencias.",
            "observar": "Que el comando de búsqueda sea claro y luego se compruebe el programa.",
            "considerar": "El curso insiste en una secuencia mental y verbal ordenada antes del rastreo.",
            "source": "manual páginas 63, 511 y 512",
        },
        {
            "id": "pattern_conflicto_emocional",
            "si_aparece": "El síntoma tiene una carga afectiva evidente o un antecedente crítico.",
            "observar": "Emoción principal, localización corporal, intensidad y evento originario.",
            "considerar": "Puede ser mejor desarticular impacto emocional antes de repetir solo pares físicos.",
            "source": "manual páginas 501-505 y 511",
        },
    ]

    interpretation_guides = [
        {
            "id": "guide_entrevista",
            "titulo": "Cómo traducir la queja a información útil",
            "senales": ["síntoma vago", "etiqueta médica repetida", "poca precisión corporal"],
            "lectura": "El terapeuta debe bajar de la etiqueta al dato fenomenológico: sensación, lugar, frecuencia, origen y detonantes.",
            "uso": "Antes de cualquier rastreo principal.",
            "source": "transcripción módulo 1; manual página 45",
        },
        {
            "id": "guide_5_elementos_global",
            "titulo": "Lectura global por 5 elementos",
            "senales": ["múltiples sistemas alterados", "sobrecarga emocional", "casos complejos"],
            "lectura": "Sirve para ubicar el estado energético de fondo y no solo el síntoma del día.",
            "uso": "Cuando el cuadro actual parece producto de un desorden más antiguo o más amplio.",
            "source": "transcripción módulo 1; manual página 513",
        },
        {
            "id": "guide_emocion_qi",
            "titulo": "Emoción como movimiento del Qi",
            "senales": ["miedo", "enojo", "tristeza", "ansiedad", "alegría desbordada"],
            "lectura": "Cada emoción cambia la dirección o calidad del Qi y orienta la lectura terapéutica.",
            "uso": "Durante entrevista, rastreo emocional y lectura de meridianos.",
            "source": "transcripción módulo 8; manual página 162",
        },
        {
            "id": "guide_organos_y_moldes",
            "titulo": "Órgano físico vs molde energético",
            "senales": ["órgano ausente", "cirugía previa", "rastreo energético persistente"],
            "lectura": "La falta anatómica no cancela automáticamente la lectura energética del sistema.",
            "uso": "En pacientes operados o con historia de extirpación.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "guide_metal",
            "titulo": "Interpretación de metal",
            "senales": ["alteración en pulmón", "alteración en intestino grueso", "tristeza o conexión social afectada"],
            "lectura": "Metal puede hablar de eliminación, vínculo social, figura paterna y forma de conectarse con otros.",
            "uso": "Cuando el rastreo señale metal o emociones de tristeza/conexión.",
            "source": "transcripción módulos 1 y 10",
        },
        {
            "id": "guide_madera",
            "titulo": "Interpretación de madera",
            "senales": ["vesícula/hígado", "enojo", "indecisión", "falta de dirección"],
            "lectura": "Madera se lee como dirección, decisión y manejo del enojo presente o retenido.",
            "uso": "Cuando aparezcan vesícula/hígado o rabia/resignación acumulada.",
            "source": "transcripción módulo 1; manual página 164",
        },
        {
            "id": "guide_distancia",
            "titulo": "Trabajo a distancia",
            "senales": ["paciente ausente", "caso remoto", "uso de sustituto"],
            "lectura": "El curso requiere aceptación explícita del sustituto y comprobación de identidad antes del rastreo.",
            "uso": "Solo en procedimientos remotos o por sustitución.",
            "source": "manual páginas 64 y 513; transcripción módulos 2, 11 y 12",
        },
    ]

    therapeutic_observations = [
        {
            "id": "obs_1",
            "observacion": "El curso trata la entrevista como parte activa de la terapia y no como preámbulo administrativo.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "obs_2",
            "observacion": "Se busca leer el estado energético de fondo antes que perseguir síntomas aislados.",
            "source": "transcripción módulo 1",
        },
        {
            "id": "obs_3",
            "observacion": "La integración con medicina tradicional china se usa como lógica de lectura e intervención, no como repetición literal de la acupuntura clásica.",
            "source": "transcripción módulo 7",
        },
        {
            "id": "obs_4",
            "observacion": "El curso enfatiza la relación entre emoción, cuerpo y meridianos como un mismo continuo clínico.",
            "source": "transcripción módulo 8; manual páginas 160-190",
        },
        {
            "id": "obs_5",
            "observacion": "Las herramientas complementarias se incorporan por rastreo, no por receta uniforme.",
            "source": "manual página 512; transcripción módulo 1",
        },
        {
            "id": "obs_6",
            "observacion": "La práctica remota no se presenta como improvisación, sino como protocolo con sustitución, comprobación y comandos de búsqueda.",
            "source": "manual páginas 64 y 513",
        },
        {
            "id": "obs_7",
            "observacion": "La dimensión psicoemocional no es adorno: forma parte del razonamiento causal del caso.",
            "source": "manual páginas 501-505; transcripción módulo 11",
        },
    ]

    clinical_warnings = [
        {
            "id": "warning_1",
            "tipo": "limite_metodologico",
            "warning": "El rastreo no se presenta como medicina alopática ni como sustituto de diagnóstico médico.",
            "detalle": "El consentimiento del manual aclara que no se deben alterar prescripciones médicas de base y que el objetivo es estabilizar o equilibrar el sistema bioeléctrico con fines homeostáticos.",
            "source": "manual página 44",
        },
        {
            "id": "warning_2",
            "tipo": "seguimiento_post_rastreo",
            "warning": "Después del rastreo pueden aparecer síntomas leves transitorios.",
            "detalle": "Se mencionan poliuria, astenia, adinamia, febrícula, cefalea, diarrea, pesadez, dolor muscular y somnolencia, que no deberían durar más de 72 horas.",
            "source": "manual página 44",
        },
        {
            "id": "warning_3",
            "tipo": "seguridad_basica",
            "warning": "Antes del trabajo se registran condiciones de control.",
            "detalle": "El formato pide revisar embarazo, marcapasos, quimio/radioterapia, transfusiones, trasplantes y cirugías.",
            "source": "manual página 45",
        },
        {
            "id": "warning_4",
            "tipo": "privacidad",
            "warning": "Los casos demostrativos deben respetar la privacidad del consultante.",
            "detalle": "En la práctica en vivo se recuerda que no debe romperse la privacidad si se graba o comparte la sesión.",
            "source": "transcripción módulo 11",
        },
        {
            "id": "warning_5",
            "tipo": "uso_profesional",
            "warning": "El manual pide practicar el material con comprensión y profesionalismo.",
            "detalle": "Advierte contra la reproducción mecánica del contenido sin haber transmitido ni entendido bien la técnica.",
            "source": "manual páginas 1-2 del PDF extraído",
        },
        {
            "id": "warning_6",
            "tipo": "ambiguedad_clinica",
            "warning": "Varias correspondencias energéticas funcionan como guía interpretativa, no como diagnóstico definitivo por sí solas.",
            "detalle": "El curso ofrece relaciones entre emociones, meridianos, elementos y síntomas, pero su uso requiere entrevista, rastreo y contextualización.",
            "source": "transcripción módulos 1 y 8-10",
        },
    ]

    protocols = [
        {
            "id": "protocol_entrevista_inicial",
            "nombre": "Entrevista inicial de rastreo",
            "objetivo": "Convertir la queja del paciente en información clínica operable para rastreo e interpretación.",
            "descripcion": "Secuencia base para ordenar síntomas, cronología, moduladores y controles antes del trabajo energético.",
            "cuando_usarlo": [
                "Al inicio de toda sesión.",
                "Antes de rastreo de pares, 5 elementos o frecuencias.",
            ],
            "cuando_no_usarlo_si_aplica": [
                "No se reportan exclusiones explícitas; en urgencias médicas o crisis severas el material no describe sustitución de atención profesional.",
            ],
            "prerequisitos": [
                "Consentimiento informado y ficha de control.",
                "Disposición del paciente para describir síntomas con detalle.",
            ],
            "pasos": [
                {
                    "orden": 1,
                    "titulo": "Identificar motivo de consulta",
                    "instruccion": "Preguntar qué síntomas desea trabajar el paciente.",
                    "objetivo_del_paso": "Definir el foco de la sesión.",
                    "que_observar": "Si el síntoma es físico, psicoemocional o mixto.",
                    "que_registrar": "Motivo principal de consulta.",
                    "notas": "El curso insiste en distinguir ambos planos desde el inicio.",
                },
                {
                    "orden": 2,
                    "titulo": "Precisar características",
                    "instruccion": "Pedir que describa cómo se siente el síntoma y dónde aparece exactamente.",
                    "objetivo_del_paso": "Bajar de la etiqueta general a la experiencia concreta.",
                    "que_observar": "Tipo de dolor, sensación, zona específica.",
                    "que_registrar": "Características detalladas del síntoma.",
                    "notas": "Ejemplo del curso: 'gastritis' no basta; se pide qué siente y dónde.",
                },
                {
                    "orden": 3,
                    "titulo": "Registrar frecuencia",
                    "instruccion": "Explorar si es diario, intermitente o recurrente por periodos.",
                    "objetivo_del_paso": "Distinguir patrón agudo de patrón repetitivo.",
                    "que_observar": "Frecuencia por día, semana o recurrencia anual.",
                    "que_registrar": "Frecuencia y recurrencia.",
                    "notas": "Hay cuadros donde no aplica frecuencia clásica; se anota como permanente.",
                },
                {
                    "orden": 4,
                    "titulo": "Ubicar origen aproximado",
                    "instruccion": "Investigar desde cuándo empezó, aunque sea por etapa de vida.",
                    "objetivo_del_paso": "Conectar el cuadro con cronología clínica.",
                    "que_observar": "Recuerdos asociados, periodos vitales, cambios importantes.",
                    "que_registrar": "Fecha aproximada de origen.",
                    "notas": "Si la persona no recuerda fecha exacta, se ubica por rangos o hitos de vida.",
                },
                {
                    "orden": 5,
                    "titulo": "Identificar factores moduladores",
                    "instruccion": "Explorar qué lo empeora, lo inhibe o lo acompaña.",
                    "objetivo_del_paso": "Entender contexto funcional y emocional.",
                    "que_observar": "Factores estresores, inhibidores, disparadores.",
                    "que_registrar": "Factores Inh/Est.",
                    "notas": "Viene explícito en la ficha del manual.",
                },
                {
                    "orden": 6,
                    "titulo": "Aplicar preguntas de control",
                    "instruccion": "Registrar embarazo, marcapasos, quimio/radioterapia, transfusiones, trasplantes y cirugías.",
                    "objetivo_del_paso": "Tener contexto de seguridad y antecedentes.",
                    "que_observar": "Condiciones previas relevantes.",
                    "que_registrar": "Preguntas de control del formato.",
                    "notas": "No se presentan como contraindicaciones absolutas, sino como datos a considerar.",
                },
            ],
            "que_registrar": [
                "Síntomas físicos y psicoemocionales.",
                "Características.",
                "Frecuencia.",
                "Fecha de origen.",
                "Factores inhibidores o estresores.",
                "Preguntas de control y antecedentes relevantes.",
            ],
            "observaciones": [
                "El curso recalca que la entrevista ya forma parte de la terapia.",
                "Sirve de base para rastreo de pares, 5 elementos y trabajo emocional.",
            ],
            "advertencias": [
                "No usar la entrevista como si fuera un diagnóstico médico cerrado.",
                "No dejar el síntoma en palabras vagas; convertirlo en experiencia concreta.",
            ],
            "fuente": ["transcripción módulo 1", "manual páginas 44-45"],
            "confianza_extraccion": 0.94,
        },
        {
            "id": "protocol_microbios_pares",
            "nombre": "Rastreo de microorganismos y pares biomagnéticos",
            "objetivo": "Detectar agentes patógenos relevantes y los pares biomagnéticos necesarios.",
            "descripcion": "Secuencia condensada para abrir búsqueda, comprobar programa, rastrear categorías de patógenos y después rastrear pares por región, zona y bloque.",
            "cuando_usarlo": [
                "Cuando se quiera explorar infección o componente microbiológico.",
                "Como secuencia base de rastreo biomagnético clásico dentro del curso.",
            ],
            "cuando_no_usarlo_si_aplica": [
                "El material no define exclusiones expresas; requiere entrevista y ficha de control previas.",
            ],
            "prerequisitos": [
                "Consentimiento y entrevista inicial.",
                "Circuito bioenergético abierto según la metodología.",
                "Listas o menús de patógenos y pares a la mano.",
            ],
            "pasos": [
                {
                    "orden": 1,
                    "titulo": "Establecer búsqueda de patógenos",
                    "instruccion": "Declarar la búsqueda de microorganismos patógenos presentes en ese momento.",
                    "objetivo_del_paso": "Fijar el foco del rastreo.",
                    "que_observar": "Respuesta afirmativa de que el sistema sabe qué se busca.",
                    "que_registrar": "Comando usado y validación.",
                    "notas": "El manual formula la frase exacta.",
                },
                {
                    "orden": 2,
                    "titulo": "Comprobar programa",
                    "instruccion": "Preguntar si el sistema sabe qué se está buscando.",
                    "objetivo_del_paso": "Evitar rastreo sin foco validado.",
                    "que_observar": "Sí/No.",
                    "que_registrar": "Confirmación del programa.",
                    "notas": "Se repite en casi todos los rastreos del curso.",
                },
                {
                    "orden": 3,
                    "titulo": "Buscar patógenos por categorías",
                    "instruccion": "Rastrear cuántas bacterias, parásitos, hongos, virus o priones hay y luego identificarlos por lista o bloque.",
                    "objetivo_del_paso": "Acotar agentes relevantes.",
                    "que_observar": "Número de agentes por categoría y grupo.",
                    "que_registrar": "Patógenos detectados y su clasificación.",
                    "notas": "El manual ordena la búsqueda por categorías.",
                },
                {
                    "orden": 4,
                    "titulo": "Abrir búsqueda de pares biomagnéticos",
                    "instruccion": "Declarar la búsqueda de pares necesarios y comprobar el programa.",
                    "objetivo_del_paso": "Pasar del agente al soporte biomagnético correctivo.",
                    "que_observar": "Confirmación de la búsqueda.",
                    "que_registrar": "Inicio de búsqueda de pares.",
                    "notas": "En transcripción se repite esta lógica operativa.",
                },
                {
                    "orden": 5,
                    "titulo": "Rastrear por región, zona y bloque",
                    "instruccion": "Preguntar si se necesita algún par de región, zona, bloque y luego el número de par.",
                    "objetivo_del_paso": "Ubicar los pares específicos.",
                    "que_observar": "Regiones y números activados.",
                    "que_registrar": "Pares detectados.",
                    "notas": "La búsqueda se hace en orden de lista.",
                },
                {
                    "orden": 6,
                    "titulo": "Colocar y retirar imanes",
                    "instruccion": "Colocar los imanes durante 20 minutos y retirarlos.",
                    "objetivo_del_paso": "Ejecutar la corrección biomagnética.",
                    "que_observar": "Tolerancia y cambios posteriores.",
                    "que_registrar": "Tiempo de colocación y observaciones de la sesión.",
                    "notas": "Es el cierre operativo resumido del manual.",
                },
            ],
            "que_registrar": [
                "Patógenos detectados por categoría.",
                "Pares biomagnéticos encontrados.",
                "Tiempo de colocación.",
                "Respuesta del paciente o del rastreo.",
            ],
            "observaciones": [
                "Esta secuencia combina biomagnetismo clásico y la disciplina verbal de búsqueda del curso.",
            ],
            "advertencias": [
                "No confundir rastreo con diagnóstico médico definitivo.",
                "Se recomienda haber completado la entrevista inicial antes de aplicar esta secuencia.",
            ],
            "fuente": ["manual página 63", "transcripción módulo 6"],
            "confianza_extraccion": 0.95,
        },
        {
            "id": "protocol_sustitucion_temporal",
            "nombre": "Programa de sustitución temporal para trabajo a distancia",
            "objetivo": "Habilitar rastreo o intervención remota mediante una persona sustituta.",
            "descripcion": "Procedimiento verbal y de comprobación para que un sustituto temporal manifieste respuestas de otra persona.",
            "cuando_usarlo": [
                "Cuando el consultante no está presente.",
                "En demostraciones o trabajo remoto donde el curso utilice sustituto.",
            ],
            "cuando_no_usarlo_si_aplica": [
                "No usar sin identificar correctamente a la persona objetivo ni sin consentimiento del proceso.",
            ],
            "prerequisitos": [
                "Nombre completo y fecha de nacimiento de la persona objetivo.",
                "Sustituto disponible y dispuesto.",
                "Apertura del circuito bioenergético según el método.",
            ],
            "pasos": [
                {
                    "orden": 1,
                    "titulo": "Declarar aceptación de sustitución",
                    "instruccion": "Pronunciar la fórmula de aceptación como sustituto temporal de la persona objetivo.",
                    "objetivo_del_paso": "Asignar la representación temporal.",
                    "que_observar": "Respuesta del sistema o resistencia muscular.",
                    "que_registrar": "Nombre y fecha de nacimiento usados.",
                    "notas": "La versión ampliada añade 'manifiesta a través de mí todas sus respuestas…'.",
                },
                {
                    "orden": 2,
                    "titulo": "Subir circuito bioenergético",
                    "instruccion": "Subir el circuito bioenergético al finalizar la fórmula.",
                    "objetivo_del_paso": "Habilitar el canal operativo para el rastreo.",
                    "que_observar": "Cambio corporal o respuesta muscular.",
                    "que_registrar": "Que el circuito fue abierto.",
                    "notas": "En la versión corta se hace tras vencer la resistencia muscular de brazos erguidos.",
                },
                {
                    "orden": 3,
                    "titulo": "Comprobar identidad",
                    "instruccion": "Preguntar si el nombre es el del sustituto y luego el de la persona objetivo.",
                    "objetivo_del_paso": "Verificar que la sintonización está correcta.",
                    "que_observar": "Respuesta negativa al nombre propio y afirmativa al nombre objetivo.",
                    "que_registrar": "Resultado de comprobación.",
                    "notas": "Es central en los ejemplos de módulos 11 y 12.",
                },
                {
                    "orden": 4,
                    "titulo": "Ejecutar el rastreo necesario",
                    "instruccion": "Realizar búsqueda de pares, impactos, 5 elementos o puntos según el objetivo de la sesión.",
                    "objetivo_del_paso": "Usar la sustitución como interfaz de trabajo.",
                    "que_observar": "Respuestas del sustituto.",
                    "que_registrar": "Comandos y hallazgos del rastreo.",
                    "notas": "El manual deja comandos de búsqueda posibles.",
                },
                {
                    "orden": 5,
                    "titulo": "Instalar información o pares",
                    "instruccion": "Insertar la información holobiomagnética activa y pulsante durante 30 minutos si el protocolo lo requiere.",
                    "objetivo_del_paso": "Aplicar la corrección a distancia.",
                    "que_observar": "Validación de que se está gestionando efectivamente.",
                    "que_registrar": "Pares o puntos instalados y duración.",
                    "notas": "Se visualizan toroides en los puntos según el manual.",
                },
            ],
            "que_registrar": [
                "Datos del consultante remoto.",
                "Nombre del sustituto.",
                "Resultado de comprobación.",
                "Búsquedas realizadas y hallazgos.",
                "Instalación o pares aplicados.",
            ],
            "observaciones": [
                "El curso lo presenta como estructura formal, no como improvisación.",
                "Se usa en prácticas remotas con casos reales.",
            ],
            "advertencias": [
                "La comprobación de identidad es obligatoria dentro del método.",
                "Respetar privacidad del consultante remoto.",
            ],
            "fuente": ["manual páginas 64 y 513", "transcripción módulos 2, 11 y 12"],
            "confianza_extraccion": 0.96,
        },
        {
            "id": "protocol_rastreo_holobiomagnetico",
            "nombre": "Rastreo holobiomagnético condensado",
            "objetivo": "Detectar e instalar pares holobiomagnéticos para restaurar la armonía biodinámica de todos los cuerpos.",
            "descripcion": "Versión condensada del manual para búsqueda de pares holobiomagnéticos e instalación de información activa y pulsante.",
            "cuando_usarlo": [
                "Cuando se busca restaurar armonía biodinámica más allá del biomagnetismo clásico.",
                "Después de entrevista y definición del síntoma o foco.",
            ],
            "cuando_no_usarlo_si_aplica": [
                "No se especifican exclusiones operativas; requiere entrevista y comando claro de búsqueda.",
            ],
            "prerequisitos": [
                "Circuito bioenergético abierto.",
                "Síntoma o foco terapéutico definido si se va a hacer búsqueda opcional por síntoma.",
            ],
            "pasos": [
                {
                    "orden": 1,
                    "titulo": "Establecer búsqueda",
                    "instruccion": "Declarar que se hará un rastreo holobiomagnético y pedir los pares necesarios para restaurar la armonía biodinámica.",
                    "objetivo_del_paso": "Fijar la intención operativa del rastreo.",
                    "que_observar": "Claridad del foco y apertura del circuito.",
                    "que_registrar": "Comando de búsqueda y síntoma focal si aplica.",
                    "notas": "El manual agrega una opción para ligar la búsqueda a un síntoma X.",
                },
                {
                    "orden": 2,
                    "titulo": "Comprobar programa",
                    "instruccion": "Verificar si el sistema sabe qué se está buscando.",
                    "objetivo_del_paso": "Confirmar que la búsqueda está correctamente planteada.",
                    "que_observar": "Respuesta sí/no.",
                    "que_registrar": "Confirmación del programa.",
                    "notas": "",
                },
                {
                    "orden": 3,
                    "titulo": "Rastrear por región, zona y bloque",
                    "instruccion": "Preguntar por región, zona, bloque y número de par necesarios.",
                    "objetivo_del_paso": "Localizar los pares activos del momento.",
                    "que_observar": "Cuántos pares y en qué áreas aparecen.",
                    "que_registrar": "Pares detectados.",
                    "notas": "Mantiene la secuencia por niveles del curso.",
                },
                {
                    "orden": 4,
                    "titulo": "Instalar información",
                    "instruccion": "Insertar información de par holobiomagnético activo y pulsante durante 30 minutos en los puntos encontrados, visualizando toroides.",
                    "objetivo_del_paso": "Aplicar la corrección holobiomagnética.",
                    "que_observar": "Si los pares se están gestionando efectivamente.",
                    "que_registrar": "Pares instalados, duración y validación.",
                    "notas": "El manual pide comprobar la gestión efectiva.",
                },
            ],
            "que_registrar": [
                "Síntoma focal si se usa.",
                "Pares hallados.",
                "Tiempo de instalación.",
                "Validación de gestión efectiva.",
            ],
            "observaciones": [
                "Es una versión condensada y escalable del enfoque del curso.",
            ],
            "advertencias": [
                "No sustituye una entrevista adecuada ni el razonamiento del caso.",
            ],
            "fuente": ["manual página 511"],
            "confianza_extraccion": 0.94,
        },
        {
            "id": "protocol_rastreo_impacto_emocional",
            "nombre": "Rastreo y desarticulación de impacto emocional",
            "objetivo": "Identificar hologramas o impactos emocionales y reunir datos para desarticularlos.",
            "descripcion": "Secuencia condensada del manual para rastrear conflictos emocionales activos y cancelarlos con apoyo holobiomagnético.",
            "cuando_usarlo": [
                "Cuando el caso tiene una carga emocional clara.",
                "Cuando el síntoma se relaciona con un conflicto, persona o evento específico.",
            ],
            "cuando_no_usarlo_si_aplica": [
                "Si el caso requiere contención emocional mayor a la descrita por el material, considerar límites del método.",
            ],
            "prerequisitos": [
                "Foco terapéutico definido.",
                "Apertura del circuito bioenergético.",
            ],
            "pasos": [
                {
                    "orden": 1,
                    "titulo": "Establecer búsqueda de impactos",
                    "instruccion": "Declarar que se hará un rastreo de impactos emocionales para restaurar armonía biodinámica.",
                    "objetivo_del_paso": "Abrir la línea de trabajo emocional.",
                    "que_observar": "Confirmación del programa.",
                    "que_registrar": "Comando de búsqueda.",
                    "notas": "",
                },
                {
                    "orden": 2,
                    "titulo": "Rastrear holograma o conflicto",
                    "instruccion": "Preguntar si hay hologramas o impactos en bloques y localizar el conflicto activo.",
                    "objetivo_del_paso": "Detectar el núcleo emocional a trabajar.",
                    "que_observar": "Número de holograma/conflicto.",
                    "que_registrar": "Bloque, holograma y conflicto principal.",
                    "notas": "",
                },
                {
                    "orden": 3,
                    "titulo": "Precisar datos complementarios",
                    "instruccion": "Rastrear si se necesita recesión de edad, emoción-reacción, persona implicada, capa embrionaria, cromosoma, microbio, par biomagnético, chakra o meridiano.",
                    "objetivo_del_paso": "Completar la lectura necesaria para la desarticulación.",
                    "que_observar": "Qué capa de información se activa.",
                    "que_registrar": "Datos complementarios requeridos.",
                    "notas": "El manual no obliga a rastrear todo, solo lo que el sistema pida.",
                },
                {
                    "orden": 4,
                    "titulo": "Cancelar conflicto e instalar información",
                    "instruccion": "Declarar la cancelación del impacto y añadir la instalación de par holobiomagnético activo y pulsante durante 30 minutos.",
                    "objetivo_del_paso": "Desarticular la estructura emocional activa.",
                    "que_observar": "Chakra y meridiano a rearmonizar.",
                    "que_registrar": "Persona implicada, matiz específico, par usado y centros reequilibrados.",
                    "notas": "La fórmula del manual integra esencia primordial y matiz específico.",
                },
            ],
            "que_registrar": [
                "Holograma/conflicto identificado.",
                "Datos complementarios rastreados.",
                "Par usado.",
                "Chakra/meridiano rearmonizado.",
            ],
            "observaciones": [
                "Se puede cruzar con EFT Pro si el caso requiere ventilación y reprocesamiento consciente.",
            ],
            "advertencias": [
                "Parte del contenido es condensado y requiere criterio del terapeuta para secuenciarlo.",
            ],
            "fuente": ["manual página 511", "manual página 508"],
            "confianza_extraccion": 0.87,
        },
        {
            "id": "protocol_rastreo_frecuencias",
            "nombre": "Rastreo de frecuencias y soportes vibratorios",
            "objetivo": "Seleccionar homeopatía, flores de Bach o sales de Schüssler por rastreo.",
            "descripcion": "Secuencia para determinar tipo de soporte, bloque, potencia y periodo temporal de aplicación.",
            "cuando_usarlo": [
                "Cuando se busca soporte vibratorio complementario.",
                "Después de definir síntoma o causa principal a tratar.",
            ],
            "cuando_no_usarlo_si_aplica": [
                "No sustituye una prescripción homeopática clásica; el propio curso lo usa dentro de su sistema de rastreo.",
            ],
            "prerequisitos": [
                "Apertura del circuito bioenergético.",
                "Acceso al repertorio de remedios del manual.",
            ],
            "pasos": [
                {
                    "orden": 1,
                    "titulo": "Declarar búsqueda",
                    "instruccion": "Anunciar el rastreo homeopático, floral o de sales de Schüssler para restaurar armonía biodinámica.",
                    "objetivo_del_paso": "Definir la familia de soporte a rastrear.",
                    "que_observar": "Que el sistema reconozca la búsqueda.",
                    "que_registrar": "Tipo de rastreo solicitado.",
                    "notas": "Puede ligarse a un síntoma X.",
                },
                {
                    "orden": 2,
                    "titulo": "Comprobar programa",
                    "instruccion": "Verificar que se sabe qué se está buscando.",
                    "objetivo_del_paso": "Validar la preparación de la búsqueda.",
                    "que_observar": "Sí/No.",
                    "que_registrar": "Confirmación del programa.",
                    "notas": "",
                },
                {
                    "orden": 3,
                    "titulo": "Rastrear remedio, potencia y tiempo",
                    "instruccion": "Preguntar si es policresto o semipolicresto, el bloque, potencia y duración; o sector y duración para flores/sales.",
                    "objetivo_del_paso": "Definir con precisión el soporte vibratorio.",
                    "que_observar": "Bloque, potencia, periodo temporal y necesidad de otros remedios.",
                    "que_registrar": "Remedio o sal/flor, potencia, tiempo y repeticiones.",
                    "notas": "El manual separa lógica homeopática y floral/sales.",
                },
                {
                    "orden": 4,
                    "titulo": "Instalar información",
                    "instruccion": "Insertar el remedio o la sal/flor con su código radiónico activo y pulsante durante el periodo indicado.",
                    "objetivo_del_paso": "Aplicar el soporte seleccionado.",
                    "que_observar": "Comprobación de gestión efectiva.",
                    "que_registrar": "Soporte instalado y validación.",
                    "notas": "El manual pide comprobar si se está gestionando efectivamente.",
                },
            ],
            "que_registrar": [
                "Tipo de soporte vibratorio.",
                "Bloque o sector.",
                "Potencia si aplica.",
                "Periodo temporal.",
                "Remedios adicionales si aparecen.",
            ],
            "observaciones": [
                "En el curso funciona como apoyo complementario al trabajo central.",
            ],
            "advertencias": [
                "No confundir esta lógica de rastreo con indicación farmacológica convencional.",
            ],
            "fuente": ["manual página 512", "manual páginas 363-499"],
            "confianza_extraccion": 0.92,
        },
        {
            "id": "protocol_eft_pro",
            "nombre": "EFT Pro",
            "objetivo": "Liberar conflicto emocional mediante entrevista, trance, tapping, reencuadre y recalibración.",
            "descripcion": "Protocolo emocional central del curso, integrando TFT/EFT, hipnosis, PNL, meridianos y biodescodificación.",
            "cuando_usarlo": [
                "Cuando hay emoción o resentir claro asociado al cuadro.",
                "Cuando se necesita liberar carga emocional reprimida.",
            ],
            "cuando_no_usarlo_si_aplica": [
                "El manual no fija contraindicaciones absolutas, pero si la intensidad no desciende se debe repetir desde el paso 5; en duelos se sugiere aplicar 'Última lágrima' antes de otra sesión.",
            ],
            "prerequisitos": [
                "Entrevista detallada del conflicto.",
                "Disposición del consultante para entrar en trance ligero y viaje temporal.",
                "Identificación de emoción principal y localización corporal.",
            ],
            "pasos": [
                {
                    "orden": 1,
                    "titulo": "Entrevista detallada",
                    "instruccion": "Revisar origen del conflicto, detalles significativos, conflicto crítico y vida post-conflicto.",
                    "objetivo_del_paso": "Recabar información suficiente sin activar en exceso la mente consciente.",
                    "que_observar": "Hechos clave, momentos críticos, narrativa del paciente.",
                    "que_registrar": "Origen, detalles, conflicto crítico, vida post-conflicto.",
                    "notas": "El manual lo formula como paso 1.",
                },
                {
                    "orden": 2,
                    "titulo": "Inducción al trance",
                    "instruccion": "Llevar atención a procesos automáticos, hacer relajación sistemática y programar visualización sin juicio.",
                    "objetivo_del_paso": "Disminuir frecuencia cerebral y permitir que aflore lo inconsciente.",
                    "que_observar": "Relajación, foco, respuesta a lenguaje hipnótico.",
                    "que_registrar": "Inducción realizada y nivel de respuesta.",
                    "notas": "",
                },
                {
                    "orden": 3,
                    "titulo": "Viaje temporal",
                    "instruccion": "Llevar la mente al origen, eventos significativos, punto crítico y vida post-conflicto.",
                    "objetivo_del_paso": "Revivir la experiencia para detectar emociones ocultas.",
                    "que_observar": "Recuerdos, reacciones emocionales, imágenes.",
                    "que_registrar": "Escenas significativas.",
                    "notas": "",
                },
                {
                    "orden": 4,
                    "titulo": "Sintonizar el conflicto",
                    "instruccion": "Definir emoción principal (máximo dos), ubicarla en el cuerpo, calificar intensidad y subir circuito bioenergético.",
                    "objetivo_del_paso": "Identificar con precisión el conflicto a liberar.",
                    "que_observar": "Emoción, zona corporal, intensidad 1-10.",
                    "que_registrar": "Emoción principal, localización, intensidad inicial.",
                    "notas": "",
                },
                {
                    "orden": 5,
                    "titulo": "Ventilar energía contenida",
                    "instruccion": "Amplificar la emoción y luego ventilarla con inhalación por nariz y exhalación por boca.",
                    "objetivo_del_paso": "Comenzar a liberar lo reprimido psicológica y energéticamente.",
                    "que_observar": "Liberación afectiva, descarga corporal.",
                    "que_registrar": "Cambios tras la ventilación.",
                    "notas": "",
                },
                {
                    "orden": 6,
                    "titulo": "Taps de ida",
                    "instruccion": "Aplicar tapping en puntos de inversión y puntos mayores repitiendo el acuerdo neurolingüístico.",
                    "objetivo_del_paso": "Liberar en profundidad cuerpo mental y emocional y matizar la experiencia.",
                    "que_observar": "Variaciones de la emoción y memoria asociada.",
                    "que_registrar": "ANL usado y respuesta del paciente.",
                    "notas": "Incluye AJ, AHT, zona sensible y punto karate.",
                },
                {
                    "orden": 7,
                    "titulo": "Secuencia 9 gamma",
                    "instruccion": "Dar taps en punto gamma entre cuarto y quinto dedo del dorso sin repetir el ANL.",
                    "objetivo_del_paso": "Llevar el programa a todo el cerebro.",
                    "que_observar": "Integración y respuesta neurológica.",
                    "que_registrar": "Aplicación de secuencia 9 gamma.",
                    "notas": "",
                },
                {
                    "orden": 8,
                    "titulo": "Taps de vuelta y reencuadre",
                    "instruccion": "Repetir tapping con ANL, dar contexto constructivo, aportar recursos y soltar necesidad del síntoma.",
                    "objetivo_del_paso": "Reencuadrar la experiencia y desactivar la necesidad de la mutación o síntoma.",
                    "que_observar": "Aceptación, cambio de narrativa, recursos emergentes.",
                    "que_registrar": "Recurso aportado y reencuadre principal.",
                    "notas": "El manual menciona confianza, paciencia, fortaleza, entre otros.",
                },
                {
                    "orden": 9,
                    "titulo": "Cierre",
                    "instruccion": "Golpetear E36 mientras se ventila, decir ANL, exhalar, peinar energéticamente meridianos y expulsar al suelo; bajar circuito bioenergético.",
                    "objetivo_del_paso": "Terminar de liberar energética y psicológicamente el conflicto.",
                    "que_observar": "Sensación de descarga y cierre.",
                    "que_registrar": "Cierre realizado.",
                    "notas": "",
                },
                {
                    "orden": 10,
                    "titulo": "Recalibración",
                    "instruccion": "Volver a conectar con la emoción y medir intensidad del 0 al 10; si sigue en 4 o más, repetir desde paso 5.",
                    "objetivo_del_paso": "Comprobar si la gestión fue suficiente.",
                    "que_observar": "Intensidad final y necesidad de repetir.",
                    "que_registrar": "Intensidad final y decisión de continuidad.",
                    "notas": "En duelos se indica 'Última lágrima' antes de otra sesión.",
                },
            ],
            "que_registrar": [
                "Origen y conflicto crítico.",
                "Emoción principal y localización corporal.",
                "Intensidad inicial y final.",
                "ANL/reencuadre usado.",
                "Recursos activados.",
            ],
            "observaciones": [
                "El manual también entrega una versión condensada de 6 grandes pasos.",
                "Integra recursos de varias tradiciones en un solo flujo operativo.",
            ],
            "advertencias": [
                "Si la intensidad sigue alta, no cerrar en falso: repetir desde el paso 5.",
                "En duelos, atender la nota específica del manual sobre 'Última lágrima'.",
            ],
            "fuente": ["manual páginas 501-505"],
            "confianza_extraccion": 0.98,
        },
        {
            "id": "protocol_rastreo_cinco_elementos_global",
            "nombre": "Rastreo de 5 elementos global",
            "objetivo": "Leer el estado energético subyacente del caso por elemento, órgano, víscera y canal.",
            "descripcion": "Secuencia inferida desde los comandos condensados del manual y la demostración clínica del curso.",
            "cuando_usarlo": [
                "Cuando el caso parece más profundo que el síntoma del día.",
                "En cuadros donde conviene ver el panel energético general.",
            ],
            "cuando_no_usarlo_si_aplica": [
                "La versión paso a paso no aparece completa en el manual; usar con criterio y marcar hallazgos como lectura orientativa.",
            ],
            "prerequisitos": [
                "Entrevista inicial completa.",
                "Conocimiento mínimo de 5 elementos y meridianos según el curso.",
            ],
            "pasos": [
                {
                    "orden": 1,
                    "titulo": "Abrir búsqueda de 5 elementos",
                    "instruccion": "Usar el comando de búsqueda para rastreo de 5 elementos global.",
                    "objetivo_del_paso": "Definir el modo de lectura energética.",
                    "que_observar": "Confirmación del programa.",
                    "que_registrar": "Comando utilizado.",
                    "notas": "El comando aparece en condensados.",
                },
                {
                    "orden": 2,
                    "titulo": "Preguntar por elemento alterado",
                    "instruccion": "Revisar agua, madera, fuego, tierra y metal.",
                    "objetivo_del_paso": "Ubicar por dónde se abre la lectura.",
                    "que_observar": "Elementos con respuesta positiva.",
                    "que_registrar": "Elementos alterados.",
                    "notas": "",
                },
                {
                    "orden": 3,
                    "titulo": "Distinguir órgano, víscera y chi",
                    "instruccion": "Para cada elemento positivo, preguntar por órgano yin, víscera yang y trastorno de chi.",
                    "objetivo_del_paso": "Precisar si el hallazgo es estructural, funcional o de canal.",
                    "que_observar": "Qué parte del sistema se activa.",
                    "que_registrar": "Órgano, víscera y/o chi implicados.",
                    "notas": "La demostración del curso hace esta distinción.",
                },
                {
                    "orden": 4,
                    "titulo": "Calificar cualidad del desequilibrio",
                    "instruccion": "Preguntar si hay frío, calor, calor por insuficiencia, deficiencia, exceso o estasis según corresponda.",
                    "objetivo_del_paso": "Caracterizar la forma del desequilibrio.",
                    "que_observar": "Cualidades energéticas predominantes.",
                    "que_registrar": "Tipo de alteración.",
                    "notas": "Se apoya en categorías Yin/Yang del manual.",
                },
                {
                    "orden": 5,
                    "titulo": "Interpretar el patrón",
                    "instruccion": "Relacionar el hallazgo con emoción, función y aspecto vital del elemento.",
                    "objetivo_del_paso": "Traducir el rastreo a razonamiento clínico.",
                    "que_observar": "Conexión con dirección, expresión, vínculos, miedo, tristeza, etc.",
                    "que_registrar": "Hipótesis interpretativa.",
                    "notas": "El curso usa esta lectura para ir más profundo que el síntoma.",
                },
            ],
            "que_registrar": [
                "Elemento alterado.",
                "Órgano/chi/víscera implicados.",
                "Tipo de alteración (frío, calor, exceso, deficiencia, estasis).",
                "Hipótesis clínica asociada.",
            ],
            "observaciones": [
                "El curso lo usa como panel de control energético general.",
                "La secuencia está parcialmente reconstruida desde una demostración práctica.",
            ],
            "advertencias": [
                "Marcar como interpretación clínica, no como dato absoluto aislado.",
            ],
            "fuente": ["transcripción módulo 1", "manual páginas 163-165", "manual página 513"],
            "confianza_extraccion": 0.68,
        },
    ]

    manual_sections = [
        {
            "title": "Cibertelepatía y capas mentales",
            "source_pages": ["26-29"],
            "summary": "Introduce la lógica de mente universal, mente local y capas mentales como soporte conceptual del trabajo a distancia, la recepción de información y la cibertelepatía.",
            "highlights": [
                "Define cibernético como sistema de retroalimentación y telepatía como recepción/emisión psíquica de información.",
                "Distingue supraconsciente, subconsciente, subliminal y consciente.",
                "Asocia esta base con el toroide y el cuerpo mental.",
            ],
        },
        {
            "title": "Anatomía y área de rastreo",
            "source_pages": ["36-45"],
            "summary": "Aporta mapas anatómicos de referencia y los formatos prácticos para autorización, preguntas de control y levantamiento de sintomatología física y psicoemocional.",
            "highlights": [
                "Incluye anatomía de sistemas y glándulas.",
                "Trae consentimiento informado para rastreo mental con biomagnetismo.",
                "Incluye ficha con características, fecha de origen, frecuencia y factores inhibidores/estresores.",
            ],
        },
        {
            "title": "Microbios y biomagnetismo",
            "source_pages": ["46-64"],
            "summary": "Contiene menús de microbios, agrupaciones y la secuencia base para buscar patógenos y pares biomagnéticos.",
            "highlights": [
                "Clasifica bacterias, parásitos, hongos, virus y priones.",
                "Condensa el paso a paso de búsqueda de patógenos y pares.",
                "Incluye programa de sustitución para rastreo a distancia.",
            ],
        },
        {
            "title": "Medicina tradicional china y principios energéticos",
            "source_pages": ["160-165"],
            "summary": "Presenta el Qi como fuerza vital, los 7 dragones o pasiones, la dinámica emocional del Qi y la base Yin/Yang para interpretar enfermedad.",
            "highlights": [
                "El enojo asciende el Qi, la tristeza lo dispersa, la alegría lo armoniza, el miedo lo hace descender.",
                "Explica exceso, deficiencia y calor por insuficiencia.",
            ],
        },
        {
            "title": "Cinco elementos",
            "source_pages": ["163-190"],
            "summary": "Organiza relaciones de generación y control entre agua, madera, fuego, tierra y metal, junto con sus asociaciones emocionales y funcionales.",
            "highlights": [
                "Describe ciclos de alimentación y control entre elementos.",
                "Permite traducir emoción y patrón vital a lectura energética.",
            ],
        },
        {
            "title": "Meridianos, puntos y homologación",
            "source_pages": ["191-326"],
            "summary": "Reúne meridianos, puntos, cruces, puntos yuan, luo, tonificación, sedación y homologación entre biomagnetismo y MTC.",
            "highlights": [
                "Hace posible la biomagnetopuntura y el rastreo por puntos.",
                "Conecta mapas energéticos con operaciones biomagnéticas.",
            ],
        },
        {
            "title": "Frecuencias biomagnéticas",
            "source_pages": ["327-329"],
            "summary": "Introduce campos magnéticos pulsantes como apoyo corporal y regulador, incluyendo Bio Vortex.",
            "highlights": [
                "Los CMP se asocian con dolor, inflamación, oxigenación, sueño y regeneración.",
            ],
        },
        {
            "title": "Frecuencias bioenergéticas",
            "source_pages": ["363-365"],
            "summary": "Explica el rastreo de remedios vibratorios y la lógica de homeopatía complementaria por bloques, potencia y tiempo.",
            "highlights": [
                "Permite decidir policrestos o semipolicrestos.",
                "Se integra al rastreo de flores y sales.",
            ],
        },
        {
            "title": "Farmacopea homeopática",
            "source_pages": ["375-452"],
            "summary": "Catálogo de remedios homeopáticos usados como soporte vibratorio dentro del sistema del curso.",
            "highlights": [
                "Incluye policrestos y descripciones de uso.",
            ],
        },
        {
            "title": "Flores de Bach",
            "source_pages": ["453-494"],
            "summary": "Introducción a los remedios florales de Bach, sus categorías y su aplicación sobre desequilibrios de carácter y emoción.",
            "highlights": [
                "Ordena las flores por grandes categorías emocionales.",
            ],
        },
        {
            "title": "Sales de Schüssler",
            "source_pages": ["495-499"],
            "summary": "Presenta las 12 sales y su lógica de apoyo funcional dentro de una lectura vibratoria complementaria.",
            "highlights": [
                "Asocia cada sal con funciones orgánicas y cuadros frecuentes.",
            ],
        },
        {
            "title": "Protocolos emocionales: EFT Pro",
            "source_pages": ["501-505"],
            "summary": "Entrega el protocolo emocional más completo del curso, desde entrevista y trance hasta tapping, reencuadre, cierre y recalibración.",
            "highlights": [
                "Integra TFT, EFT, hipnosis, PNL y biodescodificación.",
                "Incluye un flujo resumido de 6 macro pasos.",
            ],
        },
        {
            "title": "Condensados operativos",
            "source_pages": ["511-513"],
            "summary": "Compila comandos de búsqueda y secuencias resumidas para rastreo holobiomagnético, impactos emocionales, frecuencias, sustitución y comandos de búsqueda específicos.",
            "highlights": [
                "Es el bloque más operativo del manual.",
                "Permite reconstruir secuencias ejecutables para asistentes de protocolos.",
            ],
        },
    ]

    course_overview = {
        "course_id": overview["course_id"],
        "course_name": overview["course_name"],
        "linea": overview["linea"],
        "tipo": overview["tipo"],
        "edition_note": overview["edition_note"],
        "description": overview["description"],
        "main_axes": overview["main_axes"],
        "positioning": "Curso de integración terapéutica posterior a Biomagnetismo Puro de la A a la Z.",
        "prerequisites": [
            "Familiaridad previa con biomagnetismo puro o pares biomagnéticos.",
            "Capacidad de entrevista clínica básica.",
            "Interés en integrar medicina china y trabajo emocional.",
        ],
        "detected_modules": module_summaries,
        "sources_used": overview["source_files_used"],
    }

    module_summaries_json = [
        {
            "module_number": item["module_number"],
            "title": item["title"],
            "focus": item["focus"],
            "summary": " ".join(item["clean_notes"]),
            "sources": item["sources"],
        }
        for item in module_summaries
    ]

    ambiguities = [
        "El material fuente presenta el curso como 2021, pero el manual disponible indica '1era Edición, 2020'.",
        "La transcripción contiene dos bloques etiquetados como módulo 11 y un bloque final como módulo 12; parece haber continuidad entre ellos y no una separación temática totalmente limpia.",
        "El manual entrega comandos de búsqueda para '5 elementos global' y '5 elementos específico', pero no un protocolo completo y cerrado como sí ocurre con EFT Pro.",
        "Varias tablas del PDF (pares, meridianos, puntos) están mejor como referencia de catálogo que como narrativa corrida; por eso se consolidaron conceptualmente y no se copiaron completas a las capas limpias.",
    ]

    gaps = [
        "No se dispone de un metadata.json original independiente; se derivó metadata desde el manifiesto ya existente.",
        "El manual no fija siempre límites clínicos o contraindicaciones absolutas para cada protocolo; en varios casos solo deja formato de control o advertencias generales.",
        "Las páginas de listas extensas de pares y algunos diagramas del PDF no son legibles como texto narrativo continuo; se usaron como referencia estructural, no como base de explicación larga.",
    ]

    course_manifest_final = {
        "nombre_del_curso": overview["course_name"],
        "linea": overview["linea"],
        "archivos_fuente_usados": overview["source_files_used"],
        "temas_principales": overview["main_axes"],
        "modulos_detectados": [item["module_number"] for item in module_summaries],
        "cantidad_de_conceptos_extraidos": len(concepts),
        "cantidad_de_patrones_terapeuticos_extraidos": len(reasoning_patterns),
        "cantidad_de_protocolos_extraidos": len(protocols),
        "ambiguedades_detectadas": ambiguities,
        "vacios_detectados": gaps,
        "nivel_de_preparacion": {
            "academic": "alto",
            "therapeutic": "alto",
            "protocols": "alto con algunas zonas marcadas como condensadas o parcialmente inferidas",
        },
        "observacion_general": (
            "La unidad quedó lista para alimentar futuros asistentes académicos, terapéuticos y de protocolos. "
            "El siguiente paso natural ya sería chunking o indexación semántica, pero la base de organización quedó separada y reutilizable."
        ),
    }

    metadata = {
        "course_id": manifest["course_id"],
        "course_name": manifest["course_name"],
        "linea": manifest["linea"],
        "tipo": manifest["tipo"],
        "audiencia": manifest["audiencia"],
        "idioma": manifest["idioma"],
        "source_course_dir": manifest["source_course_dir"],
        "workspace_source_dir": str(SOURCE_BASE),
        "source_items": manifest["sources"],
    }

    for folder in [
        OUTPUT_BASE / "01_sources",
        OUTPUT_BASE / "02_clean",
        OUTPUT_BASE / "03_academic",
        OUTPUT_BASE / "04_therapeutic",
        OUTPUT_BASE / "05_protocols",
        OUTPUT_BASE / "06_catalog",
    ]:
        folder.mkdir(parents=True, exist_ok=True)

    copy_source(SOURCE_DIR / "transcripcion_completa.txt", OUTPUT_BASE / "01_sources" / "transcripcion_completa.txt")
    copy_source(SOURCE_DIR / "Holobiomagnetismo_2021.txt", OUTPUT_BASE / "01_sources" / "Holobiomagnetismo_2021.txt")
    copy_source(SOURCE_DIR / "index_modulos.txt", OUTPUT_BASE / "01_sources" / "index_modulos.txt")
    copy_source(SOURCE_BASE / "course_manifest.json", OUTPUT_BASE / "01_sources" / "course_manifest_source.json")
    if MANUAL_PDF.exists():
        copy_source(MANUAL_PDF, OUTPUT_BASE / "01_sources" / "manual_original.pdf")

    write_json(OUTPUT_BASE / "01_sources" / "metadata.json", metadata)

    clean_transcript = build_clean_transcript(module_summaries, ambiguities)
    manual_extracted = build_manual_extracted(manual_sections)
    merged_clean = build_merged_clean_content(overview, module_summaries, manual_sections)

    write_text(OUTPUT_BASE / "02_clean" / "clean_transcript.txt", clean_transcript)
    write_text(OUTPUT_BASE / "02_clean" / "manual_extracted.txt", manual_extracted)
    write_text(OUTPUT_BASE / "02_clean" / "merged_clean_content.txt", merged_clean)

    write_json(OUTPUT_BASE / "03_academic" / "course_overview.json", course_overview)
    write_json(OUTPUT_BASE / "03_academic" / "concepts.json", concepts)
    write_json(OUTPUT_BASE / "03_academic" / "glossary.json", glossary)
    write_json(OUTPUT_BASE / "03_academic" / "module_summaries.json", module_summaries_json)
    write_json(OUTPUT_BASE / "03_academic" / "faq_candidates.json", faq_candidates)

    write_json(OUTPUT_BASE / "04_therapeutic" / "intake_questions.json", intake_questions)
    write_json(OUTPUT_BASE / "04_therapeutic" / "reasoning_patterns.json", reasoning_patterns)
    write_json(OUTPUT_BASE / "04_therapeutic" / "interpretation_guides.json", interpretation_guides)
    write_json(OUTPUT_BASE / "04_therapeutic" / "therapeutic_observations.json", therapeutic_observations)
    write_json(OUTPUT_BASE / "04_therapeutic" / "clinical_warnings.json", clinical_warnings)

    write_json(OUTPUT_BASE / "05_protocols" / "protocols.json", protocols)

    write_json(OUTPUT_BASE / "06_catalog" / "course_manifest.json", course_manifest_final)

    # También dejar extractos estructurados de secciones del manual como insumo de auditoría.
    manual_extract_dir = OUTPUT_BASE / "01_sources" / "manual_section_extracts"
    section_specs = {
        "cibertelepatia.txt": (26, 29),
        "area_de_rastreo.txt": (43, 45),
        "microbios_y_biomagnetismo.txt": (46, 64),
        "medicina_tradicional_china.txt": (160, 165),
        "meridianos_y_puntos.txt": (191, 327),
        "frecuencias_bioenergeticas.txt": (363, 365),
        "flores_de_bach.txt": (453, 455),
        "sales_de_schussler.txt": (495, 497),
        "protocolos_emocionales.txt": (501, 505),
        "condensados.txt": (511, 513),
    }
    for filename, (start, end) in section_specs.items():
        content = extract_pages(pages, start, end)
        write_text(manual_extract_dir / filename, content)

    # Inventario básico de módulos detectados.
    index_rows = []
    with (SOURCE_DIR / "index_modulos.txt").open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            index_rows.append(
                {
                    "modulo": row["modulo"],
                    "estado": row["estado"],
                    "nombre_bloque": row["nombre_bloque"],
                }
            )
    write_json(OUTPUT_BASE / "06_catalog" / "module_inventory.json", index_rows)

    transcript_inventory = []
    for item in transcript_modules:
        transcript_inventory.append(
            {
                "module_number": item["module_number"],
                "fecha_proceso": item["fecha_proceso"],
                "chars": len(item["raw_text"]),
            }
        )
    write_json(OUTPUT_BASE / "06_catalog" / "transcript_inventory.json", transcript_inventory)


if __name__ == "__main__":
    main()
