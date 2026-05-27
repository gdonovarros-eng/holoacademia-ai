/* ═══════════════════════════════════════════════════════════════════════
   THERAPY AKINATOR · UI Conversacional Diagnóstica
   Estados: idle → loading → conversing → completed
   ═══════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  let sessionId = null;
  let isAnswering = false;
  let currentQuestionTexto = null;

  // ─── Helpers DOM ─────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, html) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  };
  const esc = (s) => String(s || '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

  // ─── Recolectar intake del form principal ────────────────────────────
  function gatherIntake() {
    const form = document.getElementById('therapy-form');
    if (!form) return {};
    const fd = new FormData(form);
    // Mapeo de nombres del form a los campos del backend
    const intake = {
      motivo_consulta: fd.get('therapeutic_reason') || null,
      inicio: fd.get('therapeutic_onset') || null,
      duracion: fd.get('therapeutic_duration') || null,
      frecuencia: fd.get('therapeutic_frequency') || null,
      contexto_emocional: fd.get('therapeutic_emotional_context') || null,
      pregunta_del_terapeuta: fd.get('therapeutic_question') || null,
      family_notes: fd.get('therapeutic_family_notes') || null,
      observaciones: fd.get('therapeutic_observations') || null,
    };
    // Síntomas: recolectar los inputs dinámicos si existen
    const sintomasInputs = document.querySelectorAll('#symptoms-list input[type="text"], #symptoms-list textarea');
    const sintomas = Array.from(sintomasInputs).map(i => i.value.trim()).filter(Boolean);
    if (sintomas.length) intake.sintomas = sintomas;
    // Antecedentes
    const antecInputs = document.querySelectorAll('#history-list input[type="text"], #history-list textarea');
    const antecedentes = Array.from(antecInputs).map(i => i.value.trim()).filter(Boolean);
    if (antecedentes.length) intake.antecedentes = antecedentes;
    // Filtrar nulls
    return Object.fromEntries(Object.entries(intake).filter(([_, v]) => v != null && v !== ''));
  }

  // ─── Render Hipótesis ────────────────────────────────────────────────
  function renderHipotesis(hipotesis, opts = {}) {
    const container = $('hipotesis-list');
    if (!container) return;
    container.innerHTML = '';

    if (!hipotesis || !hipotesis.length) {
      container.innerHTML = '<p style="font-size:0.78rem;color:#94a3b8;text-align:center;padding:20px;">Sin hipótesis activas</p>';
      return;
    }

    hipotesis.forEach((h, i) => {
      const card = el('div', 'hipotesis-card' + (i === 0 ? ' top' : '') + (opts.confirmed && i === 0 ? ' confirmed' : ''));

      // Top line: nombre + %
      const top = el('div', 'hip-top-line');
      top.appendChild(el('div', 'hip-nombre', esc(h.nombre)));
      top.appendChild(el('div', 'hip-pct', h.probabilidad_pct + '%'));
      card.appendChild(top);

      // Bar
      const bar = el('div', 'hip-bar');
      const fill = el('div', 'hip-bar-fill');
      fill.style.width = Math.min(100, h.probabilidad_pct) + '%';
      bar.appendChild(fill);
      card.appendChild(bar);

      // Categoría
      card.appendChild(el('span', 'hip-categoria', esc(h.categoria.replace(/_/g, ' '))));

      // Detalle expandible (contexto profundo)
      const detail = el('div', 'hip-detail');

      // Escuelas: las 3 lecturas
      if (h.escuelas) {
        ['hamer', 'fleche', 'lavin'].forEach(esc_k => {
          if (h.escuelas[esc_k]) {
            const sec = el('div', 'hip-detail-section');
            sec.appendChild(el('div', 'hip-detail-label', esc_k.toUpperCase()));
            sec.appendChild(el('div', 'hip-detail-text', esc(h.escuelas[esc_k])));
            detail.appendChild(sec);
          }
        });
      }

      // Ubicaciones
      if (h.ubicaciones_organicas?.length) {
        const sec = el('div', 'hip-detail-section');
        sec.appendChild(el('div', 'hip-detail-label', 'Ubicaciones orgánicas'));
        const ul = el('ul', 'hip-detail-list');
        h.ubicaciones_organicas.forEach(u => ul.appendChild(el('li', null, esc(u))));
        sec.appendChild(ul);
        detail.appendChild(sec);
      }

      // Síntomas compatibles
      if (h.sintomas_compatibles?.length) {
        const sec = el('div', 'hip-detail-section');
        sec.appendChild(el('div', 'hip-detail-label', 'Síntomas compatibles'));
        const ul = el('ul', 'hip-detail-list');
        h.sintomas_compatibles.slice(0, 5).forEach(s => ul.appendChild(el('li', null, esc(s))));
        sec.appendChild(ul);
        detail.appendChild(sec);
      }

      // Ejemplos clínicos
      if (h.ejemplos_clinicos?.length) {
        const sec = el('div', 'hip-detail-section');
        sec.appendChild(el('div', 'hip-detail-label', 'Ejemplos clínicos'));
        h.ejemplos_clinicos.forEach(ej => {
          const ejDiv = el('div', 'hip-ejemplo');
          ejDiv.appendChild(el('div', 'hip-ejemplo-perfil', esc(ej.perfil)));
          ejDiv.appendChild(el('div', 'hip-ejemplo-contexto', esc(ej.contexto)));
          if (ej.resolucion) ejDiv.appendChild(el('div', 'hip-ejemplo-resol', '→ ' + esc(ej.resolucion)));
          sec.appendChild(ejDiv);
        });
        detail.appendChild(sec);
      }

      card.appendChild(detail);

      // Toggle expand al click
      card.addEventListener('click', () => card.classList.toggle('expanded'));

      // Top card auto-expandida por default
      if (i === 0) card.classList.add('expanded');

      container.appendChild(card);
    });

    // Update header count
    const head = document.querySelector('.akinator-hipotesis-head .h-count');
    if (head) head.textContent = `${hipotesis.length} activas`;
  }

  // ─── Render chat msgs ───────────────────────────────────────────────
  function addChatMsg(text, type) {
    const stream = $('chat-stream');
    if (!stream) return;
    const msg = el('div', 'chat-msg ' + type, esc(text));
    stream.appendChild(msg);
    stream.scrollTop = stream.scrollHeight;
  }
  function addSystemMsg(text) { addChatMsg(text, 'system'); }
  function addIaMsg(text) { addChatMsg(text, 'ia'); }
  function addUserMsg(text) { addChatMsg(text, 'user'); }

  // ─── Habilitar/deshabilitar botones de respuesta ─────────────────────
  function setAnswerButtonsEnabled(enabled) {
    document.querySelectorAll('.ans-btn').forEach(b => b.disabled = !enabled);
  }

  // ─── API calls ───────────────────────────────────────────────────────
  async function apiStart(intake) {
    const resp = await fetch('/therapeutic/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(intake),
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return resp.json();
  }
  async function apiAnswer(sid, respuesta) {
    const resp = await fetch('/therapeutic/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sid, respuesta }),
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return resp.json();
  }

  // ─── Iniciar diálogo ─────────────────────────────────────────────────
  async function iniciarAkinator() {
    const btn = $('btn-start-akinator');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="akinator-loading"></span> Iniciando diálogo…'; }

    const intake = gatherIntake();
    if (Object.keys(intake).length === 0) {
      alert('Primero completa al menos el motivo de consulta en el formulario.');
      if (btn) { btn.disabled = false; btn.textContent = '🧬 Iniciar diálogo guiado'; }
      return;
    }

    // Ocultar CTA inicial, mostrar el grid Akinator
    const cta = $('akinator-cta');
    const grid = $('akinator-grid');
    if (cta) cta.style.display = 'none';
    if (grid) grid.style.display = 'grid';

    try {
      const data = await apiStart(intake);
      if (data.error) throw new Error(data.error);
      sessionId = data.session_id;

      addSystemMsg('🧬 Diálogo iniciado. Cada respuesta refina las hipótesis sobre el evento desencadenante.');
      addIaMsg('Hola. Voy a hacerte preguntas dirigidas para descubrir qué evento biológico está activo. Mirá las hipótesis a la izquierda — verás cómo se ajustan con cada respuesta. Cuando una hipótesis pase del 72% te entregaré una ficha clínica completa con protocolo + pares biomagnéticos.');

      renderHipotesis(data.hipotesis);

      if (data.siguiente_pregunta) {
        currentQuestionTexto = data.siguiente_pregunta.texto;
        setTimeout(() => {
          addIaMsg(data.siguiente_pregunta.texto);
          setAnswerButtonsEnabled(true);
        }, 600);
      }
    } catch (e) {
      addSystemMsg('⚠ Error al iniciar: ' + e.message);
      if (btn) { btn.disabled = false; btn.textContent = '🧬 Iniciar diálogo guiado'; }
    }
  }

  // ─── Responder ───────────────────────────────────────────────────────
  async function responder(respuesta) {
    if (!sessionId || isAnswering) return;
    isAnswering = true;
    setAnswerButtonsEnabled(false);

    // Mostrar respuesta del usuario
    const labels = { si: '✓ Sí', no: '✗ No', no_se: '? No estoy seguro' };
    addUserMsg(labels[respuesta] || respuesta);

    try {
      const data = await apiAnswer(sessionId, respuesta);
      if (data.error) throw new Error(data.error);

      // Actualizar hipótesis
      renderHipotesis(data.hipotesis, { confirmed: data.completed });

      if (data.completed) {
        // Mostrar mensaje de cierre + renderizar ficha
        const razon = data.razon_cierre || 'cierre';
        const razonTxt = {
          'alta_confianza': '🎯 Llegamos a una hipótesis con alta confianza.',
          'max_preguntas': 'ℹ Hemos cubierto las preguntas más relevantes.',
          'sin_mas_preguntas': 'ℹ No quedan más preguntas discriminantes.',
        }[razon] || '✓ Diálogo completado.';
        setTimeout(() => {
          addSystemMsg(razonTxt);
          renderFicha(data.ficha);
        }, 500);
        return;
      }

      // Próxima pregunta
      if (data.siguiente_pregunta) {
        currentQuestionTexto = data.siguiente_pregunta.texto;
        setTimeout(() => {
          addIaMsg(data.siguiente_pregunta.texto);
          isAnswering = false;
          setAnswerButtonsEnabled(true);
        }, 800);
      } else {
        isAnswering = false;
      }
    } catch (e) {
      addSystemMsg('⚠ Error: ' + e.message);
      isAnswering = false;
      setAnswerButtonsEnabled(true);
    }
  }

  // ─── Ficha clínica final ─────────────────────────────────────────────
  function renderFicha(ficha) {
    if (!ficha) return;
    const container = $('ficha-clinica');
    if (!container) return;
    container.classList.remove('hidden');
    container.innerHTML = '';

    // Header
    const header = el('div', 'ficha-header');
    header.appendChild(el('div', 'ficha-header-eyebrow', '🎯 Hipótesis confirmada'));
    header.appendChild(el('div', 'ficha-header-title', esc(ficha.nombre)));
    header.appendChild(el('div', 'ficha-header-confianza', `Confianza: ${ficha.probabilidad_final}%`));
    container.appendChild(header);

    const body = el('div', 'ficha-body');

    // Sección: 3 escuelas
    if (ficha.escuelas) {
      const sec = el('div', 'ficha-section');
      sec.appendChild(el('div', 'ficha-section-title', 'Lectura desde 3 escuelas'));
      const grid = el('div', 'ficha-escuelas');
      ['hamer', 'fleche', 'lavin'].forEach(k => {
        if (ficha.escuelas[k]) {
          const card = el('div', 'ficha-escuela ' + k);
          const names = { hamer: '🧬 Hamer · NMG', fleche: '🇫🇷 Flèche · Bio', lavin: '🌎 Lavín · Holo' };
          card.appendChild(el('div', 'ficha-escuela-nombre', names[k]));
          card.appendChild(el('div', 'ficha-escuela-texto', esc(ficha.escuelas[k])));
          grid.appendChild(card);
        }
      });
      sec.appendChild(grid);
      body.appendChild(sec);
    }

    // Sección: ubicaciones + síntomas compatibles
    if (ficha.sintomas_compatibles?.length) {
      const sec = el('div', 'ficha-section');
      sec.appendChild(el('div', 'ficha-section-title', 'Síntomas compatibles'));
      const tags = el('div', 'ficha-sintomas');
      ficha.sintomas_compatibles.forEach(s => tags.appendChild(el('span', 'ficha-sintoma', esc(s))));
      sec.appendChild(tags);
      body.appendChild(sec);
    }

    if (ficha.sintomas_excluyentes?.length) {
      const sec = el('div', 'ficha-section');
      sec.appendChild(el('div', 'ficha-section-title', '⚠ Síntomas que descartan esta hipótesis (revisar)'));
      const tags = el('div', 'ficha-sintomas');
      ficha.sintomas_excluyentes.forEach(s => tags.appendChild(el('span', 'ficha-sintoma ficha-sintoma-excluyente', esc(s))));
      sec.appendChild(tags);
      body.appendChild(sec);
    }

    // Sección: Ejemplos clínicos
    if (ficha.ejemplos_clinicos?.length) {
      const sec = el('div', 'ficha-section');
      sec.appendChild(el('div', 'ficha-section-title', 'Ejemplos clínicos reales'));
      const grid = el('div', 'ficha-ejemplos');
      ficha.ejemplos_clinicos.forEach(ej => {
        const e = el('div', 'ficha-ejemplo');
        e.appendChild(el('div', 'ficha-ejemplo-perfil', esc(ej.perfil)));
        e.appendChild(el('div', 'ficha-ejemplo-contexto', esc(ej.contexto)));
        if (ej.resolucion) e.appendChild(el('div', 'ficha-ejemplo-resol', esc(ej.resolucion)));
        grid.appendChild(e);
      });
      sec.appendChild(grid);
      body.appendChild(sec);
    }

    // Sección: Protocolo
    if (ficha.protocolo_terapeutico) {
      const sec = el('div', 'ficha-section');
      sec.appendChild(el('div', 'ficha-section-title', 'Protocolo terapéutico sugerido'));
      sec.appendChild(el('div', 'ficha-protocolo', esc(ficha.protocolo_terapeutico)));
      body.appendChild(sec);
    }

    // Sección: Herramientas
    if (ficha.herramientas?.length) {
      const sec = el('div', 'ficha-section');
      sec.appendChild(el('div', 'ficha-section-title', 'Herramientas para el consultante'));
      const list = el('div', 'ficha-herramientas');
      ficha.herramientas.forEach(h => list.appendChild(el('div', 'ficha-herramienta', esc(h))));
      sec.appendChild(list);
      body.appendChild(sec);
    }

    // Sección: Pares biomagnéticos
    if (ficha.pares_biomagneticos?.length) {
      const sec = el('div', 'ficha-section');
      sec.appendChild(el('div', 'ficha-section-title', 'Pares biomagnéticos relacionados'));
      const grid = el('div', 'ficha-pares');
      ficha.pares_biomagneticos.forEach(p => {
        const c = el('div', 'ficha-par-card');
        c.appendChild(el('div', 'ficha-par-nombre', esc(p.par)));
        if (p.razon) c.appendChild(el('div', 'ficha-par-razon', esc(p.razon)));
        if (p.region || p.zona) {
          const locParts = [p.region, p.zona, p.bloque].filter(Boolean).join(' · ');
          if (locParts) c.appendChild(el('span', 'ficha-par-loc', esc(locParts)));
        }
        grid.appendChild(c);
      });
      sec.appendChild(grid);
      body.appendChild(sec);
    }

    // Disclaimer
    const disclaimer = el('div', 'ficha-section');
    disclaimer.style.cssText = 'font-size:0.74rem;color:#94a3b8;padding:12px 16px;background:#fef2f2;border-radius:8px;line-height:1.5;';
    disclaimer.innerHTML = '⚕️ <strong>Importante:</strong> esta es una hipótesis terapéutica educativa. NO sustituye diagnóstico médico. Si hay sospecha de patología orgánica grave (cáncer, infección, trauma), derivá al médico correspondiente antes de iniciar trabajo terapéutico.';
    body.appendChild(disclaimer);

    container.appendChild(body);
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // ─── Reiniciar diálogo ───────────────────────────────────────────────
  function reiniciar() {
    sessionId = null;
    isAnswering = false;
    currentQuestionTexto = null;
    $('chat-stream').innerHTML = '';
    $('hipotesis-list').innerHTML = '';
    $('ficha-clinica').classList.add('hidden');
    $('ficha-clinica').innerHTML = '';
    const cta = $('akinator-cta');
    const grid = $('akinator-grid');
    if (cta) cta.style.display = 'block';
    if (grid) grid.style.display = 'none';
    const btn = $('btn-start-akinator');
    if (btn) { btn.disabled = false; btn.textContent = '🧬 Iniciar diálogo guiado'; }
  }

  // ─── Wiring DOM ──────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    const start = $('btn-start-akinator');
    if (start) start.addEventListener('click', iniciarAkinator);
    document.querySelectorAll('.ans-btn').forEach(b => {
      b.addEventListener('click', () => responder(b.dataset.resp));
      b.disabled = true;
    });
    const reset = $('btn-reset-akinator');
    if (reset) reset.addEventListener('click', reiniciar);
  });

  // Expose for debugging
  window.therapyAkinator = { iniciarAkinator, responder, reiniciar };
})();
