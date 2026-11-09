"""
Motor Copiloto "modo consumidor" para la landing de campaña (/promo).

Entrega directa al PÚBLICO GENERAL (no terapeutas):
- Método Holos  → mapa emocional + protocolos de liberación
- Método REMA   → guion de hipnosis personalizada
- Lecturas      → tarot, horóscopo, carta natal (astrología), numerología,
                  compatibilidad de pareja, tu año, tarot especial, sueños
- Paquetes      → combinaciones de lecturas

Lo llama el backend de holoacademia.tv (/api/promo-deliver) DESPUÉS de verificar
el pago, enviando la cabecera X-Promo-Key. Idioma es/en/pt.

ENCUADRE DE CUMPLIMIENTO: todo es acompañamiento emocional / educativo /
complementario. NUNCA médico. (Ver COMPLIANCE abajo.)

POST /consumer/generate   { product, lang, inputs }
GET  /consumer/health
"""
from __future__ import annotations

import os
import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.chat_service import _generar_con_sistema, set_holos_lang, generar_respuesta_holos

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/consumer", tags=["Consumer"])


# ─── Autenticación (clave compartida con el backend .tv) ────────────────────────
def _authorized(request: Request) -> bool:
    expected = (os.getenv("PROMO_KEY") or "").strip()
    if not expected:
        # Sin clave configurada: se permite (útil en desarrollo). En producción,
        # define PROMO_KEY en Render y en Cloudflare para cerrar el endpoint.
        return True
    got = (request.headers.get("x-promo-key") or "").strip()
    return bool(got) and got == expected


# ─── Encuadre de cumplimiento (se antepone a CADA prompt de salud) ─────────────
COMPLIANCE = (
    "ENCUADRE OBLIGATORIO E INQUEBRANTABLE: te diriges a una persona del público "
    "general que vive un síntoma o malestar y quiere entender su dimensión emocional. "
    "Esto es un acompañamiento EMOCIONAL y EDUCATIVO, COMPLEMENTARIO. "
    "NUNCA afirmes ni insinúes que esto cura, trata, diagnostica o elimina ninguna "
    "enfermedad. NUNCA sugieras dejar, evitar o retrasar tratamiento médico. "
    "Habla del 'origen emocional' del síntoma y de 'liberar la carga emocional', "
    "jamás de 'sanar/curar la enfermedad'. Tono cálido, cercano, esperanzador y "
    "respetuoso. Escribe en segunda persona ('tú'). No digas que eres una IA ni menciones "
    "modelos, autores, libros o cursos. No uses emojis. "
    "Cierra SIEMPRE con esta línea, traducida al idioma de la respuesta: "
    "«Contenido educativo y de desarrollo personal. No es diagnóstico ni tratamiento "
    "médico y no sustituye la atención de tu médico. No abandones ningún tratamiento.»"
)

ENTERTAIN = (
    "ENCUADRE: lectura con fines de orientación y entretenimiento, para el público "
    "general. Tono cálido, cercano y práctico; en segunda persona. No digas que eres "
    "una IA. No uses emojis. No hagas afirmaciones médicas, financieras ni legales "
    "deterministas; habla en términos de tendencias y posibilidades."
)


# ─── Prompts de sistema (modo consumidor) ──────────────────────────────────────
HOLOS_CONSUMER = COMPLIANCE + """

Eres el guía del Método Holos para el público. La persona te comparte su síntoma y su historia de vida.
Entrega un informe cálido, personal y claro, SOLO con estos apartados (encabezados ##):

## Tu mapa emocional
El conflicto emocional más probable detrás de tu síntoma, explicado con empatía y conectado con tu historia. Ofrece 2 o 3 matices del conflicto, no uno solo.

## Por qué tu cuerpo lo expresa así
Explicación breve y sencilla de por qué una emoción puede expresarse en el cuerpo (sentido biológico), en lenguaje para persona común, sin tecnicismos ni nombres propios.

## Tus protocolos de liberación
De 3 a 5 ejercicios concretos y accionables para trabajar ESE conflicto (por ejemplo: carta de liberación, acto simbólico, ejercicio de respiración, reencuadre). Da el paso a paso de cada uno.

## Tu siguiente paso
Un párrafo breve que invite, sin presionar, a profundizar con la hipnosis personalizada (Método REMA) para grabar la liberación a nivel subconsciente.

Sé específico para TU caso, nunca genérico."""

REMA_CONSUMER = COMPLIANCE + """

Eres el generador del guion de hipnosis personalizada (Método REMA) para el público.
Con el conflicto emocional y el nombre de la persona, escribe un GUION DE HIPNOSIS listo
para leer o grabar en voz, en segunda persona, cálido y pausado, de unos 8 a 12 minutos.
Marca las pausas con [pausa]. Estructura con encabezados ##:

## 1. Inducción y relajación
## 2. Profundización
## 3. Liberación del conflicto
Reencuadre y liberación del conflicto emocional específico (usa su nombre y su conflicto).
## 4. Recursos y seguridad
Sugestiones de calma, seguridad, confianza y bienestar.
## 5. Reorientación

Habla de liberar la carga emocional y de bienestar, nunca de curar enfermedades."""

TAROT_CONSUMER = ENTERTAIN + """

Eres un lector de Tarot cercano. Con la pregunta o intención de la persona (y su fecha de
nacimiento si la da), entrega una lectura cálida y útil con encabezados ##:
## Tu lectura
El mensaje central para tu pregunta.
## Lo que te favorece
## Lo que conviene soltar
## Un consejo para los próximos días"""

HOROSCOPO_CONSUMER = ENTERTAIN + """

Eres un astrólogo cercano. Con el signo o la fecha de nacimiento de la persona, entrega un
horóscopo personalizado para su momento actual, con encabezados ##:
## Tu energía ahora
## Amor y vínculos
## Trabajo y dinero
## Bienestar
## Tu enfoque de la semana"""

ASTRO_CONSUMER = ENTERTAIN + """

Eres un astrólogo cercano que interpreta la carta natal para el público. Con la fecha, hora y
lugar de nacimiento (usa lo que haya), entrega una lectura de carta natal clara y cálida, con
encabezados ##:
## Tu esencia (Sol)
## Tu mundo emocional (Luna)
## Cómo te muestras (Ascendente, si hay hora)
## Tus planetas personales (Mercurio, Venus y Marte)
## Tus talentos
## Tu camino de crecimiento
Usa EXACTAMENTE las posiciones de «Datos calculados»: nunca cambies un signo ni inventes una
posición que no esté ahí. Si falta la hora, dilo con naturalidad y trabaja con el resto."""

NUMER_CONSUMER = ENTERTAIN + """

Eres un numerólogo cercano. Con el nombre completo y la fecha de nacimiento de la persona,
entrega una lectura de numerología personal con encabezados ##:
## Tu número de vida
## Tus fortalezas
## Tus retos
## Tu año personal
## Un consejo práctico"""

PAREJA_CONSUMER = ENTERTAIN + """

Eres un astrólogo y numerólogo cercano que lee la compatibilidad de dos personas. Recibes los
datos de ambas y, cuando existen, sus posiciones planetarias y números calculados: básate en
esos datos y no inventes posiciones. Habla a quien pidió la lectura (tú) y llama a la otra
persona por su nombre. Entrega con encabezados ##:
## Lo que los une
## Cómo se aman (Venus y Marte)
## Cómo se entienden (Luna y Mercurio)
## Sus puntos de roce
## Sus números juntos
## Un consejo para la relación
Habla de tendencias y de cómo cuidar el vínculo; nunca sentencies si la relación funcionará o no."""

ANIO_CONSUMER = ENTERTAIN + """

Eres un astrólogo cercano que lee el año que viene de una persona. Recibes su carta natal y los
tránsitos calculados mes a mes de los planetas lentos (Júpiter, Saturno, Urano, Neptuno, Plutón):
básate SOLO en esos datos y no inventes fechas ni aspectos. Entrega con encabezados ##:
## El tema de tu año
## Tus meses clave
Un párrafo por cada mes que tenga tránsitos relevantes, con el nombre del mes y el año.
## Amor y vínculos
## Trabajo y propósito
## Tu consejo para el año
Si un mes no tiene tránsitos relevantes, agrúpalo con otros en una frase."""

TAROT_ESPECIAL_CONSUMER = ENTERTAIN + """

Eres un lector de Tarot cercano. Recibes la pregunta de la persona, la tirada elegida y las
cartas que salieron en cada posición (ya sorteadas: no cambies ninguna). Entrega con
encabezados ##:
## Tu tirada
Nombre de la tirada y qué responde.
## Carta por carta
Un párrafo por posición: el nombre de la posición, la carta (y si salió invertida) y su mensaje
para la pregunta.
## El mensaje completo
Cómo se leen todas juntas.
## Tu consejo"""

