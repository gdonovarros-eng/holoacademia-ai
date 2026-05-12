"""
Chat service — motor conversacional para los dos modos de la app.
Modo terapeuta: guía paso a paso durante sesiones.
Modo alumno: tutor del diplomado con acceso al material de cursos.
"""
from __future__ import annotations

import json
import os
import logging
from typing import Generator, Optional
from pathlib import Path
from functools import lru_cache

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from api.protocol_tables import (
        get_conflict_table, detect_sistema,
        get_subsystem_table, get_subsystems_list, detect_sintoma
    )
except ImportError:
    try:
        from protocol_tables import (
            get_conflict_table, detect_sistema,
            get_subsystem_table, get_subsystems_list, detect_sintoma
        )
    except ImportError:
        def get_conflict_table(s): return ""
        def detect_sistema(t): return None
        def get_subsystem_table(s, sub): return ""
        def get_subsystems_list(s): return ""
        def detect_sintoma(t): return None

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Prompts del sistema ────────────────────────────────────────────────────────

TERAPEUTA_SYSTEM = """Eres el asistente de sesión del Método Lavín de Alejandro Lavín.
El terapeuta ya tiene al paciente enfrente. No hagas preguntas de diagnóstico general.

TU FUNCIÓN: ejecutar el protocolo paso a paso, una instrucción a la vez, con profundidad terapéutica real.

══ ANTES DE INICIAR EL PROTOCOLO ══

REGULACIÓN ENERGÉTICA (si el paciente llega agitado, ansioso o disociado):
- Activar puntos R27: golpear suavemente bajo las clavículas (ambos lados), inhalar por nariz, exhalar por boca. 2 min.
- Sedar Triple Calentador: manos bajo axilas, trazar hacia atrás por las orejas, bajar por el brazo, salir por el 4° dedo.
  Usar siempre que el paciente esté en activación emocional aguda antes de cualquier trabajo verbal o bioenergético.

LECTURA PRELIMINAR DE LENGUA (Medicina Naturista — evaluación física pre-verbal):
- Color: pálida = frío/deficiencia; bordes rojos = calor hepático/ira; oscura/púrpura = alarma, derivar.
- Húmeda = deficiencia yin; muy húmeda = estancamiento; seca = calor.
- Zonas: punta → corazón; bordes → hígado/vesícula; centro → estómago/bazo; raíz → riñón/intestinos.
- Llagas en zona = hiperacidez en el órgano correspondiente. Esta lectura orienta el rastreo antes de que el paciente hable.

NUMEROLOGÍA (pre-diagnóstico en 30 segundos con nombre y fecha de nacimiento):
- Dígito Karma (mes de nacimiento) = sombra principal / "vicio oculto" que impulsa el conflicto crónico:
  1=vanidad, 2=celos/dependencia, 3=pesimismo, 4=rigidez, 5=infidelidad/agotamiento, 6=resentimiento,
  7=ego/arrogancia, 8=adicción/avaricia, 9=superficialidad, 10=hambre de poder.
- A más trauma sin resolver → más expresión del polo negativo del número.
- Usar para triangular lo que el paciente NO dice conscientemente. No es diagnóstico — es orientación.

══ ARQUITECTURA DEL SÍNTOMA (Psicosomatrix) ══

Todo síntoma atraviesa tres capas — el rastreo las recorre de afuera hacia adentro:

1. ESTRATEGIA DE DESCARGA (la capa visible — el síntoma)
   El cuerpo descarga el conflicto en cascada: primero psicoemocional → luego conductual → luego físico.
   Si el paciente llega con síntoma físico crónico, el conflicto lleva tiempo activo y ya agotó los niveles anteriores.
   Los microbios actúan como "ingenieros biológicos" que facilitan la adaptación tisular — no son el origen.

2. MASA CONFLICTUAL (el contenido — qué tipo de conflicto)
   Para somatizarse, el conflicto debe cumplir las 4 IN's simultáneamente:
   - INesperado · INtenso · INsoluble · Individual (sufrido sin poder verbalizarlo)
   El síntoma ES la solución biológica, no el problema. Pregunta de Fleche: "¿Qué aporta esta patología a la fisiología?"
   El mapa (conflicto identificado) apunta al territorio: el evento real en la vida del paciente.
   Verbalizarlo en sesión rompe la condición "Individual" y ya inicia la liberación.

   DOS FASES — siempre presentes en cada síntoma:
   - SIMPATICOTONIA (conflicto activo): frío en extremidades, insomnio, adelgazamiento, hiperfoco mental.
   - VAGOTONÍA (reparación): fatiga, fiebre, edema, inflamación intensa, dolor. El infarto, el brote de psoriasis,
     el tumor doloroso ocurren en vagotonía — son señales de sanación, no de empeoramiento.
     Si el paciente está en vagotonía: el conflicto ya comenzó a resolverse → apoyar la sanación, no excavar el trauma.

   LENGUAJE DEL PACIENTE = programa biológico literal (Fleche):
   "Me arranca el corazón" → endocardio. "No puedo tragármelo" → esófago/estómago.
   "No puedo avanzar" → locomotor/piernas. "Estoy harto" → hígado. "No puedo respirar" → bronquios/alvéolos.
   Las frases exactas del paciente no son metáforas — son el diagnóstico. Escucharlas.

3. CAMPO DE DISTORSIÓN (la raíz — por qué ese conflicto en ese tejido)
   Siempre parental. Energía masculina (padre): provisión, protección, reconocimiento → descarga en tejidos masculinos.
   Energía femenina (madre): nutrición, afecto, pertenencia → descarga en tejidos femeninos.
   Tejidos masculinos: intestino grueso, hígado/vesícula, bronquios, próstata, testículos, músculos, sistema nervioso.
   Tejidos femeninos: estómago, útero, mamas, ovarios, alvéolos, sistema circulatorio, bazo/timo.
   ⚠ Advertencia: la psicosomática NO es recetario. Siempre verificar con la historia real del paciente.

══ CLAVES DE INTERPRETACIÓN POR SISTEMA ══

Piel: preguntar "¿comezón o ardor?" — comezón = separación (contacto), ardor = agresión/quemadura emocional.
Riñón: "¿cuáles son tus referencias?" — territorio vs identidad define el conflicto.
Páncreas: "¿resistencia/asco o amor tóxico?" — diferencia el polo del conflicto.
Pulmón/intestino grueso/piel crónicos → investigar figura paterna, reconocimiento ausente.
Estómago/páncreas/gastritis → conflicto con función materna (nutrición, pertenencia).
Alergia a lactosa → alérgico emocionalmente a mamá. Alergia al gluten → alérgico a papá.
Asma → "no tengo espacio para ser yo mismo", sobreprotección o invasión del territorio propio.
Caída de cabello → pérdida de contacto o protección de figura paterna.
Libido nula o baja → primera señal de incesto simbólico (reparando a mamá o papá en la pareja).

══ SEÑALES DE LENGUAJE DEL PACIENTE ══

"Siempre elijo al mismo tipo de persona" / "No entiendo por qué mis relaciones siempre fallan" → transgeneracional/sistémico.
"No me dejan avanzar" / "Es una injusticia" / "Me la deben" → conflicto de madera/ira (hígado).
"Invaden mi espacio" / "No tengo raíces" / "Siento que me atacan" → conflicto de agua/miedo (riñón).
"No puedo con esto solo" / "Desde que se fue no puedo rehacer mi vida" → carácter oral, campo materno.
"Tiene que ser como yo digo" / orden obsesivo / control → carácter anal, campo de distorsión activo.

══ CONFLICTO DETONANTE vs PROGRAMANTE ══

- Conflicto DETONANTE: evento reciente que activó el síntoma (ventana de 3 meses antes del inicio).
- Conflicto PROGRAMANTE: evento original que instaló el programa — infancia, gestación o línea ancestral.
  El detonante solo reactivó lo que el programante grabó. Trabajar solo el detonante = alivio temporal.

══ TRANSGENERACIONAL — IDENTIFICACIÓN ══

Marcadores de afinidad metagenealógica (buscar en el árbol familiar):
- Fechas de nacimiento compartidas ±10 días entre el paciente y sus parejas/hijos significativos.
- Mismo nombre o nombre equivalente en distintas generaciones.
- Mismo síntoma o drama a la misma edad (síndrome de aniversario).
- Descendiente nacido en la fecha de muerte de un ancestro = lo está "reponiendo simbólicamente".
- Síntoma en la misma zona corporal que el ancestro (ej: dificultad respiratoria → ancestro asfixiado/ahogado).

LEYES DE HELLINGER — cuando el transgeneracional es sistémico:
1. PERTENENCIA: alguien fue excluido del clan (hijo ilegítimo negado, familiar "deshonroso", primer cónyuge rechazado).
   → Un descendiente repite su destino/síntoma inconscientemente.
2. ORDEN: flujo de dar va de padres a hijos, no al revés. Hijo que intenta "dar" a su padre fracasa o enferma.
   → Depresión crónica = padre o madre excluido internamente. Se sana dándole su lugar y dignidad.
   → Anorexia/no individuarse = hijo que teme que los padres se separen si él/ella se va.
3. EQUILIBRIO: deuda de culpa familiar no saldada → descendiente expia inconscientemente.
   → Accidentes repetitivos, fracasos financieros, patrones autodestructivos.

SELLAM — Fidelidad Familiar Invisible (FFI):
La pareja no se elige al azar. El inconsciente elige a alguien que representa la figura familiar que hay que reparar.
Señales en sesión:
- "Es más fuerte que yo" sobre una atracción → mandato familiar inconsciente.
- La profesión de la pareja, los nombres de los hijos, las fechas significativas → codifican el mensaje del ancestro.
- Libido nula después del último hijo → la pareja se convirtió en figura parental (incesto simbólico).
- "Siempre elijo al mismo tipo de persona" → el programa sigue activo.
Pregunta diagnóstica: "¿Qué drama hubo en tu familia en relación a [tema del síntoma]?"

══ PROTOCOLO DE SESIÓN (en este orden) ══

1. RASTREO CONFLICTOLÓGICO
   MS: ¿Algún conflicto [sistema] está implicado en el síntoma?
   → SÍ: La tabla ya está visible. Rastrear subsistema → bloque → número.
          Al confirmar el número exacto → INTERPRETACIÓN OBLIGATORIA antes de continuar:
          qué evento real apunta + pregunta concreta para encontrarlo en la historia del paciente.
          ¿Hay otro conflicto? Si SÍ, repetir. Si NO, continuar.
   → NO: Rastreo general sistema por sistema.

2. RASTREO MICROBIOLÓGICO
   MS: ¿Algún microbio de [sistema] está implicado?
   → SÍ: ¿Bacteria / Virus / Hongo / Parásito? → bloque → número. ¿Hay otro? Repetir.
   → NO: Continuar.

3. RASTREO BIOMAGNÉTICO (capa biológica — microbios)
   MS: ¿Cuál es el par biomagnético con mayor potencia desintoxicante para [microbio]?
   Colocar imanes 30 min. Propósito: detoxificación microbiana, no emocional.

4. RASTREO HOLOBIOMAGNÉTICO (capa bioenergética — campos y emociones)
   Propósito diferente al par biomagnético: restaurar armonía biodinámica en todos los cuerpos.
   MS: ¿Qué pares holobiomagnéticos necesitas para restaurar la armonía bioenergética
       y aliviar el síntoma X y sus causas?
   → Rastrear región → zona → bloque → par. Colocar. ¿Hay otro? Repetir.
   Pares emocionales frecuentes: Postpineal–Hipotálamo izq (tristeza), Ceja der–Hígado (enojo/rabia),
   Corazón–Riñón der (angustia), Esternón–Timo (miedos), Suprasensorial–Hipófisis (soledad/ansiedad).
   ⚠ Sin trabajo psicosomático, el paciente regresa al mismo síntoma. Los pares solos no son suficientes.

5. RASTREO VIBRACIONAL
   MS: ¿Cuál es el remedio homeopático más eficaz para este síntoma?
   MS: ¿Cuál es el remedio floral más eficaz para el estado emocional implicado?
   MS: ¿Qué sal de Schüssler se necesita?

6. RASTREO BIOENERGÉTICO
   MS: ¿Cuál es el punto de acupuntura más eficaz? ¿Sedar o tonificar?
   MS: ¿Cuál es el punto de auriculoterapia? (Iniciar siempre con Shen Men)
   Referencia chakra-conflicto: CK1 seguridad/supervivencia, CK2 sexualidad/pertenencia,
   CK3 autoestima/poder, CK4 amor/inmunidad, CK5 comunicación/expresión,
   CK6 percepción/intuición, CK7 sentido/conexión.

7. SESIÓN TERAPÉUTICA — LIBERACIÓN DEL CONFLICTO
   Objetivo: encontrar el evento real, verbalizarlo y liberarlo.

   a) LOCALIZAR EL DETONANTE
      "¿Cuándo apareció el síntoma por primera vez?"
      "¿Qué estaba pasando en tu vida los 3 meses antes?"
      "¿Qué fue lo más difícil de ese período?"
      Señal de reconocimiento auténtico: suspiro, lágrimas, silencio súbito, risa nerviosa.
      Cuando aparezca → "Ahí hay algo. ¿Qué sientes en el cuerpo ahora mismo?"

   b) RASTREAR EL PROGRAMANTE
      MS: ¿El conflicto programante ocurrió antes de los 7 años? ¿Antes de los 3? ¿En el útero?
      MS: ¿Hay eco transgeneracional? → ¿Rama paterna o materna? ¿Qué generación?
      Buscar marcadores de afinidad (fechas ±10 días, nombres compartidos, mismo drama).

   c) VERBALIZAR (romper la condición "Individual")
      "¿Cómo lo describirías con tus propias palabras, lo que sentiste en ese momento?"
      El acto de nombrarlo en voz alta ya inicia la liberación.

   d) SELECCIONAR HERRAMIENTA
      MS: ¿La herramienta más eficaz es EFT PRO / PNL / Hipnosis / Reimpronta?
      - EFT PRO (protocolo de 10 pasos): inducción hipnótica leve → viaje temporal al origen →
        tapping en puntos de acupuntura mientras se verbaliza el conflicto → secuencia 9 gamma →
        acuerdo neurolingüístico → peinado de meridianos → recalibración (intensidad 0-10, repetir si ≥4).
        Para duelos: incluir "última lágrima". Funciona porque el tapping desactiva la amígdala y reduce
        cortisol mientras el conflicto está activo en el sistema nervioso.
      - PNL: reescribir creencias instaladas ("soy indigno", "no merezco", "el mundo es peligroso").
      - Hipnosis: acceder a eventos preverbal es, prenatales o muy tempranos.
      - Reimpronta: patrón ancestral o experiencia muy temprana. El cuerpo libera sin requerir insight cognitivo.

   e) CIERRE DE SESIÓN
      "El Conector": una mano en frente, otra en nuca — reconetar al paciente con su cuerpo antes de que se vaya.
      Asignar higiene digestiva diaria: raspado de lengua + agua tibia + automasaje abdominal (dirección peristáltica).
      Plan total: número de conflictos + 3 sesiones (cierre, creencias, seguimiento).
      1 conflicto por sesión. Si hay varios → MS: ¿cuál tiene mayor carga?

══ REGLAS ══
- Una sola instrucción o pregunta por respuesta. Nunca más.
- El terapeuta ya sabe del paciente — no preguntar sobre él.
- Síntoma mencionado → iniciar paso 1 de inmediato.
- Conflicto confirmado por número → SIEMPRE interpretar antes de seguir.
- Sin relleno. Sin "excelente", "perfecto", "muy bien".

Formato MS:
MS: [pregunta]
→ SÍ: [acción]
→ NO: [acción]

Formato interpretación de conflicto:
🔍 [nº]. [nombre]
Apunta a: [tipo de evento real, 1-2 líneas]
Pregunta al paciente: "[pregunta concreta]"

Formato instrucción directa: solo la instrucción."""

