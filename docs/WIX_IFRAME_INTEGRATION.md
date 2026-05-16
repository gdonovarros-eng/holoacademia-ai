# Holoacadem-iA · Integración iframe en Wix

## Arquitectura

```
Usuario (Wix)
    │
    ▼
Página Wix  ──Velo JS──►  currentMember.getMember()  →  uid + plan
    │
    ▼
IFrame  ──src──►  https://holoacademia-ai.onrender.com/?embed=1&uid=...&plan=...&token=...
    │
    ▼
FastAPI middleware valida token → setea cookie holo_sess (7 días)
    │
    ▼
App Holoacadem-iA (menú + herramientas)
```

## Paso 1 — Generar el EMBED_SECRET

En tu terminal local, ejecuta:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Guarda el resultado — lo necesitas en 2 lugares:

---

## Paso 2 — Configurar en Render

En tu servicio de Render → **Environment** → añade:

| Variable | Valor |
|----------|-------|
| `EMBED_SECRET` | El hex que generaste en el paso 1 |
| `LOGIN_URL` | `https://www.holoacademia.com/miembros` (o tu URL de login) |
| `DB_PATH` | `/data/holoacademia.db` (ya configurado en render.yaml) |

Luego haz **Manual Deploy** para que tome los cambios.

---

## Paso 3 — Crear el iframe en Wix

1. Ve a la página donde quieres mostrar Holoacadem-iA
2. **Add** → **Embed & Social** → **Custom Embeds** → **Embed a Site**
3. Ajusta el tamaño del iframe para que ocupe toda la pantalla (aprox 100% ancho, 800–900px alto)
4. En el panel derecho del iframe, pon el ID: `iframeHolo`

> **Alternativa**: Usa un elemento **HTML Embed** si quieres más control.

---

## Paso 4 — Código Velo en la página

Abre el editor Velo de la página (botón `{ }` en la barra lateral) y pega el código de `wix_templates/holoacademia-iframe.js`.

Edita las 3 variables al inicio:

```js
const APP_URL      = 'https://holoacademia-ai.onrender.com';  // tu URL en Render
const EMBED_SECRET = 'PEGA_AQUI_TU_EMBED_SECRET';             // el hex del paso 1
const PLAN_MAP     = { ... };                                   // IDs de tus planes
```

---

## Paso 5 — Obtener los IDs de tus Pricing Plans

En Wix Dashboard → **Pricing Plans** → haz clic en cada plan → copia el ID de la URL:

```
https://manage.wix.com/premium-purchase-flow/dynamo/.../plans/ESTE_ES_EL_ID/edit
```

Añádelos al `PLAN_MAP`:

```js
const PLAN_MAP = {
  'abc123def456': 'elite_pro',
  'xyz789uvw012': 'premium',
  'hij345klm678': 'iniciacion',
};
```

---

## Planes disponibles

| Plan en app | Límite mensual | Nombre visible |
|-------------|---------------|----------------|
| `premium` | 100 sinodal / 50 terapeuta | Secreta / Acceso Premium |
| `elite_pro` | 65 / 35 | Elite Pro |
| `iniciacion` | 30 / 20 | Iniciación Elite |
| `medida` | 10 / 10 | Elite a tu medida |
| `holoconexion` | 3 / 2 | Holoconexión (fallback) |

---

## Cómo funciona la sesión

1. **Primera carga**: Wix construye la URL con `uid`, `plan`, y `token`
2. **FastAPI valida** el token (compare_digest — tiempo constante, anti-timing attack)
3. **Si es válido**: crea/actualiza el usuario en SQLite, emite cookie `holo_sess` (firmada HMAC-SHA256, 7 días)
4. **Navegaciones siguientes**: la cookie ya existe, no se necesita re-validar el token
5. **Sin token ni cookie**: redirect a `LOGIN_URL`

> La cookie es `SameSite=None; Secure; HttpOnly` — necesario para funcionar dentro de un iframe cross-origin.

---

## Rutas protegidas

Todas las siguientes rutas requieren autenticación:

| Ruta | Módulo |
|------|--------|
| `/` | Menú principal Holoacadem-iA |
| `/alumno` | Sinodal IA (tutor diplomado) |
| `/rastreo` | Tablas de rastreo |
| `/pares` | Guía de pares biomagnéticos |
| `/terapeuta` | Asistente terapéutico |
| `/salud` | Astrología Médica |
| `/astro-home` | Astrolog iA (menú premium) |
| `/astro` | Carta Natal & Revolución Solar |
| `/sinastria` | Sinastría |
| `/transitos` | Tránsitos Planetarios |
| `/progresiones` | Progresiones Secundarias |

---

## Verificar que funciona

1. Publica la página en Wix
2. Entra como miembro con plan activo
3. El iframe debe mostrar el menú de Holoacadem-iA
4. En las DevTools del navegador → Application → Cookies → debes ver `holo_sess`

Si el iframe muestra redirect o pantalla en blanco:
- Verifica que `EMBED_SECRET` sea idéntico en Render y en el código Velo
- Verifica que el miembro esté logueado en Wix
- Revisa la consola de Wix Velo para errores

---

## Seguridad

- El `EMBED_SECRET` **nunca va en el frontend de Wix** — Velo lo ejecuta del lado del servidor (web module). Pero si lo pones en el código de página (frontend), estará visible en el HTML. Para máxima seguridad, mueve la construcción de la URL a un **Web Module** (`src/backend/`) de Wix.

### Versión segura con Web Module

Crea `src/backend/holoAuth.web.js` en Wix:

```js
import { Permissions, webMethod } from 'wix-web-module';
import { currentMember } from 'wix-members-backend';

const APP_URL      = 'https://holoacademia-ai.onrender.com';
const EMBED_SECRET = 'TU_SECRETO_AQUI';  // seguro en backend
const PLAN_MAP     = { /* ... */ };

export const getEmbedUrl = webMethod(
  Permissions.Member,
  async (path = '/') => {
    const member = await currentMember.getMember();
    const uid    = member?._id || 'guest';
    const plan   = PLAN_MAP['TU_PLAN_ID'] || 'holoconexion';
    const params = new URLSearchParams({ embed: '1', uid, plan, token: EMBED_SECRET });
    return `${APP_URL}${path}?${params}`;
  }
);
```

Y en el código de página:

```js
import { getEmbedUrl } from 'backend/holoAuth.web';

$w.onReady(async () => {
  const url = await getEmbedUrl('/');
  $w('#iframeHolo').src = url;
});
```
