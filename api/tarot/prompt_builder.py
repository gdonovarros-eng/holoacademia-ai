"""
Constructor del prompt para la lectura de tarot.
Ensambla el perfil personal, las cartas de la tirada e instrucciones terapéuticas
para el LLM que actúa como terapeuta/acompañante — no como oráculo predictivo.
"""
from __future__ import annotations

from .knowledge import ARCANOS_MAYORES, ARCANOS_MENORES, TIRADAS, PALO_INFO

# ─── Descripción de enfoques ──────────────────────────────────────────────────

_ENFOQUE_DESC: dict[str, str] = {
    "terapeutico": (
        "Actúas como terapeuta holístico que usa el tarot como espejo psicológico. "
        "No predices el futuro — acompañas al consultante a explorar su mundo interior. "
        "Usas preguntas reflexivas, perspectiva junguiana y lenguaje de responsabilidad personal. "
        "El tarot describe energías y patrones, no destinos fijos."
    ),
    "orientativo": (
        "Actúas como guía que ofrece orientación práctica y claridad. "
        "Combinas la simbología de las cartas con consejos concretos y accionables. "
        "Tu tono es sabio pero accesible, inspirador pero realista."
    ),
    "espiritual": (
        "Actúas como guía espiritual que lee el tarot como lenguaje del Alma. "
        "Conectas las cartas con el camino espiritual del consultante, su propósito de vida "
        "y las lecciones que el Alma ha venido a aprender. "
        "Tu lenguaje es poético, profundo y reverente."
    ),
}

# ─── Etapas alquímicas (para profundidad 'profunda' — sistema Wynne) ─────────

_ETAPAS_ALQUIMICAS: list[dict] = [
    {"etapa": "Nigredo",     "descripcion": "La materia prima — lo que hay que ver y reconocer con valentía"},
    {"etapa": "Albedo",      "descripcion": "La purificación — separar lo esencial de lo accesorio"},
    {"etapa": "Citrinitas",  "descripcion": "El despertar — la conciencia que emerge del proceso"},
    {"etapa": "Rubedo",      "descripcion": "La integración — el oro que resulta de la transformación"},
    {"etapa": "Multiplicatio","descripcion": "La expansión — compartir la sabiduría adquirida"},
    {"etapa": "Projectio",   "descripcion": "La manifestación — llevar la transformación al mundo"},
    {"etapa": "Imaginatio",  "descripcion": "La imaginación activa — diálogo con las imágenes del tarot"},
]

# ─── Preguntas terapéuticas por área de vida ──────────────────────────────────

_PREGUNTAS_POR_AREA: dict[str, list[str]] = {
    "amor": [
        "¿Qué patrón relacional estás repitiendo?",
        "¿Qué necesitas recibir que te cuesta pedir?",
        "¿Amarte a ti mismo/a primero cómo cambiaría esta relación?",
    ],
    "trabajo": [
        "¿Tu trabajo refleja tu propósito o solo tu necesidad?",
        "¿Qué talento tuyo está infrautilizado?",
        "¿Qué miedo te impide dar el siguiente paso profesional?",
    ],
    "familia": [
        "¿Qué herida familiar estás repitiendo sin darte cuenta?",
        "¿Qué límite necesitas establecer con amor?",
        "¿Qué versión de ti mismo/a mostrarías si no tuvieras que cumplir expectativas?",
    ],
    "salud": [
        "¿Qué mensaje tiene tu cuerpo que aún no has querido escuchar?",
        "¿Qué emoción no expresada se manifiesta en tu cuerpo?",
        "¿Qué necesita tu cuerpo que aún no le estás dando?",
    ],
    "espiritual": [
        "¿Qué llamado de tu alma estás ignorando?",
        "¿Dónde buscas lo sagrado en tu vida cotidiana?",
        "¿Qué creencia sobre ti mismo/a necesita evolucionar?",
    ],
    "dinero": [
        "¿Qué creencia limitante tienes sobre merecer abundancia?",
        "¿El dinero para ti es seguridad, poder, o libertad?",
        "¿Qué relación tienes con dar y recibir en el plano material?",
    ],
    "general": [
        "¿Qué parte de esta situación depende realmente de ti?",
        "¿Qué necesitas soltar para avanzar?",
        "¿Qué sabiduría interior ya tienes sobre esto?",
    ],
}


def _detectar_area(pregunta: str) -> str:
    """Detecta el área de vida de la pregunta para adaptar las preguntas terapéuticas."""
    p = pregunta.lower()
    if any(w in p for w in ["amor", "pareja", "relación", "novio", "novia", "matrimonio", "separación"]):
        return "amor"
    if any(w in p for w in ["trabajo", "empleo", "carrera", "negocio", "profesión", "dinero", "economía"]):
        return "trabajo"
    if any(w in p for w in ["familia", "madre", "padre", "hijo", "hija", "hermano", "herencia"]):
        return "familia"
    if any(w in p for w in ["salud", "enfermedad", "cuerpo", "síntoma", "sanación", "curación"]):
        return "salud"
    if any(w in p for w in ["espiritual", "alma", "propósito", "sentido", "dios", "universo"]):
        return "espiritual"
    if any(w in p for w in ["dinero", "deuda", "abundancia", "finanzas", "económ", "ingresos"]):
        return "dinero"
    return "general"


