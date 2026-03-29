# Integracion Wix -> API externa

## Idea general

1. Wix muestra la pagina del alumno.
2. El frontend de Wix llama a un web module.
3. El web module llama a la API externa.
4. La API externa responde con `answer`, `visual` y `sources`.
5. Wix puede reenviar historial para que el asistente mantenga contexto.
5. Wix muestra la respuesta.

## Requisito importante

La API externa debe tener una URL publica con `https`.

Esto significa que `http://127.0.0.1:8000` no sirve directamente desde Wix.

Opciones:

- Publicar la API en un servidor.
- Usar un tunel HTTPS temporal para pruebas.

## Archivos plantilla

- `wix_templates/aiApi.web.js`
- `wix_templates/asistente-page.js`

## Que pegar en Wix

### Backend

Crear `src/backend/aiApi.web.js` y pegar el contenido de:

- `wix_templates/aiApi.web.js`

Luego cambiar:

```js
const API_BASE_URL = 'https://TU-API-PUBLICA.com';
```

por la URL real de la API.

### Pagina

En la pagina `Asistente IA`, reemplazar el codigo por el contenido de:

- `wix_templates/asistente-page.js`

Este ejemplo usa los IDs actuales:

- `#input1`
- `#button36`
- `#text1094`

Si cambian en Wix, hay que actualizar ese archivo.

## Nota sobre la experiencia

La respuesta principal ya sale en tono natural.

Si la API devuelve `visual`, puedes:

- anexarla debajo de la respuesta en el mismo texto
- mostrarla en un segundo bloque visual
- convertirla despues en tarjetas, acordeon o mapa mas elaborado
- si `visual.format === 'mermaid'`, renderizarla como diagrama
- si `visual.format === 'image_prompt'`, usarla para generar una imagen en un paso posterior
- si `visual.image_data_url` viene lleno, puedes mostrarla directamente en un widget de imagen de Wix
