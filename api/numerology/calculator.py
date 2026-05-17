"""
Motor de cálculo numerológico completo.
Sistema: Numerhología (Alejandro González Lavín) + Numerología Pitagórica.

Incluye:
  - Pentagrama del nombre: Expresión, Impulso, Impresión
  - Pentagrama del nacimiento: Alma, Karma, Misión
  - 4 Pináculos + 4 Desafíos + Ciclos de vida
  - Deudas Kármicas (13/4, 14/5, 16/7, 19/1)
  - Herencia Paterna y Materna
  - Esencia del nombre + Influencia Locomotora
  - Planos de expresión (Mental, Físico, Emocional, Espiritual)
  - Vibración Latente / Número de Madurez
  - Año Universal, Año Personal, Mes Personal, Día Personal
  - Número de la Casa / Hogar
  - Potencias y Carencias

Cálculos puramente matemáticos — sin dependencias externas.
"""
from __future__ import annotations

import datetime
import unicodedata

# ─── Tabla Pitagórica ─────────────────────────────────────────────────────────
_TABLA: dict[str, int] = {
    "A": 1, "J": 1, "S": 1,
    "B": 2, "K": 2, "T": 2,
    "C": 3, "L": 3, "U": 3,
    "D": 4, "M": 4, "V": 4,
    "E": 5, "N": 5, "W": 5,
    "F": 6, "O": 6, "X": 6,
    "G": 7, "P": 7, "Y": 7,
    "H": 8, "Q": 8, "Z": 8,
    "I": 9, "R": 9,
    # Español
    "Ñ": 5,
    "Á": 1, "É": 5, "Í": 9, "Ó": 6, "Ú": 3, "Ü": 3,
}

_VOCALES: frozenset[str] = frozenset("AEIOUÁÉÍÓÚÜ")

# ─── Deudas Kármicas ──────────────────────────────────────────────────────────
_DEUDAS: dict[int, dict] = {
    13: {
        "codigo": "13/4",
        "tema": "Renacimiento por el trabajo",
        "descripcion": (
            "Patrón de inercia o pereza acumulada. Esta deuda exige disciplina, "
            "esfuerzo sostenido y aprender a construir paso a paso. "
            "El camino es la transformación a través del trabajo consciente."
        ),
    },
    14: {
        "codigo": "14/5",
        "tema": "Equilibrio entre libertad y compromiso",
        "descripcion": (
            "Exceso de libertad o irresponsabilidad en vidas pasadas. "
            "El reto es crear vínculos estables, comprometerse sin escapar, "
            "y equilibrar la libertad personal con el respeto a los demás."
        ),
    },
    16: {
        "codigo": "16/7",
        "tema": "Caída del ego y renacer espiritual",
        "descripcion": (
            "Abuso de poder o posición en el pasado. Esta deuda trae caídas "
            "aparentemente súbitas para limpiar el ego. El camino es la humildad, "
            "la búsqueda espiritual honesta y servir sin buscar reconocimiento."
        ),
    },
    19: {
        "codigo": "19/1",
        "tema": "Servicio más allá del ego",
        "descripcion": (
            "Individualismo extremo o uso del poder en detrimento de otros. "
            "El reto es aprender a pedir ayuda, reconocer la interdependencia "
            "y liderar desde el servicio genuino, no desde el ego."
        ),
    },
}


# ─── Utilidades base ──────────────────────────────────────────────────────────

def reducir(n: int, mantener_maestros: bool = True) -> int:
    """Reduce n a un solo dígito. Preserva 11, 22, 33 si mantener_maestros=True."""
    while n > 9:
        if mantener_maestros and n in (11, 22, 33):
            break
        n = sum(int(d) for d in str(n))
    return n


def _detectar_deuda(suma_intermedia: int) -> dict | None:
    """Si la suma antes de reducir es 13/14/16/19, retorna la deuda kármica."""
    return _DEUDAS.get(suma_intermedia)


def _limpiar_nombre(nombre: str) -> str:
    """Devuelve letras del nombre en mayúsculas, solo caracteres con valor en la tabla."""
    resultado = []
    for ch in nombre.upper():
        if ch in _TABLA:
            resultado.append(ch)
        elif ch.isalpha():
            norm = unicodedata.normalize("NFD", ch)
            base = norm[0] if norm else ch
            if base in _TABLA:
                resultado.append(base)
    return "".join(resultado)


def _valor_letra(letra: str) -> int:
    return _TABLA.get(letra.upper(), 0)


