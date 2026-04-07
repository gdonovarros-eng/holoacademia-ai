# Formulario Terapéutico Definitivo V1

## Versión operativa aprobada

Este formulario sigue la estructura definida directamente por operación, no una reconstrucción libre.

Debe verse y capturarse así:

---

## 1. Información del consultante

- `Nombre completo`
- `Fecha de nacimiento`
- `Hora de nacimiento`
- `Edad`

La edad debe calcularse automáticamente a partir de la fecha de nacimiento.

---

## 2. Genograma básico

### Padre
- `Nombre del Padre`
- `Fecha de Nacimiento`
- `Fecha de Muerte`

### Abuelo paterno
- `Nombre del Abuelo Paterno`
- `Fecha de Nacimiento`
- `Fecha de Muerte`

### Abuela paterna
- `Nombre de la Abuela Paterna`
- `Fecha de Nacimiento`
- `Fecha de Muerte`

### Madre
- `Nombre de la Madre`
- `Fecha de Nacimiento`
- `Fecha de Muerte`

### Abuelo materno
- `Nombre del Abuelo Materno`
- `Fecha de Nacimiento`
- `Fecha de Muerte`

### Abuela materna
- `Nombre de la Abuela Materna`
- `Fecha de Nacimiento`
- `Fecha de Muerte`

---

## 3. Pareja actual

- `Nombre Completo`
- `Fecha de Nacimiento`
- `Años de relación`

---

## 4. Más parejas significativas

Debe iniciar vacío.

Pregunta operativa:
- `¿Hay más parejas significativas?`

Si sí:
- botón `Agregar`

Cada pareja agregada incluye:
- `Nombre completo`
- `Fecha de nacimiento`
- `Años de relación`

Se repite hasta que ya no agreguen más.

---

## 5. Hijos

Debe poder agregarse dinámicamente.

Cada hijo incluye:
- `Nombre completo`
- `Fecha de nacimiento`
- `Fecha de muerte`
- `Nombre del padre o madre`
- `Fecha de nacimiento`
- `Fecha de muerte`
- `Tiempo de relación en años`

Debe haber botón:
- `Agregar hijo`

---

## 6. Hermanos

Cada hermano incluye:
- `Nombre completo`
- `Fecha de nacimiento`
- `Fecha de muerte`

Debe haber botón:
- `Agregar hermano`

---

## 7. Historial clínico básico

### Síntomas a trabajar por orden de intensidad

Cada síntoma incluye:
- `Síntoma`
- `Edad aproximada de aparición o diagnóstico`
- `Características del síntoma`
- `Frecuencia de síntoma`

Debe haber botón:
- `Agregar síntoma`

### Síntomas recurrentes del pasado como cirugías

Cada síntoma incluye:
- `Síntoma`
- `Edad aproximada de aparición o diagnóstico`
- `Características del síntoma`
- `Frecuencia de síntoma`

Debe haber botón:
- `Agregar síntoma`

---

## Modelo de datos sugerido

```json
{
  "consultant": {
    "full_name": "",
    "birth_date": "",
    "birth_time": "",
    "age": ""
  },
  "parents": {
    "father": {
      "full_name": "",
      "birth_date": "",
      "death_date": ""
    },
    "mother": {
      "full_name": "",
      "birth_date": "",
      "death_date": ""
    }
  },
  "grandparents": {
    "paternal_grandfather": {
      "full_name": "",
      "birth_date": "",
      "death_date": ""
    },
    "paternal_grandmother": {
      "full_name": "",
      "birth_date": "",
      "death_date": ""
    },
    "maternal_grandfather": {
      "full_name": "",
      "birth_date": "",
      "death_date": ""
    },
    "maternal_grandmother": {
      "full_name": "",
      "birth_date": "",
      "death_date": ""
    }
  },
  "current_partner": {
    "full_name": "",
    "birth_date": "",
    "relationship_years": ""
  },
  "significant_partners": [],
  "children": [],
  "siblings": [],
  "current_symptoms": [],
  "history_events": []
}
```
