# Holoacademia AI – Frontend Integration

## 🎯 Objetivo

Definir cómo el frontend interactúa con los 3 motores.

---

## 🧩 Entradas principales

### 1. Asistente Académico

Endpoint: `POST /academic/ask`

Uso:

- preguntas del curso
- dudas conceptuales

Input:

```json
{
  "query": "¿Qué es un par biomagnético?"
}
```

---

### 2. Asistente Terapéutico

Endpoint: `POST /therapeutic/analyze`

Uso:

- análisis de casos
- guía al terapeuta

Input:

```json
{
  "motivo_consulta": "...",
  "sintomas": [],
  "pregunta_del_terapeuta": "..."
}
```

---

### 3. Guía de Protocolos

Endpoint: `POST /protocols/guide`

Uso:

- ejecución paso a paso
- selección de protocolo

Input:

```json
{
  "protocol_name": "Entrevista inicial de rastreo"
}
```

---

## 🔁 Flujo recomendado UI

Usuario selecciona modo:

- 📘 Aprender → Asistente Académico
- 🧠 Analizar caso → Asistente Terapéutico
- 🛠 Ejecutar protocolo → Guía de Protocolos

---

## ⚠️ Manejo de respuestas

### confidence

- `high` → confiable
- `medium` → interpretar con criterio
- `low` → falta información

### used_fallback

- `true` → respuesta básica
- `false` → respuesta completa

---

## 🧠 UX recomendada

- mostrar respuestas limpias
- permitir follow-ups
- no mostrar trazas técnicas al usuario
- usar warnings como apoyo, no como alarma

---

# UI v1 – Implementación actual

## 1. Estructura general

La UI actual vive en tres archivos principales:

- `api/static/therapy.html`
- `api/static/therapy.js`
- `api/static/therapy.css`

La implementación es una interfaz simple basada en pestañas. No hay un frontend separado ni un framework adicional para esta versión: FastAPI sirve directamente el HTML, el JS y el CSS.

---

## 2. Vistas disponibles

### Asistente Académico

- input principal: `query`
- endpoint: `POST /academic/ask`
- output visible:
  - `answer`
  - `confidence`
  - `suggested_followups`

### Asistente Terapéutico

- inputs principales:
  - `motivo_consulta`
  - `sintomas`
  - `inicio`
  - `contexto_emocional`
  - `pregunta_del_terapeuta`
- endpoint: `POST /therapeutic/analyze`
- output visible:
  - `answer`
  - `missing_data`
  - `priority_questions`
  - `possible_lines`
  - `warnings`

### Guía de Protocolos

- input principal:
  - `protocol_name` o `protocol_id`
- endpoint: `POST /protocols/guide`
- output visible:
  - datos del protocolo
  - objetivo
  - descripción
  - cuándo usarlo
  - prerequisitos
  - pasos estructurados
  - advertencias

---

## 3. Flujo de interacción

El flujo actual es directo:

1. el usuario selecciona una pestaña
2. llena el input o formulario mínimo de esa vista
3. presiona el botón principal
4. la UI muestra un estado de carga
5. `therapy.js` hace `fetch` al endpoint correspondiente
6. la respuesta se renderiza en la misma vista

---

## 4. Helpers principales (JS)

Las funciones principales en `api/static/therapy.js` son:

- `postJson`
  - hace el `fetch` con JSON y normaliza errores de red o backend
- `runViewRequest`
  - centraliza loading + ejecución + manejo de error por vista
- `setStatus`
  - muestra estados simples de loading o error en la UI
- `submitAcademic`
  - conecta la vista académica con `POST /academic/ask`
- `submitTherapeutic`
  - conecta la vista terapéutica con `POST /therapeutic/analyze`
- `submitProtocols`
  - conecta la vista de protocolos con `POST /protocols/guide`

---

## 5. Render de respuestas

La UI actual muestra cada motor de forma distinta:

- académico:
  - respuesta en texto
  - confianza
  - sugerencias de follow-up
- terapéutico:
  - lectura inicial
  - listas de datos faltantes
  - preguntas prioritarias
  - líneas posibles
  - advertencias
- protocolos:
  - presentación estructurada del protocolo
  - pasos numerados
  - qué observar
  - qué registrar
  - advertencias

---

## 6. Estados

La UI contempla estos estados:

- `loading`
  - aparece mientras se espera respuesta del endpoint
- `error`
  - muestra un mensaje simple y limpio
- `empty`
  - se usa cuando todavía no hay conversación o resultado
- `found = false`
  - en protocolos, muestra una respuesta prudente cuando no se encuentra el protocolo

---

## 7. Decisiones de diseño

La UI v1 sigue estas decisiones:

- no mostrar trazas técnicas al usuario
- mantener respuestas limpias y legibles
- separar claramente los 3 motores
- preferir simplicidad y estabilidad sobre complejidad visual

---

## 8. Limitaciones actuales

La versión actual todavía tiene límites claros:

- no hay historial conversacional real entre sesiones
- no hay selección de curso desde la UI
- no hay memoria de usuario
- la interfaz es simple y todavía no está optimizada para una UX más avanzada

---

## 9. Próximos pasos

Posibles mejoras futuras:

- mejorar UX visual por vista
- añadir historial conversacional
- añadir selección de curso
- integrar mejor estados, ayudas y navegación contextual

---

## 🚀 Futuro

- historial conversacional
- selección de curso
- combinación de motores
