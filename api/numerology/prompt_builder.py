"""
Construcción del prompt para el análisis numerológico.
Ensambla todos los datos del numeroscopio en un prompt estructurado para el LLM.
"""
from __future__ import annotations
import datetime

# ─── Significados de cada número ──────────────────────────────────────────────

_SIGNIFICADOS: dict[int, dict] = {
    1: {
        "nombre": "El Líder Inconsciente",
        "palabras": "originalidad · creatividad · autenticidad · individualismo · pionero",
        "positivo": "Auténtico, original, creativo, bondadoso desde el corazón. Tiene visión y capacidad de innovar. La gente lo busca por consejo aunque él no busca liderar.",
        "negativo": "Vanidoso, disperso, conecta solo cuando ve beneficio. En exceso: arrogante, terco, aislado.",
        "mision": "Desarrollar la autenticidad y la individualidad. Ser pionero en algo nuevo.",
        "vocacion": "Innovación, diseño, emprendimiento, arte, exploración de nuevos territorios.",
    },
    2: {
        "nombre": "El Diplomático",
        "palabras": "cooperación · sensibilidad · intuición · paciencia · armonía",
        "positivo": "Empático, cooperador, muy intuitivo. Excelente mediador. Siente lo que otros no ven. Leal y amoroso.",
        "negativo": "Dependiente, inseguro, manipulador pasivo. Puede ser excesivamente sensible hasta la parálisis.",
        "mision": "Aprender a relacionarse sanamente. Ser puente entre personas y situaciones.",
        "vocacion": "Relaciones públicas, terapia, mediación, música, trabajo en equipo.",
    },
    3: {
        "nombre": "El Creativo",
        "palabras": "expresión · alegría · comunicación · arte · optimismo",
        "positivo": "Alegre, expresivo, artístico, magnético. Don natural para comunicar y entretener. Muy sociable.",
        "negativo": "Disperso, superficial, chismoso, irresponsable. Puede usar las palabras para herir.",
        "mision": "Expresarse creativamente y alegrar el mundo a través del arte, la comunicación o el humor.",
        "vocacion": "Arte, escritura, actuación, comunicación, enseñanza creativa, entretenimiento.",
    },
    4: {
        "nombre": "El Constructor",
        "palabras": "disciplina · trabajo · orden · estabilidad · base sólida",
        "positivo": "Trabajador, organizado, confiable, práctico. Construye sobre bases sólidas. Disciplinado y constante.",
        "negativo": "Rígido, terco, excesivamente controlador. Puede ser workaholic o limitarse por el miedo.",
        "mision": "Construir estructuras sólidas: familia, empresa, conocimiento. Ser el pilar que otros necesitan.",
        "vocacion": "Arquitectura, ingeniería, administración, finanzas, construcción, medicina.",
    },
    5: {
        "nombre": "El Aventurero",
        "palabras": "libertad · cambio · adaptabilidad · experiencia · sensualidad",
        "positivo": "Versátil, aventurero, adaptable, magnético. Aprende de la experiencia directa. Ama la libertad y los viajes.",
        "negativo": "Inconstante, disperso, adicto a las sensaciones. Miedo al compromiso. Irresponsable.",
        "mision": "Vivir plenamente la experiencia humana y ser agente de cambio y transformación.",
        "vocacion": "Viajes, ventas, periodismo, publicidad, deportes, exploración, comunicación.",
    },
    6: {
        "nombre": "El Místico",
        "palabras": "verbo · familia · amor · responsabilidad · pureza",
        "positivo": "Palabra poderosa. Hogareño, responsable, excelente maestro. Talento para lo místico y el ocultismo.",
        "negativo": "Chismoso, mentiroso, vengativo cuando está herido. Controlador con la familia.",
        "mision": "Purificar la palabra. Conectar con lo místico y compartirlo. Ser maestro o guía espiritual.",
        "vocacion": "Artes místicas, enseñanza, consejería, trabajo con familia, sanación.",
    },
    7: {
        "nombre": "El Sabio",
        "palabras": "análisis · espiritualidad · conocimiento · introspección · perfección",
        "positivo": "Analítico, profundo, espiritual, estudioso. Busca la verdad oculta. Intuitivo y líder bondadoso.",
        "negativo": "Frío, arrogante, hermético, desconectado de lo material. Puede caer en el cinismo.",
        "mision": "Buscar la verdad y compartirla. Integrar lo espiritual con lo práctico.",
        "vocacion": "Investigación, filosofía, ciencias ocultas, espiritualidad, tecnología, psicología.",
    },
    8: {
        "nombre": "El Ejecutivo",
        "palabras": "poder · dinero · justicia · perfeccionismo · equilibrio",
        "positivo": "Perfeccionista, ejecutivo, poderoso en los negocios. Busca equilibrar la balanza. Muy trabajador.",
        "negativo": "Workaholic, dominante, materialista, excesivamente rígido. Puede caer en el autoritarismo.",
        "mision": "Generar abundancia material y distribuirla con justicia. Equilibrar lo material y lo espiritual.",
        "vocacion": "Negocios, finanzas, política, derecho, medicina, administración de alto nivel.",
    },
    9: {
        "nombre": "El Humanitario",
        "palabras": "compasión · universalidad · sabiduría · conclusión · entrega",
        "positivo": "Compasivo, universal, sabio. Número de mayor espiritualidad práctica. Perspectiva global. Maestro natural.",
        "negativo": "Mártir, se pierde en el ego espiritual. Puede ser impráctico, desapegado de lo cotidiano.",
        "mision": "Servir a la humanidad. Integrar todo lo aprendido y transmitirlo con amor universal.",
        "vocacion": "Humanitarismo, sanación, arte, enseñanza, espiritualidad, trabajo social.",
    },
    11: {
        "nombre": "Número Maestro — El Iluminador",
        "palabras": "intuición elevada · espiritualidad personal · inspiración · sensibilidad extrema",
        "positivo": "Intuitivo en niveles extraordinarios. Profundamente espiritual. Inspira a otros sin proponérselo.",
        "negativo": "Sensibilidad al punto del agotamiento. Nerviosismo y ansiedad altos. Idealismo sin aterrizaje.",
        "mision": "Ser canal de luz espiritual. Elevar la conciencia de quienes lo rodean.",
        "vocacion": "Espiritualidad, psicología, arte místico, sanación energética, inspiración colectiva.",
    },
    22: {
        "nombre": "Número Maestro — El Constructor Maestro",
        "palabras": "visión práctica · construcción · trascendencia · legado",
        "positivo": "Visión del 11 aterrizada como el 4. Constructor de sistemas, instituciones, legados.",
        "negativo": "El peso de la misión puede aplastarlo. Sin trabajo personal, cae en la mediocridad del 4.",
        "mision": "Materializar visiones espirituales en estructuras concretas que beneficien a muchos.",
        "vocacion": "Liderazgo institucional, arquitectura de sistemas, construcción de movimientos espirituales.",
    },
    33: {
        "nombre": "Número Maestro — El Maestro de Maestros",
        "palabras": "amor incondicional · enseñanza · sacrificio · compasión máxima",
        "positivo": "El más raro y elevado. Amor incondicional y capacidad de transformar comunidades enteras.",
        "negativo": "Sin altura suficiente, cae en el 6 básico. Riesgo de martirio o control 'por el bien de todos'.",
        "mision": "Enseñar con amor incondicional. Ser maestro de maestros.",
        "vocacion": "Enseñanza espiritual profunda, sanación, arte sagrado, servicio incondicional.",
    },
}

