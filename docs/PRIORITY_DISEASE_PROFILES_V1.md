# Perfiles Prioritarios De Enfermedad V1

## Objetivo

Definir una primera capa curada de padecimientos y síntomas útiles para el asistente terapéutico.

No conviene empezar con todo el diccionario completo. Conviene empezar con una selección limpia, frecuente y accionable.

Archivo base:

- [data/reference_processed/disease_profiles_priority_v1.json](/Users/m2/Documents/New%20project/data/reference_processed/disease_profiles_priority_v1.json)

---

## Criterios de selección

Se incluyeron primero perfiles que:

- aparecen con frecuencia en consulta
- tienen alta conexión con síntomas reportables por el paciente
- tienen utilidad clara para entrevista terapéutica
- se conectan bien con sistemas, conflictos y pares

Se excluyeron por ahora:

- ruido OCR
- entradas de cromoterapia
- categorías demasiado ajenas al flujo terapéutico principal
- entradas que requieren mucha validación doctrinal antes de usarse

---

## Grupos iniciales

### Respiratorio

- Asma
- Bronquitis crónica
- Sinusitis
- Resfriado común
- Amigdalitis

### Digestivo

- Gastritis
- Acidez estomacal
- Reflujo gastroesofágico (ERGE)
- Colitis ulcerosa
- Síndrome del intestino irritable (SII)
- Diverticulitis
- Pancreatitis
- Cálculos biliares

### Endocrino / metabólico

- Diabetes
- Hipoglucemia
- Hipertiroidismo
- Síndrome de ovario poliquístico (SOP)
- Obesidad

### Neurosensorial

- Migraña
- Vértigo
- Parálisis facial
- Glaucoma
- Cataratas

### Dermatológico

- Dermatitis
- Urticaria

### Osteomuscular

- Fibromialgia
- Columna vertebral
- Cuello o tortícolis
- Escoliosis
- Artritis reumatoide
- Osteoporosis

### Emocional / mental

- Ansiedad
- Depresión
- Insomnio
- Trastorno bipolar
- Trastorno obsesivo compulsivo (TOC)
- Bulimia nerviosa

---

## Niveles de prioridad

### `alta`

Debe integrarse primero al análisis terapéutico.

### `media`

Puede entrar en la segunda ronda de curación manual.

### `baja`

Se mantiene visible, pero no debe ser de las primeras entradas activas del sistema.

---

## Uso recomendado

En el análisis del formulario:

1. detectar síntomas escritos por el terapeuta
2. cruzarlos contra esta lista prioritaria
3. recuperar la ficha canónica correspondiente
4. enriquecer la lectura del caso

---

## Próximo paso lógico

Construir un archivo curado final por perfil, agregando:

- sistemas verificados
- conflictos asociados
- preguntas guía
- métodos sugeridos
- relación con protocolos de liberación
