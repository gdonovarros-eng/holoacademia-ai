"""
Constructor del mega-prompt para el motor astrológico.
Ensambla los datos calculados + el conocimiento de los libros
en un prompt que Claude interpreta como astrólogo experto.
"""
from __future__ import annotations

import datetime
from typing import Optional

from .knowledge import (
    ASC_ANUAL_POR_SIGNO,
    ASC_ANUAL_POR_CASA_NATAL,
    MC_ANUAL_POR_CASA,
    PLANETA_EN_CASA_RS,
    FIGURAS_ASPECTUALES,
    TIPO_ASPECTO,
    DIGNIDAD_INTERPRETACION,
    CASAS_RS_DESCRIPCION,
    TIMING_RS_MESES,
    RSP_EXPLICACION,
    MENSALES_EXPLICACION,
    NODOS_SIGNIFICADO,
    CONJUNCIONES_EN_RS,
    TEMPERAMENTOS,
    ASTRO_MEDICA_PLANETAS,
    ASTRO_MEDICA_SIGNOS,
    TRIADA_PERSONALIDAD,
    CAPAS_PLANETARIAS,
    RETROGRADACION_EN_RS,
    TRANSITOS_SOL_EN_RS,
    ASTEROIDES_SIGNIFICADO,
)

PLANET_NOMBRES_ES = {
    "sun": "Sol",
    "moon": "Luna",
    "mercury": "Mercurio",
    "venus": "Venus",
    "mars": "Marte",
    "jupiter": "Júpiter",
    "saturn": "Saturno",
    "uranus": "Urano",
    "neptune": "Neptuno",
    "pluto": "Plutón",
    "true_node": "Nodo Norte",
    "chiron": "Quirón",
}

ASPECT_NOMBRES_ES = {
    "conjunction": "conjunción",
    "opposition": "oposición",
    "trine": "trígono",
    "square": "cuadratura",
    "sextile": "sextil",
    "quincunx": "quincuncio",
    "semisquare": "semicuadrado",
    "sesquisquare": "sesquicuadrado",
    "semisextile": "semisextil",
}


def _fmt_planet(name: str, data: dict) -> str:
    pname = PLANET_NOMBRES_ES.get(name, name.capitalize())
    retro = " (Retrógrado)" if data.get("retrogrado") else ""
    dig = data.get("dignidad", "neutral")
    dig_str = f" [{DIGNIDAD_INTERPRETACION.get(dig, dig)}]" if dig != "neutral" else ""
    return (
        f"  {pname}: {data['signo']} {data['grado']:.1f}° — "
        f"Casa {data['casa']}{retro}{dig_str}"
    )


def _fmt_aspect(a: dict) -> str:
    p1 = PLANET_NOMBRES_ES.get(a["planeta1"].lower(), a["planeta1"])
    p2 = PLANET_NOMBRES_ES.get(a["planeta2"].lower(), a["planeta2"])
    tipo = ASPECT_NOMBRES_ES.get(a["tipo"], a["tipo"])
    orbe = a.get("orbe", 0)
    mov = a.get("movimiento", "")
    sep_apl = "separativo (ya ocurrió)" if "Separating" in mov else "aplicativo (aún por venir)"
    return f"  {p1} {tipo} {p2} — orbe {orbe:.1f}° ({sep_apl})"