_PLANO_DESC = {
    "mental":     "Pensamiento, intuición mental, razonamiento abstracto (letras 1 y 8)",
    "fisico":     "Acción, materia, sensorialidad, mundo tangible (letras 4 y 5)",
    "emocional":  "Sentimiento, relaciones, arte, expresión (letras 2, 3 y 6)",
    "espiritual": "Búsqueda interior, compasión, trascendencia (letras 7 y 9)",
}

_AÑO_PERS_DESC = {
    1: "Año de inicios, nuevos proyectos, siembra. Ideal para lanzar, comenzar, ser pionero.",
    2: "Año de cooperación, paciencia, relaciones. Cultivar vínculos, esperar y diplomacia.",
    3: "Año de expresión, creatividad, alegría. Comunicar, crear, celebrar la vida.",
    4: "Año de trabajo, orden y construcción. Sentar bases, organizarse, disciplina.",
    5: "Año de cambio, libertad y movimiento. Adaptarse, viajar, transformar.",
    6: "Año de familia, responsabilidad y amor. Compromisos, hogar, servicio.",
    7: "Año de introspección, análisis y espiritualidad. Retiro, estudio interior.",
    8: "Año de poder, abundancia y cosecha. Negocios, resultados, reconocimiento.",
    9: "Año de cierre, soltar y conclusiones. Finalizar ciclos, perdonar, liberarse.",
    11: "Año maestro de intuición e iluminación. Revelaciones espirituales importantes.",
    22: "Año maestro de construcción y legado. Materializar grandes visiones.",
}