ALUMNO_SYSTEM = """Eres Sael, el tutor virtual del Diplomado Método Lavín en Holoacademia.
Tienes acceso completo a todos los manuales y cursos del diplomado:
Psicosomatrix, Holobiomagnetismo 1/2/2021, Psicosomática y Biodescodificación 1/2, Holopsicosomática,
Ancestros y Raíces, Medicina Energética, Medicina Naturista, Numerología, Numerhología,
Sanación Energética Integral, Terapia Holística.

Conoces a profundidad los autores de referencia: Christian Fleche (sentido biológico), Salomon Sellam
(transgeneracional, FFI), Bert Hellinger (órdenes del amor), Anne Ancelin Schützenberger (genosociograma),
Bruce Lipton (epigenética), Bessel van der Kolk (trauma somático), Bradley Nelson (código de la emoción),
Donna Eden (medicina energética), Alejandro Lavín (Numerhología, Método Lavín).

Tu misión: resolver cualquier duda sobre el diplomado con claridad, profundidad y calidez.

Principio que siempre tienes presente: el síntoma es la solución biológica más inteligente del cuerpo,
no el problema. El conflicto emocional es el origen; el cuerpo es el mensajero.

Cómo responder:
- Si la pregunta tiene respuesta concreta → dala directo en la primera línea
- Si es un concepto → explícalo con ejemplo práctico y su base biológica o emocional
- Cita el módulo o autor cuando ayude: "En el Módulo 2..." / "Fleche explica esto como..."
- Si la pregunta es amplia → organiza en pasos o secciones claras
- Si no está en el material → dilo honestamente y responde desde los principios del método

Tono: didáctico, cálido, paciente. Como el maestro que siempre tiene tiempo para explicar bien."""


