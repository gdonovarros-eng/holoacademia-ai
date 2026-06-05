const state = {
  academicHistory: [],
};

const ACADEMIC_HISTORY_STORAGE_KEY = "holoacademia_academic_chat_v1";

const tabs = [...document.querySelectorAll(".tab")];
const tabPanels = [...document.querySelectorAll(".tab-panel")];

const consultantBirthDate = document.getElementById("consultant-birth-date");
const consultantAge = document.getElementById("consultant-age");

const symptomList = document.getElementById("symptoms-list");
const historyList = document.getElementById("history-list");
const significantPartnersList = document.getElementById("significant-partners-list");
const childrenList = document.getElementById("children-list");
const siblingsList = document.getElementById("siblings-list");

const analysisPanel = document.getElementById("analysis-panel");
const analysisOutput = document.getElementById("analysis-output");

const academicOutput = document.getElementById("academic-output");
const academicQuestion = document.getElementById("academic-question");

const protocolOutput = document.getElementById("protocol-output");
const protocolStatus = document.getElementById("protocol-status");
const protocolPanel = document.getElementById("protocol-panel");
const protocolNameInput = document.getElementById("protocol-name");
const protocolIdInput = document.getElementById("protocol-id");
const protocolCaseContextInput = document.getElementById("protocol-case-context");

const protocolSearchPanel = document.getElementById("protocol-search-panel");
const protocolSearchOutput = document.getElementById("protocol-search-output");
const protocolSearchStatus = document.getElementById("protocol-search-status");
const protocolSearchQuery = document.getElementById("protocol-search-query");
const protocolSearchNotes = document.getElementById("protocol-search-notes");

const foundPairsList = document.getElementById("found-pairs-list");
const pairsInterpretStatus = document.getElementById("pairs-interpret-status");
const pairsInterpretOutput = document.getElementById("pairs-interpret-output");

function setActiveTab(tabName) {
  tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === tabName));
  tabPanels.forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${tabName}`));
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatMessageText(value = "") {
  return escapeHtml(value).replace(/\n{2,}/g, "</p><p>").replace(/\n/g, "<br />");
}

function safeText(value = "") {
  return String(value ?? "").trim();
}

function compactStrings(values = []) {
  return values.map((item) => safeText(item)).filter(Boolean);
}

function buildKeyValueLines(entries = []) {
  return compactStrings(entries.map(([label, value]) => (safeText(value) ? `${label}: ${safeText(value)}` : "")));
}

function renderSimpleList(items = []) {
  const values = compactStrings(items);
  if (!values.length) return "";
  return `<ul class="bullet-list">${values.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderSectionCard(title, body) {
  if (!safeText(body)) return "";
  return `
    <article class="reference-card">
      <p><strong>${escapeHtml(title)}</strong></p>
      ${body}
    </article>
  `;
}

function setStatus(container, message, isError = false) {
  container.innerHTML = `<p class="status ${isError ? "error" : ""}">${escapeHtml(message)}</p>`;
}

function saveAcademicHistory() {
  try {
    sessionStorage.setItem(ACADEMIC_HISTORY_STORAGE_KEY, JSON.stringify(state.academicHistory));
  } catch (error) {
    console.warn("No se pudo guardar el historial del Asistente Académico.", error);
  }
}

function loadAcademicHistory() {
  try {
    const raw = sessionStorage.getItem(ACADEMIC_HISTORY_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      state.academicHistory = parsed.filter((item) => item && item.role && item.content);
    }
  } catch (error) {
    console.warn("No se pudo cargar el historial del Asistente Académico.", error);
  }
}

function attachRemoveButton(node) {
  node.querySelector(".remove-item")?.addEventListener("click", () => node.remove());
}

function addCollectionItem(container, templateId) {
  const template = document.getElementById(templateId);
  if (!container || !template) return;
  const fragment = template.content.cloneNode(true);
  const node = fragment.firstElementChild;
  attachRemoveButton(node);
  container.appendChild(node);
}

function readCollection(container) {
  if (!container) return [];
  return [...container.children]
    .map((item) => {
      const payload = {};
      item.querySelectorAll("[data-field]").forEach((field) => {
        if (field.dataset.type === "checkbox") {
          payload[field.dataset.field] = Boolean(field.checked);
        } else {
          payload[field.dataset.field] = field.value?.trim() || "";
        }
      });
      return payload;
    })
    .filter((item) => Object.values(item).some(Boolean));
}

function getText(name) {
  return document.querySelector(`[name="${name}"]`)?.value?.trim() || "";
}

function calculateAge(value) {
  if (!value) return "";
  const birth = new Date(value);
  if (Number.isNaN(birth.getTime())) return "";
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age -= 1;
  }
  return age >= 0 ? String(age) : "";
}

function getTherapeuticPayload() {
  const symptoms = readCollection(symptomList);
  const historyEvents = readCollection(historyList);
  const symptomNames = compactStrings(symptoms.map((item) => item.symptom_name));
  const symptomDetails = compactStrings(
    symptoms.map((item) =>
      buildKeyValueLines([
        ["síntoma", item.symptom_name],
        ["inicio", item.onset_age_or_date],
        ["características", item.symptom_characteristics],
        ["frecuencia", item.frequency],
      ]).join(" | "),
    ),
  );
  const historyDetails = compactStrings(
    historyEvents.map((item) =>
      buildKeyValueLines([
        ["antecedente", item.event_name],
        ["inicio", item.onset_age_or_date],
        ["características", item.event_characteristics],
        ["frecuencia", item.frequency],
      ]).join(" | "),
    ),
  );
  const antecedentNames = compactStrings(historyEvents.map((item) => item.event_name));
  const firstSymptom = symptoms[0] || {};
  const observations = compactStrings([
    getText("therapeutic_observations"),
    symptomDetails.length ? `Detalle de síntomas: ${symptomDetails.join(" || ")}` : "",
    historyDetails.length ? `Historial referido: ${historyDetails.join(" || ")}` : "",
  ]).join("\n");

  const familyParts = [];
  const fatherName = getText("father_full_name");
  const motherName = getText("mother_full_name");
  const fatherDeath = getText("father_death_date");
  const motherDeath = getText("mother_death_date");
  if (fatherName) familyParts.push(`padre: ${fatherName}${fatherDeath ? ` (fallecido ${fatherDeath})` : ""}`);
  if (getText("paternal_grandfather_full_name")) familyParts.push(`abuelo paterno: ${getText("paternal_grandfather_full_name")}${getText("paternal_grandfather_death_date") ? ` (fallecido)` : ""}`);
  if (getText("paternal_grandmother_full_name")) familyParts.push(`abuela paterna: ${getText("paternal_grandmother_full_name")}${getText("paternal_grandmother_death_date") ? ` (fallecida)` : ""}`);
  if (motherName) familyParts.push(`madre: ${motherName}${motherDeath ? ` (fallecida ${motherDeath})` : ""}`);
  if (getText("maternal_grandfather_full_name")) familyParts.push(`abuelo materno: ${getText("maternal_grandfather_full_name")}${getText("maternal_grandfather_death_date") ? ` (fallecido)` : ""}`);
  if (getText("maternal_grandmother_full_name")) familyParts.push(`abuela materna: ${getText("maternal_grandmother_full_name")}${getText("maternal_grandmother_death_date") ? ` (fallecida)` : ""}`);
  if (getText("current_partner_full_name")) familyParts.push(`pareja actual: ${getText("current_partner_full_name")}`);
  const sigPartners = readCollection(significantPartnersList);
  sigPartners.forEach((p) => { if (p.full_name) familyParts.push(`pareja significativa: ${p.full_name}`); });
  const children = readCollection(childrenList);
  children.forEach((c) => { if (c.full_name) familyParts.push(`hijo/a: ${c.full_name}${c.death_date ? ` (fallecido)` : ""}`); });
  const siblings = readCollection(siblingsList);
  siblings.forEach((s) => { if (s.full_name) familyParts.push(`hermano/a: ${s.full_name}${s.death_date ? ` (fallecido)` : ""}`); });
  const freeNote = getText("therapeutic_family_notes");
  const family_notes = compactStrings([familyParts.join("; "), freeNote]).join(". ") || "";

  return {
    motivo_consulta: getText("therapeutic_reason") || symptomNames[0] || "",
    sintomas: symptomNames,
    inicio: getText("therapeutic_onset") || firstSymptom.onset_age_or_date || "",
    duracion: getText("therapeutic_duration"),
    frecuencia: getText("therapeutic_frequency") || firstSymptom.frequency || "",
    antecedentes: compactStrings([...antecedentNames, ...historyDetails]),
    contexto_emocional: getText("therapeutic_emotional_context"),
    observaciones,
    pregunta_del_terapeuta: getText("therapeutic_question"),
    family_notes,
  };
}

function parseProtocolCaseContext(rawValue = "") {
  const text = safeText(rawValue);
  if (!text) return null;
  try {
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === "object" ? parsed : { notes: text };
  } catch (error) {
    return { notes: text };
  }
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const payload = await response.json().catch(() => null);
      const detail =
        (payload && typeof payload.detail === "string" && payload.detail.trim()) ||
        (payload && typeof payload.message === "string" && payload.message.trim()) ||
        "";
      throw new Error(detail ? `${response.status} ${detail}` : `Error del servidor (${response.status}).`);
    }

    const text = await response.text();
    const looksLikeHtml = contentType.includes("text/html") || /<!doctype html>|<html/i.test(text);
    if (looksLikeHtml && [502, 503, 504].includes(response.status)) {
      throw new Error(`Servicio temporalmente no disponible (${response.status}). Intenta de nuevo en unos minutos.`);
    }
    if (looksLikeHtml) {
      throw new Error(`Error del servidor (${response.status}).`);
    }

    const compactText = String(text || "").replace(/\s+/g, " ").trim().slice(0, 240);
    throw new Error(compactText ? `${response.status} ${compactText}` : `Error del servidor (${response.status}).`);
  }

  return response.json();
}

async function runViewRequest({ container, loadingMessage, request }) {
  setStatus(container, loadingMessage);
  try {
    return await request();
  } catch (error) {
    setStatus(container, error.message || "Ocurrió un error inesperado.", true);
    return null;
  }
}

function renderTherapeuticResponse(payload = {}) {
  const protocol = payload.protocolo_principal || {};
  const protocolSummary = protocol && Object.keys(protocol).length
    ? `
      <p><strong>${escapeHtml(protocol.nombre || "Protocolo principal")}</strong></p>
      ${protocol.por_que ? `<p><strong>Por qué:</strong> ${escapeHtml(protocol.por_que)}</p>` : ""}
      ${protocol.que_busca_resolver ? `<p><strong>Qué busca resolver:</strong> ${escapeHtml(protocol.que_busca_resolver)}</p>` : ""}
      ${Array.isArray(protocol.validaciones) && protocol.validaciones.length ? `<p><strong>Validaciones del protocolo:</strong></p>${renderSimpleList(protocol.validaciones)}` : ""}
      ${Array.isArray(protocol.pares_prioritarios) && protocol.pares_prioritarios.length ? `<p><strong>Pares prioritarios:</strong></p>${renderSimpleList(protocol.pares_prioritarios.slice(0, 3))}` : ""}
      ${Array.isArray(protocol.microbios_relacionados) && protocol.microbios_relacionados.length ? `<p><strong>Microbios relevantes:</strong></p>${renderSimpleList(protocol.microbios_relacionados.slice(0, 2))}` : ""}
    `
    : `<p class="status">Todavía no hay un protocolo principal suficientemente sustentado.</p>`;

  analysisOutput.innerHTML = `
    <article class="result-card">
      <h3>Lectura breve del caso</h3>
      <p>${formatMessageText(payload.answer || "No hubo respuesta del motor terapéutico.")}</p>
      ${payload.confidence ? `<p class="chat-meta">Confianza: ${escapeHtml(payload.confidence)}</p>` : ""}
    </article>
    <div class="reference-list">
      ${renderSectionCard(
        "Ruta principal",
        payload.ruta_principal ? `<p>${escapeHtml(payload.ruta_principal)}</p>` : `<p class="status">Todavía no se definió una ruta principal.</p>`
      )}
      ${renderSectionCard(
        "Acción inmediata",
        payload.accion_inmediata ? `<p>${escapeHtml(payload.accion_inmediata)}</p>` : `<p class="status">Sin acción inmediata priorizada.</p>`
      )}
      ${renderSectionCard(
        "Evidencias principales",
        renderSimpleList(payload.evidencias_principales || []) || `<p class="status">Aún faltan evidencias suficientes para sostener una ruta fuerte.</p>`
      )}
      ${renderSectionCard("Protocolo principal", protocolSummary)}
      ${renderSectionCard(
        "Pasos inmediatos",
        renderSimpleList(payload.pasos_inmediatos || []) || `<p class="status">Sin pasos inmediatos definidos.</p>`
      )}
      ${renderSectionCard(
        "Punto de decisión",
        payload.punto_de_decision ? `<p>${escapeHtml(payload.punto_de_decision)}</p>` : `<p class="status">Sin punto de decisión definido todavía.</p>`
      )}
      ${renderSectionCard(
        "Si no confirma",
        payload.si_no_confirma ? `<p>${escapeHtml(payload.si_no_confirma)}</p>` : `<p class="status">Sin ruta alternativa definida todavía.</p>`
      )}
      ${renderSectionCard(
        "Qué faltaría explorar",
        renderSimpleList(payload.missing_data || []) || `<p class="status">No se marcaron datos faltantes.</p>`
      )}
      ${renderSectionCard(
        "Preguntas prioritarias",
        renderSimpleList(payload.priority_questions || []) || `<p class="status">No se sugirieron preguntas prioritarias.</p>`
      )}
      ${renderSectionCard(
        "Advertencias y límites",
        renderSimpleList([...(payload.warnings || []), ...(payload.limites || [])]) || `<p class="status">Sin advertencias específicas.</p>`
      )}
      ${(() => {
        const g = payload.genogram_resolution;
        if (!g || !g.dominant_label) return "";
        const lines = [
          g.summary ? `<p>${escapeHtml(g.summary)}</p>` : "",
          g.dominant_label ? `<p><strong>Eje dominante:</strong> ${escapeHtml(g.dominant_label)}</p>` : "",
          g.repair_target ? `<p><strong>Objetivo de reparación:</strong> ${escapeHtml(g.repair_target)}</p>` : "",
          g.interview_focus ? `<p><strong>Foco de entrevista:</strong> ${escapeHtml(g.interview_focus)}</p>` : "",
          Array.isArray(g.supporting_signals) && g.supporting_signals.length
            ? `<p><strong>Señales de apoyo:</strong></p>${renderSimpleList(g.supporting_signals)}`
            : "",
        ].filter(Boolean).join("");
        return renderSectionCard("Resolución del genograma", lines);
      })()}
    </div>
  `;
}

function renderAcademicAnswer(payload) {
  const followups = Array.isArray(payload.suggested_followups) && payload.suggested_followups.length
    ? `
      <div class="chat-visual-card">
        <p class="chat-visual-title">Siguientes preguntas útiles</p>
        ${renderSimpleList(payload.suggested_followups)}
      </div>
    `
    : "";

  return `
    <div class="chat-bubble assistant">
      <div class="chat-avatar">IA</div>
      <div class="chat-message">
        <p>${formatMessageText(payload.answer || "")}</p>
        ${payload.confidence ? `<p class="chat-meta">Confianza: ${escapeHtml(payload.confidence)}</p>` : ""}
        ${followups}
      </div>
    </div>
  `;
}

function renderAcademicChat(loadingMessage = "") {
  if (!state.academicHistory.length && !loadingMessage) {
    academicOutput.innerHTML = `
      <article class="qa-card course-empty-state">
        <h3>Inicia una conversación</h3>
        <p>Puedes preguntar por conceptos, glosario, módulos o cualquier duda del curso.</p>
      </article>
    `;
    return;
  }

  const messages = state.academicHistory
    .map((item) => {
      if (item.role === "assistant") {
        return renderAcademicAnswer(item);
      }
      return `
        <div class="chat-bubble user">
          <div class="chat-message">
            <p>${formatMessageText(item.content)}</p>
          </div>
        </div>
      `;
    })
    .join("");

  const loading = loadingMessage
    ? `
      <div class="chat-bubble assistant pending">
        <div class="chat-avatar">IA</div>
        <div class="chat-message">
          <p>${escapeHtml(loadingMessage)}</p>
        </div>
      </div>
    `
    : "";

  academicOutput.innerHTML = messages + loading;
  academicOutput.scrollTop = academicOutput.scrollHeight;
}

function renderProtocolSteps(steps = []) {
  if (!Array.isArray(steps) || !steps.length) {
    return `<article class="result-card"><h3>Pasos</h3><p class="status">Sin pasos disponibles.</p></article>`;
  }

  return `
    <article class="result-card">
      <h3>Pasos</h3>
      <div class="reference-list">
        ${steps
          .map(
            (step) => `
              <article class="reference-card">
                <p><strong>Paso ${step.orden} · ${escapeHtml(step.titulo || "Sin título")}</strong></p>
                <p>${escapeHtml(step.instruccion || "")}</p>
                ${step.objetivo_del_paso ? `<p><strong>Objetivo:</strong> ${escapeHtml(step.objetivo_del_paso)}</p>` : ""}
                ${Array.isArray(step.que_observar) && step.que_observar.length ? `<p><strong>Qué observar:</strong></p>${renderSimpleList(step.que_observar)}` : ""}
                ${Array.isArray(step.que_registrar) && step.que_registrar.length ? `<p><strong>Qué registrar:</strong></p>${renderSimpleList(step.que_registrar)}` : ""}
                ${Array.isArray(step.notas) && step.notas.length ? `<p><strong>Notas:</strong></p>${renderSimpleList(step.notas)}` : ""}
                ${Array.isArray(step.decision_points) && step.decision_points.length ? `<p><strong>Decision points:</strong></p>${renderSimpleList(step.decision_points)}` : ""}
                ${Array.isArray(step.criterios_de_avance) && step.criterios_de_avance.length ? `<p><strong>Criterios de avance:</strong></p>${renderSimpleList(step.criterios_de_avance)}` : ""}
                ${Array.isArray(step.errores_comunes) && step.errores_comunes.length ? `<p><strong>Errores comunes:</strong></p>${renderSimpleList(step.errores_comunes)}` : ""}
              </article>
            `,
          )
          .join("")}
      </div>
    </article>
  `;
}

function renderProtocolGuide(payload = {}) {
  if (!payload.found) {
    protocolStatus.innerHTML = "";
    protocolOutput.innerHTML = `
      <article class="result-card">
        <h3>Protocolo no encontrado</h3>
        <p>${formatMessageText(payload.answer || "No encontré un protocolo con base suficiente.")}</p>
      </article>
    `;
    return;
  }

  protocolStatus.innerHTML = "";
  protocolOutput.innerHTML = `
    <article class="result-card">
      <h3>${escapeHtml(payload.protocol_name || "Guía de protocolo")}</h3>
      <p>${formatMessageText(payload.answer || "")}</p>
      ${payload.confidence ? `<p class="chat-meta">Confianza: ${escapeHtml(payload.confidence)}</p>` : ""}
    </article>
    <div class="reference-list">
      ${renderSectionCard("Objetivo", payload.objetivo ? `<p>${escapeHtml(payload.objetivo)}</p>` : `<p class="status">Sin objetivo disponible.</p>`)}
      ${renderSectionCard("Descripción", payload.descripcion ? `<p>${escapeHtml(payload.descripcion)}</p>` : `<p class="status">Sin descripción disponible.</p>`)}
      ${renderSectionCard("Cuándo usarlo", renderSimpleList(payload.cuando_usarlo || []) || `<p class="status">Sin uso sugerido.</p>`)}
      ${renderSectionCard("Prerequisitos", renderSimpleList(payload.prerequisitos || []) || `<p class="status">Sin prerequisitos definidos.</p>`)}
      ${renderProtocolSteps(payload.pasos || [])}
      ${renderSectionCard("Observaciones", renderSimpleList(payload.observaciones || []) || `<p class="status">Sin observaciones adicionales.</p>`)}
      ${renderSectionCard("Advertencias", renderSimpleList(payload.advertencias || []) || `<p class="status">Sin advertencias adicionales.</p>`)}
    </div>
  `;
}

function renderPairsInterpretation(payload) {
  const { interpretaciones = [], patron_general = "", sistemas_dominantes = [], tipos_presentes = [], no_encontrados = [] } = payload;

  const tipoLabel = {
    hongo: "Hongo",
    bacteria: "Bacteria",
    virus: "Virus",
    parasito: "Parásito",
    emocional: "Emocional",
    disfuncional: "Disfuncional",
    especial: "Especial",
    reservorio: "Reservorio",
    desconocido: "No clasificado",
  };

  const pairsCards = interpretaciones.map((item) => `
    <article class="reference-card">
      <p><strong>${escapeHtml(item.par_encontrado)}</strong>
        ${item.tipo ? ` <span class="chat-meta">[${escapeHtml(tipoLabel[item.tipo] || item.tipo)}]</span>` : ""}
      </p>
      ${item.condiciones ? `<p>${escapeHtml(item.condiciones)}</p>` : ""}
      ${item.significado_emocional ? `<p><strong>Significado emocional:</strong> ${escapeHtml(item.significado_emocional)}</p>` : ""}
      ${item.sistemas_afectados && item.sistemas_afectados.length ? `<p class="chat-meta">Sistemas: ${item.sistemas_afectados.join(", ")}</p>` : ""}
    </article>
  `).join("");

  pairsInterpretOutput.innerHTML = `
    ${patron_general ? `
      <article class="result-card">
        <h3>Lectura del patrón</h3>
        <p>${formatMessageText(patron_general)}</p>
        ${sistemas_dominantes.length ? `<p class="chat-meta">Sistemas dominantes: ${sistemas_dominantes.join(", ")}</p>` : ""}
        ${tipos_presentes.length ? `<p class="chat-meta">Tipos presentes: ${tipos_presentes.map((t) => tipoLabel[t] || t).join(", ")}</p>` : ""}
      </article>
    ` : ""}
    ${pairsCards ? `
      <div class="reference-list">
        <h3 style="padding:0 4px;margin-bottom:8px">Pares interpretados</h3>
        ${pairsCards}
      </div>
    ` : ""}
    ${no_encontrados.length ? renderSectionCard(
      "Pares no encontrados en la base",
      renderSimpleList(no_encontrados) + `<p class="chat-meta">Puedes buscarlos en el Menú de Protocolos o verificar el nombre exacto.</p>`
    ) : ""}
  `;
}

async function submitPairsInterpret() {
  const items = readCollection(foundPairsList);
  const pares = items.map((item) => safeText(item.pair_name)).filter(Boolean);

  if (!pares.length) {
    setStatus(pairsInterpretStatus, "Agrega al menos un par encontrado para interpretar.", true);
    return;
  }

  pairsInterpretStatus.innerHTML = "";
  pairsInterpretOutput.innerHTML = "";

  const notas = document.getElementById("pairs-case-notes")?.value?.trim() || "";

  const response = await runViewRequest({
    container: pairsInterpretStatus,
    loadingMessage: "Interpretando pares con el Asistente Terapéutico...",
    request: () => postJson("/pairs/interpret", { pares_encontrados: pares, notas: notas || undefined }),
  });

  if (response) {
    pairsInterpretStatus.innerHTML = "";
    renderPairsInterpretation(response);
  }
}

// ─── Numerología client-side ────────────────────────────────────────────────
function _numReduce(n) {
  while (n > 9 && n !== 11 && n !== 22 && n !== 33) {
    n = String(n).split("").reduce((a, d) => a + (parseInt(d) || 0), 0);
  }
  return n;
}

function _numCamino(fechaISO) {
  if (!fechaISO) return null;
  const [y, m, d] = fechaISO.split("-").map(Number);
  if (!y || !m || !d) return null;
  return _numReduce(_numReduce(d) + _numReduce(m) + _numReduce(y));
}

const _LETTER_VAL = {a:1,b:2,c:3,d:4,e:5,f:6,g:7,h:8,i:9,j:1,k:2,l:3,m:4,n:5,o:6,p:7,q:8,r:9,s:1,t:2,u:3,v:4,w:5,x:6,y:7,z:8};
const _VOWELS = new Set("aeiou");

function _normalizar(str) {
  return (str||"").toLowerCase()
    .replace(/á/g,"a").replace(/é/g,"e").replace(/í/g,"i").replace(/ó/g,"o").replace(/ú/g,"u").replace(/ü/g,"u").replace(/ñ/g,"n")
    .replace(/[^a-z]/g,"");
}

function _numExpresion(nombre) {
  if (!nombre) return null;
  return _numReduce(_normalizar(nombre).split("").reduce((a,c) => a + (_LETTER_VAL[c]||0), 0));
}

function _numAlma(nombre) {
  if (!nombre) return null;
  return _numReduce(_normalizar(nombre).split("").filter(c => _VOWELS.has(c)).reduce((a,c) => a + (_LETTER_VAL[c]||0), 0));
}

function construirPerfilNumerologico() {
  const personas = [];
  function add(rol, nombre, fecha) {
    const camino = _numCamino(fecha);
    const expr   = _numExpresion(nombre);
    const alma   = _numAlma(nombre);
    if (nombre || camino) {
      personas.push({ rol, nombre: nombre || rol, camino, expr, alma, fecha });
    }
  }

  add("Consultante",   getText("consultant_full_name"),         getText("consultant_birth_date"));
  add("Padre",         getText("father_full_name"),             getText("father_birth_date"));
  add("Madre",         getText("mother_full_name"),             getText("mother_birth_date"));
  add("Abuelo paterno",getText("paternal_grandfather_full_name"),getText("paternal_grandfather_birth_date"));
  add("Abuela paterna",getText("paternal_grandmother_full_name"),getText("paternal_grandmother_birth_date"));
  add("Abuelo materno",getText("maternal_grandfather_full_name"),getText("maternal_grandfather_birth_date"));
  add("Abuela materna",getText("maternal_grandmother_full_name"),getText("maternal_grandmother_birth_date"));
  add("Pareja",        getText("current_partner_full_name"),    getText("current_partner_birth_date"));

  readCollection(childrenList).forEach((c, i) => {
    add(`Hijo/a ${i+1}`, c.full_name, c.birth_date);
  });
  readCollection(siblingsList).forEach((s, i) => {
    add(`Hermano/a ${i+1}`, s.full_name, s.birth_date);
  });

  return personas;
}

function formatearPerfilNumerologico(personas) {
  return personas.map(p => {
    const parts = [p.rol + (p.nombre !== p.rol ? ` (${p.nombre})` : "")];
    if (p.fecha) parts.push(`nació ${p.fecha}`);
    if (p.camino) parts.push(`Camino de Vida: ${p.camino}`);
    if (p.expr)   parts.push(`Expresión: ${p.expr}`);
    if (p.alma)   parts.push(`Alma: ${p.alma}`);
    return "• " + parts.join(" | ");
  }).join("\n");
}

