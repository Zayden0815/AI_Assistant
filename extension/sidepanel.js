const API_BASE = "http://127.0.0.1:8000";
const ANALYZE_URL = `${API_BASE}/analyze`;
const GENERATE_TC_URL = `${API_BASE}/generate-testcases`;
const GENERATE_TRACE_URL = `${API_BASE}/generate-traceability`;
const GENERATE_REPORT_URL = `${API_BASE}/generate-report`;
const EXPORT_URL = `${API_BASE}/export-document`;

const SETTINGS_KEY = "iso26262_sidebar_settings_v2";
const HISTORY_KEY = "iso26262_analysis_history_v2";

let currentTestCases = [];
let currentISOReference = [];
let currentTraceability = null;
let currentAnalysis = {};

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();

  bindButton("analyzeBtn", analyzeRequirement);
  bindButton("saveBtn", saveResult);
  bindButton("exportBtn", exportDocument);
  bindButton("generateTcBtn", generateTestCasesOnly);
  bindButton("generateTraceBtn", generateTraceabilityOnly);
  bindButton("generateReportBtn", generateReportOnly);
  bindButton("resetSettingsBtn", resetSettings);

  bindSettingAutoSave();

  renderHistory();
  setStatus("Ready. Backend: http://127.0.0.1:8000");
});

function bindButton(id, handler) {
  const el = document.getElementById(id);
  if (el) el.addEventListener("click", handler);
}

function bindSettingAutoSave() {
  const ids = [
    "requirementInput", "isoPart", "topK", "outputType", "autoTcNumber",
    "tcPrefix", "developmentMethod", "documentTemplate", "exportFormat",
    "asilPolicy"
  ];

  ids.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("change", saveSettings);
    el.addEventListener("input", saveSettings);
  });
}

function getSettings() {
  return {
    requirement_text: getValue("requirementInput"),
    iso_part: getValue("isoPart") || "all",
    top_k: Number(getValue("topK") || 8),
    output_type: getValue("outputType") || "analysis",
    auto_tc_number: document.getElementById("autoTcNumber")?.checked ?? true,
    tc_prefix: getValue("tcPrefix") || "ATDD",
    development_method: getValue("developmentMethod") || "ATDD",
    document_template: getValue("documentTemplate") || "safety_report",
    export_format: getValue("exportFormat") || "json",
    asil_policy: getValue("asilPolicy") || "candidate"
  };
}

function saveSettings() {
  const settings = getSettings();
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

function loadSettings() {
  const defaults = {
    requirement_text: "",
    iso_part: "all",
    top_k: 8,
    output_type: "analysis",
    auto_tc_number: true,
    tc_prefix: "ATDD",
    development_method: "ATDD",
    document_template: "safety_report",
    export_format: "json",
    asil_policy: "candidate"
  };

  let saved = {};
  try {
    saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}");
  } catch {
    saved = {};
  }

  const settings = {...defaults, ...saved};

  setValue("requirementInput", settings.requirement_text || "");
  setValue("isoPart", settings.iso_part);
  setValue("topK", settings.top_k);
  setValue("outputType", settings.output_type);
  setValue("tcPrefix", settings.tc_prefix);
  setValue("developmentMethod", settings.development_method);
  setValue("documentTemplate", settings.document_template);
  setValue("exportFormat", settings.export_format);
  setValue("asilPolicy", settings.asil_policy);

  const autoTc = document.getElementById("autoTcNumber");
  if (autoTc) autoTc.checked = settings.auto_tc_number ?? true;
}

function resetSettings() {
  localStorage.removeItem(SETTINGS_KEY);
  location.reload();
}

async function analyzeRequirement() {
  const payload = buildAnalyzePayload();

  if (!payload.requirement_text.trim()) {
    alert("Requirement를 입력하세요.");
    return;
  }

  saveSettings();
  clearResults();
  setLoading(true);
  setStatus("Analyzing requirement...");

  try {
    const data = await postJson(ANALYZE_URL, payload);
    renderResults(data);
    setStatus("Analyze completed.");
  } catch (error) {
    console.error(error);
    setStatus("Analyze failed:\n" + error.message);
    alert("분석 실패. FastAPI 서버와 /analyze 응답을 확인하세요.");
  } finally {
    setLoading(false);
  }
}