def _sig(n: int) -> dict:
    return _SIGNIFICADOS.get(n, _SIGNIFICADOS.get(n % 9 or 9, _SIGNIFICADOS[1]))


def _nombre_num(n: int) -> str:
    return _sig(n)["nombre"]


def _star(n: int) -> str:
    """Añade ✦ a números maestros para destacarlos."""
    return f"{n} ✦" if n in (11, 22, 33) else str(n)


# ─── Construcción del prompt ──────────────────────────────────────────────────

def build_numerology_prompt(
    nombre: str,
    datos: dict,
    profundidad: str = "completo",
) -> str:
    nb   = datos["nombre"]
    na   = datos["nacimiento"]
    cp   = datos["ciclos_personales"]
    pd_p = datos["pinaculos"]
    pd_d = datos["desafios"]
    ciclos = datos["ciclos"]
    pc   = datos["potencias_carencias"]
    deudas = datos["deudas_karmicas"]
    planos = nb["planos"]
    lat  = datos["vibracion_latente"]
    her_pat = datos.get("herencia_paterna")
    her_mat = datos.get("herencia_materna")

    expr  = nb["expresion"]
    imp_a = nb["impulso"]
    imp_r = nb["impresion"]
    alma  = na["alma"]
    karma = na["karma"]
    mis   = na["mision"]
    dia, mes, anio = na["dia"], na["mes"], na["anio"]

    meses_es = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    fecha_str = f"{dia} de {meses_es[mes] if 1 <= mes <= 12 else mes} de {anio}"

    hoy = datetime.date.today()
    edad = hoy.year - anio

    # ── Tabla de letras ────────────────────────────────────────────────────────
    voc_str  = " + ".join(f"{l['letra']}({l['valor']})" for l in nb["letras"] if l["es_vocal"]  and l["valor"])
    con_str  = " + ".join(f"{l['letra']}({l['valor']})" for l in nb["letras"] if not l["es_vocal"] and l["valor"])
    todo_str = " + ".join(f"{l['letra']}({l['valor']})" for l in nb["letras"] if l["valor"])

    # ── Ciclo actual ────────────────────────────────────────────────────────────
    ciclo_actual = pin_actual = des_actual = None
    for i, c in enumerate(ciclos):
        hasta = c["hasta"] if c["hasta"] is not None else 9999
        if c["desde"] <= edad <= hasta:
            ciclo_actual = c
            pin_actual   = pd_p[i]
            des_actual   = pd_d[i]
            break

    # ── Planos ────────────────────────────────────────────────────────────────
    planos_txt = "\n".join(
        f"  {k.capitalize():12s}: {v['cantidad']} letras — {v['nivel']}  ({_PLANO_DESC[k]})"
        for k, v in planos.items()
    )

    # ── Deudas kármicas ───────────────────────────────────────────────────────
    deudas_txt = ""
    if deudas:
        deudas_txt = "\n⚠️  DEUDAS KÁRMICAS DETECTADAS:\n"
        for dk in deudas:
            deudas_txt += f"  {dk['codigo']} en {dk['fuente']}: {dk['tema']}\n"

    # ── Herencias ─────────────────────────────────────────────────────────────
    her_txt = ""
    if her_pat:
        her_txt += f"  Herencia Paterna ({her_pat['apellido']}): {_star(her_pat['valor'])} — {_nombre_num(her_pat['valor'])}\n"
    if her_mat:
        her_txt += f"  Herencia Materna ({her_mat['apellido']}): {_star(her_mat['valor'])} — {_nombre_num(her_mat['valor'])}\n"

    # ── Año personal y descripción ────────────────────────────────────────────
    ap     = cp["año_personal"]
    au     = cp["año_universal"]
    mp     = cp["mes_personal"]
    dp_num = cp["dia_personal"]
    ap_desc = _AÑO_PERS_DESC.get(ap, "")

    # ── Potencias y carencias ──────────────────────────────────────────────────
    pot_str = ", ".join(f"{p} ({_nombre_num(p)})" for p in pc["potencias"]) or "Ninguna"
    car_str = ", ".join(str(c) for c in pc["carencias"]) or "Ninguna"

    # ══════════════════════════════════════════════════════════════════════════
    # BLOQUE DE DATOS
    # ══════════════════════════════════════════════════════════════════════════
    datos_bloque = f"""Eres numerólogo experto en Numerhología (Alejandro González Lavín) y numerología pitagórica clásica.
Analiza el numeroscopio de {nombre} de forma profunda, empática y orientada al autoconocimiento y la sanación holística.

══════════════════════════════════════════════════════════════════
DATOS DE {nombre.upper()}
Fecha de nacimiento: {fecha_str}  |  Edad: {edad} años
══════════════════════════════════════════════════════════════════

▸ TABLA PITAGÓRICA DEL NOMBRE
  Vocales   (Impulso):    {voc_str or '—'} = {nb["impulso_suma"]} → {_star(imp_a)}
  Consonantes (Impresión): {con_str or '—'} = {nb["impresion_suma"]} → {_star(imp_r)}
  Todas las letras (Expresión): {todo_str} = {nb["expresion_suma"]} → {_star(expr)}
  Esencia del primer nombre: {_star(nb["esencia"])}
  Influencia Locomotora (1ª letra): {nb["locomotora"]}

▸ PENTAGRAMA DEL NACIMIENTO
  🌟 Alma    (día {dia}):           {_star(alma)}  — {_nombre_num(alma)}
  ♾️  Karma   (mes {mes}):          {_star(karma)} — {_nombre_num(karma)}
  🎯 Misión  (fecha completa):      {_star(mis)}   — {_nombre_num(mis)}

▸ PENTAGRAMA DEL NOMBRE
  💫 Impulso  (vocales):            {_star(imp_a)} — {_nombre_num(imp_a)}
  🎭 Impresión (consonantes):       {_star(imp_r)} — {_nombre_num(imp_r)}
  ✨ Expresión (todas las letras):  {_star(expr)}  — {_nombre_num(expr)}

▸ VIBRACIÓN LATENTE / NÚMERO DE MADUREZ
  {_star(lat)} — {_nombre_num(lat)}  (Expresión + Misión; se activa ~35-45 años)

{her_txt if her_txt else ''}
▸ PLANOS DE EXPRESIÓN DEL NOMBRE
{planos_txt}

▸ PINÁCULOS Y DESAFÍOS
  P1: {_star(pd_p[0])} ({_nombre_num(pd_p[0])})  |  D1: {pd_d[0]}
  P2: {_star(pd_p[1])} ({_nombre_num(pd_p[1])})  |  D2: {pd_d[1]}
  P3: {_star(pd_p[2])} ({_nombre_num(pd_p[2])})  |  D3: {pd_d[2]}
  P4: {_star(pd_p[3])} ({_nombre_num(pd_p[3])})  |  D4: {pd_d[3]}

▸ CICLOS DE VIDA
  Ciclo 1 (0-{ciclos[0]["hasta"]}): Pináculo {_star(pd_p[0])}, Desafío {pd_d[0]} — {ciclos[0]["descripcion"]}
  Ciclo 2 ({ciclos[1]["desde"]}-{ciclos[1]["hasta"]}): Pináculo {_star(pd_p[1])}, Desafío {pd_d[1]} — {ciclos[1]["descripcion"]}
  Ciclo 3 ({ciclos[2]["desde"]}-{ciclos[2]["hasta"]}): Pináculo {_star(pd_p[2])}, Desafío {pd_d[2]} — {ciclos[2]["descripcion"]}
  Ciclo 4 ({ciclos[3]["desde"]}+):   Pináculo {_star(pd_p[3])}, Desafío {pd_d[3]} — {ciclos[3]["descripcion"]}
{"  → Ciclo activo ahora: Ciclo " + str(ciclo_actual["ciclo"]) + " | Pináculo " + _star(pin_actual) + " | Desafío " + str(des_actual) if ciclo_actual else ""}

▸ CICLOS PERSONALES (fecha de consulta: {cp["fecha_consulta"]})
  Año Universal {cp["año_consultado"]}: {au}  (energía colectiva del año)
  Año Personal:  {_star(ap)} — {ap_desc}
  Mes Personal:  {_star(mp)} ({meses_es[cp["mes_consultado"]] if cp["mes_consultado"] <= 12 else cp["mes_consultado"]})
  Día Personal:  {dp_num} (hoy, {hoy.strftime("%d/%m/%Y")})

▸ POTENCIAS Y CARENCIAS
  Potencias (≥3 apariciones): {pot_str}
  Carencias (ausentes):       {car_str}
{deudas_txt}
══════════════════════════════════════════════════════════════════
REFERENCIA DE NÚMEROS:"""

    # Significados de los números presentes
    nums_presentes = set([expr, imp_a, imp_r, alma, karma, mis, lat,
                          nb["esencia"], nb["locomotora"]] + pd_p)
    for n in sorted(nums_presentes):
        if n in _SIGNIFICADOS:
            s = _SIGNIFICADOS[n]
            datos_bloque += (
                f"\n  [{_star(n)}] {s['nombre']}\n"
                f"  Palabras: {s['palabras']}\n"
                f"  Positivo: {s['positivo']}\n"
                f"  Negativo: {s['negativo']}\n"
                f"  Misión: {s['mision']}"
            )

    # ══════════════════════════════════════════════════════════════════════════
    # INSTRUCCIONES DEL ANÁLISIS
    # ══════════════════════════════════════════════════════════════════════════
    if profundidad == "basico":
        instrucciones = f"""

══════════════════════════════════════════════════════════════════
INSTRUCCIONES (nivel básico):

## Misión de Vida — el {_star(mis)}
Propósito central. Por qué vino a esta vida. Qué viene a lograr.

## Expresión e Impulso — {_star(expr)} y {_star(imp_a)}
Talentos naturales y motivación profunda.

## Alma y Karma — {_star(alma)} y {_star(karma)}
Personalidad privada vs. personalidad pública.

## Momento actual
Ciclo de vida activo y Año Personal {_star(ap)}: qué energía rige este período.

## Síntesis terapéutica
3-4 frases integradoras. Tono empático y orientado al crecimiento. Solo en español."""
    else:
        instrucciones = f"""

══════════════════════════════════════════════════════════════════
INSTRUCCIONES (análisis completo):

Redacta un análisis numerológico profundo de {nombre}. Usa encabezados markdown ##.

## 1. Misión de Vida — el {_star(mis)}: {_nombre_num(mis)}
Propósito central de esta encarnación. Por qué eligió nacer en esta fecha. Qué viene a lograr, aprender y dejar como legado.

## 2. Pentagrama del Nombre
### Expresión — {_star(expr)}: {_nombre_num(expr)}
Talentos naturales, manifestación en el mundo, vocación principal.
### Impulso — {_star(imp_a)}: {_nombre_num(imp_a)}
Motivación más íntima. Lo que lo mueve cuando nadie lo ve.
### Impresión — {_star(imp_r)}: {_nombre_num(imp_r)}
Primera impresión que genera. Cómo lo perciben los demás al conocerlo.
### Esencia del nombre e Influencia Locomotora
Esencia: {_star(nb["esencia"])} — vibración del primer nombre de pila.
Locomotora (1ª letra): {nb["locomotora"]} — impulso instintivo primario.

## 3. Pentagrama del Nacimiento
### Alma — {_star(alma)}: {_nombre_num(alma)}
Personalidad privada. Cómo es cuando está solo o en íntima confianza.
### Karma — {_star(karma)}: {_nombre_num(karma)}
Personalidad pública. Rol que adopta en sistemas (trabajo, familia, social).

## 4. Vibración Latente / Número de Madurez — {_star(lat)}
Potencial que emerge cuando la persona integra su nombre y su fecha (~35-45 años).
Qué nueva dimensión de sí mismo puede despertar.

## 5. Planos de Expresión
Con base en los planos {" / ".join(f"{k}: {v['cantidad']}" for k, v in planos.items())},
analiza desde qué plano opera principalmente {nombre}: ¿es más mental, físico, emocional o espiritual?
¿Hay desequilibrios? ¿Qué implica para su salud, relaciones y vocación?

{f"## 6. Herencias{chr(10)}Analiza brevemente las herencias familiar encontradas en el cuadro.{chr(10)}" if her_txt else ""}
## {"7" if her_txt else "6"}. Ciclo Actual y Pináculo Activo
{nombre} tiene {edad} años y está en el Ciclo {ciclo_actual["ciclo"] if ciclo_actual else "?"} de su vida.
Pináculo activo: {_star(pin_actual) if pin_actual else "?"} — {_nombre_num(pin_actual) if pin_actual else "?"}.
Desafío activo: {des_actual}.
¿Qué oportunidad específica trae este pináculo? ¿Qué aprendizaje exige el desafío?

## {"8" if her_txt else "7"}. Pináculos a lo Largo de la Vida
Describe brevemente cada pináculo y su momento:
- P1 ({_star(pd_p[0])}): 0-{ciclos[0]["hasta"]} años
- P2 ({_star(pd_p[1])}): {ciclos[1]["desde"]}-{ciclos[1]["hasta"]} años
- P3 ({_star(pd_p[2])}): {ciclos[2]["desde"]}-{ciclos[2]["hasta"]} años
- P4 ({_star(pd_p[3])}): {ciclos[3]["desde"]}+ años

## {"9" if her_txt else "8"}. Ciclos Personales — Ahora ({cp["fecha_consulta"]})
Año Universal {cp["año_consultado"]}: {au} — {_AÑO_PERS_DESC.get(au, "")}
Año Personal {nombre}: {_star(ap)} — {ap_desc}
Mes Personal: {_star(mp)} — ¿qué energía específica rige este mes?
Día Personal hoy: {dp_num} — tono del día presente.
Integra todo: ¿qué mensaje tiene el cosmos para {nombre} en este momento concreto?

## {"10" if her_txt else "9"}. Deudas Kármicas
{"Analiza las deudas kármicas encontradas: " + ", ".join(dk["codigo"] + " (" + dk["tema"] + ")" for dk in deudas) + ". ¿Cómo se manifiestan en la vida de " + nombre + "? ¿Qué aprendizaje kármico traen?" if deudas else "No se detectaron deudas kármicas directas en este cuadro. Menciona brevemente qué significa esto para la persona."}

## {"11" if her_txt else "10"}. Potencias y Carencias
Potencias ({", ".join(str(p) for p in pc["potencias"]) or "ninguna"}): energías en exceso, posibles puntos ciegos.
Carencias ({", ".join(str(c) for c in pc["carencias"]) or "ninguna"}): energías ausentes y cómo cultivarlas.

## {"12" if her_txt else "11"}. Síntesis Terapéutica
4-5 frases que integren todo: quién es {nombre} en esencia, qué vino a aprender, qué talentos tiene para lograrlo, y qué le sugeriría el terapeuta para este momento de su vida.

Tono: empático, profundo, orientado al crecimiento y la autocompasión. Solo en español."""

    return datos_bloque + instrucciones