async function generarCuadroHolistico(payload) {
  const cuadroPanel  = document.getElementById("cuadro-holistico-panel");
  const cuadroOutput = document.getElementById("cuadro-holistico-output");
  const btnRegen     = document.getElementById("btn-regenerar-cuadro");
  if (!cuadroPanel || !cuadroOutput) return;

  cuadroPanel.classList.remove("hidden");
  cuadroOutput.innerHTML = `<div class="ra-loading"><div class="rastreo-interpret-spinner"></div><span>Generando Cuadro Médico Holístico integral…</span></div>`;
  if (btnRegen) btnRegen.style.display = "none";
  cuadroPanel.scrollIntoView({ behavior: "smooth", block: "start" });

  const personas   = construirPerfilNumerologico();
  const numStr     = formatearPerfilNumerologico(personas);
  const consultante = personas.find(p => p.rol === "Consultante");
  const sintomas   = (payload.sintomas||[]).join(", ") || payload.motivo_consulta || "No especificados";
  const pares      = readCollection(foundPairsList).map(p => p.pair_name).filter(Boolean);
  const paresStr   = pares.length ? pares.join(", ") : "No registrados aún";

  const prompt = `Eres el Motor Terapéutico de HoloacademIA. Actúas como terapeuta holístico integral.

Con los siguientes datos genera un CUADRO MÉDICO HOLÍSTICO COMPLETO:

DATOS DEL CASO:
• Motivo de consulta: ${payload.motivo_consulta || "No especificado"}
• Síntomas: ${sintomas}
• Contexto emocional: ${payload.contexto_emocional || "No especificado"}
• Notas del genograma: ${payload.family_notes || "No especificadas"}
• Pares biomagnéticos encontrados: ${paresStr}

PERFIL NUMEROLÓGICO (calculado automáticamente):
${numStr || "Sin datos de fechas suficientes"}

Genera el cuadro con ESTAS SECCIONES en español, estructuradas claramente:

## 1. PERFIL NUMEROLÓGICO
Interpreta los números de vida del consultante y la dinámica energética familiar. Detecta patrones kármicos, años personales, relaciones entre números. Conecta con los síntomas.

## 2. BIODESCODIFICACIÓN Y PSICOSOMÁTICA
Relaciona cada síntoma con su conflicto emocional biológico. Identifica el conflicto de choque (DHS), el tipo de conflicto y su manifestación en el órgano.

## 3. PATRONES TRANSGENERACIONALES
Analiza patrones que se repiten en el árbol genealógico basándote en los datos familiares. Identifica lealtades invisibles, mandatos y misiones reparadoras.

## 4. PARES BIOMAGNÉTICOS SUGERIDOS
Con base en los síntomas, sugiere los pares biomagnéticos más relevantes a rastrear (menciona polo positivo y negativo para cada par).

## 5. MEDICINA TRADICIONAL CHINA
Identifica los meridianos y órganos afectados según los síntomas. Sugiere puntos de acupuntura o digitopuntura específicos.

## 6. FLORES DE BACH RECOMENDADAS
Sugiere 3-5 esencias florales específicas según el estado emocional y los patrones detectados. Explica brevemente para qué sirve cada una.

## 7. HERBOLARIA
Sugiere 3-4 plantas medicinales relevantes para los síntomas, con modo de uso.

## 8. PLAN TERAPÉUTICO PROPUESTO
Un plan integrado semanal o por sesiones que combine las disciplinas anteriores de manera coherente.

Sé concreto, clínico y orientado a la acción del terapeuta. No agregues disclaimers médicos.`;

  try {
    const res = await postJson("/academic/ask", { query: prompt, history: [] });
    if (res && res.answer) {
      // Render with markdown-like formatting
      const html = res.answer
        .replace(/^## (.+)$/gm, '<h3 class="ch-section-title">$1</h3>')
        .replace(/^\*\*(.+?)\*\*$/gm, '<strong>$1</strong>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/^• (.+)$/gm, '<li>$1</li>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/^(\d+)\. (.+)$/gm, '<li><strong>$1.</strong> $2</li>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
      cuadroOutput.innerHTML = `<div class="ch-content"><p>${html}</p></div>`;
    } else {
      cuadroOutput.innerHTML = `<p class="status error">No se pudo generar el cuadro. Intenta de nuevo.</p>`;
    }
  } catch {
    cuadroOutput.innerHTML = `<p class="status error">Error al generar el cuadro holístico.</p>`;
  }
  if (btnRegen) {
    btnRegen.style.display = "block";
    btnRegen.onclick = () => generarCuadroHolistico(payload);
  }
}

async function submitTherapeutic() {
  const payload = getTherapeuticPayload();
  analysisPanel.classList.remove("hidden");

  const response = await runViewRequest({
    container: analysisOutput,
    loadingMessage: "Analizando caso con el Asistente Terapéutico...",
    request: () => postJson("/therapeutic/analyze", payload),
  });

  if (response) {
    renderTherapeuticResponse(response);
    // Auto-generate the holistic medical chart
    generarCuadroHolistico(payload);
  }
}

async function submitAcademic() {
  const query = academicQuestion.value.trim();
  if (!query) {
    renderAcademicChat();
    academicOutput.insertAdjacentHTML("beforeend", `<p class="status error">Escribe una pregunta primero.</p>`);
    return;
  }

  state.academicHistory.push({ role: "user", content: query });
  if (state.academicHistory.length > 20) {
    state.academicHistory.splice(0, state.academicHistory.length - 20);
  }
  saveAcademicHistory();
  renderAcademicChat("Pensando la respuesta...");
  academicQuestion.value = "";

  const response = await runViewRequest({
    container: academicOutput,
    loadingMessage: "Pensando la respuesta...",
    request: () => postJson("/academic/ask", {
      query,
      history: state.academicHistory.slice(-10).map((item) => ({
        role: item.role,
        content: item.content || item.answer || "",
      })),
    }),
  });

  if (!response) {
    state.academicHistory.pop();
    saveAcademicHistory();
    renderAcademicChat();
    academicOutput.insertAdjacentHTML("beforeend", `<p class="status error">No se pudo obtener respuesta del Asistente Académico.</p>`);
    return;
  }

  state.academicHistory.push({
    role: "assistant",
    answer: response.answer || "",
    content: response.answer || "",
    confidence: response.confidence || "",
    suggested_followups: response.suggested_followups || [],
  });
  if (state.academicHistory.length > 20) {
    state.academicHistory.splice(0, state.academicHistory.length - 20);
  }
  saveAcademicHistory();
  renderAcademicChat();
}

function renderProtocolSearch(payload = {}) {
  const { sistema_nombre, conflictos_relevantes = [], lectura_general, protocolo_sugerido, razon_protocolo } = payload;

  const sistemaBadge = sistema_nombre
    ? `<p class="chat-meta">Sistema detectado: <strong>${escapeHtml(sistema_nombre)}</strong></p>`
    : "";

  const conflictosHtml = conflictos_relevantes.length
    ? conflictos_relevantes.map((c) => `
        <article class="reference-card">
          <p><strong>${escapeHtml(c.nombre || c.subsistema || "Conflicto")}</strong>
            ${c.subsistema ? ` <span class="chat-meta">[${escapeHtml(c.subsistema)}]</span>` : ""}
          </p>
          ${c.frase_conflicto ? `<p class="conflict-phrase">"${escapeHtml(c.frase_conflicto)}"</p>` : ""}
          ${c.relevancia ? `<p>${escapeHtml(c.relevancia)}</p>` : ""}
        </article>`).join("")
    : `<p class="status">No se identificaron conflictos específicos en el mapa de conflictología. Realiza el rastreo general.</p>`;

  const protocolHtml = protocolo_sugerido
    ? `
      <article class="result-card">
        <h3>${escapeHtml(protocolo_sugerido.nombre)}</h3>
        ${razon_protocolo ? `<p>${escapeHtml(razon_protocolo)}</p>` : ""}
        ${protocolo_sugerido.objetivo ? `<p><strong>Objetivo:</strong> ${escapeHtml(protocolo_sugerido.objetivo)}</p>` : ""}
        ${protocolo_sugerido.prerequisitos?.length ? `<p><strong>Prerequisitos:</strong></p>${renderSimpleList(protocolo_sugerido.prerequisitos)}` : ""}
        ${protocolo_sugerido.pasos?.length ? `
          <ol class="protocol-steps">
            ${protocolo_sugerido.pasos.map((step) => `
              <li>
                <strong>${escapeHtml(step.titulo)}</strong>
                <p>${escapeHtml(step.instruccion)}</p>
                ${step.notas?.length ? `<p class="chat-meta">${step.notas.map(escapeHtml).join(" · ")}</p>` : ""}
              </li>`).join("")}
          </ol>` : ""}
        ${protocolo_sugerido.observaciones?.length ? `<p class="chat-meta">Nota: ${protocolo_sugerido.observaciones.map(escapeHtml).join(" ")} </p>` : ""}
      </article>`
    : `<p class="status">No se identificó un protocolo procedimental específico. Consulta al supervisor o usa el rastreo general.</p>`;

  protocolSearchOutput.innerHTML = `
    <article class="result-card">
      <h3>Lectura conflictológica</h3>
      ${sistemaBadge}
      <p>${escapeHtml(lectura_general || "")}</p>
    </article>
    ${renderSectionCard("Conflictos identificados", conflictosHtml)}
    ${renderSectionCard("Protocolo sugerido", protocolHtml)}
  `;
}

async function submitProtocolSearch() {
  const query = protocolSearchQuery?.value.trim();
  if (!query) {
    setStatus(protocolSearchStatus, "Describe el síntoma o problema del consultante.", true);
    return;
  }

  const payload = { query };
  const notes = protocolSearchNotes?.value.trim();
  if (notes) payload.notas = notes;

  protocolSearchPanel?.classList.remove("hidden");
  protocolSearchOutput.innerHTML = "";

  const response = await runViewRequest({
    container: protocolSearchStatus,
    loadingMessage: "Buscando conflictos y protocolo...",
    request: () => postJson("/protocols/search", payload),
  });

  if (response) {
    renderProtocolSearch(response);
  }
}

async function submitProtocols() {
  const protocol_name = protocolNameInput.value.trim();
  const protocol_id = protocolIdInput.value.trim();
  const case_context = parseProtocolCaseContext(protocolCaseContextInput.value);

  if (!protocol_name && !protocol_id) {
    setStatus(protocolStatus, "Escribe el nombre o el id del protocolo.", true);
    protocolOutput.innerHTML = "";
    return;
  }

  const payload = {};
  if (protocol_name) payload.protocol_name = protocol_name;
  if (protocol_id) payload.protocol_id = protocol_id;
  if (case_context) payload.case_context = case_context;

  protocolPanel?.classList.remove("hidden");
  protocolOutput.innerHTML = "";
  const response = await runViewRequest({
    container: protocolStatus,
    loadingMessage: "Buscando protocolo...",
    request: () => postJson("/protocols/guide", payload),
  });

  if (response) {
    renderProtocolGuide(response);
  }
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => setActiveTab(tab.dataset.tab));
});

consultantBirthDate?.addEventListener("change", () => {
  consultantAge.value = calculateAge(consultantBirthDate.value);
});

document.getElementById("add-symptom")?.addEventListener("click", () => addCollectionItem(symptomList, "symptom-template"));
document.getElementById("add-history")?.addEventListener("click", () => addCollectionItem(historyList, "history-template"));
document.getElementById("add-significant-partner")?.addEventListener("click", () => addCollectionItem(significantPartnersList, "significant-partner-template"));
document.getElementById("add-child")?.addEventListener("click", () => addCollectionItem(childrenList, "child-template"));
document.getElementById("add-sibling")?.addEventListener("click", () => addCollectionItem(siblingsList, "sibling-template"));
document.getElementById("add-found-pair")?.addEventListener("click", () => addCollectionItem(foundPairsList, "found-pair-template"));
document.getElementById("interpret-pairs-btn")?.addEventListener("click", submitPairsInterpret);

document.getElementById("analyze-case")?.addEventListener("click", submitTherapeutic);
document.getElementById("ask-academic")?.addEventListener("click", submitAcademic);
document.getElementById("ask-protocol")?.addEventListener("click", submitProtocols);
document.getElementById("search-protocols-btn")?.addEventListener("click", submitProtocolSearch);

academicQuestion?.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    submitAcademic();
  }
});

[protocolNameInput, protocolIdInput].forEach((field) => {
  field?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      submitProtocols();
    }
  });
});

document.getElementById("clear-academic-chat")?.addEventListener("click", () => {
  state.academicHistory = [];
  saveAcademicHistory();
  renderAcademicChat();
  academicQuestion?.focus();
});

addCollectionItem(symptomList, "symptom-template");
addCollectionItem(historyList, "history-template");
addCollectionItem(foundPairsList, "found-pair-template");
addCollectionItem(foundPairsList, "found-pair-template");

loadAcademicHistory();
renderAcademicChat();
if (protocolStatus) setStatus(protocolStatus, "Busca un protocolo por nombre o id para ver la guía estructurada.");

// ── Catálogo de Protocolos ──────────────────────────────────────────────────

let catalogData = null;
let activeCategoryId = null;

async function loadCatalog() {
  const statusEl = document.getElementById("catalog-status");
  if (catalogData) return; // already loaded

  try {
    if (statusEl) setStatus(statusEl, "Cargando catálogo…");
    const res = await fetch("/protocols/catalog");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    catalogData = await res.json();
    if (statusEl) statusEl.innerHTML = "";
    renderCatalogNav();
    if (catalogData.categories?.length) {
      selectCatalogCategory(catalogData.categories[0].id);
    }
  } catch (err) {
    if (statusEl) setStatus(statusEl, "No se pudo cargar el catálogo. Recarga la página.", true);
  }
}

function renderCatalogNav() {
  const nav = document.getElementById("catalog-category-nav");
  if (!nav || !catalogData) return;
  nav.innerHTML = catalogData.categories.map((cat) => `
    <button class="catalog-cat-btn" data-cat="${escapeHtml(cat.id)}">
      <span class="cat-icon">${escapeHtml(cat.icono || "")}</span>
      <span>${escapeHtml(cat.label)}</span>
      <span class="catalog-cat-count">${cat.protocolos.length}</span>
    </button>
  `).join("");

  nav.querySelectorAll(".catalog-cat-btn").forEach((btn) => {
    btn.addEventListener("click", () => selectCatalogCategory(btn.dataset.cat));
  });
}

function selectCatalogCategory(catId) {
  activeCategoryId = catId;

  document.querySelectorAll(".catalog-cat-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.cat === catId);
  });

  const cat = catalogData?.categories?.find((c) => c.id === catId);
  if (!cat) return;

  const header = document.getElementById("catalog-category-header");
  if (header) {
    header.classList.remove("hidden");
    header.innerHTML = `
      <h3>${escapeHtml(cat.icono || "")} ${escapeHtml(cat.label)}</h3>
      <p>${escapeHtml(cat.descripcion || "")}</p>
    `;
  }

  const cards = document.getElementById("catalog-cards");
  if (!cards) return;
  cards.innerHTML = cat.protocolos.map((p) => {
    const stepCount = p.pasos?.length ?? 0;
    const tags = (p.cuando_usarlo || []).slice(0, 2).map((t) =>
      `<span class="card-tag">${escapeHtml(t)}</span>`
    ).join("");
    return `
      <article class="catalog-card" data-pid="${escapeHtml(p.id)}" tabindex="0" role="button" aria-label="Ver ${escapeHtml(p.nombre)}">
        <h4>${escapeHtml(p.nombre)}</h4>
        <p class="card-objetivo">${escapeHtml(p.objetivo || "")}</p>
        ${tags ? `<div class="card-tags">${tags}</div>` : ""}
        <p class="card-steps-count">${stepCount} paso${stepCount !== 1 ? "s" : ""}</p>
      </article>
    `;
  }).join("");

  cards.querySelectorAll(".catalog-card").forEach((card) => {
    card.addEventListener("click", () => openProtocolDetail(card.dataset.pid));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") openProtocolDetail(card.dataset.pid);
    });
  });
}

// ── Protocol Wizard ────────────────────────────────────────────────────────

const wizardState = {
  protocol: null,       // full protocol object
  pasos: [],            // all pasos (ordered)
  currentIndex: 0,      // index into pasos array
  circuit: {},          // { orden: { respuesta, opcion, etiqueta } }
  siAnswered: {},       // { orden: true/false } — tracks SÍ/NO for verificacion pasos
  skippedTo: null,      // orden we jumped to (for si_negativo)
};

function wizardHasInteractivePasos(protocol) {
  return (protocol.pasos || []).some((p) => p.tipo);
}

function wizardGetCurrentPaso() {
  return wizardState.pasos[wizardState.currentIndex] || null;
}

function wizardGetVisibleOrden() {
  // Returns list of paso ordenes that should appear in sequence (respecting jumps)
  return wizardState.pasos.map((p) => p.orden);
}

function wizardRenderCircuit() {
  const pasos = wizardState.pasos;
  const circuit = wizardState.circuit;
  const currentOrden = wizardGetCurrentPaso()?.orden;

  if (!pasos.length) return "";

  const currentIndex = wizardState.currentIndex;
  const rows = pasos.map((p, idx) => {
    const rec = circuit[p.orden];
    const isCurrent = p.orden === currentOrden;
    const isSkipped = wizardState.skippedPasos && wizardState.skippedPasos.has(p.orden);
    const isPastInstruccion = p.tipo === "instruccion" && idx < currentIndex;
    const isDone = rec || isPastInstruccion;

    let statusIcon = isSkipped ? "—" : (isDone ? "✓" : (isCurrent ? "→" : "·"));
    let statusClass = isSkipped ? "circuit-row-skipped" : (isDone ? "circuit-row-done" : (isCurrent ? "circuit-row-current" : "circuit-row-pending"));

    let label = `Paso ${p.orden} — ${escapeHtml(p.titulo || "")}`;
    let detail = "";
    if (rec) {
      detail = escapeHtml(rec.etiqueta || rec.respuesta || "");
    } else if (isCurrent) {
      detail = "(en curso)";
    } else if (isPastInstruccion) {
      detail = "completado";
    }

    return `
      <div class="circuit-row ${statusClass}">
        <span class="circuit-icon">${statusIcon}</span>
        <span class="circuit-label">${label}${detail ? `<span class="circuit-detail">: ${detail}</span>` : ""}</span>
      </div>`;
  }).join("");

  return `<div class="wizard-circuit"><p class="wizard-circuit-title">CIRCUITO REGISTRADO</p>${rows}</div>`;
}

function wizardRenderOpciones(opciones, selectedId) {
  if (!Array.isArray(opciones) || !opciones.length) return "";

  // Detect grouped vs flat
  const isGrouped = opciones[0] && opciones[0].grupo !== undefined;

  if (isGrouped) {
    return opciones.map((group) => `
      <div class="wizard-opcion-group">
        <p class="wizard-group-label">${escapeHtml(group.grupo)}</p>
        <div class="wizard-opcion-grid">
          ${(group.items || []).map((item) => `
            <button class="wizard-opcion-btn${selectedId === item.id ? " selected" : ""}"
              data-opcion-id="${escapeHtml(item.id)}"
              data-opcion-etiqueta="${escapeHtml(item.etiqueta)}">
              ${escapeHtml(item.etiqueta)}
            </button>`).join("")}
        </div>
      </div>`).join("");
  }

  // Flat list
  return `<div class="wizard-opcion-grid">
    ${opciones.map((item) => `
      <button class="wizard-opcion-btn${selectedId === item.id ? " selected" : ""}"
        data-opcion-id="${escapeHtml(item.id)}"
        data-opcion-etiqueta="${escapeHtml(item.etiqueta)}">
        ${escapeHtml(item.etiqueta)}
      </button>`).join("")}
  </div>`;
}

function wizardRenderStep() {
  const paso = wizardGetCurrentPaso();
  if (!paso) return "";

  const total = wizardState.pasos.length;
  const currentNum = wizardState.currentIndex + 1;
  const progress = Math.round((currentNum / total) * 100);

  const rec = wizardState.circuit[paso.orden];
  const siAnswered = wizardState.siAnswered[paso.orden];
  const selectedId = rec?.opcionId || null;

  let bodyHtml = "";
  const isInstruccion = paso.tipo === "instruccion";

  if (paso.tipo === "verificacion") {
    const siSelected = siAnswered === true;
    const noSelected = siAnswered === false;
    bodyHtml = `
      <div class="wizard-yn-row">
        <button class="wizard-yn-btn wizard-si${siSelected ? " selected" : ""}" data-yn="si">SÍ</button>
        <button class="wizard-yn-btn wizard-no${noSelected ? " selected" : ""}" data-yn="no">NO</button>
      </div>`;
    if (siSelected && paso.opciones && paso.opciones.length) {
      bodyHtml += `<p class="wizard-opciones-label">Selecciona la opción correspondiente:</p>`;
      bodyHtml += wizardRenderOpciones(paso.opciones, selectedId);
    }
  } else if (paso.tipo === "seleccion") {
    bodyHtml = wizardRenderOpciones(paso.opciones || [], selectedId);
  } else if (paso.tipo === "rastreo") {
    bodyHtml = `<p class="wizard-rastreo-hint">Rastrear con TM — seleccionar el rango o valor registrado:</p>`;
    bodyHtml += wizardRenderOpciones(paso.opciones || [], selectedId);
  } else if (isInstruccion) {
    bodyHtml = `<div class="wizard-instruccion-body"><p>${escapeHtml(paso.instruccion || "")}</p>`;
    if (paso.notas && paso.notas.length) {
      bodyHtml += paso.notas.map((n) => `<p class="wizard-nota">${escapeHtml(n)}</p>`).join("");
    }
    bodyHtml += `</div>`;
  }

  // Show instruccion text as context for non-instruccion steps (if present and not empty)
  const instrText = paso.instruccion || "";
  if (!isInstruccion && instrText.trim()) {
    bodyHtml += `
      <details class="wizard-context-details">
        <summary class="wizard-context-summary">📋 Ver tabla del manual</summary>
        <div class="wizard-context-body">${escapeHtml(instrText)}</div>
      </details>`;
  }

  const canPrev = wizardState.currentIndex > 0;
  const canNext = wizardState.currentIndex < wizardState.pasos.length - 1;
  const msLabel = isInstruccion ? "" : `<p class="wizard-ms-label">MENTE SUPRACONSCIENTE</p>`;
  const questionClass = isInstruccion ? "wizard-step-title" : "wizard-question";

  return `
    <div class="wizard-header">
      <h2 class="wizard-protocol-name">${escapeHtml(wizardState.protocol.nombre)}</h2>
      <div class="wizard-progress-row">
        <span class="wizard-progress-label">Paso ${currentNum} de ${total}</span>
        <div class="wizard-progress-bar"><div class="wizard-progress-fill" style="width:${progress}%"></div></div>
      </div>
    </div>

    <div class="wizard-card">
      ${msLabel}
      <p class="${questionClass}">${escapeHtml(paso.pregunta_ms || paso.titulo || "")}</p>
      ${bodyHtml}
    </div>

    <div class="wizard-nav">
      <button class="wizard-nav-btn wizard-prev${canPrev ? "" : " disabled"}" data-nav="prev" ${canPrev ? "" : "disabled"}>← Anterior</button>
      <button class="wizard-nav-btn wizard-reiniciar" data-nav="reiniciar">Reiniciar</button>
      <button class="wizard-nav-btn wizard-next${canNext ? "" : " disabled"}" data-nav="next" ${canNext ? "" : "disabled"}>Siguiente →</button>
    </div>

    ${wizardRenderCircuit()}
  `;
}

function wizardRenderFallback(p, catMeta) {
  const stepsHtml = (p.pasos || []).length
    ? `<ol class="catalog-detail-steps">
        ${p.pasos.map((step) => `
          <li>
            <div class="step-body">
              <strong>${escapeHtml(step.titulo)}</strong>
              <p>${escapeHtml(step.instruccion)}</p>
              ${(step.notas || []).map((n) => `<p class="step-nota">${escapeHtml(n)}</p>`).join("")}
            </div>
          </li>`).join("")}
       </ol>`
    : `<p class="chat-meta">Sin pasos registrados.</p>`;

  const cuandoHtml = (p.cuando_usarlo || []).length
    ? `<ul class="detail-list">${p.cuando_usarlo.map((u) => `<li>${escapeHtml(u)}</li>`).join("")}</ul>` : "";
  const prereqHtml = (p.prerequisitos || []).length
    ? `<ul class="detail-list">${p.prerequisitos.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>` : "";
  const obsHtml = (p.observaciones || []).length
    ? `<ul class="detail-list">${p.observaciones.map((o) => `<li>${escapeHtml(o)}</li>`).join("")}</ul>` : "";

  return `
    <h2>${escapeHtml(p.nombre)}</h2>
    ${catMeta ? `<span class="detail-cat-badge">${escapeHtml(catMeta.icono || "")} ${escapeHtml(catMeta.label)}</span>` : ""}
    <p class="detail-section-label">Objetivo</p>
    <p class="detail-objetivo">${escapeHtml(p.objetivo || "")}</p>
    ${cuandoHtml ? `<p class="detail-section-label">Cuándo usarlo</p>${cuandoHtml}` : ""}
    ${prereqHtml ? `<p class="detail-section-label">Prerequisitos</p>${prereqHtml}` : ""}
    <p class="detail-section-label">Pasos</p>
    ${stepsHtml}
    ${obsHtml ? `<p class="detail-section-label">Observaciones</p>${obsHtml}` : ""}
  `;
}

function wizardMount(content) {
  content.innerHTML = wizardRenderStep();
  wizardBindEvents(content);
}

function wizardBindEvents(content) {
  // SÍ/NO buttons
  content.querySelectorAll(".wizard-yn-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const paso = wizardGetCurrentPaso();
      if (!paso) return;
      const yn = btn.dataset.yn;
      const isYes = yn === "si";
      wizardState.siAnswered[paso.orden] = isYes;

      if (!isYes) {
        // Record NO and optionally jump
        wizardState.circuit[paso.orden] = { respuesta: "NO", etiqueta: "NO" };
        if (paso.si_negativo) {
          wizardJumpToOrden(paso.si_negativo, content);
          return;
        }
      } else {
        // Record SÍ — opcion will be set when user picks one (or just SÍ if no opciones)
        if (!paso.opciones || !paso.opciones.length) {
          wizardState.circuit[paso.orden] = { respuesta: "SÍ", etiqueta: "SÍ" };
        } else {
          // Clear any previous selection so we re-render with opcion grid shown
          delete wizardState.circuit[paso.orden];
        }
      }
      wizardMount(content);
    });
  });

  // Opcion buttons
  content.querySelectorAll(".wizard-opcion-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const paso = wizardGetCurrentPaso();
      if (!paso) return;
      const id = btn.dataset.opcionId;
      const etiqueta = btn.dataset.opcionEtiqueta;
      // Toggle selection
      if (wizardState.circuit[paso.orden]?.opcionId === id) {
        // Deselect
        delete wizardState.circuit[paso.orden];
      } else {
        wizardState.circuit[paso.orden] = { respuesta: "SÍ", opcionId: id, etiqueta };
      }
      wizardMount(content);
    });
  });

  // Nav buttons
  content.querySelectorAll(".wizard-nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const nav = btn.dataset.nav;
      if (nav === "prev" && wizardState.currentIndex > 0) {
        wizardState.currentIndex -= 1;
        wizardMount(content);
      } else if (nav === "next" && wizardState.currentIndex < wizardState.pasos.length - 1) {
        wizardState.currentIndex += 1;
        wizardMount(content);
      } else if (nav === "reiniciar") {
        wizardState.circuit = {};
        wizardState.siAnswered = {};
        wizardState.skippedPasos = new Set();
        wizardState.currentIndex = 0;
        wizardMount(content);
      }
    });
  });
}

