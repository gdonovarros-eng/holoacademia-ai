#!/usr/bin/env python3
"""Verifica setup: dependencias, API key, acceso a modelo gpt-image-1."""
import os, sys

def main():
    print("🔍 Verificando setup para generación de fichas...\n")

    # 1. Dependencias
    print("1. Dependencias:")
    try:
        import openai
        print(f"   ✓ openai SDK {openai.__version__}")
    except ImportError:
        print("   ❌ openai SDK no instalado. Run: pip3 install --user openai")
        return 1
    try:
        from dotenv import load_dotenv
        print("   ✓ python-dotenv")
    except ImportError:
        print("   ❌ python-dotenv no instalado. Run: pip3 install --user python-dotenv")
        return 1
    try:
        from PIL import Image
        print("   ✓ Pillow")
    except ImportError:
        print("   ❌ Pillow no instalado. Run: pip3 install --user pillow")
        return 1

    # 2. API key
    print("\n2. API key:")
    # Buscar .env en raíz del proyecto
    HERE = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(HERE, "..", ".."))
    env_path = os.path.join(project_root, ".env")
    load_dotenv(env_path)

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print(f"   ❌ OPENAI_API_KEY no encontrada.")
        print(f"      Crea el archivo: {env_path}")
        print(f"      con contenido:    OPENAI_API_KEY=sk-proj-...")
        return 1
    masked = key[:7] + "..." + key[-4:]
    print(f"   ✓ OPENAI_API_KEY: {masked}")

    # 3. Cliente OpenAI + ping ligero
    print("\n3. Conexión OpenAI:")
    from openai import OpenAI
    client = OpenAI(api_key=key)
    try:
        # Llamar a /v1/models para verificar credenciales (gratis, sin costo)
        models = client.models.list()
        image_models = [m.id for m in models.data if "image" in m.id.lower()]
        print(f"   ✓ Autenticación OK")
        if "gpt-image-1" in image_models:
            print(f"   ✓ Modelo 'gpt-image-1' disponible en tu cuenta")
        elif "dall-e-3" in image_models:
            print(f"   ⚠ 'gpt-image-1' no detectado, pero 'dall-e-3' sí")
            print(f"     Verifica acceso a gpt-image-1 en tu organización OpenAI.")
        else:
            print(f"   ⚠ No se detectaron modelos de imagen. Modelos disponibles:")
            for m in models.data[:5]:
                print(f"      - {m.id}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 1

    # 4. Archivos del proyecto
    print("\n4. Archivos del proyecto:")
    db_file = os.path.join(project_root, "data", "biomagnetic_pairs_db.json")
    fichas_map = os.path.join(project_root, "data", "fichas_mapping.json")
    ref_ficha = os.path.join(project_root, "data", "fichas_pares",
                             "000_Timo_Esternon_plantilla_aprobada.png")

    for label, path in [("DB pares", db_file),
                         ("mapping fichas", fichas_map),
                         ("ficha referencia", ref_ficha)]:
        if os.path.exists(path):
            size_kb = os.path.getsize(path) // 1024
            print(f"   ✓ {label:20s}: {path} ({size_kb} KB)")
        else:
            print(f"   ❌ {label:20s}: NO ENCONTRADO en {path}")

    print("\n✅ Setup verificado. Ahora puedes correr:")
    print("    python3 scripts/ficha_generator/02_generate_one.py \"Pineal - Cerebelo\"")
    return 0

if __name__ == "__main__":
    sys.exit(main())