function buildAnalyzePayload() {
  const s = getSettings();
  return {
    requirement_text: s.requirement_text,
    iso_part: s.iso_part,
    top_k: s.top_k,
    output_type: s.output_type,
    auto_tc_number: s.auto_tc_number,
    tc_prefix: s.tc_prefix,
    development_method: s.development_method,
    document_template: s.document_template,
    export_format: s.export_format,
    asil_policy: s.asil_policy
  };
}

async function generateTestCasesOnly() {
  const s = getSettings();

  if (!s.requirement_text.trim()) {
    alert("Requirement를 입력하세요.");
    return;
  }

  setLoading(true);
  setStatus("Generating test cases...");

  try {
    const data = await postJson(GENERATE_TC_URL, {
      requirement_text: s.requirement_text,
      tc_prefix: s.tc_prefix,
      auto_tc_number: s.auto_tc_number,
      development_method: s.development_method,
      document_template: s.document_template,
      output_type: "testcase",
      asil_policy: s.asil_policy
    });

    currentTestCases = Array.isArray(data.test_cases) ? data.test_cases : [];
    renderTestCases(currentTestCases);
    setStatus(`Generated ${currentTestCases.length} test cases.`);
  } catch (error) {
    console.error(error);
    setStatus("Test case generation failed:\n" + error.message);
    alert("Test Case 생성 실패.");
  } finally {
    setLoading(false);
  }
}

async function generateTraceabilityOnly() {
  const s = getSettings();

  if (!s.requirement_text.trim()) {
    alert("Requirement를 입력하세요.");
    return;
  }

  setLoading(true);
  setStatus("Generating traceability...");

  try {
    const data = await postJson(GENERATE_TRACE_URL, {
      requirement_text: s.requirement_text,
      test_cases: currentTestCases,
      development_method: s.development_method,
      document_template: "traceability_matrix"
    });

    currentTraceability = data.traceability || null;
    renderTraceability(currentTraceability);
    setStatus("Traceability generated.");
  } catch (error) {
    console.error(error);
    setStatus("Traceability failed:\n" + error.message);
    alert("Traceability 생성 실패.");
  } finally {
    setLoading(false);
  }
}

async function generateReportOnly() {
  const s = getSettings();

  if (!s.requirement_text.trim()) {
    alert("Requirement를 입력하세요.");
    return;
  }

  setLoading(true);
  setStatus("Generating report data...");

  try {
    const data = await postJson(GENERATE_REPORT_URL, {
      requirement_text: s.requirement_text,
      iso_reference: currentISOReference,
      hazard: getText("hazardResult"),
      asil: currentAnalysis.asil || currentAnalysis.asil_candidate || "",
      asil_candidate: currentAnalysis.asil_candidate || currentAnalysis.asil || "",
      asil_basis: currentAnalysis.asil_basis || currentAnalysis.hara_basis || "",
      safety_goal: currentAnalysis.safety_goal || "",
      fsr: currentAnalysis.fsr || "",
      tsr: currentAnalysis.tsr || "",
      test_cases: currentTestCases,
      traceability: currentTraceability,
      development_method: s.development_method,
      document_template: s.document_template,
      output_type: "report"
    });

    setStatus(data.message || "Report data generated. Use Export Document.");
    alert(data.message || "Report data generated. Export Document 버튼으로 저장하세요.");
  } catch (error) {
    console.error(error);
    setStatus("Report generation failed:\n" + error.message);
    alert("Report 생성 실패.");
  } finally {
    setLoading(false);
  }
}

async function exportDocument() {
  const s = getSettings();
  const payload = collectCurrentData();

  payload.export_format = s.export_format;
  payload.document_template = s.document_template;
  payload.development_method = s.development_method;
  payload.test_cases = currentTestCases;

  setLoading(true);
  setStatus("Exporting document...");

  try {
    const response = await fetch(EXPORT_URL, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Export failed: ${response.status}\n${text}`);
    }

    const blob = await response.blob();
    let fileName = getFileNameFromHeader(response.headers.get("Content-Disposition"));

    if (!fileName) {
      let ext = "pdf";
      if (s.export_format === "excel") ext = "xlsx";
      if (s.export_format === "json") ext = "json";
      fileName = `ISO26262_${s.development_method}_ImportReady.${ext}`;
    }

    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = blobUrl;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();

    setTimeout(() => {
      URL.revokeObjectURL(blobUrl);
      a.remove();
    }, 1500);

    setStatus(`Export completed:\n${fileName}`);
  } catch (error) {
    console.error(error);
    setStatus("Export failed:\n" + error.message);
    alert("문서 다운로드 실패. 백엔드 /export-document를 확인하세요.");
  } finally {
    setLoading(false);
  }
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  const text = await response.text();

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}\n${text}`);
  }

  try {
    return JSON.parse(text);
  } catch {
    throw new Error("Backend returned non-JSON response:\n" + text.slice(0, 500));
  }
}