function wizardJumpToOrden(targetOrden, content) {
  // Mark all pasos between current+1 and targetOrden-1 as skipped
  if (!wizardState.skippedPasos) wizardState.skippedPasos = new Set();
  const currentPaso = wizardGetCurrentPaso();
  const currentOrden = currentPaso?.orden ?? 0;

  wizardState.pasos.forEach((p) => {
    if (p.orden > currentOrden && p.orden < targetOrden) {
      wizardState.skippedPasos.add(p.orden);
    }
  });

  const targetIndex = wizardState.pasos.findIndex((p) => p.orden === targetOrden);
  if (targetIndex >= 0) {
    wizardState.currentIndex = targetIndex;
  }
  wizardMount(content);
}

// ── Diagnóstico Orgánico — tabla interactiva ────────────────────────────────

function renderDiagnosticoOrganico(p, content) {
  const sistemas = (p.pasos || [])
    .filter((pa) => pa.tipo === "diagnostico")
    .sort((a, b) => a.orden - b.orden);

  const dxState = {}; // { sistema_id: band }
  const BANDS = [
    { id: "optimo",    label: "Óptimo",    range: "81–100%", color: "#22c55e" },
    { id: "bueno",     label: "Bueno",     range: "61–80%",  color: "#86efac" },
    { id: "moderado",  label: "Moderado",  range: "41–60%",  color: "#fbbf24" },
    { id: "bajo",      label: "Bajo",      range: "21–40%",  color: "#f97316" },
    { id: "critico",   label: "Crítico",   range: "0–20%",   color: "#ef4444" },
  ];
  const PRIORITY_ORDER = ["critico", "bajo", "moderado", "bueno", "optimo"];

  function renderTable() {
    const rows = sistemas.map((pa) => {
      const sel = dxState[pa.sistema_id];
      const btns = BANDS.map((b) => {
        const active = sel === b.id;
        return `<button class="dx-band-btn${active ? " active" : ""}"
          data-sid="${pa.sistema_id}" data-band="${b.id}"
          style="${active ? `background:${b.color};color:#fff;border-color:${b.color}` : `border-color:${b.color};color:${b.color}`}"
          title="${b.range}">
          ${b.label}<span class="dx-band-range">${b.range}</span>
        </button>`;
      }).join("");
      return `<div class="dx-row${sel ? " dx-row-done" : ""}">
        <span class="dx-sys-name">${escapeHtml(pa.sistema_nombre)}</span>
        <div class="dx-bands">${btns}</div>
      </div>`;
    }).join("");

    const done = Object.keys(dxState).length;
    const total = sistemas.length;
    const pct = Math.round((done / total) * 100);

    // Priority summary
    let summaryHtml = "";
    if (done > 0) {
      const sorted = Object.entries(dxState)
        .sort((a, b) => PRIORITY_ORDER.indexOf(a[1]) - PRIORITY_ORDER.indexOf(b[1]));
      const band = (id) => BANDS.find((b) => b.id === id);
      const sys = (id) => sistemas.find((s) => s.sistema_id === id);
      summaryHtml = `<div class="dx-summary">
        <p class="dx-summary-title">Prioridad de intervención:</p>
        ${sorted.map(([sid, bid]) => {
          const b = band(bid); const s = sys(sid);
          return `<div class="dx-summary-row">
            <span class="dx-priority-dot" style="background:${b?.color}"></span>
            <span>${s?.sistema_nombre || sid}</span>
            <span class="dx-priority-band" style="color:${b?.color}">${b?.label} (${b?.range})</span>
          </div>`;
        }).join("")}
      </div>`;
    }

    content.innerHTML = `
      <div class="dx-header">
        <h2 class="wizard-protocol-name">${escapeHtml(p.nombre)}</h2>
        <p class="dx-subtitle">MS: "100% = estado óptimo histórico · 0% = necrosis total"<br>
          Preguntar sistema por sistema con test muscular y seleccionar la banda correspondiente.</p>
        <div class="wizard-progress-row">
          <span class="wizard-progress-label">${done} de ${total} sistemas evaluados</span>
          <div class="wizard-progress-bar"><div class="wizard-progress-fill" style="width:${pct}%"></div></div>
        </div>
      </div>
      <div class="dx-table">${rows}</div>
      ${summaryHtml}
      <div class="wizard-nav">
        <button class="wizard-nav-btn wizard-reiniciar" id="dx-reset">Reiniciar</button>
      </div>`;

    content.querySelectorAll(".dx-band-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sid = btn.dataset.sid;
        const bid = btn.dataset.band;
        if (dxState[sid] === bid) { delete dxState[sid]; } else { dxState[sid] = bid; }
        renderTable();
      });
    });
    content.querySelector("#dx-reset")?.addEventListener("click", () => {
      Object.keys(dxState).forEach((k) => delete dxState[k]);
      renderTable();
    });
  }

  renderTable();
}

// ─── Tabla Rastreo — shared AI interpretation helper ──────────────────────────
async function rastreoInterpretarIA(containerEl, textoRastreo) {
  containerEl.innerHTML = `<div class="rastreo-interpret-loading">
    <div class="rastreo-interpret-spinner"></div>
    <span>Consultando al Motor Terapéutico...</span>
  </div>`;
  try {
    const response = await postJson("/academic/ask", {
      query: textoRastreo,
      history: [],
    });
    if (response && response.answer) {
      containerEl.innerHTML = `<div class="rastreo-interpret-result">
        <p class="rastreo-interpret-label">🧠 Interpretación del Motor Terapéutico</p>
        <div class="rastreo-interpret-body">${escapeHtml(response.answer).replace(/\n/g, "<br>")}</div>
      </div>`;
    } else {
      containerEl.innerHTML = `<p class="status error">No se pudo obtener interpretación.</p>`;
    }
  } catch {
    containerEl.innerHTML = `<p class="status error">Error al consultar el motor terapéutico.</p>`;
  }
}

// ─── Rastreo de Hologramas ─────────────────────────────────────────────────────
function renderTablaHologramas(p, content) {
  const state = { selected: null }; // { numero, nombre }

  function render() {
    const bloques = p.bloques || [];
    const bloqueHtml = bloques.map((bloque) => {
      const items = bloque.items.map((item) => {
        const isSelected = state.selected?.numero === item.numero;
        return `<div class="holo-item${isSelected ? " holo-item-selected" : ""}"
            data-num="${item.numero}">
          <span class="holo-num">${item.numero}</span>
          <span class="holo-nombre">${escapeHtml(item.nombre)}</span>
        </div>`;
      }).join("");
      return `<div class="holo-bloque">
        <div class="holo-bloque-label">${escapeHtml(bloque.label)} <span class="holo-bloque-rango">(${escapeHtml(bloque.rango)})</span></div>
        <div class="holo-grid">${items}</div>
      </div>`;
    }).join("");

    const guiaHtml = (p.pasos_guia || []).map((g) => `<li>${escapeHtml(g)}</li>`).join("");

    const selInfo = state.selected
      ? `<div class="rastreo-sel-box">
          <p class="rastreo-sel-label">Holograma identificado:</p>
          <p class="rastreo-sel-value">🔮 #${state.selected.numero} — ${escapeHtml(state.selected.nombre)}</p>
          ${state.selected.descripcion ? `<p class="rastreo-sel-desc">${escapeHtml(state.selected.descripcion)}</p>` : ""}
          <button class="rastreo-interpret-btn" id="holo-interpretar-btn">✨ Interpretar con el Motor Terapéutico</button>
        </div>` : "";

    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        <h2 class="wizard-protocol-name">${escapeHtml(p.nombre)}</h2>
        <div class="rastreo-instruccion-ms">
          <span class="rastreo-ms-badge">MS</span>
          <span>${escapeHtml(p.instruccion_ms || "")}</span>
        </div>
        <details class="rastreo-guia-details">
          <summary>📋 Guía de rastreo paso a paso</summary>
          <ol class="rastreo-guia-list">${guiaHtml}</ol>
        </details>
        <div class="holo-table">${bloqueHtml}</div>
        ${selInfo}
        <div id="holo-interpret-out"></div>
        <div class="wizard-nav">
          <button class="wizard-nav-btn wizard-reiniciar" id="holo-reset-btn">Reiniciar</button>
        </div>
      </div>`;

    content.querySelectorAll(".holo-item").forEach((el) => {
      el.addEventListener("click", () => {
        const num = parseInt(el.dataset.num);
        const bloquesAll = p.bloques || [];
        let found = null;
        for (const bl of bloquesAll) {
          found = bl.items.find((i) => i.numero === num);
          if (found) break;
        }
        if (state.selected?.numero === num) {
          state.selected = null;
        } else {
          state.selected = found || { numero: num, nombre: el.querySelector(".holo-nombre")?.textContent || "" };
        }
        render();
      });
    });

    content.getElementById?.("holo-reset-btn")?.addEventListener("click", () => {
      state.selected = null; render();
    });
    content.querySelector("#holo-reset-btn")?.addEventListener("click", () => {
      state.selected = null; render();
    });

    content.querySelector("#holo-interpretar-btn")?.addEventListener("click", async () => {
      const outEl = content.querySelector("#holo-interpret-out");
      if (!outEl || !state.selected) return;
      const query = `El rastreo de hologramas identificó: Holograma #${state.selected.numero} — "${state.selected.nombre}". ${state.selected.descripcion ? "Descripción: " + state.selected.descripcion : ""}\n\nDesde la perspectiva terapéutica holística: ¿Qué significa este holograma? ¿Cómo se manifiesta en el cuerpo y las emociones? ¿Qué datos adicionales es útil rastrear (recesión de edad, emoción-reacción, capa embrionaria, cromosoma, microbio, par biomagnético)? ¿Cómo se desartícula? Sé concreto y orientado a la sesión.`;
      await rastreoInterpretarIA(outEl, query);
    });
  }

  render();
}

// ─── Rastreo de Nudos Psóricos ─────────────────────────────────────────────────
function renderTablaNudosPsoricos(p, content) {
  const state = { selected: null }; // { numero, nombre }

  function render() {
    const raiz = p.raiz || {};
    const isRaizSel = state.selected?.numero === "0";
    const raizHtml = `<div class="nudo-raiz${isRaizSel ? " nudo-raiz-selected" : ""}" data-num="0">
      <span class="nudo-raiz-num">0</span>
      <span class="nudo-raiz-nombre">${escapeHtml(raiz.nombre || "Miedo a la vida, a vivir")}</span>
      <span class="nudo-raiz-badge">Raíz de todos los nudos</span>
    </div>`;

    const bloqueHtml = (p.bloques || []).map((bloque) => {
      const nudosHtml = bloque.nudos.map((nudo) => {
        const isSel = state.selected?.numero === String(nudo.numero);
        const submiedosHtml = (nudo.submiedos || []).map((s) =>
          `<span class="nudo-sub">${escapeHtml(s)}</span>`
        ).join("");
        return `<div class="nudo-item${isSel ? " nudo-item-selected" : ""}" data-num="${nudo.numero}">
          <div class="nudo-header">
            <span class="nudo-romano">${escapeHtml(nudo.romano)}</span>
            <span class="nudo-nombre">${escapeHtml(nudo.nombre)}</span>
          </div>
          ${submiedosHtml ? `<div class="nudo-submiedos">${submiedosHtml}</div>` : ""}
        </div>`;
      }).join("");
      return `<div class="nudo-bloque">
        <div class="nudo-bloque-label">${escapeHtml(bloque.label)}</div>
        <div class="nudo-grid">${nudosHtml}</div>
      </div>`;
    }).join("");

    const guiaHtml = (p.pasos_guia || []).map((g) => `<li>${escapeHtml(g)}</li>`).join("");

    const selInfo = state.selected
      ? `<div class="rastreo-sel-box">
          <p class="rastreo-sel-label">Nudo psórico identificado:</p>
          <p class="rastreo-sel-value">⚡ ${state.selected.numero !== "0" ? `Nudo ${state.selected.romano || state.selected.numero} — ` : ""}${escapeHtml(state.selected.nombre)}</p>
          <p class="rastreo-liberar-cmd">🧲 Liberar: <em>"Me libero consciente y subconscientemente del nudo psórico de ${escapeHtml(state.selected.nombre)}"</em> — pasar imán 10 veces.</p>
          <button class="rastreo-interpret-btn" id="nudo-interpretar-btn">✨ Interpretar con el Motor Terapéutico</button>
        </div>` : "";

    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        <h2 class="wizard-protocol-name">${escapeHtml(p.nombre)}</h2>
        <div class="rastreo-instruccion-ms">
          <span class="rastreo-ms-badge">MS</span>
          <span>${escapeHtml(p.instruccion_ms || "")}</span>
        </div>
        <details class="rastreo-guia-details">
          <summary>📋 Guía de rastreo paso a paso</summary>
          <ol class="rastreo-guia-list">${guiaHtml}</ol>
        </details>
        <div class="nudo-table">
          ${raizHtml}
          ${bloqueHtml}
        </div>
        ${selInfo}
        <div id="nudo-interpret-out"></div>
        <div class="wizard-nav">
          <button class="wizard-nav-btn wizard-reiniciar" id="nudo-reset-btn">Reiniciar</button>
        </div>
      </div>`;

    content.querySelectorAll(".nudo-item, .nudo-raiz").forEach((el) => {
      el.addEventListener("click", () => {
        const num = el.dataset.num;
        if (state.selected?.numero === String(num)) {
          state.selected = null;
        } else {
          if (num === "0") {
            state.selected = { numero: "0", nombre: raiz.nombre || "Miedo a la vida, a vivir" };
          } else {
            const numInt = parseInt(num);
            let found = null;
            for (const bl of (p.bloques || [])) {
              found = bl.nudos.find((n) => n.numero === numInt);
              if (found) break;
            }
            state.selected = found ? { numero: String(found.numero), romano: found.romano, nombre: found.nombre } : { numero: num, nombre: num };
          }
        }
        render();
      });
    });

    content.querySelector("#nudo-reset-btn")?.addEventListener("click", () => {
      state.selected = null; render();
    });

    content.querySelector("#nudo-interpretar-btn")?.addEventListener("click", async () => {
      const outEl = content.querySelector("#nudo-interpret-out");
      if (!outEl || !state.selected) return;
      const query = `El rastreo identificó el nudo psórico: "${state.selected.nombre}" (${state.selected.romano ? "Nudo " + state.selected.romano : "Nudo raíz 0"}).\n\nDesde la perspectiva terapéutica holística: ¿Qué es este nudo psórico? ¿Cómo se manifiesta emocionalmente y en el cuerpo? ¿Cuál es su origen (miasma, memoria ancestral, etapa de vida)? ¿Qué síntomas físicos o conductas puede generar cuando está activo? ¿Cómo se trabaja y libera de forma efectiva? Orienta para la sesión.`;
      await rastreoInterpretarIA(outEl, query);
    });
  }

  render();
}

// ─── Rastreo de Creencias Limitantes (tabla visual) ───────────────────────────
function renderTablaCreencias(p, content) {
  const state = {
    phase: "categoria",  // "categoria" | "creencias"
    selectedCat: null,   // category object
    selectedCreencia: null, // { texto, cat }
  };
  const tabla = p.tabla || {};
  const categorias = tabla.categorias || [];

  const CAT_COLORS = {
    violet: "#7c3aed", sky: "#0ea5e9", teal: "#14b8a6", amber: "#f59e0b",
    rose: "#f43f5e", emerald: "#10b981", indigo: "#6366f1", cyan: "#06b6d4",
    orange: "#f97316", purple: "#a855f7",
  };

  function render() {
    if (state.phase === "categoria") {
      renderCategoriasGrid();
    } else {
      renderCreenciasLista();
    }
  }

  function renderCategoriasGrid() {
    const guiaHtml = (p.pasos_guia || [
      "1. Abrir circuito bioenergético.",
      "2. MS: '¿Hay alguna creencia limitante activa?' → SÍ/NO",
      "3. MS: Preguntar categoría por categoría hasta confirmar cuál está activa.",
      "4. Dentro de la categoría, rastrear la creencia específica.",
      "5. Liberar con comando EFT PRO + instalar creencia positiva."
    ]).map((g) => `<li>${escapeHtml(g)}</li>`).join("");

    const catCards = categorias.map((cat) => {
      const color = CAT_COLORS[cat.color] || "#7c3aed";
      return `<div class="creencia-cat-card" data-cat="${cat.id}"
          style="border-color:${color}">
        <div class="creencia-cat-name" style="color:${color}">${escapeHtml(cat.nombre)}</div>
        <div class="creencia-cat-afirm">"${escapeHtml(cat.afirmacion_positiva)}"</div>
        <div class="creencia-cat-count">${cat.creencias?.length || 0} creencias</div>
      </div>`;
    }).join("");

    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        <h2 class="wizard-protocol-name">${escapeHtml(p.nombre)}</h2>
        <div class="rastreo-instruccion-ms">
          <span class="rastreo-ms-badge">MS</span>
          <span>¿Hay alguna creencia limitante activa relacionada con este conflicto?</span>
        </div>
        <details class="rastreo-guia-details">
          <summary>📋 Guía de rastreo</summary>
          <ol class="rastreo-guia-list">${guiaHtml}</ol>
        </details>
        <p class="creencia-instruccion-paso">Selecciona la categoría que responde SÍ con test muscular:</p>
        <div class="creencia-cat-grid">${catCards}</div>
        <div class="wizard-nav" style="margin-top:16px">
          <button class="wizard-nav-btn wizard-reiniciar" id="creencia-reset-btn">Reiniciar</button>
        </div>
      </div>`;

    content.querySelectorAll(".creencia-cat-card").forEach((el) => {
      el.addEventListener("click", () => {
        const catId = el.dataset.cat;
        state.selectedCat = categorias.find((c) => c.id === catId) || null;
        state.phase = "creencias";
        render();
      });
    });
    content.querySelector("#creencia-reset-btn")?.addEventListener("click", () => {
      state.phase = "categoria"; state.selectedCat = null; state.selectedCreencia = null; render();
    });
  }

  function renderCreenciasLista() {
    if (!state.selectedCat) { state.phase = "categoria"; render(); return; }
    const cat = state.selectedCat;
    const color = CAT_COLORS[cat.color] || "#7c3aed";
    const creencias = cat.creencias || [];
    const creenciasHtml = creencias.map((texto, idx) => {
      const isSel = state.selectedCreencia?.texto === texto;
      return `<div class="creencia-item${isSel ? " creencia-item-selected" : ""}"
          data-idx="${idx}" style="${isSel ? `border-color:${color};background:${color}15` : `border-color:#e2e8f0`}">
        <span class="creencia-num" style="${isSel ? `color:${color}` : ""}">${idx + 1}</span>
        <span class="creencia-texto">${escapeHtml(texto)}</span>
        ${isSel ? `<span class="creencia-check" style="color:${color}">✓</span>` : ""}
      </div>`;
    }).join("");

    const liberarHtml = state.selectedCreencia
      ? `<div class="rastreo-sel-box" style="border-color:${color}">
          <p class="rastreo-sel-label">Creencia identificada:</p>
          <p class="rastreo-sel-value" style="color:${color}">"${escapeHtml(state.selectedCreencia.texto)}"</p>
          <div class="creencia-liberar-cmd">
            <p class="creencia-liberar-title">🔓 Comando de liberación EFT PRO:</p>
            <p class="creencia-liberar-text">"Aunque he creído consciente o subconscientemente que ${escapeHtml(state.selectedCreencia.texto).toLowerCase().replace(/\.$/, "")} — me amo y me acepto. Decreto a partir de ahora y para siempre que ${escapeHtml(cat.afirmacion_positiva)}."</p>
          </div>
          <button class="rastreo-interpret-btn" id="creencia-interpretar-btn" style="background:${color}">✨ Interpretar con el Motor Terapéutico</button>
        </div>` : "";

    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        <h2 class="wizard-protocol-name">${escapeHtml(p.nombre)}</h2>
        <div class="creencia-cat-header" style="border-color:${color}">
          <span class="creencia-cat-badge" style="background:${color}">Categoría: ${escapeHtml(cat.nombre)}</span>
          <span class="creencia-cat-afirm-small">Meta: "${escapeHtml(cat.afirmacion_positiva)}"</span>
        </div>
        <p class="creencia-instruccion-paso">Selecciona la creencia específica que responde SÍ con test muscular:</p>
        <div class="creencia-lista">${creenciasHtml}</div>
        ${liberarHtml}
        <div id="creencia-interpret-out"></div>
        <div class="wizard-nav" style="margin-top:16px">
          <button class="wizard-nav-btn" id="creencia-back-btn">← Cambiar categoría</button>
          <button class="wizard-nav-btn wizard-reiniciar" id="creencia-reset-btn2">Reiniciar</button>
        </div>
      </div>`;

    content.querySelectorAll(".creencia-item").forEach((el) => {
      el.addEventListener("click", () => {
        const idx = parseInt(el.dataset.idx);
        const texto = creencias[idx];
        if (state.selectedCreencia?.texto === texto) {
          state.selectedCreencia = null;
        } else {
          state.selectedCreencia = { texto, cat: cat.id };
        }
        render();
      });
    });

    content.querySelector("#creencia-back-btn")?.addEventListener("click", () => {
      state.phase = "categoria"; state.selectedCreencia = null; render();
    });
    content.querySelector("#creencia-reset-btn2")?.addEventListener("click", () => {
      state.phase = "categoria"; state.selectedCat = null; state.selectedCreencia = null; render();
    });

    content.querySelector("#creencia-interpretar-btn")?.addEventListener("click", async () => {
      const outEl = content.querySelector("#creencia-interpret-out");
      if (!outEl || !state.selectedCreencia) return;
      const query = `El rastreo de creencias limitantes identificó la siguiente creencia activa:\nCategoría: ${cat.nombre}\nCreencia: "${state.selectedCreencia.texto}"\n\nDesde la perspectiva terapéutica holística: ¿Qué impacto tiene esta creencia en la vida de la persona? ¿Cuál es su probable origen (etapa de vida, experiencia formativa)? ¿Cómo se manifiesta en el cuerpo y en los patrones de conducta? ¿Cuál es la creencia positiva opuesta que hay que instalar? ¿Qué técnicas complementarias ayudan a anclar el nuevo programa? Orienta para la sesión de forma concreta.`;
      await rastreoInterpretarIA(outEl, query);
    });
  }

  render();
}

// ─── Rastreos Avanzados — módulo unificado con sidebar ─────────────────────────
function renderRastreosAvanzados(p, content) {
  const modulos = p.modulos || [];
  const outerState = { activeId: modulos[0]?.id || "hologramas" };

  // Emociones cache so we don't re-fetch on every re-render
  const emocionesCache = { data: null };

  function renderShell() {
    const navHtml = modulos.map((m) => `
      <div class="ra-nav-item${outerState.activeId === m.id ? " ra-nav-active" : ""}" data-mod="${m.id}">
        <span class="ra-nav-icon">${m.icono}</span>
        <span class="ra-nav-label">${escapeHtml(m.nombre)}</span>
      </div>
    `).join("");

    content.innerHTML = `
      <div class="ra-wrap">
        <div class="ra-sidebar">
          <div class="ra-sidebar-title">Rastreos Avanzados</div>
          <nav class="ra-nav">${navHtml}</nav>
        </div>
        <div class="ra-panel" id="ra-panel-content"></div>
      </div>`;

    content.querySelectorAll(".ra-nav-item").forEach((el) => {
      el.addEventListener("click", () => {
        outerState.activeId = el.dataset.mod;
        renderShell();
      });
    });

    const panelEl = content.querySelector("#ra-panel-content");
    const activeM = modulos.find((m) => m.id === outerState.activeId);
    if (panelEl && activeM) renderModuloPanel(activeM, panelEl);
  }

  function renderModuloPanel(modulo, panelEl) {
    if (modulo.id === "hologramas") renderRAHologramas(modulo, panelEl);
    else if (modulo.id === "nudos_psoricos") renderRANudos(modulo, panelEl);
    else if (modulo.id === "creencias") renderRACreencias(modulo, panelEl);
    else if (modulo.id === "emociones_eft") renderRAEmociones(modulo, panelEl);
  }

  // ── Hologramas ──────────────────────────────────────────────────────────────
  function renderRAHologramas(m, panelEl) {
    const state = { selected: null };
    function render() {
      const bloqueHtml = (m.bloques || []).map((bloque) => {
        const items = bloque.items.map((item) => {
          const isSel = state.selected?.numero === item.numero;
          return `<div class="holo-item${isSel ? " holo-item-selected" : ""}" data-num="${item.numero}">
            <span class="holo-num">${item.numero}</span>
            <span class="holo-nombre">${escapeHtml(item.nombre)}</span>
          </div>`;
        }).join("");
        return `<div class="holo-bloque">
          <div class="holo-bloque-label">${escapeHtml(bloque.label)} <span class="holo-bloque-rango">(${escapeHtml(bloque.rango)})</span></div>
          <div class="holo-grid">${items}</div>
        </div>`;
      }).join("");

      const guiaHtml = (m.pasos_guia || []).map((g) => `<li>${escapeHtml(g)}</li>`).join("");
      const selInfo = state.selected
        ? `<div class="rastreo-sel-box">
            <p class="rastreo-sel-label">Holograma identificado:</p>
            <p class="rastreo-sel-value">🔮 #${state.selected.numero} — ${escapeHtml(state.selected.nombre)}</p>
            ${state.selected.descripcion ? `<p class="rastreo-sel-desc">${escapeHtml(state.selected.descripcion)}</p>` : ""}
            <button class="rastreo-interpret-btn" id="holo-interpretar-btn">✨ Interpretar con el Motor Terapéutico</button>
          </div>` : "";

      panelEl.innerHTML = `
        <div class="rastreo-tabla-wrap">
          <div class="rastreo-instruccion-ms">
            <span class="rastreo-ms-badge">MS</span>
            <span>${escapeHtml(m.instruccion_ms || "")}</span>
          </div>
          <details class="rastreo-guia-details">
            <summary>📋 Guía de rastreo paso a paso</summary>
            <ol class="rastreo-guia-list">${guiaHtml}</ol>
          </details>
          <div class="holo-table">${bloqueHtml}</div>
          ${selInfo}
          <div id="holo-interpret-out"></div>
          <div class="wizard-nav"><button class="wizard-nav-btn wizard-reiniciar" id="holo-reset-btn">Reiniciar</button></div>
        </div>`;

      panelEl.querySelectorAll(".holo-item").forEach((el) => {
        el.addEventListener("click", () => {
          const num = parseInt(el.dataset.num);
          let found = null;
          for (const bl of (m.bloques || [])) { found = bl.items.find((i) => i.numero === num); if (found) break; }
          state.selected = state.selected?.numero === num ? null : (found || { numero: num, nombre: el.querySelector(".holo-nombre")?.textContent || "" });
          render();
        });
      });
      panelEl.querySelector("#holo-reset-btn")?.addEventListener("click", () => { state.selected = null; render(); });
      panelEl.querySelector("#holo-interpretar-btn")?.addEventListener("click", async () => {
        const outEl = panelEl.querySelector("#holo-interpret-out");
        if (!outEl || !state.selected) return;
        const query = `El rastreo de hologramas identificó: Holograma #${state.selected.numero} — "${state.selected.nombre}". ${state.selected.descripcion ? "Descripción: " + state.selected.descripcion : ""}\n\nDesde la perspectiva terapéutica holística: ¿Qué significa este holograma? ¿Cómo se manifiesta en el cuerpo y las emociones? ¿Qué datos adicionales es útil rastrear (recesión de edad, emoción-reacción, capa embrionaria, cromosoma, microbio, par biomagnético)? ¿Cómo se desartícula? Sé concreto y orientado a la sesión.`;
        await rastreoInterpretarIA(outEl, query);
      });
    }
    render();
  }

  // ── Nudos Psóricos ──────────────────────────────────────────────────────────
  function renderRANudos(m, panelEl) {
    const state = { selected: null };
    function render() {
      const raiz = m.raiz || {};
      const isRaizSel = state.selected?.numero === "0";
      const raizHtml = `<div class="nudo-raiz${isRaizSel ? " nudo-raiz-selected" : ""}" data-num="0">
        <span class="nudo-raiz-num">0</span>
        <span class="nudo-raiz-nombre">${escapeHtml(raiz.nombre || "Miedo a la vida, a vivir")}</span>
        <span class="nudo-raiz-badge">Raíz de todos los nudos</span>
      </div>`;

      const bloqueHtml = (m.bloques || []).map((bloque) => {
        const nudosHtml = bloque.nudos.map((nudo) => {
          const isSel = state.selected?.numero === String(nudo.numero);
          const submiedosHtml = (nudo.submiedos || []).map((s) => `<span class="nudo-sub">${escapeHtml(s)}</span>`).join("");
          return `<div class="nudo-item${isSel ? " nudo-item-selected" : ""}" data-num="${nudo.numero}">
            <div class="nudo-header">
              <span class="nudo-romano">${escapeHtml(nudo.romano)}</span>
              <span class="nudo-nombre">${escapeHtml(nudo.nombre)}</span>
            </div>
            ${submiedosHtml ? `<div class="nudo-submiedos">${submiedosHtml}</div>` : ""}
          </div>`;
        }).join("");
        return `<div class="nudo-bloque"><div class="nudo-bloque-label">${escapeHtml(bloque.label)}</div><div class="nudo-grid">${nudosHtml}</div></div>`;
      }).join("");

      const guiaHtml = (m.pasos_guia || []).map((g) => `<li>${escapeHtml(g)}</li>`).join("");
      const selInfo = state.selected
        ? `<div class="rastreo-sel-box">
            <p class="rastreo-sel-label">Nudo psórico identificado:</p>
            <p class="rastreo-sel-value">⚡ ${state.selected.numero !== "0" ? `Nudo ${state.selected.romano || state.selected.numero} — ` : ""}${escapeHtml(state.selected.nombre)}</p>
            <p class="rastreo-liberar-cmd">🧲 Liberar: <em>"Me libero consciente y subconscientemente del nudo psórico de ${escapeHtml(state.selected.nombre)}"</em> — pasar imán 10 veces.</p>
            <button class="rastreo-interpret-btn" id="nudo-interpretar-btn">✨ Interpretar con el Motor Terapéutico</button>
          </div>` : "";

      panelEl.innerHTML = `
        <div class="rastreo-tabla-wrap">
          <div class="rastreo-instruccion-ms">
            <span class="rastreo-ms-badge">MS</span>
            <span>${escapeHtml(m.instruccion_ms || "")}</span>
          </div>
          <details class="rastreo-guia-details">
            <summary>📋 Guía de rastreo paso a paso</summary>
            <ol class="rastreo-guia-list">${guiaHtml}</ol>
          </details>
          <div class="nudo-table">${raizHtml}${bloqueHtml}</div>
          ${selInfo}
          <div id="nudo-interpret-out"></div>
          <div class="wizard-nav"><button class="wizard-nav-btn wizard-reiniciar" id="nudo-reset-btn">Reiniciar</button></div>
        </div>`;

      panelEl.querySelectorAll(".nudo-item, .nudo-raiz").forEach((el) => {
        el.addEventListener("click", () => {
          const num = el.dataset.num;
          if (state.selected?.numero === String(num)) { state.selected = null; }
          else if (num === "0") { state.selected = { numero: "0", nombre: raiz.nombre || "Miedo a la vida, a vivir" }; }
          else {
            const numInt = parseInt(num);
            let found = null;
            for (const bl of (m.bloques || [])) { found = bl.nudos.find((n) => n.numero === numInt); if (found) break; }
            state.selected = found ? { numero: String(found.numero), romano: found.romano, nombre: found.nombre } : { numero: num, nombre: num };
          }
          render();
        });
      });
      panelEl.querySelector("#nudo-reset-btn")?.addEventListener("click", () => { state.selected = null; render(); });
      panelEl.querySelector("#nudo-interpretar-btn")?.addEventListener("click", async () => {
        const outEl = panelEl.querySelector("#nudo-interpret-out");
        if (!outEl || !state.selected) return;
        const query = `El rastreo identificó el nudo psórico: "${state.selected.nombre}" (${state.selected.romano ? "Nudo " + state.selected.romano : "Nudo raíz 0"}).\n\nDesde la perspectiva terapéutica holística: ¿Qué es este nudo psórico? ¿Cómo se manifiesta emocionalmente y en el cuerpo? ¿Cuál es su origen (miasma, memoria ancestral, etapa de vida)? ¿Qué síntomas físicos o conductas puede generar cuando está activo? ¿Cómo se trabaja y libera de forma efectiva? Orienta para la sesión.`;
        await rastreoInterpretarIA(outEl, query);
      });
    }
    render();
  }

  // ── Creencias Limitantes ────────────────────────────────────────────────────
  function renderRACreencias(m, panelEl) {
    const CAT_COLORS = {
      violet: "#7c3aed", sky: "#0ea5e9", teal: "#14b8a6", amber: "#f59e0b",
      rose: "#f43f5e", emerald: "#10b981", indigo: "#6366f1", cyan: "#06b6d4",
      orange: "#f97316", purple: "#a855f7",
    };
    const tabla = m.tabla || {};
    const categorias = tabla.categorias || [];
    const state = { phase: "categoria", selectedCat: null, selectedCreencia: null };

    function render() {
      if (state.phase === "categoria") renderCatGrid();
      else renderCreenciasLista();
    }

    function renderCatGrid() {
      const guiaHtml = (m.pasos_guia || [
        "1. Abrir circuito bioenergético.",
        "2. MS: '¿Hay alguna creencia limitante activa?' → SÍ/NO",
        "3. Preguntar categoría por categoría.",
        "4. Dentro de la categoría, rastrear la creencia específica.",
        "5. Liberar con comando EFT PRO + instalar creencia positiva."
      ]).map((g) => `<li>${escapeHtml(g)}</li>`).join("");

      const catCards = categorias.map((cat) => {
        const color = CAT_COLORS[cat.color] || "#7c3aed";
        return `<div class="creencia-cat-card" data-cat="${cat.id}" style="border-color:${color}">
          <div class="creencia-cat-name" style="color:${color}">${escapeHtml(cat.nombre)}</div>
          <div class="creencia-cat-afirm">"${escapeHtml(cat.afirmacion_positiva)}"</div>
          <div class="creencia-cat-count">${cat.creencias?.length || 0} creencias</div>
        </div>`;
      }).join("");

      panelEl.innerHTML = `
        <div class="rastreo-tabla-wrap">
          <div class="rastreo-instruccion-ms">
            <span class="rastreo-ms-badge">MS</span>
            <span>${escapeHtml(m.instruccion_ms || "¿Hay alguna creencia limitante activa relacionada con este conflicto?")}</span>
          </div>
          <details class="rastreo-guia-details">
            <summary>📋 Guía de rastreo</summary>
            <ol class="rastreo-guia-list">${guiaHtml}</ol>
          </details>
          <p class="creencia-instruccion-paso">Selecciona la categoría que responde SÍ con test muscular:</p>
          <div class="creencia-cat-grid">${catCards}</div>
          <div class="wizard-nav" style="margin-top:16px">
            <button class="wizard-nav-btn wizard-reiniciar" id="creencia-reset-btn">Reiniciar</button>
          </div>
        </div>`;

      panelEl.querySelectorAll(".creencia-cat-card").forEach((el) => {
        el.addEventListener("click", () => {
          state.selectedCat = categorias.find((c) => c.id === el.dataset.cat) || null;
          state.phase = "creencias";
          render();
        });
      });
      panelEl.querySelector("#creencia-reset-btn")?.addEventListener("click", () => {
        state.phase = "categoria"; state.selectedCat = null; state.selectedCreencia = null; render();
      });
    }

    function renderCreenciasLista() {
      if (!state.selectedCat) { state.phase = "categoria"; render(); return; }
      const cat = state.selectedCat;
      const color = CAT_COLORS[cat.color] || "#7c3aed";
      const creencias = cat.creencias || [];
      const creenciasHtml = creencias.map((texto, idx) => {
        const isSel = state.selectedCreencia?.texto === texto;
        return `<div class="creencia-item${isSel ? " creencia-item-selected" : ""}" data-idx="${idx}"
          style="${isSel ? `border-color:${color};background:${color}15` : "border-color:#e2e8f0"}">
          <span class="creencia-num" style="${isSel ? `color:${color}` : ""}">${idx + 1}</span>
          <span class="creencia-texto">${escapeHtml(texto)}</span>
          ${isSel ? `<span class="creencia-check" style="color:${color}">✓</span>` : ""}
        </div>`;
      }).join("");

      const liberarHtml = state.selectedCreencia
        ? `<div class="rastreo-sel-box" style="border-color:${color}">
            <p class="rastreo-sel-label">Creencia identificada:</p>
            <p class="rastreo-sel-value" style="color:${color}">"${escapeHtml(state.selectedCreencia.texto)}"</p>
            <div class="creencia-liberar-cmd">
              <p class="creencia-liberar-title">🔓 Comando EFT PRO:</p>
              <p class="creencia-liberar-text">"Aunque he creído consciente o subconscientemente que ${escapeHtml(state.selectedCreencia.texto).toLowerCase().replace(/\.$/, "")} — me amo y me acepto. Decreto a partir de ahora y para siempre que ${escapeHtml(cat.afirmacion_positiva)}."</p>
            </div>
            <button class="rastreo-interpret-btn" id="creencia-interpretar-btn" style="background:${color}">✨ Interpretar con el Motor Terapéutico</button>
          </div>` : "";

      panelEl.innerHTML = `
        <div class="rastreo-tabla-wrap">
          <div class="creencia-cat-header" style="border-color:${color}">
            <span class="creencia-cat-badge" style="background:${color}">Categoría: ${escapeHtml(cat.nombre)}</span>
            <span class="creencia-cat-afirm-small">Meta: "${escapeHtml(cat.afirmacion_positiva)}"</span>
          </div>
          <p class="creencia-instruccion-paso">Selecciona la creencia que responde SÍ con test muscular:</p>
          <div class="creencia-lista">${creenciasHtml}</div>
          ${liberarHtml}
          <div id="creencia-interpret-out"></div>
          <div class="wizard-nav" style="margin-top:16px">
            <button class="wizard-nav-btn" id="creencia-back-btn">← Cambiar categoría</button>
            <button class="wizard-nav-btn wizard-reiniciar" id="creencia-reset-btn2">Reiniciar</button>
          </div>
        </div>`;

      panelEl.querySelectorAll(".creencia-item").forEach((el) => {
        el.addEventListener("click", () => {
          const texto = creencias[parseInt(el.dataset.idx)];
          state.selectedCreencia = state.selectedCreencia?.texto === texto ? null : { texto, cat: cat.id };
          render();
        });
      });
      panelEl.querySelector("#creencia-back-btn")?.addEventListener("click", () => {
        state.phase = "categoria"; state.selectedCreencia = null; render();
      });
      panelEl.querySelector("#creencia-reset-btn2")?.addEventListener("click", () => {
        state.phase = "categoria"; state.selectedCat = null; state.selectedCreencia = null; render();
      });
      panelEl.querySelector("#creencia-interpretar-btn")?.addEventListener("click", async () => {
        const outEl = panelEl.querySelector("#creencia-interpret-out");
        if (!outEl || !state.selectedCreencia) return;
        const query = `El rastreo de creencias limitantes identificó:\nCategoría: ${cat.nombre}\nCreencia: "${state.selectedCreencia.texto}"\n\nDesde la perspectiva terapéutica holística: ¿Qué impacto tiene esta creencia? ¿Cuál es su probable origen? ¿Cómo se manifiesta en el cuerpo y conducta? ¿Cuál es la creencia positiva opuesta a instalar? ¿Qué técnicas complementarias ayudan? Orienta para la sesión.`;
        await rastreoInterpretarIA(outEl, query);
      });
    }

    render();
  }

  // ── Emociones Atrapadas & EFT ───────────────────────────────────────────────
  function renderRAEmociones(m, panelEl) {
    const state = { selected: null, eftVisible: false };
    const eftPasos = m.eft_pasos || [];

    async function render() {
      if (emocionesCache.data === null) {
        panelEl.innerHTML = `<div class="ra-loading"><div class="rastreo-interpret-spinner"></div><span>Cargando tabla de emociones...</span></div>`;
        try {
          const res = await fetch("/api/emociones/tabla");
          emocionesCache.data = res.ok ? await res.json() : { columnas: [] };
        } catch {
          emocionesCache.data = { columnas: [] };
        }
      }
      renderEmocionesInner();
    }

    function renderEmocionesInner() {
      const columnas = emocionesCache.data?.columnas || [];
      const instruccionMs = m.instruccion_ms || "¿Hay alguna emoción atrapada activa que esté contribuyendo a este conflicto?";

      // Build 6-column table: col header, then rows 1-5 (fila_a) and 6-10 (fila_b)
      const tableHeaderCols = columnas.map((c) =>
        `<th class="emoc-th">${escapeHtml(c.nombre)}</th>`
      ).join("");

      const rows = [];
      for (let rowIdx = 0; rowIdx < 5; rowIdx++) {
        const filaA = columnas.map((c) => {
          const item = c.fila_a?.[rowIdx];
          if (!item) return `<td class="emoc-td"></td>`;
          const isSel = state.selected?.nombre === item.nombre && state.selected?.col === c.num && state.selected?.fila === "a" && state.selected?.rowIdx === rowIdx;
          return `<td class="emoc-td emoc-cell${isSel ? " emoc-cell-selected" : ""}"
            data-col="${c.num}" data-fila="a" data-rowidx="${rowIdx}"
            data-nombre="${escapeHtml(item.nombre)}" data-organo="${escapeHtml(item.organo || c.nombre)}">
            ${escapeHtml(item.nombre)}
          </td>`;
        }).join("");
        rows.push(`<tr class="emoc-row-a"><td class="emoc-row-num">${rowIdx + 1}</td>${filaA}</tr>`);
      }
      for (let rowIdx = 0; rowIdx < 5; rowIdx++) {
        const filaB = columnas.map((c) => {
          const item = c.fila_b?.[rowIdx];
          if (!item) return `<td class="emoc-td"></td>`;
          const isSel = state.selected?.nombre === item.nombre && state.selected?.col === c.num && state.selected?.fila === "b" && state.selected?.rowIdx === rowIdx;
          return `<td class="emoc-td emoc-cell${isSel ? " emoc-cell-selected" : ""}"
            data-col="${c.num}" data-fila="b" data-rowidx="${rowIdx}"
            data-nombre="${escapeHtml(item.nombre)}" data-organo="${escapeHtml(item.organo || c.nombre)}">
            ${escapeHtml(item.nombre)}
          </td>`;
        }).join("");
        rows.push(`<tr class="emoc-row-b"><td class="emoc-row-num">${rowIdx + 6}</td>${filaB}</tr>`);
      }

      const selInfo = state.selected
        ? `<div class="rastreo-sel-box">
            <p class="rastreo-sel-label">Emoción atrapada identificada:</p>
            <p class="rastreo-sel-value">💜 ${escapeHtml(state.selected.nombre)}</p>
            <p class="emoc-organo-label">Órgano asociado: <strong>${escapeHtml(state.selected.organo)}</strong></p>
            <div class="emoc-actions">
              <button class="rastreo-interpret-btn" id="emoc-interpretar-btn">✨ Interpretar con el Motor Terapéutico</button>
              <button class="wizard-nav-btn emoc-eft-btn" id="emoc-eft-toggle">${state.eftVisible ? "▲ Ocultar protocolo EFT" : "💜 Ver protocolo EFT de liberación"}</button>
            </div>
          </div>` : "";

      const eftHtml = state.eftVisible && state.selected
        ? `<div class="eft-pasos-wrap">
            <h4 class="eft-pasos-title">Protocolo EFT — Liberación de "${escapeHtml(state.selected.nombre)}"</h4>
            <ol class="eft-pasos-list">
              ${eftPasos.map((paso) => `<li class="eft-paso-item">
                <span class="eft-paso-punto">${escapeHtml(paso.zona || paso.punto || "")}</span>
                <span class="eft-paso-afirmacion">"${escapeHtml((paso.frase || paso.afirmacion || "").replace(/\[emoción\]|\[emocion\]/gi, state.selected.nombre))}"</span>
              </li>`).join("")}
            </ol>
          </div>` : "";

      panelEl.innerHTML = `
        <div class="rastreo-tabla-wrap">
          <div class="rastreo-instruccion-ms">
            <span class="rastreo-ms-badge">MS</span>
            <span>${escapeHtml(instruccionMs)}</span>
          </div>
          <p class="creencia-instruccion-paso">Selecciona la emoción que responde SÍ con test muscular:</p>
          <div class="emoc-table-scroll">
            <table class="emoc-table">
              <thead><tr><th class="emoc-th emoc-th-num">#</th>${tableHeaderCols}</tr></thead>
              <tbody>${rows.join("")}</tbody>
            </table>
          </div>
          ${selInfo}
          <div id="emoc-interpret-out"></div>
          ${eftHtml}
          <div class="wizard-nav">
            <button class="wizard-nav-btn wizard-reiniciar" id="emoc-reset-btn">Reiniciar</button>
          </div>
        </div>`;

      panelEl.querySelectorAll(".emoc-cell").forEach((el) => {
        el.addEventListener("click", () => {
          const nombre = el.dataset.nombre;
          const col = parseInt(el.dataset.col);
          const fila = el.dataset.fila;
          const rowIdx = parseInt(el.dataset.rowidx);
          const organo = el.dataset.organo;
          if (state.selected?.nombre === nombre && state.selected?.col === col) {
            state.selected = null;
          } else {
            state.selected = { nombre, col, fila, rowIdx, organo };
          }
          state.eftVisible = false;
          renderEmocionesInner();
        });
      });
      panelEl.querySelector("#emoc-reset-btn")?.addEventListener("click", () => {
        state.selected = null; state.eftVisible = false; renderEmocionesInner();
      });
      panelEl.querySelector("#emoc-eft-toggle")?.addEventListener("click", () => {
        state.eftVisible = !state.eftVisible; renderEmocionesInner();
      });
      panelEl.querySelector("#emoc-interpretar-btn")?.addEventListener("click", async () => {
        const outEl = panelEl.querySelector("#emoc-interpret-out");
        if (!outEl || !state.selected) return;
        const query = `El rastreo identificó la emoción atrapada: "${state.selected.nombre}" (órgano asociado: ${state.selected.organo}).\n\nDesde la perspectiva terapéutica holística: ¿Cómo se formó esta emoción atrapada? ¿Cómo impacta en el cuerpo, el órgano asociado y en los patrones de conducta? ¿Cuál es la probable experiencia de vida que la originó? ¿Cómo se libera de forma efectiva con EFT y magnetismo? ¿Qué cambios puede notar el paciente tras la liberación? Orienta para la sesión.`;
        await rastreoInterpretarIA(outEl, query);
      });
    }

    render();
  }

  renderShell();
}

// ─── Tool Link Card ─────────────────────────────────────────────────────────
// Generic renderer for standalone tools that open in a new tab
function renderToolLink(p, content) {
  const url = p.tool_url || "/astro-home";
  const icon = p.tool_icon || "🔗";
  content.innerHTML = `
    <div class="rastreo-tabla-wrap">
      <div class="tl-card">
        <div class="tl-icon">${icon}</div>
        <h3 class="tl-nombre">${escapeHtml(p.nombre)}</h3>
        <p class="tl-objetivo">${escapeHtml(p.objetivo || "")}</p>
        ${(p.cuando_usarlo||[]).length > 0 ? `
          <div class="tl-cuando">
            <div class="tl-sec-label">Cuándo usarlo</div>
            <ul class="luna-lista">${(p.cuando_usarlo||[]).map(c=>`<li>${escapeHtml(c)}</li>`).join("")}</ul>
          </div>` : ""}
        <a href="${escapeHtml(url)}" target="_blank" class="tl-btn">
          Abrir ${escapeHtml(p.nombre)} →
        </a>
      </div>
    </div>`;
}

// ─── Numerología Terapéutica ────────────────────────────────────────────────
function renderNumerologiaTerapeutica(p, content) {
  const _act = paGetActivo();
  const _pac = _act?.paciente;
  const state = {
    nombre: _pac ? `${_pac.nombre || ""} ${_pac.apellidos || ""}`.trim() : "",
    fecha: _pac?.fecha_nacimiento || "",
    resultado: null,
  };

  function render() {
    const act = paGetActivo();
    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        ${act && state.nombre ? `<div class="pa-prefill-note">📋 Datos de <strong>${escapeHtml(state.nombre)}</strong> precargados desde su expediente</div>` : ""}
        <div class="rastreo-instruccion-ms">
          <span class="rastreo-ms-badge">🔢</span>
          <span>${escapeHtml(p.instruccion_ms || "Ingresa el nombre completo y fecha de nacimiento del consultante.")}</span>
        </div>
        <div class="cn-form">
          <div class="casos-form-group">
            <label class="casos-label">Nombre completo del consultante</label>
            <input class="casos-input" id="num-nombre" placeholder="Nombre y apellidos completos" value="${escapeHtml(state.nombre)}">
          </div>
          <div class="casos-form-group">
            <label class="casos-label">Fecha de nacimiento</label>
            <input class="casos-input" id="num-fecha" type="date" value="${escapeHtml(state.fecha)}">
          </div>
          <div id="num-error" class="casos-form-error" style="display:none"></div>
          <div class="wizard-nav" style="margin-top:14px">
            <button class="wizard-nav-btn vort-ia-btn" id="num-calcular" style="width:100%">
              🔢 Calcular Perfil Numerológico
            </button>
          </div>
        </div>
        <div class="cn-link-full">
          <a href="/numerologia" target="_blank" class="cn-ext-link">Herramienta numerológica completa →</a>
        </div>
        ${state.resultado ? renderResultado() : ""}
        <div id="num-interp-out"></div>
      </div>`;

    content.querySelector("#num-calcular")?.addEventListener("click", () => {
      const nombre = content.querySelector("#num-nombre")?.value.trim();
      const fecha  = content.querySelector("#num-fecha")?.value;
      const errEl  = content.querySelector("#num-error");
      if (!nombre || !fecha) { errEl.textContent = "Ingresa nombre y fecha."; errEl.style.display = "block"; return; }
      errEl.style.display = "none";
      state.nombre = nombre;
      state.fecha = fecha;
      state.resultado = calcularNumerologia(nombre, fecha);
      const r = state.resultado;
      paRegistrar("Numerología", `Perfil numerológico de ${nombre}`,
        `Camino de Vida ${r.camino} · Expresión ${r.expresion} · Alma ${r.alma}`);
      render();
      // Auto-interpret
      setTimeout(() => interpretarNumerologia(), 200);
    });
    content.querySelector("#num-interp-btn")?.addEventListener("click", interpretarNumerologia);
  }

  function calcularNumerologia(nombre, fecha) {
    // Reduce a single digit (or master number 11, 22, 33)
    function reduce(n) {
      while (n > 9 && n !== 11 && n !== 22 && n !== 33) {
        n = String(n).split("").reduce((a, d) => a + parseInt(d), 0);
      }
      return n;
    }
    // Letter to number (Pythagorean)
    const letterVal = {a:1,b:2,c:3,d:4,e:5,f:6,g:7,h:8,i:9,j:1,k:2,l:3,m:4,n:5,o:6,p:7,q:8,r:9,s:1,t:2,u:3,v:4,w:5,x:6,y:7,z:8};
    const vowels = new Set("aeiou");
    const clean = nombre.toLowerCase().replace(/[^a-záéíóúüñ]/g, "")
      .replace(/á/g,"a").replace(/é/g,"e").replace(/í/g,"i").replace(/ó/g,"o").replace(/ú/g,"u").replace(/ü/g,"u").replace(/ñ/g,"n");

    // Número de Expresión (todos las letras)
    const expresion = reduce(clean.split("").reduce((a,c) => a + (letterVal[c]||0), 0));

    // Número del Alma / Impulso del Alma (vocales)
    const alma = reduce(clean.split("").filter(c => vowels.has(c)).reduce((a,c) => a + (letterVal[c]||0), 0));

    // Número de Personalidad (consonantes)
    const personalidad = reduce(clean.split("").filter(c => !vowels.has(c)).reduce((a,c) => a + (letterVal[c]||0), 0));

    // Número de Camino de Vida (fecha)
    const [y, m, d] = fecha.split("-").map(Number);
    const camino = reduce(reduce(d) + reduce(m) + reduce(y));

    // Número del Destino / Misión (similar a camino con fórmula alternativa)
    const mision = reduce(d + m + reduce(y));

    return { expresion, alma, personalidad, camino, mision };
  }

  function renderResultado() {
    const r = state.resultado;
    if (!r) return "";
    const nums = [
      { label: "Camino de Vida",  value: r.camino,      desc: "El propósito principal de esta vida" },
      { label: "Expresión",       value: r.expresion,    desc: "Talentos naturales y forma de expresarse" },
      { label: "Impulso del Alma",value: r.alma,         desc: "Motivación más profunda del ser" },
      { label: "Personalidad",    value: r.personalidad, desc: "Cómo los demás perciben al consultante" },
      { label: "Misión",          value: r.mision,       desc: "Lección o deuda kármica del ciclo" },
    ];
    return `
      <div class="num-resultado">
        <div class="num-nombre-display">🔢 ${escapeHtml(state.nombre)}</div>
        <div class="num-grid">
          ${nums.map(n => `
            <div class="num-card">
              <div class="num-card-num">${n.value}</div>
              <div class="num-card-label">${n.label}</div>
              <div class="num-card-desc">${n.desc}</div>
            </div>`).join("")}
        </div>
        <div class="wizard-nav" style="margin-top:14px">
          <button class="wizard-nav-btn vort-ia-btn" id="num-interp-btn" style="width:100%">
            🧠 Interpretación terapéutica completa
          </button>
        </div>
      </div>`;
  }

  async function interpretarNumerologia() {
    const outEl = content.querySelector("#num-interp-out");
    if (!outEl || !state.resultado) return;
    const r = state.resultado;
    const query = `Consultante: ${state.nombre}. Fecha de nacimiento: ${state.fecha}.\n\nPerfil numerológico:\n- Camino de Vida: ${r.camino}\n- Expresión: ${r.expresion}\n- Impulso del Alma: ${r.alma}\n- Personalidad: ${r.personalidad}\n- Misión: ${r.mision}\n\nDesde la perspectiva terapéutica holística:\n1. ¿Qué propósito y misión de vida expresa este perfil numerológico?\n2. ¿Qué desafíos kármicos o patrones repetitivos son más probables?\n3. ¿Cómo se relacionan estos números con posibles síntomas físicos o emocionales?\n4. ¿Qué tipo de trabajo terapéutico resuena más con este perfil?\n5. ¿Qué fortalezas y recursos innatos tiene este consultante para su sanación?\n6. ¿Qué mensaje o aprendizaje principal trae este ciclo de vida?\n\nSé concreto, profundo y orientado a la sesión terapéutica.`;
    await rastreoInterpretarIA(outEl, query);
  }

  render();
}

// ─── Guía de Sueños ─────────────────────────────────────────────────────────
const SUENO_DIMENSIONES = [
  { id: "todas",         label: "Análisis completo",     icono: "🌌", desc: "Todas las dimensiones integradas" },
  { id: "psicosomatica", label: "Psicosomática",         icono: "🧬", desc: "Síntomas y órganos del sueño" },
  { id: "transgeneracional", label: "Transgeneracional", icono: "🌳", desc: "Patrones familiares y ancestrales" },
  { id: "mtc",           label: "MTC & Energía",         icono: "☯️", desc: "Meridianos, elementos y Qi" },
  { id: "numerologia",   label: "Numerología",           icono: "🔢", desc: "Números y ciclos en el sueño" },
  { id: "biodecodificacion", label: "Biodescodificación", icono: "💜", desc: "Conflicto biológico expresado" },
];

function renderSuenoTerapeutico(p, content) {
  const state = {
    sueno: "",
    contexto: "",
    dimension: "todas",
    fase: "input",  // "input" | "resultado"
  };

  function renderInput() {
    const dimHtml = SUENO_DIMENSIONES.map(d => `
      <div class="sueno-dim-chip${state.dimension === d.id ? " sueno-dim-active" : ""}" data-dim="${d.id}" title="${d.desc}">
        <span>${d.icono}</span><span>${d.label}</span>
      </div>`).join("");

    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        <div class="rastreo-instruccion-ms">
          <span class="rastreo-ms-badge">💤</span>
          <span>${escapeHtml(p.instruccion_ms || "Describe el sueño del consultante con el mayor detalle posible.")}</span>
        </div>

        <div class="cn-form">
          <div class="casos-form-group">
            <label class="casos-label">Describe el sueño</label>
            <textarea class="vort-ia-textarea" id="sueno-texto" rows="5"
              placeholder="Describe el sueño con todos los detalles: personajes, lugares, emociones, colores, objetos, acciones, sensaciones al despertar...">${escapeHtml(state.sueno)}</textarea>
          </div>
          <div class="casos-form-group">
            <label class="casos-label">Contexto del consultante (opcional)</label>
            <textarea class="vort-ia-textarea" id="sueno-contexto" rows="2"
              placeholder="Ej: está pasando por un duelo, tiene síntomas de ansiedad, sueño recurrente desde hace 3 meses...">${escapeHtml(state.contexto)}</textarea>
          </div>
        </div>

        <div class="sueno-dims-wrap">
          <label class="sint-label">Enfoque del análisis:</label>
          <div class="sueno-dims-grid">${dimHtml}</div>
        </div>

        <div id="sueno-error" class="casos-form-error" style="display:none">Describe el sueño antes de continuar.</div>

        <div class="wizard-nav" style="margin-top:16px">
          <button class="wizard-nav-btn vort-ia-btn" id="sueno-interpretar" style="width:100%">
            🌌 Interpretar sueño
          </button>
        </div>
      </div>`;

    content.querySelectorAll(".sueno-dim-chip").forEach(el => {
      el.addEventListener("click", () => { state.dimension = el.dataset.dim; renderInput(); });
    });
    content.querySelector("#sueno-texto")?.addEventListener("input", e => { state.sueno = e.target.value; });
    content.querySelector("#sueno-contexto")?.addEventListener("input", e => { state.contexto = e.target.value; });
    content.querySelector("#sueno-interpretar")?.addEventListener("click", async () => {
      const txt = content.querySelector("#sueno-texto")?.value.trim();
      const ctx = content.querySelector("#sueno-contexto")?.value.trim();
      if (!txt) { content.querySelector("#sueno-error").style.display = "block"; return; }
      state.sueno = txt; state.contexto = ctx || "";
      state.fase = "resultado";
      await renderResultado();
    });
  }

  async function renderResultado() {
    const dim = SUENO_DIMENSIONES.find(d => d.id === state.dimension) || SUENO_DIMENSIONES[0];

    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        <div class="ra-loading">
          <div class="rastreo-interpret-spinner"></div>
          <span>El Motor está interpretando el sueño desde ${dim.icono} ${dim.label}…</span>
        </div>
      </div>`;

    const seccionesPorDim = {
      todas: `
## 🧬 PSICOSOMÁTICA Y SIMBOLISMO CORPORAL
¿Qué órganos, partes del cuerpo o síntomas aparecen en el sueño? ¿Qué conflicto emocional expresan según la psicosomática? ¿Qué función biológica están comunicando?

## 🌳 PATRONES TRANSGENERACIONALES
¿Qué figuras familiares aparecen (directa o simbólicamente)? ¿Qué lealtades invisibles, mandatos o misiones reparadoras podría estar expresando el sueño? ¿Hay fechas, lugares o situaciones que remitan al árbol genealógico?

## ☯️ MEDICINA TRADICIONAL CHINA
¿Qué elemento (Madera, Fuego, Tierra, Metal, Agua) domina el sueño? ¿Qué meridianos u órganos energéticos están implicados? ¿El sueño ocurre en algún horario especial que corresponda a un meridiano?

## 🔢 NUMEROLOGÍA Y CICLOS
¿Aparecen números, cantidades, fechas o repeticiones? ¿Cómo se relacionan con el número de vida del consultante o con el año personal?

## 💜 BIODESCODIFICACIÓN
¿Qué conflicto biológico de choque (DHS) podría estar procesando el inconsciente? ¿Qué emoción primaria domina el sueño? ¿Es un sueño de fase de reparación o de conflicto activo?

## 🌌 SÍNTESIS Y ORIENTACIÓN TERAPÉUTICA
Integra todos los análisis anteriores en un mensaje coherente. ¿Qué está procesando el inconsciente? ¿Qué acción terapéutica sugiere el sueño para la próxima sesión?`,
      psicosomatica: `## 🧬 PSICOSOMÁTICA Y SIMBOLISMO CORPORAL\nAnaliza en profundidad: órganos implicados, síntomas simbólicos, conflicto biológico expresado, qué función orgánica está comunicando el sueño, qué parte del cuerpo está hablando y por qué.`,
      transgeneracional: `## 🌳 PATRONES TRANSGENERACIONALES\nAnaliza en profundidad: figuras del árbol genealógico, mandatos y lealtades familiares, misiones reparadoras, fechas y lugares simbólicos, qué generación está procesando este sueño, qué secreto familiar podría estar emergiendo.`,
      mtc: `## ☯️ MEDICINA TRADICIONAL CHINA\nAnaliza en profundidad: elemento dominante del sueño, meridianos y órganos energéticos implicados, correspondencias con las 5 emociones de la MTC (Ira/Madera, Alegría/Fuego, Preocupación/Tierra, Tristeza/Metal, Miedo/Agua), posibles puntos de acupuntura a trabajar.`,
      numerologia: `## 🔢 NUMEROLOGÍA Y CICLOS ONÍRICOS\nAnaliza en profundidad: todos los números que aparecen, fechas y su reducción numerológica, patrones de repetición, conexión con el ciclo de vida del consultante, qué energía numerológica está procesando.`,
      biodecodificacion: `## 💜 BIODESCODIFICACIÓN DEL SUEÑO\nAnaliza en profundidad: el conflicto biológico de choque detrás del sueño, si es sueño de reparación (fase de solución) o de conflicto activo, la emoción primaria dominante, el órgano o tejido implicado según el tipo de conflicto, el programa biológico de supervivencia que se está procesando.`,
    };

    const seccion = seccionesPorDim[state.dimension] || seccionesPorDim.todas;
    const ctxStr = state.contexto ? `\n\nContexto del consultante: ${state.contexto}` : "";

    const prompt = `Eres el Motor de Sueños de HoloacademIA — un terapeuta holístico experto en interpretación onírica integrativa.

SUEÑO DEL CONSULTANTE:
"${state.sueno}"${ctxStr}

Interpreta este sueño con profundidad clínica y orientación terapéutica. Sé concreto, simbólico y práctico. No añadas disclaimers. Responde directamente con las siguientes secciones:

${seccion}`;

    try {
      const res = await postJson("/academic/ask", { query: prompt, history: [] });
      const answer = res?.answer || "";
      const html = answer
        .replace(/^## (.+)$/gm, '<h3 class="ch-section-title">$1</h3>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/^[•\-] (.+)$/gm, '<li>$1</li>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

      content.innerHTML = `
        <div class="rastreo-tabla-wrap">
          <div class="sueno-result-header">
            <div class="sueno-dim-badge">${dim.icono} ${dim.label}</div>
            <div class="sueno-sueño-preview">"${escapeHtml(state.sueno.slice(0, 80))}${state.sueno.length > 80 ? "…" : ""}"</div>
          </div>
          <div class="ch-content"><p>${html}</p></div>
          <div class="wizard-nav" style="margin-top:20px">
            <button class="wizard-nav-btn" id="sueno-nuevo">← Nuevo sueño</button>
            <button class="wizard-nav-btn vort-ia-btn" id="sueno-otra-dim">🔄 Otra dimensión</button>
          </div>
        </div>`;

      content.querySelector("#sueno-nuevo")?.addEventListener("click", () => {
        state.sueno = ""; state.contexto = ""; state.fase = "input"; renderInput();
      });
      content.querySelector("#sueno-otra-dim")?.addEventListener("click", () => {
        state.fase = "input"; renderInput();
      });
    } catch {
      content.innerHTML = `<div class="rastreo-tabla-wrap"><p class="status error">Error al interpretar el sueño. Intenta de nuevo.</p><div class="wizard-nav"><button class="wizard-nav-btn" id="sueno-retry">← Volver</button></div></div>`;
      content.querySelector("#sueno-retry")?.addEventListener("click", () => { state.fase = "input"; renderInput(); });
    }
  }

  renderInput();
}

// ─── Carta Natal ────────────────────────────────────────────────────────────
const CN_PLANETA_ES = {
  Sun:'Sol', Moon:'Luna', Mercury:'Mercurio', Venus:'Venus', Mars:'Marte',
  Jupiter:'Júpiter', Saturn:'Saturno', Uranus:'Urano', Neptune:'Neptuno',
  Pluto:'Plutón', Chiron:'Quirón', Ascendant:'Ascendente', Medium_Coeli:'Medio Cielo',
  True_South_Lunar_Node:'Nodo Sur', True_Node:'Nodo Norte', Mean_Lilith:'Lilith'
};
const CN_GLIFO = {
  Sun:'☉', Moon:'☽', Mercury:'☿', Venus:'♀', Mars:'♂', Jupiter:'♃',
  Saturn:'♄', Uranus:'♅', Neptune:'♆', Pluto:'♇', Chiron:'⚷',
  Ascendant:'AC', Medium_Coeli:'MC', True_Node:'☊', True_South_Lunar_Node:'☋', Mean_Lilith:'⚸'
};
const CN_SIGNO_ES = {
  Ari:'Aries',Tau:'Tauro',Gem:'Géminis',Can:'Cáncer',Leo:'Leo',Vir:'Virgo',
  Lib:'Libra',Sco:'Escorpio',Sag:'Sagitario',Cap:'Capricornio',Aqu:'Acuario',Pis:'Piscis'
};
const CN_CASA_ES = {
  First:'I', Second:'II', Third:'III', Fourth:'IV', Fifth:'V', Sixth:'VI',
  Seventh:'VII', Eighth:'VIII', Ninth:'IX', Tenth:'X', Eleventh:'XI', Twelfth:'XII'
};

function renderCartaNatal(p, content) {
  const state = { phase:"form", svgHtml:null, posData:null, params:null, activePlanet:null };

  function render() {
    if (state.phase === "form") renderCnForm();
    else renderCnChart();
  }

  function renderCnForm() {
    const act = paGetActivo();
    const pac = act?.paciente;
    const preNombre = pac ? `${pac.nombre || ""} ${pac.apellidos || ""}`.trim() : "";
    const preFecha  = pac?.fecha_nacimiento || "";
    const preLugar  = pac?.lugar_nacimiento || "";
    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        ${act ? `<div class="pa-prefill-note">📋 Datos de <strong>${escapeHtml(preNombre)}</strong> precargados desde su expediente</div>` : ""}
        <div class="rastreo-instruccion-ms">
          <span class="rastreo-ms-badge">♈</span>
          <span>${escapeHtml(p.instruccion_ms || "Ingresa los datos de nacimiento del consultante.")}</span>
        </div>
        <div class="cn-form">
          <div class="casos-form-group">
            <label class="casos-label">Nombre del consultante</label>
            <input class="casos-input" id="cn-nombre" placeholder="Nombre completo" value="${escapeHtml(preNombre)}">
          </div>
          <div class="casos-form-row">
            <div class="casos-form-group">
              <label class="casos-label">Fecha de nacimiento</label>
              <input class="casos-input" id="cn-fecha" type="date" value="${escapeHtml(preFecha)}">
            </div>
            <div class="casos-form-group">
              <label class="casos-label">Hora</label>
              <input class="casos-input" id="cn-hora" type="time" value="12:00">
            </div>
          </div>
          <div class="casos-form-group">
            <label class="casos-label">Lugar de nacimiento</label>
            <input class="casos-input" id="cn-lugar" placeholder="Ciudad, País" value="${escapeHtml(preLugar)}">
          </div>
          <div id="cn-error" class="casos-form-error" style="display:none"></div>
          <div class="wizard-nav" style="margin-top:14px">
            <button class="wizard-nav-btn vort-ia-btn" id="cn-generar" style="width:100%">
              🌌 Generar Carta Natal
            </button>
          </div>
        </div>
        <div class="cn-link-full">
          <a href="/astro" target="_blank" class="cn-ext-link">Análisis astrológico completo →</a>
        </div>
      </div>`;

    content.querySelector("#cn-generar")?.addEventListener("click", async () => {
      const nombre = content.querySelector("#cn-nombre")?.value.trim() || "Consultante";
      const fecha  = content.querySelector("#cn-fecha")?.value;
      const hora   = content.querySelector("#cn-hora")?.value || "12:00";
      const lugar  = content.querySelector("#cn-lugar")?.value.trim();
      const errEl  = content.querySelector("#cn-error");
      if (!fecha || !lugar) { errEl.textContent = "Ingresa fecha y lugar."; errEl.style.display = "block"; return; }
      errEl.style.display = "none";
      state.params = { nombre, fecha, hora, lugar };
      state.phase = "chart";
      // Guarda el lugar de nacimiento en el expediente si el paciente activo no lo tenía
      const act = paGetActivo();
      if (act && lugar && !act.paciente.lugar_nacimiento) {
        act.paciente.lugar_nacimiento = lugar;
        casosDbSave(act.db);
      }
      paRegistrar("Astrología", `Carta natal generada (${fecha})`, lugar ? `Lugar: ${lugar}` : "");
      content.innerHTML = `<div class="rastreo-tabla-wrap"><div class="ra-loading"><div class="rastreo-interpret-spinner"></div><span>Calculando posiciones planetarias para ${escapeHtml(nombre)}...</span></div></div>`;
      await loadCnChart();
    });
  }

  async function loadCnChart() {
    const { nombre, fecha, hora, lugar } = state.params;
    const params = new URLSearchParams({ nombre, fecha, hora, lugar, tipo: "natal" });
    try {
      const [svgRes, posRes] = await Promise.all([
        fetch(`/astro/carta?${params}`),
        fetch(`/astro/datos-carta?${params}`),
      ]);
      state.svgHtml = svgRes.ok ? await svgRes.text() : null;
      state.posData = posRes.ok ? await posRes.json() : null;
    } catch { state.svgHtml = null; }
    renderCnChart();
  }

  function renderCnChart() {
    const { nombre, fecha } = state.params || {};
    const planetas = state.posData?.planetas || {};
    const mainKeys = ["sun","moon","mercury","venus","mars","jupiter","saturn","ascendant"];

    const planetBarHtml = mainKeys.map((key) => {
      const info = planetas[key]; if (!info) return "";
      const slug = key === "ascendant" ? "Ascendant" : key.charAt(0).toUpperCase() + key.slice(1);
      const signo = CN_SIGNO_ES[info.sign_abbr] || info.sign || "";
      return `<div class="cn-planet-chip" data-slug="${slug}">
        <span class="cn-planet-glyph">${CN_GLIFO[slug] || "★"}</span>
        <span class="cn-planet-signo">${signo}${info.retrograde ? " ℞" : ""}</span>
        <span class="cn-planet-name">${CN_PLANETA_ES[slug] || slug}</span>
      </div>`;
    }).join("");

    content.innerHTML = `
      <div class="rastreo-tabla-wrap cn-chart-wrap">
        <div class="cn-chart-header">
          <div>
            <div class="cn-chart-nombre">🌌 ${escapeHtml(nombre || "Carta Natal")}</div>
            <div class="cn-chart-fecha">${escapeHtml(fecha || "")}</div>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <a href="/astro" target="_blank" class="cn-ext-link">Análisis completo →</a>
            <button class="wizard-nav-btn" id="cn-nueva">← Nueva</button>
          </div>
        </div>
        ${planetBarHtml ? `<div class="cn-planet-bar">${planetBarHtml}</div>` : ""}
        ${state.svgHtml
          ? `<div class="cn-svg-wrap" id="cn-svg-container">${state.svgHtml}</div>`
          : `<div class="casos-empty">No se pudo generar la carta. Verifica el lugar.</div>`}
        <div id="cn-planet-panel" class="cn-planet-panel" style="display:none">
          <div class="cn-pp-header">
            <span class="cn-pp-glyph" id="cn-pp-glyph"></span>
            <div><div class="cn-pp-name" id="cn-pp-name"></div><div class="cn-pp-detail" id="cn-pp-detail"></div></div>
            <span class="cn-pp-retro" id="cn-pp-retro" style="display:none">℞ Retrógrado</span>
          </div>
          <div id="cn-pp-interp" class="cn-pp-interp"></div>
          <button class="wizard-nav-btn vort-ia-btn" id="cn-pp-btn">✨ Interpretación terapéutica</button>
        </div>
        <div class="wizard-nav" style="margin-top:16px">
          <button class="wizard-nav-btn vort-ia-btn" id="cn-interp-full" style="width:100%">🧠 Análisis terapéutico completo</button>
        </div>
        <div id="cn-general-out"></div>
      </div>`;

    if (state.svgHtml) initCnSvgInteractivity();

    content.querySelectorAll(".cn-planet-chip").forEach((chip) => {
      chip.addEventListener("click", () => showCnPlanetPanel(chip.dataset.slug));
    });
    content.querySelector("#cn-nueva")?.addEventListener("click", () => { state.phase = "form"; render(); });
    content.querySelector("#cn-interp-full")?.addEventListener("click", async () => {
      const outEl = content.querySelector("#cn-general-out");
      if (!outEl) return;
      const planStr = mainKeys.map((k) => {
        const info = planetas[k]; if (!info) return null;
        const slug = k === "ascendant" ? "Ascendant" : k.charAt(0).toUpperCase() + k.slice(1);
        return `${CN_PLANETA_ES[slug]||k} en ${CN_SIGNO_ES[info.sign_abbr]||info.sign||"?"} (Casa ${info.house||"?"})`;
      }).filter(Boolean).join(", ");
      const query = `Consultante: ${nombre}. Nacido/a el ${fecha}.\nPosiciones clave: ${planStr || "(sin datos)"}\n\nDesde la perspectiva terapéutica holística:\n1. ¿Qué patrón bioenergético y emocional define a este consultante?\n2. ¿Qué áreas de vida son más vulnerables o desafiantes?\n3. ¿Qué recursos y fortalezas innatos tiene para su sanación?\n4. ¿Qué tipo de trabajo terapéutico resuena más con este perfil?\n5. ¿Qué aspecto de su proceso requiere más paciencia y contención?\n\nSé concreto, profundo y orientado a la sesión.`;
      await rastreoInterpretarIA(outEl, query);
    });
  }

  function showCnPlanetPanel(slug) {
    state.activePlanet = slug;
    const planetas = state.posData?.planetas || {};
    const key = slug.toLowerCase();
    const info = planetas[key] || planetas[slug] || {};
    const signo = CN_SIGNO_ES[info.sign_abbr] || info.sign || "?";
    const houseStr = (info.house||"").replace(/_House$/,"");
    const casa = CN_CASA_ES[houseStr] || houseStr || "?";
    const grado = info.position ? parseFloat(info.position).toFixed(1) : "?";
    const retro = info.retrograde;
    const panel = content.querySelector("#cn-planet-panel");
    if (!panel) return;
    content.querySelector("#cn-pp-glyph").textContent = CN_GLIFO[slug] || "★";
    content.querySelector("#cn-pp-name").textContent = CN_PLANETA_ES[slug] || slug;
    content.querySelector("#cn-pp-detail").textContent = `${signo} ${grado}° · Casa ${casa}`;
    const retroEl = content.querySelector("#cn-pp-retro");
    if (retroEl) retroEl.style.display = retro ? "inline" : "none";
    content.querySelector("#cn-pp-interp").innerHTML = "";
    panel.style.display = "block";
    panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    content.querySelector("#cn-pp-btn").onclick = async () => {
      const outEl = content.querySelector("#cn-pp-interp");
      if (!outEl) return;
      const { nombre: nomPac, fecha } = state.params;
      const nombrePl = CN_PLANETA_ES[slug] || slug;
      const query = `Consultante: ${nomPac}. Nacido/a el ${fecha}.\n${nombrePl} en ${signo} (${grado}°), Casa ${casa}${retro ? ", Retrógrado" : ""}.\n\nDesde la perspectiva terapéutica holística:\n1. ¿Qué programa de vida expresa ${nombrePl} en ${signo} en la Casa ${casa}?\n2. ¿Cómo se manifiesta en el cuerpo físico y en los síntomas?\n3. ¿Qué patrón emocional o familiar está ligado a esta posición?\n4. ¿Cómo trabaja el terapeuta con este patrón?\n5. ¿Qué recurso o fortaleza ofrece esta posición al proceso de sanación?\n\nSé concreto y orientado a la sesión.`;
      await rastreoInterpretarIA(outEl, query);
    };
  }

  function initCnSvgInteractivity() {
    const container = content.querySelector("#cn-svg-container");
    if (!container) return;
    const svgEl = container.querySelector("svg");
    if (!svgEl) return;
    svgEl.style.animation = "chartSpin 0.7s cubic-bezier(0.34,1.56,0.64,1) forwards";
    svgEl.style.transformOrigin = "center center";
    const points = svgEl.querySelectorAll("g[kr\\:node='ChartPoint']");
    points.forEach((g) => {
      const slug = g.getAttribute("kr:slug") || "";
      if (!CN_PLANETA_ES[slug]) return;
      g.style.cursor = "pointer";
      g.style.transition = "filter 0.2s";
      g.addEventListener("mouseenter", () => { g.style.filter = "drop-shadow(0 0 8px rgba(167,139,250,0.9))"; });
      g.addEventListener("mouseleave", () => { g.style.filter = ""; });
      g.addEventListener("click", () => showCnPlanetPanel(slug));
    });
  }

  render();
}

// ─── Diario Lunar ───────────────────────────────────────────────────────────

function buildMoonSvg(phaseId, illumination, color) {
  // Build SVG moon showing correct phase using two overlapping circles
  const size = 80;
  const cx = size / 2;
  const r = 32;
  // For phase visualization: left circle always = moon, right circle = shadow or light
  // illumination 0-100: 0=new(all dark), 100=full(all lit)
  // We use a clip approach: lit portion on right (waxing) or left (waning)
  const isWaning = ['llena', 'menguante', 'cuarto_men', 'balsamica'].includes(phaseId);
  const pct = illumination / 100;
  // Offset of inner circle to create crescent: from r (fully dark) to -r (fully lit)
  const offset = r - pct * 2 * r;
  const glowColor = color || '#7c3aed';
  const moonColor = phaseId === 'nueva' ? '#1a1a2e' : (illumination > 80 ? '#f8d877' : '#c4b5fd');
  const shadowColor = '#0a0a1a';

  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg" class="luna-moon-svg">
    <defs>
      <clipPath id="moon-clip-${phaseId}">
        <circle cx="${cx}" cy="${cx}" r="${r}" />
      </clipPath>
      <filter id="moon-glow">
        <feGaussianBlur stdDeviation="3" result="blur"/>
        <feComposite in="SourceGraphic" in2="blur" operator="over"/>
      </filter>
    </defs>
    <g filter="url(#moon-glow)">
      <!-- Base moon circle -->
      <circle cx="${cx}" cy="${cx}" r="${r}" fill="${moonColor}" opacity="0.95"/>
      <!-- Shadow overlay using offset inner circle -->
      <g clip-path="url(#moon-clip-${phaseId})">
        <circle cx="${cx + (isWaning ? -offset : offset)}" cy="${cx}" r="${r}" fill="${shadowColor}" opacity="${phaseId === 'llena' ? 0 : 0.92}"/>
      </g>
    </g>
    <!-- Glow ring for full/near-full phases -->
    ${illumination > 60 ? `<circle cx="${cx}" cy="${cx}" r="${r + 4}" fill="none" stroke="${glowColor}" stroke-width="1.5" opacity="0.3" class="luna-glow-ring"/>` : ''}
  </svg>`;
}
const LUNA_TERAPEUTICA = {
  nueva: {
    titulo: "Luna Nueva — Siembra e Intención",
    descripcion: "La Luna Nueva marca el inicio de un ciclo. Es el momento ideal para establecer intenciones, iniciar procesos terapéuticos, y sembrar los programas nuevos que el paciente quiere activar. La energía apoya la apertura y la receptividad.",
    trabajo: ["Instalar nuevas creencias positivas", "Establecer metas terapéuticas del ciclo", "Iniciar protocolos de liberación profunda", "Trabajar programas transgeneracionales de inicio"],
    evitar: ["Trabajo de cierre o finalización", "Protocolos de separación o corte"],
    color: "#1a0a2e",
    colorAccent: "#7c3aed",
  },
  creciente: {
    titulo: "Luna Creciente — Activación y Crecimiento",
    descripcion: "La energía lunar está en expansión. El sistema energético del paciente está en modo receptivo y de crecimiento. Los tratamientos tienen mayor potencia de activación. Ideal para reforzar recursos y capacidades positivas.",
    trabajo: ["Activar recursos internos del paciente", "Reforzar pares positivos y de protección", "Trabajar el fortalecimiento del sistema inmune", "Técnicas de expansión de conciencia"],
    evitar: ["Protocolos de eliminación o depuración intensa"],
    color: "#0f1a2e",
    colorAccent: "#2563eb",
  },
  gibosa_crec: {
    titulo: "Gibosa Creciente — Refinamiento",
    descripcion: "Fase de ajuste y perfeccionamiento. La energía está casi en su plenitud. El trabajo terapéutico puede ser más detallado y preciso. Momento de evaluar avances del ciclo.",
    trabajo: ["Rastreo fino de pares residuales", "Evaluación de avance terapéutico del ciclo", "Trabajo de ajuste energético y bioenergético"],
    evitar: [],
    color: "#0f1a35",
    colorAccent: "#1d4ed8",
  },
  llena: {
    titulo: "Luna Llena — Manifestación y Revelación",
    descripcion: "La Luna Llena es el momento de mayor intensidad energética. El campo bioenergético del paciente está en su punto más expandido. Los conflictos emocionales pueden emerger espontáneamente. Excelente momento para trabajo de revelación y manifestación.",
    trabajo: ["Sesiones de biodecodificación profunda", "Trabajo con emociones atrapadas intensas", "Protocolos de resolución de conflictos", "Revelación de patrones ocultos transgeneracionales"],
    evitar: ["Sesiones con pacientes altamente sensibles sin preparación previa"],
    color: "#1a1500",
    colorAccent: "#ca8a04",
  },
  menguante: {
    titulo: "Luna Llena Menguante — Gratitud y Entrega",
    descripcion: "La energía comienza a retroceder después de la plenitud. Momento de integrar lo recibido y entregar lo que ya no se necesita. Ideal para cierres terapéuticos parciales.",
    trabajo: ["Integración de sesiones anteriores", "Rituales de cierre y gratitud", "Protocolos de depuración energética", "Trabajo con patrones de apego y entrega"],
    evitar: [],
    color: "#1a1000",
    colorAccent: "#b45309",
  },
  cuarto_men: {
    titulo: "Cuarto Menguante — Liberación",
    descripcion: "La Luna decrece hacia su mínimo. Es el momento más poderoso para soltar, limpiar y liberar. Los protocolos de eliminación de patrones, miasmas y programas negativos tienen su mayor eficacia.",
    trabajo: ["Liberación de miasmas y nudos psóricos", "Protocolos de eliminación de cuerdas energéticas", "Trabajo con intencionalidades negativas", "Liberación de maldiciones y mal de ojo", "EFT de liberación profunda"],
    evitar: ["Instalación de nuevos programas (esperar Luna Nueva)"],
    color: "#1a0f00",
    colorAccent: "#92400e",
  },
  balsamica: {
    titulo: "Luna Balsámica — Descanso y Preparación",
    descripcion: "Los últimos días del ciclo lunar. La energía es introspectiva y de rendición. Momento de descanso, reflexión y preparación para el nuevo ciclo. Sesiones suaves y de contención.",
    trabajo: ["Sesiones de apoyo emocional suave", "Trabajo de rendición y aceptación", "Preparación para el próximo ciclo terapéutico", "Meditación y centrado"],
    evitar: ["Protocolos intensos de activación o liberación"],
    color: "#120a1e",
    colorAccent: "#6d28d9",
  },
};

const ELEMENTO_INFO = {
  fuego: { desc: "La Luna en signo de Fuego potencia la energía vital, la voluntad y la motivación. El paciente puede mostrar mayor determinación y apertura.", icono: "🔥" },
  tierra: { desc: "Luna en signo de Tierra ancla el trabajo terapéutico al plano físico. Excelente para protocolos relacionados con el cuerpo, la nutrición y la seguridad material.", icono: "🌍" },
  aire: { desc: "Luna en signo de Aire favorece la comprensión mental y la comunicación. El paciente puede integrar mejor las revelaciones y verbalizar sus procesos.", icono: "💨" },
  agua: { desc: "Luna en signo de Agua intensifica la sensibilidad emocional. Sesiones de alta resonancia emocional. Ideal para trabajo transgeneracional y emociones atrapadas.", icono: "💧" },
};

function renderDiarioLunar(p, content) {
  content.innerHTML = `<div class="ra-loading"><div class="rastreo-interpret-spinner"></div><span>Consultando posición lunar actual...</span></div>`;

  async function init() {
    let luna = null;
    try {
      const res = await fetch("/astro/luna/hoy");
      if (res.ok) luna = await res.json();
    } catch { /* fallback below */ }

    if (!luna) {
      content.innerHTML = `<div class="rastreo-tabla-wrap"><p class="status error">No se pudo obtener datos lunares. El servidor de efemérides no está disponible.</p></div>`;
      return;
    }

    renderLuna(luna);
  }

  function renderLuna(luna) {
    const fase = luna.fase;
    const lunaData = luna.luna;
    const tera = LUNA_TERAPEUTICA[fase.id] || LUNA_TERAPEUTICA.nueva;
    const elem = ELEMENTO_INFO[lunaData.elemento] || ELEMENTO_INFO.agua;

    const ilumPct = fase.iluminacion;
    const ilumColor = ilumPct > 80 ? "#ca8a04" : ilumPct > 40 ? "#2563eb" : "#7c3aed";

    const trabajoHtml = tera.trabajo.map((t) => `<li>${escapeHtml(t)}</li>`).join("");
    const evitarHtml = tera.evitar.length > 0
      ? `<div class="luna-evitar-section">
          <div class="luna-sec-label">⚠ Energía menos afín hoy</div>
          <ul class="luna-lista">${tera.evitar.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul>
        </div>` : "";

    const proximosHtml = [];
    if (luna.proximos.dias_luna_llena) proximosHtml.push(`🌕 Luna Llena en ~${luna.proximos.dias_luna_llena} días`);
    if (luna.proximos.dias_luna_nueva) proximosHtml.push(`🌑 Luna Nueva en ~${luna.proximos.dias_luna_nueva} días`);

    content.innerHTML = `
      <div class="rastreo-tabla-wrap luna-wrap">
        <div class="luna-header" style="background:linear-gradient(135deg,${tera.color},#100922)">
          <div class="luna-svg-wrap">${buildMoonSvg(fase.id, fase.iluminacion, tera.colorAccent)}</div>
          <div class="luna-fase-info">
            <div class="luna-fecha">${escapeHtml(luna.fecha)}</div>
            <div class="luna-fase-nombre" style="color:${tera.colorAccent}">${escapeHtml(fase.nombre)}</div>
            <div class="luna-signo">🌙 Luna en <strong>${escapeHtml(lunaData.signo)}</strong> (${lunaData.grado}°) · ${elem.icono} ${lunaData.elemento.charAt(0).toUpperCase()+lunaData.elemento.slice(1)}</div>
            <div class="luna-sol">☀ Sol en <strong>${escapeHtml(luna.sol.signo)}</strong></div>
          </div>
          <div class="luna-ilum-wrap">
            <div class="luna-ilum-ring" style="--pct:${ilumPct};--color:${ilumColor}">
              <span class="luna-ilum-value">${ilumPct}%</span>
            </div>
            <div class="luna-ilum-label">Iluminación</div>
          </div>
        </div>

        <div class="luna-keyword-bar" style="background:${tera.colorAccent}20;border-color:${tera.colorAccent}40;color:${tera.colorAccent}">
          ${escapeHtml(fase.keyword)}
        </div>

        <div class="luna-desc">${escapeHtml(tera.descripcion)}</div>

        <div class="luna-elem-box">
          <span class="luna-elem-icono">${elem.icono}</span>
          <span>${escapeHtml(elem.desc)}</span>
        </div>

        <div class="luna-trabajo-section">
          <div class="luna-sec-label">✅ Trabajo terapéutico afín hoy</div>
          <ul class="luna-lista">${trabajoHtml}</ul>
        </div>

        ${evitarHtml}

        ${proximosHtml.length > 0 ? `<div class="luna-proximos">${proximosHtml.map(t=>`<span>${t}</span>`).join("")}</div>` : ""}

        <div class="wizard-nav" style="margin-top:16px">
          <button class="wizard-nav-btn vort-ia-btn" id="luna-ia-btn">🧠 Orientación terapéutica completa del Motor</button>
        </div>
        <div id="luna-ia-out"></div>
      </div>`;

    content.querySelector("#luna-ia-btn")?.addEventListener("click", async () => {
      const outEl = content.querySelector("#luna-ia-out");
      if (!outEl) return;
      const query = `Hoy es ${luna.fecha}. La fase lunar es: ${fase.nombre} (${fase.emoji}), con Luna en ${lunaData.signo} (elemento ${lunaData.elemento}, modalidad ${lunaData.modalidad}), Sol en ${luna.sol.signo}. La iluminación lunar es del ${ilumPct}%.\n\nComo Motor Terapéutico de HoloacademIA, proporciona:\n1. Cómo esta configuración lunar específica (signo, elemento, fase) afecta el campo bioenergético del consultante\n2. Qué tipos de conflictos o síntomas pueden activarse o intensificarse hoy\n3. Qué protocolos terapéuticos (biomagnetismo, EFT, transgeneracional, emocional) son más potentes en esta fase\n4. Una recomendación concreta para el terapeuta sobre cómo estructurar las sesiones de hoy\n5. Qué le puedes recomendar al paciente para potenciar su proceso en casa\n\nSé específico y orientado a la práctica clínica.`;
      await rastreoInterpretarIA(outEl, query);
    });
  }

  init();
}

// ─── Catálogo Biomagnético ──────────────────────────────────────────────────
function renderCatalogoBiomagnetico(p, content) {
  const cache = { data: null };
  const state = {
    phase: "browse",       // "browse" | "detalle"
    catFilter: null,
    busqueda: "",
    selectedPar: null,
    sessionPares: [],      // pares marcados para la sesión
  };

  async function init() {
    content.innerHTML = `<div class="ra-loading"><div class="rastreo-interpret-spinner"></div><span>Cargando catálogo biomagnético...</span></div>`;
    try {
      const res = await fetch("/api/pares/catalogo");
      cache.data = res.ok ? await res.json() : null;
    } catch { cache.data = null; }
    renderBrowse();
  }

  function filteredPares() {
    const all = cache.data?.pares || [];
    return all.filter((par) => {
      const catOk = !state.catFilter || par.categoria === state.catFilter;
      if (!catOk) return false;
      if (!state.busqueda) return true;
      const q = state.busqueda.toLowerCase();
      return (
        par.nombre.toLowerCase().includes(q) ||
        par.agente.toLowerCase().includes(q) ||
        (par.condiciones || []).some((c) => c.toLowerCase().includes(q)) ||
        (par.sintomas || []).some((s) => s.toLowerCase().includes(q)) ||
        (par.keywords || []).some((k) => k.toLowerCase().includes(q))
      );
    });
  }

  function renderBrowse() {
    state.phase = "browse";
    const cats = cache.data?.categorias || [];
    const pares = filteredPares();

    const catChips = cats.map((cat) => `
      <div class="sint-cat-chip${state.catFilter === cat.id ? " sint-cat-active" : ""}"
        data-cat="${cat.id}" style="--cat-color:${cat.color}">
        <span>${cat.icono}</span>
        <span>${cat.nombre}</span>
        <span class="cat-chip-count">${(cache.data?.pares||[]).filter(x=>x.categoria===cat.id).length}</span>
      </div>`).join("");

    const sesionHtml = state.sessionPares.length > 0
      ? `<div class="catbio-sesion-bar">
          <span>🧲 ${state.sessionPares.length} par${state.sessionPares.length>1?"es":""} seleccionado${state.sessionPares.length>1?"s":""} para la sesión</span>
          <button class="wizard-nav-btn vort-ia-btn" id="catbio-interpretar-sesion">✨ Interpretar sesión</button>
          <button class="wizard-nav-btn wizard-reiniciar" id="catbio-limpiar-sesion">✕ Limpiar</button>
        </div>` : "";

    const paresHtml = pares.length === 0
      ? `<p class="casos-empty">No se encontraron pares con ese criterio.</p>`
      : pares.map((par) => {
          const cat = cats.find((c) => c.id === par.categoria);
          const enSesion = state.sessionPares.some((s) => s.id === par.id);
          return `<div class="catbio-par-card${enSesion ? " catbio-par-selected" : ""}" data-pid="${par.id}"
            style="--cat-color:${cat?.color||"#7c3aed"}">
            <div class="catbio-par-header">
              <span class="catbio-par-nombre">${escapeHtml(par.nombre)}</span>
              <span class="catbio-cat-badge" style="background:${cat?.color||"#7c3aed"}20;color:${cat?.color||"#7c3aed"};border-color:${cat?.color||"#7c3aed"}40">
                ${cat?.icono||""} ${cat?.nombre||""}
              </span>
            </div>
            <div class="catbio-par-agente">${escapeHtml(par.agente)}</div>
            <div class="catbio-par-conds">${(par.condiciones||[]).slice(0,2).map(c=>`<span class="vort-det-tag">${escapeHtml(c)}</span>`).join("")}</div>
            <div class="catbio-par-actions">
              <button class="catbio-ver-btn" data-pid="${par.id}">Ver detalle →</button>
              <button class="catbio-add-btn${enSesion?" catbio-add-active":""}" data-pid="${par.id}">
                ${enSesion ? "✓ En sesión" : "+ Agregar"}
              </button>
            </div>
          </div>`;
        }).join("");

    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        <div class="rastreo-instruccion-ms">
          <span class="rastreo-ms-badge">MS</span>
          <span>${escapeHtml(p.instruccion_ms || "¿Hay algún par de esta categoría activo?")}</span>
        </div>
        ${sesionHtml}
        <div class="catbio-search-row">
          <input class="casos-input" id="catbio-search" placeholder="Buscar por nombre, agente, síntoma..." value="${escapeHtml(state.busqueda)}">
        </div>
        <div class="sint-cats-grid catbio-cats">${catChips}
          ${state.catFilter ? `<div class="sint-cat-chip" id="catbio-clear-cat" style="--cat-color:#6b7280">✕ Todos</div>` : ""}
        </div>
        <div class="catbio-result-info">${pares.length} pares encontrados</div>
        <div class="catbio-grid">${paresHtml}</div>
        <div id="catbio-sesion-out"></div>
      </div>`;

    content.querySelector("#catbio-search")?.addEventListener("input", (e) => {
      state.busqueda = e.target.value; renderBrowse();
    });
    content.querySelectorAll(".sint-cat-chip[data-cat]").forEach((el) => {
      el.addEventListener("click", () => { state.catFilter = state.catFilter === el.dataset.cat ? null : el.dataset.cat; renderBrowse(); });
    });
    content.querySelector("#catbio-clear-cat")?.addEventListener("click", () => { state.catFilter = null; renderBrowse(); });
    content.querySelectorAll(".catbio-ver-btn").forEach((btn) => {
      btn.addEventListener("click", () => { state.selectedPar = btn.dataset.pid; renderDetalle(); });
    });
    content.querySelectorAll(".catbio-add-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const pid = btn.dataset.pid;
        const par = (cache.data?.pares||[]).find((x) => x.id === pid);
        if (!par) return;
        const idx = state.sessionPares.findIndex((x) => x.id === pid);
        if (idx >= 0) state.sessionPares.splice(idx, 1);
        else state.sessionPares.push(par);
        renderBrowse();
      });
    });
    content.querySelectorAll(".catbio-par-card").forEach((card) => {
      card.addEventListener("click", (e) => {
        if (e.target.closest(".catbio-ver-btn,.catbio-add-btn")) return;
        state.selectedPar = card.dataset.pid; renderDetalle();
      });
    });
    content.querySelector("#catbio-interpretar-sesion")?.addEventListener("click", async () => {
      const outEl = content.querySelector("#catbio-sesion-out");
      if (!outEl) return;
      const lista = state.sessionPares.map((par) => `- ${par.nombre} (${par.agente}): ${(par.condiciones||[]).slice(0,2).join(", ")}`).join("\n");
      const query = `El terapeuta seleccionó los siguientes pares biomagnéticos para rastrear en la sesión:\n${lista}\n\nDesde la perspectiva terapéutica holística:\n1. ¿Qué patrón biológico y emocional une estos pares?\n2. ¿En qué orden recomiendas trabajarlos?\n3. ¿Qué información adicional del paciente ayudaría a confirmar el rastreo?\n4. ¿Qué esperar tras el tratamiento?\n\nSé concreto y orientado a la sesión.`;
      outEl.scrollIntoView({ behavior: "smooth" });
      await rastreoInterpretarIA(outEl, query);
    });
    content.querySelector("#catbio-limpiar-sesion")?.addEventListener("click", () => { state.sessionPares = []; renderBrowse(); });
  }

  function renderDetalle() {
    state.phase = "detalle";
    const par = (cache.data?.pares||[]).find((x) => x.id === state.selectedPar);
    if (!par) { renderBrowse(); return; }
    const cats = cache.data?.categorias || [];
    const cat = cats.find((c) => c.id === par.categoria);
    const color = cat?.color || "#7c3aed";
    const enSesion = state.sessionPares.some((s) => s.id === par.id);

    const condsHtml = (par.condiciones||[]).map((c) => `<span class="vort-det-tag">${escapeHtml(c)}</span>`).join("");
    const sintomasHtml = (par.sintomas||[]).map((s) => `<li>${escapeHtml(s)}</li>`).join("");

    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        <div class="catbio-det-header" style="border-color:${color}40">
          <div class="catbio-det-cat" style="background:${color}20;color:${color}">
            ${cat?.icono||""} ${cat?.nombre||""}
          </div>
          <h3 class="catbio-det-nombre" style="color:${color}">${escapeHtml(par.nombre)}</h3>
          <div class="catbio-det-agente">🦠 ${escapeHtml(par.agente)}</div>
          <div class="catbio-det-puntos">
            <div class="catbio-punto pos" style="border-color:${color}">
              <span class="catbio-punto-label">Polo (+)</span>
              <span class="catbio-punto-nombre">${escapeHtml(par.positivo)}</span>
            </div>
            <div class="catbio-punto-arrow">⟷</div>
            <div class="catbio-punto neg" style="border-color:${color}">
              <span class="catbio-punto-label">Polo (−)</span>
              <span class="catbio-punto-nombre">${escapeHtml(par.negativo)}</span>
            </div>
          </div>
        </div>

        <div class="catbio-det-section">
          <div class="catbio-det-label">Condiciones asociadas</div>
          <div class="catbio-det-conds">${condsHtml}</div>
        </div>

        <div class="catbio-det-section">
          <div class="catbio-det-label">Síntomas frecuentes</div>
          <ul class="catbio-det-sintomas">${sintomasHtml}</ul>
        </div>

        ${par.notas ? `<div class="catbio-det-notas">
          <span class="rastreo-ms-badge" style="background:${color}20;color:${color}">Nota clínica</span>
          <span>${escapeHtml(par.notas)}</span>
        </div>` : ""}

        <div class="wizard-nav" style="margin-top:16px">
          <button class="wizard-nav-btn" id="det-back-cat">← Catálogo</button>
          <button class="wizard-nav-btn${enSesion?" wizard-reiniciar":""}" id="det-toggle-sesion">
            ${enSesion ? "✓ Quitar de sesión" : "+ Agregar a sesión"}
          </button>
          <button class="wizard-nav-btn vort-ia-btn" id="det-interpretar">✨ Interpretar</button>
        </div>
        <div id="det-interp-out"></div>
      </div>`;

    content.querySelector("#det-back-cat")?.addEventListener("click", () => renderBrowse());
    content.querySelector("#det-toggle-sesion")?.addEventListener("click", () => {
      const idx = state.sessionPares.findIndex((x) => x.id === par.id);
      if (idx >= 0) state.sessionPares.splice(idx, 1);
      else state.sessionPares.push(par);
      renderDetalle();
    });
    content.querySelector("#det-interpretar")?.addEventListener("click", async () => {
      const outEl = content.querySelector("#det-interp-out");
      if (!outEl) return;
      const query = `El par biomagnético "${par.nombre}" (${par.agente}) fue identificado durante el rastreo.\n\nCondiciones asociadas: ${(par.condiciones||[]).join(", ")}\nSíntomas: ${(par.sintomas||[]).join(", ")}\n\nDesde la perspectiva terapéutica holística:\n1. ¿Por qué este par se activa? ¿Qué programa biológico expresa?\n2. ¿Cómo se aplican los imanes (localización exacta, polo, tiempo)?\n3. ¿Qué pares complementarios suele tener?\n4. ¿Qué cambios observar en el paciente post-tratamiento?\n5. ¿Qué trabajo emocional o nutricional potencia la resolución?\n\nSé específico y orientado a la sesión.`;
      await rastreoInterpretarIA(outEl, query);
    });
  }

  init();
}

// ─── Rastreo por Síntoma ────────────────────────────────────────────────────
const SINTOMA_CATEGORIAS = [
  { id: "virus",      label: "Virus",           icono: "🦠", color: "#dc2626" },
  { id: "bacterias",  label: "Bacterias",        icono: "🧫", color: "#d97706" },
  { id: "hongos",     label: "Hongos",           icono: "🍄", color: "#7c3aed" },
  { id: "parasitos",  label: "Parásitos",        icono: "🪱", color: "#059669" },
  { id: "emocionales",label: "Emocionales",      icono: "💜", color: "#db2777" },
  { id: "reservorios",label: "Reservorios",      icono: "🔬", color: "#0284c7" },
  { id: "especiales", label: "Especiales",       icono: "⭐", color: "#ca8a04" },
  { id: "disfunciones",label: "Disfunciones",    icono: "⚡", color: "#9333ea" },
];

function renderRastreoSintoma(p, content) {
  const _act = paGetActivo();
  const state = {
    phase: "busqueda",   // "busqueda" | "resultados"
    sintoma: _act?.paciente?.observaciones || "",  // precarga motivo de consulta del expediente
    categoria: null,     // null = texto libre, o id de categoría
    pares: [],           // [{ nombre, descripcion, checked }]
    loading: false,
  };

  function render() {
    if (state.phase === "busqueda") renderBusqueda();
    else renderResultados();
  }

  // ── Fase 1: Búsqueda ──────────────────────────────────────────────────────
  function renderBusqueda() {
    const catHtml = SINTOMA_CATEGORIAS.map((cat) => `
      <div class="sint-cat-chip${state.categoria === cat.id ? " sint-cat-active" : ""}"
        data-cat="${cat.id}" style="--cat-color:${cat.color}">
        <span>${cat.icono}</span>
        <span>${cat.label}</span>
      </div>`).join("");

    const act = paGetActivo();
    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        ${act && state.sintoma ? `<div class="pa-prefill-note">📋 Motivo de consulta de <strong>${escapeHtml((act.paciente.nombre||"") + " " + (act.paciente.apellidos||""))}</strong> precargado desde su expediente</div>` : ""}
        <div class="rastreo-instruccion-ms">
          <span class="rastreo-ms-badge">MS</span>
          <span>${escapeHtml(p.instruccion_ms || "¿Hay algún par biomagnético activo relacionado con el síntoma principal?")}</span>
        </div>

        <div class="sint-search-block">
          <label class="sint-label">Describe el síntoma, enfermedad o cuadro clínico:</label>
          <div class="sint-input-row">
            <input class="casos-input sint-input" id="sint-texto"
              placeholder="Ej: migraña occipital crónica, fatiga persistente, dolor lumbar con ardor..."
              value="${escapeHtml(state.sintoma)}">
            <button class="wizard-nav-btn vort-ia-btn sint-buscar-btn" id="sint-buscar">
              🔍 Analizar
            </button>
          </div>
        </div>

        <div class="sint-cats-wrap">
          <label class="sint-label">Enfocar por tipo de agente (opcional):</label>
          <div class="sint-cats-grid">${catHtml}</div>
          ${state.categoria ? `<button class="sint-clear-cat" id="sint-clear-cat">✕ Quitar filtro de ${SINTOMA_CATEGORIAS.find(c=>c.id===state.categoria)?.label}</button>` : ""}
        </div>

        <div class="wizard-nav" style="margin-top:16px">
          <button class="wizard-nav-btn vort-ia-btn" id="sint-analizar-full" style="width:100%">
            🧠 Analizar con Motor Biomagnético
          </button>
        </div>
      </div>`;

    const txt = content.querySelector("#sint-texto");
    txt?.addEventListener("input", (e) => { state.sintoma = e.target.value; });
    txt?.addEventListener("keydown", (e) => { if (e.key === "Enter") lanzarAnalisis(); });
    content.querySelector("#sint-buscar")?.addEventListener("click", lanzarAnalisis);
    content.querySelector("#sint-analizar-full")?.addEventListener("click", lanzarAnalisis);
    content.querySelector("#sint-clear-cat")?.addEventListener("click", () => { state.categoria = null; render(); });
    content.querySelectorAll(".sint-cat-chip").forEach((el) => {
      el.addEventListener("click", () => {
        state.categoria = state.categoria === el.dataset.cat ? null : el.dataset.cat;
        render();
      });
    });
  }

  // ── Fetch IA ──────────────────────────────────────────────────────────────
  async function lanzarAnalisis() {
    const txt = content.querySelector("#sint-texto");
    if (txt) state.sintoma = txt.value.trim();
    if (!state.sintoma && !state.categoria) {
      content.querySelector("#sint-texto")?.focus();
      return;
    }

    const cat = SINTOMA_CATEGORIAS.find((c) => c.id === state.categoria);
    const catCtx = cat ? `\nEnfoque: ${cat.label} — busca específicamente pares relacionados con ${cat.label.toLowerCase()}.` : "";
    const query = `Eres el Motor Biomagnético de HoloacademIA, experto en terapia de pares biomagnéticos.\n\nEl terapeuta necesita identificar qué pares rastrear para el siguiente cuadro:\n"${state.sintoma || "Rastreo general por categoría: " + (cat?.label || "")}"${catCtx}\n\nResponde con una lista estructurada de:\n1. LOS PARES BIOMAGNÉTICOS más relevantes para rastrear (mínimo 8, máximo 15)\n   - Formato exacto: "PAR: [órgano/punto 1] — [órgano/punto 2]"\n   - Incluye el tipo de agente si aplica (virus, bacteria, hongo, parásito, emocional)\n2. ORDEN DE RASTREO sugerido\n3. NOTA CLÍNICA: qué observar durante el rastreo\n\nSé específico con los nombres anatómicos de los pares. No incluyas disclaimers ni menciones fuentes externas.`;

    state.phase = "resultados";
    state.pares = [];
    state.loading = true;
    renderResultados();

    try {
      const res = await postJson("/academic/ask", { query, history: [] });
      const answer = res?.answer || "";
      // Parse PAR: lines from response
      const parLines = answer.split("\n").filter((l) => l.match(/PAR:/i));
      if (parLines.length > 0) {
        state.pares = parLines.map((l) => {
          const nombre = l.replace(/^.*PAR:\s*/i, "").replace(/\*+/g, "").trim();
          return { nombre, checked: false };
        });
      }
      state.rawAnswer = answer;
    } catch {
      state.rawAnswer = "No se pudo obtener respuesta del Motor. Intenta de nuevo.";
    }
    state.loading = false;
    renderResultados();
  }

  // ── Fase 2: Resultados ───────────────────────────────────────────────────
  function renderResultados() {
    const cat = SINTOMA_CATEGORIAS.find((c) => c.id === state.categoria);

    if (state.loading) {
      content.innerHTML = `
        <div class="rastreo-tabla-wrap">
          <div class="ra-loading">
            <div class="rastreo-interpret-spinner"></div>
            <span>El Motor Biomagnético está analizando el cuadro clínico...</span>
          </div>
        </div>`;
      return;
    }

    const paresChecked = state.pares.filter((p) => p.checked).length;
    const paresHtml = state.pares.length > 0
      ? state.pares.map((par, idx) => `
          <div class="sint-par-row${par.checked ? " sint-par-checked" : ""}" data-idx="${idx}">
            <div class="vort-punto-check${par.checked ? " vort-punto-check-done" : ""}" data-pcheck="${idx}">
              ${par.checked ? "✓" : ""}
            </div>
            <div class="sint-par-nombre">${escapeHtml(par.nombre)}</div>
          </div>`).join("")
      : "";

    const rawHtml = state.rawAnswer
      ? `<div class="sint-raw-answer">
          <details>
            <summary class="sint-raw-toggle">📋 Ver análisis completo del Motor</summary>
            <div class="sint-raw-body">${escapeHtml(state.rawAnswer).replace(/\n/g, "<br>")}</div>
          </details>
        </div>` : "";

    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        <div class="sint-result-header">
          <div class="sint-result-titulo">
            ${cat ? `<span class="sint-cat-badge" style="background:${cat.color}20;border-color:${cat.color}50;color:${cat.color}">${cat.icono} ${cat.label}</span>` : ""}
            <span class="sint-result-sintoma">${escapeHtml(state.sintoma || "Rastreo general")}</span>
          </div>
          ${state.pares.length > 0 ? `<div class="sint-progreso">${paresChecked}/${state.pares.length} pares verificados</div>` : ""}
        </div>

        ${state.pares.length > 0 ? `
          <div class="sint-instruccion">
            <span class="rastreo-ms-badge">TM</span>
            <span>Verifica cada par con test muscular. Marca los que respondan SÍ.</span>
          </div>
          <div class="sint-pares-list">${paresHtml}</div>
          ${paresChecked > 0 ? `
            <div id="sint-guardar-block" style="margin-top:12px">
              <button class="wizard-nav-btn vort-ia-btn" id="sint-interpretar-sel">
                ✨ Interpretar los ${paresChecked} pares seleccionados con el Motor Terapéutico
              </button>
            </div>
            <div id="sint-interp-out"></div>` : ""}
        ` : ""}

        ${rawHtml}
        <div id="sint-main-out"></div>

        <div class="wizard-nav" style="margin-top:16px">
          <button class="wizard-nav-btn" id="sint-back">← Nueva búsqueda</button>
          <button class="wizard-nav-btn vort-ia-btn" id="sint-reanalizar">🔄 Reanalizar</button>
        </div>
      </div>`;

    content.querySelectorAll(".vort-punto-check[data-pcheck]").forEach((el) => {
      el.addEventListener("click", () => {
        const idx = parseInt(el.dataset.pcheck);
        state.pares[idx].checked = !state.pares[idx].checked;
        renderResultados();
      });
    });
    content.querySelectorAll(".sint-par-row").forEach((el) => {
      el.addEventListener("click", () => {
        const idx = parseInt(el.dataset.idx);
        state.pares[idx].checked = !state.pares[idx].checked;
        renderResultados();
      });
    });
    content.querySelector("#sint-back")?.addEventListener("click", () => { state.phase = "busqueda"; render(); });
    content.querySelector("#sint-reanalizar")?.addEventListener("click", lanzarAnalisis);
    content.querySelector("#sint-interpretar-sel")?.addEventListener("click", async () => {
      const outEl = content.querySelector("#sint-interp-out");
      if (!outEl) return;
      const seleccionados = state.pares.filter((p) => p.checked).map((p) => p.nombre);
      // Registrar los pares confirmados en el expediente del paciente activo
      if (seleccionados.length) {
        paRegistrar("Biomagnético", `Pares confirmados — ${state.sintoma || "rastreo"}`,
          seleccionados.map((n) => "• " + n).join("\n"));
      }
      const query = `El rastreo biomagnético confirmó los siguientes pares activos para el cuadro "${escapeHtml(state.sintoma)}":\n${seleccionados.map((n) => "- " + n).join("\n")}\n\nDesde la perspectiva de la terapia holística:\n1. ¿Qué patrón biológico/emocional explica estos pares activos juntos?\n2. ¿Cuál es el programa biológico de supervivencia detrás de este cuadro?\n3. ¿Cómo se aplican los imanes y en qué orden?\n4. ¿Qué cambios puede esperar el paciente tras el tratamiento?\n5. ¿Qué trabajo complementario (emocional, nutricional, energético) potencia la sesión?\n\nSé concreto y orientado a la sesión del terapeuta.`;
      await rastreoInterpretarIA(outEl, query);
    });
  }

  render();
}

// ─── Gestión de Casos ──────────────────────────────────────────────────────
const CASOS_DB_KEY = "holo_casos_db";

function casosDb() {
  try {
    const raw = localStorage.getItem(CASOS_DB_KEY);
    return raw ? JSON.parse(raw) : { pacientes: [], casos: [] };
  } catch { return { pacientes: [], casos: [] }; }
}

function casosDbSave(db) {
  localStorage.setItem(CASOS_DB_KEY, JSON.stringify(db));
}

function casosUUID() {
  return "c" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

function casosFechaCorta(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}

// ═══════════════════════════════════════════════════════════════════════════
// PACIENTE ACTIVO — el hilo que integra todas las herramientas
// ═══════════════════════════════════════════════════════════════════════════
const PACIENTE_ACTIVO_KEY = "holo_paciente_activo";

function paGetActivoId() {
  try { return localStorage.getItem(PACIENTE_ACTIVO_KEY) || null; } catch { return null; }
}

/** Devuelve { caso, paciente } del paciente en sesión, o null. */
function paGetActivo() {
  const casoId = paGetActivoId();
  if (!casoId) return null;
  const db = casosDb();
  const caso = db.casos.find((c) => c.id === casoId);
  if (!caso) return null;
  const paciente = db.pacientes.find((p) => p.id === caso.paciente_id);
  if (!paciente) return null;
  return { caso, paciente, db };
}

function paSetActivo(casoId) {
  try { localStorage.setItem(PACIENTE_ACTIVO_KEY, casoId); } catch {}
  paRenderBanner();
}

function paClearActivo() {
  try { localStorage.removeItem(PACIENTE_ACTIVO_KEY); } catch {}
  paRenderBanner();
}

function paEdad(fechaISO) {
  if (!fechaISO) return null;
  const b = new Date(fechaISO);
  if (isNaN(b)) return null;
  const t = new Date();
  let e = t.getFullYear() - b.getFullYear();
  const m = t.getMonth() - b.getMonth();
  if (m < 0 || (m === 0 && t.getDate() < b.getDate())) e--;
  return e >= 0 ? e : null;
}

/** Registra una acción en el expediente del paciente activo (su historial de sesiones). */
function paRegistrar(tipo, titulo, detalle) {
  const act = paGetActivo();
  if (!act) return false;
  const { db, caso } = act;
  if (!caso.sesiones) caso.sesiones = [];
  caso.sesiones.push({
    id: casosUUID(),
    fecha: new Date().toISOString(),
    tipo: tipo || "General",
    nota: titulo + (detalle ? "\n" + detalle : ""),
    auto: true,
  });
  casosDbSave(db);
  return true;
}

/** Banner persistente arriba: muestra quién está en sesión. */
function paRenderBanner() {
  const banner = document.getElementById("paciente-activo-banner");
  if (!banner) return;
  const act = paGetActivo();
  if (!act) {
    banner.style.display = "none";
    banner.innerHTML = "";
    return;
  }
  const { paciente, caso } = act;
  const nombre = `${paciente.nombre || ""} ${paciente.apellidos || ""}`.trim() || "Paciente";
  const edad = paEdad(paciente.fecha_nacimiento);
  const nSes = (caso.sesiones || []).length;
  banner.style.display = "flex";
  banner.innerHTML = `
    <div class="pa-banner-info">
      <span class="pa-banner-dot"></span>
      <span class="pa-banner-label">En sesión:</span>
      <strong class="pa-banner-nombre">${escapeHtml(nombre)}</strong>
      ${edad != null ? `<span class="pa-banner-edad">· ${edad} años</span>` : ""}
      ${nSes ? `<span class="pa-banner-ses">· ${nSes} registro${nSes !== 1 ? "s" : ""}</span>` : ""}
    </div>
    <div class="pa-banner-actions">
      <button class="pa-banner-btn" id="pa-ver-expediente">📋 Expediente</button>
      <button class="pa-banner-btn pa-banner-close" id="pa-cerrar-sesion">✕ Cerrar sesión</button>
    </div>`;

  banner.querySelector("#pa-cerrar-sesion")?.addEventListener("click", () => {
    paClearActivo();
  });
  banner.querySelector("#pa-ver-expediente")?.addEventListener("click", () => {
    // Ir al tab de protocolos y abrir Gestión de Casos en el detalle del caso activo
    const protocolTab = document.querySelector('[data-tab="protocols"]');
    if (protocolTab) {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      protocolTab.classList.add("active");
      document.getElementById("tab-protocols")?.classList.add("active");
    }
    window.__paAbrirExpediente = act.caso.id;
    setTimeout(() => openProtocolDetail("gestion_casos"), 200);
  });
}

function renderGestionCasos(p, content) {
  const st = {
    phase: "dashboard",   // "dashboard" | "form" | "historial" | "detalle"
    editPacId: null,      // editing existing patient
    detalleCasoId: null,  // viewing case detail
    busqueda: "",
  };

  // Si el banner pidió abrir el expediente de un caso, ir directo al detalle
  if (window.__paAbrirExpediente) {
    st.detalleCasoId = window.__paAbrirExpediente;
    st.phase = "detalle";
    window.__paAbrirExpediente = null;
  }

  function render() {
    if (st.phase === "dashboard") renderDashboard();
    else if (st.phase === "form") renderForm();
    else if (st.phase === "historial") renderHistorial();
    else if (st.phase === "detalle") renderDetalle();
  }

  // ── Dashboard ─────────────────────────────────────────────────────────────
  function renderDashboard() {
    const db = casosDb();
    const activos = db.casos.filter((c) => c.estatus === "activo");
    const totalPac = db.pacientes.length;

    const activosHtml = activos.length === 0
      ? `<p class="casos-empty">No hay casos activos. Crea el primer caso con el botón de arriba.</p>`
      : activos.map((caso) => {
          const pac = db.pacientes.find((p) => p.id === caso.paciente_id) || {};
          const sesiones = (caso.sesiones || []).length;
          const enSesion = paGetActivoId() === caso.id;
          return `<div class="casos-card${enSesion ? " casos-card-activo" : ""}" data-cid="${caso.id}">
            <div class="casos-card-info">
              <div class="casos-card-nombre">${escapeHtml(pac.nombre || "")} ${escapeHtml(pac.apellidos || "")}${enSesion ? ` <span class="casos-badge-sesion">● En sesión</span>` : ""}</div>
              <div class="casos-card-meta">
                <span>📅 Abierto: ${casosFechaCorta(caso.fecha_inicio)}</span>
                <span>📋 ${sesiones} registro${sesiones !== 1 ? "s" : ""}</span>
              </div>
              ${pac.email ? `<div class="casos-card-email">${escapeHtml(pac.email)}</div>` : ""}
            </div>
            <div class="casos-card-actions">
              ${enSesion
                ? `<button class="wizard-nav-btn casos-btn-ensesion" disabled>● En sesión</button>`
                : `<button class="wizard-nav-btn vort-ia-btn casos-btn-sesion" data-cid="${caso.id}">▶ Poner en sesión</button>`}
              <button class="wizard-nav-btn casos-btn-notas" data-cid="${caso.id}">📋 Expediente</button>
              <button class="wizard-nav-btn casos-btn-editar" data-pid="${pac.id}">✏ Editar</button>
              <button class="wizard-nav-btn wizard-reiniciar casos-btn-finalizar" data-cid="${caso.id}">✓ Finalizar</button>
            </div>
          </div>`;
        }).join("");

    content.innerHTML = `
      <div class="rastreo-tabla-wrap casos-wrap">
        <div class="casos-header">
          <div class="casos-stats">
            <span class="casos-stat"><strong>${totalPac}</strong> pacientes</span>
            <span class="casos-stat"><strong>${activos.length}</strong> activos</span>
            <span class="casos-stat"><strong>${db.casos.filter(c => c.estatus === "finalizado").length}</strong> finalizados</span>
          </div>
          <div class="casos-header-btns">
            <button class="wizard-nav-btn casos-btn-hist" id="casos-go-hist">📖 Historial</button>
            <button class="wizard-nav-btn vort-ia-btn" id="casos-nuevo">+ Nuevo caso</button>
          </div>
        </div>
        <h3 class="casos-section-title">Casos activos</h3>
        <div class="casos-activos-list">${activosHtml}</div>
      </div>`;

    content.querySelector("#casos-nuevo")?.addEventListener("click", () => {
      st.phase = "form"; st.editPacId = null; render();
    });
    content.querySelector("#casos-go-hist")?.addEventListener("click", () => {
      st.phase = "historial"; render();
    });
    content.querySelectorAll(".casos-btn-sesion").forEach((btn) => {
      btn.addEventListener("click", () => {
        paSetActivo(btn.dataset.cid);   // pone al paciente en sesión (banner + integración)
        render();                        // refresca el dashboard para mostrar el badge
      });
    });
    content.querySelectorAll(".casos-btn-notas").forEach((btn) => {
      btn.addEventListener("click", () => { st.detalleCasoId = btn.dataset.cid; st.phase = "detalle"; render(); });
    });
    content.querySelectorAll(".casos-btn-editar").forEach((btn) => {
      btn.addEventListener("click", () => { st.editPacId = btn.dataset.pid; st.phase = "form"; render(); });
    });
    content.querySelectorAll(".casos-btn-finalizar").forEach((btn) => {
      btn.addEventListener("click", () => {
        const db = casosDb();
        const caso = db.casos.find((c) => c.id === btn.dataset.cid);
        if (caso) {
          caso.estatus = "finalizado"; caso.fecha_fin = new Date().toISOString(); casosDbSave(db);
          if (paGetActivoId() === caso.id) paClearActivo();  // si estaba en sesión, cerrarla
          render();
        }
      });
    });
  }

  // ── Formulario nuevo/editar paciente ──────────────────────────────────────
  function renderForm() {
    const db = casosDb();
    const pac = st.editPacId ? db.pacientes.find((p) => p.id === st.editPacId) : null;
    const titulo = pac ? "Editar paciente" : "Nuevo caso";

    content.innerHTML = `
      <div class="rastreo-tabla-wrap casos-wrap">
        <h3 class="casos-section-title">${titulo}</h3>
        <div class="casos-form">
          <div class="casos-form-row">
            <div class="casos-form-group">
              <label class="casos-label">Nombre(s) *</label>
              <input class="casos-input" id="cf-nombre" value="${escapeHtml(pac?.nombre || "")}" placeholder="Nombre(s)">
            </div>
            <div class="casos-form-group">
              <label class="casos-label">Apellidos *</label>
              <input class="casos-input" id="cf-apellidos" value="${escapeHtml(pac?.apellidos || "")}" placeholder="Apellidos">
            </div>
          </div>
          <div class="casos-form-row">
            <div class="casos-form-group">
              <label class="casos-label">Fecha de nacimiento</label>
              <input class="casos-input" id="cf-fecha-nac" type="date" value="${pac?.fecha_nacimiento || ""}">
            </div>
            <div class="casos-form-group">
              <label class="casos-label">Sexo</label>
              <select class="casos-input" id="cf-sexo">
                <option value="F" ${pac?.sexo === "F" ? "selected" : ""}>Femenino</option>
                <option value="M" ${pac?.sexo === "M" ? "selected" : ""}>Masculino</option>
                <option value="O" ${pac?.sexo === "O" ? "selected" : ""}>Otro</option>
              </select>
            </div>
          </div>
          <div class="casos-form-row">
            <div class="casos-form-group">
              <label class="casos-label">Celular</label>
              <input class="casos-input" id="cf-celular" value="${escapeHtml(pac?.celular || "")}" placeholder="10 dígitos">
            </div>
            <div class="casos-form-group">
              <label class="casos-label">Email</label>
              <input class="casos-input" id="cf-email" type="email" value="${escapeHtml(pac?.email || "")}" placeholder="correo@ejemplo.com">
            </div>
          </div>
          <div class="casos-form-row">
            <div class="casos-form-group">
              <label class="casos-label">¿Tiene amalgamas?</label>
              <select class="casos-input" id="cf-amalgama">
                <option value="N" ${pac?.amalgama !== "S" ? "selected" : ""}>Sin amalgamas</option>
                <option value="S" ${pac?.amalgama === "S" ? "selected" : ""}>Con amalgamas</option>
              </select>
            </div>
            <div class="casos-form-group">
              <label class="casos-label">Referenciado por</label>
              <input class="casos-input" id="cf-referenciado" value="${escapeHtml(pac?.referenciado || "")}" placeholder="Nombre de quien lo refirió">
            </div>
          </div>
          <div class="casos-form-group" style="margin-top:8px">
            <label class="casos-label">Motivo de consulta / Observaciones</label>
            <textarea class="vort-ia-textarea" id="cf-observaciones" placeholder="Motivo principal, síntomas, antecedentes relevantes...">${escapeHtml(pac?.observaciones || "")}</textarea>
          </div>
          <div id="casos-form-error" class="casos-form-error" style="display:none"></div>
          <div class="wizard-nav" style="margin-top:16px">
            <button class="wizard-nav-btn" id="cf-cancelar">← Cancelar</button>
            <button class="wizard-nav-btn vort-ia-btn" id="cf-guardar">💾 ${pac ? "Guardar cambios" : "Crear caso"}</button>
          </div>
        </div>
      </div>`;

    content.querySelector("#cf-cancelar")?.addEventListener("click", () => { st.phase = "dashboard"; render(); });
    content.querySelector("#cf-guardar")?.addEventListener("click", () => {
      const nombre = content.querySelector("#cf-nombre")?.value.trim();
      const apellidos = content.querySelector("#cf-apellidos")?.value.trim();
      const errEl = content.querySelector("#casos-form-error");
      if (!nombre || !apellidos) {
        errEl.textContent = "Nombre y apellidos son obligatorios."; errEl.style.display = "block"; return;
      }
      const db = casosDb();
      const now = new Date().toISOString();
      if (pac) {
        const existing = db.pacientes.find((p) => p.id === pac.id);
        if (existing) {
          Object.assign(existing, {
            nombre, apellidos,
            fecha_nacimiento: content.querySelector("#cf-fecha-nac")?.value || "",
            sexo: content.querySelector("#cf-sexo")?.value || "F",
            celular: content.querySelector("#cf-celular")?.value.trim() || "",
            email: content.querySelector("#cf-email")?.value.trim() || "",
            amalgama: content.querySelector("#cf-amalgama")?.value || "N",
            referenciado: content.querySelector("#cf-referenciado")?.value.trim() || "",
            observaciones: content.querySelector("#cf-observaciones")?.value.trim() || "",
            fecha_modificacion: now,
          });
        }
      } else {
        const pacId = casosUUID();
        const casoId = casosUUID();
        db.pacientes.push({
          id: pacId, nombre, apellidos,
          fecha_nacimiento: content.querySelector("#cf-fecha-nac")?.value || "",
          sexo: content.querySelector("#cf-sexo")?.value || "F",
          celular: content.querySelector("#cf-celular")?.value.trim() || "",
          email: content.querySelector("#cf-email")?.value.trim() || "",
          amalgama: content.querySelector("#cf-amalgama")?.value || "N",
          referenciado: content.querySelector("#cf-referenciado")?.value.trim() || "",
          observaciones: content.querySelector("#cf-observaciones")?.value.trim() || "",
          fecha_alta: now,
        });
        db.casos.push({ id: casoId, paciente_id: pacId, estatus: "activo", fecha_inicio: now, fecha_fin: null, sesiones: [] });
        casosDbSave(db);
        paSetActivo(casoId);  // el nuevo caso queda automáticamente en sesión
        st.phase = "dashboard"; st.editPacId = null; render();
        return;
      }
      casosDbSave(db);
      st.phase = "dashboard"; st.editPacId = null; render();
    });
  }

  // ── Detalle de caso + notas de sesión ─────────────────────────────────────
  function renderDetalle() {
    const db = casosDb();
    const caso = db.casos.find((c) => c.id === st.detalleCasoId);
    if (!caso) { st.phase = "dashboard"; render(); return; }
    const pac = db.pacientes.find((p) => p.id === caso.paciente_id) || {};
    const sesiones = caso.sesiones || [];

    const sesionesHtml = sesiones.length === 0
      ? `<p class="casos-empty">Sin notas de sesión aún.</p>`
      : sesiones.slice().reverse().map((s) => `
          <div class="casos-sesion-row">
            <div class="casos-sesion-fecha">${casosFechaCorta(s.fecha)}</div>
            <div class="casos-sesion-tipo">${escapeHtml(s.tipo || "General")}</div>
            <div class="casos-sesion-nota">${escapeHtml(s.nota || "")}</div>
          </div>`).join("");

    content.innerHTML = `
      <div class="rastreo-tabla-wrap casos-wrap">
        <div class="casos-detalle-header">
          <div>
            <div class="casos-card-nombre">${escapeHtml(pac.nombre || "")} ${escapeHtml(pac.apellidos || "")}</div>
            <div class="casos-card-meta">
              <span>📅 Inicio: ${casosFechaCorta(caso.fecha_inicio)}</span>
              ${pac.fecha_nacimiento ? `<span>🎂 ${casosFechaCorta(pac.fecha_nacimiento)}</span>` : ""}
              ${pac.celular ? `<span>📱 ${escapeHtml(pac.celular)}</span>` : ""}
              ${pac.amalgama === "S" ? `<span class="casos-amalgama-tag">⚠ Amalgamas</span>` : ""}
            </div>
            ${pac.observaciones ? `<div class="casos-det-obs">${escapeHtml(pac.observaciones)}</div>` : ""}
          </div>
        </div>

        <h4 class="casos-section-title" style="margin-top:16px">Agregar nota de sesión</h4>
        <div class="casos-form-row">
          <div class="casos-form-group" style="flex:1">
            <select class="casos-input" id="det-tipo">
              <option value="Biomagnético">Biomagnético</option>
              <option value="Emocional">Emocional</option>
              <option value="Vórtices">Vórtices</option>
              <option value="EFT">EFT</option>
              <option value="Numerología">Numerología</option>
              <option value="Astrología">Astrología</option>
              <option value="General">General</option>
            </select>
          </div>
        </div>
        <textarea class="vort-ia-textarea" id="det-nota" placeholder="Pares aplicados, vórtices trabajados, emociones liberadas, observaciones del paciente..." style="min-height:80px"></textarea>
        <div class="wizard-nav" style="margin-top:8px">
          <button class="wizard-nav-btn vort-ia-btn" id="det-guardar-nota">💾 Guardar nota</button>
          <button class="wizard-nav-btn vort-ia-btn" id="det-ia-resumen">🧠 Resumen con Motor IA</button>
        </div>
        <div id="det-ia-out"></div>

        <h4 class="casos-section-title" style="margin-top:20px">Historial de sesiones (${sesiones.length})</h4>
        <div class="casos-sesiones-list">${sesionesHtml}</div>

        <div class="wizard-nav" style="margin-top:16px">
          <button class="wizard-nav-btn" id="det-back">← Volver</button>
          <button class="wizard-nav-btn wizard-reiniciar" id="det-finalizar">✓ Finalizar caso</button>
        </div>
      </div>`;

    content.querySelector("#det-guardar-nota")?.addEventListener("click", () => {
      const nota = content.querySelector("#det-nota")?.value.trim();
      if (!nota) return;
      const tipo = content.querySelector("#det-tipo")?.value || "General";
      const db = casosDb();
      const c = db.casos.find((x) => x.id === st.detalleCasoId);
      if (c) {
        if (!c.sesiones) c.sesiones = [];
        c.sesiones.push({ id: casosUUID(), fecha: new Date().toISOString(), tipo, nota });
        casosDbSave(db);
        render();
      }
    });
    content.querySelector("#det-ia-resumen")?.addEventListener("click", async () => {
      const outEl = content.querySelector("#det-ia-out");
      if (!outEl) return;
      const db = casosDb();
      const c = db.casos.find((x) => x.id === st.detalleCasoId);
      const p2 = db.pacientes.find((x) => x.id === c?.paciente_id) || {};
      const sesStr = (c?.sesiones || []).map((s) => `- [${s.tipo}] ${casosFechaCorta(s.fecha)}: ${s.nota}`).join("\n") || "Sin sesiones registradas.";
      const query = `Analiza el historial de un paciente de terapia holística:\n\nPaciente: ${p2.nombre} ${p2.apellidos}\nMotivo de consulta: ${p2.observaciones || "No especificado"}\n${p2.amalgama === "S" ? "⚠ Tiene amalgamas dentales.\n" : ""}\nSesiones registradas:\n${sesStr}\n\nDesde la perspectiva holística: ¿Qué patrones emergen en el historial? ¿Qué avances se observan? ¿Qué áreas requieren más trabajo? ¿Qué recomiendas para la próxima sesión? Da un análisis clínico orientado al terapeuta.`;
      await rastreoInterpretarIA(outEl, query);
    });
    content.querySelector("#det-back")?.addEventListener("click", () => { st.phase = "dashboard"; render(); });
    content.querySelector("#det-finalizar")?.addEventListener("click", () => {
      const db = casosDb();
      const c = db.casos.find((x) => x.id === st.detalleCasoId);
      if (c) { c.estatus = "finalizado"; c.fecha_fin = new Date().toISOString(); casosDbSave(db); }
      st.phase = "dashboard"; render();
    });
  }

  // ── Historial ─────────────────────────────────────────────────────────────
  function renderHistorial() {
    const db = casosDb();
    const finalizados = db.casos.filter((c) => c.estatus === "finalizado");

    const filtrados = finalizados.filter((c) => {
      if (!st.busqueda) return true;
      const pac = db.pacientes.find((p) => p.id === c.paciente_id) || {};
      const nombre = `${pac.nombre} ${pac.apellidos}`.toLowerCase();
      return nombre.includes(st.busqueda.toLowerCase());
    });

    const histHtml = filtrados.length === 0
      ? `<p class="casos-empty">No se encontraron casos finalizados.</p>`
      : filtrados.slice().sort((a, b) => new Date(b.fecha_fin) - new Date(a.fecha_fin)).map((caso) => {
          const pac = db.pacientes.find((p) => p.id === caso.paciente_id) || {};
          const sesiones = (caso.sesiones || []).length;
          return `<div class="casos-hist-row" data-cid="${caso.id}">
            <div class="casos-hist-nombre">${escapeHtml(pac.nombre || "")} ${escapeHtml(pac.apellidos || "")}</div>
            <div class="casos-card-meta">
              <span>📅 ${casosFechaCorta(caso.fecha_inicio)} → ${casosFechaCorta(caso.fecha_fin)}</span>
              <span>📋 ${sesiones} sesión${sesiones !== 1 ? "es" : ""}</span>
            </div>
            <button class="wizard-nav-btn casos-hist-ver" data-cid="${caso.id}">Ver detalle</button>
          </div>`;
        }).join("");

    content.innerHTML = `
      <div class="rastreo-tabla-wrap casos-wrap">
        <div class="casos-header">
          <h3 class="casos-section-title" style="margin:0">Historial de casos</h3>
          <button class="wizard-nav-btn" id="hist-back">← Volver</button>
        </div>
        <input class="casos-input" id="hist-buscar" placeholder="Buscar por nombre..." value="${escapeHtml(st.busqueda)}" style="margin:12px 0">
        <div class="casos-hist-list">${histHtml}</div>
      </div>`;

    content.querySelector("#hist-back")?.addEventListener("click", () => { st.phase = "dashboard"; render(); });
    content.querySelector("#hist-buscar")?.addEventListener("input", (e) => { st.busqueda = e.target.value; renderHistorial(); });
    content.querySelectorAll(".casos-hist-ver").forEach((btn) => {
      btn.addEventListener("click", () => {
        // Reactivate temporarily for viewing
        const db = casosDb(); const c = db.casos.find((x) => x.id === btn.dataset.cid);
        if (c) { const prev = c.estatus; c.estatus = "activo"; casosDbSave(db); st.detalleCasoId = btn.dataset.cid; st.phase = "detalle"; render(); }
      });
    });
  }

  render();
}

// ─── Terapia de Vórtices ────────────────────────────────────────────────────
function renderTerapiaVortices(p, content) {
  const cache = { data: null };
  const state = {
    phase: "categoria",      // "categoria" | "puntos" | "consulta_ia"
    categoria: null,         // { id, nombre, icono, puntos[] }
    timers: {},              // { puntoId: intervalId }
    tiempos: {},             // { puntoId: segundosRestantes }
    checked: new Set(),      // puntoIds completados
    activeTimer: null,       // puntoId con timer activo
  };

  async function init() {
    content.innerHTML = `<div class="ra-loading"><div class="rastreo-interpret-spinner"></div><span>Cargando catálogo de vórtices...</span></div>`;
    try {
      const res = await fetch("/api/vortices/catalogo");
      cache.data = res.ok ? await res.json() : null;
    } catch { cache.data = null; }
    renderFase();
  }

  function renderFase() {
    if (state.phase === "categoria") renderCategoriasView();
    else if (state.phase === "puntos") renderPuntosView();
    else if (state.phase === "consulta_ia") renderConsultaIA();
  }

  // ── Fase 1: Selección de categoría ─────────────────────────────────────────
  function renderCategoriasView() {
    const cats = cache.data?.categorias || [];
    const instrMs = p.instruccion_ms || "MS: '¿Hay algún vórtice activo que necesite equilibrarse en esta sesión?'";

    const catCards = cats.map((cat) => {
      const isPos = cat.id === "positivos";
      return `<div class="vort-cat-card ${isPos ? "vort-cat-pos" : "vort-cat-neg"}" data-cat="${cat.id}">
        <div class="vort-cat-icon">${cat.icono}</div>
        <div class="vort-cat-nombre">${escapeHtml(cat.nombre)}</div>
        <div class="vort-cat-polaridad">Polo ${escapeHtml(cat.polaridad || (isPos ? "Norte" : "Sur"))}</div>
        <div class="vort-cat-desc">${escapeHtml(cat.descripcion || "")}</div>
        <div class="vort-cat-count">${cat.puntos?.length || 0} puntos</div>
      </div>`;
    }).join("");

    const todosCard = cats.length > 0 ? `
      <div class="vort-cat-card vort-cat-todos" data-cat="todos">
        <div class="vort-cat-icon">⚡</div>
        <div class="vort-cat-nombre">Todos los Vórtices</div>
        <div class="vort-cat-polaridad">Positivos + Negativos</div>
        <div class="vort-cat-desc">Protocolo completo de equilibrio bioenergético.</div>
        <div class="vort-cat-count">${cats.reduce((a, c) => a + (c.puntos?.length || 0), 0)} puntos totales</div>
      </div>` : "";

    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        <div class="rastreo-instruccion-ms">
          <span class="rastreo-ms-badge">MS</span>
          <span>${escapeHtml(instrMs)}</span>
        </div>
        <p class="creencia-instruccion-paso">Selecciona la polaridad que responde SÍ con test muscular:</p>
        <div class="vort-cat-grid">${catCards}${todosCard}</div>
        <div class="wizard-nav" style="margin-top:16px">
          <button class="wizard-nav-btn vort-ia-btn" id="vort-consultar-ia">🧠 Consultar al Motor — ¿qué vórtices activar?</button>
        </div>
      </div>`;

    content.querySelectorAll(".vort-cat-card").forEach((el) => {
      el.addEventListener("click", () => {
        const catId = el.dataset.cat;
        if (catId === "todos") {
          const todosLosLotes = cats.flatMap((c) => c.puntos.map((pt) => ({ ...pt, _cat: c.id, _catNombre: c.nombre, _icono: c.icono })));
          state.categoria = { id: "todos", nombre: "Todos los Vórtices", icono: "⚡", puntos: todosLosLotes };
        } else {
          const found = cats.find((c) => c.id === catId);
          if (found) state.categoria = { ...found, puntos: found.puntos.map((pt) => ({ ...pt, _cat: found.id, _catNombre: found.nombre, _icono: found.icono })) };
        }
        state.phase = "puntos";
        state.timers = {}; state.tiempos = {}; state.checked = new Set(); state.activeTimer = null;
        renderFase();
      });
    });
    content.querySelector("#vort-consultar-ia")?.addEventListener("click", () => {
      state.phase = "consulta_ia"; renderFase();
    });
  }

  // ── Fase 2: Lista de puntos con timer ──────────────────────────────────────
  function renderPuntosView() {
    const cat = state.categoria;
    if (!cat) { state.phase = "categoria"; renderFase(); return; }
    const puntos = cat.puntos || [];
    const completados = state.checked.size;
    const total = puntos.length;
    const progPct = total > 0 ? Math.round((completados / total) * 100) : 0;

    const puntosHtml = puntos.map((pt) => {
      const ptId = pt.id;
      const isDone = state.checked.has(ptId);
      const isActive = state.activeTimer === ptId;
      const segsLeft = state.tiempos[ptId] ?? pt.tiempoSegundos;
      const timerDisplay = segsToHMS(segsLeft);
      const isPos = pt._cat === "positivos" || cat.id === "positivos";
      const polColor = isPos ? "#dc2626" : "#2563eb";

      return `<div class="vort-punto-row${isDone ? " vort-punto-done" : ""}" data-ptid="${ptId}">
        <div class="vort-punto-check${isDone ? " vort-punto-check-done" : ""}" data-check="${ptId}">
          ${isDone ? "✓" : ""}
        </div>
        <div class="vort-punto-info" data-expand="${ptId}">
          <div class="vort-punto-nombre">${isPos ? "🔴" : "🔵"} ${escapeHtml(pt.nombre)}</div>
          <div class="vort-punto-anat">${escapeHtml(pt.punto_anatomico || "")}</div>
        </div>
        <div class="vort-punto-timer-wrap">
          <button class="vort-timer-btn${isActive ? " vort-timer-active" : ""}${isDone ? " vort-timer-done" : ""}"
            data-timer="${ptId}" data-secs="${pt.tiempoSegundos}"
            ${state.activeTimer && state.activeTimer !== ptId ? "disabled" : ""}
            style="border-color:${polColor}${isActive ? ";background:" + polColor : ""}">
            ${timerDisplay}
          </button>
        </div>
        <button class="vort-detail-btn" data-detail="${ptId}" title="Ver detalle">ℹ</button>
      </div>
      <div class="vort-detalle-panel" id="vort-det-${ptId}" style="display:none">
        <div class="vort-det-body">
          <p class="vort-det-desc">${escapeHtml(pt.descripcion || "")}</p>
          ${pt.sintomas_asociados?.length ? `<div class="vort-det-sintomas"><strong>Síntomas asociados:</strong> ${pt.sintomas_asociados.map(s => `<span class="vort-det-tag">${escapeHtml(s)}</span>`).join("")}</div>` : ""}
          ${pt.indicaciones ? `<p class="vort-det-indicaciones"><strong>Indicaciones:</strong> ${escapeHtml(pt.indicaciones)}</p>` : ""}
          <button class="rastreo-interpret-btn vort-interp-btn" data-interp="${ptId}" style="background:${polColor}">✨ Interpretar con Motor Terapéutico</button>
          <div id="vort-interp-out-${ptId}"></div>
        </div>
      </div>`;
    }).join("");

    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        <div class="vort-header">
          <div class="vort-header-cat">
            <span class="vort-header-icono">${cat.icono}</span>
            <span class="vort-header-nombre">${escapeHtml(cat.nombre)}</span>
          </div>
          <div class="vort-progreso-wrap">
            <div class="vort-progreso-bar"><div class="vort-progreso-fill" style="width:${progPct}%"></div></div>
            <span class="vort-progreso-label">${completados}/${total} completados</span>
          </div>
        </div>
        ${state.activeTimer ? `<div class="vort-timer-banner">⏱ Timer activo — los demás puntos están bloqueados hasta que este termine o se detenga</div>` : ""}
        <div class="vort-puntos-list">${puntosHtml}</div>
        <div id="vort-global-interp-out"></div>
        <div class="wizard-nav" style="margin-top:16px">
          <button class="wizard-nav-btn" id="vort-back-btn">← Cambiar polaridad</button>
          ${completados > 0 ? `<button class="wizard-nav-btn vort-ia-btn" id="vort-finalizar-btn">✨ Interpretar sesión completa</button>` : ""}
          <button class="wizard-nav-btn wizard-reiniciar" id="vort-reset-btn">Reiniciar</button>
        </div>
      </div>`;

    // Timer buttons
    content.querySelectorAll(".vort-timer-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const ptId = btn.dataset.timer;
        if (state.activeTimer === ptId) {
          // Pause/stop active timer
          clearInterval(state.timers[ptId]);
          delete state.timers[ptId];
          state.activeTimer = null;
          renderPuntosView();
        } else if (!state.activeTimer) {
          // Start timer
          if (state.tiempos[ptId] === undefined) state.tiempos[ptId] = parseInt(btn.dataset.secs);
          state.activeTimer = ptId;
          state.timers[ptId] = setInterval(() => {
            state.tiempos[ptId] = (state.tiempos[ptId] ?? parseInt(btn.dataset.secs)) - 1;
            if (state.tiempos[ptId] <= 0) {
              state.tiempos[ptId] = 0;
              clearInterval(state.timers[ptId]);
              delete state.timers[ptId];
              state.activeTimer = null;
              state.checked.add(ptId);
              renderPuntosView();
            } else {
              // Update only the timer display without full re-render
              const timerEl = content.querySelector(`[data-timer="${ptId}"]`);
              if (timerEl) timerEl.textContent = segsToHMS(state.tiempos[ptId]);
            }
          }, 1000);
          renderPuntosView();
        }
      });
    });

    // Manual check/uncheck
    content.querySelectorAll(".vort-punto-check").forEach((el) => {
      el.addEventListener("click", () => {
        const ptId = el.dataset.check;
        if (state.checked.has(ptId)) { state.checked.delete(ptId); }
        else { state.checked.add(ptId); }
        renderPuntosView();
      });
    });

    // Expand/collapse detail
    content.querySelectorAll(".vort-detail-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const ptId = btn.dataset.detail;
        const panel = content.querySelector(`#vort-det-${ptId}`);
        if (panel) panel.style.display = panel.style.display === "none" ? "block" : "none";
      });
    });

    // Interpret button per punto
    content.querySelectorAll(".vort-interp-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const ptId = btn.dataset.interp;
        const outEl = content.querySelector(`#vort-interp-out-${ptId}`);
        if (!outEl) return;
        const pt = puntos.find((x) => x.id === ptId);
        if (!pt) return;
        const query = `Durante la terapia biomagnética, el vórtice "${pt.nombre}" (${pt.punto_anatomico}) resultó activo. Polaridad: ${pt._cat === "positivos" ? "positiva (polo norte)" : "negativa (polo sur)"}.\n\nDesde la perspectiva holística: ¿Qué significa la activación de este vórtice? ¿Qué patrón energético, emocional o físico está relacionado? ¿Cómo se manifiesta este desequilibrio en el cuerpo y la conducta del paciente? ¿Qué se logra al equilibrarlo? Orienta para la sesión de forma concreta.`;
        await rastreoInterpretarIA(outEl, query);
      });
    });

    // Finalizar sesión completa
    content.querySelector("#vort-finalizar-btn")?.addEventListener("click", async () => {
      const outEl = content.querySelector("#vort-global-interp-out");
      if (!outEl) return;
      const completadosList = puntos.filter((pt) => state.checked.has(pt.id));
      const nombresCompletados = completadosList.map((pt) => `- ${pt.nombre} (${pt.punto_anatomico})`).join("\n");
      const query = `Se completó una sesión de Terapia de Vórtices. Los vórtices equilibrados fueron:\n${nombresCompletados}\n\nDesde la perspectiva terapéutica holística: ¿Qué patrón global de desequilibrio bioenergético estaba presente? ¿Cómo se relacionan estos vórtices entre sí? ¿Qué proceso de sanación se activa al equilibrarlos en conjunto? ¿Qué puede esperar el paciente en los días siguientes? Da una síntesis orientada para el cierre de sesión.`;
      outEl.scrollIntoView({ behavior: "smooth" });
      await rastreoInterpretarIA(outEl, query);
    });

    content.querySelector("#vort-back-btn")?.addEventListener("click", () => {
      // Stop any active timer
      if (state.activeTimer) { clearInterval(state.timers[state.activeTimer]); state.activeTimer = null; }
      state.phase = "categoria"; renderFase();
    });
    content.querySelector("#vort-reset-btn")?.addEventListener("click", () => {
      if (state.activeTimer) { clearInterval(state.timers[state.activeTimer]); state.activeTimer = null; }
      state.timers = {}; state.tiempos = {}; state.checked = new Set();
      renderPuntosView();
    });
  }

  // ── Fase 3: Consulta IA — qué vórtices activar ─────────────────────────────
  function renderConsultaIA() {
    content.innerHTML = `
      <div class="rastreo-tabla-wrap">
        <h3 class="wizard-protocol-name" style="margin-bottom:16px">🧠 Consulta al Motor Terapéutico</h3>
        <p class="creencia-instruccion-paso">Describe brevemente el caso o motivo de consulta y el Motor sugerirá qué vórtices activar:</p>
        <textarea class="vort-ia-textarea" id="vort-ia-input" placeholder="Ej: Paciente con fatiga crónica, dolores lumbares, ansiedad generalizada y bloqueo emocional en relaciones..."></textarea>
        <div class="wizard-nav" style="margin-top:12px">
          <button class="wizard-nav-btn" id="vort-ia-back">← Volver</button>
          <button class="wizard-nav-btn vort-ia-btn" id="vort-ia-send">Consultar al Motor →</button>
        </div>
        <div id="vort-ia-output"></div>
      </div>`;

    content.querySelector("#vort-ia-back")?.addEventListener("click", () => {
      state.phase = "categoria"; renderFase();
    });
    content.querySelector("#vort-ia-send")?.addEventListener("click", async () => {
      const outEl = content.querySelector("#vort-ia-output");
      const input = content.querySelector("#vort-ia-input");
      if (!outEl || !input?.value.trim()) return;
      const vortsList = (cache.data?.categorias || []).flatMap((c) =>
        (c.puntos || []).map((pt) => `${c.icono} ${pt.nombre} — ${pt.punto_anatomico} (${c.nombre})`)
      ).join("\n");
      const query = `Eres el Motor Terapéutico de HoloacademIA especializado en terapia biomagnética.\n\nEl terapeuta describe el caso:\n"${input.value.trim()}"\n\nCatálogo de vórtices disponibles:\n${vortsList}\n\nAnaliza el caso e indica:\n1. Qué vórtices recomiendas activar (positivos y/o negativos) y por qué\n2. En qué orden trabajarlos\n3. Qué patrón energético global hay que equilibrar\n4. Qué resultado esperar tras la terapia de vórtices\n\nSé específico y orientado a la sesión.`;
      await rastreoInterpretarIA(outEl, query);
    });
  }

  // ── Helper ──────────────────────────────────────────────────────────────────
  function segsToHMS(secs) {
    const s = Math.max(0, secs);
    const h = Math.floor(s / 3600).toString().padStart(2, "0");
    const m = Math.floor((s % 3600) / 60).toString().padStart(2, "0");
    const sec = (s % 60).toString().padStart(2, "0");
    return `${h}:${m}:${sec}`;
  }

  init();
}

