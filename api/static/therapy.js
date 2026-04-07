const state = {
  courseHistory: [],
  analysis: null,
  pairAnalysis: null,
  report: null,
};

const tabs = [...document.querySelectorAll(".tab")];
const tabPanels = [...document.querySelectorAll(".tab-panel")];
const steps = [...document.querySelectorAll(".step")];

const consultantSection = document.getElementById("consultant-section");
const grandparentsSection = document.getElementById("grandparents-section");
const parentsSection = document.getElementById("parents-section");
const siblingsSection = document.getElementById("siblings-section");
const partnersSection = document.getElementById("partners-section");
const childrenSection = document.getElementById("children-section");
const symptomList = document.getElementById("symptoms-list");
const historyList = document.getElementById("history-list");
const pairsList = document.getElementById("pairs-list");
const analysisPanel = document.getElementById("analysis-panel");
const pairsPanel = document.getElementById("pairs-panel");
const reportPanel = document.getElementById("report-panel");
const analysisOutput = document.getElementById("analysis-output");
const pairsOutput = document.getElementById("pairs-output");
const reportOutput = document.getElementById("report-output");
const courseOutput = document.getElementById("course-output");

function setActiveTab(tabName) {
  tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === tabName));
  tabPanels.forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${tabName}`));
}

function setStep(stepNumber) {
  steps.forEach((step) => step.classList.toggle("active", Number(step.dataset.step) <= stepNumber));
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => setActiveTab(tab.dataset.tab));
});

function attachRemoveButton(node) {
  node.querySelector(".remove-item")?.addEventListener("click", () => node.remove());
}

function addCollectionItem(container, templateId) {
  const template = document.getElementById(templateId);
  const fragment = template.content.cloneNode(true);
  const node = fragment.firstElementChild;
  attachRemoveButton(node);
  container.appendChild(node);
}

function createFieldMarkup(field) {
  return `
    <label>
      ${field.label}
      <input type="text" data-field="${field.key}" placeholder="${field.placeholder || ""}" />
    </label>
  `;
}

function createCard(title, fields, columns = "two") {
  return `
    <article class="collection-item">
      <h3>${title}</h3>
      <div class="grid ${columns}">
        ${fields.map(createFieldMarkup).join("")}
      </div>
    </article>
  `;
}

function appendCard(container, title, fields, columns = "two") {
  container.insertAdjacentHTML("beforeend", createCard(title, fields, columns));
}

function readCollection(container) {
  return [...container.children].map((item) => {
    const payload = {};
    item.querySelectorAll("[data-field]").forEach((field) => {
      payload[field.dataset.field] = field.value?.trim() || "";
    });
    return payload;
  }).filter((item) => Object.values(item).some(Boolean));
}

function readSingleCard(container) {
  return readCollection(container)[0] || {};
}

function getCasePayload() {
  return {
    consultant: readSingleCard(consultantSection),
    grandparents: {
      maternal_grandmother: readCollection(grandparentsSection)[0] || {},
      maternal_grandfather: readCollection(grandparentsSection)[1] || {},
      paternal_grandmother: readCollection(grandparentsSection)[2] || {},
      paternal_grandfather: readCollection(grandparentsSection)[3] || {},
    },
    parents: {
      mother: readCollection(parentsSection)[0] || {},
      father: readCollection(parentsSection)[1] || {},
    },
    siblings: readCollection(siblingsSection),
    current_partner: readCollection(partnersSection)[0] || {},
    significant_partners: readCollection(partnersSection).slice(1),
    children: readCollection(childrenSection),
    current_symptoms: readCollection(symptomList),
    history_events: readCollection(historyList),
    patient_name: readSingleCard(consultantSection).full_name || "",
    patient_birth_date: readSingleCard(consultantSection).birth_date || "",
  };
}

function getPairsPayload() {
  return readCollection(pairsList);
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${text}`);
  }
  return response.json();
}

function renderChipList(values = []) {
  if (!values.length) {
    return `<p class="status">Sin elementos detectados todavía.</p>`;
  }
  return `<div class="chip-list">${values.map((value) => `<span class="chip">${value}</span>`).join("")}</div>`;
}

