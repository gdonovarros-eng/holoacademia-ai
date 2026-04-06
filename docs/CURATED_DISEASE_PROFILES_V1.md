# Perfiles De Enfermedad Curados V1

## Objetivo

Pasar de un diccionario general de enfermedades a una capa realmente útil para el asistente terapéutico.

Archivo:

- [data/reference_processed/disease_profiles_curated_v1.json](/Users/m2/Documents/New%20project/data/reference_processed/disease_profiles_curated_v1.json)

---

## Qué contiene

Cada perfil ya incluye:

- `canonical_name`
- `slug`
- `system_name`
- `priority_group`
- `orientation_summary`
- `possible_conflicts`
- `guiding_questions`
- `suggested_course_routes`
- `release_protocol_routes`
- `sources_basis`

---

## Propósito

Esta capa no responde sola al usuario.

Sirve para alimentar:

1. el análisis inicial del caso
2. la lectura previa al rastreo
3. la interpretación posterior de pares
4. la sugerencia de protocolo

---

## Perfiles incluidos en esta primera capa

- Asma
- Gastritis
- Reflujo gastroesofágico (ERGE)
- Colitis ulcerosa
- Diabetes
- Migraña
- Fibromialgia
- Ansiedad
- Depresión
- Insomnio

---

## Cómo se usarán

### Paso 1

El terapeuta llena el formulario.

### Paso 2

El motor detecta síntomas o padecimientos mencionados.

### Paso 3

Cruza esos términos contra esta capa curada.

### Paso 4

Construye:

- sistemas probables
- conflictos probables
- preguntas guía
- rutas sugeridas

### Paso 5

Después del rastreo, la interpretación de pares usa esta misma capa como apoyo contextual.

---

## Qué no hace todavía

Todavía no:

- consolida automáticamente múltiples perfiles en una sola lectura de caso
- selecciona protocolo final automáticamente
- conecta par por par con enfermedad

Esa será la siguiente fase.

---

## Siguiente paso técnico

Hay dos opciones lógicas:

1. construir el motor de **análisis inicial del formulario**
2. construir el catálogo de **interpretación de pares**

Mi recomendación:

Primero construir el análisis inicial del formulario, porque de ahí parte todo el resto del flujo.
