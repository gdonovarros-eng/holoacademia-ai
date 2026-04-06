# API Terapéutica V1

## Objetivo

Exponer el flujo terapéutico ya construido como endpoints reales para una app propia o un `iframe` embebido en Wix.

---

## Endpoints

### `POST /therapy/analyze`

Entrada:

- `case_payload`

Salida:

- análisis inicial del caso
- síntomas prioritarios
- sistemas probables
- conflictos probables
- ejes familiares/transgeneracionales
- preguntas guía
- rutas sugeridas

---

### `POST /therapy/pairs`

Entrada:

- `case_payload`
- `pairs`

Salida:

- interpretación de pares
- tipos dominantes
- condiciones relacionadas
- lectura integrada
- protocolos sugeridos
- visuales por par

---

### `POST /therapy/report`

Entrada:

- `case_payload`
- `pairs`

Salida:

- reporte terapéutico final
- resumen para terapeuta
- cuadro integrador
- protocolo principal
- resumen para paciente
- visuales por par

---

## Estructura mínima de `case_payload`

Campos relevantes:

- `patient_name`
- `patient_birth_date`
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

El modelo acepta además campos extra para no bloquear la evolución del formulario.

---

## Estructura mínima de `pairs`

Lista de objetos con:

- `pair_name`
- `therapist_note` opcional

Ejemplo:

```json
[
  {"pair_name": "ANO - PILORO"},
  {"pair_name": "ADUCTOR MENOR - ADUCTOR MENOR"}
]
```

---

## Uso sugerido en interfaz

### Pantalla 1: formulario

1. capturar formulario
2. llamar `POST /therapy/analyze`
3. mostrar lectura inicial

### Pantalla 2: pares

1. capturar pares encontrados
2. llamar `POST /therapy/pairs`
3. mostrar interpretación + visuales

### Pantalla 3: cierre

1. llamar `POST /therapy/report`
2. mostrar reporte final, cuadro integrador y protocolo