def _palabras_carta(carta_nombre: str, invertida: bool) -> str:
    """Retorna las palabras clave de una carta (upright o sombra)."""
    datos = ARCANOS_MENORES.get(carta_nombre) or next(
        (v for v in ARCANOS_MAYORES.values() if v["nombre_rws"] == carta_nombre
         or v["nombre_marsella"] == carta_nombre),
        None,
    )
    if not datos:
        return ""
    if invertida:
        return ", ".join(datos.get("sombra", []))
    return ", ".join(datos.get("palabras_clave", []))


def _pregunta_terapeutica_carta(carta_nombre: str) -> str:
    """Retorna la pregunta terapéutica de una carta."""
    datos = ARCANOS_MENORES.get(carta_nombre) or next(
        (v for v in ARCANOS_MAYORES.values() if v["nombre_rws"] == carta_nombre),
        None,
    )
    return datos.get("pregunta_terapeutica", "") if datos else ""


def _bloque_perfil(perfil: dict) -> str:
    """Construye el bloque de perfil tarótico personal."""
    if not perfil:
        return ""

    lineas = ["\n▸ PERFIL TARÓTICO DEL CONSULTANTE"]

    pers = perfil.get("personalidad", {})
    if pers:
        lineas.append(
            f"  Carta de Personalidad: {pers.get('nombre', '—')} (#{pers.get('numero', '?')}) "
            f"— {', '.join(pers.get('datos', {}).get('palabras_clave', []))}"
        )

    alma = perfil.get("alma", {})
    if alma:
        lineas.append(
            f"  Carta del Alma:        {alma.get('nombre', '—')} (#{alma.get('numero', '?')}) "
            f"— {', '.join(alma.get('datos', {}).get('palabras_clave', []))}"
        )

    oculto = perfil.get("factor_oculto", {})
    if oculto:
        lineas.append(
            f"  Factor Oculto:         {oculto.get('nombre', '—')} (#{oculto.get('numero', '?')}) "
            f"— energía complementaria a integrar"
        )

    anio = perfil.get("anio_personal", {})
    actual = anio.get("actual", {})
    if actual:
        lineas.append(
            f"  Año Personal {actual.get('anio', '')}: {actual.get('nombre', '—')} "
            f"— {', '.join(actual.get('datos', {}).get('palabras_clave', [])[:3])}"
        )

    zodiaco = perfil.get("carta_zodiaco", {})
    if zodiaco and zodiaco.get("nombre"):
        lineas.append(f"  Arcano del Signo:      {zodiaco.get('nombre', '—')} ({zodiaco.get('signo', '').capitalize()})")

    persona = perfil.get("carta_persona", {})
    if persona and persona.get("nombre"):
        lineas.append(f"  Carta de Persona:      {persona.get('nombre', '—')}")

    leccion = perfil.get("leccion_zodiacal", {})
    if leccion and leccion.get("nombre"):
        lineas.append(f"  Lección Zodiacal:      {leccion.get('nombre', '—')} (decanato de nacimiento)")

    return "\n".join(lineas) + "\n"