function renderBulletList(values = []) {
  if (!values.length) {
    return `<p class="status">Sin elementos sugeridos en esta etapa.</p>`;
  }
  return `<ul class="bullet-list">${values.map((value) => `<li>${value}</li>`).join("")}</ul>`;
}

function renderAnalysis(analysis) {
  analysisOutput.innerHTML = `
    <article class="result-card">
      <h3>Lectura inicial</h3>
      <p>${analysis.reading || ""}</p>
      <p><strong>Masa conflictual:</strong> ${analysis.mass_conflict_hypothesis || "Aún no definida."}</p>
    </article>
    <article class="result-card">
      <h3>Síntomas prioritarios</h3>
      ${renderChipList(analysis.priority_symptoms || [])}
    </article>
    <article class="result-card">
      <h3>Sistemas probables</h3>
      ${renderChipList(analysis.probable_systems || [])}
    </article>
    <article class="result-card">
      <h3>Conflictos probables</h3>
      ${renderBulletList(analysis.probable_conflicts || [])}
    </article>
    <article class="result-card">
      <h3>Ejes familiares y transgeneracionales</h3>
      ${renderBulletList(analysis.family_axes || [])}
    </article>
    <article class="result-card">
      <h3>Preguntas guía</h3>
      ${renderBulletList(analysis.guiding_questions || [])}
    </article>
  `;
}

function renderPairCard(pair) {
  const visualImages = (pair.visual?.image_candidates || [])
    .map((url) => `<img src="${url}" alt="Referencia anatómica ${pair.pair_name}" />`)
    .join("");

  return `
    <article class="pair-card">
      <h3>${pair.pair_name}</h3>
      <div class="meta-list">
        <span class="chip">${pair.pair_type || "Sin tipo"}</span>
        <span class="chip">${pair.related_condition || "Sin condición"}</span>
      </div>
      <p><strong>Punto A:</strong> ${pair.visual?.point_a?.label || ""} · ${pair.visual?.point_a?.region_hint || ""}</p>
      <p><strong>Punto B:</strong> ${pair.visual?.point_b?.label || ""} · ${pair.visual?.point_b?.region_hint || ""}</p>
      <p><strong>Fuente:</strong> ${pair.source_file || "Sin fuente detectada"}</p>
      ${visualImages ? `<div class="pair-visual-grid">${visualImages}</div>` : `<p class="status">Sin referencia visual disponible.</p>`}
    </article>
  `;
}

function renderPairs(pairAnalysis) {
  const protocols = (pairAnalysis.suggested_protocols || []).map((protocol) => `
    <article class="protocol-card">
      <h3>${protocol.title}</h3>
      <p><strong>Ruta:</strong> ${protocol.route}</p>
      <p>${protocol.body}</p>
    </article>
  `).join("");

  pairsOutput.innerHTML = `
    <article class="result-card">
      <h3>Lectura integrada de pares</h3>
      <p>${pairAnalysis.integrated_reading || ""}</p>
    </article>
    <article class="result-card">
      <h3>Tipos dominantes</h3>
      ${renderChipList(pairAnalysis.dominant_pair_types || [])}
    </article>
    <article class="result-card">
      <h3>Condiciones relacionadas</h3>
      ${renderBulletList(pairAnalysis.related_conditions || [])}
    </article>
    ${(pairAnalysis.interpreted_pairs || []).map(renderPairCard).join("")}
    ${protocols || '<p class="status">Sin protocolos sugeridos todavía.</p>'}
  `;
}

