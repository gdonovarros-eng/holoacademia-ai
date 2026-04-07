# Formulario Terapéutico Definitivo V1

## Fuente real

Esta versión queda corregida **directamente** desde:

- `/Users/m2/Library/Mobile Documents/com~apple~CloudDocs/Formulario registro círculo terapéutico.pptx`

El formulario anterior estaba inferido y no respetaba el archivo original. Este sí.

---

## Estructura general

El PPT contiene **2 bloques**:

1. `Genograma Básico: Abuelos, Progenitores, Pareja(s) y Descendiente(s)`
2. `Historial Clínico Básico: Síntomas Actuales, Recurrentes y Cirugías`

Todo debe ser visible desde el inicio y lo llena el terapeuta durante la entrevista.

---

## Bloque 1. Genograma básico

### 1. Consultante

- `Nombre completo del (a) consultante`
- `Fecha de nacimiento (día / mes / año)`

### 2. Abuelos

#### Abuela materna
- nombre completo
- fecha de nacimiento
- fecha de muerte

#### Abuelo materno
- nombre completo
- fecha de nacimiento
- fecha de muerte

#### Abuela paterna
- nombre completo
- fecha de nacimiento
- fecha de muerte

#### Abuelo paterno
- nombre completo
- fecha de nacimiento
- fecha de muerte

### 3. Progenitores

#### Madre
- nombre completo
- fecha de nacimiento
- fecha de muerte

#### Padre
- nombre completo
- fecha de nacimiento
- fecha de muerte

### 4. Hermanos

El formato trae `5` espacios:

- `Herman@ 1`
- `Herman@ 2`
- `Herman@ 3`
- `Herman@ 4`
- `Herman@ 5`

Cada uno con:
- nombre completo
- fecha de nacimiento

### 5. Parejas

#### Pareja actual
- nombre completo
- fecha de nacimiento
- tiempo de relación

#### Parejas significativas

El formato trae `3` espacios de `Pareja significativa`.

Cada una con:
- nombre
- fecha de nacimiento
- tiempo de relación

### 6. Descendientes

El formato trae `5` espacios para `Hij@`.

Cada uno con:
- nombre completo
- fecha de nacimiento
- fecha de muerte
- nombre completo del progenitor(a)
- tiempo de duración en la relación

---

## Bloque 2. Historial clínico básico

### A. Síntomas actuales a trabajar por orden de intensidad

El formato trae `4` filas.

Cada fila incluye:
- `Síntoma`
- `Edad aproximada de aparición o diagnóstico`
- `Características del síntoma`
- `Frecuencia de síntoma`

### B. Síntomas recurrentes en el pasado, cirugías, etc.

El formato trae `3` filas.

Cada fila incluye:
- `Síntoma`
- `Edad aproximada de aparición o diagnóstico`
- `Características del síntoma`
- `Frecuencia de síntoma`

---

## Modelo de datos sugerido

```json
{
  "consultant": {
    "full_name": "",
    "birth_date": ""
  },
  "grandparents": {
    "maternal_grandmother": { "full_name": "", "birth_date": "", "death_date": "" },
    "maternal_grandfather": { "full_name": "", "birth_date": "", "death_date": "" },
    "paternal_grandmother": { "full_name": "", "birth_date": "", "death_date": "" },
    "paternal_grandfather": { "full_name": "", "birth_date": "", "death_date": "" }
  },
  "parents": {
    "mother": { "full_name": "", "birth_date": "", "death_date": "" },
    "father": { "full_name": "", "birth_date": "", "death_date": "" }
  },
  "siblings": [
    { "full_name": "", "birth_date": "" }
  ],
  "current_partner": {
    "full_name": "",
    "birth_date": "",
    "relationship_duration": ""
  },
  "significant_partners": [
    { "full_name": "", "birth_date": "", "relationship_duration": "" }
  ],
  "children": [
    {
      "full_name": "",
      "birth_date": "",
      "death_date": "",
      "other_parent_name": "",
      "relationship_duration": ""
    }
  ],
  "current_symptoms": [
    {
      "symptom_name": "",
      "onset_age_or_date": "",
      "symptom_characteristics": "",
      "frequency": ""
    }
  ],
  "history_events": [
    {
      "event_name": "",
      "onset_age_or_date": "",
      "event_characteristics": "",
      "frequency": ""
    }
  ]
}
```

---

## Nota importante

Este formulario **no trae** en el PPT original campos como:

- motivo de consulta
- objetivo de la sesión
- emoción principal
- detonante reciente
- observaciones libres
- conflictos familiares escritos como notas abiertas

Si luego quieres añadirlos, deben entrar como una **versión extendida** del formulario, no como si vinieran del archivo original.
