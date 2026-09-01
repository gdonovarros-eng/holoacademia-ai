/* ═══════════════════════════════════════════════════════════════════════
   RASTREO GUIADO HOLOS — Bloque 11 del Cuestionario Holos
   Camino A: el Motor sugiere pares según síntomas.
   Camino B: zonas del cuerpo (3 niveles) → patógeno (3 niveles) → mapa.
   Los pares confirmados se vuelcan a #found-pairs-list para el Cuadro Holos.
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  let paresDb = null;        // /api/pares-db (371 pares planos)
  let uiDb = null;           // 9 zonas del cuerpo construidas desde paresDb
  let patogenosDb = null;    // /api/pares/catalogo (1433 pares por categoría)
  const state = { zona: null, region: null };

  // Las 9 zonas del cuerpo (UI) mapeadas a (region_db, zona_db).
  const UI_ZONAS_DEF = [
    ["Cabeza",  [["Cabeza", "Coronilla"], ["Cabeza", "Posterior"], ["Cabeza", "Lateral"], ["Cabeza", "Frente"], ["Cabeza", "Rostro"]]],
    ["Cuello",  [["Cabeza", "Cuello"]]],
    ["Pecho",   [["Tronco", "Tórax"]]],
    ["Abdomen", [["Tronco", "Abdomen"], ["Tronco", "Hepatitis"]]],
    ["Espalda", [["Tronco", "Espalda"], ["Extras", "Columna Vertebral"]]],
    ["Pelvis",  [["Pelvis", "Delantera"], ["Pelvis", "Trasera"], ["Pelvis", "Sexo"]]],
    ["Brazos",  [["Miembros", "Brazo"]]],
    ["Piernas", [["Miembros", "Pierna"]]],
    ["Extras",  [["Extras", "Variables"], ["Extras", "Ejes Corporales"]]],
  ];

  const panel = () => document.getElementById("holos-rastreo-panel");
  const fpList = () => document.getElementById("found-pairs-list");
  function esc(s) { return (window.escapeHtml ? window.escapeHtml(s) : String(s == null ? "" : s)); }

  function agregarParConfirmado(nombre, nota) {
    const list = fpList();
    if (!list || !nombre) return;
    const yaExiste = [...list.children].some((it) =>
      (it.querySelector('[data-field="pair_name"]')?.value || "").trim().toLowerCase() === nombre.toLowerCase());
    if (yaExiste) return;
    const tpl = document.getElementById("found-pair-template");
    if (!tpl) return;
    const node = tpl.content.cloneNode(true).firstElementChild;
    if (window.attachRemoveButton) window.attachRemoveButton(node);
    const nameInput = node.querySelector('[data-field="pair_name"]');
    if (nameInput) nameInput.value = nombre;
    if (nota) { const n = node.querySelector('[data-field="therapist_note"]'); if (n) n.value = nota; }
    list.appendChild(node);
  }

  async function cargarParesDb() {
    if (paresDb) return paresDb;
    try { const r = await fetch("/api/pares-db"); paresDb = r.ok ? await r.json() : null; } catch { paresDb = null; }
    return paresDb;
  }
  function reset() { const p = panel(); if (p) p.innerHTML = ""; }
  function loading(msg) { const p = panel(); if (p) p.innerHTML = `<div class="holos-rastreo-loading"><span class="holos-spin"></span> ${esc(msg)}</div>`; }
  function renderAviso(msg) { const p = panel(); if (p) p.innerHTML = `<div class="holos-rastreo-aviso">${esc(msg)}</div>`; }
  function parsePares(answer) {
    return (answer || "").split("\n").filter((l) => /PAR:/i.test(l)).map((l) => {
      const body = l.replace(/^.*PAR:\s*/i, "").replace(/\*+/g, "").trim();
      const [nombre, extra] = body.split("|").map((s) => (s || "").trim());
      return { nombre, extra: extra || "" };
    }).filter((p) => p.nombre);
  }

  // Pares actualmente confirmados (leídos de #found-pairs-list)
  function paresConfirmados() {
    const list = fpList(); if (!list) return [];
    return [...list.querySelectorAll('[data-field="pair_name"]')].map((i) => (i.value || "").trim()).filter(Boolean);
  }

  // Pares confirmados CON su contexto (la nota del rastreo: zona/región/patógeno),
  // para que el Motor cierre con significado y diagnóstico, no solo ubicaciones.
  function paresConfirmadosDetalle() {
    const list = fpList(); if (!list) return [];
    return [...list.querySelectorAll('[data-field="pair_name"]')].map((inp) => {
      const row = inp.closest("[data-pair-row], li, .found-pair, div") || inp.parentElement;
      const nombre = (inp.value || "").trim();
      const nota = (row && row.querySelector('[data-field="therapist_note"]')?.value || "").trim();
      return { nombre, nota };
    }).filter((x) => x.nombre);
  }

  // Markdown clínico → HTML (encabezados ###/##, negritas, viñetas, párrafos).
  function mdClinico(src) {
    const lines = String(src || "").split("\n");
    let html = "", inList = false;
    const closeList = () => { if (inList) { html += "</ul>"; inList = false; } };
    for (let raw of lines) {
      let line = raw.trimEnd();
      if (!line.trim()) { closeList(); continue; }
      line = line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      let m;
      if ((m = line.match(/^#{3,}\s+(.*)/))) { closeList(); html += `<h4 class="holos-mapa-par">${m[1]}</h4>`; continue; }
      if ((m = line.match(/^#{1,2}\s+(.*)/))) { closeList(); html += `<h3 class="holos-mapa-diag">${m[1]}</h3>`; continue; }
      if ((m = line.match(/^[-•]\s+(.*)/))) { if (!inList) { html += "<ul>"; inList = true; } html += `<li>${m[1]}</li>`; continue; }
      closeList(); html += `<p>${line}</p>`;
    }
    closeList();
    return html;
  }

  // ── CAMINO A · Sugerir según síntomas ──────────────────────────────────
  async function caminoSugerir() {
    const p = panel(); if (!p) return;
    const payload = window.getTherapeuticPayload ? window.getTherapeuticPayload() : {};
    const sintomas = (payload.sintomas || []).join(", ") || payload.motivo_consulta || "";
    if (!sintomas) { p.innerHTML = `<div class="holos-rastreo-aviso">Primero describe el motivo de consulta y los síntomas (bloque 2) para que el Motor sugiera pares.</div>`; return; }
    loading("El Motor analiza el cuadro y sugiere pares…");
    const eco = payload.ecosistema || {};
    const prompt = `Eres el Motor Biomagnético de HoloacademIA. Con base en este cuadro clínico:
Motivo: ${payload.motivo_consulta || ""}
Síntomas: ${sintomas}
Evento al inicio del síntoma: ${(eco.eventos_recientes && eco.eventos_recientes.al_inicio_sintoma) || ""}
Sugiere de 8 a 14 pares biomagnéticos prioritarios a rastrear. Una línea EXACTA por par:
PAR: [punto 1] - [punto 2] | [razón breve]
Sin numeración, sin texto adicional, sin advertencias.`;
    let pares = [];
    try { const res = await window.postJson("/therapeutic/holos", { prompt }); pares = parsePares(res && res.answer); }
    catch { p.innerHTML = `<div class="holos-rastreo-aviso">No se pudo consultar el Motor. Intenta de nuevo.</div>`; return; }
    const items = pares.map((x, i) =>
      `<label class="holos-par-check"><input type="checkbox" data-sug="${i}"><span class="holos-par-nom">${esc(x.nombre)}</span>${x.extra ? `<span class="holos-par-razon">${esc(x.extra)}</span>` : ""}</label>`).join("");
    p.innerHTML = `
      <div class="holos-rastreo-head"><strong>Pares sugeridos por el Motor</strong><span>Confirma con test muscular los que den positivo</span></div>
      <div class="holos-par-lista">${items || '<p class="holos-rastreo-aviso">El Motor no devolvió pares. Agrega más detalle del síntoma.</p>'}</div>
      <div class="holos-rastreo-acciones">
        <button type="button" class="secondary-btn" id="hr-sug-volver">Volver</button>
        <button type="button" class="holos-rastreo-btn" id="hr-sug-confirmar">Confirmar seleccionados</button>
      </div>`;
    p.querySelector("#hr-sug-volver")?.addEventListener("click", reset);
    p.querySelector("#hr-sug-confirmar")?.addEventListener("click", () => {
      p.querySelectorAll('input[data-sug]:checked').forEach((cb) => agregarParConfirmado(pares[+cb.dataset.sug].nombre, "Sugerido por el Motor"));
      renderNivelZonas();
    });
  }

  // ── CAMINO B · Guiar: 3 niveles (zona del cuerpo → región → pares) ─────
  async function caminoGuiar() {
    const p = panel(); if (!p) return;
    state.zona = null; state.region = null;
    loading("Cargando mapa de rastreo…");
    const db = await cargarParesDb();
    if (!db) { p.innerHTML = `<div class="holos-rastreo-aviso">No se pudo cargar el catálogo de pares.</div>`; return; }
    if (!uiDb) uiDb = buildUiDb();
    renderNivelZonas();
  }

  function buildUiDb() {
    const byZona = {};
    (paresDb.pairs || []).forEach((x) => {
      const k = x.region + "|" + x.zona;
      (byZona[k] = byZona[k] || {});
      (byZona[k][x.bloque] = byZona[k][x.bloque] || []).push(x);
    });
    const zonas = [];
    UI_ZONAS_DEF.forEach(([label, sources]) => {
      const regiones = [];
      sources.forEach(([dbReg, dbZon]) => {
        const blMap = byZona[dbReg + "|" + dbZon];
        if (!blMap) return;
        Object.entries(blMap).forEach(([bloqueNombre, pares]) => {
          regiones.push({ nombre: bloqueNombre, pares, zonaPadre: dbZon });
        });
      });
      if (regiones.length) {
        const total = regiones.reduce((a, r) => a + r.pares.length, 0);
        zonas.push({ nombre: label, regiones, total });
      }
    });
    return { zonas };
  }

  // Divide pares en bloques: <10 → 1 bloque; 10+ → partes iguales de ~5
  function chunkPares(pares) {
    const total = pares.length;
    if (total < 10) return [{ nombre: null, pares }];
    const numChunks = Math.max(2, Math.round(total / 5));
    const base = Math.floor(total / numChunks); let rem = total % numChunks;
    const chunks = []; let idx = 0;
    for (let i = 0; i < numChunks; i++) {
      const size = base + (rem > 0 ? 1 : 0); if (rem > 0) rem--;
      chunks.push({ nombre: `Bloque ${i + 1}`, pares: pares.slice(idx, idx + size) });
      idx += size;
    }
    return chunks;
  }

  function footerRastreo(extraBtn) {
    const n = paresConfirmados().length;
    return `<div class="holos-rastreo-footer">
      <button type="button" class="secondary-btn" id="hr-cancelar">Cancelar</button>
      <span class="holos-rastreo-estado"><strong class="holos-rastreo-count">${n}</strong> pares en el rastreo</span>
      ${extraBtn || ""}
    </div>`;
  }

  // NIVEL 1 · Zonas del cuerpo (9)
  function renderNivelZonas() {
    const p = panel(); if (!p || !uiDb) return;
    state.zona = null; state.region = null;
    const n = paresConfirmados().length;
    const cards = uiDb.zonas.map((z, i) =>
      `<button type="button" class="holos-zona-card" data-zona="${i}">
        <span class="holos-zona-card-nom">${esc(z.nombre)}</span>
        <span class="holos-zona-card-meta">${z.total} pares · ${z.regiones.length} ${z.regiones.length === 1 ? "región" : "regiones"}</span>
      </button>`).join("");
    const continuar = n > 0 ? `<button type="button" class="holos-rastreo-btn" id="hr-patogeno">Continuar a patógeno</button>` : "";
    p.innerHTML = `
      <div class="holos-rastreo-head"><strong>Rastreo biomagnético · Zonas del cuerpo</strong><span>Paso 1 de 3 · Elige la zona del cuerpo a rastrear</span></div>
      <div class="holos-zona-grid">${cards}</div>
      ${footerRastreo(continuar)}`;
    p.querySelectorAll(".holos-zona-card").forEach((b) => b.addEventListener("click", () => renderNivelRegiones(+b.dataset.zona)));
    p.querySelector("#hr-cancelar")?.addEventListener("click", reset);
    p.querySelector("#hr-patogeno")?.addEventListener("click", fasePatogeno);
  }

  // NIVEL 2 · Regiones dentro de la zona
  function renderNivelRegiones(zonaIdx) {
    const p = panel(); if (!p || !uiDb) return;
    state.zona = zonaIdx; state.region = null;
    const z = uiDb.zonas[zonaIdx];
    const cards = z.regiones.map((r, i) =>
      `<button type="button" class="holos-zona-card" data-region="${i}">
        <span class="holos-zona-card-nom">${esc(r.nombre)}</span>
        <span class="holos-zona-card-meta">${r.pares.length} ${r.pares.length === 1 ? "par" : "pares"}</span>
      </button>`).join("");
    p.innerHTML = `
      <div class="holos-rastreo-bc"><button type="button" class="holos-bc-link" id="hr-bc-zonas">Zonas del cuerpo</button><span class="holos-bc-sep">›</span><span>${esc(z.nombre)}</span></div>
      <div class="holos-rastreo-head"><strong>${esc(z.nombre)} · Regiones</strong><span>Paso 2 de 3 · Elige la región a rastrear</span></div>
      <div class="holos-zona-grid">${cards}</div>
      ${footerRastreo()}`;
    p.querySelectorAll(".holos-zona-card").forEach((b) => b.addEventListener("click", () => renderNivelBloques(zonaIdx, +b.dataset.region)));
    p.querySelector("#hr-bc-zonas")?.addEventListener("click", renderNivelZonas);
    p.querySelector("#hr-cancelar")?.addEventListener("click", reset);
  }

  // NIVEL 3 · Pares por bloques (marcar y confirmar)
  function renderNivelBloques(zonaIdx, regionIdx) {
    const p = panel(); if (!p || !uiDb) return;
    state.zona = zonaIdx; state.region = regionIdx;
    const z = uiDb.zonas[zonaIdx];
    const r = z.regiones[regionIdx];
    const yaConf = new Set(paresConfirmados().map((x) => x.toLowerCase()));
    const chunks = chunkPares(r.pares);
    const bloquesHtml = chunks.map((b) => `
      <div class="holos-zona-bloque">
        ${b.nombre ? `<div class="holos-zona-bloque-t">${esc(b.nombre)}</div>` : ""}
        <div class="holos-zona-pares">${b.pares.map((x) => {
          const conf = yaConf.has(x.nombre.toLowerCase());
          return `<label class="holos-par-check sm${conf ? " ya" : ""}"><input type="checkbox" data-par="${esc(x.nombre)}" ${conf ? "checked disabled" : ""}><span>${esc(x.nombre)}</span></label>`;
        }).join("")}</div>
      </div>`).join("");
    p.innerHTML = `
      <div class="holos-rastreo-bc"><button type="button" class="holos-bc-link" id="hr-bc-zonas">Zonas del cuerpo</button><span class="holos-bc-sep">›</span><button type="button" class="holos-bc-link" id="hr-bc-reg">${esc(z.nombre)}</button><span class="holos-bc-sep">›</span><span>${esc(r.nombre)}</span></div>
      <div class="holos-rastreo-head"><strong>${esc(r.nombre)} · Pares</strong><span>Paso 3 de 3 · Marca los pares que den positivo con test muscular y confírmalos</span></div>
      <div class="holos-zonas-cont">${bloquesHtml}</div>
      <div class="holos-rastreo-footer">
        <button type="button" class="secondary-btn" id="hr-b-volver">Volver a regiones</button>
        <span class="holos-rastreo-estado"><strong class="holos-sel-count">0</strong> seleccionados</span>
        <button type="button" class="holos-rastreo-btn" id="hr-b-confirmar">Confirmar pares</button>
      </div>`;
    const recount = () => { const n = p.querySelectorAll('input[data-par]:not(:disabled):checked').length; const c = p.querySelector(".holos-sel-count"); if (c) c.textContent = n; };
    p.querySelectorAll('input[data-par]:not(:disabled)').forEach((cb) => cb.addEventListener("change", recount));
    p.querySelector("#hr-bc-zonas")?.addEventListener("click", renderNivelZonas);
    p.querySelector("#hr-bc-reg")?.addEventListener("click", () => renderNivelRegiones(zonaIdx));
    p.querySelector("#hr-b-volver")?.addEventListener("click", () => renderNivelRegiones(zonaIdx));
    p.querySelector("#hr-b-confirmar")?.addEventListener("click", () => {
      const sel = [...p.querySelectorAll('input[data-par]:not(:disabled):checked')];
      if (!sel.length) { renderNivelZonas(); return; }
      sel.forEach((cb) => agregarParConfirmado(cb.dataset.par, `Rastreo · ${z.nombre} / ${r.nombre}`));
      renderNivelZonas();
    });
  }

  // ── FASE PATÓGENO · catálogo navegable real (categoría → región → bloque) ──
  async function cargarPatogenos() {
    if (patogenosDb) return patogenosDb;
    try { const r = await fetch("/api/pares/catalogo"); patogenosDb = r.ok ? await r.json() : null; } catch { patogenosDb = null; }
    return patogenosDb;
  }
  function filtraPatogenos(lista, term) {
    if (!term || term.length < 2) return lista;
    return lista.filter((x) => (`${x.nombre} ${x.agente || ""} ${(x.sintomas || []).join(" ")} ${(x.keywords || []).join(" ")}`).toLowerCase().includes(term));
  }
  function parPatogenoHtml(x, yaConf) {
    const conf = yaConf.has(x.nombre.toLowerCase());
    const sint = (x.sintomas || []).slice(0, 3).join(" · ");
    return `<label class="holos-pat-item${conf ? " ya" : ""}">
      <input type="checkbox" data-pat-nom="${esc(x.nombre)}" data-pat-ag="${esc(x.agente || "")}" ${conf ? "checked disabled" : ""}>
      <span class="holos-pat-info"><span class="holos-par-nom">${esc(x.nombre)}</span>${x.agente ? `<span class="holos-pat-ag">${esc(x.agente)}</span>` : ""}${sint ? `<span class="holos-pat-sint">${esc(sint)}</span>` : ""}</span>
    </label>`;
  }
  function listaPatogenosHtml(pares, titulo) {
    if (!pares.length) return `<p class="holos-rastreo-aviso">Sin resultados.</p>`;
    const yaConf = new Set(paresConfirmados().map((x) => x.toLowerCase()));
    return `${titulo ? `<div class="holos-zona-bloque-t">${esc(titulo)}</div>` : ""}<div class="holos-pat-lista">${pares.map((x) => parPatogenoHtml(x, yaConf)).join("")}</div>`;
  }
  function recountPat(p) { const n = p.querySelectorAll('input[data-pat-nom]:not(:disabled):checked').length; const c = p.querySelector(".holos-sel-count"); if (c) c.textContent = n; }
  function confirmarPatogenosSeleccionados(p) {
    [...p.querySelectorAll('input[data-pat-nom]:not(:disabled):checked')]
      .forEach((cb) => agregarParConfirmado(cb.dataset.patNom, cb.dataset.patAg ? `Patógeno · ${cb.dataset.patAg}` : "Rastreo por patógeno"));
  }

  async function fasePatogeno() {
    const p = panel(); if (!p) return;
    loading("Cargando catálogo de patógenos…");
    const cat = await cargarPatogenos();
    if (!cat) { renderAviso("No se pudo cargar el catálogo de patógenos."); return; }
    renderPatogenoCats();
  }

  function renderPatogenoCats() {
    const p = panel(); if (!p || !patogenosDb) return;
    const conteo = {};
    (patogenosDb.pares || []).forEach((x) => { conteo[x.categoria] = (conteo[x.categoria] || 0) + 1; });
    const cards = (patogenosDb.categorias || []).map((c) =>
      `<button type="button" class="holos-zona-card" data-cat="${esc(c.id)}">
        <span class="holos-zona-card-nom">${esc(c.nombre)}</span>
        <span class="holos-zona-card-meta">${conteo[c.id] || 0} pares</span>
      </button>`).join("");
    p.innerHTML = `
      <div class="holos-rastreo-head"><strong>Rastreo por patógeno</strong><span>Busca por síntoma o agente, o elige una categoría</span></div>
      <input type="text" class="holos-pat-search" id="hr-pat-q" placeholder="Buscar por síntoma, agente o par…" autocomplete="off">
      <div class="holos-zona-grid" id="hr-pat-grid">${cards}</div>
      <div id="hr-pat-res" style="display:none"></div>
      <div class="holos-rastreo-footer">
        <button type="button" class="secondary-btn" id="hr-pat-volver">Volver a zonas</button>
        <span class="holos-rastreo-estado"><strong class="holos-rastreo-count">${paresConfirmados().length}</strong> pares en el rastreo</span>
        <button type="button" class="holos-rastreo-btn" id="hr-pat-mapa">Generar mapa clínico</button>
      </div>`;
    p.querySelectorAll(".holos-zona-card").forEach((b) => b.addEventListener("click", () => renderPatogenoRegiones(b.dataset.cat)));
    const grid = p.querySelector("#hr-pat-grid");
    const res = p.querySelector("#hr-pat-res");
    p.querySelector("#hr-pat-q")?.addEventListener("input", (e) => {
      const term = e.target.value.trim().toLowerCase();
      if (term.length < 2) { grid.style.display = ""; res.style.display = "none"; res.innerHTML = ""; return; }
      grid.style.display = "none"; res.style.display = "";
      const hits = filtraPatogenos(patogenosDb.pares || [], term).slice(0, 80);
      res.innerHTML = `<div class="holos-zonas-cont">${listaPatogenosHtml(hits, `${hits.length} resultado${hits.length === 1 ? "" : "s"}`)}</div>
        <div class="holos-rastreo-acciones"><span class="holos-rastreo-estado"><strong class="holos-sel-count">0</strong> seleccionados</span><button type="button" class="holos-rastreo-btn" id="hr-pat-confs">Confirmar seleccionados</button></div>`;
      res.querySelectorAll('input[data-pat-nom]:not(:disabled)').forEach((cb) => cb.addEventListener("change", () => recountPat(p)));
      res.querySelector("#hr-pat-confs")?.addEventListener("click", () => { confirmarPatogenosSeleccionados(p); renderPatogenoCats(); });
    });
    p.querySelector("#hr-pat-volver")?.addEventListener("click", renderNivelZonas);
    p.querySelector("#hr-pat-mapa")?.addEventListener("click", faseMapa);
  }

  const PARES_POR_REGION = 30;
  function primeraPalabra(nombre) { return ((nombre || "").split(/\s*[—–-]\s*/)[0] || nombre || "").trim(); }
  function subdividirCategoria(catId) {
    const pares = (patogenosDb.pares || []).filter((x) => x.categoria === catId);
    const total = pares.length;
    const numReg = Math.max(1, Math.ceil(total / PARES_POR_REGION));
    const base = Math.floor(total / numReg); let rem = total % numReg;
    const regiones = []; let idx = 0;
    for (let i = 0; i < numReg; i++) {
      const size = base + (rem > 0 ? 1 : 0); if (rem > 0) rem--;
      const slice = pares.slice(idx, idx + size); idx += size;
      if (!slice.length) continue;
      const d = primeraPalabra(slice[0].nombre), h = primeraPalabra(slice[slice.length - 1].nombre);
      regiones.push({ idx: regiones.length, rango: d === h ? d : `${d} – ${h}`, pares: slice });
    }
    return regiones;
  }
  function renderPatogenoRegiones(catId) {
    const p = panel(); if (!p || !patogenosDb) return;
    const cat = (patogenosDb.categorias || []).find((c) => c.id === catId);
    const nombre = cat ? cat.nombre : catId;
    const regiones = subdividirCategoria(catId);
    const cards = regiones.map((r) =>
      `<button type="button" class="holos-zona-card" data-region="${r.idx}">
        <span class="holos-zona-card-nom">Región ${r.idx + 1}</span>
        <span class="holos-zona-card-meta">${r.pares.length} pares · ${esc(r.rango)}</span>
      </button>`).join("");
    p.innerHTML = `
      <div class="holos-rastreo-bc"><button type="button" class="holos-bc-link" id="hr-pat-bc">Rastreo por patógeno</button><span class="holos-bc-sep">›</span><span>${esc(nombre)}</span></div>
      <div class="holos-rastreo-head"><strong>${esc(nombre)} · Regiones</strong><span>${regiones.length} ${regiones.length === 1 ? "región" : "regiones"} · elige una para ver sus bloques</span></div>
      <div class="holos-zona-grid">${cards}</div>
      ${footerRastreo()}`;
    p.querySelectorAll(".holos-zona-card").forEach((b) => b.addEventListener("click", () => renderPatogenoBloques(catId, +b.dataset.region)));
    p.querySelector("#hr-pat-bc")?.addEventListener("click", renderPatogenoCats);
    p.querySelector("#hr-cancelar")?.addEventListener("click", renderPatogenoCats);
  }
  function renderPatogenoBloques(catId, regionIdx) {
    const p = panel(); if (!p || !patogenosDb) return;
    const cat = (patogenosDb.categorias || []).find((c) => c.id === catId);
    const nombre = cat ? cat.nombre : catId;
    const r = subdividirCategoria(catId)[regionIdx];
    if (!r) { renderPatogenoRegiones(catId); return; }
    const yaConf = new Set(paresConfirmados().map((x) => x.toLowerCase()));
    const chunks = chunkPares(r.pares);
    const cards = chunks.map((b, bi) => {
      const hechos = b.pares.filter((x) => yaConf.has(x.nombre.toLowerCase())).length;
      const d = primeraPalabra(b.pares[0].nombre), h = primeraPalabra(b.pares[b.pares.length - 1].nombre);
      return `<button type="button" class="holos-zona-card" data-bloque="${bi}">
        <span class="holos-zona-card-nom">Bloque ${bi + 1}</span>
        <span class="holos-zona-card-meta">${b.pares.length} pares · ${esc(d === h ? d : `${d} – ${h}`)}${hechos ? ` · ${hechos} en rastreo` : ""}</span>
      </button>`;
    }).join("");
    p.innerHTML = `
      <div class="holos-rastreo-bc"><button type="button" class="holos-bc-link" id="hr-pat-bc">Rastreo por patógeno</button><span class="holos-bc-sep">›</span><button type="button" class="holos-bc-link" id="hr-pat-bc2">${esc(nombre)}</button><span class="holos-bc-sep">›</span><span>Región ${regionIdx + 1}</span></div>
      <div class="holos-rastreo-head"><strong>${esc(nombre)} · Región ${regionIdx + 1}</strong><span>${chunks.length} bloques · elige uno para rastrear sus pares</span></div>
      <div class="holos-zona-grid">${cards}</div>
      ${footerRastreo()}`;
    p.querySelectorAll(".holos-zona-card").forEach((b) => b.addEventListener("click", () => renderPatogenoPares(catId, regionIdx, +b.dataset.bloque)));
    p.querySelector("#hr-pat-bc")?.addEventListener("click", renderPatogenoCats);
    p.querySelector("#hr-pat-bc2")?.addEventListener("click", () => renderPatogenoRegiones(catId));
    p.querySelector("#hr-cancelar")?.addEventListener("click", () => renderPatogenoRegiones(catId));
  }
  function renderPatogenoPares(catId, regionIdx, bloqueIdx) {
    const p = panel(); if (!p || !patogenosDb) return;
    const cat = (patogenosDb.categorias || []).find((c) => c.id === catId);
    const nombre = cat ? cat.nombre : catId;
    const r = subdividirCategoria(catId)[regionIdx];
    if (!r) { renderPatogenoRegiones(catId); return; }
    const b = chunkPares(r.pares)[bloqueIdx];
    if (!b) { renderPatogenoBloques(catId, regionIdx); return; }
    const yaConf = new Set(paresConfirmados().map((x) => x.toLowerCase()));
    p.innerHTML = `
      <div class="holos-rastreo-bc"><button type="button" class="holos-bc-link" id="hr-pat-bc">Rastreo por patógeno</button><span class="holos-bc-sep">›</span><button type="button" class="holos-bc-link" id="hr-pat-bc2">${esc(nombre)}</button><span class="holos-bc-sep">›</span><button type="button" class="holos-bc-link" id="hr-pat-bc3">Región ${regionIdx + 1}</button><span class="holos-bc-sep">›</span><span>Bloque ${bloqueIdx + 1}</span></div>
      <div class="holos-rastreo-head"><strong>${esc(nombre)} · Región ${regionIdx + 1} · Bloque ${bloqueIdx + 1}</strong><span>Marca los que den positivo con test muscular y confírmalos</span></div>
      <div class="holos-zonas-cont"><div class="holos-pat-lista">${b.pares.map((x) => parPatogenoHtml(x, yaConf)).join("")}</div></div>
      <div class="holos-rastreo-footer">
        <button type="button" class="secondary-btn" id="hr-pat-back">Volver a bloques</button>
        <span class="holos-rastreo-estado"><strong class="holos-sel-count">0</strong> seleccionados</span>
        <button type="button" class="holos-rastreo-btn" id="hr-pat-conf">Confirmar pares</button>
      </div>`;
    p.querySelectorAll('input[data-pat-nom]:not(:disabled)').forEach((cb) => cb.addEventListener("change", () => recountPat(p)));
    p.querySelector("#hr-pat-bc")?.addEventListener("click", renderPatogenoCats);
    p.querySelector("#hr-pat-bc2")?.addEventListener("click", () => renderPatogenoRegiones(catId));
    p.querySelector("#hr-pat-bc3")?.addEventListener("click", () => renderPatogenoBloques(catId, regionIdx));
    p.querySelector("#hr-pat-back")?.addEventListener("click", () => renderPatogenoBloques(catId, regionIdx));
    p.querySelector("#hr-pat-conf")?.addEventListener("click", () => { confirmarPatogenosSeleccionados(p); renderPatogenoBloques(catId, regionIdx); });
  }

  async function faseMapa() {
    const p = panel(); if (!p) return;
    const activos = paresConfirmados();
    const detalle = paresConfirmadosDetalle();
    if (!activos.length) { renderAviso("Aún no hay pares confirmados. Confirma al menos uno antes de cerrar el rastreo."); return; }
    loading("El Motor interpreta los pares y arma el diagnóstico…");
    const lista = detalle.map((d) => "- " + d.nombre + (d.nota ? ` (contexto del rastreo: ${d.nota})` : "")).join("\n");
    const prompt = `Eres el Motor Biomagnético de HoloacademIA. El terapeuta TERMINÓ el rastreo y confirmó estos pares:
${lista}

Entrega el CIERRE CLÍNICO del rastreo. La interpretación de cada par es información de REFERENCIA del método (su lectura estándar), NO un dato inventado: da la lectura clínica conocida y, si un par admite varias, ofrece la más probable según su órgano/tejido y su ubicación. No omitas ninguna sección por prudencia; el terapeuta necesita el significado y el diagnóstico, no solo las ubicaciones.

Para CADA par, usa EXACTAMENTE este formato:
### [Nombre del par]
- **Significado del par:** qué conecta (órganos, tejidos o función) y qué representa clínicamente.
- **Patógeno o conflicto asociado:** microorganismo, toxina o conflicto biológico más probable.
- **Interpretación biológica y emocional:** lectura en clave de biodescodificación y Nueva Medicina Germánica (órgano, sentido biológico, emoción o conflicto de fondo).
- **Ubicación de polos:** polo norte / polo sur de referencia.
- **Aplicación:** orden sugerido y tiempo aproximado de imán.

Al final, cierra con:
## Diagnóstico integrativo
La historia clínica que cuenta el conjunto de pares: patrón general, sistema u órgano dominante, conflicto emocional de fondo y hacia dónde apunta el tratamiento. 3 a 6 líneas, afirmativo y clínico. Sin advertencias ni descargos médicos.`;
    try {
      const res = await window.postJson("/therapeutic/holos", { prompt });
      const cuerpo = mdClinico((res && res.answer) || "");
      if (!cuerpo.trim()) { renderAviso("El Motor no devolvió la interpretación. Intenta cerrar el rastreo de nuevo."); return; }
      p.innerHTML = `
        <div class="holos-rastreo-head"><strong>Cierre clínico del rastreo</strong><span>${activos.length} ${activos.length === 1 ? "par" : "pares"} · significado y diagnóstico</span></div>
        <div class="holos-mapa holos-mapa-clinico">${cuerpo}</div>
        <div class="holos-rastreo-acciones"><button type="button" class="secondary-btn" id="hr-m-nuevo">Nuevo rastreo</button></div>`;
      p.querySelector("#hr-m-nuevo")?.addEventListener("click", reset);
    } catch {
      renderAviso("No se pudo generar el cierre, pero los pares quedaron confirmados en el cuadro.");
    }
  }

  function init() {
    document.getElementById("holos-rastreo-sugerir")?.addEventListener("click", caminoSugerir);
    document.getElementById("holos-rastreo-guiar")?.addEventListener("click", caminoGuiar);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
