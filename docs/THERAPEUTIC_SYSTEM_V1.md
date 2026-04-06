# Sistema Holoacademia V1

## Objetivo

Construir un software propio con dos experiencias separadas:

1. Dudas sobre cursos
2. Asistente terapéutico

El sistema debe responder solo con base en los textos y manuales proporcionados por la escuela. No debe usar fuentes externas como verdad doctrinal.

---

## Principios de diseño

### 1. Dos motores separados

No debe existir un solo chat ambiguo.

- `Course QA Engine`
  - Responde dudas sobre cursos, conceptos, módulos, protocolos, cuestionarios, maestros y estructura académica.
- `Therapy Intake Engine`
  - Analiza la información del paciente cargada en un formulario estructurado.
- `Pair Interpretation Engine`
  - Interpreta los pares biomagnéticos capturados después del rastreo y propone lectura integradora y protocolo.

### 2. Base de conocimiento estructurada

No responder desde chunks crudos como salida final.

El sistema debe:

- extraer información de los textos
- normalizarla
- guardarla en entidades claras
- responder desde esas entidades

### 3. Flujo terapéutico por fases

1. Captura del caso
2. Análisis inicial
3. Rastreo de pares
4. Interpretación de pares
5. Protocolo de liberación
6. Seguimiento

---

## Pantallas

## Pantalla 1: Dudas sobre cursos

### Entrada

- pregunta libre
- memoria conversacional por sesión

### Tipos de intención

- definición
- resumen
- qué se ve en un curso
- módulos
- maestro / ponente
- protocolos
- cuestionarios
- sistemas
- pares
- comparación entre cursos
- integración de varias fuentes

### Salida

- respuesta completa y humana
- opcionalmente:
  - lista
  - pasos
  - cuadro
  - mapa de estudio
  - ruta de aprendizaje

### Regla

Si el usuario pide algo exacto, el sistema debe priorizar recuperación fiel y reorganización clara.

Ejemplos:

- "dame el cuestionario"
- "dame el protocolo"
- "cuántos módulos hay"
- "qué sistemas se ven"

---

## Pantalla 2: Asistente terapéutico

### Paso 1. Formulario inicial

Bloques:

- datos del consultante
- genograma básico
- padres y abuelos
- hermanos
- parejas significativas
- hijos
- síntomas actuales
- síntomas recurrentes / cirugías / antecedentes
- frecuencia
- edad o fecha aproximada de aparición
- factores que estimulan o inhiben el síntoma

### Paso 2. Análisis inicial

El sistema devuelve:

- lectura general del caso
- síntomas prioritarios
- sistemas probablemente implicados
- posibles ejes conflictivos
- masa conflictual probable
- focos familiares o transgeneracionales relevantes
- preguntas faltantes para afinar el rastreo
- ruta sugerida de abordaje

### Paso 3. Captura de rastreo

El usuario terapéutico captura:

- pares biomagnéticos encontrados
- orden o prioridad
- observaciones
- notas relevantes

### Paso 4. Interpretación de pares

El sistema devuelve:

- significado de cada par
- conflicto o sistema sugerido por cada par
- relación entre los pares detectados
- patrón dominante del caso
- cuadro integrador final

### Paso 5. Protocolo de liberación

El sistema propone un protocolo disponible en los cursos, por ejemplo:

- estrés postraumático
- sentimental
- sistémico
- transgeneracional

La salida debe incluir:

- nombre del protocolo
- cuándo aplica
- pasos
- comando sugerido
- repetición / días
- observaciones de seguimiento

### Paso 6. Seguimiento

Debe permitir:

- registrar evolución
- registrar nuevos pares
- registrar cambios de síntomas
- registrar nuevas interpretaciones

---

## Modelo de datos

## Tabla: `courses`

- `id`
- `slug`
- `name`
- `line`
- `type`
- `description`
- `priority`
- `active`

## Tabla: `course_sources`

- `id`
- `course_id`
- `source_name`
- `source_type`
- `path`
- `is_primary`
- `cleanliness_score`

## Tabla: `course_modules`

- `id`
- `course_id`
- `module_number`
- `module_name`
- `summary`

## Tabla: `teachers`

- `id`
- `name`
- `bio`

## Tabla: `course_teachers`

- `id`
- `course_id`
- `teacher_id`
- `role`

## Tabla: `concepts`

- `id`
- `name`
- `slug`
- `definition`
- `notes`

## Tabla: `course_concepts`

- `id`
- `course_id`
- `concept_id`
- `importance`

## Tabla: `systems`

- `id`
- `name`
- `slug`
- `description`

## Tabla: `symptoms`

- `id`
- `name`
- `slug`
- `description`

## Tabla: `conflicts`

- `id`
- `name`
- `slug`
- `description`
- `system_id`
- `conflict_group`

## Tabla: `tracking_questions`

- `id`
- `scope_type`
- `scope_id`
- `question_text`
- `question_order`
- `phase`

`scope_type` puede ser:

- `system`
- `conflict`
- `protocol`
- `course`

## Tabla: `biomagnetic_pairs`

- `id`
- `pair_name`
- `pair_code`
- `system_id`
- `description`
- `notes`

## Tabla: `pair_interpretations`

