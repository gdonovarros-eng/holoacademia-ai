/**
 * HOLOACADEM-iA · Integración iframe en Wix (Velo)
 * ═══════════════════════════════════════════════════
 *
 * Pega este código en la página de Wix que contiene el iframe de Holoacadem-iA.
 * El iframe debe ser un elemento HTML Embed o un elemento IFrame con ID #iframeHolo
 *
 * REQUISITOS PREVIOS:
 *  1. En Render → Environment vars: EMBED_SECRET = (secreto que tú generas)
 *  2. Aquí abajo: EMBED_SECRET debe ser el mismo valor
 *  3. El elemento iframe en Wix debe tener ID: #iframeHolo
 *  4. Wix Members debe estar activado (para leer el UID del miembro)
 *
 * PLANES VÁLIDOS (deben coincidir exactamente con lo configurado en Render):
 *   "premium"      → Secreta / Acceso Premium  (100 sinodal / 50 terapeuta)
 *   "elite_pro"    → Elite Pro                 (65 / 35)
 *   "iniciacion"   → Iniciación Elite          (30 / 20)
 *   "medida"       → Elite a tu medida         (10 / 10)
 *   "holoconexion" → Holoconexión              (3 / 2) ← fallback
 *
 * CÓMO LEER EL PLAN DEL MIEMBRO:
 *   Opción A (recomendada): Wix Pricing Plans — el plan del pedido activo
 *   Opción B: Campo custom en el perfil del miembro (Member Badges, custom field)
 *   Opción C: Hardcoded temporal para pruebas
 *
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { currentMember } from 'wix-members';
import wixWindowFrontend from 'wix-window-frontend';

// ── CONFIGURACIÓN (EDITAR ANTES DE PUBLICAR) ──────────────────────────────────

/** URL de tu app en Render. Sin barra final. */
const APP_URL = 'https://holoacademia-ai.onrender.com';

/**
 * Secreto compartido con Render (EMBED_SECRET).
 * DEBE ser idéntico al configurado en las variables de entorno de Render.
 * Genera uno con: python3 -c "import secrets; print(secrets.token_hex(32))"
 */
const EMBED_SECRET = 'PEGA_AQUI_TU_EMBED_SECRET';

/**
 * Mapa de IDs de Wix Pricing Plans → nombres de plan de la app.
 * Para obtener los IDs: Wix Dashboard → Pricing Plans → cada plan tiene un ID.
 * Ejemplo: 'abc123' → 'elite_pro'
 *
 * Si no usas Pricing Plans, elimina esta función y usa getPlanFromBadge().
 */
const PLAN_MAP = {
  // 'PLAN_ID_DE_WIX':  'nombre_en_app'
  // Reemplaza con los IDs reales de tus planes en Wix:
  'PREMIUM_PLAN_ID':     'premium',
  'ELITE_PRO_PLAN_ID':   'elite_pro',
  'INICIACION_PLAN_ID':  'iniciacion',
  'MEDIDA_PLAN_ID':      'medida',
};

// ── HELPERS ───────────────────────────────────────────────────────────────────

/**
 * Obtiene el plan del miembro desde Wix Pricing Plans.
 * Requiere: import { orders } from 'wix-pricing-plans-frontend';
 * Devuelve el nombre del plan o 'holoconexion' como fallback.
 */
async function getPlanFromPricingPlans(memberId) {
  try {
    // Importación dinámica para evitar error si el módulo no existe
    const { orders } = await import('wix-pricing-plans-frontend');
    const result = await orders.listCurrentMemberOrders();
    const activeOrder = result.orders?.find(o => o.status === 'ACTIVE');
    if (activeOrder) {
      return PLAN_MAP[activeOrder.planId] || 'holoconexion';
    }
  } catch (e) {
    console.warn('No se pudo leer Pricing Plans:', e);
  }
  return 'holoconexion';
}

/**
 * Construye la URL del iframe con uid + plan + token para la primera carga.
 * En cargas posteriores, la cookie de sesión ya existe y no se necesita el token.
 */
function buildEmbedUrl(path, uid, plan) {
  const params = new URLSearchParams({
    embed: '1',
    uid:   uid,
    plan:  plan,
    token: EMBED_SECRET,
  });
  return `${APP_URL}${path}?${params.toString()}`;
}

// ── PÁGINA PRINCIPAL (pega en la página con el iframe del menú principal) ────

$w.onReady(async function () {

  // 1. Leer el miembro actual de Wix
  let uid   = 'guest';
  let plan  = 'holoconexion';

  try {
    const member = await currentMember.getMember();
    if (member && member._id) {
      uid  = member._id;
      plan = await getPlanFromPricingPlans(member._id);
    }
  } catch (e) {
    console.warn('No se pudo leer el miembro actual:', e);
  }

  // 2. Construir URL del iframe apuntando al menú principal (/)
  const iframeUrl = buildEmbedUrl('/', uid, plan);

  // 3. Inyectar en el iframe de Wix
  // Si usas HTML Embed ($w('#htmlEmbed1')):
  //   $w('#htmlEmbed1').src = iframeUrl;
  //
  // Si usas un IFrame element ($w('#iframeHolo')):
  $w('#iframeHolo').src = iframeUrl;

  console.log('HoloAcadem-iA cargado para uid:', uid, '| plan:', plan);
});
