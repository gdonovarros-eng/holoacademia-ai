"""
Calculadora tarótica — funciones puras sin dependencias externas.
Sistemas: Greer (personalidad/alma), Zodiaco, Decanatos.
"""
from __future__ import annotations

import datetime

from .knowledge import (
    ARCANOS_MAYORES,
    ARCANOS_MENORES,
    SIGNO_A_MAYOR,
    SIGNO_A_PERSONA,
    FECHA_A_LECCION,
    PALO_INFO,
)


# ─── Utilidades internas ──────────────────────────────────────────────────────

def _reducir_hasta_mayor(n: int) -> int:
    """Reduce sumando dígitos hasta llegar al rango 0-22."""
    while n > 22:
        n = sum(int(d) for d in str(n))
    return n


def _nombre_arcano_mayor(numero: int, sistema: str = "rws") -> str:
    """Retorna el nombre del arcano mayor por número y sistema."""
    for nombre, datos in ARCANOS_MAYORES.items():
        if datos["numero"] == numero:
            if sistema == "marsella":
                return datos["nombre_marsella"]
            if sistema == "thoth":
                return datos["nombre_thoth"]
            return datos["nombre_rws"]
    return str(numero)


def _datos_mayor(numero: int) -> dict:
    """Retorna el dict completo de un arcano mayor por número."""
    return next(
        (v for v in ARCANOS_MAYORES.values() if v["numero"] == numero),
        {},
    )


# ─── Cálculos de cartas personales ───────────────────────────────────────────

def carta_personalidad(dia: int, mes: int, anio: int) -> dict:
    """
    Carta de Personalidad (Mary K. Greer):
    Suma día + mes + año y reduce hasta ≤ 22.
    Representa la misión de vida y la forma de ser en el mundo.
    """
    total = dia + mes + anio
    numero = _reducir_hasta_mayor(total)
    nombre = _nombre_arcano_mayor(numero)
    datos = _datos_mayor(numero)
    return {
        "numero": numero,
        "nombre": nombre,
        "suma_original": total,
        "datos": datos,
    }


def carta_alma(numero_personalidad: int) -> dict:
    """
    Carta del Alma (Greer):
    Reduce el número de Personalidad a un solo dígito (≤ 9).
    Representa la esencia del alma, la motivación más profunda.
    Si la Personalidad ya es ≤ 9, son la misma carta.
    """
    n = numero_personalidad
    while n > 9:
        n = sum(int(d) for d in str(n))
    nombre = _nombre_arcano_mayor(n)
    datos = _datos_mayor(n)
    return {"numero": n, "nombre": nombre, "datos": datos}


def carta_factor_oculto(numero_personalidad: int) -> dict:
    """
    Factor Oculto (Greer):
    Complemento a 23: 23 - número de Personalidad.
    Representa el potencial oculto, la sombra que integrar,
    la energía opuesta que equilibra la Personalidad.
    """
    numero = 23 - numero_personalidad
    if numero < 0 or numero > 22:
        return {}
    nombre = _nombre_arcano_mayor(numero)
    datos = _datos_mayor(numero)
    return {"numero": numero, "nombre": nombre, "datos": datos}


def carta_anio_personal(
    dia: int,
    mes: int,
    anio_actual: int | None = None,
) -> dict:
    """
    Carta del Año Personal:
    Misma fórmula que Personalidad pero con el año actual, anterior y siguiente.
    Refleja la energía arquetípica que rige cada período de 12 meses.
    """
    if anio_actual is None:
        anio_actual = datetime.date.today().year

    resultado: dict[str, dict] = {}
    for label, anio in [
        ("anterior", anio_actual - 1),
        ("actual", anio_actual),
        ("siguiente", anio_actual + 1),
    ]:
        total = dia + mes + anio
        numero = _reducir_hasta_mayor(total)
        nombre = _nombre_arcano_mayor(numero)
        datos = _datos_mayor(numero)
        resultado[label] = {
            "anio": anio,
            "numero": numero,
            "nombre": nombre,
            "datos": datos,
        }
    return resultado


def carta_zodiaco(signo: str, sistema: str = "rws") -> dict:
    """
    Arcano Mayor asociado al signo solar según sistema (rws/marsella/thoth).
    Refleja la energía arquetípica del signo en el tarot.
    """
    signo_lower = signo.lower().strip()
    info = SIGNO_A_MAYOR.get(signo_lower, {})
    numero = info.get(sistema, info.get("rws", 0))
    nombre = _nombre_arcano_mayor(numero, sistema)
    datos = _datos_mayor(numero)
    return {"numero": numero, "nombre": nombre, "signo": signo_lower, "datos": datos}


