"""MASTER PROMPT Symbelia — versión cerrada del usuario.

Reglas globales:
- Polaridad fija: Punto A = NEGRO = Norte, Punto B = ROJO = Sur (siempre)
- Tamaño: 1448 × 1086 px horizontal
- Layout fijo: encabezado azul / panel anatómico izq / panel info der / footer
- Nunca rediseñar la plantilla, nunca cambiar estilo
- Footer: "Vista de [REGIÓN] · www.symbelia.com"
"""
from __future__ import annotations
from pair_analysis import analyze_pair


def build_prompt(par_name: str, region: str, zona: str, bloque: str,
                 tipo: str = None, patogeno: str = None,
                 enfermedades: str = None, descripcion: str = None,
                 punto_a: str = None, punto_b: str = None) -> str:
    """Construye el MASTER PROMPT con datos del par + análisis automático."""

    matrix = analyze_pair(par_name, region, zona, bloque,
                          tipo=tipo, patogeno=patogeno,
                          enfermedades=enfermedades, descripcion=descripcion)

    # Override sides if explicitly provided
    if punto_a is None:
        punto_a = matrix["punto_a"]
    if punto_b is None:
        punto_b = matrix["punto_b"]

    # Bloque condicional según la variante visual
    variante = matrix["variante_visual"]
    if variante == "bilateral_real":
        regla_critica = """REGLA APLICADA: BILATERAL REAL.
Mostrar dos marcadores en lados anatómicos opuestos:
- Punto A NEGRO sobre el lado DERECHO anatómico del cuerpo
- Punto B ROJO sobre el lado IZQUIERDO anatómico del cuerpo
No duplicar como si fueran puntos distintos. Ambos son el mismo punto bilateral."""
    elif variante == "par_doble":
        regla_critica = """REGLA APLICADA: PAR DOBLE.
Mostrar UN SOLO marcador en la ubicación del punto, dividido visualmente:
- Mitad izquierda del círculo: NEGRO
- Mitad derecha del círculo: ROJO
NO duplicar el marcador. Es un único imán/punto con polaridad dividida."""
    elif variante == "mismo_punto_simple":
        regla_critica = """REGLA APLICADA: MISMO PUNTO REPETIDO (NO bilateral).
Mostrar UN SOLO marcador en la ubicación anatómica del punto:
- Marcador combinado: mitad negra mitad roja, o anillo doble (negro exterior + rojo interior)
NO duplicar la marca. Es el mismo punto repetido por la fuente, no dos puntos distintos."""
    else:  # normal
        regla_critica = """REGLA APLICADA: PAR NORMAL (dos puntos anatómicos distintos).
- Punto A NEGRO sobre la ubicación anatómica de "{punto_a}"
- Punto B ROJO sobre la ubicación anatómica de "{punto_b}"
Cada marcador en su propia ubicación correcta.""".format(punto_a=punto_a, punto_b=punto_b)

    # Diagonal split si aplica
    if matrix["requiere_diagonal"]:
        regla_vista = """REGLA APLICADA: DIVISIÓN DIAGONAL del panel anatómico.
Los dos puntos están en regiones anatómicamente distantes. Dividir el panel izquierdo con una línea diagonal:
- Lado superior-izquierdo: vista anatómica del Punto A (NEGRO)
- Lado inferior-derecho: vista anatómica del Punto B (ROJO)
Ambas vistas dentro del MISMO panel anatómico izquierdo (no cambiar el layout general)."""
    else:
        regla_vista = f"VISTA ÚNICA: {matrix['vista_anatomica']}."

    # Cobertura sensible
    cobertura_extra = ""
    if matrix["es_zona_sensible"]:
        cobertura_extra = """
ZONA SENSIBLE - COBERTURA OBLIGATORIA:
- Licra negra ajustada en la parte baja (cubriendo pelvis/genitales)
- Top negro ajustado si el cuerpo expone tórax femenino
- SIN desnudez, SIN genitales visibles
- Estilo médico sobrio, profesional, no erótico"""

    # ===== MASTER PROMPT (verbatim del usuario) =====
    prompt = f"""PROMPT MAESTRO SYMBELIA

Genera una ficha anatómica del atlas Symbelia usando EXACTAMENTE el mismo estilo visual de las imágenes aprobadas del atlas. No rediseñes la plantilla. No reinterpretar el layout. No crear una infografía moderna nueva.

══════ FORMATO FIJO ══════
- Tamaño exacto: 1448 x 1086 px (horizontal)
- Encabezado azul oscuro (#1a3a5c) con título en blanco, mayúsculas, sans-serif bold
- Panel anatómico grande a la IZQUIERDA (~60% del ancho)
- Panel derecho fijo (~38% del ancho) en blanco con borde sutil
- Footer inferior gris pequeño

══════ PANEL DERECHO (orden exacto) ══════
1. TIPO
2. PUNTO A (Norte)
3. PUNTO B (Sur)
4. REGIÓN
5. DESCRIPCIÓN

══════ FOOTER ══════
"Vista de {matrix['region']} · www.symbelia.com"

══════ REGLAS DE POLARIDAD ══════
- Punto A = NEGRO = Norte (PRIMER punto del par)
- Punto B = ROJO = Sur (SEGUNDO punto del par)
- NUNCA invertir colores

══════ REGLA CRÍTICA ══════
{regla_critica}

══════ REGLA DE VISTA ══════
{regla_vista}
{cobertura_extra}

══════ CONTENIDO ESPECÍFICO DE ESTA FICHA ══════
Título (encabezado): "{par_name.upper()}"

TIPO: {matrix['tipo']}

PUNTO A (Norte) ● negro:
  Nombre: {punto_a}
  Ubicación: [descripción anatómica breve, 1 línea]

PUNTO B (Sur) ● rojo:
  Nombre: {punto_b}
  Ubicación: [descripción anatómica breve, 1 línea]

REGIÓN: {matrix['region']}

DESCRIPCIÓN: {matrix['texto_clinico']}

══════ PROHIBIDO ══════
- Cambiar el layout
- Cambiar los colores del sistema
- Agregar logos nuevos
- Agregar numeración decorativa
- Usar otra plantilla
- Agregar elementos modernos ajenos al atlas
- Cambiar la tipografía general del estilo aprobado
- Inventar anatomía
- Repetir imanes cuando no corresponda
- Texto inventado o palabras inexistentes en español

══════ REFERENCIAS ══════
Usar como ancla principal la plantilla aprobada del atlas (Timo-Esternón adjunta como referencia) y las referencias anatómicas aprobadas más parecidas a la región del par.
Fuente principal del contenido: {matrix['fuente_principal']}
Fuente secundaria: {matrix['fuente_secundaria']}

══════ CHECKLIST DE SALIDA ══════
La imagen final debe cumplir:
[1] Tamaño 1448x1086 px o ratio equivalente (16:12)
[2] Layout idéntico al template Timo-Esternón
[3] Título correcto en mayúsculas
[4] Punto A NEGRO en posición anatómica de "{punto_a}"
[5] Punto B ROJO en posición anatómica de "{punto_b}"
[6] Sidebar con TIPO, PUNTO A, PUNTO B, REGIÓN, DESCRIPCIÓN en ese orden
[7] Si zona sensible: licra/top negro, sin desnudez
[8] Footer: "Vista de {matrix['region']} · www.symbelia.com"
[9] Texto correcto en español (sin palabras inventadas)
[10] Si bilateral/doble/diagonal: aplicar la regla específica arriba
"""

    return prompt


# ============================================================
# Utilidad: generar nombre de archivo según convención
# ============================================================
def safe_filename(idx: int, par_name: str) -> str:
    """Convención: NNN_PuntoA_PuntoB.png (sin acentos, espacios=_)"""
    import re
    import unicodedata
    base = par_name
    # Strip accents
    base = ''.join(c for c in unicodedata.normalize("NFKD", base)
                   if not unicodedata.combining(c))
    # Replace separators with _
    base = re.sub(r'\s*[-–—]\s*', '_', base)
    # Replace non-alphanumeric with _
    base = re.sub(r'[^A-Za-z0-9]+', '_', base)
    base = base.strip('_')[:80]
    return f"{idx:03d}_{base}.png"