def build_tarot_prompt(
    pregunta: str,
    tirada_nombre: str,
    cartas: list[dict],   # [{"posicion": str, "carta": str, "invertida": bool}]
    perfil: dict | None = None,
    profundidad: str = "estandar",   # "rapida" | "estandar" | "profunda"
    enfoque: str = "terapeutico",    # "terapeutico" | "orientativo" | "espiritual"
    sistema: str = "rws",
) -> str:
    """
    Construye el prompt completo para la lectura de tarot.

    Incluye:
    1. Rol e instrucciones de enfoque
    2. Perfil personal (si disponible)
    3. Pregunta del consultante
    4. Cartas con posiciones y palabras clave
    5. Instrucciones de estructura según profundidad
    6. Preguntas terapéuticas sugeridas
    """

    # ── Enfoque e instrucciones del rol ────────────────────────────────────────
    enfoque_desc = _ENFOQUE_DESC.get(enfoque, _ENFOQUE_DESC["terapeutico"])
    tirada_info = TIRADAS.get(tirada_nombre, {})
    tirada_display = tirada_info.get("nombre", tirada_nombre)

    area = _detectar_area(pregunta)
    preguntas_area = _PREGUNTAS_POR_AREA.get(area, _PREGUNTAS_POR_AREA["general"])

    # ── Bloque introductorio ────────────────────────────────────────────────────
    intro = f"""Eres un experto en tarot terapéutico con profunda formación en psicología junguiana, simbología esotérica y acompañamiento holístico.

{enfoque_desc}

Sistema de tarot: {sistema.upper()}
Tirada: {tirada_display}

══════════════════════════════════════════════════════════════════
PREGUNTA / INTENCIÓN DEL CONSULTANTE:
"{pregunta}"
══════════════════════════════════════════════════════════════════
"""

    # ── Perfil personal ─────────────────────────────────────────────────────────
    perfil_bloque = _bloque_perfil(perfil) if perfil else ""

    # ── Cartas en sus posiciones ────────────────────────────────────────────────
    cartas_bloque = "\n▸ CARTAS REVELADAS EN LA TIRADA\n"
    for i, entrada in enumerate(cartas, 1):
        pos = entrada.get("posicion", f"Posición {i}")
        carta_nombre = entrada.get("carta", "Carta desconocida")
        invertida = entrada.get("invertida", False)

        estado = " [INVERTIDA / SOMBRA]" if invertida else " [UPRIGHT]"
        kw = _palabras_carta(carta_nombre, invertida)
        pt = _pregunta_terapeutica_carta(carta_nombre)

        cartas_bloque += f"\n  [{i}] {pos.upper()}\n"
        cartas_bloque += f"      Carta: {carta_nombre}{estado}\n"
        if kw:
            cartas_bloque += f"      Palabras clave: {kw}\n"
        if pt:
            cartas_bloque += f"      Pregunta terapéutica de la carta: {pt}\n"

    # ── Instrucciones según profundidad ────────────────────────────────────────
    if profundidad == "rapida":
        instrucciones = f"""
══════════════════════════════════════════════════════════════════
INSTRUCCIONES (lectura rápida — 3 secciones):

## 1. El mensaje central
Integra las cartas y la pregunta en 2-3 párrafos. Identifica el tema principal que emerge.

## 2. Las cartas hablan
Para cada carta, 2-3 frases sobre lo que aporta a la pregunta del consultante.

## 3. Sugerencia para integrar
Una propuesta concreta de reflexión o acción que el consultante pueda aplicar.

Preguntas para invitar a la reflexión:
{chr(10).join('- ' + p for p in preguntas_area)}

Tono: empático y directo. Máximo 600 palabras. Solo en español."""

    elif profundidad == "profunda":
        etapas_txt = "\n".join(
            f"  {e['etapa']}: {e['descripcion']}"
            for e in _ETAPAS_ALQUIMICAS
        )
        instrucciones = f"""
══════════════════════════════════════════════════════════════════
INSTRUCCIONES (lectura profunda — 7 secciones + imaginación activa):

## 1. El campo de la tirada
Describe la energía general que emerge de la disposición de las cartas. Qué tema arquetípico subyace.

## 2. Las cartas en diálogo
Analiza cada carta en su posición. No de forma aislada — en conversación con las cartas adyacentes.
¿Cómo se complementan o tensionan las energías?

## 3. La sombra presente
¿Qué cartas invertidas o de sombra revelan? ¿Qué patrón inconsciente está activo?

## 4. El patrón alquímico
Usa el proceso alquímico para describir la transformación que la tirada sugiere:
{etapas_txt}

## 5. El eje del perfil personal
Si hay perfil tarótico: ¿cómo dialogan la Carta de Personalidad y el Año Personal con la tirada?
¿Qué coherencia o tensión hay entre quien es el consultante y lo que enfrenta?

## 6. Preguntas para la sesión terapéutica
Ofrece 4-5 preguntas profundas que el terapeuta podría usar en sesión, basadas en las cartas.
Incluye estas áreas si son relevantes:
{chr(10).join('- ' + p for p in preguntas_area)}

## 7. Imaginación activa
Propón un ejercicio de imaginación activa (estilo junguiano) basado en la imagen más significativa
de la tirada. El consultante cierra los ojos, entra en la imagen de la carta y dialoga con ella.
Describe paso a paso la guía.

Tono: profundo, poético y terapéutico. Solo en español."""

    else:  # estandar
        instrucciones = f"""
══════════════════════════════════════════════════════════════════
INSTRUCCIONES (lectura estándar — 5 secciones):

## 1. El campo energético
Describe en 1-2 párrafos la energía general que emerge de las cartas juntas.
¿Qué arquetipo o proceso psicológico está activo?

## 2. Las cartas en su contexto
Para cada carta en su posición: qué dice sobre la pregunta del consultante,
qué sombra o luz está presente, y cómo se conecta con las otras cartas.

## 3. El hilo narrativo
Teje las cartas en una historia coherente que responda a la pregunta del consultante.
¿Cuál es la narrativa que emerge?

## 4. Reflexiones terapéuticas
Ofrece 3-4 preguntas reflexivas para que el consultante explore desde las cartas:
{chr(10).join('- ' + p for p in preguntas_area)}
¿Qué acción pequeña y concreta podrían tomar esta semana?

## 5. Síntesis
2-3 frases de cierre que integren el mensaje más importante de la lectura.
Tono de empoderamiento y responsabilidad personal — no de predicción.

Tono: empático, profundo y orientado al crecimiento. Solo en español."""

    # ── Ensamblaje final ────────────────────────────────────────────────────────
    return intro + perfil_bloque + cartas_bloque + instrucciones