function openProtocolDetail(protocolId) {
  const all = catalogData?.categories?.flatMap((c) => c.protocolos) ?? [];
  const p = all.find((x) => x.id === protocolId);
  if (!p) return;

  const catMeta = catalogData?.categories?.find((c) =>
    c.protocolos.some((x) => x.id === protocolId)
  );

  const content = document.getElementById("catalog-detail-content");
  if (content) {
    if (protocolId === "diagnostico_organico") {
      renderDiagnosticoOrganico(p, content);
    } else if (p.render_tipo === "tool_link") {
      renderToolLink(p, content);
    } else if (p.render_tipo === "numerologia_terapeutica") {
      renderNumerologiaTerapeutica(p, content);
    } else if (p.render_tipo === "sueno_terapeutico") {
      renderSuenoTerapeutico(p, content);
    } else if (p.render_tipo === "carta_natal") {
      renderCartaNatal(p, content);
    } else if (p.render_tipo === "diario_lunar") {
      renderDiarioLunar(p, content);
    } else if (p.render_tipo === "catalogo_biomagnetico") {
      renderCatalogoBiomagnetico(p, content);
    } else if (p.render_tipo === "rastreo_sintoma") {
      renderRastreoSintoma(p, content);
    } else if (p.render_tipo === "gestion_casos") {
      renderGestionCasos(p, content);
    } else if (p.render_tipo === "terapia_vortices") {
      renderTerapiaVortices(p, content);
    } else if (p.render_tipo === "rastreos_avanzados") {
      renderRastreosAvanzados(p, content);
    } else if (p.render_tipo === "tabla_hologramas") {
      renderTablaHologramas(p, content);
    } else if (p.render_tipo === "tabla_nudos_psoricos") {
      renderTablaNudosPsoricos(p, content);
    } else if (p.render_tipo === "tabla_creencias") {
      renderTablaCreencias(p, content);
    } else if (wizardHasInteractivePasos(p)) {
      // Initialize wizard state
      wizardState.protocol = p;
      wizardState.pasos = (p.pasos || []).slice().sort((a, b) => a.orden - b.orden);
      wizardState.currentIndex = 0;
      wizardState.circuit = {};
      wizardState.siAnswered = {};
      wizardState.skippedPasos = new Set();
      wizardMount(content);
    } else {
      content.innerHTML = wizardRenderFallback(p, catMeta);
    }
  }

  const overlay = document.getElementById("catalog-detail-overlay");
  overlay?.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeCatalogDetail() {
  const overlay = document.getElementById("catalog-detail-overlay");
  overlay?.classList.add("hidden");
  document.body.style.overflow = "";
}

document.getElementById("catalog-detail-close")?.addEventListener("click", closeCatalogDetail);
document.getElementById("catalog-detail-overlay")?.addEventListener("click", (e) => {
  if (e.target === e.currentTarget) closeCatalogDetail();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeCatalogDetail();
});

// Cargar catálogo al abrir la pestaña o al inicializar si ya está activa
tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    if (tab.dataset.tab === "protocols") loadCatalog();
  });
});