def _suma_con_deuda(suma: int) -> tuple[int, dict | None]:
    """Retorna (valor_reducido, deuda_o_None). Detecta deuda antes de reducir."""
    deuda = _detectar_deuda(suma)
    return reducir(suma), deuda


# ─── Dígitos del nombre ───────────────────────────────────────────────────────

def digito_nombre(nombre_completo: str) -> dict:
    """
    Expresión (todas), Impulso (vocales), Impresión (consonantes).
    Detecta deudas kármicas en cada suma.
    """
    nombre = _limpiar_nombre(nombre_completo)
    letras = []
    suma_expr = suma_imp = suma_impr = 0

    for ch in nombre:
        val = _valor_letra(ch)
        es_vocal = ch in _VOCALES
        letras.append({"letra": ch, "valor": val, "es_vocal": es_vocal})
        suma_expr += val
        if es_vocal:
            suma_imp += val
        else:
            suma_impr += val

    expresion, deuda_expr = _suma_con_deuda(suma_expr)
    impulso,   deuda_imp  = _suma_con_deuda(suma_imp)
    impresion, deuda_impr = _suma_con_deuda(suma_impr)

    return {
        "expresion":      expresion,
        "impulso":        impulso,
        "impresion":      impresion,
        "expresion_suma": suma_expr,
        "impulso_suma":   suma_imp,
        "impresion_suma": suma_impr,
        "deuda_expresion": deuda_expr,
        "deuda_impulso":   deuda_imp,
        "deuda_impresion": deuda_impr,
        "letras":          letras,
    }


def esencia_nombre(primer_nombre: str) -> tuple[int, dict | None]:
    """
    Esencia = solo el primer nombre (sin apellidos), letras sumadas y reducidas.
    Representa la vibración intrínseca del nombre de pila.
    """
    letras = _limpiar_nombre(primer_nombre)
    suma = sum(_valor_letra(ch) for ch in letras)
    return _suma_con_deuda(suma)


def influencia_locomotora(nombre: str) -> int:
    """
    Valor de la primera letra del primer nombre.
    Rige el impulso primario de reacción e instinto.
    """
    letras = _limpiar_nombre(nombre)
    return _valor_letra(letras[0]) if letras else 0


def calcular_planos(nombre_completo: str) -> dict:
    """
    Planos de expresión (de qué plano provienen los talentos del nombre).
      Mental    = cantidad de 1s y 8s  (pensamiento, intuición mental)
      Físico    = cantidad de 4s y 5s  (acción, materia, sensorialidad)
      Emocional = cantidad de 2s, 3s y 6s (sentimiento, relaciones, arte)
      Espiritual= cantidad de 7s y 9s  (búsqueda, compasión, trascendencia)
    """
    letras = _limpiar_nombre(nombre_completo)
    vals = [_valor_letra(ch) for ch in letras if _valor_letra(ch)]

    mental     = vals.count(1) + vals.count(8)
    fisico     = vals.count(4) + vals.count(5)
    emocional  = vals.count(2) + vals.count(3) + vals.count(6)
    espiritual = vals.count(7) + vals.count(9)
    total      = mental + fisico + emocional + espiritual

    def _nivel(n: int) -> str:
        if total == 0:
            return "sin datos"
        pct = n / total
        if pct == 0:
            return "ausente"
        if pct < 0.15:
            return "muy bajo"
        if pct < 0.30:
            return "bajo"
        if pct < 0.50:
            return "equilibrado"
        return "dominante"

    return {
        "mental":     {"cantidad": mental,     "nivel": _nivel(mental)},
        "fisico":     {"cantidad": fisico,      "nivel": _nivel(fisico)},
        "emocional":  {"cantidad": emocional,   "nivel": _nivel(emocional)},
        "espiritual": {"cantidad": espiritual,  "nivel": _nivel(espiritual)},
    }


def herencia(apellido: str) -> tuple[int, dict | None]:
    """Suma de los valores de las letras del apellido, reducida."""
    letras = _limpiar_nombre(apellido)
    suma = sum(_valor_letra(ch) for ch in letras)
    return _suma_con_deuda(suma)


# ─── Dígitos del nacimiento ───────────────────────────────────────────────────

def digito_alma(dia: int) -> tuple[int, dict | None]:
    """Alma = reducción del día. Personalidad privada, esencia íntima."""
    return _suma_con_deuda(dia)