function renderReport(report) {
  const tableRows = (report.integrative_chart || []).map((row) => `
    <tr>
      <td>${row.dimension}</td>
      <td>${row.value}</td>
      <td>${row.meaning}</td>
    </tr>
  `).join("");

  const protocol = report.primary_protocol;
  const pairVisualCards = (report.pair_visual_summary || []).map((item) => `
    <article class="pair-card">
      <h3>${item.pair_name}</h3>
      <p><strong>Interpretación:</strong> ${item.pair_type || "Sin tipo"} · ${item.related_condition || "Sin condición"}</p>
      <p><strong>Punto A:</strong> ${item.point_a_label} · ${item.point_a_region}</p>
      <p><strong>Punto B:</strong> ${item.point_b_label} · ${item.point_b_region}</p>
      ${(item.image_candidates || []).length
        ? `<div class="pair-visual-grid">${item.image_candidates.map((url) => `<img src="${url}" alt="${item.pair_name}" />`).join("")}</div>`
        : `<p class="status">Sin visuales disponibles.</p>`}
    </article>
  `).join("");

  reportOutput.innerHTML = `
    <article class="result-card">
      <h3>Resumen para terapeuta</h3>
      <p>${report.therapist_summary || ""}</p>
    </article>
    <article class="result-card">
      <h3>Próximos pasos</h3>
      ${renderBulletList(report.next_steps || [])}
    </article>
    <article class="result-card">
      <h3>Cuadro integrador</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Dimensión</th><th>Valor</th><th>Significado</th></tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>
    </article>
    ${protocol ? `
      <article class="protocol-card">
        <h3>Protocolo principal sugerido</h3>
        <p><strong>${protocol.title}</strong></p>
        <p>${protocol.body}</p>
      </article>
    ` : '<p class="status">Aún no hay protocolo principal sugerido.</p>'}
    <article class="result-card">
      <h3>Entrega para el paciente</h3>
      <p>${report.patient_delivery?.patient_summary || ""}</p>
      <p><strong>Foco terapéutico:</strong></p>
      ${renderChipList(report.patient_delivery?.therapeutic_focus || [])}
      <p><strong>Foco de pares:</strong></p>
      ${renderChipList(report.patient_delivery?.pair_focus || [])}
    </article>
    ${pairVisualCards}
  `;
}

function renderCourseAnswer(payload) {
  const visual = payload.visual?.content ? `
    <article class="qa-card">
      <h3>${payload.visual.title || "Apoyo visual"}</h3>
      <div>${payload.visual.content}</div>
    </article>
  ` : "";

  courseOutput.innerHTML = `
    <article class="qa-card">
      <h3>Respuesta</h3>
      <p>${payload.answer || ""}</p>
      <p class="status">Modo: ${payload.generation_mode || "n/a"}</p>
    </article>
    ${visual}
  `;
}

function setStatus(container, message, isError = false) {
  container.innerHTML = `<p class="status ${isError ? "error" : ""}">${message}</p>`;
}

document.getElementById("add-pair").addEventListener("click", () => addCollectionItem(pairsList, "pair-template"));

document.getElementById("analyze-case").addEventListener("click", async () => {
  const casePayload = getCasePayload();
  setStatus(analysisOutput, "Analizando caso...");
  analysisPanel.classList.remove("hidden");
  try {
    const response = await postJson("/therapy/analyze", { case_payload: casePayload });
    state.analysis = response.analysis;
    renderAnalysis(response.analysis);
    pairsPanel.classList.remove("hidden");
    reportPanel.classList.remove("hidden");
    setStep(2);
  } catch (error) {
    setStatus(analysisOutput, `Error al analizar el caso: ${error.message}`, true);
  }
});

document.getElementById("analyze-pairs").addEventListener("click", async () => {
  const casePayload = getCasePayload();
  const pairs = getPairsPayload();
  setStatus(pairsOutput, "Integrando pares...");
  try {
    const response = await postJson("/therapy/pairs", { case_payload: casePayload, pairs });
    state.pairAnalysis = response.pair_analysis;
    renderPairs(response.pair_analysis);
    setStep(3);
  } catch (error) {
    setStatus(pairsOutput, `Error al interpretar pares: ${error.message}`, true);
  }
});

document.getElementById("build-report").addEventListener("click", async () => {
  const casePayload = getCasePayload();
  const pairs = getPairsPayload();
  setStatus(reportOutput, "Construyendo reporte final...");
  try {
    const response = await postJson("/therapy/report", { case_payload: casePayload, pairs });
    state.report = response.report;
    renderReport(response.report);
  } catch (error) {
    setStatus(reportOutput, `Error al construir el reporte: ${error.message}`, true);
  }
});

