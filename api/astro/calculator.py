"""
Capa de cálculo astronómico.
Usa kerykeion (Swiss Ephemeris) para:
  - Carta natal
  - Revolución Solar (RS) — lugar de nacimiento o residencia
  - Revolución Solar con Precesión (RSP) — corrección Froger
  - Mensal / Revolución Lunar (RL)
  - Tránsitos actuales
"""
from __future__ import annotations

import datetime
import math
import warnings
from typing import Optional

warnings.filterwarnings("ignore")

import swisseph as swe
from kerykeion import AstrologicalSubject, NatalAspects

# ─── Constantes ─────────────────────────────────────────────────────────────────

PLANETS = [
    ("sun", swe.SUN),
    ("moon", swe.MOON),
    ("mercury", swe.MERCURY),
    ("venus", swe.VENUS),
    ("mars", swe.MARS),
    ("jupiter", swe.JUPITER),
    ("saturn", swe.SATURN),
    ("uranus", swe.URANUS),
    ("neptune", swe.NEPTUNE),
    ("pluto", swe.PLUTO),
]

SIGN_NAMES = [
    "Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo",
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis",
]

SIGN_ES = {
    "Ari": "Aries", "Tau": "Tauro", "Gem": "Géminis", "Can": "Cáncer",
    "Leo": "Leo", "Vir": "Virgo", "Lib": "Libra", "Sco": "Escorpio",
    "Sag": "Sagitario", "Cap": "Capricornio", "Aqu": "Acuario", "Pis": "Piscis",
}

HOUSE_MAP = {
    "First_House": 1, "Second_House": 2, "Third_House": 3, "Fourth_House": 4,
    "Fifth_House": 5, "Sixth_House": 6, "Seventh_House": 7, "Eighth_House": 8,
    "Ninth_House": 9, "Tenth_House": 10, "Eleventh_House": 11, "Twelfth_House": 12,
}

PRECESSION_PER_YEAR_DEG = 50.29 / 3600.0   # 50.29 arcsec/year en grados


# ─── Helpers ────────────────────────────────────────────────────────────────────

def _sign_es(abbr: str) -> str:
    return SIGN_ES.get(abbr[:3], abbr)