def _detect_aspect_figures(aspectos: list[dict]) -> list[str]:
    """Detecta figuras aspectuales presentes según el catálogo de Maciá."""
    figuras_detectadas = []

    # Contar tipos de aspectos
    tipos = [a["tipo"] for a in aspectos]
    sq_count = tipos.count("square")
    opp_count = tipos.count("opposition")
    tri_count = tipos.count("trine")
    sex_count = tipos.count("sextile")
    qui_count = tipos.count("quincunx")
    ssq_count = tipos.count("semisquare") + tipos.count("sesquisquare")

    if opp_count >= 1 and sq_count >= 2:
        figuras_detectadas.append("T Cuadrada")
    if opp_count >= 2 and sq_count >= 4:
        figuras_detectadas.append("Gran Cruz")
    if tri_count >= 2 and sex_count >= 3:
        figuras_detectadas.append("Gran Sextil")
    if tri_count >= 3:
        figuras_detectadas.append("Gran Trígono")
    if qui_count >= 2 and sex_count >= 1:
        figuras_detectadas.append("Dedo de Dios")
    if ssq_count >= 4:
        figuras_detectadas.append("Semicuadrado Cósmico")
    if qui_count >= 4:
        figuras_detectadas.append("Quincucio Cósmico")
    if sex_count >= 4 and opp_count >= 1:
        figuras_detectadas.append("Sextil Cósmico")

    return figuras_detectadas


def _nodo_norte_sign(natal: dict) -> str:
    """Retorna el signo del Nodo Norte natal."""
    nn = natal.get("planetas", {}).get("true_node", {})
    return nn.get("signo", "")


