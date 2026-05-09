# Motor terapéutico v1

Este motor construye una lectura inicial prudente del caso usando la capa terapéutica del curso, sin mezclar todavía protocolos como flujo principal ni usar un LLM.

## Qué carga

Desde `data/knowledge_units/<curso>` carga principalmente:

- `04_therapeutic/intake_questions.json`
- `04_therapeutic/reasoning_patterns.json`
- `04_therapeutic/interpretation_guides.json`
- `04_therapeutic/therapeutic_observations.json`
- `04_therapeutic/clinical_warnings.json`
- `06_catalog/course_manifest.json`
- `09_connection_map.json`

Como soporte secundario también puede leer:

- `03_academic/course_overview.json`
- `03_academic/module_summaries.json`
- `03_academic/concepts.json`

## Cómo funciona

1. `loader.py`
   Carga y normaliza la base terapéutica del curso con degradación elegante si falta algún archivo.

2. `intake_engine.py`
   Detecta qué datos del caso ya están presentes, cuáles faltan y qué preguntas conviene priorizar.

3. `case_analyzer.py`
   Ordena el caso en síntomas, cronología, contexto, vacíos y puntos de atención.

4. `reasoning_engine.py`
   Hace match prudente contra patrones terapéuticos del curso y propone líneas posibles, no conclusiones cerradas.

5. `interpretation_engine.py`
   Añade guías interpretativas y advertencias para no sobreleer el caso.

6. `response_builder.py`
   Convierte todo eso en una respuesta útil, humana y prudente para el terapeuta.

7. `service.py`
   Orquesta el flujo completo con `answer_therapeutic_query(case_input)`.

## Uso rápido

```python
from therapeutic_assistant.service import answer_therapeutic_query

response = answer_therapeutic_query(
    {
        "motivo_consulta": "Dolor digestivo recurrente",
        "sintomas": ["ardor", "pesadez"],
        "inicio": "Hace seis meses",
        "frecuencia": "Cada semana",
        "contexto_emocional": "Mucho miedo desde una separación",
        "pregunta_del_terapeuta": "Ayúdame a ordenar este caso",
    }
)
```

## Tests

```bash
python -m unittest discover "/Users/m2/Documents/New project/Motor terapeutico/therapeutic_assistant/tests"
```