function renderResults(data) {
  currentTestCases = Array.isArray(data.test_cases) ? data.test_cases : [];
  currentISOReference = Array.isArray(data.iso_reference) ? data.iso_reference : [];
  currentTraceability = data.traceability || null;
  currentAnalysis = data || {};

  const isoText = currentISOReference.length
    ? currentISOReference.map(item =>
      `Part: ${item.part || "-"}\n` +
      `Clause: ${item.clause || "-"}\n` +
      `Page: ${item.page || "-"}\n` +
      `Score: ${item.score ?? "-"}\n` +
      `Summary: ${item.summary || "-"}`
    ).join("\n\n")
    : "-";

  setText("methodResult", `${data.development_method || getValue("developmentMethod") || "-"}\n${data.methodology_notes || ""}`);
  setText("isoResult", isoText);
  setText("relatedPartsResult", Array.isArray(data.related_iso_parts) ? data.related_iso_parts.join("\n") : "-");
  setText("referencedPagesResult", Array.isArray(data.referenced_pages) ? data.referenced_pages.join(", ") : "-");

  const asilCandidate = data.asil_candidate || data.asil || "-";
  const asilBasis = data.asil_basis || data.hara_basis || data.required_hara_inputs || "";

  setText(
    "hazardResult",
    `${data.hazard || "-"}\n\nASIL Candidate: ${asilCandidate}\n` +
    `${asilBasis ? "\nASIL / HARA Basis:\n" + asilBasis : ""}`
  );

  setText(
    "safetyResult",
    `Safety Goal:\n${data.safety_goal || "-"}\n\n` +
    `FSR:\n${data.fsr || "-"}\n\n` +
    `TSR:\n${data.tsr || "-"}`
  );

  renderTestCases(currentTestCases);
  renderTraceability(currentTraceability);
}

function renderTestCases(testCases) {
  if (!Array.isArray(testCases) || testCases.length === 0) {
    setText("testCaseResult", "-");
    return;
  }

  const method = getValue("developmentMethod") || "ATDD";

  const txt = testCases.map(tc =>
    `${tc.tc_id || "-"} - ${tc.title || "-"}\n` +
    `Given: ${tc.given || tc.arrange || tc.acceptance_criteria || "-"}\n` +
    `When: ${tc.when || tc.act || tc.trigger || "-"}\n` +
    `Then: ${tc.then || tc.assert || tc.expected_result || "-"}\n` +
    `Expected Action: ${tc.expected_action || tc.expected || "-"}\n` +
    `Verification Method: ${tc.verification_method || tc.method || "-"}\n` +
    `Methodology: ${tc.methodology || method}`
  ).join("\n\n");

  setText("testCaseResult", txt);
}

function renderTraceability(trace) {
  if (!trace) {
    setText("traceResult", "-");
    return;
  }

  const chain = Array.isArray(trace.chain) ? trace.chain.join(" → ") : "-";

  setText(
    "traceResult",
    `Development Method: ${trace.development_method || getValue("developmentMethod") || "-"}\n` +
    `Requirement: ${trace.requirement || "-"}\n` +
    `Hazard: ${trace.hazard || "-"}\n` +
    `Safety Goal: ${trace.safety_goal || "-"}\n` +
    `FSR: ${trace.fsr || "-"}\n` +
    `TSR: ${trace.tsr || "-"}\n` +
    `Test Cases: ${Array.isArray(trace.test_cases) ? trace.test_cases.join(", ") : trace.test_cases || "-"}\n\n` +
    `Trace Chain:\n${chain}`
  );
}

function saveResult() {
  const savedData = collectCurrentData();
  const history = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  history.push(savedData);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  alert("분석 결과가 저장되었습니다.");
  renderHistory();
}

