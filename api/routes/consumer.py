"""
Motor Copiloto "modo consumidor" para la landing de campaña (/promo).

Entrega directa al PÚBLICO GENERAL (no terapeutas):
- Método Holos  → mapa emocional + protocolos de liberación
- Método REMA   → guion de hipnosis personalizada
- Lecturas      → tarot, horóscopo, carta natal (astrología), numerología
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

from api.chat_service import _generar_con_sistema, set_holos_lang

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
## Tus talentos
## Tu camino de crecimiento
Si falta la hora, dilo con naturalidad y trabaja con el resto."""

NUMER_CONSUMER = ENTERTAIN + """

Eres un numerólogo cercano. Con el nombre completo y la fecha de nacimiento de la persona,
entrega una lectura de numerología personal con encabezados ##:
## Tu número de vida
## Tus fortalezas
## Tus retos
## Tu año personal
## Un consejo práctico"""


def _texto_inputs(inputs: dict) -> str:
    """Convierte el formulario de la persona en un bloque de texto para el prompt."""
    if not isinstance(inputs, dict):
        return ""
    etiquetas = {
        "nombre": "Nombre", "sintoma": "Síntoma o malestar", "historia": "Su historia / contexto",
        "pregunta": "Pregunta o intención", "signo": "Signo", "fecha_nacimiento": "Fecha de nacimiento",
        "hora_nacimiento": "Hora de nacimiento", "lugar_nacimiento": "Lugar de nacimiento",
        "conflicto": "Conflicto emocional detectado",
    }
    partes = []
    for k, v in inputs.items():
        if v is None or str(v).strip() == "":
            continue
        partes.append(f"{etiquetas.get(k, k)}: {str(v).strip()[:1500]}")
    return "\n".join(partes)


# product → (system_prompt, max_tokens)
_PRODUCTOS = {
    "holos":         (HOLOS_CONSUMER, 3500),
    "rema":          (REMA_CONSUMER, 4000),
    "tarot":         (TAROT_CONSUMER, 1600),
    "horoscopo":     (HOROSCOPO_CONSUMER, 1600),
    "carta-natal":   (ASTRO_CONSUMER, 2400),
    "numerologia":   (NUMER_CONSUMER, 1800),
}
# Paquetes = varias lecturas, una tras otra.
_PAQUETES = {
    "pack-claridad": ["carta-natal", "horoscopo", "tarot"],
    "pack-completo": ["carta-natal", "horoscopo", "tarot", "numerologia"],
}


class GenReq(BaseModel):
    product: str = Field(..., description="holos | rema | tarot | horoscopo | carta-natal | numerologia | pack-*")
    lang: str = Field(default="es")
    inputs: dict = Field(default_factory=dict)


def _generar_uno(product: str, inputs: dict) -> dict:
    sys_tok = _PRODUCTOS.get(product)
    if not sys_tok:
        return {"ok": False, "error": "producto_invalido", "answer": ""}
    system, max_tokens = sys_tok
    prompt = _texto_inputs(inputs) or "(sin datos adicionales)"
    temp = 0.6 if product in ("tarot", "horoscopo", "carta-natal", "numerologia") else 0.5
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


@router.get("/health")
async def health():
    return {"ok": True, "productos": list(_PRODUCTOS.keys()) + list(_PAQUETES.keys())}
