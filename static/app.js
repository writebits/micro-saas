const API = "/api/v1/reports";

let selectedFile = null;
let currentReportId = null;

const el = (id) => document.getElementById(id);

const fileInput = el("fileInput");
const dropzone = el("dropzone");
const fileName = el("fileName");
const uploadBtn = el("uploadBtn");
const sampleBtn = el("sampleBtn");

function setStatus(node, message, type) {
  node.className = "status" + (type ? " " + type : "");
  node.textContent = message || "";
}

function fmtInt(v) {
  return Math.round(v).toLocaleString("pt-BR");
}
function fmtBRL(v) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
function fmtDec(v, d = 2) {
  return v.toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
}

function selectFile(file) {
  selectedFile = file;
  fileName.textContent = file ? file.name : "Nenhum arquivo selecionado";
  uploadBtn.disabled = !file;
}

dropzone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => {
  if (e.target.files.length) selectFile(e.target.files[0]);
});
["dragover", "dragenter"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length) selectFile(e.dataTransfer.files[0]);
});

sampleBtn.addEventListener("click", async () => {
  setStatus(el("uploadStatus"), "Carregando dados de exemplo...", "loading");
  try {
    const res = await fetch("/static/sample/meta_ads_sample.csv");
    const blob = await res.blob();
    selectFile(new File([blob], "meta_ads_sample.csv", { type: "text/csv" }));
    setStatus(el("uploadStatus"), "Dados de exemplo prontos. Clique em 'Processar relatório'.", "success");
  } catch (err) {
    setStatus(el("uploadStatus"), "Não foi possível carregar o exemplo.", "error");
  }
});

uploadBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  setStatus(el("uploadStatus"), "Processando CSV com Pandas...", "loading");
  uploadBtn.disabled = true;

  const form = new FormData();
  form.append("file", selectedFile);
  form.append("agency_name", el("agency").value || "Sua Agência");

  try {
    const res = await fetch(`${API}/upload`, { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Erro ao processar.");

    currentReportId = data.report_id;
    renderResults(data);
    setStatus(el("uploadStatus"), `Processado com sucesso! ${data.rows_processed} linhas analisadas.`, "success");
    el("results").classList.remove("hidden");
    el("results").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    setStatus(el("uploadStatus"), err.message, "error");
  } finally {
    uploadBtn.disabled = false;
  }
});

function renderResults(data) {
  const sourceLabels = { meta_ads: "Meta Ads", google_ads: "Google Ads", unknown: "Origem desconhecida" };
  el("sourceBadge").textContent = sourceLabels[data.source] || data.source;

  const m = data.metrics;
  const kpis = [
    { label: "Investimento", value: fmtBRL(m.spend) },
    { label: "Impressões", value: fmtInt(m.impressions) },
    { label: "Cliques", value: fmtInt(m.clicks) },
    { label: "Conversões", value: fmtInt(m.conversions) },
    { label: "CTR", value: fmtDec(m.ctr) + "%" },
    { label: "CPC", value: fmtBRL(m.cpc) },
    { label: "CPM", value: fmtBRL(m.cpm) },
    { label: "ROAS", value: fmtDec(m.roas) + "x" },
  ];
  el("kpis").innerHTML = kpis
    .map((k) => `<div class="kpi"><div class="label">${k.label}</div><div class="value">${k.value}</div></div>`)
    .join("");

  const rows = data.campaigns
    .map(
      (c) => `<tr>
        <td>${c.campaign_name}</td>
        <td>${fmtInt(c.impressions)}</td>
        <td>${fmtInt(c.clicks)}</td>
        <td>${fmtBRL(c.spend)}</td>
        <td>${fmtDec(c.ctr)}%</td>
        <td>${fmtBRL(c.cpc)}</td>
        <td>${fmtBRL(c.cpm)}</td>
        <td>${fmtInt(c.conversions)}</td>
        <td>${fmtDec(c.roas)}x</td>
      </tr>`
    )
    .join("");
  el("campaignTable").querySelector("tbody").innerHTML = rows;

  el("insights").classList.add("hidden");
}

el("insightsBtn").addEventListener("click", async () => {
  if (!currentReportId) return;
  setStatus(el("insightsStatus"), "Gerando insights com IA...", "loading");
  el("insightsBtn").disabled = true;

  try {
    const res = await fetch(`${API}/generate-insights`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ report_id: currentReportId, agency_name: el("agency").value }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Erro ao gerar insights.");

    const ins = data.insights;
    el("insResumo").textContent = ins.resumo_executivo;
    el("insDestaques").textContent = ins.destaques_positivos_e_gargalos;
    el("insAcoes").innerHTML = ins.acoes_de_otimizacao.map((a) => `<li>${a}</li>`).join("");
    el("insights").classList.remove("hidden");

    const tag = ins.generated_by === "openai" ? "IA (OpenAI)" : "análise automática";
    setStatus(el("insightsStatus"), `Insights gerados por ${tag}.`, "success");
  } catch (err) {
    setStatus(el("insightsStatus"), err.message, "error");
  } finally {
    el("insightsBtn").disabled = false;
  }
});

el("pdfBtn").addEventListener("click", () => {
  if (!currentReportId) return;
  window.open(`${API}/${currentReportId}/pdf`, "_blank");
});
