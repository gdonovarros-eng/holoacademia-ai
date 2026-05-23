#!/usr/bin/env python3
"""Genera UNA ficha aplicando el criterio maestro Symbelia con post-composición.

Workflow:
1. IA genera SOLO la imagen anatómica (cuerpo + puntos A/B marcados)
2. Pillow compone banner + sidebar + footer con texto perfecto en español

Uso:
    python3 scripts/ficha_generator/02_generate_one.py "Pineal - Cerebelo"
    python3 scripts/ficha_generator/02_generate_one.py "Vagina - Vagina" --quality high
    python3 scripts/ficha_generator/02_generate_one.py "Recto - Timo"
"""
import argparse, os, sys, json, base64

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from openai import OpenAI
from prompt_template import safe_filename
from pair_analysis import analyze_pair
from composer import compose_from_bytes
from PIL import Image
from io import BytesIO

# ============================================================
# Prompt para SOLO la imagen anatómica (sin texto de sidebar)
# ============================================================
def build_anatomy_prompt(matrix: dict, punto_a: str, punto_b: str) -> str:
    """Prompt minimalista que pide SOLO la imagen anatómica con A/B marcados.
    El texto del sidebar/banner se compone luego con Pillow."""

    variante = matrix["variante_visual"]
    if variante == "bilateral_real":
        regla = ("Marcar el punto en LOS DOS LADOS anatómicos: "
                 "círculo NEGRO con letra 'A' en lado DERECHO anatómico del cuerpo, "
                 "círculo ROJO con letra 'B' en lado IZQUIERDO anatómico del cuerpo.")
    elif variante == "par_doble":
        regla = ("UN SOLO marcador dividido visualmente en mitad NEGRA y mitad ROJA "
                 "(como un imán bicolor) sobre la ubicación del punto.")
    elif variante == "mismo_punto_simple":
        regla = ("UN SOLO marcador en la ubicación del punto, mostrando ambos polos "
                 "(círculo dividido mitad negra mitad roja, o anillo doble negro+rojo).")
    else:
        regla = (f"Círculo NEGRO con letra 'A' sobre la ubicación anatómica de '{punto_a}'. "
                 f"Círculo ROJO con letra 'B' sobre la ubicación anatómica de '{punto_b}'.")

    diagonal_extra = ""
    if matrix["requiere_diagonal"]:
        diagonal_extra = ("\nDIVIDIR el espacio en DOS vistas anatómicas separadas por una "
                          "línea diagonal: arriba-izquierda muestra el Punto A negro, "
                          "abajo-derecha muestra el Punto B rojo.")

    sensible_extra = ""
    if matrix["es_zona_sensible"]:
        sensible_extra = ("\nVestuario médico: el sujeto lleva ROPA DEPORTIVA OSCURA "
                          "(pantalón corto y top deportivo si aplica) cubriendo completamente "
                          "la zona íntima. Imagen estrictamente anatómica/educativa, no erótica, "
                          "estilo manual médico profesional.")

    prompt = f"""Imagen anatómica médica para ficha biomagnética.

CONTENIDO: {matrix['vista_anatomica']}.

MARCADORES:
{regla}{diagonal_extra}

Los círculos marcadores deben ser GRANDES (~60-80px diámetro), claramente visibles,
con la letra A o B en blanco centrada, sombra suave.

ESTILO:
- Modelo anatómico 3D realista estilizado (estilo BodyParts3D / Zygote)
- Fondo blanco/marfil neutro
- Estructuras óseas/musculares semitransparentes visibles bajo la piel si aplica
- Vista clara, didáctica, sin elementos decorativos
- Resolución limpia, sin texto sobreimpreso adicional{sensible_extra}

NO INCLUIR:
- NO incluir ningún sidebar con texto
- NO incluir banner con título
- NO incluir footer ni URL
- NO incluir texto descriptivo de ningún tipo
- NO incluir números numerados de otros puntos
- SOLO el cuerpo anatómico con los marcadores A y B descritos arriba"""

    return prompt

# ============================================================
# DB lookups
# ============================================================
def find_pair_in_db(par_name: str):
    db_path = os.path.join(PROJECT_ROOT, "data", "biomagnetic_pairs_db.json")
    with open(db_path) as f:
        db = json.load(f)
    par_norm = par_name.lower().strip()
    for reg in db["regiones"]:
        for zona in reg.get("zonas", []):
            for bloque in zona.get("bloques", []):
                for p in bloque.get("pares", []):
                    if p.lower().strip() == par_norm:
                        return {"par": p, "region": reg["nombre"],
                                "zona": zona["nombre"], "bloque": bloque["nombre"]}
    return None

def get_classification(region, zona, bloque, par):
    clas_path = os.path.join(PROJECT_ROOT, "data", "pares_clasificacion.json")
    if not os.path.exists(clas_path): return {}
    with open(clas_path) as f:
        data = json.load(f)
    for c in data["clasificaciones"]:
        if (c["region"], c["zona"], c["bloque"], c["par"]) == (region, zona, bloque, par):
            return {
                "tipo": c.get("tipo"),
                "patogeno": c.get("patogeno_canonico") or c.get("patogeno"),
                "enfermedades": c.get("enfermedades_reales"),
                "descripcion": c.get("descripcion"),
                "transmision": c.get("transmision"),
            }
    return {}