def _abs_to_sign_pos(abs_pos: float) -> tuple[str, float]:
    sign_idx = int(abs_pos // 30) % 12
    pos = abs_pos % 30
    return SIGN_NAMES[sign_idx], round(pos, 2)


def _house_num(house_str: str) -> int:
    return HOUSE_MAP.get(house_str, 0)


def _planet_dict(p, natal_houses: Optional[list] = None) -> dict:
    """Convierte un objeto planeta de kerykeion a dict limpio."""
    sign = _sign_es(p.sign)
    house_n = _house_num(p.house)
    return {
        "signo": sign,
        "grado": round(p.position, 2),
        "abs_pos": round(p.abs_pos, 4),
        "casa": house_n,
        "retrogrado": bool(p.retrograde),
        "velocidad": round(getattr(p, "speed", 0), 4),
    }


def _get_essential_dignity(planet_name: str, sign: str) -> str:
    """Dignidades esenciales básicas según el sistema tradicional."""
    dignities = {
        # Domicilio
        "sun": {"Leo": "domicilio"},
        "moon": {"Cáncer": "domicilio"},
        "mercury": {"Géminis": "domicilio", "Virgo": "domicilio"},
        "venus": {"Tauro": "domicilio", "Libra": "domicilio"},
        "mars": {"Aries": "domicilio", "Escorpio": "domicilio"},
        "jupiter": {"Sagitario": "domicilio", "Piscis": "domicilio"},
        "saturn": {"Capricornio": "domicilio", "Acuario": "domicilio"},
        # Exaltación
        "sun_ex": {"Aries": "exaltación"},
        "moon_ex": {"Tauro": "exaltación"},
        "mercury_ex": {"Virgo": "exaltación"},
        "venus_ex": {"Piscis": "exaltación"},
        "mars_ex": {"Capricornio": "exaltación"},
        "jupiter_ex": {"Cáncer": "exaltación"},
        "saturn_ex": {"Libra": "exaltación"},
        # Detrimento
        "sun_det": {"Acuario": "detrimento"},
        "moon_det": {"Capricornio": "detrimento"},
        "mercury_det": {"Sagitario": "detrimento", "Piscis": "detrimento"},
        "venus_det": {"Escorpio": "detrimento", "Aries": "detrimento"},
        "mars_det": {"Libra": "detrimento", "Tauro": "detrimento"},
        "jupiter_det": {"Géminis": "detrimento", "Virgo": "detrimento"},
        "saturn_det": {"Cáncer": "detrimento", "Leo": "detrimento"},
        # Caída
        "sun_cai": {"Libra": "caída"},
        "moon_cai": {"Escorpio": "caída"},
        "mercury_cai": {"Piscis": "caída"},
        "venus_cai": {"Virgo": "caída"},
        "mars_cai": {"Cáncer": "caída"},
        "jupiter_cai": {"Capricornio": "caída"},
        "saturn_cai": {"Aries": "caída"},
    }
    pn = planet_name.lower()
    checks = [pn, f"{pn}_ex", f"{pn}_det", f"{pn}_cai"]
    for key in checks:
        if key in dignities and sign in dignities[key]:
            return dignities[key][sign]
    return "neutral"


# ─── Solar Return via pyswisseph ─────────────────────────────────────────────────

def _find_solar_return_jd(natal_sun_abs: float, year: int) -> float:
    """
    Encuentra el JD exacto del retorno solar en 'year'.
    Usa swe.solcross_ut (efímeras suizas).
    """
    # Punto de partida: ~60 días antes del posible retorno
    approx_month = int((natal_sun_abs / 30)) + 1  # mes aproximado del signo solar
    # Aproximación: buscar desde 1 Feb del año para garantizar cobertura
    jd_start = swe.julday(year, 1, 15, 0.0)
    try:
        sr_jd = swe.solcross_ut(natal_sun_abs, jd_start, swe.FLG_SWIEPH)
        # Verificar que caiga en el año correcto
        yr, *_ = swe.revjul(sr_jd)
        if yr != year:
            # Intentar con inicio en año anterior
            jd_start2 = swe.julday(year - 1, 10, 1, 0.0)
            sr_jd = swe.solcross_ut(natal_sun_abs, jd_start2, swe.FLG_SWIEPH)
        return sr_jd
    except Exception:
        # Fallback manual
        jd_start = swe.julday(year, 1, 1, 0.0)
        best_jd = jd_start
        best_diff = 999.0
        for i in range(400):
            jd = jd_start + i * 0.1
            pos, _ = swe.calc_ut(jd, swe.SUN)
            diff = abs(pos[0] - natal_sun_abs)
            if diff > 180:
                diff = 360 - diff
            if diff < best_diff:
                best_diff = diff
                best_jd = jd
        return best_jd


def _jd_to_utc(jd: float) -> tuple[int, int, int, int, int]:
    """Convierte JD a (year, month, day, hour, minute) UTC."""
    yr, mo, dy, hr = swe.revjul(jd)
    h = int(hr)
    m = int((hr - h) * 60)
    return int(yr), int(mo), int(dy), h, m


# ─── Cálculo de carta con kerykeion ──────────────────────────────────────────────

def _kerykeion_subject(
    name: str, year: int, month: int, day: int, hour: int, minute: int,
    lat: float, lng: float, tz_str: str,
) -> AstrologicalSubject:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return AstrologicalSubject(
            name, year, month, day, hour, minute,
            lat=lat, lng=lng, tz_str=tz_str,
        )


def _extract_chart_data(subj: AstrologicalSubject, label: str = "") -> dict:
    """Extrae todos los datos de un AstrologicalSubject en un dict limpio."""
    # Planetas
    planet_names = [
        "sun", "moon", "mercury", "venus", "mars",
        "jupiter", "saturn", "uranus", "neptune", "pluto",
        "true_node", "chiron",
    ]
    planetas = {}
    for pn in planet_names:
        try:
            p = getattr(subj, pn)
            if p is None:
                continue
            d = _planet_dict(p)
            d["dignidad"] = _get_essential_dignity(pn, d["signo"])
            planetas[pn] = d
        except Exception:
            pass

    # Casas
    house_attrs = [
        "first_house", "second_house", "third_house", "fourth_house",
        "fifth_house", "sixth_house", "seventh_house", "eighth_house",
        "ninth_house", "tenth_house", "eleventh_house", "twelfth_house",
    ]
    casas = {}
    for i, ha in enumerate(house_attrs, 1):
        try:
            h = getattr(subj, ha)
            casas[i] = {
                "signo": _sign_es(h.sign),
                "grado": round(h.position, 2),
                "abs_pos": round(h.abs_pos, 4),
            }
        except Exception:
            pass

    # Aspectos
    aspectos = []
    try:
        na = NatalAspects(subj)
        for a in na.relevant_aspects:
            ad = a.model_dump() if hasattr(a, "model_dump") else dict(a)
            aspectos.append({
                "planeta1": ad.get("p1_name", ""),
                "planeta2": ad.get("p2_name", ""),
                "tipo": ad.get("aspect", ""),
                "orbe": round(ad.get("orbit", 0), 2),
                "movimiento": ad.get("aspect_movement", ""),
            })
    except Exception:
        pass

    return {
        "label": label,
        "fecha": f"{subj.year}-{subj.month:02d}-{subj.day:02d}",
        "hora": f"{subj.hour:02d}:{subj.minute:02d}",
        "lat": subj.lat,
        "lng": subj.lng,
        "tz": subj.tz_str,
        "planetas": planetas,
        "casas": casas,
        "aspectos": aspectos,
    }


# ─── API pública ─────────────────────────────────────────────────────────────────

def get_natal_data(
    nombre: str,
    year: int, month: int, day: int, hour: int, minute: int,
    lat: float, lng: float, tz_str: str,
) -> dict:
    """Calcula y devuelve la carta natal completa."""
    subj = _kerykeion_subject(nombre, year, month, day, hour, minute, lat, lng, tz_str)
    return _extract_chart_data(subj, "natal")


def get_solar_return(
    natal_sun_abs: float,
    sr_year: int,
    lat: float, lng: float, tz_str: str,
    nombre: str = "RS",
) -> dict:
    """
    Calcula la Revolución Solar para 'sr_year'.
    El lugar puede ser nacimiento o residencia actual.
    """
    sr_jd = _find_solar_return_jd(natal_sun_abs, sr_year)
    yr, mo, dy, h, m = _jd_to_utc(sr_jd)

    # kerykeion recibe hora local; convertimos UTC aproximado a local
    # (para producción: usar pytz para conversión exacta)
    subj = _kerykeion_subject(nombre, yr, mo, dy, h, m, lat, lng, tz_str)
    data = _extract_chart_data(subj, "rs")
    data["jd"] = round(sr_jd, 6)
    return data


def get_rsp(
    natal_sun_abs: float,
    edad: int,
    sr_year: int,
    lat: float, lng: float, tz_str: str,
    nombre: str = "RSP",
) -> dict:
    """
    Revolución Solar con Precesión (Froger).
    Corrige la longitud solar natal sumando 50.29"/año × edad,
    luego calcula el retorno a esa posición sidérea.
    """
    correccion_deg = PRECESSION_PER_YEAR_DEG * edad
    natal_sun_rsp = (natal_sun_abs + correccion_deg) % 360

    rsp_jd = _find_solar_return_jd(natal_sun_rsp, sr_year)
    yr, mo, dy, h, m = _jd_to_utc(rsp_jd)

    subj = _kerykeion_subject(nombre, yr, mo, dy, h, m, lat, lng, tz_str)
    data = _extract_chart_data(subj, "rsp")
    data["correccion_arcseg"] = round(correccion_deg * 3600, 2)
    data["jd"] = round(rsp_jd, 6)
    return data


def get_mensal(
    sr_moon_abs: float,
    sr_date: str,          # "YYYY-MM-DD"
    lat: float, lng: float, tz_str: str,
    nombre: str = "RL",
) -> dict:
    """
    Calcula el Mensal (Revolución Lunar) más próximo a hoy,
    usando la posición de la Luna en la RS como punto de retorno.
    La Luna regresa a esa posición cada ~27.32 días (mes sidéreo).
    """
    today = datetime.date.today()
    sr_dt = datetime.date.fromisoformat(sr_date)
    jd_start = swe.julday(sr_dt.year, sr_dt.month, sr_dt.day, 12.0)

    # Buscar el próximo retorno lunar a la posición de RS
    best_jd = None
    best_diff = 999.0
    for i in range(400):  # ~400 * 0.1 días = ~40 días de búsqueda
        jd = jd_start + i * 0.1
        yr, mo, dy, _ = swe.revjul(jd)
        check_date = datetime.date(int(yr), int(mo), int(dy))
        if check_date < today:
            continue
        pos, _ = swe.calc_ut(jd, swe.MOON)
        diff = abs(pos[0] - sr_moon_abs)
        if diff > 180:
            diff = 360 - diff
        if diff < best_diff:
            best_diff = diff
            best_jd = jd
        if diff < 0.5 and best_diff < 0.5:
            break

    if best_jd is None:
        best_jd = jd_start + 27.32

    yr, mo, dy, h, m = _jd_to_utc(best_jd)
    subj = _kerykeion_subject(nombre, yr, mo, dy, h, m, lat, lng, tz_str)
    data = _extract_chart_data(subj, "mensal")
    data["jd"] = round(best_jd, 6)
    return data


def get_transits_today(
    lat: float, lng: float, tz_str: str,
) -> dict:
    """Posiciones planetarias actuales (tránsitos del día)."""
    now = datetime.datetime.utcnow()
    subj = _kerykeion_subject(
        "Tránsitos", now.year, now.month, now.day, now.hour, now.minute,
        lat, lng, tz_str,
    )
    return _extract_chart_data(subj, "transitos")


def compute_house_superposition(
    rs_casas: dict, natal_casas: dict,
) -> dict:
    """
    Determina en qué casa natal cae cada cúspide de la RS.
    Retorna {casa_rs: casa_natal} para las 12 casas.
    """
    result = {}
    for rs_num, rs_data in rs_casas.items():
        rs_abs = rs_data["abs_pos"]
        # Encontrar en qué casa natal cae esa posición
        natal_house = 12  # default
        for n_num in range(1, 13):
            n_start = natal_casas.get(n_num, {}).get("abs_pos", 0)
            n_end = natal_casas.get(n_num % 12 + 1, {}).get("abs_pos", n_start + 30)
            # Normalizar arco
            if n_end < n_start:
                n_end += 360
            rs_check = rs_abs if rs_abs >= n_start else rs_abs + 360
            if n_start <= rs_check < n_end:
                natal_house = n_num
                break
        result[rs_num] = natal_house
    return result
