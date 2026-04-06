# Reporte Terapéutico Final V1

## Archivo

- [api/therapy_report_engine.py](/Users/m2/Documents/New%20project/api/therapy_report_engine.py)

## Objetivo

Unir en una sola salida:

1. el análisis inicial del formulario
2. la interpretación de pares biomagnéticos
3. el cuadro integrador del caso
4. el protocolo principal sugerido
5. la entrega resumida para el paciente

---

## Entrada

### `case_payload`

Formulario terapéutico ya llenado por el terapeuta en entrevista.

### `pairs_input`

Lista de pares encontrados durante el rastreo.

Puede venir vacía en una primera versión del reporte.

---

## Qué hace

1. ejecuta el análisis inicial del caso
2. interpreta los pares capturados
3. selecciona un protocolo principal sugerido
4. construye un cuadro integrador
5. arma una salida separada para:
   - terapeuta
   - paciente

---

## Salida

Devuelve un objeto con estos bloques:

- `case_analysis`
- `pair_analysis`
- `therapist_summary`
- `integrative_chart`
- `pair_visual_summary`
- `primary_protocol`
- `next_steps`
- `patient_delivery`

---

## Criterio de selección del protocolo

La lógica actual prioriza:

1. protocolos transgeneracionales si el caso apunta fuerte a esa línea
2. protocolos de trauma/estrés postraumático si el conflicto lo sugiere
3. protocolos sentimentales si el caso está cargado en vínculos
4. protocolo sistémico como base general

Si nada de eso discrimina con fuerza, toma el primer protocolo congruente sugerido por el análisis previo.

---

## Cuadro integrador

El cuadro mezcla:

- sistemas probables
- conflictos probables
- pares encontrados
- significado breve de cada par

La idea es que el terapeuta vea la lectura del caso en una sola tabla breve, no solo en párrafos largos.

---

## Visuales de pares

La salida `pair_visual_summary` agrega para cada par:

- nombre del par
- tipo de par
- condición relacionada
- punto A y su región
- punto B y su región
- imágenes candidatas del atlas/manual

Esto permite que la futura interfaz muestre junto a cada par:

- su interpretación
- la referencia anatómica real
- y la lámina regional correspondiente

---

## Entrega al paciente

La salida `patient_delivery` no es una explicación doctrinal extensa.

Está pensada para devolver:

- resumen breve del foco terapéutico
- puntos principales a trabajar
- protocolo sugerido
- cuerpo del protocolo

Luego se puede convertir a:

- ficha imprimible
- resumen en PDF
- pantalla de cierre

---

## Próximo paso

Conectar este motor a:

1. la futura interfaz del formulario terapéutico
2. la captura de rastreo de pares
3. la pantalla final del reporte
