# Motor académico

Primer motor real del Asistente Académico de Holoacademia.

## Qué hace

- carga la base académica de un curso
- busca contexto por conceptos, glosario, módulos y FAQs
- construye un contexto compacto y pedagógico
- genera una respuesta académica clara
- evita mezclar terapia, intake clínico o protocolos

## Estructura

- `academic_assistant/models.py`: modelos de datos
- `academic_assistant/loader.py`: carga y normaliza datos del curso
- `academic_assistant/retriever.py`: búsqueda heurística híbrida sin embeddings
- `academic_assistant/context_builder.py`: consolida contexto corto y útil
- `academic_assistant/prompt_builder.py`: crea el prompt del tutor académico
- `academic_assistant/answer_generator.py`: integra LLM actual o usa fallback determinístico
- `academic_assistant/service.py`: orquesta el flujo completo
- `academic_assistant/tests/`: tests mínimos

## Cómo carga los datos

Por defecto toma:

`../04_holoacademia_app/data/knowledge_units/course_holobiomagnetismo_2021`

También puedes pasar otra ruta de curso al servicio o usar la variable:

`ACADEMIC_ASSISTANT_COURSE_DIR`

## Cómo busca

Orden de prioridad:

1. `concepts.json`
2. `glossary.json`
3. `module_summaries.json`
4. `faq_candidates.json`
5. `course_overview.json`
6. `course_manifest.json`
7. inventarios
8. texto limpio como fallback

La búsqueda usa:

- exact match
- aliases
- contains
- coincidencia parcial
- heurística por módulo

## Cómo arma el contexto

El `context_builder`:

- elimina duplicados
- prioriza conceptos bien definidos
- agrega glosario solo como apoyo
- añade resúmenes de módulo si ayudan
- conserva citas internas y `retrieval_trace`

## Cómo responde

Si hay cliente LLM configurado, usa el proveedor actual compatible con OpenAI/Groq.
Si no hay LLM disponible, devuelve una respuesta determinística y honesta basada en el contexto recuperado.

## Uso rápido

```python
from academic_assistant import answer_academic_query

response = answer_academic_query("¿Qué es el par biomagnético?")
print(response["answer"])
```

## Tests

Desde esta carpeta:

```bash
python -m unittest discover -s academic_assistant/tests
```
