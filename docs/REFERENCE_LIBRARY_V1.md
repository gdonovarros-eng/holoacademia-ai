# Biblioteca de Referencia V1

## Objetivo

Separar los libros y PDFs de referencia de los cursos oficiales.

Esta biblioteca no debe mezclarse doctrinalmente con los cursos. Debe funcionar como:

- apoyo analítico
- diccionario ampliado
- contexto complementario

## Jerarquía propuesta

1. Cursos y manuales de Holoacademia
2. Diccionarios y libros de referencia
3. Material complementario

Cuando exista tensión entre fuentes, el sistema debe priorizar primero la enseñanza derivada de los cursos.

---

## Entrada esperada

Ruta:

- [data/reference_library](/Users/m2/Documents/New%20project/data/reference_library)

Tipos de archivo aceptados inicialmente:

- PDF
- TXT
- MD
- CSV

---

## Salida procesada

Ruta recomendada:

- [data/reference_processed](/Users/m2/Documents/New%20project/data/reference_processed)

Contenido:

- `catalog.json`
- `summary.json`
- `texts/<category>/*.txt`

---

## Categorías iniciales

### `disease_dictionary`

Para:

- diccionarios de biodescodificación
- diccionarios de psicodescodificación
- orígenes emocionales de enfermedades
- referencias dentales cuando se relacionan a conflicto

Uso:

- consulta por enfermedad
- posibles significados
- síntomas asociados
- conflictos vinculados

### `transgenerational`

Para:

- ancestros
- yaciente
- vínculos familiares
- constelaciones familiares
- órdenes del amor

Uso:

- análisis del genograma
- patrones repetitivos
- secretos
- injusticias
- lealtades invisibles

### `trauma_emotion_release`

Para:

- tapping
- trauma
- emoción
- corte de cordones

Uso:

- liberación
- estrategias emocionales
- recursos complementarios

### `belief_consciousness`

Para:

- biología de la creencia
- memoria celular
- observador
- conciencia

Uso:

- explicación complementaria
- marcos interpretativos adicionales

### `complementary_misc`

Para:

- tarot
- grabovoi
- referencias no nucleares

Uso:

- apoyo opcional
- nunca como primera capa analítica

### `uncategorized`

Para archivos aún no clasificados.

---

## Script de procesamiento

Se agregó:

- [scripts/process_reference_library.py](/Users/m2/Documents/New%20project/scripts/process_reference_library.py)

### Qué hace

1. Recorre la carpeta de referencia
2. Clasifica cada archivo por nombre
3. Extrae el texto
4. Genera un catálogo procesado

### Uso recomendado

```bash
./.venv/bin/python scripts/process_reference_library.py \
  data/reference_library \
  data/reference_processed \
  --clean
```

---

## Cómo se integrará al sistema

### Dudas sobre cursos

No debe responder principalmente desde esta biblioteca.

La biblioteca de referencia solo sirve para:

- ampliar una explicación
- enriquecer un concepto
- consultar diccionarios específicos cuando el usuario pregunte por enfermedad o conflicto

### Asistente terapéutico

Sí debe apoyarse en esta biblioteca para:

- consultar diccionario de enfermedades
- enriquecer posibles significados
- ampliar ejes transgeneracionales
- apoyar liberación emocional

Pero la secuencia debe seguir siendo:

1. curso/manual
2. referencia
3. integración del caso

---

## Próximo paso lógico

Después de procesar esta biblioteca, conviene construir:

1. un catálogo normalizado de enfermedades
2. un catálogo normalizado de entradas transgeneracionales
3. reglas de uso por módulo del sistema