function renderHistory() {
  const historyBox = document.getElementById("historyResult");
  if (!historyBox) return;

  const history = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  historyBox.innerHTML = "";

  if (history.length === 0) {
    historyBox.innerText = "저장된 결과가 없습니다.";
    return;
  }

  history.slice().reverse().forEach((item, index) => {
    const div = document.createElement("div");
    div.className = "history-item";
    const title = item.requirement ? item.requirement.substring(0, 55) : "No Requirement";
    div.innerText = `${index + 1}. ${title}...`;
    div.addEventListener("click", () => loadHistoryItem(item));
    historyBox.appendChild(div);
  });
}

function loadHistoryItem(item) {
  setValue("requirementInput", item.requirement || "");
  setText("methodResult", item.development_method || "");
  setText("relatedPartsResult", item.related_parts || "");
  setText("referencedPagesResult", item.referenced_pages || "");
  setText("isoResult", item.iso || "");
  setText("hazardResult", item.hazard || "");
  setText("safetyResult", item.safety || "");
  setText("testCaseResult", item.testcase || "");
  setText("traceResult", item.trace || "");

  currentTestCases = item.test_cases || [];
  currentISOReference = item.iso_reference || [];
  currentTraceability = item.traceability || null;

  if (item.settings) {
    setValue("isoPart", item.settings.iso_part || "all");
    setValue("topK", item.settings.top_k || 8);
    setValue("outputType", item.settings.output_type || "analysis");
    setValue("tcPrefix", item.settings.tc_prefix || "ATDD");
    setValue("exportFormat", item.settings.export_format || "json");
    setValue("documentTemplate", item.settings.document_template || "safety_report");
    setValue("developmentMethod", item.settings.development_method || "ATDD");
    setValue("asilPolicy", item.settings.asil_policy || "candidate");
    const autoTc = document.getElementById("autoTcNumber");
    if (autoTc) autoTc.checked = item.settings.auto_tc_number ?? true;
    saveSettings();
  }
}

function collectCurrentData() {
  const s = getSettings();

  return {
    requirement: s.requirement_text,
    development_method: s.development_method,
    export_format: s.export_format,
    document_template: s.document_template,

    related_parts: getText("relatedPartsResult"),
    referenced_pages: getText("referencedPagesResult"),
    iso: getText("isoResult"),
    hazard: getText("hazardResult"),
    safety: getText("safetyResult"),
    testcase: getText("testCaseResult"),
    trace: getText("traceResult"),

    asil: currentAnalysis.asil || "",
    asil_candidate: currentAnalysis.asil_candidate || currentAnalysis.asil || "",
    asil_basis: currentAnalysis.asil_basis || currentAnalysis.hara_basis || "",
    required_hara_inputs: currentAnalysis.required_hara_inputs || "",

    test_cases: currentTestCases,
    iso_reference: currentISOReference,
    traceability: currentTraceability,

    settings: {
      iso_part: s.iso_part,
      top_k: s.top_k,
      output_type: s.output_type,
      auto_tc_number: s.auto_tc_number,
      tc_prefix: s.tc_prefix,
      export_format: s.export_format,
      document_template: s.document_template,
      development_method: s.development_method,
      asil_policy: s.asil_policy
    },
    created_at: new Date().toISOString()
  };
}

function clearResults() {
  setText("methodResult", "");
  setText("relatedPartsResult", "");
  setText("referencedPagesResult", "");
  setText("isoResult", "");
  setText("hazardResult", "");
  setText("safetyResult", "");
  setText("testCaseResult", "");
  setText("traceResult", "");

  currentTestCases = [];
  currentISOReference = [];
  currentTraceability = null;
  currentAnalysis = {};
}

function getFileNameFromHeader(disposition) {
  if (!disposition) return "";
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) return decodeURIComponent(utf8Match[1]);
  const match = disposition.match(/filename="?([^"]+)"?/i);
  if (match) return match[1];
  return "";
}

function setLoading(isLoading) {
  const loading = document.getElementById("loading");
  if (!loading) return;
  if (isLoading) loading.classList.remove("hidden");
  else loading.classList.add("hidden");
}

function setStatus(message) {
  const el = document.getElementById("statusBox");
  if (el) el.innerText = message || "";
}

function getValue(id) {
  const el = document.getElementById(id);
  return el ? el.value : "";
}

function setValue(id, value) {
  const el = document.getElementById(id);
  if (el) el.value = value;
}

function getText(id) {
  const el = document.getElementById(id);
  return el ? el.innerText : "";
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.innerText = value;
}