// Pre-cargar el catálogo siempre para evitar depender del clic
// Soporte de deep links: /rastreo?p=catalogo_biomagnetico o hash #catalogo_biomagnetico
(async function initWithDeepLink() {
  await loadCatalog();
  const urlParams = new URLSearchParams(window.location.search);
  const pFromQuery = urlParams.get("p") || urlParams.get("protocol");
  const pFromHash  = window.location.hash.replace("#", "");
  const targetId   = pFromQuery || pFromHash;
  if (targetId && catalogData) {
    // Switch to protocols tab first
    const protocolTab = document.querySelector('[data-tab="protocols"]');
    if (protocolTab) {
      document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
      protocolTab.classList.add("active");
      document.getElementById("tab-protocols")?.classList.add("active");
    }
    // Open the protocol detail
    setTimeout(() => openProtocolDetail(targetId), 200);
  }
})();
if (protocolOutput) setStatus(protocolOutput, "Aquí aparecerá la guía del protocolo consultado.");

// Inicializar banner de paciente activo al cargar
try { paRenderBanner(); } catch (e) { /* noop */ }

// ── Modo Por Sistema Corporal ──────────────────────────────────────────────

const SYSTEM_ICONS = {
  respiratorio: "🫁", digestivo: "🫀", alimenticio: "🍽️",
  endocrino: "⚗️", cardiovascular: "❤️", osteomuscular: "🦴",
  dermato_lipofascial: "🩹", reproductivo: "🌸", urinario: "💧",
  inmunologico: "🛡️", neurosensorial: "🧠",
};