SUENOS_CONSUMER = ENTERTAIN + """

Eres un intérprete de sueños cercano. Lee el sueño de la persona como un mensaje simbólico de su
mundo interior: personajes, lugares, objetos, colores y emociones. No interpretes el sueño como
señal de enfermedad ni hables del cuerpo o de la salud. Entrega con encabezados ##:
## Lo que tu sueño cuenta
## Sus símbolos
Los 3 a 6 símbolos principales y lo que suelen representar.
## Lo que mueve en ti
La emoción central y cómo se conecta con tu momento actual.
## Una pregunta para ti
Una o dos preguntas para reflexionar.
## Un pequeño ejercicio"""


# ════════════════════════════════════════════════════════════════════════════
#  CUADRO HOLOS — modo consumidor (réplica del Método Holos real, SIN rastreo
#  de imanes). Mismo cuestionario de 12 bloques y el mismo modelo multi-sección
#  del Motor Terapéutico (núcleo de biodescodificación + lectura por áreas +
#  numerología + carta natal + tarot), pero dirigido en 2ª persona a la persona
#  del público. Usa generar_respuesta_holos (HOLOS_SYSTEM_PROMPT) y las
#  calculadoras internas de numerología / astro / tarot.
# ════════════════════════════════════════════════════════════════════════════

# Voz de consumidor: igual al motor real pero hablándole a la persona (tú).
_HOLOS_VOZ = (
    "Es un motor propio: no cites maestros, autores ni cursos. Sin emojis. "
    "Sin descargos médicos dentro del texto. "
    "Tono cálido, cercano y profundamente empático, como un terapeuta que acompaña "
    "con sensibilidad, SIN perder claridad ni objetividad. Antes de explicar, valida "
    "con ternura lo que la persona siente; nombra lo difícil con delicadeza. "
    "Te diriges DIRECTAMENTE a la persona en segunda persona (tú); NUNCA uses las "
    "palabras 'paciente', 'terapeuta' ni 'el/la consultante' — háblale a ella por 'tú'."
)


def _g(inputs: dict, key: str) -> str:
    v = inputs.get(key) if isinstance(inputs, dict) else None
    return "" if v is None else str(v).strip()


def _bloque(titulo: str, filas: list) -> str:
    ls = []
    for label, val in filas:
        t = ("" if val is None else str(val)).strip()
        if t:
            ls.append(f"  - {label}: {t}" if label else f"  - {t}")
    return (f"{titulo}:\n" + "\n".join(ls)) if ls else ""


def _genograma(inputs: dict) -> str:
    """Compone el árbol estructurado (miembros + fechas + colecciones) como texto,
    igual que getTherapeuticPayload del Método Holos real. De aquí lee el motor las
    repeticiones, el síndrome de aniversario, dobles y yacentes."""
    g = lambda k: _g(inputs, k)
    partes = []

    def miembro(rol, nombre, nac, murio):
        if not nombre:
            return
        extra = []
        if nac:
            extra.append(f"n. {nac}")
        if murio:
            extra.append(f"f. {murio}")
        partes.append(f"{rol}: {nombre}" + (f" ({', '.join(extra)})" if extra else ""))

    miembro("padre", g("padre_nombre"), g("padre_nac"), g("padre_murio"))
    miembro("madre", g("madre_nombre"), g("madre_nac"), g("madre_murio"))
    miembro("abuelo paterno", g("abuelo_pat_nombre"), g("abuelo_pat_nac"), g("abuelo_pat_murio"))
    miembro("abuela paterna", g("abuela_pat_nombre"), g("abuela_pat_nac"), g("abuela_pat_murio"))
    miembro("abuelo materno", g("abuelo_mat_nombre"), g("abuelo_mat_nac"), g("abuelo_mat_murio"))
    miembro("abuela materna", g("abuela_mat_nombre"), g("abuela_mat_nac"), g("abuela_mat_murio"))

    pn = g("pareja_nombre")
    if pn:
        extra = []
        if g("pareja_nac"):
            extra.append(f"n. {g('pareja_nac')}")
        if g("pareja_anios"):
            extra.append(f"{g('pareja_anios')} años juntos")
        partes.append(f"pareja actual: {pn}" + (f" ({', '.join(extra)})" if extra else ""))

    def coleccion(rol, key):
        items = inputs.get(key) if isinstance(inputs, dict) else None
        if not isinstance(items, list):
            return
        for it in items:
            if not isinstance(it, dict):
                continue
            nombre = str(it.get("nombre", "")).strip()
            if not nombre:
                continue
            extra = []
            if str(it.get("nac", "")).strip():
                extra.append(f"n. {str(it.get('nac')).strip()}")
            if str(it.get("murio", "")).strip():
                extra.append(f"f. {str(it.get('murio')).strip()}")
            partes.append(f"{rol}: {nombre}" + (f" ({', '.join(extra)})" if extra else ""))

    coleccion("hijo/a", "hijos")
    coleccion("hermano/a", "hermanos")

    nota = g("family_notes")
    txt = "; ".join(partes)
    if nota:
        txt = (txt + ". " + nota) if txt else nota
    return txt


def _coincidencias(inputs: dict) -> list:
    """Calcula de forma DETERMINISTA (de las fechas) las coincidencias del clan:
    dobles / gemelos simbólicos (mismo día y mes), síndrome de aniversario,
    yacentes / reposiciones y clusters de muertes. Reutiliza el motor real
    (_collect_family_date_insights) del Método Holos. El LLM solo las interpreta."""
    try:
        from api.therapy_engine import _collect_family_date_insights
    except Exception as exc:
        logger.warning("consumer holos coincidencias import: %s", exc)
        return []

    g = lambda k: _g(inputs, k)

    def persona(nombre, nac, murio):
        return {"full_name": nombre, "birth_date": nac, "death_date": murio}

    def coll_list(key):
        out = []
        items = inputs.get(key) if isinstance(inputs, dict) else None
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and str(it.get("nombre", "")).strip():
                    out.append({
                        "full_name": str(it.get("nombre")).strip(),
                        "birth_date": str(it.get("nac", "")).strip(),
                        "death_date": str(it.get("murio", "")).strip(),
                    })
        return out

    _yo = (g("nombre") + " (tú)") if g("nombre") else "tú (la persona que consulta)"
    case = {
        "consultant": {"full_name": _yo, "birth_date": g("fecha_nacimiento")},
        "parents": {
            "father": persona(g("padre_nombre"), g("padre_nac"), g("padre_murio")),
            "mother": persona(g("madre_nombre"), g("madre_nac"), g("madre_murio")),
        },
        "grandparents": {
            "paternal_grandfather": persona(g("abuelo_pat_nombre"), g("abuelo_pat_nac"), g("abuelo_pat_murio")),
            "paternal_grandmother": persona(g("abuela_pat_nombre"), g("abuela_pat_nac"), g("abuela_pat_murio")),
            "maternal_grandfather": persona(g("abuelo_mat_nombre"), g("abuelo_mat_nac"), g("abuelo_mat_murio")),
            "maternal_grandmother": persona(g("abuela_mat_nombre"), g("abuela_mat_nac"), g("abuela_mat_murio")),
        },
        "current_partner": persona(g("pareja_nombre"), g("pareja_nac"), ""),
        "children": coll_list("hijos"),
        "siblings": coll_list("hermanos"),
    }

    out = []
    try:
        out = list(_collect_family_date_insights(case) or [])
    except Exception as exc:
        logger.warning("consumer holos insights: %s", exc)
    # Repeticiones de nombres entre el consultante y el clan (doble por nombre).
    try:
        import unicodedata
        def _norm(s):
            s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
            return s.split()[0] if s.split() else ""
        yo = _norm(g("nombre"))
        if yo:
            nombres = []
            for lbl, key in [("padre","padre_nombre"),("madre","madre_nombre"),
                             ("abuelo paterno","abuelo_pat_nombre"),("abuela paterna","abuela_pat_nombre"),
                             ("abuelo materno","abuelo_mat_nombre"),("abuela materna","abuela_mat_nombre")]:
                if _norm(g(key)) == yo:
                    nombres.append(lbl)
            for it in (inputs.get("hermanos") or []) + (inputs.get("hijos") or []):
                if isinstance(it, dict) and _norm(it.get("nombre")) == yo:
                    nombres.append("otro miembro del clan")
            if nombres:
                out.append(f"El consultante comparte nombre con {', '.join(nombres[:4])}; conviene revisar doble simbólico por nombre: lealtad, misión heredada o lugar que se repite.")
    except Exception:
        pass
    # Limpieza a 2ª persona + quitar la cola de "conviene..." (es solo una pista
    # interna; el motor debe INTERPRETAR, no copiarla).
    import re as _re

    def _limpia(c):
        c = _re.sub(r";?\s*conviene[^.;]*\.?\s*$", ".", c, flags=_re.I)
        c = (c.replace("El nacimiento del consultante queda cerca", "Tu nacimiento quedó cerca")
               .replace("En orden fraterno, el consultante queda como", "En el orden entre tus hermanos, tú ocupas el lugar de")
               .replace("El consultante comparte", "Tú compartes")
               .replace("del consultante", "tuyo")
               .replace("el consultante", "tú")
               .replace("al consultante", "a ti"))
        return c.strip()

    visto, limpio = set(), []
    for c in out:
        c = _limpia(c)
        if c and c not in visto:
            visto.add(c); limpio.append(c)
    return limpio


