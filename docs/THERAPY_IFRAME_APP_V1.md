# App Terapéutica Embebible V1

## URL

La interfaz se sirve desde:

- `/therapy/app`

En producción, por ejemplo:

- `https://tu-backend.onrender.com/therapy/app`

---

## Archivos

- [api/static/therapy.html](/Users/m2/Documents/New%20project/api/static/therapy.html)
- [api/static/therapy.css](/Users/m2/Documents/New%20project/api/static/therapy.css)
- [api/static/therapy.js](/Users/m2/Documents/New%20project/api/static/therapy.js)

---

## Qué incluye

### Módulo 1

`Asistente terapéutico`

Con flujo en tres pasos:

1. Entrevista
2. Pares
3. Reporte

### Módulo 2

`Dudas sobre cursos`

Con caja de pregunta libre conectada a `/ask`.

---

## Endpoints usados por la interfaz

- `POST /therapy/analyze`
- `POST /therapy/pairs`
- `POST /therapy/report`
- `POST /ask`

---

## Embebido en Wix

La forma más simple es usar un `iframe` o un elemento HTML embebido apuntando a:

```text
https://tu-backend.onrender.com/therapy/app
```

---

## Estado actual

La app ya permite:

- capturar formulario terapéutico
- analizar el caso
- capturar pares
- ver interpretación de pares
- ver láminas anatómicas del manual
- construir el reporte final

Todavía no incluye:

- autenticación
- guardado persistente por paciente
- exportación a PDF
- edición histórica de casos
