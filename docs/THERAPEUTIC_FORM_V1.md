# Formulario Terapéutico Definitivo V1

## Objetivo

Formulario que llena el terapeuta durante la entrevista con el paciente.

Debe servir para:

1. Capturar el caso completo
2. Construir una lectura inicial
3. Preparar el rastreo terapéutico
4. Interpretar pares después
5. Sugerir protocolo de liberación

---

## Reglas generales

- Todo visible en una sola experiencia de captura
- Permitir múltiples síntomas
- Permitir texto libre amplio
- Guardar tanto estructura como notas del terapeuta
- No asumir diagnóstico médico
- Enfocarse en orientación terapéutica alternativa

---

## Estructura del formulario

## Sección 1. Datos de la sesión

### Campos

- `session_date`
  - tipo: `date`
  - obligatorio: sí
  - etiqueta: `Fecha de la sesión`

- `therapist_name`
  - tipo: `text`
  - obligatorio: sí
  - etiqueta: `Nombre del terapeuta`

- `session_type`
  - tipo: `select`
  - obligatorio: sí
  - opciones:
    - `primera_vez`
    - `seguimiento`
  - etiqueta: `Tipo de sesión`

- `case_status`
  - tipo: `select`
  - obligatorio: sí
  - opciones:
    - `abierto`
    - `en_proceso`
    - `cerrado`
  - etiqueta: `Estado del caso`

---

## Sección 2. Datos del consultante

### Campos

- `patient_full_name`
  - tipo: `text`
  - obligatorio: sí
  - etiqueta: `Nombre completo del consultante`

- `patient_birthdate`
  - tipo: `date`
  - obligatorio: sí
  - etiqueta: `Fecha de nacimiento`

- `patient_age`
  - tipo: `number`
  - obligatorio: no
  - etiqueta: `Edad`

- `patient_gender`
  - tipo: `text`
  - obligatorio: no
  - etiqueta: `Sexo / género`

- `patient_occupation`
  - tipo: `text`
  - obligatorio: no
  - etiqueta: `Ocupación`

- `patient_city`
  - tipo: `text`
  - obligatorio: no
  - etiqueta: `Ciudad / lugar de residencia`

---

## Sección 3. Motivo de consulta

### Campos

- `consultation_reason`
  - tipo: `textarea`
  - obligatorio: sí
  - etiqueta: `Motivo de consulta`

- `session_goal`
  - tipo: `textarea`
  - obligatorio: sí
  - etiqueta: `Objetivo de la sesión`

- `main_emotion`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Emoción principal reportada`

- `recent_trigger`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Detonante reciente`

- `therapist_initial_observation`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Observación inicial del terapeuta`

---

## Sección 4. Genograma básico

## 4.1 Abuelos

Repetir estructura para:

- `maternal_grandmother`
- `maternal_grandfather`
- `paternal_grandmother`
- `paternal_grandfather`

### Subcampos

- `full_name`
  - tipo: `text`
- `birthdate`
  - tipo: `date`
- `death_date`
  - tipo: `date`
- `notes`
  - tipo: `textarea`

## 4.2 Padres

Repetir estructura para:

- `mother`
- `father`

### Subcampos

- `full_name`
  - tipo: `text`
- `birthdate`
  - tipo: `date`
- `death_date`
  - tipo: `date`
- `notes`
  - tipo: `textarea`

## 4.3 Hermanos

Lista dinámica.

### Subcampos por hermano

- `full_name`
- `birthdate`
- `notes`

## 4.4 Parejas

### Pareja actual

- `current_partner_name`
- `current_partner_birthdate`
- `current_relationship_duration`
- `current_partner_notes`

### Parejas significativas

Lista dinámica.

#### Subcampos

- `full_name`
- `birthdate`
- `relationship_duration`
- `relationship_notes`

## 4.5 Hijos

Lista dinámica.

### Subcampos

- `full_name`
- `birthdate`
- `death_date`
- `other_parent_name`
- `relationship_duration_with_other_parent`
- `notes`

---

## Sección 5. Historia familiar y relacional

### Campos

- `family_conflicts_notes`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Conflictos familiares relevantes`

- `family_secrets_notes`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Secretos, pérdidas, injusticias o hechos relevantes`

- `transgenerational_patterns_notes`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Patrones familiares repetitivos observados`