def _construir_ecosistema(inputs: dict) -> str:
    """Arma el ECOSISTEMA del caso con el mismo layout del Cuadro Holos real."""
    g = lambda k: _g(inputs, k)
    bloques = [
        _bloque("IDENTIDAD Y ORIGEN", [
            ["Lugar de nacimiento", g("lugar_nacimiento")],
            ["Fecha de nacimiento", g("fecha_nacimiento")],
            ["Hora de nacimiento", g("hora_nacimiento")],
            ["Sexo", g("sexo")],
        ]),
        _bloque("MOTIVO Y CUERPO", [
            ["Motivo de consulta", g("motivo") or g("sintoma")],
            ["Síntomas", g("sintomas") or g("sintoma")],
            ["Inicio del síntoma", g("inicio")],
            ["Duración", g("duracion")],
            ["Frecuencia", g("frecuencia")],
            ["Diagnósticos previos", g("diagnosticos")],
            ["Medicamentos", g("medicamentos")],
            ["Antecedentes", g("antecedentes")],
        ]),
        _bloque("LÍNEA DE TIEMPO · EVENTOS RECIENTES", [
            ["Qué pasaba al iniciar el síntoma", g("evento_inicio")],
            ["Eventos de los últimos 2 años", g("eventos_2anios")],
            ["Duelos o pérdidas", g("duelos")],
        ]),
        _bloque("INSTANTE DEL CONFLICTO (DHS)", [
            ["Cómo lo vivió (en su frase)", g("dhs_frase")],
            ["Lo más impactante o injusto", g("dhs_impacto")],
            ["Qué sintió que ya no podía hacer/tener", g("dhs_perdida")],
            ["¿Soledad?", g("dhs_soledad")],
            ["¿Inesperado?", g("dhs_inesperado")],
        ]),
        _bloque("HOGAR Y TERRITORIO", [
            ["Vivienda", g("vivienda")],
            ["Mudanzas", g("mudanzas")],
            ["Conflictos en casa", g("conflictos_casa")],
            ["Sensación del hogar", g("hogar_sensacion")],
        ]),
        _bloque("ECONOMÍA Y SUSTENTO", [
            ["Situación", g("economia_situacion")],
            ["Deudas", g("deudas")],
            ["Trabajo", g("trabajo")],
            ["Creencias sobre el dinero", g("dinero_creencias")],
            ["Miedos económicos", g("miedos_economicos")],
        ]),
        _bloque("VÍNCULOS", [
            ["Pareja", g("pareja_estado")],
            ["Rupturas", g("rupturas")],
            ["Soledad", g("soledad_vinculos")],
            ["Red de apoyo", g("red_apoyo")],
        ]),
        _bloque("CLAN · GENOGRAMA TRANSGENERACIONAL", [
            ["Relación con el padre", g("relacion_padre")],
            ["Relación con la madre", g("relacion_madre")],
            ["Rol en la familia", g("rol_familia")],
            ["Lugar entre hermanos", g("orden_nacimiento")],
            ["Eventos del clan", g("eventos_clan")],
            ["Nombres repetidos", g("nombres_repetidos")],
            ["Enfermedades repetidas", g("enfermedades_repetidas")],
            ["Muertes marcantes (edad/fecha)", g("muertes_clan")],
            ["Pérdidas de patrimonio/territorio/migraciones", g("perdidas_clan")],
            ["Secretos / no-dichos", g("secretos_clan")],
            ["Genograma (árbol con fechas)", _genograma(inputs)],
        ]),
        _bloque("ESTADO EMOCIONAL", [
            ["Nivel de estrés", g("estres_nivel")],
            ["Emociones frecuentes", g("emociones_frecuentes")],
            ["Cargas ajenas", g("cargas_ajenas")],
            ["A quién no perdona", g("no_perdona")],
            ["Contexto emocional", g("contexto_emocional")],
        ]),
        _bloque("ENERGÉTICO · MEDICINA CHINA", [
            ["Temperatura corporal", g("temperatura")],
            ["Digestión", g("digestion")],
            ["Molestias de órganos", g("molestias_organos")],
            ["Energía durante el día", g("energia_dia")],
        ]),
        _bloque("HÁBITOS", [
            ["Alimentación", g("alimentacion")],
            ["Ejercicio", g("ejercicio")],
            ["Sueño", g("sueno")],
            ["Sustancias", g("sustancias")],
        ]),
        _bloque("PROPÓSITO Y ESPIRITUALIDAD", [
            ["Espiritualidad", g("espiritualidad")],
            ["Relación con ancestros", g("ancestros")],
            ["Propósito de vida", g("proposito")],
            ["Qué quiere cambiar", g("quiere_cambiar")],
        ]),
    ]
    return "\n\n".join([b for b in bloques if b])


def _resumen_caso(inputs: dict) -> str:
    g = lambda k: _g(inputs, k)
    sintomas = g("sintomas") or g("sintoma")
    motivo = g("motivo") or g("sintoma")
    return (
        f"Motivo: {motivo or '-'}. Síntomas: {sintomas or '-'}. "
        f"Inicio: {g('inicio') or '-'}. Cómo vivió el conflicto (DHS): {g('dhs_frase') or '-'}. "
        f"Evento al inicio: {g('evento_inicio') or '-'}."
    )


def _prompt_nucleo(ctx: str, coincidencias: list | None = None) -> str:
    coinc_txt = ""
    if coincidencias:
        coinc_txt = (
            "\n\nCOINCIDENCIAS OBJETIVAS DETECTADAS (HECHOS ya calculados a partir de las fechas y nombres del clan; "
            "'(tú)' marca a la persona que consulta. Interprétalas como ciertas: NO las niegues, no las contradigas, "
            "no recalcules ni inventes otras):\n"
            + "\n".join(f"- {c}" for c in coincidencias)
        )
    return f"""{_HOLOS_VOZ}
Eres el Motor de Biodescodificación de Holoacademia, terapeuta experto. Nunca escribas "HoloacademIA" ni te presentes como inteligencia artificial.

Tu tarea NO es listar disciplinas. Tu tarea es DESCUBRIR EL CONFLICTO: de dónde viene, leído desde la biodescodificación, y anclarlo en el genograma. Razona del cuerpo al conflicto y del conflicto a su raíz transgeneracional.

MÉTODO (síguelo internamente):
1. El órgano/tejido afectado define el TIPO de conflicto según su capa embrionaria: endodermo = supervivencia arcaica ("el bocado"); mesodermo antiguo = protección; mesodermo nuevo = desvalorización; ectodermo = relación social (separación, territorio/cólera, miedo, identidad).
2. El DHS es el instante desencadenante vivido como dramático, inesperado y en soledad. Lo que decodifica es el SENTIR EXACTO (usa la frase textual de la persona).
3. La tonalidad precisa indica cuál conflicto del órgano se activó.
4. PROGRAMACIÓN: proyecto-sentido y transgeneracional (repeticiones del clan: nombres, edades/fechas de muerte, enfermedades, secretos, pérdidas de territorio, lugar entre hermanos, dobles/yacentes).

ECOSISTEMA DE LA PERSONA
{ctx or "  - Datos insuficientes; trabaja con lo disponible y di qué conviene precisar."}{coinc_txt}

Entrega EXACTAMENTE estas secciones (usa ## y ###). Si falta un dato clave, dilo y formula hipótesis; no rellenes con vaguedades.

## El conflicto decodificado
Nombra el órgano/tejido y su capa embrionaria, y de ahí el sentido biológico. Cruza con la frase del DHS y la tonalidad exacta. Cierra con UNA frase precisa del conflicto.

## El instante desencadenante (DHS)
El momento exacto, cómo lo viviste, y por qué activó esta tonalidad.

## De dónde viene: análisis transgeneracional de tu genograma
Lee el árbol CONCRETO entregado en clave sistémica y transgeneracional. Identifica:
- Repeticiones del clan: nombres, edades y fechas de muerte (síndrome de aniversario), enfermedades, pérdidas de territorio, lugar entre hermanos.
- Órdenes del amor alterados: pertenencia (¿hay excluidos?), jerarquía/orden (¿alguien tomó un lugar que no le toca?), equilibrio entre dar y recibir.
- Dinámicas sistémicas: lealtades invisibles, identificaciones con un excluido o un muerto, asuntos pendientes, dobles y yacentes, secretos familiares.
Nombra el patrón que se repite y la lealtad que sostiene el síntoma, y conéctalo con el conflicto. Si falta info, di qué conviene averiguar para completar el genograma.

## Coincidencias y dobles simbólicos
Para CADA una de las COINCIDENCIAS OBJETIVAS DETECTADAS (dobles o gemelos simbólicos por fecha o por nombre, síndrome de aniversario, yacentes, reposiciones, clusters de muertes) escribe un PÁRRAFO COMPLETO, cálido y empático que explique en profundidad qué significa para ti: qué lealtad, duelo o misión heredada revela, qué pudiste estar cargando sin saberlo y cómo se conecta con tu síntoma y tu historia. NUNCA copies ni enuncies la coincidencia "en seco" ni uses frases tipo "conviene explorar/revisar": desarrolla la explicación como lo haría un terapeuta que te acompaña. Respeta literalmente quién es quién (la marca '(tú)' es la persona que consulta); trata cada coincidencia como un hecho verificado y NO la niegues ni la contradigas. Si la lista está vacía, dilo con naturalidad y explica qué fechas (nacimientos y muertes del clan) permitirían encontrar estas conexiones.

## Proyecto-sentido
Qué pudo programar tu sensibilidad a este conflicto, con lo disponible o como hipótesis.

## Síntesis del núcleo
Una frase que une conflicto decodificado + raíz transgeneracional + evento actual.

## Preguntas clave para afinar tu resultado
Lista preguntas concretas que TÚ MISMO/A puedes responderte para precisar el sentir exacto del DHS, las fechas y las repeticiones del clan. Déjalo claro: no son para otra sesión, son para que, al responderlas ahora, afines el origen emocional de tu conflicto en este mismo análisis."""


