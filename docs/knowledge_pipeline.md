# Holoacademia AI – Knowledge Pipeline

## 🎯 Objetivo

Convertir cursos en una base estructurada usable por IA.

---

## 📚 Estructura por curso

Cada curso se organiza en:

### Académico

- `concepts.json`
- `glossary.json`
- `module_summaries.json`
- `faq_candidates.json`

### Terapéutico

- `intake_questions.json`
- `reasoning_patterns.json`
- `interpretation_guides.json`
- `therapeutic_observations.json`
- `clinical_warnings.json`

### Protocolos

- `protocols.json`

---

## 🔄 Flujo de procesamiento

1. Transcripción del curso
2. Limpieza de contenido
3. Separación por capas:
   - académico
   - terapéutico
   - protocolos
4. Estructuración en JSON
5. Enriquecimiento:
   - aliases
   - relaciones
   - claridad
6. Validación
7. Uso en motores

---

## 🧠 Principios

- no inventar contenido
- priorizar claridad sobre volumen
- separar conocimiento por función
- mantener trazabilidad

---

## ⚠️ Consideraciones

- no todo debe ser concept
- listas viven mejor en `module_summaries.json`
- procesos viven mejor en protocolos
- razonamiento vive en la capa terapéutica

---

## 🚀 Escalabilidad

Para agregar un nuevo curso:

1. crear carpeta en `/data/knowledge_units`
2. seguir misma estructura
3. validar archivos
4. conectar automáticamente a motores