- `important_relationships_notes`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Relaciones significativas y su impacto`

---

## Sección 6. Síntomas actuales

Lista dinámica sin límite fijo.

### Subcampos por síntoma

- `symptom_name`
  - tipo: `text`
  - obligatorio: sí
  - etiqueta: `Síntoma`

- `intensity_order`
  - tipo: `number`
  - obligatorio: no
  - etiqueta: `Orden de intensidad`

- `approx_onset_age_or_date`
  - tipo: `text`
  - obligatorio: no
  - etiqueta: `Edad o fecha aproximada de aparición`

- `symptom_characteristics`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Características del síntoma`

- `symptom_frequency`
  - tipo: `text`
  - obligatorio: no
  - etiqueta: `Frecuencia del síntoma`

- `stimulating_factors`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Factores que lo activan o empeoran`

- `relieving_factors`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Factores que lo alivian`

- `associated_people_places_events`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Personas, lugares, momentos o situaciones asociadas`

- `therapist_notes`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Notas del terapeuta sobre este síntoma`

---

## Sección 7. Antecedentes y recurrencias

Lista dinámica.

### Subcampos por antecedente

- `event_type`
  - tipo: `select`
  - obligatorio: sí
  - opciones:
    - `sintoma_recurrente`
    - `cirugia`
    - `diagnostico_previsto`
    - `evento_relevante`
  - etiqueta: `Tipo de antecedente`

- `event_name`
  - tipo: `text`
  - obligatorio: sí
  - etiqueta: `Nombre del antecedente`

- `approx_onset_age_or_date`
  - tipo: `text`
  - obligatorio: no
  - etiqueta: `Edad o fecha aproximada`

- `event_characteristics`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Características`

- `event_frequency`
  - tipo: `text`
  - obligatorio: no
  - etiqueta: `Frecuencia o repetición`

- `event_notes`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Notas del terapeuta`

---

## Sección 8. Historia emocional

### Campos

- `current_emotional_context`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Contexto emocional actual`

- `emotional_context_at_onset`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Contexto emocional al inicio del síntoma`

- `main_worries_before_symptom`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Preocupaciones previas al problema`

- `what_bothers_today`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Qué le molesta hoy en su vida`

- `perceived_impediments`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Impedimentos o bloqueos percibidos`

- `secondary_benefit`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Beneficio secundario del síntoma o situación`

---

## Sección 9. Historia terapéutica

### Campos

- `previous_alternative_therapies`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Terapias alternativas previas`

- `previous_results`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Resultados previos`

- `current_support_practices`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Prácticas actuales de apoyo`

---

## Sección 10. Observaciones del terapeuta

### Campos

- `free_case_notes`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Notas libres del caso`

- `initial_hypothesis`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Hipótesis inicial del terapeuta`

- `priority_to_explore`
  - tipo: `textarea`
  - obligatorio: no
  - etiqueta: `Prioridades para explorar`

---

## Sección 11. Datos de rastreo posterior

Esta sección no necesariamente se llena en la primera entrevista, pero debe existir en el mismo expediente.

### Lista dinámica de pares encontrados

#### Subcampos

- `pair_name`
  - tipo: `text`
  - obligatorio: sí

- `pair_order`
  - tipo: `number`
  - obligatorio: no

- `pair_notes`
  - tipo: `textarea`
  - obligatorio: no

- `pair_detected_context`
  - tipo: `textarea`
  - obligatorio: no

---

## Campos clave para análisis automático

Estos campos alimentan directamente el motor terapéutico:

- `consultation_reason`
- `session_goal`
- `main_emotion`
- `recent_trigger`
- `family_conflicts_notes`
- `family_secrets_notes`
- `transgenerational_patterns_notes`
- `current_emotional_context`
- `emotional_context_at_onset`
- `what_bothers_today`
- `perceived_impediments`
- `secondary_benefit`
- lista de síntomas actuales
- lista de antecedentes
- datos de madre, padre, hijos y parejas significativas

---

## Resultado esperado del análisis

Con este formulario, el sistema debe poder construir:

1. lectura general del caso
2. síntomas prioritarios
3. sistemas probablemente implicados
4. posibles conflictos a revisar
5. masa conflictual probable
6. preguntas faltantes
7. sugerencia de rastreo
8. interpretación posterior de pares
9. protocolo de liberación sugerido

---

## Recomendación de interfaz

Aunque todo esté visible, conviene mostrarlo en bloques expandibles:

- Datos de la sesión
- Consultante
- Genograma
- Historia familiar
- Síntomas actuales
- Antecedentes
- Historia emocional
- Historia terapéutica
- Notas del terapeuta
- Rastreo posterior

Así se mantiene todo visible, pero con orden visual.

---

## Siguiente documento

Después de este formulario, toca diseñar:

1. salida del análisis terapéutico
2. cuadro de interpretación de pares
3. catálogo de protocolos de liberación