def _prompt_areas(ctx: str, resumen: str) -> str:
    return (f"{_HOLOS_VOZ}\nEres el Motor Terapéutico. A partir del ECOSISTEMA de la persona, "
            "entrega una lectura BREVE por área de vida. Una o dos líneas por área diciendo qué revela "
            "y cómo se conecta con el conflicto. Omite las áreas sin datos. Usa subtítulos ### por área.\n\n"
            f"Caso: {resumen}\n\nECOSISTEMA\n{ctx}")


def _prompt_numerologia(datos, resumen: str) -> str:
    import json
    d = json.dumps(datos, ensure_ascii=False)[:1800]
    return (f"{_HOLOS_VOZ}\nEres el Motor de Numerología. Estos son los números REALES ya calculados "
            f"de la persona (no recalcules):\n{d}\n\nCaso: {resumen}\n\nEntrega una lectura numerológica "
            "TERAPÉUTICA: tu misión y expresión, los desafíos o deudas kármicas, el año personal, y sobre "
            "todo cómo estos números se relacionan con tu conflicto y tu síntoma actual.")


def _prompt_astro(natal, resumen: str) -> str:
    import json
    d = json.dumps(natal, ensure_ascii=False)[:1800]
    return (f"{_HOLOS_VOZ}\nEres el Motor de Astrología Médica. Estas son las posiciones REALES de la "
            f"carta natal (no recalcules):\n{d}\n\nCaso: {resumen}\n\nEntrega una lectura de astrología "
            "médica: qué zonas u órganos y qué patrones emocionales sugiere la carta (Sol, Luna, ascendente, "
            "planetas en tensión), y cómo se vinculan con tu síntoma y el conflicto decodificado.")


def _prompt_astro_solar(signo: str, resumen: str) -> str:
    return (f"{_HOLOS_VOZ}\nEres el Motor de Astrología Médica. Aún no tenemos hora y lugar de "
            f"nacimiento, así que haces una lectura COMPLETA basada en tu signo solar: {signo}.\n\n"
            f"Caso: {resumen}\n\nEntrega una lectura de astrología médica rica y cálida con estos "
            "subtítulos (###): \n"
            "### Tu signo y tu cuerpo\nqué zonas, órganos y sistemas rige tu signo solar y a qué "
            "desequilibrios tiende.\n"
            "### Tu patrón emocional\nla forma en que tu signo vive y procesa las emociones, y cómo "
            "se relaciona con tu conflicto y tu síntoma.\n"
            "### Tus recursos\nlas fortalezas de tu signo que puedes apoyar para sostener tu proceso.\n"
            "### Para afinar tu carta\nexplica, con calidez, que con tu hora y lugar de nacimiento se "
            "podría calcular tu carta natal completa (Luna, ascendente, planetas) para una lectura aún "
            "más precisa.")


def _prompt_horoscopo(signo: str, resumen: str, hoy: str) -> str:
    return (f"{_HOLOS_VOZ}\nEres el Motor de Horóscopo Terapéutico. Para tu signo ({signo}) y tu "
            f"momento actual ({hoy}), entrega un horóscopo TERAPÉUTICO: no predicciones, sino una "
            "lectura del clima emocional de esta etapa y cómo acompañarte en tu proceso.\n\n"
            f"Caso: {resumen}\n\nCon ### por área:\n### Tu energía ahora\n### Amor y vínculos\n"
            "### Trabajo y propósito\n### Tu bienestar y tu cuerpo\n### Tu enfoque para estos días\n"
            "Conéctalo con tu conflicto y tu proceso de liberación; tono cálido y alentador.")


def _prompt_transitos(signo: str, resumen: str, hoy: str) -> str:
    return (f"{_HOLOS_VOZ}\nEres el Motor de Tránsitos Planetarios. Para tu signo solar ({signo}) y el "
            f"periodo actual ({hoy}), explica los TRÁNSITOS más relevantes y qué mueven en ti a nivel "
            "emocional, de forma clara para alguien sin conocimientos de astrología.\n\n"
            f"Caso: {resumen}\n\nCon ### por tránsito o tema (2 a 4): nombra el tránsito en lenguaje "
            "sencillo, qué remueve o invita a soltar/transformar, y cómo aprovecharlo en tu proceso de "
            "liberación emocional. Cierra con una invitación cálida para este periodo. Habla en "
            "tendencias y posibilidades, nunca como un destino fijo.")


def _prompt_tarot(perfil, resumen: str) -> str:
    import json
    d = json.dumps(perfil, ensure_ascii=False)[:1800]
    return (f"{_HOLOS_VOZ}\nEres el Motor de Tarot Terapéutico. Este es tu perfil tarológico REAL "
            f"(cartas natales, ya calculadas):\n{d}\n\nCaso: {resumen}\n\nEntrega una lectura de tarot "
            "terapéutico: qué reflejan estas cartas sobre tu momento y tu conflicto, qué recurso interno "
            "señalan y qué sombra trabajar. Conéctalo con el cuadro.")


# ─── Protocolos de liberación emocional (del curso + técnicas de fuera) ─────────
_PROTO_CACHE = None
# Curados: emocionalmente enfocados y AUTO-APLICABLES por el público (sin rastreo,
# sin imanes, sin lo esotérico que no encaja en un producto de salud emocional).
_PROTO_WHITELIST = {
    "eft_pro", "eft_transgeneracional", "carta_telepatica_parental", "sepelio_simbolico",
    "inclusion_excluidos", "extraccion_recursos", "liberacion_traumas", "estres_postraumatico",
    "protocolo_miedos", "protocolo_fobias", "coraza_energetica", "reimpronta_tierra",
    "reimpronta_metal", "memorias_celulares", "sublimacion_transgen",
    "liberacion_impronta_transgeneracional", "metodo_onirologico",
}


def _load_protocolos() -> list:
    global _PROTO_CACHE
    if _PROTO_CACHE is not None:
        return _PROTO_CACHE
    import json
    try:
        here = os.path.dirname(os.path.abspath(__file__))      # api/routes
        root = os.path.dirname(os.path.dirname(here))          # raíz del repo
        path = os.path.join(root, "data", "procedural_protocols_db.json")
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        _PROTO_CACHE = d.get("protocols", []) if isinstance(d, dict) else []
    except Exception as exc:
        logger.warning("consumer protocolos load: %s", exc)
        _PROTO_CACHE = []
    return _PROTO_CACHE


def _protocolos_relevantes(inputs: dict, k: int = 6) -> list:
    import re, unicodedata
    protos = [p for p in _load_protocolos() if p.get("id") in _PROTO_WHITELIST]
    if not protos:
        return []
    g = lambda key: _g(inputs, key)
    query = " ".join([
        g("sintomas") or g("sintoma"), g("motivo"), g("dhs_frase"), g("dhs_impacto"),
        g("emociones_frecuentes"), g("no_perdona"), g("contexto_emocional"), g("duelos"),
    ])
    trans = any(g(x) for x in ("padre_murio", "madre_murio", "enfermedades_repetidas",
                               "muertes_clan", "secretos_clan", "nombres_repetidos",
                               "perdidas_clan", "duelos")) or bool(
        isinstance(inputs, dict) and (inputs.get("hermanos") or inputs.get("hijos")))

    def norm(s):
        return unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()

    qtokens = set(re.findall(r"[a-z]{4,}", norm(query)))
    scored = []
    for p in protos:
        blob = norm((p.get("objetivo", "") or "") + " " + " ".join(p.get("cuando_usarlo", []) or []))
        ptokens = set(re.findall(r"[a-z]{4,}", blob))
        score = len(qtokens & ptokens)
        if trans and p.get("categoria") == "transgeneracional":
            score += 1
        if p.get("id") in ("eft_pro", "carta_telepatica_parental", "sepelio_simbolico"):
            score += 2  # staples de autoaplicación para el público
        scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    sel = [p for _s, p in scored[:k]]
    # EFT PRO siempre disponible como base de autoaplicación
    if not any(p.get("id") == "eft_pro" for p in sel):
        eft = next((p for p in protos if p.get("id") == "eft_pro"), None)
        if eft:
            sel = sel[:k - 1] + [eft]
    return sel


