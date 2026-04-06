# Motor De Interpretación De Pares V1

## Archivo

- [api/pair_engine.py](/Users/m2/Documents/New%20project/api/pair_engine.py)

## Objetivo

Tomar:

1. el análisis inicial del caso
2. la lista de pares encontrados por el terapeuta

y devolver:

- interpretación de cada par
- tipos de pares dominantes
- condiciones relacionadas
- lectura integrada
- protocolos sugeridos

---

## Entrada esperada

### `case_analysis`

Salida previa de:

- [api/therapy_engine.py](/Users/m2/Documents/New%20project/api/therapy_engine.py)

### `pairs_input`

Lista de pares capturados por el terapeuta.

Puede ser:

- lista de strings
- lista de objetos con `pair_name`

Ejemplos:

- `["ANO - PILORO", "ADUCTOR MENOR - ADUCTOR MENOR"]`
- `[{"pair_name": "ANO - PILORO"}]`

---

## Qué hace

1. busca cada par en el catálogo de pares
2. recupera:
   - tipo de par
   - condición relacionada
   - fuente
3. integra esa información con:
   - sistemas probables
   - conflictos probables
   - ejes familiares
   - rutas de liberación
4. sugiere protocolos congruentes con el análisis

---

## Salida

Devuelve:

- `pairs_count`
- `interpreted_pairs`
- `dominant_pair_types`
- `related_conditions`
- `probable_systems`
- `probable_conflicts`
- `family_axes`
- `integrated_reading`
- `suggested_protocols`

---

## Cómo sugiere protocolos

Usa una tabla inicial de relación entre rutas y protocolos:

- `estres_postraumatico_si_aplica`
- `sistemico`
- `transgeneracional`
- `transgeneracional_si_aplica`
- `sentimental_si_aplica`

Y la cruza con el catálogo real de protocolos disponible en:

- [data/teacher_knowledge_cache.json](/Users/m2/Documents/New%20project/data/teacher_knowledge_cache.json)

---

## Limitaciones actuales

- la interpretación integrada todavía es una síntesis estructurada básica
- no pondera intensidad clínica entre pares
- no detecta aún patrones avanzados entre pares emocionales, reservorios y especiales
- no elige todavía un único protocolo final, sino una lista sugerida

---

## Próximo paso técnico

Construir la fase que una:

- análisis inicial del formulario
- interpretación de pares
- selección final del protocolo
- reporte final para el terapeuta