# ============================================================
# Anatomical descriptions for sidebar
# ============================================================
ANATOMY_DESC = {
    "pineal": "Centro del cráneo, glándula pineal",
    "cerebelo": "Posterior bajo del cráneo",
    "bulbo": "Bulbo raquídeo, base del cráneo",
    "bulbo raquídeo": "Bulbo raquídeo, base del cráneo",
    "timo": "Tórax central, mediastino superior",
    "esternón": "Hueso central del pecho",
    "hígado": "Cuadrante superior derecho del abdomen",
    "bazo": "Cuadrante superior izquierdo del abdomen",
    "riñón": "Región lumbar dorsal",
    "vagina": "Pelvis íntima femenina",
    "útero": "Pelvis interna femenina",
    "trocánter mayor": "Prominencia ósea lateral del fémur proximal",
    "trocánter menor": "Prominencia ósea medial del fémur proximal",
    "sacro": "Base posterior de la columna",
    "coxis": "Punta inferior de la columna",
    "rodilla": "Articulación tibio-femoral",
    "tibia": "Hueso anterior de la pierna",
    "pleura": "Membrana que envuelve el pulmón",
    "vejiga": "Reservorio urinario pélvico",
    "laringe": "Garganta superior",
    "tiroides": "Cuello frontal, debajo de la laringe",
    "ano": "Recto inferior",
    "recto": "Final del tracto digestivo",
}

def anatomy_desc(point: str) -> str:
    """Devuelve descripción anatómica del punto si la conocemos."""
    p = point.lower().strip()
    # Quitar laterality para lookup
    import re
    p_clean = re.sub(r'\s*\(?(der|izq|derech[oa]|izquierd[oa]|ras)\)?\s*$', '', p)
    return ANATOMY_DESC.get(p_clean.strip(), point)

# ============================================================
# Main
# ============================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("par")
    ap.add_argument("--quality", default="medium", choices=["low","medium","high"])
    ap.add_argument("--size", default="1536x1024",
                    choices=["1024x1024","1024x1536","1536x1024"])
    ap.add_argument("--output-dir",
                    default=os.path.join(PROJECT_ROOT, "data", "fichas_generadas"))
    ap.add_argument("--no-reference", action="store_true")
    ap.add_argument("--save-anatomy", action="store_true",
                    help="Guardar también la imagen IA sin composición")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # 1. Buscar en DB
    info = find_pair_in_db(args.par)
    if not info:
        print(f"⚠ Par '{args.par}' no encontrado en DB. Usando defaults.")
        info = {"par": args.par, "region": "Desconocida", "zona": "Desconocida",
                "bloque": "Desconocido"}

    # 2. Clasificación
    clf = get_classification(info["region"], info["zona"], info["bloque"], info["par"])

    # 3. Matriz
    matrix = analyze_pair(info["par"], info["region"], info["zona"], info["bloque"],
                          tipo=clf.get("tipo"), patogeno=clf.get("patogeno"),
                          enfermedades=clf.get("enfermedades"),
                          descripcion=clf.get("descripcion"))

    print(f"\n📊 MATRIZ DE ANÁLISIS")
    print(f"   Par: {matrix['nombre_par']}")
    print(f"   A=NEGRO: {matrix['punto_a']}  ·  B=ROJO: {matrix['punto_b']}")
    print(f"   Región: {matrix['region']} > {matrix['subregion']} > {matrix['bloque']}")
    print(f"   Tipo: {matrix['tipo']}  ·  Patógeno: {matrix['patogeno'] or '-'}")
    print(f"   Variante: {matrix['variante_visual']}")
    print(f"     → {matrix['variante_descripcion']}")
    if matrix['requiere_diagonal']:
        print(f"   ⚠ Diagonal split requerido")
    if matrix['es_zona_sensible']:
        print(f"   ⚠ Zona sensible: licra/top negro")

    # 4. Prompt SOLO de anatomía (sin texto)
    prompt = build_anatomy_prompt(matrix, matrix["punto_a"], matrix["punto_b"])

    # 5. Generar imagen anatómica con IA
    client = OpenAI()
    print(f"\n🎨 Generando anatomía con IA (size={args.size}, quality={args.quality})...")
    try:
        if not args.no_reference:
            ref_path = os.path.join(PROJECT_ROOT, "data", "fichas_pares",
                                    "000_Timo_Esternon_plantilla_aprobada.png")
            with open(ref_path, "rb") as ref_file:
                response = client.images.edit(
                    model="gpt-image-1", image=ref_file, prompt=prompt,
                    size=args.size, quality=args.quality, n=1,
                )
        else:
            response = client.images.generate(
                model="gpt-image-1", prompt=prompt,
                size=args.size, quality=args.quality, n=1,
            )
        b64 = response.data[0].b64_json
        anatomy_png = base64.b64decode(b64)

        # Save raw anatomy if requested
        if args.save_anatomy:
            raw_path = os.path.join(args.output_dir,
                "anatomia_" + safe_filename(0, info["par"]).replace("000_", ""))
            with open(raw_path, "wb") as f:
                f.write(anatomy_png)
            print(f"   📷 Anatomía IA guardada: {os.path.basename(raw_path)}")

        # 6. Componer con Pillow (texto perfecto)
        print(f"🖼  Componiendo ficha con banner+sidebar+footer...")
        final_png = compose_from_bytes(
            anatomy_png,
            par_name=info["par"],
            tipo=clf.get("tipo"),
            punto_a=matrix["punto_a"],
            punto_a_desc=anatomy_desc(matrix["punto_a"]),
            punto_b=matrix["punto_b"],
            punto_b_desc=anatomy_desc(matrix["punto_b"]),
            region=info["region"],
            descripcion=matrix["texto_clinico"],
        )

        # 7. Save
        fname = safe_filename(0, info["par"]).replace("000_", "test_")
        out_path = os.path.join(args.output_dir, fname)
        with open(out_path, "wb") as f:
            f.write(final_png)

        size_kb = os.path.getsize(out_path) // 1024
        print(f"\n✅ Ficha completa generada:")
        print(f"   {out_path}  ({size_kb} KB)")
        print(f"\n💡 Abre con: open '{out_path}'")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