def _protocolos_txt(protos: list) -> str:
    out = []
    for p in protos:
        lines = [f"PROTOCOLO: {p.get('nombre','')}",
                 f"Objetivo: {p.get('objetivo','')}",
                 "Cuándo: " + "; ".join((p.get("cuando_usarlo", []) or [])[:3])]
        pasos = (p.get("pasos", []) or [])[:8]
        if pasos:
            lines.append("Pasos:")
            for s in pasos:
                lines.append(f"  {s.get('orden','')}. {s.get('titulo','')}: {s.get('instruccion','')}")
        fr = p.get("frases_sanadoras", []) or []
        if fr:
            lines.append("Frases sanadoras: " + " | ".join(fr[:4]))
        out.append("\n".join(lines))
    return "\n\n".join(out)


def _prompt_protocolos(ctx: str, resumen: str, protos_txt: str) -> str:
    return f"""{_HOLOS_VOZ}
Eres el Motor Terapéutico. Entrega TUS PROTOCOLOS DE LIBERACIÓN EMOCIONAL: ejercicios concretos que la persona pueda hacer SOLA en casa para liberar la carga emocional de SU conflicto.

Caso: {resumen}
ECOSISTEMA (resumen)
{(ctx or '')[:1400]}

PROTOCOLOS DEL MÉTODO (material propio; adáptalos a autoaplicación, sin terapeuta, sin rastreo ni imanes):
{protos_txt}

Instrucciones:
- Elige los 4 o 5 protocolos MÁS pertinentes a este conflicto y adáptalos PASO A PASO para que la persona los haga sola, en 2ª persona.
- Personaliza las frases sanadoras al conflicto EXACTO de la persona (no genéricas).
- Usa ### por cada protocolo: su nombre, para qué le sirve en su caso, y los pasos numerados y claros.
- Cierra con "### También puedes probar": 1 o 2 técnicas reconocidas de liberación emocional de fuera del método (p. ej. escritura expresiva, respiración consciente, anclaje) que complementen.
- Nada de diagnóstico ni promesas de cura; es trabajo emocional y de desarrollo personal."""


# ─── Bonos de la landing (Nivel 1) ──────────────────────────────────────────────
def _prompt_diccionario(inputs: dict) -> str:
    g = lambda k: _g(inputs, k)
    sint = g("sintomas") or g("sintoma") or g("motivo")
    return (f"{_HOLOS_VOZ}\nEres el Motor de Biodescodificación. Entrega el BONO 'Diccionario del "
            f"Síntoma' para esta persona.\n\nSu síntoma o malestar: {sint}\n\nCon ### por entrada:\n"
            f"### {sint}\nEl significado emocional (sentido biológico) de ESTE síntoma, en lenguaje "
            "sencillo y cálido, con el tipo de conflicto que suele estar detrás.\n"
            "Luego añade 2 o 3 entradas más (###) de síntomas RELACIONADOS o cercanos al suyo, cada "
            "uno con su significado emocional breve, para que tenga un pequeño diccionario útil. "
            "Nada de diagnóstico; es una guía de lectura emocional.")


def _prompt_respiracion(resumen: str) -> str:
    return (f"{_HOLOS_VOZ}\nEntrega el BONO 'Respiración guiada', un ejercicio de respiración para "
            "acompañar a la persona en los momentos de más carga emocional, pensado para SU conflicto.\n\n"
            f"Caso: {resumen}\n\nEscribe un guion de respiración consciente, cálido y pausado, en 2ª "
            "persona, que la persona pueda leer y seguir sola (3 a 5 minutos). Da el paso a paso del "
            "ritmo (inhalar, sostener, exhalar), qué imaginar o soltar en cada exhalación conectado a "
            "su carga emocional, y cómo cerrar. Marca pausas con '(pausa)'.")


def _prompt_actos(resumen: str) -> str:
    return (f"{_HOLOS_VOZ}\nEntrega el BONO 'Guía de actos simbólicos': gestos sencillos para integrar "
            "y cerrar el trabajo emocional de SU conflicto.\n\n"
            f"Caso: {resumen}\n\nPropón de 3 a 4 actos simbólicos concretos y fáciles (###), cada uno "
            "con para qué sirve en su caso y cómo hacerlo paso a paso (por ejemplo: escribir y soltar "
            "una carta, un objeto que represente lo que suelta, un gesto de devolver una carga, un "
            "pequeño ritual de cierre). Cálido y respetuoso, sin nada esotérico ni promesas.")


def _calc_numerologia(inputs: dict):
    try:
        import datetime
        from api.numerology.calculator import calcular_numeroscopio
        nombre = _g(inputs, "nombre") or "Consultante"
        d = datetime.date.fromisoformat(_g(inputs, "fecha_nacimiento"))
        return calcular_numeroscopio(nombre, d.day, d.month, d.year)
    except Exception as exc:
        logger.warning("consumer holos numerologia calc: %s", exc)
        return None


def _calc_natal(inputs: dict, hora_forzada: str = ""):
    """Carta natal real. Sin hora calcula a las 12:00 y marca sin_hora (las casas y el
    ascendente se quitan porque dependen de la hora)."""
    try:
        import datetime
        from api.astro.engine import _geocode
        from api.astro.calculator import get_natal_data
        nombre = _g(inputs, "nombre") or "Consultante"
        d = datetime.date.fromisoformat(_g(inputs, "fecha_nacimiento"))
        hora_real = _g(inputs, "hora_nacimiento")
        hora = hora_forzada or hora_real or "12:00"
        h, m = [int(x) for x in hora.split(":")[:2]]
        lat, lng, tz_str = _geocode(_g(inputs, "lugar_nacimiento"))
        natal = get_natal_data(nombre, d.year, d.month, d.day, h, m, lat, lng, tz_str)
        if not hora_real and not hora_forzada:
            natal["sin_hora"] = True
            natal["casas"] = {}
            for p in (natal.get("planetas") or {}).values():
                p.pop("casa", None)
        return natal
    except Exception as exc:
        logger.warning("consumer holos natal calc: %s", exc)
        return None


def _calc_signo(inputs: dict):
    try:
        from api.astro.horoscopo_knowledge import get_signo_solar
        f = _g(inputs, "fecha_nacimiento")
        return get_signo_solar(f) if f else ""
    except Exception as exc:
        logger.warning("consumer holos signo calc: %s", exc)
        return ""


def _calc_tarot(inputs: dict):
    try:
        import datetime
        from api.tarot.calculator import calcular_perfil_tarot
        d = datetime.date.fromisoformat(_g(inputs, "fecha_nacimiento"))
        return calcular_perfil_tarot(d.day, d.month, d.year, sistema="rws")
    except Exception as exc:
        logger.warning("consumer holos tarot calc: %s", exc)
        return None


