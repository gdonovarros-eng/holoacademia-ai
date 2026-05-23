# Holoacademia AI – API Endpoints

## 1. Resumen general

Holoacademia AI expone 3 motores principales por HTTP:

- **Asistente Académico**
  Responde dudas sobre conceptos, glosario, módulos y contenido formativo de los cursos.
- **Asistente Terapéutico**
  Ayuda a ordenar un caso, detectar vacíos de información y sugerir líneas prudentes de análisis.
- **Guía de Protocolos**
  Devuelve la guía estructurada de un protocolo existente, con pasos, observaciones y advertencias.

### Cuándo usar cada uno

- Usa **`/academic/ask`** cuando el usuario quiere aprender o entender algo del curso.
- Usa **`/therapeutic/analyze`** cuando el terapeuta quiere ordenar un caso o pensar mejor qué explorar.
- Usa **`/protocols/guide`** cuando se necesita consultar un protocolo específico ya existente en la base.

---

## 2. Endpoint: `POST /academic/ask`

### Propósito
Responder dudas académicas sobre cursos, conceptos, glosario y módulos.

### Request ejemplo

```json
{
  "query": "¿Qué es un par biomagnético?"
}
```

### Response ejemplo

```json
{
  "answer": "No encontré base suficiente dentro del curso para responder eso con precisión académica. Si quieres, puedo intentar con otro término, con un módulo concreto o con una pregunta más específica.",
  "confidence": "low",
  "sources_used": [],
  "concepts_used": [],
  "suggested_followups": [
    "Dame un glosario rápido de este curso",
    "Resume el tema como si fuera estudiante nuevo"
  ],
  "retrieval_trace": [],
  "intent": "definition",
  "mode_used": "fast",
  "used_fallback": true,
  "concept_resolution": {},
  "target_resolution_trace": [],
  "timings": {
    "retrieval_ms": 1.44,
    "context_building_ms": 0.01,
    "llm_ms": 0.23,
    "total_ms": 1.69
  }
}
```

### Campos principales

- `answer`: respuesta final para el usuario
- `confidence`: `high | medium | low`
- `sources_used`: fuentes académicas usadas
- `concepts_used`: conceptos centrales detectados
- `suggested_followups`: preguntas sugeridas para seguir
- `intent`: intención detectada de la pregunta
- `mode_used`: `fast` o `deep`
- `used_fallback`: indica si respondió con fallback local
- `concept_resolution`: trazabilidad de resolución del concepto
- `timings`: tiempos internos del motor

### Cuándo usarlo

- conceptos
- diferencias entre términos
- resúmenes de módulo
- ubicación de temas en el curso
- explicaciones simples para estudiantes

---

## 3. Endpoint: `POST /therapeutic/analyze`

### Propósito
Ayudar al terapeuta a ordenar el caso y detectar qué faltaría explorar, sin reemplazar su criterio clínico.

### Request ejemplo

```json
{
  "motivo_consulta": "dolor lumbar",
  "sintomas": ["dolor lumbar", "fatiga"],
  "inicio": "hace 3 meses",
  "contexto_emocional": "estrés laboral",
  "pregunta_del_terapeuta": "¿qué me falta explorar?"
}
```

### Response ejemplo

```json
{
  "answer": "Con lo que compartes, sí aparecen algunos elementos útiles para ordenar el caso, pero todavía faltan datos antes de hacer una lectura más firme.",
  "confidence": "medium",
  "missing_data": [
    "duración",
    "frecuencia o recurrencia",
    "antecedentes relevantes",
    "observaciones clínicas"
  ],
  "priority_questions": [
    "¿Cómo es exactamente el síntoma: dónde está, cómo duele o cómo se siente?",
    "¿Con qué frecuencia aparece: diario, varias veces por semana o en recurrencias por periodos?",
    "¿Qué factores lo inhiben, lo agravan o lo disparan?"
  ],
  "possible_lines": [
    "La intervención ya empezó; no separar investigación y terapia de manera rígida."
  ],
  "warnings": [
    "El rastreo no se presenta como medicina alopática ni como sustituto de diagnóstico médico."
  ],
  "used_patterns": [
    "patron_subyacente_vs_sintoma"
  ],
  "used_guides": [
    "guide_5_elementos_global"
  ],
  "trace": {}
}
```

### Campos principales

- `answer`: lectura inicial prudente
- `confidence`: nivel de firmeza de la lectura
- `missing_data`: datos que todavía faltan
- `priority_questions`: preguntas más útiles para seguir
- `possible_lines`: líneas posibles de análisis, no conclusiones cerradas
- `warnings`: límites y advertencias activadas
- `used_patterns`: patrones del curso usados
- `used_guides`: guías interpretativas usadas
- `trace`: trazabilidad interna

