# Despliegue en Render

Esta es la ruta recomendada para que el asistente funcione sin depender de tu computadora.

## 1. Subir el proyecto a GitHub

Desde la raíz del proyecto:

```bash
cd "/Users/m2/Documents/New project"
git init
git add .
git commit -m "Initial Holoacademia AI backend"
```

Luego crea un repositorio vacío en GitHub y conecta el remoto:

```bash
git remote add origin TU_URL_DE_GITHUB
git branch -M main
git push -u origin main
```

## 2. Crear el servicio en Render

1. Entra a Render.
2. Crea un nuevo servicio desde tu repositorio.
3. Render detectará automáticamente [render.yaml](/Users/m2/Documents/New%20project/render.yaml).
4. Configura la variable secreta:

```bash
OPENAI_API_KEY=tu_clave_real
```

5. Lanza el deploy.

## 3. Verificar el backend

Cuando Render termine, abre:

```text
https://TU-SERVICIO.onrender.com/health
```

Debe mostrar:

- `llm_enabled: true`
- `model: gpt-5`
- `teacher_memory_ready: true`
- `semantic_index_ready: true`

## 4. Conectar Wix

En tu backend de Wix, cambia la URL base:

```js
const API_BASE_URL = 'https://TU-SERVICIO.onrender.com';
```

Luego publica otra vez el sitio.

## 5. Resultado esperado

Con esto:

- ya no dependes de tu Mac
- ya no dependes de `cloudflared`
- ya no cambian las URLs
- Wix siempre hablará con un backend estable