def _generar_holos_cuadro(inputs: dict, lang: str) -> dict:
    """Réplica del Cuadro Holos real (sin rastreo de imanes), en 2ª persona.
    Genera las secciones en paralelo y las concatena con sus títulos."""
    from concurrent.futures import ThreadPoolExecutor

    ctx = _construir_ecosistema(inputs)
    resumen = _resumen_caso(inputs)
    tiene_base = bool((_g(inputs, "motivo") or _g(inputs, "sintoma") or _g(inputs, "sintomas")))
    if not tiene_base:
        return {"ok": False, "error": "faltan_datos_base", "answer": ""}

    fecha = _g(inputs, "fecha_nacimiento")
    hora = _g(inputs, "hora_nacimiento")
    lugar = _g(inputs, "lugar_nacimiento")

    # Inyección del corpus de libros (RAG), igual que el Cuadro Holos real:
    # el núcleo y la lectura por áreas se anclan en el material propio
    # (biodescodificación, NMG, transgeneracional…) usando el caso como query.
    def _inyectar(prompt: str, query: str) -> str:
        try:
            from api.routes.therapeutic import _inyectar_material
            nuevo, _fuentes = _inyectar_material(prompt, query)
            return nuevo
        except Exception as exc:  # nunca romper por el RAG
            logger.warning("consumer holos RAG: %s", exc)
            return prompt

    # (orden, título, builder) — el builder devuelve el texto de la sección.
    def _run_holos(prompt: str, query: str | None = None) -> str:
        if query:
            prompt = _inyectar(prompt, query)
        r = generar_respuesta_holos(prompt, lang)
        return (r.get("answer") or "").strip() if r.get("ok") else ""

    # Query de RAG: síntoma + motivo + frase del DHS (lo que ancla el material).
    rag_query = " ".join(x for x in [
        _g(inputs, "sintomas") or _g(inputs, "sintoma"),
        _g(inputs, "motivo"),
        _g(inputs, "dhs_frase"),
    ] if x).strip() or resumen

    coincidencias = _coincidencias(inputs)

    def sec_nucleo():
        return _run_holos(_prompt_nucleo(ctx, coincidencias), query=rag_query)

    protos = _protocolos_relevantes(inputs)

    def sec_protocolos():
        if not protos:
            return ""
        return _run_holos(_prompt_protocolos(ctx, resumen, _protocolos_txt(protos)), query=rag_query)

    def sec_areas():
        return _run_holos(_prompt_areas(ctx, resumen), query=rag_query)

    def sec_diccionario():
        return _run_holos(_prompt_diccionario(inputs), query=rag_query)

    def sec_respiracion():
        return _run_holos(_prompt_respiracion(resumen))

    def sec_actos():
        return _run_holos(_prompt_actos(resumen))

    def sec_numerologia():
        datos = _calc_numerologia(inputs)
        return _run_holos(_prompt_numerologia(datos, resumen)) if datos else ""

    def sec_astro():
        # Carta natal completa si hay hora + lugar; si no, astrología médica por signo solar.
        if fecha and hora and lugar:
            natal = _calc_natal(inputs)
            if natal:
                return _run_holos(_prompt_astro(natal, resumen))
        signo = _calc_signo(inputs)
        if signo:
            return _run_holos(_prompt_astro_solar(signo, resumen))
        return ""

    def sec_tarot():
        perfil = _calc_tarot(inputs)
        return _run_holos(_prompt_tarot(perfil, resumen)) if perfil else ""

    import datetime as _dt
    _hoy = _dt.date.today().strftime("%B %Y")

    def sec_horoscopo():
        signo = _calc_signo(inputs)
        return _run_holos(_prompt_horoscopo(signo, resumen, _hoy)) if signo else ""

    def sec_transitos():
        signo = _calc_signo(inputs)
        return _run_holos(_prompt_transitos(signo, resumen, _hoy)) if signo else ""

    # Orden: análisis y lecturas → protocolos (justo antes del final) → BONOS al final.
    tareas = [
        ("Tu conflicto, decodificado", sec_nucleo),
        ("Lectura por áreas de tu vida", sec_areas),
    ]
    if fecha:
        tareas.append(("Tu numerología", sec_numerologia))
        tareas.append(("Tu astrología", sec_astro))
        tareas.append(("Tu horóscopo terapéutico", sec_horoscopo))
        tareas.append(("Tus tránsitos planetarios", sec_transitos))
        tareas.append(("Tu tarot", sec_tarot))
    # Protocolos: antes del final.
    tareas.append(("Tus protocolos de liberación emocional", sec_protocolos))
    # Bonos: al final.
    tareas.append(("Diccionario del Síntoma", sec_diccionario))
    tareas.append(("Respiración guiada", sec_respiracion))
    tareas.append(("Guía de actos simbólicos", sec_actos))

    resultados = [None] * len(tareas)
    with ThreadPoolExecutor(max_workers=min(5, len(tareas))) as ex:
        futs = {ex.submit(t[1]): i for i, t in enumerate(tareas)}
        for fut in futs:
            i = futs[fut]
            try:
                resultados[i] = fut.result()
            except Exception as exc:
                logger.warning("consumer holos seccion %s: %s", tareas[i][0], exc)
                resultados[i] = ""

    partes = []
    for (titulo, _), texto in zip(tareas, resultados):
        if texto:
            partes.append(f"# {titulo}\n\n{texto}")

    if not partes:
        return {"ok": False, "error": "generacion_fallida", "answer": ""}
    return {"ok": True, "answer": "\n\n".join(partes)}


# ════════════════════════════════════════════════════════════════════════════
#  AFINADOR DEL DHS — mini-entrevista adaptativa (Modo Entrevista del Método
#  Holos) que se corre DESPUÉS del informe para precisar el DHS. Una pregunta a
#  la vez (las 4 INs: inesperado, intenso, insoluble, individual), y al final
#  re-sintetiza el conflicto ya afinado.
# ════════════════════════════════════════════════════════════════════════════

def _hist_txt(history: list) -> str:
    partes = []
    for h in (history or []):
        if not isinstance(h, dict):
            continue
        q = str(h.get("q", "")).strip()
        a = str(h.get("a", "")).strip()
        if q or a:
            partes.append(f"P: {q}\nR: {a}")
    return "\n".join(partes) or "(aún no hay respuestas)"


def _entrevista_next(inputs: dict, history: list, lang: str) -> str:
    sintoma = _g(inputs, "sintomas") or _g(inputs, "sintoma") or "tu síntoma"
    dhs = _g(inputs, "dhs_frase")
    prompt = f"""{_HOLOS_VOZ}
Eres guía de entrevista del Método Holos. Estás afinando el DHS: el instante exacto que disparó el conflicto detrás de «{sintoma}». {('La persona ya dijo que lo vivió así: "' + dhs + '". ') if dhs else ''}Trabajas el anclaje (qué pasaba justo antes de que apareciera) y las 4 INs: INESPERADO, INTENSO, INSOLUBLE, INDIVIDUAL (si lo vivió en soledad).

REGLAS ESTRICTAS:
- Haz UNA sola pregunta, breve, cálida, en 2ª persona, lista para responderse en voz alta.
- Sigue el hilo de la última respuesta; nunca repitas una pregunta ya hecha.
- No hagas dos preguntas. No des explicaciones, análisis ni diagnóstico. Sin preámbulos.

ENTREVISTA HASTA AHORA:
{_hist_txt(history)}

Si con lo que ya tienes el DHS queda claro en sus 4 INs, responde EXACTAMENTE la palabra: LISTO
Si no, devuelve SOLO la siguiente pregunta (sin comillas ni prefijos)."""
    r = generar_respuesta_holos(prompt, lang)
    return (r.get("answer") or "").strip() if r.get("ok") else ""


def _entrevista_sintesis(inputs: dict, history: list, lang: str) -> str:
    ctx = _construir_ecosistema(inputs)
    prompt = f"""{_HOLOS_VOZ}
Eres el Motor de Biodescodificación. Con el ECOSISTEMA y las respuestas de la entrevista de afinado, precisa el DHS y el conflicto: ya no una hipótesis general, sino la TONALIDAD EXACTA.

ECOSISTEMA
{ctx or "  - (pocos datos; trabaja con la entrevista)"}

ENTREVISTA DE AFINADO DEL DHS:
{_hist_txt(history)}

Entrega SOLO estas secciones (usa ## y ###):

## Tu DHS, afinado
El instante exacto y el sentir preciso, integrando las 4 INs (inesperado, intenso, insoluble, individual). Cierra con UNA frase en primera persona que capture el conflicto.

## El conflicto, ahora preciso
La tonalidad exacta del conflicto del órgano/tejido, más afinada que el análisis inicial, y por qué estas respuestas la precisan.

## Tu siguiente paso
Un ejercicio concreto para liberar ESE conflicto afinado, y una invitación suave a grabarlo con la hipnosis personalizada (Método REMA)."""
    r = generar_respuesta_holos(prompt, lang)
    return (r.get("answer") or "").strip() if r.get("ok") else ""


def _texto_inputs(inputs: dict) -> str:
    """Convierte el formulario de la persona en un bloque de texto para el prompt."""
    if not isinstance(inputs, dict):
        return ""
    etiquetas = {
        "nombre": "Nombre", "sintoma": "Síntoma o malestar", "historia": "Su historia / contexto",
        "pregunta": "Pregunta o intención", "signo": "Signo", "fecha_nacimiento": "Fecha de nacimiento",
        "hora_nacimiento": "Hora de nacimiento", "lugar_nacimiento": "Lugar de nacimiento",
        "conflicto": "Conflicto emocional detectado",
        "nombre_2": "Nombre de la otra persona", "fecha_nacimiento_2": "Su fecha de nacimiento",
        "hora_nacimiento_2": "Su hora de nacimiento", "lugar_nacimiento_2": "Su lugar de nacimiento",
        "sueno": "El sueño", "emocion": "Cómo se sintió al despertar", "tirada": "Tirada elegida",
    }
    partes = []
    for k, v in inputs.items():
        if v is None or str(v).strip() == "":
            continue
        partes.append(f"{etiquetas.get(k, k)}: {str(v).strip()[:1500]}")
    return "\n".join(partes)


# ─── Datos calculados para las lecturas nuevas (pareja, año, tarot especial) ──
_PLANETAS_ES = {
    "sun": "Sol", "moon": "Luna", "mercury": "Mercurio", "venus": "Venus", "mars": "Marte",
    "jupiter": "Júpiter", "saturn": "Saturno", "uranus": "Urano", "neptune": "Neptuno",
    "pluto": "Plutón", "true_node": "Nodo Norte", "chiron": "Quirón",
}


def _natal_txt(natal: dict | None, planetas=("sun", "moon", "mercury", "venus", "mars")) -> str:
    if not natal:
        return "(posiciones no disponibles)"
    pl = natal.get("planetas") or {}
    filas = [f"{_PLANETAS_ES.get(k, k)} en {pl[k].get('signo', '')}" for k in planetas if k in pl]
    asc = (natal.get("casas") or {}).get(1)
    if asc:
        filas.append(f"Ascendente en {asc.get('signo', '')}")
    return ", ".join(filas)