document.getElementById("ask-course").addEventListener("click", async () => {
  const question = document.getElementById("course-question").value.trim();
  if (!question) {
    setStatus(courseOutput, "Escribe una pregunta primero.", true);
    return;
  }
  setStatus(courseOutput, "Consultando...");
  try {
    const response = await postJson("/ask", {
      question,
      history: state.courseHistory,
      want_visual: true,
      render_image: false,
      max_results: 2,
    });
    state.courseHistory.push({ role: "user", content: question });
    state.courseHistory.push({ role: "assistant", content: response.answer || "" });
    if (state.courseHistory.length > 6) {
      state.courseHistory.splice(0, state.courseHistory.length - 6);
    }
    renderCourseAnswer(response);
  } catch (error) {
    setStatus(courseOutput, `Error al consultar cursos: ${error.message}`, true);
  }
});

addCollectionItem(pairsList, "pair-template");

appendCard(consultantSection, "Consultante", [
  { key: "full_name", label: "Nombre completo del (a) consultante" },
  { key: "birth_date", label: "Fecha de nacimiento (día / mes / año)", placeholder: "DD/MM/AAAA" },
]);

[
  "Abuela materna",
  "Abuelo materno",
  "Abuela paterna",
  "Abuelo paterno",
].forEach((label) => {
  appendCard(grandparentsSection, label, [
    { key: "full_name", label: `Nombre completo de ${label.toLowerCase()}` },
    { key: "birth_date", label: "Fecha de nacimiento (día / mes / año)", placeholder: "DD/MM/AAAA" },
    { key: "death_date", label: "Fecha de muerte (día / mes / año)", placeholder: "DD/MM/AAAA" },
  ], "three");
});

["Madre", "Padre"].forEach((label) => {
  appendCard(parentsSection, label, [
    { key: "full_name", label: `Nombre completo de ${label.toLowerCase()}` },
    { key: "birth_date", label: "Fecha de nacimiento (día / mes / año)", placeholder: "DD/MM/AAAA" },
    { key: "death_date", label: "Fecha de muerte (día / mes / año)", placeholder: "DD/MM/AAAA" },
  ], "three");
});

for (let index = 1; index <= 5; index += 1) {
  appendCard(siblingsSection, `Herman@ ${index}`, [
    { key: "full_name", label: `Nombre completo herman@ ${index}` },
    { key: "birth_date", label: "Fecha de nacimiento (día / mes / año)", placeholder: "DD/MM/AAAA" },
  ]);
}

appendCard(partnersSection, "Pareja actual", [
  { key: "full_name", label: "Nombre completo pareja actual" },
  { key: "birth_date", label: "Fecha de nacimiento (día / mes / año)", placeholder: "DD/MM/AAAA" },
  { key: "relationship_duration", label: "Tiempo de relación" },
], "three");

for (let index = 1; index <= 3; index += 1) {
  appendCard(partnersSection, `Pareja significativa ${index}`, [
    { key: "full_name", label: "Nombre pareja significativa" },
    { key: "birth_date", label: "Fecha de nacimiento (día / mes / año)", placeholder: "DD/MM/AAAA" },
    { key: "relationship_duration", label: "Tiempo de relación" },
  ], "three");
}

for (let index = 1; index <= 5; index += 1) {
  appendCard(childrenSection, `Hij@ ${index}`, [
    { key: "full_name", label: "Nombre completo" },
    { key: "birth_date", label: "Fecha de nacimiento (día / mes / año)", placeholder: "DD/MM/AAAA" },
    { key: "death_date", label: "Fecha de muerte (día / mes / año)", placeholder: "DD/MM/AAAA" },
    { key: "other_parent_name", label: "Nombre completo progenitor (a)" },
    { key: "relationship_duration", label: "Tiempo de duración en la relación" },
  ], "three");
}

for (let index = 1; index <= 4; index += 1) {
  appendCard(symptomList, `Síntoma actual ${index}`, [
    { key: "symptom_name", label: "Síntoma" },
    { key: "onset_age_or_date", label: "Edad aproximada de aparición o diagnóstico" },
    { key: "symptom_characteristics", label: "Características del síntoma" },
    { key: "frequency", label: "Frecuencia de síntoma" },
  ], "two");
}

for (let index = 1; index <= 3; index += 1) {
  appendCard(historyList, `Antecedente / recurrente ${index}`, [
    { key: "event_name", label: "Síntoma" },
    { key: "onset_age_or_date", label: "Edad aproximada de aparición o diagnóstico" },
    { key: "event_characteristics", label: "Características del síntoma" },
    { key: "frequency", label: "Frecuencia de síntoma" },
  ], "two");
}