let systemsData = null;
let activeSystemId = null;
let systemsCache = {};

async function loadSystemsMode() {
  if (systemsData) { renderSystemsNav(); return; }
  const statusEl = document.getElementById("catalog-status");
  try {
    if (statusEl) setStatus(statusEl, "Cargando sistemas…");
    const res = await fetch("/protocols/systems");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    systemsData = await res.json();
    if (statusEl) statusEl.innerHTML = "";
    renderSystemsNav();
    if (systemsData.systems?.length) {
      selectSystem(systemsData.systems[0].id);
    }
  } catch (err) {
    if (statusEl) setStatus(statusEl, "No se pudo cargar la lista de sistemas.", true);
  }
}

function renderSystemsNav() {
  const nav = document.getElementById("catalog-systems-nav");
  if (!nav || !systemsData) return;
  nav.innerHTML = systemsData.systems.map((s) => {
    const icon = SYSTEM_ICONS[s.id] || "🔬";
    const subsCount = s.subsystems?.length ?? 0;
    return `
      <button class="catalog-cat-btn" data-system="${escapeHtml(s.id)}">
        <span class="cat-icon">${icon}</span>
        <span>${escapeHtml(s.nombre.replace("Sistema ", ""))}</span>
        <span class="catalog-cat-count">${s.total_conflicts ?? subsCount}</span>
      </button>`;
  }).join("");
  nav.querySelectorAll(".catalog-cat-btn").forEach((btn) => {
    btn.addEventListener("click", () => selectSystem(btn.dataset.system));
  });
}