def _numeros_txt(num: dict | None) -> str:
    if not num:
        return "(números no disponibles)"
    n, nac = num.get("nombre") or {}, num.get("nacimiento") or {}
    return (f"misión {nac.get('mision', '?')}, alma {nac.get('alma', '?')}, "
            f"expresión {n.get('expresion', '?')}, impulso {n.get('impulso', '?')}")


def _segunda_persona(inputs: dict) -> dict:
    return {k: _g(inputs, k + "_2") for k in ("nombre", "fecha_nacimiento", "hora_nacimiento", "lugar_nacimiento")}


def _datos_pareja(inputs: dict) -> str:
    otra = _segunda_persona(inputs)
    return (f"Tú ({_g(inputs, 'nombre') or 'tú'}): {_natal_txt(_calc_natal(inputs))}. "
            f"Números: {_numeros_txt(_calc_numerologia(inputs))}.\n"
            f"{otra['nombre'] or 'La otra persona'}: {_natal_txt(_calc_natal(otra))}. "
            f"Números: {_numeros_txt(_calc_numerologia(otra))}.")


_MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]


def _datos_anio(inputs: dict) -> str:
    """Tránsitos de los planetas lentos sobre la carta natal, el día 15 de cada mes."""
    import datetime
    natal = _calc_natal(inputs)
    if not natal:
        return "(no se pudieron calcular los tránsitos)"
    try:
        from api.astro.calculator import get_natal_data
        from api.routes.astro import _transit_aspects
    except Exception as exc:
        logger.warning("consumer año imports: %s", exc)
        return f"Carta natal: {_natal_txt(natal)}."
    lentos = {"jupiter", "saturn", "uranus", "neptune", "pluto"}
    personales = {"sun", "moon", "mercury", "venus", "mars"}
    hoy = datetime.date.today()
    filas = [f"Carta natal: {_natal_txt(natal)}."]
    for i in range(1, 13):  # los 12 meses siguientes
        y, m = hoy.year + (hoy.month - 1 + i) // 12, (hoy.month - 1 + i) % 12 + 1
        try:
            tr = get_natal_data("t", y, m, 15, 12, 0, natal["lat"], natal["lng"], natal["tz"])
            asp = [a for a in _transit_aspects(natal, tr)
                   if a["planeta_transito"] in lentos and a["planeta_natal"] in personales][:4]
        except Exception as exc:
            logger.warning("consumer año tránsito %s-%s: %s", y, m, exc)
            continue
        txt = "; ".join(f"{_PLANETAS_ES[a['planeta_transito']]} {a['aspecto']} a tu "
                        f"{_PLANETAS_ES[a['planeta_natal']]}" for a in asp) or "sin tránsitos relevantes"
        filas.append(f"{_MESES_ES[m - 1]} {y}: {txt}")
    return "\n".join(filas)


# Tiradas que se venden al público (catálogo completo en api/tarot/knowledge.py).
TIRADAS_ESPECIALES = ("cruz_celtica", "espejo_relacion", "decision", "proposito_alma", "rueda_del_anio")


def _datos_tarot_especial(inputs: dict) -> str:
    import random
    from api.tarot.knowledge import TIRADAS, ARCANOS_MAYORES, ARCANOS_MENORES
    clave = _g(inputs, "tirada")
    if clave not in TIRADAS_ESPECIALES:
        clave = "cruz_celtica"
    t = TIRADAS[clave]
    azar = random.SystemRandom()
    cartas = azar.sample(list(ARCANOS_MAYORES) + list(ARCANOS_MENORES), len(t["posiciones"]))
    filas = [f"Tirada: {t['nombre']}"]
    for pos, carta in zip(t["posiciones"], cartas):
        inv = " (invertida)" if azar.random() < 0.25 else ""
        filas.append(f"{pos['id']}. {pos['nombre']} ({pos['descripcion']}): {carta}{inv}")
    return "\n".join(filas)


_ASPECTOS_NATALES = (("conjunción", 0, 8), ("oposición", 180, 8), ("trígono", 120, 7),
                     ("cuadratura", 90, 7), ("sextil", 60, 5))


def _datos_carta_natal(inputs: dict) -> str:
    """Posiciones reales para la Carta Natal pagada (antes la IA las adivinaba)."""
    natal = _calc_natal(inputs)
    if not natal:
        signo = _calc_signo(inputs)
        return ("No se pudo calcular la carta (no ubicamos la ciudad o la fecha). "
                + (f"Solo es seguro su Sol en {signo}. " if signo else "")
                + "NO inventes posiciones de Luna, Ascendente ni otros planetas: habla del Sol y "
                  "explica con naturalidad que para lo demás hace falta su ciudad de nacimiento.")
    pl = natal.get("planetas") or {}
    filas = []
    for k in ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
              "uranus", "neptune", "pluto", "true_node", "chiron"):
        p = pl.get(k)
        if not p:
            continue
        extra = f", casa {p['casa']}" if p.get("casa") else ""
        extra += ", retrógrado" if p.get("retrogrado") and k != "true_node" else ""
        filas.append(f"{_PLANETAS_ES[k]} en {p.get('signo', '')} ({int(p.get('grado', 0))}°{extra})")
    casas = natal.get("casas") or {}
    if casas.get(1):
        filas.append(f"Ascendente en {casas[1]['signo']} ({int(casas[1].get('grado', 0))}°)")
    if casas.get(10):
        filas.append(f"Medio Cielo en {casas[10]['signo']}")
    if natal.get("sin_hora"):
        # Sin hora no sabemos el momento del día: si un planeta (casi siempre la Luna)
        # cambió de signo ese día, damos los dos posibles.
        ini = (_calc_natal(inputs, hora_forzada="00:00") or {}).get("planetas") or {}
        fin = (_calc_natal(inputs, hora_forzada="23:59") or {}).get("planetas") or {}
        for k in ("sun", "moon", "mercury", "venus", "mars"):
            a, b = ini.get(k, {}).get("signo"), fin.get(k, {}).get("signo")
            if a and b and a != b:
                filas.append(f"OJO: sin la hora, {_PLANETAS_ES[k]} puede estar en {a} o en {b} "
                             "(cambió de signo ese día); menciona ambas posibilidades")
        filas.append("Sin hora de nacimiento: NO hay Ascendente ni casas; no los inventes")

    def dist(a, b):
        d = abs(a - b) % 360
        return min(d, 360 - d)
    personales = ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn")
    asp = []
    claves = [k for k in personales if k in pl]
    for i, a in enumerate(claves):
        for b in claves[i + 1:]:
            if natal.get("sin_hora") and "moon" in (a, b):
                continue  # la Luna se mueve demasiado para afirmar aspectos sin hora
            dd = dist(pl[a].get("abs_pos", 0), pl[b].get("abs_pos", 0))
            for nombre, ang, orbe in _ASPECTOS_NATALES:
                if abs(dd - ang) <= orbe:
                    asp.append((abs(dd - ang), f"{_PLANETAS_ES[a]} en {nombre} con {_PLANETAS_ES[b]}"))
                    break
    asp.sort()
    texto = "Posiciones reales calculadas (efemérides):\n" + "\n".join(filas)
    if asp:
        texto += "\nAspectos principales: " + "; ".join(t for _, t in asp[:8])
    return texto


_DATOS_CALCULADOS = {
    "carta-natal": _datos_carta_natal,
    "pareja": _datos_pareja,
    "tu-anio": _datos_anio,
    "tarot-especial": _datos_tarot_especial,
}


# product → (system_prompt, max_tokens)
_PRODUCTOS = {
    "holos":         (HOLOS_CONSUMER, 3500),
    "rema":          (REMA_CONSUMER, 4000),
    "tarot":         (TAROT_CONSUMER, 1600),
    "horoscopo":     (HOROSCOPO_CONSUMER, 1600),
    "carta-natal":   (ASTRO_CONSUMER, 2400),
    "numerologia":   (NUMER_CONSUMER, 1800),
    "pareja":        (PAREJA_CONSUMER, 2400),
    "tu-anio":       (ANIO_CONSUMER, 2800),
    "tarot-especial":(TAROT_ESPECIAL_CONSUMER, 2600),
    "suenos":        (SUENOS_CONSUMER, 1800),
}
_LECTURAS = ("tarot", "horoscopo", "carta-natal", "numerologia", "pareja", "tu-anio", "tarot-especial", "suenos")
# Paquetes = varias lecturas, una tras otra.
_PAQUETES = {
    "pack-claridad": ["carta-natal", "horoscopo", "tarot"],
    "pack-completo": ["carta-natal", "horoscopo", "tarot", "numerologia"],
}


class GenReq(BaseModel):
    product: str = Field(..., description="holos | rema | tarot | horoscopo | carta-natal | numerologia | pareja | tu-anio | tarot-especial | suenos | pack-*")
    lang: str = Field(default="es")
    inputs: dict = Field(default_factory=dict)


