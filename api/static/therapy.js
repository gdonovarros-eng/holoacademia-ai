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

function openProtocolDetail(protocolId) {
  const all = catalogData?.categories?.flatMap((c) => c.protocolos) ?? [];
  const p = all.find((x) => x.id === protocolId);
  if (!p) return;

  const catMeta = catalogData?.categories?.find((c) =>
    c.protocolos.some((x) => x.id === protocolId)
  );

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
    ? `<ul class="detail-list">${p.cuando_usarlo.map((u) => `<li>${escapeHtml(u)}</li>`).join("")}</ul>`
    : "";

  const prereqHtml = (p.prerequisitos || []).length
    ? `<ul class="detail-list">${p.prerequisitos.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>`
    : "";

  const obsHtml = (p.observaciones || []).length
    ? `<ul class="detail-list">${p.observaciones.map((o) => `<li>${escapeHtml(o)}</li>`).join("")}</ul>`
    : "";

  const content = document.getElementById("catalog-detail-content");
  if (content) {
    content.innerHTML = `
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
loadCatalog();
if (protocolOutput) setStatus(protocolOutput, "Aquí aparecerá la guía del protocolo consultado.");

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
