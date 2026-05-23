# Generador de Fichas vía OpenAI Images API

Genera las fichas pendientes (≈1,296) usando `gpt-image-1` con la ficha Symbelia
ya aprobada (Timo-Esternón) como referencia visual.

## 1. Setup (una sola vez)

```bash
# 1.1 Crear API key en OpenAI
# → https://platform.openai.com/api-keys

# 1.2 Instalar dependencias
pip3 install --user openai python-dotenv pillow

# 1.3 Crear archivo .env en la raíz del proyecto
echo 'OPENAI_API_KEY=sk-proj-...' >> /Users/highdata/Desktop/New\ Project/.env

# 1.4 Verificar
cd "/Users/highdata/Desktop/New Project"
python3 scripts/ficha_generator/01_verify_setup.py
```

## 2. Test con 1 ficha

```bash
cd "/Users/highdata/Desktop/New Project"
python3 scripts/ficha_generator/02_generate_one.py "Pineal - Cerebelo"
# → Genera data/fichas_generadas/test_Pineal_Cerebelo.png
# Revisa la calidad. Si te gusta, sigue al paso 3.
```

## 3. Generación en lote (toda la DB)

```bash
cd "/Users/highdata/Desktop/New Project"
python3 scripts/ficha_generator/03_generate_batch.py --limit 10
# → genera 10 primero. Si OK, quita --limit para correr todo.
```

El script:
- ✅ Salta las que ya existen (resume-safe)
- ✅ Reintenta con backoff si hay errores de red
- ✅ Respeta rate limits (≤50 imágenes/min en gpt-image-1)
- ✅ Guarda checkpoint en `data/fichas_generadas/_progress.json`
- ✅ Puede pausarse con Ctrl+C y continuar después

## 4. Costos estimados

| Calidad | Tamaño | $/imagen | 1,296 imágenes |
|---------|--------|----------|----------------|
| low     | 1024×1024 | $0.011 | **$14.26** |
| medium  | 1024×1024 | $0.042 | **$54.43** |
| high    | 1024×1024 | $0.167 | **$216.43** |
| high    | 1536×1024 | $0.250 | **$324.00** |

Recomendado: empezar con **medium 1024×1024** (~$55 total).

## 5. Rate limits

`gpt-image-1` tier 1: ~50 requests/min. A 1.5s entre llamadas → 40 RPM.
1,296 imágenes ÷ 40 RPM = **~32 minutos** de ejecución.

## 6. Estructura de archivos

```
scripts/ficha_generator/
├── README.md                  ← este archivo
├── 01_verify_setup.py         ← test API key + dependencias
├── 02_generate_one.py         ← genera 1 ficha (test)
├── 03_generate_batch.py       ← batch completo con checkpointing
└── prompt_template.py         ← prompt unificado (editar para ajustar estilo)

data/
├── fichas_pares/              ← 107 fichas Symbelia APROBADAS (no tocar)
├── fichas_generadas/          ← salida nueva (1,296 pendientes)
│   ├── _progress.json         ← checkpoint
│   ├── _failures.log          ← log de fallos
│   └── NNN_Par_Generado.png
└── fichas_mapping.json        ← agregar generadas tras revisión
```

## 7. Iteración: ajustar prompts

Si las fichas no salen como quieres:
1. Edita `prompt_template.py`
2. Regenera 5 de muestra con `02_generate_one.py`
3. Cuando te guste, corre `03_generate_batch.py` completo

Variables del prompt que puedes ajustar:
- `STYLE_DESCRIPTION` — estética general
- `LAYOUT_DESCRIPTION` — disposición de elementos
- `TIPO_HINT_MAP` — pistas por tipo (Virus, Bacteria, etc.)
