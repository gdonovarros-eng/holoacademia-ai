# Holoacademia AI – Architecture Overview

## 🧠 Visión general

El sistema está compuesto por 3 motores principales, cada uno con un propósito distinto:

| Motor | Endpoint | Función |
|------|--------|--------|
| Asistente Académico | `POST /academic/ask` | Responder dudas de contenido |
| Asistente Terapéutico | `POST /therapeutic/analyze` | Analizar casos clínicos |
| Guía de Protocolos | `POST /protocols/guide` | Guiar ejecución de protocolos |

---

## 🔵 Asistente Académico

- Basado en recuperación estructurada de conocimiento académico
- Usa principalmente:
  - `concepts.json`
  - `glossary.json`
  - `module_summaries.json`
- Enfocado en:
  - explicación
  - enseñanza
  - claridad

---

## 🟣 Asistente Terapéutico

- Basado en razonamiento estructurado
- Usa principalmente:
  - `intake_questions.json`
  - `reasoning_patterns.json`
  - `interpretation_guides.json`
  - `clinical_warnings.json`
- Enfocado en:
  - análisis del caso
  - preguntas útiles
  - interpretación prudente

---

## 🟡 Guía de Protocolos

- Basado en estructura operativa
- Usa principalmente:
  - `protocols.json`
- Enfocado en:
  - ejecución paso a paso
  - guía clara
  - soporte práctico

---

## 🔗 Flujo general

Usuario → Interfaz → Endpoint → Motor → Respuesta estructurada

---

## 🧩 Principios de diseño

- separación clara de responsabilidades
- no mezclar académico con terapéutico
- no inventar información
- trazabilidad interna
- respuestas prudentes

---

## 📦 Ubicación clave

- API: `/api`
- Motores: `/Motor academico` y `/Motor terapeutico`
- Data: `/data/knowledge_units`
- Docs: `/docs`
