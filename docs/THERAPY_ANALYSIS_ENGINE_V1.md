# Motor De Análisis Terapéutico V1

## Archivo

- [api/therapy_engine.py](/Users/m2/Documents/New%20project/api/therapy_engine.py)

## Objetivo

Tomar el formulario del caso y devolver una lectura inicial estructurada antes del rastreo de pares.

No diagnostica médicamente.
No sustituye criterio humano.
Sí organiza el caso desde el marco terapéutico definido.

---

## Entrada esperada

Un objeto `case_payload` con campos del formulario terapéutico, especialmente:

- `consultation_reason`
- `session_goal`
- `main_emotion`
- `recent_trigger`
- `current_emotional_context`
- `emotional_context_at_onset`
- `what_bothers_today`
- `perceived_impediments`
- `family_conflicts_notes`
- `family_secrets_notes`
- `transgenerational_patterns_notes`
- `important_relationships_notes`
- `free_case_notes`
- `current_symptoms`
- `history_events`

---

## Qué hace

1. reúne texto relevante del caso
2. detecta coincidencias con los perfiles curados de enfermedad
3. propone sistemas probables
4. propone conflictos probables
5. detecta ejes familiares o transgeneracionales
6. arma preguntas guía
7. sugiere rutas de rastreo y liberación

---

## Salida

Devuelve un objeto con:

- `reading`
- `priority_symptoms`
- `matched_profiles`
- `probable_systems`
- `probable_conflicts`
- `family_axes`
- `mass_conflict_hypothesis`
- `guiding_questions`
- `suggested_course_routes`
- `release_protocol_routes`

---

## Sentido en el flujo general

### Antes del rastreo

Este motor responde:

- qué parece importante
- qué sistema mirar primero
- qué conflicto podría estar dominando
- qué preguntas faltan

### Después del rastreo

La siguiente fase será:

- leer pares
- integrarlos con esta salida
- proponer protocolo de liberación

---

## Limitaciones actuales

- usa matching textual y heurístico, no razonamiento profundo
- depende de los perfiles curados iniciales
- todavía no integra el catálogo de pares
- todavía no selecciona un protocolo concreto por sí solo

---

## Próximo paso técnico

Construir:

1. el motor de interpretación de pares
2. la unión entre análisis inicial + pares + protocolo