- `id`
- `pair_id`
- `meaning`
- `suggested_conflict`
- `suggested_system`
- `observations`

## Tabla: `release_protocols`

- `id`
- `name`
- `slug`
- `summary`
- `steps_markdown`
- `command_text`
- `repeat_notes`
- `days_notes`
- `source_course_id`

## Tabla: `protocol_triggers`

- `id`
- `protocol_id`
- `trigger_type`
- `trigger_value`

`trigger_type` puede ser:

- `conflict`
- `system`
- `pair`
- `pattern`

## Tabla: `questionnaires`

- `id`
- `name`
- `slug`
- `description`

## Tabla: `questionnaire_fields`

- `id`
- `questionnaire_id`
- `section_name`
- `field_key`
- `label`
- `field_type`
- `required`
- `field_order`

## Tabla: `patient_cases`

- `id`
- `created_at`
- `updated_at`
- `case_status`
- `patient_name`
- `patient_birthdate`
- `intake_payload_json`
- `therapist_notes`

## Tabla: `case_analysis`

- `id`
- `case_id`
- `summary`
- `priority_symptoms_json`
- `probable_systems_json`
- `probable_conflicts_json`
- `mass_conflict_hypothesis`
- `followup_questions_json`
- `suggested_route_json`

## Tabla: `case_pairs`

- `id`
- `case_id`
- `pair_name`
- `pair_id`
- `priority_order`
- `notes`

## Tabla: `case_pair_analysis`

- `id`
- `case_id`
- `integrated_reading`
- `pair_table_json`
- `dominant_patterns_json`
- `suggested_protocol_id`

## Tabla: `source_fragments`

- `id`
- `course_id`
- `source_id`
- `fragment_type`
- `title`
- `content`
- `tags_json`

Uso:

- evidencia interna
- trazabilidad
- reconstrucción de respuestas fieles

---

## Flujo exacto del Asistente terapéutico

## Fase 1. Intake

### Objetivo

Capturar una imagen suficientemente completa del caso.

### Salida del backend

- validar campos
- normalizar fechas
- normalizar parentescos
- normalizar síntomas
- generar `case_id`

## Fase 2. Preanálisis

### Objetivo

Cruzar la información del caso contra:

- sistemas
- conflictos
- preguntas clave
- señales familiares

### Reglas iniciales

- priorizar síntomas actuales por intensidad
- buscar temporalidad del síntoma
- buscar "gota que derramó el vaso"
- buscar "agua que llenó el vaso"
- buscar asociaciones psicológicas
- buscar drama repetitivo o masa conflictual

### Salida

- resumen del caso
- hipótesis de sistemas
- hipótesis conflictiva
- preguntas faltantes
- recomendación de rastreo

## Fase 3. Rastreo

### Objetivo

Permitir que el terapeuta capture el resultado del rastreo físico/energético realizado fuera del software.

### Entrada

- lista de pares encontrados
- comentarios del terapeuta

### Salida

- almacenamiento estructurado de pares

## Fase 4. Interpretación de pares

### Objetivo

Traducir los pares a:

- significado puntual
- lectura integrada
- relación con el caso

### Salida

- cuadro de pares
- lectura global
- sistema dominante
- conflicto dominante
- patrones familiares / emocionales

## Fase 5. Protocolo de liberación

### Objetivo

Seleccionar un protocolo congruente con:

- análisis inicial
- pares encontrados
- patrón dominante

### Salida

- nombre del protocolo
- pasos exactos
- texto del comando
- repetición
- observaciones

---

## Lógica de decisión

## Dudas sobre cursos

1. Detectar curso o cursos mencionados
2. Detectar tipo de consulta
3. Si es factual:
   - responder desde estructura
4. Si es artefacto exacto:
   - recuperar fuente + reorganizar
5. Si es explicación:
   - sintetizar desde conceptos y módulos

## Asistente terapéutico

1. Analizar formulario
2. Mapear síntomas a sistemas probables
3. Mapear sistemas a conflictos probables
4. Cruzar contra genograma y relaciones
5. Proponer preguntas faltantes
6. Esperar resultado de rastreo
7. Interpretar pares
8. Seleccionar protocolo

---

## Orden de construcción recomendado

## Fase 1

- crear base de datos
- importar cursos
- importar módulos
- importar conceptos base
- construir pantalla `Dudas sobre cursos`

## Fase 2

- construir formulario terapéutico
- persistencia de casos
- análisis inicial del caso

## Fase 3

- catálogo estructurado de pares
- captura de rastreo
- interpretación de pares

## Fase 4

- protocolos de liberación
- recomendación de protocolo
- reporte final del caso

## Fase 5

- seguimiento de pacientes
- historial clínico-terapéutico
- panel interno

---

## Recomendación de implementación

### Frontend

- `Next.js`

### Backend

- `FastAPI`

### Base de datos

- `Postgres`

### Integración con Wix

- usar `iframe`

### Razón

Esto da:

- más control
- mejores formularios
- sesión real
- evolución a software propio
- menor fricción técnica que intentar vivir dentro de Wix

---

## Siguiente documento

Después de esta arquitectura, toca definir:

1. formulario terapéutico final
2. taxonomía de conflictos
3. taxonomía de sistemas
4. estructura del cuadro de interpretación de pares
5. formato exacto del reporte final al usuario
