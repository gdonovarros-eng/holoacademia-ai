# Esquema Del Diccionario De Enfermedades V1

## Objetivo

Construir una capa estructurada para consultar enfermedades, síntomas y posibles orígenes desde la biodescodificación y referencias afines, sin mezclar este material con los cursos oficiales.

Esta capa debe servir para:

1. consulta directa por enfermedad
2. enriquecer el análisis terapéutico
3. cruzar síntomas del formulario con entradas del diccionario
4. complementar la lectura de pares y protocolos

---

## Regla doctrinal

Jerarquía recomendada:

1. Cursos y manuales de Holoacademia
2. Diccionario de enfermedades y referencias
3. Material complementario

Si una enfermedad aparece en el diccionario y también en cursos, la lectura final debe priorizar la línea del curso y usar el diccionario como apoyo.

---

## Qué ya existe

Biblioteca procesada:

- [data/reference_processed/catalog.json](/Users/m2/Documents/New%20project/data/reference_processed/catalog.json)

Categorías útiles:

- `disease_dictionary`
- `transgenerational`
- `trauma_emotion_release`
- `belief_consciousness`
- `complementary_misc`

---

## Entidades recomendadas

## Tabla: `disease_dictionary_sources`

Representa cada libro o fuente.

Campos:

- `id`
- `title`
- `author`
- `category`
- `source_path`
- `text_path`
- `priority`
- `active`

Ejemplos:

- "El Gran Diccionario de la Biodescodificación"
- "Diccionario de Psicodescodificación"
- "El Origen Emocional de las Enfermedades"

---

## Tabla: `disease_entries`

Entrada principal por enfermedad.

Campos:

- `id`
- `canonical_name`
- `slug`
- `system_name`
- `entry_status`
- `notes`

### `entry_status`

- `draft`
- `reviewed`
- `canonical`

Ejemplos de `canonical_name`:

- `asma`
- `colitis ulcerosa`
- `diabetes`
- `migraña`
- `eczema`

---

## Tabla: `disease_aliases`

Permite buscar variantes.

Campos:

- `id`
- `disease_entry_id`
- `alias`

Ejemplos:

- `migraña`
- `migrañas`
- `cefalea migrañosa`

---

## Tabla: `disease_source_entries`

Una misma enfermedad puede aparecer en varios libros.

Campos:

- `id`
- `disease_entry_id`
- `source_id`
- `source_heading`
- `source_fragment`
- `source_page_reference`
- `confidence`

Uso:

- trazabilidad
- revisión manual
- reconstrucción de ficha consolidada

---

## Tabla: `disease_meanings`

Posibles significados o ejes emocionales.

Campos:

- `id`
- `disease_entry_id`
- `meaning_text`
- `meaning_type`
- `source_id`
- `priority`

### `meaning_type`

- `possible_origin`
- `emotional_axis`
- `symbolic_interpretation`
- `chakra_association`
- `body_function_conflict`

---

## Tabla: `disease_symptoms`

Síntomas típicos ligados a la entrada.

Campos:

- `id`
- `disease_entry_id`
- `symptom_text`
- `source_id`

---

## Tabla: `disease_related_conflicts`

Conflictos posibles asociados.

Campos:

- `id`
- `disease_entry_id`
- `conflict_label`
- `conflict_description`
- `source_id`

Ejemplos:

- separación
- abandono
- resistencia
- protección
- identidad

---

## Tabla: `disease_related_systems`

Campos:

- `id`
- `disease_entry_id`
- `system_label`
- `source_id`

Ejemplos:

- digestivo
- respiratorio
- endocrino
- neurosensorial

---

## Tabla: `disease_questions`

Preguntas sugeridas para profundizar.

Campos:

- `id`
- `disease_entry_id`
- `question_text`
- `source_id`
- `question_order`

Uso:

- seguimiento del análisis terapéutico
- apoyo al terapeuta

---

## Tabla: `disease_support_methods`

No como tratamiento médico, sino como rutas terapéuticas dentro del marco de la escuela o de referencias.

Campos:

- `id`
- `disease_entry_id`
- `method_label`
- `method_notes`
- `source_id`

Ejemplos:

- trabajo emocional
- liberación
- rastreo
- recurso energético
- exploración transgeneracional

---

## Tabla: `disease_canonical_profiles`

Esta es la ficha consolidada final por enfermedad.

Campos:

- `id`
- `disease_entry_id`
- `summary`
- `possible_origins_json`
- `related_conflicts_json`
- `related_systems_json`
- `guiding_questions_json`
- `support_methods_json`
- `compiled_from_sources_json`
- `review_status`

### `review_status`

- `auto_compiled`
- `reviewed`
- `approved`

Esta tabla será la que consultará el software en producción.

---

## Flujo de construcción

## Fase 1. Extraer entradas

Desde los textos procesados:

- detectar títulos de enfermedades
- extraer bloques cercanos
- guardar cada bloque como `disease_source_entries`

## Fase 2. Consolidar

Para cada enfermedad:

- unir aliases
- detectar sistemas
- detectar conflictos
- detectar síntomas
- detectar preguntas

## Fase 3. Curar

Revisión manual de:

- duplicados
- conflictos redundantes
- nombres inconsistentes
- ruido OCR

## Fase 4. Aprobar

Construir la ficha canónica:

- resumen claro
- lista de orígenes posibles
- conflictos posibles
- sistemas relacionados
- preguntas guía
- métodos sugeridos

---

## Cómo se usará

## Modo: Dudas sobre cursos

Uso secundario.

Ejemplo:

- usuario pregunta por `migraña`
- el sistema puede complementar con una entrada del diccionario

## Modo: Asistente terapéutico

Uso directo.

Ejemplo:

1. En el formulario aparece `migraña`
2. El sistema busca la ficha canónica de `migraña`
3. Cruza eso con:
   - contexto emocional
   - masa conflictual
   - genograma
   - pares encontrados
4. Integra la orientación

---

## Formato de salida sugerido al terapeuta

Cuando una enfermedad se detecta en el caso:

- `Enfermedad / síntoma`
- `Posibles ejes de fondo`
- `Conflictos asociados`
- `Sistemas implicados`
- `Preguntas para profundizar`
- `Métodos sugeridos dentro del marco terapéutico`

No debe decir:

- diagnóstico definitivo
- verdad única
- causalidad absoluta

Sí debe decir:

- `posibles ejes`
- `posibles causas`
- `líneas a revisar`

---

## Campos mínimos para la primera versión

Si quieres una versión rápida y útil, empieza con:

- `canonical_name`
- `aliases`
- `summary`
- `possible_origins`
- `related_conflicts`
- `related_systems`
- `guiding_questions`
- `support_methods`
- `source_titles`

Eso ya da suficiente valor para una primera app.

---

## Riesgos detectados

### 1. OCR débil

Algunos PDFs extrajeron muy poco texto y pueden requerir OCR externo.

### 2. Solapamiento doctrinal

Varias fuentes pueden decir cosas similares con palabras distintas.

### 3. Ruido

No todo libro tiene formato limpio por enfermedad; algunos son expositivos y no diccionarios puros.

Por eso conviene construir la capa:

- `source entry`
- `canonical profile`

en vez de consultar libros crudos en vivo.

---

## Siguiente paso lógico

Después de este esquema, conviene construir:

1. un extractor de entradas por enfermedad
2. un catálogo inicial de 20-30 enfermedades frecuentes
3. una ficha canónica consolidada por enfermedad