def digito_karma(mes: int) -> tuple[int, dict | None]:
    """Karma = reducción del mes. Personalidad pública, rol social."""
    return _suma_con_deuda(mes)


def digito_mision(dia: int, mes: int, anio: int) -> tuple[int, dict | None]:
    """
    Misión de Vida = suma de TODOS los dígitos de la fecha completa.
    Principal propósito vital. Detecta deuda kármica antes de reducir.
    """
    suma = sum(int(d) for d in f"{dia:02d}{mes:02d}{anio}")
    return _suma_con_deuda(suma)


# ─── Vibración Latente / Número de Madurez ───────────────────────────────────

def vibracion_latente(expresion: int, mision: int) -> tuple[int, dict | None]:
    """
    Vibración Latente = Expresión + Misión, reducida.
    También llamado Número de Madurez. Se activa alrededor de los 35-45 años.
    Representa el potencial que emerge cuando la persona integra su nombre y su fecha.
    """
    return _suma_con_deuda(expresion + mision)


# ─── Pináculos y Desafíos ─────────────────────────────────────────────────────

def _año_reducido_sin_maestros(anio: int) -> int:
    return reducir(sum(int(d) for d in str(anio)), mantener_maestros=False)


def calcular_pinaculos_desafios(dia: int, mes: int, anio: int) -> dict:
    """
    Cuatro pináculos (energía de cada ciclo de vida) y cuatro desafíos (aprendizaje).

    P1 = día_r + mes_r        D1 = |día_r - mes_r|
    P2 = día_r + año_r        D2 = |día_r - año_r|
    P3 = P1 + P2              D3 = |D1 - D2|
    P4 = mes_r + año_r        D4 = |mes_r - año_r|
    """
    d = reducir(dia,  mantener_maestros=False)
    m = reducir(mes,  mantener_maestros=False)
    a = _año_reducido_sin_maestros(anio)

    p1, dp1 = _suma_con_deuda(d + m)
    p2, dp2 = _suma_con_deuda(d + a)
    p3, dp3 = _suma_con_deuda(p1 + p2)
    p4, dp4 = _suma_con_deuda(m + a)

    return {
        "pinaculos": [p1, p2, p3, p4],
        "desafios":  [abs(d - m), abs(d - a), abs(abs(d - m) - abs(d - a)), abs(m - a)],
        "deudas_pinaculos": [dp1, dp2, dp3, dp4],
    }


def calcular_ciclos(mision: int) -> list[dict]:
    """
    Duración del 1er ciclo = 36 - misión (maestros convertidos: 11→2, 22→4, 33→6).
    2do y 3er ciclo: 9 años. 4to: el resto de la vida.
    """
    mis_base = {11: 2, 22: 4, 33: 6}.get(mision, mision)
    inicio_2 = 36 - mis_base
    inicio_3 = inicio_2 + 9
    inicio_4 = inicio_3 + 9

    return [
        {"ciclo": 1, "desde": 0,        "hasta": inicio_2 - 1, "descripcion": "Formación del carácter"},
        {"ciclo": 2, "desde": inicio_2, "hasta": inicio_3 - 1, "descripcion": "Desarrollo y construcción"},
        {"ciclo": 3, "desde": inicio_3, "hasta": inicio_4 - 1, "descripcion": "Consolidación"},
        {"ciclo": 4, "desde": inicio_4, "hasta": None,         "descripcion": "Madurez y legado"},
    ]


# ─── Potencias y Carencias ────────────────────────────────────────────────────

def calcular_potencias_carencias(numeros: list[int]) -> dict:
    """
    Cuenta la frecuencia de cada dígito 1-9 en todos los números del cuadro.
    Potencias ≥ 3 apariciones. Carencias = 0 apariciones.
    """
    conteo = {i: 0 for i in range(1, 10)}
    for n in numeros:
        if n == 11:
            conteo[1] += 2
        elif n == 22:
            conteo[2] += 2
        elif n == 33:
            conteo[3] += 2
        elif 1 <= n <= 9:
            conteo[n] += 1

    return {
        "conteo":    conteo,
        "potencias": sorted(k for k, v in conteo.items() if v >= 3),
        "carencias":  sorted(k for k, v in conteo.items() if v == 0),
    }


# ─── Ciclos personales (Año / Mes / Día) ─────────────────────────────────────

def año_universal(anio: int) -> int:
    """
    Energía colectiva del año calendario.
    2026 → 2+0+2+6 = 10 → 1. Afecta a todo el mundo por igual.
    """
    return reducir(sum(int(d) for d in str(anio)), mantener_maestros=False)