### Cuándo usarlo

- ordenar un caso
- detectar información faltante
- ver qué conviene preguntar después
- construir una lectura inicial prudente

---

## 4. Endpoint: `POST /protocols/guide`

### Propósito
Consultar un protocolo específico de la base y devolver su guía estructurada.

### Request ejemplo por nombre

```json
{
  "protocol_name": "Entrevista inicial de rastreo"
}
```

### Request ejemplo por id

```json
{
  "protocol_id": "entrevista_inicial_de_rastreo"
}
```

### Request ejemplo con contexto opcional

```json
{
  "protocol_name": "Entrevista inicial de rastreo",
  "user_goal": "quiero usarlo para ordenar mejor una primera sesión",
  "case_context": {
    "motivo_consulta": "dolor digestivo recurrente"
  }
}
```

### Response ejemplo

```json
{
  "found": true,
  "protocol_id": "entrevista_inicial_de_rastreo",
  "protocol_name": "Entrevista inicial de rastreo",
  "answer": "Encontré el protocolo solicitado. Te dejo una guía clara del objetivo, cuándo se usa y los pasos principales para seguirlo con orden.",
  "confidence": "high",
  "objetivo": "Convertir la queja del paciente en información clínica operable para rastreo e interpretación.",
  "descripcion": "Secuencia base para ordenar síntomas, cronología, moduladores y controles antes del trabajo energético.",
  "cuando_usarlo": [
    "Al inicio de toda sesión."
  ],
  "prerequisitos": [
    "Consentimiento informado y ficha de control."
  ],
  "pasos": [
    {
      "orden": 1,
      "titulo": "Identificar motivo de consulta",
      "instruccion": "Preguntar qué síntomas desea trabajar el paciente.",
      "objetivo_del_paso": "Definir el foco de la sesión.",
      "que_observar": [],
      "que_registrar": [],
      "notas": [],
      "decision_points": [],
      "criterios_de_avance": [],
      "errores_comunes": []
    }
  ],
  "observaciones": [],
  "advertencias": [],
  "trace": {}
}
```

### Si el protocolo no se encuentra

```json
{
  "found": false,
  "protocol_id": null,
  "protocol_name": null,
  "answer": "No encontré un protocolo con base suficiente usando ese nombre o id. Si quieres, prueba con el nombre exacto del protocolo o con un identificador más específico.",
  "confidence": "low",
  "objetivo": null,
  "descripcion": null,
  "cuando_usarlo": [],
  "prerequisitos": [],
  "pasos": [],
  "observaciones": [],
  "advertencias": [],
  "trace": {}
}
```

### Campos principales

- `found`: indica si se encontró el protocolo
- `protocol_id` / `protocol_name`: identificadores del protocolo
- `answer`: introducción breve y clara
- `pasos`: lista estructurada del protocolo
- `observaciones`: notas complementarias
- `advertencias`: precauciones o límites
- `trace`: datos de matching interno

### Cuándo usarlo

- consultar un protocolo específico
- obtener pasos estructurados
- revisar qué observar y qué registrar
- mostrar una guía operacional en frontend

---

## 5. Notas rápidas para frontend y Postman

### Content-Type

Usar siempre:

```http
Content-Type: application/json
```

### Método HTTP

Los tres endpoints usan `POST`.

### Endpoints disponibles

- `POST /academic/ask`
- `POST /therapeutic/analyze`
- `POST /protocols/guide`

### Recomendación de uso en frontend

- Usa **académico** para preguntas del alumno
- usa **terapéutico** para apoyar razonamiento del terapeuta
- usa **protocolos** para abrir una guía estructurada paso a paso

### Respuestas de error controlado

En estos endpoints se intenta devolver una respuesta estructurada incluso si algo falla internamente.  
Eso significa que muchas veces recibirás `200` con una respuesta prudente y `confidence: "low"` en vez de un error duro.

---

## 6. Ejemplos rápidos con cURL

### Académico

```bash
curl -X POST http://localhost:8000/academic/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"¿Qué es un par biomagnético?"}'
```

### Terapéutico

```bash
curl -X POST http://localhost:8000/therapeutic/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "motivo_consulta":"dolor lumbar",
    "sintomas":["dolor lumbar","fatiga"],
    "inicio":"hace 3 meses",
    "contexto_emocional":"estrés laboral",
    "pregunta_del_terapeuta":"¿qué me falta explorar?"
  }'
```

### Protocolos

```bash
curl -X POST http://localhost:8000/protocols/guide \
  -H "Content-Type: application/json" \
  -d '{"protocol_name":"Entrevista inicial de rastreo"}'
```