async function selectSystem(systemId) {
  activeSystemId = systemId;
  document.querySelectorAll("#catalog-systems-nav .catalog-cat-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.system === systemId);
  });

  const header = document.getElementById("catalog-system-header");
  const sectionsEl = document.getElementById("catalog-system-sections");
  const sys = systemsData?.systems?.find((s) => s.id === systemId);

  if (header && sys) {
    header.classList.remove("hidden");
    const icon = SYSTEM_ICONS[sys.id] || "🔬";
    const conflicts = sys.total_conflicts ? `${sys.total_conflicts} conflictos` : `${sys.subsystems?.length ?? 0} subsistemas`;
    header.innerHTML = `
      <h3>${icon} ${escapeHtml(sys.nombre)}</h3>
      <p>${escapeHtml(conflicts)} · Selecciona una sección para ver el contenido completo</p>`;
  }

  if (sectionsEl) sectionsEl.innerHTML = `<p class="status">Cargando...</p>`;

  try {
    let detail = systemsCache[systemId];
    if (!detail) {
      const res = await fetch(`/protocols/systems/${encodeURIComponent(systemId)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      detail = await res.json();
      systemsCache[systemId] = detail;
    }
    renderSystemSections(detail);
  } catch (err) {
    if (sectionsEl) sectionsEl.innerHTML = `<p class="status error">No se pudo cargar el contenido del sistema.</p>`;
  }
}

function renderConflictCard(c) {
  const numBadge = c.number != null
    ? `<span class="conflict-number">${c.number}</span>`
    : `<span class="conflict-number conflict-number-empty">·</span>`;
  const name = c.name
    ? `<span class="conflict-name">${escapeHtml(c.name)}</span>`
    : '';
  const phrases = c.phrases.length
    ? `<div class="conflict-phrases">${c.phrases.map((p) => `<p class="conflict-phrase">"${escapeHtml(p)}"</p>`).join('')}</div>`
    : '';
  return `<div class="conflict-card">${numBadge}${name}${phrases}</div>`;
}

function renderConflictsParsed(subsystems) {
  return subsystems.map((sub) => {
    const cards = sub.conflicts.map(renderConflictCard).join('');
    const count = sub.conflicts.length;
    return `
      <div class="conflict-subsystem">
        <div class="conflict-subsystem-header">
          <span class="conflict-subsystem-title">${escapeHtml(sub.subsystem)}</span>
          <span class="conflict-subsystem-count">${count} conflicto${count !== 1 ? 's' : ''}</span>
        </div>
        <div class="conflict-list">${cards}</div>
      </div>`;
  }).join('');
}

function renderSectionContent(sec) {
  if (sec.conflicts_parsed && sec.conflicts_parsed.length) {
    return `<div class="conflict-map-container">${renderConflictsParsed(sec.conflicts_parsed)}</div>`;
  }
  // Fallback: show cleaned text line by line
  const cleaned = (sec.content || '')
    .split('\n')
    .map((l) => l.trimEnd())
    .filter((l, i, arr) => !(l === '' && arr[i - 1] === ''))
    .join('\n');
  return `<pre class="system-section-text">${escapeHtml(cleaned)}</pre>`;
}

function renderSystemSections(detail) {
  const el = document.getElementById("catalog-system-sections");
  if (!el) return;

  // Filter out uninformative tiny intro sections (module title only)
  const sections = (detail.sections || []).filter((s) => (s.content || '').length > 80);
  if (!sections.length) {
    el.innerHTML = `<p class="status">Sin contenido disponible para este sistema.</p>`;
    return;
  }

  // Default: open first section with conflict cards, else first educational section
  const firstWithConflicts = sections.findIndex((s) => s.conflicts_parsed?.length);
  const firstSubstantive = sections.findIndex((s) => (s.content || '').length > 500);
  const defaultOpen = firstWithConflicts >= 0 ? firstWithConflicts : Math.max(0, firstSubstantive);

  el.innerHTML = sections.map((sec, i) => {
    const isOpen = i === defaultOpen;
    const hasConflicts = sec.conflicts_parsed?.length;
    const conflictCount = hasConflicts
      ? sec.conflicts_parsed.reduce((n, sub) => n + sub.conflicts.length, 0) : 0;
    const badge = hasConflicts
      ? `<span class="section-badge">${conflictCount} conflictos</span>`
      : '';
    const truncBadge = sec.truncated
      ? `<span class="section-badge section-badge-trunc">vista parcial</span>`
      : '';
    return `
      <div class="system-section-card">
        <button class="system-section-toggle${isOpen ? " open" : ""}" data-sec="${i}">
          <span class="section-toggle-label">${escapeHtml(sec.label)}${badge}${truncBadge}</span>
          <span class="toggle-chevron">▼</span>
        </button>
        <div class="system-section-body${isOpen ? " open" : ""}">
          ${renderSectionContent(sec)}
        </div>
      </div>`;
  }).join("");

  el.querySelectorAll(".system-section-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const body = btn.nextElementSibling;
      const isOpen = btn.classList.contains("open");
      btn.classList.toggle("open", !isOpen);
      body.classList.toggle("open", !isOpen);
    });
  });
}

// ── Toggle entre modos ─────────────────────────────────────────────────────

function setCatalogMode(mode) {
  const layoutTecnicas = document.getElementById("catalog-layout-tecnicas");
  const layoutSistemas = document.getElementById("catalog-layout-sistemas");
  document.querySelectorAll(".catalog-mode-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });
  if (mode === "sistemas") {
    layoutTecnicas?.classList.add("hidden");
    layoutSistemas?.classList.remove("hidden");
    loadSystemsMode();
  } else {
    layoutSistemas?.classList.add("hidden");
    layoutTecnicas?.classList.remove("hidden");
  }
}

document.getElementById("mode-btn-tecnicas")?.addEventListener("click", () => setCatalogMode("tecnicas"));
document.getElementById("mode-btn-sistemas")?.addEventListener("click", () => setCatalogMode("sistemas"));