def año_personal(dia: int, mes: int, anio_actual: int) -> int:
    """
    Año Personal = día_nac + mes_nac + todos los dígitos del año actual.
    Ciclo de 9 años que rige la energía personal de cada período de 12 meses.
    El ciclo comienza en el cumpleaños, no el 1 de enero.
    """
    suma = dia + mes + sum(int(d) for d in str(anio_actual))
    return reducir(suma)


def mes_personal(anio_pers: int, mes_actual: int) -> int:
    """
    Mes Personal = Año Personal + mes del calendario (1-12).
    Energía específica del mes en curso dentro del año personal.
    """
    return reducir(anio_pers + mes_actual)


def dia_personal(mes_pers: int, dia_actual: int) -> int:
    """
    Día Personal = Mes Personal + día del calendario (1-31).
    Energía puntual del día.
    """
    return reducir(mes_pers + dia_actual)


def calcular_ciclos_personales(dia_nac: int, mes_nac: int,
                                fecha_consulta: datetime.date | None = None) -> dict:
    """
    Calcula el Año Universal, Año Personal, Mes Personal y Día Personal
    para la fecha de consulta (por defecto: hoy).
    """
    hoy = fecha_consulta or datetime.date.today()
    au  = año_universal(hoy.year)
    ap  = año_personal(dia_nac, mes_nac, hoy.year)
    mp  = mes_personal(ap, hoy.month)
    dp  = dia_personal(mp, hoy.day)

    return {
        "fecha_consulta":  hoy.isoformat(),
        "año_universal":   au,
        "año_personal":    ap,
        "mes_personal":    mp,
        "dia_personal":    dp,
        "año_consultado":  hoy.year,
        "mes_consultado":  hoy.month,
        "dia_consultado":  hoy.day,
    }


# ─── Número de la Casa ────────────────────────────────────────────────────────

def numero_casa(numero_str: str) -> int:
    """
    Número numerológico del hogar.
    Suma SOLO los dígitos del número de calle/puerta (NO el nombre de la calle).
    Para casas NO se preservan números maestros — siempre reducción completa a 1 dígito.

    Ejemplos:
      "638"        → 6+3+8=17 → 1+7=8
      "510, apt 304" → 5+1+0+3+0+4=13 → 1+3=4
    """
    digitos = sum(int(ch) for ch in numero_str if ch.isdigit())
    return reducir(digitos, mantener_maestros=False)


# ─── API pública: cálculo completo ───────────────────────────────────────────