def build_mega_prompt(
    nombre: str,
    natal: dict,
    rs: dict,
    rsp: Optional[dict],
    mensal: Optional[dict],
    transitos: Optional[dict],
    superposicion: dict,
    edad: int,
    fecha_nacimiento: str,
    lugar_nacimiento: str,
    lugar_actual: str,
    profundidad: str = "completo",
) -> str:
    """
    Construye el mega-prompt completo para la interpretación de Claude.
    """
    hoy = datetime.date.today().strftime("%d de %B de %Y")
    lines = []

    # ── INSTRUCCIÓN DE ROL ──────────────────────────────────────────────────────
    lines.append(f"""Eres un astrólogo experto con formación en Astrología Occidental clásica y moderna.
Tu análisis integra cuatro sistemas:
1. Carta Natal (análisis del carácter, misión y potencial)
2. Revolución Solar (predicción anual — sistema Volguine)
3. RSP Sidérea (corrección por precesión — método Froger)
4. Mensal (Revolución Lunar mensual — método Privat)

FUNDAMENTOS DEL ANÁLISIS NATAL (ten estos presentes):
{TRIADA_PERSONALIDAD}

CAPAS PLANETARIAS:
{chr(10).join(f"  {k}: {v}" for k, v in CAPAS_PLANETARIAS.items())}

INSTRUCCIONES DE REDACCIÓN:
- Escribe en español, en primera persona dirigida al consultante ("tu Sol en...", "este año tu...")
- Sé concreto, profundo y útil. Nada de vaguedades.
- Estructura el análisis con las secciones indicadas, usando encabezados claros.
- Para cada sección, integra el conocimiento de todos los sistemas disponibles.
- El INDICADOR #1 de la RS es el ASC anual en la casa natal (⭐ marcado abajo). ÚSALO.
- Tono: sabio, cálido, directo. Como un maestro que conoce al alumno profundamente.
- Extensión: análisis completo y detallado. No escatimes en profundidad.
""")

    # ── DATOS DEL CONSULTANTE ───────────────────────────────────────────────────
    lines.append(f"═══════════════════════════════════════════════════════════")
    lines.append(f"DATOS DEL CONSULTANTE")
    lines.append(f"═══════════════════════════════════════════════════════════")
    lines.append(f"Nombre: {nombre}")
    lines.append(f"Fecha de nacimiento: {fecha_nacimiento}")
    lines.append(f"Lugar de nacimiento: {lugar_nacimiento}")
    lines.append(f"Lugar actual (para RS): {lugar_actual}")
    lines.append(f"Edad: {edad} años")
    lines.append(f"Fecha del análisis: {hoy}")
    lines.append("")

    # ── CARTA NATAL ──────────────────────────────────────────────────────────────
    natal_planetas = natal.get("planetas", {})
    natal_casas = natal.get("casas", {})
    natal_aspectos = natal.get("aspectos", [])

    lines.append(f"═══════════════════════════════════════════════════════════")
    lines.append(f"CARTA NATAL — {fecha_nacimiento} — {lugar_nacimiento}")
    lines.append(f"═══════════════════════════════════════════════════════════")
    lines.append("")
    lines.append("PUNTOS PRINCIPALES:")

    # ASC y MC natal
    asc_natal = natal_casas.get(1, {})
    mc_natal = natal_casas.get(10, {})
    lines.append(f"  ASC (Ascendente): {asc_natal.get('signo','?')} {asc_natal.get('grado',0):.1f}°")
    lines.append(f"  MC (Medio Cielo): {mc_natal.get('signo','?')} {mc_natal.get('grado',0):.1f}°")
    lines.append("")

    lines.append("POSICIONES PLANETARIAS:")
    for pname, pdata in natal_planetas.items():
        lines.append(_fmt_planet(pname, pdata))
    lines.append("")

    lines.append("CASAS (cúspides):")
    for n in range(1, 13):
        casa = natal_casas.get(n, {})
        lines.append(f"  Casa {n:2d}: {casa.get('signo','?')} {casa.get('grado',0):.1f}°")
    lines.append("")

    # Aspectos natales más importantes (filtrar orbe < 5°)
    aspectos_fuertes = [a for a in natal_aspectos if a.get("orbe", 99) < 5.0]
    aspectos_fuertes.sort(key=lambda x: x.get("orbe", 99))
    lines.append(f"ASPECTOS EXACTOS (orbe < 5°) — {len(aspectos_fuertes)} encontrados:")
    for a in aspectos_fuertes[:15]:
        lines.append(_fmt_aspect(a))
    lines.append("")

    # Figuras aspectuales natales
    figuras_natal = _detect_aspect_figures(natal_aspectos)
    if figuras_natal:
        lines.append("FIGURAS ASPECTUALES PRESENTES EN LA CARTA NATAL (Maciá):")
        for fig in figuras_natal:
            lines.append(f"\n{FIGURAS_ASPECTUALES.get(fig, fig)}")
        lines.append("")

    # Nodo Norte
    nn_signo = _nodo_norte_sign(natal)
    if nn_signo:
        nn_key = f"norte_{nn_signo.lower().replace('é','e').replace('á','a').replace('ó','o').replace('ú','u').replace('í','i')}"
        nn_interp = NODOS_SIGNIFICADO.get(nn_key, "")
        if nn_interp:
            lines.append(f"NODO NORTE EN {nn_signo.upper()}:")
            lines.append(f"  {nn_interp}")
            lines.append("")

    # ── REVOLUCIÓN SOLAR ─────────────────────────────────────────────────────────
    rs_planetas = rs.get("planetas", {})
    rs_casas = rs.get("casas", {})
    rs_aspectos = rs.get("aspectos", [])
    rs_fecha = rs.get("fecha", "")

    asc_rs = rs_casas.get(1, {})
    mc_rs = rs_casas.get(10, {})
    asc_rs_signo = asc_rs.get("signo", "")
    mc_rs_casa_natal = superposicion.get(10, "?")

    lines.append(f"═══════════════════════════════════════════════════════════")
    lines.append(f"REVOLUCIÓN SOLAR — Año {rs_fecha[:4] if rs_fecha else ''}")
    lines.append(f"Fecha exacta de la RS: {rs_fecha} {rs.get('hora','')}")
    lines.append(f"Lugar de RS: {lugar_actual}")
    lines.append(f"═══════════════════════════════════════════════════════════")
    lines.append("")

    # ASC anual — por signo (tonalidad) + por casa natal (el indicador #1 de Volguine)
    asc_rs_casa_natal = superposicion.get(1, None)  # en qué casa natal cae el ASC de RS
    if asc_rs_signo:
        lines.append(f"ASC ANUAL: {asc_rs_signo} — TONALIDAD PSICOLÓGICA DEL AÑO:")
        tone = ASC_ANUAL_POR_SIGNO.get(asc_rs_signo, "")
        if tone:
            lines.append(f"  {tone}")
        lines.append("")

    if asc_rs_casa_natal and asc_rs_casa_natal != "?":
        try:
            casa_n = int(asc_rs_casa_natal)
            lines.append(f"⭐ ASC ANUAL en CASA {casa_n} NATAL — INDICADOR PRIMARIO (Volguine):")
            asc_natal_interp = ASC_ANUAL_POR_CASA_NATAL.get(casa_n, "")
            if asc_natal_interp:
                lines.append(f"  {asc_natal_interp}")
            lines.append("")
        except (ValueError, TypeError):
            pass

    # MC anual
    if mc_rs_casa_natal and mc_rs_casa_natal != "?":
        lines.append(f"MC ANUAL en Casa {mc_rs_casa_natal} natal — SECTOR DE ACCIÓN PRINCIPAL:")
        mc_interp = MC_ANUAL_POR_CASA.get(int(mc_rs_casa_natal), "")
        if mc_interp:
            lines.append(f"  {mc_interp}")
        lines.append("")

    # Superposición de casas RS→natal
    lines.append("SUPERPOSICIÓN DE CASAS RS→NATAL:")
    lines.append("(Casa RS → Casa Natal donde cae)")
    for rs_n in range(1, 13):
        nat_n = superposicion.get(rs_n, "?")
        desc_rs = CASAS_RS_DESCRIPCION.get(rs_n, f"Casa {rs_n} RS")
        lines.append(f"  {desc_rs} → cae en Casa {nat_n} natal")
    lines.append("")

    # Planetas de RS en sus casas de RS
    lines.append("PLANETAS EN CASAS DE RS:")
    for pname, pdata in rs_planetas.items():
        casa_rs = pdata.get("casa", 0)
        pname_es = PLANET_NOMBRES_ES.get(pname, pname)
        interp = PLANETA_EN_CASA_RS.get(pname, {}).get(casa_rs, "")
        retro = " (Ret.)" if pdata.get("retrogrado") else ""
        lines.append(f"  {pname_es} en Casa {casa_rs} RS{retro}: {pdata['signo']} {pdata['grado']:.1f}°")
        if interp:
            lines.append(f"    → {interp}")
    lines.append("")

    # Aspectos de RS fuertes + detección de conjunciones clave (Volguine)
    asp_rs_fuertes = [a for a in rs_aspectos if a.get("orbe", 99) < 5.0]
    asp_rs_fuertes.sort(key=lambda x: x.get("orbe", 99))
    lines.append(f"ASPECTOS INTERNOS RS (orbe < 5°):")
    for a in asp_rs_fuertes[:12]:
        lines.append(_fmt_aspect(a))
    lines.append("")

    # Conjunciones clave de Volguine detectadas en RS
    conjunciones_detectadas = []
    _conj_map = {
        ("sun", "moon"): "sol_luna", ("moon", "sun"): "sol_luna",
        ("sun", "mars"): "sol_marte", ("mars", "sun"): "sol_marte",
        ("sun", "jupiter"): "sol_jupiter", ("jupiter", "sun"): "sol_jupiter",
        ("sun", "saturn"): "sol_saturno", ("saturn", "sun"): "sol_saturno",
        ("sun", "uranus"): "sol_urano", ("uranus", "sun"): "sol_urano",
        ("sun", "neptune"): "sol_neptuno", ("neptune", "sun"): "sol_neptuno",
        ("sun", "pluto"): "sol_pluton", ("pluto", "sun"): "sol_pluton",
        ("moon", "mars"): "luna_marte", ("mars", "moon"): "luna_marte",
        ("moon", "jupiter"): "luna_jupiter", ("jupiter", "moon"): "luna_jupiter",
        ("moon", "saturn"): "luna_saturno", ("saturn", "moon"): "luna_saturno",
        ("moon", "uranus"): "luna_urano", ("uranus", "moon"): "luna_urano",
        ("venus", "mars"): "venus_marte", ("mars", "venus"): "venus_marte",
        ("venus", "jupiter"): "venus_jupiter", ("jupiter", "venus"): "venus_jupiter",
        ("venus", "uranus"): "venus_urano", ("uranus", "venus"): "venus_urano",
        ("mars", "jupiter"): "marte_jupiter", ("jupiter", "mars"): "marte_jupiter",
        ("mars", "saturn"): "marte_saturno", ("saturn", "mars"): "marte_saturno",
        ("mars", "uranus"): "marte_urano", ("uranus", "mars"): "marte_urano",
        ("jupiter", "saturn"): "jupiter_saturno", ("saturn", "jupiter"): "jupiter_saturno",
        ("jupiter", "uranus"): "jupiter_urano", ("uranus", "jupiter"): "jupiter_urano",
    }
    for a in asp_rs_fuertes:
        if a.get("tipo") == "conjunction":
            key = (a.get("planeta1", "").lower(), a.get("planeta2", "").lower())
            conj_key = _conj_map.get(key)
            if conj_key and conj_key in CONJUNCIONES_EN_RS:
                conjunciones_detectadas.append((key, conj_key))

    if conjunciones_detectadas:
        lines.append("CONJUNCIONES DESTACADAS EN RS (Volguine):")
        for (p1, p2), ckey in conjunciones_detectadas:
            p1_es = PLANET_NOMBRES_ES.get(p1, p1)
            p2_es = PLANET_NOMBRES_ES.get(p2, p2)
            lines.append(f"\n  {p1_es} conjunción {p2_es}:")
            lines.append(f"  {CONJUNCIONES_EN_RS[ckey]}")
        lines.append("")

    # Figuras en RS
    figuras_rs = _detect_aspect_figures(rs_aspectos)
    if figuras_rs:
        lines.append("FIGURAS ASPECTUALES EN LA RS (Maciá):")
        for fig in figuras_rs:
            lines.append(f"\n{FIGURAS_ASPECTUALES.get(fig, fig)}")
        lines.append("")

    # Retrogradación en RS
    retrogrados_rs = [pname for pname, pdata in rs_planetas.items() if pdata.get("retrogrado")]
    if retrogrados_rs:
        retrogr_es = [PLANET_NOMBRES_ES.get(p, p) for p in retrogrados_rs]
        lines.append(f"PLANETAS RETRÓGRADOS EN RS: {', '.join(retrogr_es)}")
        lines.append(f"  {RETROGRADACION_EN_RS}")
        lines.append("")

    # Timing mensual
    lines.append("SISTEMA DE TIMING MENSUAL:")
    lines.append(TIMING_RS_MESES)
    lines.append(TRANSITOS_SOL_EN_RS)
    lines.append("")

    # ── RSP ──────────────────────────────────────────────────────────────────────
    if rsp:
        rsp_casas = rsp.get("casas", {})
        asc_rsp = rsp_casas.get(1, {})
        mc_rsp = rsp_casas.get(10, {})

        lines.append(f"═══════════════════════════════════════════════════════════")
        lines.append(f"RSP (REVOLUCIÓN SOLAR SIDÉREA) — Método Froger")
        lines.append(f"Fecha RSP: {rsp.get('fecha','')} {rsp.get('hora','')}")
        lines.append(f"Corrección precesional aplicada: {rsp.get('correccion_arcseg',0):.1f}\" ({edad} años × 50.29\")")
        lines.append(f"═══════════════════════════════════════════════════════════")
        lines.append(RSP_EXPLICACION)
        lines.append(f"ASC en RSP: {asc_rsp.get('signo','?')} {asc_rsp.get('grado',0):.1f}°")
        lines.append(f"MC en RSP: {mc_rsp.get('signo','?')} {mc_rsp.get('grado',0):.1f}°")
        lines.append(f"Luna en RSP: {rsp.get('planetas',{}).get('moon',{}).get('signo','?')} {rsp.get('planetas',{}).get('moon',{}).get('grado',0):.1f}°")
        lines.append("")

    # ── MENSAL ───────────────────────────────────────────────────────────────────
    if mensal:
        mensal_planetas = mensal.get("planetas", {})
        mensal_casas = mensal.get("casas", {})

        lines.append(f"═══════════════════════════════════════════════════════════")
        lines.append(f"MENSAL (REVOLUCIÓN LUNAR) — Método Privat")
        lines.append(f"Fecha del próximo Mensal: {mensal.get('fecha','')} {mensal.get('hora','')}")
        lines.append(f"═══════════════════════════════════════════════════════════")
        lines.append(MENSALES_EXPLICACION)
        lines.append("")
        lines.append("POSICIONES DEL MENSAL:")
        asc_rl = mensal_casas.get(1, {})
        mc_rl = mensal_casas.get(10, {})
        lines.append(f"  ASC Mensal: {asc_rl.get('signo','?')} {asc_rl.get('grado',0):.1f}°")
        lines.append(f"  MC Mensal: {mc_rl.get('signo','?')} {mc_rl.get('grado',0):.1f}°")
        lines.append("")
        lines.append("PLANETAS EN MENSAL:")
        for pname, pdata in list(mensal_planetas.items())[:7]:
            lines.append(_fmt_planet(pname, pdata))
        lines.append("")

    # ── INSTRUCCIÓN FINAL DE REDACCIÓN ───────────────────────────────────────────
    lines.append(f"═══════════════════════════════════════════════════════════")
    lines.append("AHORA GENERA EL ANÁLISIS ASTROLÓGICO COMPLETO")
    lines.append(f"═══════════════════════════════════════════════════════════")
    lines.append(f"""
Escribe el análisis COMPLETO de {nombre} con estas secciones exactas:

## 🌟 IDENTIDAD ASTROLÓGICA — Tu Carta Natal
Analiza en profundidad: ASC natal (máscara y actitud vital), Sol (identidad central),
Luna (mundo emocional interno), MC (vocación y propósito), los planetas más fuertes
(por dignidad y aspectos), las figuras aspectuales detectadas y su significado profundo,
el Nodo Norte como misión de vida. Integra todo en un retrato psicológico coherente.

## 💫 EL AÑO EN CURSO — Tu Revolución Solar
Analiza: el ASC anual y la tonalidad psicológica de este año específico,
el MC anual y el sector de acción principal, la superposición de casas más importante
(cuál es EL gran tema del año), los planetas más destacados de la RS y qué anuncian,
los aspectos más fuertes (aplicativos = lo que viene; separativos = lo que ya pasó),
figuras aspectuales en la RS y su significado para este año concreto.

## 📅 CALENDARIO DEL AÑO — Timing Mensual
Indica en qué período del año se activan los principales temas de la RS.
Nombra 2-3 momentos o períodos clave del año (aproximados en meses).
Identifica el período de mayor oportunidad y el período de mayor precaución.

## 🌙 ESTE MES — Tu Mensal
{f"Analiza el Mensal: qué tema domina las próximas semanas, qué planeta está activado, qué área de vida está en foco. Integra con la RS y el tema natal." if mensal else "El Mensal no fue calculado para este análisis."}

## 🔭 RSP SIDÉREA — La Lectura Profunda
{f"Compara RS y RSP: ¿el ASC cambia de signo? ¿El MC se traslada a una casa natal diferente? ¿Qué matiza o confirma la RSP respecto a la RS tropical? ¿Cuál de los dos sistemas parece más resonante con los eventos del año?" if rsp else "La RSP no fue calculada para este análisis."}

## ✨ SÍNTESIS Y RECOMENDACIONES
El gran tema vital de este año en una frase poderosa.
Las 3 acciones concretas más importantes que el nativo debería tomar este año.
Lo que debería evitar o posponer.
Una pregunta de reflexión profunda para el consultante.

RECUERDA: Sé específico, usa los datos calculados, integra los sistemas y escribe
como un maestro astrólogo que conoce profundamente al consultante.
""")

    return "\n".join(lines)
