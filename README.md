# HoloAcademia AI Backend

Backend externo para consultar la biblioteca procesada de cursos y responder como un asistente natural.

## Dos modos de conocimiento

Este proyecto ahora tiene dos capas distintas:

- `knowledge_base`: busqueda rapida sobre chunks de la biblioteca.
- `teacher_memory`: memoria pedagogica compilada previamente curso por curso, para que el asistente responda como maestro y no como buscador.

Si quieres que el asistente realmente responda desde conocimiento estudiado, debes construir `teacher_memory.json` una vez.

## Requisitos

- Python 3.9+
- Dependencias de `requirements.txt`

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecutar

```bash
uvicorn api.main:app --reload
```

La API quedará disponible en:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/courses`
- `http://127.0.0.1:8000/ask`

## Despliegue estable en la nube

Si quieres que el asistente funcione sin depender de tu computadora ni de `cloudflared`, la opción más simple para este proyecto es desplegarlo como servicio web con Docker.

Este repositorio ya quedó preparado para eso con:

- [Dockerfile](/Users/m2/Documents/New%20project/Dockerfile)
- [render.yaml](/Users/m2/Documents/New%20project/render.yaml)
- datos incluidos en el contenedor (`data/chunks`, `data/embeddings`, `data/teacher_memory.json`)

### Opción recomendada: Render

Pasos:

1. Sube este proyecto a GitHub.
2. En Render, crea un nuevo servicio desde el repositorio.
3. Render detectará [render.yaml](/Users/m2/Documents/New%20project/render.yaml).
4. Configura la variable secreta:

```bash
OPENAI_API_KEY=tu_clave_real
```

5. Despliega.

Si todavía no tienes el proyecto en GitHub, sigue la guía corta en:

- [docs/DEPLOY_RENDER.md](/Users/m2/Documents/New%20project/docs/DEPLOY_RENDER.md)

Cuando termine, revisa:

- `/health`

Debe devolver:

- `llm_enabled: true`
- `semantic_index_ready: true`
- `teacher_memory_ready: true`

### Qué gana esta arquitectura

- Ya no depende de que tu Mac esté encendida
- Ya no depende de `cloudflared`
- Tendrás una URL fija del backend
- Cada cambio nuevo se podrá desplegar desde GitHub
- Wix podrá apuntar siempre al mismo backend

## Construir memoria de maestro

Este paso estudia toda la biblioteca con OpenAI, resume cada fuente, luego resume cada curso, y guarda la memoria docente en:

- `data/teacher_memory.json`

Ejecuta:

```bash
source .venv/bin/activate
python scripts/build_teacher_memory.py
```

Cuando termine, reinicia `uvicorn`.

En `http://127.0.0.1:8000/health` veras estos campos:

- `teacher_memory_ready`
- `teacher_memory_courses`
- `teacher_memory_sources`

Solo cuando `teacher_memory_ready` sea `true`, el asistente empezara a responder desde la memoria pedagogica compilada.

## Variables opcionales

- `CHUNKS_PATH`: ruta al archivo JSONL con los chunks de la biblioteca
- `OPENAI_API_KEY`: activa generacion natural con OpenAI
- `OPENAI_MODEL`: modelo para redactar respuestas naturales, por defecto `gpt-5-mini`
- `OPENAI_IMAGE_MODEL`: modelo para generar imagenes cuando el asistente lo sugiera, por defecto `gpt-image-1`

Tambien puedes crear un archivo `.env` en la raiz del proyecto usando `.env.example`.

## Ejemplo de consulta

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"¿Qué es el genograma?","max_results":3,"want_visual":true}'
```

## Que devuelve ahora

- `answer`: respuesta redactada de forma natural
- `visual`: apoyo visual que puede salir como texto plano, diagrama `mermaid`, prompt de imagen o `image_data_url`
- `generation_mode`: `openai` si uso modelo, `fallback` si respondio sin modelo
- `sources`: se conservan por depuracion o auditoria, pero no hace falta mostrarlas al alumno

La consulta normal no genera una imagen real por defecto, porque eso puede volver lenta la respuesta en Wix. En su lugar, devuelve la idea visual y, si hace falta, despues se puede pedir la imagen en un segundo paso.

## Nota importante

Si quieres respuestas realmente conversacionales, con contexto, buenos resúmenes y ayudas visuales de calidad, necesitas crear un archivo `.env` real con tu clave:

```bash
cp .env.example .env
```

Luego edita `.env` y agrega tu clave de OpenAI:

```bash
OPENAI_API_KEY=tu_clave_real
OPENAI_MODEL=gpt-5-mini
OPENAI_IMAGE_MODEL=gpt-image-1
```

Despues reinicia `uvicorn` para que la API cargue esa configuracion.
