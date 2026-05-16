/**
 * HOLOACADEM-iA · Backend Web Module (Wix Velo)
 * ═══════════════════════════════════════════════
 *
 * INSTRUCCIONES:
 *  1. En el editor de Wix, abre el panel de Velo (Dev Mode)
 *  2. En la barra lateral izquierda → Backend → New File
 *  3. Nómbralo: holoAuth.web.js
 *  4. Pega este código completo
 *  5. Guarda y publica
 *
 * Este módulo corre en el servidor de Wix (seguro).
 * El EMBED_SECRET nunca llega al navegador del usuario.
 */

import { Permissions, webMethod } from 'wix-web-module';
import { currentMember } from 'wix-members-backend';
import { orders } from 'wix-pricing-plans-backend';

// ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────

const APP_URL      = 'https://holoacademia-ai.onrender.com';
const EMBED_SECRET = '71324df194cd5e535e40d1c570754f48f63aa4293ad6a49af1acc875724bd695';

/**
 * Mapa de IDs de Wix Pricing Plans → plan en la app.
 * Generado automáticamente desde la API de Wix.
 */
const PLAN_MAP = {
  // Holoconexión (gratis)
  'd979609e-e575-4790-8119-5188a438cfe5': 'holoconexion',

  // Iniciación Elite (mensual + anual + Semilla Estelar)
  'fd9fed62-e6e9-4e7f-9ae7-79ffdefc2b9d': 'iniciacion',   // Iniciación Elite MXN 299/mes
  'e56e1890-fb49-4f57-a08a-bc19613e2cf1': 'iniciacion',   // Pago Anual Iniciación Elite MXN 2990
  '0bdabea3-ec9d-4672-815f-fb071225b640': 'iniciacion',   // Semilla Estelar MXN 149/mes

  // Premium (todos los planes premium)
  '49af874c-e6e0-4be5-a666-fc96078ec0c9': 'premium',      // Pago Mensual Acceso Premium MXN 799
  '864ffe82-34f1-4ffa-98f4-e4d9c10090e2': 'premium',      // Pago Anual Acceso Premium MXN 7999
  'cc3e25be-3c2e-4fee-8dfc-e668c350268c': 'premium',      // Suscripción Secreta MXN 799
  'e42bd65e-5cf9-48c9-adcf-13fef478eb34': 'premium',      // Pago Anual Suscripción Secreta MXN 8800
  'd0c02146-ce2d-4586-9bf7-46e87a16d67e': 'premium',      // Pase Dorado 2026 MXN 999
};

// ── HELPERS ───────────────────────────────────────────────────────────────────

async function getMemberPlan() {
  try {
    const result = await orders.listCurrentMemberOrders({ planId: Object.keys(PLAN_MAP) });
    const active  = (result.orders || []).find(o => o.status === 'ACTIVE');
    if (active && PLAN_MAP[active.planId]) {
      return PLAN_MAP[active.planId];
    }
  } catch (e) {
    console.warn('[holoAuth] Error leyendo plan:', e.message);
  }
  return 'holoconexion';
}

// ── MÉTODO PÚBLICO ────────────────────────────────────────────────────────────

/**
 * Devuelve la URL del iframe con token de sesión para la página solicitada.
 * Llamado desde el frontend de Wix: import { getEmbedUrl } from 'backend/holoAuth.web';
 *
 * @param {string} path - ruta de la app, p.ej. '/', '/salud', '/astro-home'
 * @returns {Promise<string>} URL completa con parámetros embed
 */
export const getEmbedUrl = webMethod(
  Permissions.Member,
  async (path = '/') => {
    let uid  = 'guest';
    let plan = 'holoconexion';

    try {
      const member = await currentMember.getMember();
      if (member && member._id) {
        uid  = member._id;
        plan = await getMemberPlan();
      }
    } catch (e) {
      console.warn('[holoAuth] Error leyendo miembro:', e.message);
    }

    const params = new URLSearchParams({
      embed: '1',
      uid,
      plan,
      token: EMBED_SECRET,
    });

    const url = `${APP_URL}${path}?${params.toString()}`;
    console.log(`[holoAuth] Embed URL generada para uid=${uid} plan=${plan} path=${path}`);
    return url;
  }
);
