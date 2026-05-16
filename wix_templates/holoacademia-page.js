/**
 * HOLOACADEM-iA · Código de Página (Wix Velo Frontend)
 * ══════════════════════════════════════════════════════
 *
 * INSTRUCCIONES:
 *  1. En el editor de Wix, abre la página donde va el iframe
 *  2. Añade un elemento "HTML Embed" o "iFrame" y dale el ID: iframeHolo
 *  3. Abre el editor de código Velo de esa página (panel derecho)
 *  4. Pega este código completo
 *  5. Guarda y publica
 *
 * REQUISITO: holoAuth.web.js debe estar creado en Backend primero.
 */

import { getEmbedUrl } from 'backend/holoAuth.web';

$w.onReady(async function () {

  // Mostrar spinner mientras carga
  if ($w('#loadingSpinner').length) {
    $w('#loadingSpinner').show();
  }

  try {
    // Obtener URL del iframe desde el backend seguro
    // Cambia '/' por la ruta que quieras mostrar en esta página:
    //   '/'           → Menú principal Holoacadem-iA
    //   '/salud'      → Astrología Médica
    //   '/astro-home' → Astrolog iA (módulo premium)
    //   '/alumno'     → Sinodal IA
    //   '/rastreo'    → Tablas de Rastreo
    //   '/pares'      → Guía de Pares
    //   '/terapeuta'  → Asistente Terapéutico
    const url = await getEmbedUrl('/');

    // Inyectar URL en el iframe
    $w('#iframeHolo').src = url;

  } catch (err) {
    console.error('[HoloAcadem-iA] Error cargando iframe:', err);

    // Mostrar mensaje de error si el iframe no carga
    if ($w('#errorMsg').length) {
      $w('#errorMsg').text = 'No se pudo cargar el asistente. Por favor recarga la página.';
      $w('#errorMsg').show();
    }
  } finally {
    if ($w('#loadingSpinner').length) {
      $w('#loadingSpinner').hide();
    }
  }
});