def carta_persona(signo: str) -> dict:
    """
    Carta de Corte (figura) asociada al signo solar.
    Usada para identificar al consultante en la tirada.
    """
    signo_lower = signo.lower().strip()
    nombre_completo = SIGNO_A_PERSONA.get(signo_lower, "")
    datos = ARCANOS_MENORES.get(nombre_completo, {})
    return {"nombre": nombre_completo, "signo": signo_lower, "datos": datos}


def carta_leccion_zodiacal(dia: int, mes: int) -> dict:
    """
    Arcano Menor de destino según el decanato astrológico de la fecha de nacimiento.
    Cada decanato de 10° corresponde a un arcano menor que describe la lección del alma.
    """
    fecha_num = mes * 100 + dia
    for rango in FECHA_A_LECCION:
        inicio = rango["inicio"]
        fin = rango["fin"]
        inicio_num = inicio[0] * 100 + inicio[1]
        fin_num = fin[0] * 100 + fin[1]
        if inicio_num <= fecha_num <= fin_num:
            carta = rango["carta"]
            return {
                "nombre": carta,
                "datos": ARCANOS_MENORES.get(carta, {}),
            }
    return {}


def cartas_leccion_numerologica(numero_alma: int) -> list[dict]:
    """
    Los 4 arcanos menores con el número del alma (uno por palo).
    Cada palo aporta una dimensión distinta de la misma vibración numérica.
    """
    nombres_num = {
        1: "As",
        2: "Dos",
        3: "Tres",
        4: "Cuatro",
        5: "Cinco",
        6: "Seis",
        7: "Siete",
        8: "Ocho",
        9: "Nueve",
        10: "Diez",
    }
    palos = ["Bastos", "Copas", "Espadas", "Pentáculos"]
    palos_key = ["bastos", "copas", "espadas", "pentaculos"]

    # Normalizar al rango 1-10
    n = numero_alma
    if n < 1:
        n = 1
    elif n > 10:
        n = (n % 10) or 10

    prefijo = nombres_num.get(n, str(n))
    resultado = []
    for palo, palo_k in zip(palos, palos_key):
        nombre = f"{prefijo} de {palo}"
        datos = ARCANOS_MENORES.get(nombre, {})
        palo_data = PALO_INFO.get(palo_k, {})
        resultado.append({
            "nombre": nombre,
            "palo": palo_k,
            "numero": n,
            "datos": datos,
            "palo_info": palo_data,
        })
    return resultado


def calcular_perfil_tarot(
    dia: int,
    mes: int,
    anio: int,
    signo_solar: str = "",
    numero_alma_numerologia: int | None = None,
    anio_actual: int | None = None,
    sistema: str = "rws",
) -> dict:
    """
    Perfil tarótico completo del consultante.

    Incluye:
    - Carta de Personalidad (Greer)
    - Carta del Alma
    - Factor Oculto
    - Carta del Año Personal (anterior, actual, siguiente)
    - Lección Zodiacal (decanato)
    - Carta del Zodíaco (si hay signo solar)
    - Carta de Persona / figura (si hay signo solar)
    - Lecciones Numerológicas (si hay número del alma de numerología)
    """
    if anio_actual is None:
        anio_actual = datetime.date.today().year

    # Cálculos del nacimiento
    pers = carta_personalidad(dia, mes, anio)
    alma = carta_alma(pers["numero"])
    oculto = carta_factor_oculto(pers["numero"])
    anio_pers = carta_anio_personal(dia, mes, anio_actual)
    leccion_zodiacal = carta_leccion_zodiacal(dia, mes)

    # Cálculos zodiacales (opcionales)
    zodiaco: dict = {}
    persona: dict = {}
    if signo_solar:
        zodiaco = carta_zodiaco(signo_solar, sistema)
        persona = carta_persona(signo_solar)

    # Lecciones numerológicas (opcionales)
    lecciones_num: list[dict] = []
    if numero_alma_numerologia and 1 <= numero_alma_numerologia <= 22:
        n_norm = numero_alma_numerologia if numero_alma_numerologia <= 10 else (
            numero_alma_numerologia % 10 or 10
        )
        lecciones_num = cartas_leccion_numerologica(n_norm)

    return {
        "personalidad": pers,
        "alma": alma,
        "factor_oculto": oculto,
        "anio_personal": anio_pers,
        "leccion_zodiacal": leccion_zodiacal,
        "carta_zodiaco": zodiaco,
        "carta_persona": persona,
        "lecciones_numerologicas": lecciones_num,
        "sistema": sistema,
        "fecha_nacimiento": {
            "dia": dia,
            "mes": mes,
            "anio": anio,
        },
    }