def calcular_numeroscopio(
    nombre_completo: str,
    dia: int,
    mes: int,
    anio: int,
    apellido_paterno: str = "",
    apellido_materno: str = "",
    fecha_consulta: datetime.date | None = None,
) -> dict:
    """
    Calcula el numeroscopio completo con todos los indicadores disponibles.

    Parámetros:
      nombre_completo   — nombre y apellido(s) completos
      dia, mes, anio    — fecha de nacimiento
      apellido_paterno  — solo apellido paterno (para herencia)
      apellido_materno  — solo apellido materno (para herencia)
      fecha_consulta    — para ciclos personales (default: hoy)
    """
    # ── Nombre completo ────────────────────────────────────────────────────────
    nd = digito_nombre(nombre_completo)

    # ── Primer nombre (para esencia y locomotora) ──────────────────────────────
    primer_nombre = nombre_completo.strip().split()[0]
    esencia_val, deuda_esencia = esencia_nombre(primer_nombre)
    locomotora_val = influencia_locomotora(primer_nombre)

    # ── Planos de expresión ────────────────────────────────────────────────────
    planos = calcular_planos(nombre_completo)

    # ── Nacimiento ────────────────────────────────────────────────────────────
    alma_val,   deuda_alma   = digito_alma(dia)
    karma_val,  deuda_karma  = digito_karma(mes)
    mision_val, deuda_mision = digito_mision(dia, mes, anio)

    # ── Vibración Latente / Número de Madurez ─────────────────────────────────
    latente_val, deuda_latente = vibracion_latente(nd["expresion"], mision_val)

    # ── Pináculos y desafíos ───────────────────────────────────────────────────
    pd = calcular_pinaculos_desafios(dia, mes, anio)

    # ── Ciclos de vida ─────────────────────────────────────────────────────────
    ciclos = calcular_ciclos(mision_val)

    # ── Herencias ────────────────────────────────────────────────────────────
    her_pat = her_mat = None
    if apellido_paterno.strip():
        hp_val, hp_deuda = herencia(apellido_paterno)
        her_pat = {"valor": hp_val, "deuda": hp_deuda, "apellido": apellido_paterno}
    if apellido_materno.strip():
        hm_val, hm_deuda = herencia(apellido_materno)
        her_mat = {"valor": hm_val, "deuda": hm_deuda, "apellido": apellido_materno}

    # ── Ciclos personales (hoy) ────────────────────────────────────────────────
    ciclos_pers = calcular_ciclos_personales(dia, mes, fecha_consulta)

    # ── Potencias y carencias ──────────────────────────────────────────────────
    todos = [
        nd["expresion"], nd["impulso"], nd["impresion"],
        alma_val, karma_val, mision_val, latente_val,
        *pd["pinaculos"], *pd["desafios"],
    ]
    if her_pat:
        todos.append(her_pat["valor"])
    if her_mat:
        todos.append(her_mat["valor"])
    pc = calcular_potencias_carencias(todos)

    # ── Recopilar todas las deudas kármicas detectadas ─────────────────────────
    deudas_encontradas = []
    for fuente, deuda in [
        ("expresion",  nd["deuda_expresion"]),
        ("impulso",    nd["deuda_impulso"]),
        ("impresion",  nd["deuda_impresion"]),
        ("alma",       deuda_alma),
        ("karma",      deuda_karma),
        ("mision",     deuda_mision),
        ("latente",    deuda_latente),
        ("pináculo 1", pd["deudas_pinaculos"][0]),
        ("pináculo 2", pd["deudas_pinaculos"][1]),
        ("pináculo 3", pd["deudas_pinaculos"][2]),
        ("pináculo 4", pd["deudas_pinaculos"][3]),
    ]:
        if deuda:
            deudas_encontradas.append({"fuente": fuente, **deuda})

    return {
        # ── Nombre ────────────────────────────────────────────────────────────
        "nombre": {
            "original":       nombre_completo,
            "letras":         nd["letras"],
            "expresion":      nd["expresion"],
            "expresion_suma": nd["expresion_suma"],
            "impulso":        nd["impulso"],
            "impulso_suma":   nd["impulso_suma"],
            "impresion":      nd["impresion"],
            "impresion_suma": nd["impresion_suma"],
            "esencia":        esencia_val,
            "locomotora":     locomotora_val,
            "planos":         planos,
        },
        # ── Nacimiento ───────────────────────────────────────────────────────
        "nacimiento": {
            "dia": dia, "mes": mes, "anio": anio,
            "alma":   alma_val,
            "karma":  karma_val,
            "mision": mision_val,
        },
        # ── Síntesis y madurez ────────────────────────────────────────────────
        "vibracion_latente": latente_val,
        # ── Herencias ────────────────────────────────────────────────────────
        "herencia_paterna": her_pat,
        "herencia_materna": her_mat,
        # ── Ciclos de vida ────────────────────────────────────────────────────
        "pinaculos":  pd["pinaculos"],
        "desafios":   pd["desafios"],
        "ciclos":     ciclos,
        # ── Ciclos personales (hoy) ───────────────────────────────────────────
        "ciclos_personales": ciclos_pers,
        # ── Deudas kármicas ───────────────────────────────────────────────────
        "deudas_karmicas": deudas_encontradas,
        # ── Potencias y carencias ─────────────────────────────────────────────
        "potencias_carencias": pc,
        # ── Resumen plano (para UI) ───────────────────────────────────────────
        "resumen": {
            "expresion":  nd["expresion"],
            "impulso":    nd["impulso"],
            "impresion":  nd["impresion"],
            "alma":       alma_val,
            "karma":      karma_val,
            "mision":     mision_val,
            "latente":    latente_val,
            "esencia":    esencia_val,
            "locomotora": locomotora_val,
            "año_personal":  ciclos_pers["año_personal"],
            "mes_personal":  ciclos_pers["mes_personal"],
            "dia_personal":  ciclos_pers["dia_personal"],
            "año_universal": ciclos_pers["año_universal"],
            "p1": pd["pinaculos"][0], "p2": pd["pinaculos"][1],
            "p3": pd["pinaculos"][2], "p4": pd["pinaculos"][3],
            "d1": pd["desafios"][0],  "d2": pd["desafios"][1],
            "d3": pd["desafios"][2],  "d4": pd["desafios"][3],
        },
    }