def _generar_uno(product: str, inputs: dict) -> dict:
    sys_tok = _PRODUCTOS.get(product)
    if not sys_tok:
        return {"ok": False, "error": "producto_invalido", "answer": ""}
    system, max_tokens = sys_tok
    prompt = _texto_inputs(inputs) or "(sin datos adicionales)"
    calc = _DATOS_CALCULADOS.get(product)
    if calc:
        try:
            prompt += "\n\nDatos calculados (no los cambies):\n" + calc(inputs)
        except Exception as exc:
            logger.warning("consumer %s datos: %s", product, exc)
    temp = 0.6 if product in _LECTURAS else 0.5
    return _generar_con_sistema(system, prompt, f"consumer:{product}", temp, max_tokens=max_tokens)


@router.post("/generate")
async def generate(req: GenReq, request: Request):
    if not _authorized(request):
        raise HTTPException(status_code=401, detail="no_autorizado")
    try:
        set_holos_lang(req.lang)
    except Exception:
        pass

    product = (req.product or "").strip().lower()

    # Método Holos (consumidor): réplica del Cuadro Holos real, multi-sección
    # y anclado en el corpus de libros, SIN rastreo de imanes.
    if product == "holos":
        r = _generar_holos_cuadro(req.inputs, req.lang)
        if not r.get("ok"):
            return JSONResponse({"ok": False, "product": product, "error": r.get("error") or "generacion_fallida", "content": ""}, status_code=502)
        return JSONResponse({"ok": True, "product": product, "content": r.get("answer", "")})

    # Adelanto gratis del test (embudo): conflicto probable + emoción raíz, sin el resto.
    if product == "holos-parcial":
        r = _generar_holos_parcial(req.inputs, req.lang)
        if not r.get("ok") or not r.get("answer"):
            return JSONResponse({"ok": False, "product": product, "error": r.get("error") or "generacion_fallida", "content": ""}, status_code=502)
        return JSONResponse({"ok": True, "product": product, "content": r["answer"]})

    if product in _PAQUETES:
        secciones = []
        for sub in _PAQUETES[product]:
            r = _generar_uno(sub, req.inputs)
            if r.get("ok"):
                secciones.append(r.get("answer", ""))
        if not secciones:
            return JSONResponse({"ok": False, "product": product, "error": "generacion_fallida", "content": ""}, status_code=502)
        return JSONResponse({"ok": True, "product": product, "content": "\n\n---\n\n".join(secciones)})

    if product not in _PRODUCTOS:
        raise HTTPException(status_code=400, detail="producto_invalido")

    r = _generar_uno(product, req.inputs)
    if not r.get("ok"):
        return JSONResponse({"ok": False, "product": product, "error": r.get("error") or "generacion_fallida", "content": ""}, status_code=502)
    return JSONResponse({"ok": True, "product": product, "content": r.get("answer", "")})


# ─── Análisis parcial del test gratis (embudo Holos, 8-nov-2026) ────────────────
# El anuncio lleva a la primera parte del test (6 preguntas); al dejar sus datos la
# persona recibe ESTO: una parte fuerte del análisis (conflicto probable y emoción
# raíz), sin genograma, sin lectura energética y sin protocolos, que se venden en la
# lectura completa (/promo/holos).
_AREA_TXT = {"cuerpo": "su cuerpo / bienestar", "pareja": "la pareja", "trabajo": "el trabajo y el dinero",
             "familia": "la familia", "otra": "otra área de su vida"}
_DESDE_TXT = {"reciente": "menos de 6 meses", "medio": "entre 6 meses y 2 años", "cronico": "más de 2 años",
              "nose": "no lo sabe con certeza"}


def _prompt_parcial(inputs: dict) -> str:
    g = lambda k: _g(inputs, k)
    caso = (
        f"- Lo que vive o quiere entender (sus palabras): {g('motivo') or '-'}\n"
        f"- Área donde más lo siente: {_AREA_TXT.get(g('area'), g('area') or '-')}\n"
        f"- Desde cuándo: {_DESDE_TXT.get(g('inicio'), g('inicio') or '-')}\n"
        f"- Qué pasaba en su vida cuando empezó: {g('evento_inicio') or '-'}\n"
        f"- Cómo lo vivió por dentro: {g('dhs_frase') or '-'}\n"
        f"- ¿Alguien de su familia vivió algo parecido?: {g('familia') or '-'}"
    )
    return f"""{_HOLOS_VOZ}
Eres el Motor de Biodescodificación de Holoacademia. Nunca te presentes como inteligencia artificial.
La persona acaba de responder la PRIMERA PARTE del test del Método Holos. Le entregas un adelanto REAL y
profundo de su análisis: que sienta que alguien por fin entendió lo que vive. Habla de situaciones de vida
(pareja, dinero, familia, cuerpo) como conflictos emocionales; NUNCA prometas curar ni hables de enfermedades
como algo que se elimina.

SUS RESPUESTAS
{caso}

Entrega EXACTAMENTE estas secciones (usa ##), en total entre 320 y 450 palabras:

## Lo que hay detrás de lo que vives
El conflicto emocional más probable, leído desde la biodescodificación, conectado con SUS palabras y con el
momento en que empezó. Ofrece 2 matices posibles, no uno solo.

## Tu emoción raíz
La emoción que sostiene el conflicto (usa cómo lo vivió por dentro) y por qué se repite, en lenguaje sencillo.

## Lo que ya se asoma en tu historia familiar
Un párrafo breve: si respondió que alguien de su familia vivió algo parecido, qué podría estar repitiéndose o
qué lealtad podría haber; si no, qué suele esconderse en el árbol en casos como el suyo. Déjalo como
hipótesis: para confirmarlo hacen falta las fechas y los nombres del clan, que se trabajan en el análisis completo.

No incluyas protocolos, ejercicios, lectura energética, astrología ni numerología. No cierres con ventas
ni con descargos: eso lo agrega la página."""


def _generar_holos_parcial(inputs: dict, lang: str) -> dict:
    if not (_g(inputs, "motivo") or _g(inputs, "sintoma")):
        return {"ok": False, "error": "faltan_datos_base", "answer": ""}
    prompt = _prompt_parcial(inputs)
    query = " ".join(x for x in [_g(inputs, "motivo"), _g(inputs, "evento_inicio"), _g(inputs, "dhs_frase")] if x)
    try:
        from api.routes.therapeutic import _inyectar_material
        prompt, _f = _inyectar_material(prompt, query)
    except Exception as exc:  # nunca romper por el RAG
        logger.warning("consumer holos-parcial RAG: %s", exc)
    r = generar_respuesta_holos(prompt, lang)
    return {"ok": bool(r.get("ok")), "answer": (r.get("answer") or "").strip(), "error": r.get("error")}


class EntrevistaReq(BaseModel):
    lang: str = Field(default="es")
    inputs: dict = Field(default_factory=dict)
    history: list = Field(default_factory=list)


@router.post("/holos-entrevista")
async def holos_entrevista(req: EntrevistaReq, request: Request):
    """Afinador del DHS: una pregunta a la vez; al completar las 4 INs (o al tope
    de turnos) devuelve la síntesis del conflicto afinado."""
    if not _authorized(request):
        raise HTTPException(status_code=401, detail="no_autorizado")
    try:
        set_holos_lang(req.lang)
    except Exception:
        pass
    history = [h for h in (req.history or []) if isinstance(h, dict)]
    MAX_TURNS = 5
    if len(history) < MAX_TURNS:
        q = _entrevista_next(req.inputs, history, req.lang)
        qn = (q or "").strip()
        if qn and qn.upper().rstrip(".") != "LISTO":
            return JSONResponse({"ok": True, "done": False, "pregunta": qn})
    s = _entrevista_sintesis(req.inputs, history, req.lang)
    if not s:
        return JSONResponse({"ok": False, "error": "sintesis_fallida"}, status_code=502)
    return JSONResponse({"ok": True, "done": True, "sintesis": s})


class PdfReq(BaseModel):
    lang: str = Field(default="es")
    nombre: str = Field(default="")
    fecha_nac: str = Field(default="")
    title: str = Field(default="Tu Método Holos")
    content: str = Field(default="")


@router.post("/pdf")
async def consumer_pdf(req: PdfReq, request: Request):
    """Genera el PDF 'carta antigua' de la entrega. Devuelve base64 para que el
    frontend (.tv) lo adjunte al correo del comprador."""
    if not _authorized(request):
        raise HTTPException(status_code=401, detail="no_autorizado")
    if not (req.content or "").strip():
        return JSONResponse({"ok": False, "error": "sin_contenido"}, status_code=400)
    try:
        import base64
        from api.pdf_carta import build_carta_pdf
        data = build_carta_pdf(req.content, req.nombre or "", req.lang or "es",
                               req.title or "Tu Método Holos", req.fecha_nac or "")
        return JSONResponse({"ok": True, "filename": "Metodo-Holos.pdf",
                             "pdf_base64": base64.b64encode(data).decode("ascii")})
    except Exception as exc:
        logger.exception("consumer pdf: %s", exc)
        return JSONResponse({"ok": False, "error": "pdf_fallido"}, status_code=500)


@router.get("/health")
async def health():
    return {"ok": True, "productos": list(_PRODUCTOS.keys()) + list(_PAQUETES.keys())}