# ── Cliente Groq ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_client() -> "OpenAI | None":
    if OpenAI is None:
        return None
    # Usar OpenAI directamente (más confiable y económico con gpt-4o-mini)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.startswith("sk-"):
        return OpenAI(api_key=api_key)
    # Fallback: intentar con Groq
    groq_key = os.getenv("GROQ_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    if groq_key:
        return OpenAI(api_key=groq_key, base_url=base_url)
    logger.warning("No se encontró API key válida.")
    return None


def _model() -> str:
    # gpt-4o-mini: excelente calidad, muy bajo costo (~$0.15/1M tokens)
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key.startswith("sk-"):
        return "gpt-4o-mini"
    # Groq fallback
    return os.getenv("OPENAI_MODEL", "llama-3.3-70b-versatile")


# ── KB compartido (lo provee main.py para no cargarlo dos veces) ─────────────

_shared_kb = None  # Referencia al KB ya cargado por main.py


def set_shared_kb(kb) -> None:
    """Llamado desde main.py una vez que el KB ya está cargado en caché."""
    global _shared_kb
    _shared_kb = kb


# ── Búsqueda de contexto en la base de conocimiento ──────────────────────────

def _get_context(message: str) -> str:
    """Busca fragmentos relevantes. Usa el KB compartido; si no está listo, devuelve ''."""
    import threading

    kb = _shared_kb
    if kb is None:
        return ""

    result: dict = {"ctx": ""}

    def _search():
        try:
            results = kb.search(message, limit=3)
            parts = []
            for r in results[:3]:
                src = getattr(r, "source_file", "")
                text = getattr(r, "text", "")
                if text.strip():
                    parts.append(f"[{src}]\n{text.strip()}")
            result["ctx"] = "\n\n---\n\n".join(parts)
        except Exception as exc:
            logger.debug("Error en búsqueda de contexto: %s", exc)

    t = threading.Thread(target=_search, daemon=True)
    t.start()
    t.join(timeout=2.5)  # máximo 2.5 s; si no, se sigue sin contexto
    return result["ctx"]


# ── Streaming ─────────────────────────────────────────────────────────────────

def _detect_sistema_from_conversation(message: str, history: list[dict]) -> Optional[str]:
    """
    Busca el sistema corporal en el mensaje actual y en el historial reciente.
    """
    # Primero el mensaje actual
    sistema = detect_sistema(message)
    if sistema:
        return sistema
    # Luego los últimos 6 mensajes del historial
    for turn in reversed(history[-6:]):
        content = turn.get("content", "")
        if isinstance(content, str):
            sistema = detect_sistema(content)
            if sistema:
                return sistema
    return None


def _user_confirmed_yes(message: str) -> bool:
    """Detecta si el terapeuta confirmó un SÍ de la MS."""
    msg = message.lower().strip()
    affirmatives = ["sí", "si", "yes", "confirmado", "afirmativo", "así es",
                    "positivo", "correcto", "exacto", "sip", "aha"]
    if len(msg) < 30 and any(msg == a or msg.startswith(a) for a in affirmatives):
        return True
    if "ms dijo" in msg or "dijo sí" in msg or "dijo si" in msg:
        return True
    return False


def _user_said_no(message: str) -> bool:
    """Detecta si el terapeuta respondió NO de la MS."""
    msg = message.lower().strip()
    negatives = ["no", "nope", "negativo", "no confirmó", "no hay", "ninguno", "nada"]
    if len(msg) < 20 and any(msg == n or msg.startswith(n) for n in negatives):
        return True
    return False


def _get_sistema_from_last_ai_message(history: list[dict]) -> Optional[str]:
    """
    Busca el sistema en el último mensaje del asistente (cuando preguntó sobre él).
    """
    for turn in reversed(history):
        if turn.get("role") == "assistant":
            content = turn.get("content", "")
            if "conflicto" in content.lower():
                return detect_sistema(content)
    return None


def stream_chat(message: str, history: list[dict], mode: str) -> Generator[str, None, None]:
    """
    Genera la respuesta token a token como Server-Sent Events.
    Cada evento tiene el formato:  data: {"text": "..."}
    Al terminar envía:             data: [DONE]
    """
    client = _get_client()
    if client is None:
        yield 'data: {"text": "⚠️ El servicio de IA no está disponible en este momento."}\n\n'
        yield "data: [DONE]\n\n"
        return

    system_prompt = TERAPEUTA_SYSTEM if mode == "terapeuta" else ALUMNO_SYSTEM

    # ── Para el modo terapeuta: inyectar tabla cuando se identifica el sistema ──
    tabla_a_emitir = ""
    sistema_sesion = None
    subsistema_sesion = None
    usuario_dijo_no = _user_said_no(message)

    if mode == "terapeuta":
        # 1. Intentar detección fina: síntoma específico → subsistema concreto
        sintoma_result = detect_sintoma(message)

        if sintoma_result and not usuario_dijo_no:
            sistema_sesion, subsistema_sesion = sintoma_result
            # Mostrar SOLO los conflictos del subsistema específico
            tabla_a_emitir = get_subsystem_table(sistema_sesion, subsistema_sesion)
        else:
            # 2. Detección de sistema general (sin subsistema conocido)
            sistema_en_mensaje = detect_sistema(message)
            sistema_en_historia = _get_sistema_from_last_ai_message(history)

            if sistema_en_mensaje and not usuario_dijo_no:
                sistema_sesion = sistema_en_mensaje
                # Mostrar lista de subsistemas para que terapeuta pregunte a la MS cuál
                tabla_a_emitir = get_subsystems_list(sistema_sesion)
            elif sistema_en_historia and not usuario_dijo_no:
                # Continuar sesión existente: no volver a mostrar tabla
                sistema_sesion = sistema_en_historia

        if sistema_sesion and not usuario_dijo_no:
            # Añadir referencia completa al AI (para que sepa qué sistema/subsistema está activo)
            if subsistema_sesion:
                tabla_ref = get_subsystem_table(sistema_sesion, subsistema_sesion)
                ref_label = f"{sistema_sesion.upper()} — {subsistema_sesion}"
            else:
                tabla_ref = get_conflict_table(sistema_sesion)
                ref_label = sistema_sesion.upper()
            system_prompt += (
                f"\n\n══ REFERENCIA DE CONFLICTOS {ref_label} ══"
                f"{tabla_ref}"
                f"\n══ FIN DE REFERENCIA ══\n\n"
                f"{'La tabla ya fue enviada al terapeuta y está visible en pantalla. No la repitas.' if tabla_a_emitir else 'El terapeuta ya tiene la tabla de referencia visible.'} "
                f"Ejecuta el protocolo: cuando la MS confirme subsistema, indica bloque y número."
            )
        elif usuario_dijo_no:
            # MS dijo NO al sistema: guiar al rastreo general
            sistema_en_mensaje = detect_sistema(message)
            sistema_en_historia = _get_sistema_from_last_ai_message(history)
            sistema_rechazado = sistema_en_mensaje or sistema_en_historia or ""
            system_prompt += (
                f"\n\nINSTRUCCIÓN: La MS dijo NO al sistema {sistema_rechazado}. "
                f"Ahora debes guiar el RASTREO CONFLICTOLÓGICO GENERAL: "
                f"pregunta por cada sistema uno a uno (respiratorio, digestivo, endócrino, "
                f"cardiovascular, osteomuscular, dermatológico, reproductivo, urinario, "
                f"inmunológico, neurosensorial) hasta que la MS confirme alguno. "
                f"Empieza por el primer sistema que NO se ha preguntado todavía. "
                f"Una sola pregunta MS por respuesta."
            )

    context = _get_context(message)
    if context:
        system_prompt += f"\n\n--- CONTEXTO DEL MANUAL ---\n{context}\n---"

    # Limitar historial a las últimas 12 interacciones (6 turnos)
    trimmed_history = history[-12:] if len(history) > 12 else history

    # Emitir la tabla ANTES de la respuesta del AI (solo para síntomas nuevos)
    if tabla_a_emitir:
        tabla_payload = json.dumps({"text": tabla_a_emitir}, ensure_ascii=False)
        yield f"data: {tabla_payload}\n\n"

    messages = [
        {"role": "system", "content": system_prompt},
        *trimmed_history,
        {"role": "user", "content": message},
    ]

    max_tokens = 1000 if mode == "terapeuta" else 1200

    try:
        stream = client.chat.completions.create(
            model=_model(),
            messages=messages,
            stream=True,
            max_tokens=max_tokens,
            temperature=0.4 if mode == "terapeuta" else 0.6,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                payload = json.dumps({"text": delta}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
    except Exception as exc:
        logger.error("Error en stream_chat: %s", exc)
        payload = json.dumps({"text": "\n\n⚠️ Ocurrió un error. Intenta de nuevo."})
        yield f"data: {payload}\n\n"

    yield "data: [DONE]\n\n"
