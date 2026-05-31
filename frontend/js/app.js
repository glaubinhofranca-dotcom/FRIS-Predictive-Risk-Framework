/**
 * FRIS v3 — Dashboard JavaScript
 * Handles file upload, SSE pipeline progress, and Chart.js rendering.
 */

"use strict";

// ── Palette (matches CSS variables) ─────────────────────────────────────────
const C = {
  blue:   "#378ADD",
  red:    "#E24B4A",
  green:  "#1D9E75",
  amber:  "#EF9F27",
  gray:   "#888780",
  muted:  "#7b7f96",
  border: "#2a2e3f",
  card:   "#1a1d27",
};

// ── State ────────────────────────────────────────────────────────────────────
let sessionId = null;
let charts = {};

// ── Helpers ──────────────────────────────────────────────────────────────────
function $(id) { return document.getElementById(id); }

function show(id) { $(id).classList.remove("hidden"); }
function hide(id) { $(id).classList.add("hidden"); }

function setStatus(text, cls) {
  const el = $("header-status");
  el.textContent = text;
  el.className = "status-badge " + cls;
}

/** Animate a numeric value from 0 to target over ~1500ms. */
function animateCounter(el, target, format) {
  const start = performance.now();
  const duration = 1500;
  const from = 0;
  function tick(now) {
    const t = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    const cur = from + (target - from) * ease;
    el.textContent = format(cur);
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

/** Return bar color vs. overall rate (±3% threshold). */
function segColor(rate, overall) {
  if (rate > overall + 0.03) return C.red;
  if (rate < overall - 0.03) return C.green;
  return C.amber;
}

/** Destroy existing chart on canvas and create a new one. */
function makeChart(id, config) {
  if (charts[id]) { charts[id].destroy(); }
  const ctx = $(id).getContext("2d");
  charts[id] = new Chart(ctx, config);
}

// ── Upload ───────────────────────────────────────────────────────────────────
const zone = $("upload-zone");
const fileInput = $("file-input");
const errorBox = $("upload-error");

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.classList.remove("hidden");
}
function clearError() { errorBox.classList.add("hidden"); }

zone.addEventListener("click", () => fileInput.click());
zone.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") fileInput.click(); });

zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
zone.addEventListener("drop", e => {
  e.preventDefault();
  zone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

async function handleFile(file) {
  clearError();
  const ext = file.name.split(".").pop().toLowerCase();
  if (!["xlsx", "xls", "csv"].includes(ext)) {
    showError(`Unsupported file type ".${ext}". Please upload .xlsx, .xls, or .csv.`);
    return;
  }

  setStatus("Uploading…", "status-running");

  const form = new FormData();
  form.append("file", file);

  let resp;
  try {
    resp = await fetch("/api/upload", { method: "POST", body: form });
  } catch {
    showError("Network error — could not reach the server.");
    setStatus("Error", "status-error");
    return;
  }

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    showError(body.detail || "Upload failed.");
    setStatus("Error", "status-error");
    return;
  }

  const { session_id } = await resp.json();
  sessionId = session_id;

  hide("upload-section");
  show("progress-section");
  setStatus("Running pipeline…", "status-running");

  startPipeline(session_id);
}

// ── SSE Pipeline ─────────────────────────────────────────────────────────────
function startPipeline(sid) {
  const es = new EventSource(`/api/run?session_id=${sid}`);

  es.addEventListener("progress", e => {
    const d = JSON.parse(e.data);
    updateProgress(d);
  });

  es.addEventListener("complete", e => {
    es.close();
    setStatus("Complete", "status-done");
    loadDashboard(sid);
  });

  es.addEventListener("error", e => {
    if (e.data) {
      const d = JSON.parse(e.data);
      showError(`Pipeline error in step "${d.step}": ${d.message}`);
    }
    es.close();
    setStatus("Error", "status-error");
    show("upload-section");
    hide("progress-section");
  });

  // Browser-level SSE connection error
  es.onerror = () => {
    if (es.readyState === EventSource.CLOSED) return;
    showError("Connection lost. Please try again.");
    es.close();
    setStatus("Error", "status-error");
  };
}

function updateProgress({ step, status, pct, message }) {
  const fill = $("progress-fill");
  const label = $("progress-label");
  const pctEl = $("progress-pct");

  fill.style.width = pct + "%";
  label.textContent = message || "";
  pctEl.textContent = pct + "%";

  const stepEl = $("step-" + step);
  if (stepEl) {
    // Mark previous steps as done when a new one starts
    const stepOrder = ["etl", "eda", "segmentation", "model"];
    const idx = stepOrder.indexOf(step);
    stepOrder.forEach((s, i) => {
      const el = $("step-" + s);
      if (!el) return;
      if (i < idx) { el.className = "step-item done"; }
      else if (i === idx) {
        el.className = "step-item " + (status === "done" ? "done" : "running");
      }
    });
  }
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
async function loadDashboard(sid) {
  let resp;
  try {
    resp = await fetch(`/api/results?session_id=${sid}`);
  } catch {
    showError("Could not load results.");
    return;
  }
  if (!resp.ok) { showError("Results not available yet."); return; }
  const data = await resp.json();

  hide("progress-section");
  show("dashboard-section");

  renderKPIs(data);
  renderModelCharts(data.model);
  renderSubgroupAUC(data.model);
  renderEDA(data.eda);
  renderSegmentation(data.segmentation);
  renderImages(sid);
}

// ── KPI Cards ────────────────────────────────────────────────────────────────
function renderKPIs(data) {
  const { etl, model, segmentation } = data;
  const overall = segmentation.overall_default_rate;

  animateCounter($("val-borrowers"), etl.valid_population, v => Math.round(v).toLocaleString());
  $("sub-borrowers").textContent = `${etl.defaults.toLocaleString()} defaults`;

  animateCounter($("val-default-rate"), overall * 100, v => v.toFixed(1) + "%");
  const byLevel = Object.entries(etl.default_rate_by_level || {})
    .map(([k, v]) => `${k}: ${(v * 100).toFixed(1)}%`).join("  ·  ");
  $("sub-default-rate").textContent = byLevel;

  animateCounter($("val-auc"), model.best_auc * 100, v => (v / 100).toFixed(3));
  $("sub-auc").textContent = model.best_model;

  const diff = segmentation.idr_differential;
  animateCounter($("val-idr"), diff * 100, v => "−" + v.toFixed(1) + "pp");
  $("sub-idr").textContent =
    `IDR ${(segmentation.idr_rate * 100).toFixed(1)}% vs non-IDR ${(segmentation.non_idr_rate * 100).toFixed(1)}%`;

  // Add pulse only if differential is significant
  if (diff < 0.05) $("kpi-idr").classList.remove("pulse-red");
}

// ── Model Charts ─────────────────────────────────────────────────────────────
function renderModelCharts(model) {
  const names = Object.keys(model.model_results);
  const means = names.map(n => model.model_results[n].roc_auc_mean);
  const stds  = names.map(n => model.model_results[n].roc_auc_std);
  const colors = names.map(n => n === model.best_model ? C.blue : C.gray);

  makeChart("chart-auc", {
    type: "bar",
    data: {
      labels: names,
      datasets: [{
        data: means,
        backgroundColor: colors,
        borderColor: colors,
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const n = names[ctx.dataIndex];
              const s = stds[ctx.dataIndex];
              return `AUC: ${ctx.raw.toFixed(3)} ± ${s.toFixed(3)}`;
            },
          },
        },
      },
      scales: {
        y: {
          min: 0.5, max: 0.85,
          ticks: { color: C.muted, callback: v => v.toFixed(2) },
          grid: { color: C.border },
        },
        x: { ticks: { color: C.muted }, grid: { display: false } },
      },
    },
  });

  const featNames = Object.keys(model.feature_importance).slice(0, 10);
  const featVals  = featNames.map(k => model.feature_importance[k]);
  const academic  = new Set(["gpa", "graduated", "credits_earned", "withdrawn", "level"]);
  const loanFin   = new Set(["num_loans", "original_loan_amount", "current_balance"]);
  const featColors = featNames.map(f =>
    academic.has(f) ? C.blue : loanFin.has(f) ? C.green : C.gray
  );

  makeChart("chart-features", {
    type: "bar",
    data: {
      labels: featNames.map(f => f.replace(/_/g, " ")),
      datasets: [{ data: featVals, backgroundColor: featColors, borderRadius: 4 }],
    },
    options: {
      indexAxis: "y",
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: C.muted, callback: v => (v * 100).toFixed(0) + "%" }, grid: { color: C.border } },
        y: { ticks: { color: C.muted, font: { size: 11 } }, grid: { display: false } },
      },
    },
  });
}

// ── Subgroup AUC ─────────────────────────────────────────────────────────────
function renderSubgroupAUC(model) {
  const grid = $("subgroup-grid");
  grid.innerHTML = "";
  for (const [code, info] of Object.entries(model.subgroup_auc || {})) {
    const badge = document.createElement("div");
    badge.className = "subgroup-badge";
    badge.innerHTML = `
      <div class="sg-code">${code}</div>
      <div class="sg-auc">${info.auc.toFixed(3)}</div>
      <div class="sg-sub">n=${info.n.toLocaleString()} · ${info.defaults} defaults · ${(info.default_rate * 100).toFixed(1)}% rate</div>
    `;
    grid.appendChild(badge);
  }
}

// ── EDA ──────────────────────────────────────────────────────────────────────
function renderEDA(eda) {
  // Correlation bar chart
  const corr = eda.correlations_with_default;
  const corrLabels = Object.keys(corr).sort((a, b) => Math.abs(corr[b]) - Math.abs(corr[a]));
  const corrVals = corrLabels.map(k => corr[k]);
  const corrColors = corrVals.map(v => v < 0 ? C.green : C.red);

  makeChart("chart-corr", {
    type: "bar",
    data: {
      labels: corrLabels.map(l => l.replace(/_/g, " ")),
      datasets: [{ data: corrVals, backgroundColor: corrColors, borderRadius: 4 }],
    },
    options: {
      indexAxis: "y",
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: C.muted },
          grid: { color: C.border },
          title: { display: true, text: "Pearson r", color: C.muted },
        },
        y: { ticks: { color: C.muted, font: { size: 11 } }, grid: { display: false } },
      },
    },
  });

  // Distribution table
  const tbl = $("dist-table");
  tbl.innerHTML = "";
  const fmtNum = (v, col) => {
    if (col === "gpa") return v.toFixed(2);
    if (col === "num_loans") return v.toFixed(1);
    return v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : v.toFixed(0);
  };
  for (const [col, stats] of Object.entries(eda.distributions)) {
    const row = document.createElement("div");
    row.className = "dist-row";
    const name = col.replace(/_/g, " ");
    row.innerHTML = `
      <span class="dist-col-name">${name}</span>
      <span class="dist-col-vals">
        <span class="dist-stat"><span class="dist-stat-val">${fmtNum(stats.mean, col)}</span><span class="dist-stat-lbl">mean</span></span>
        <span class="dist-stat"><span class="dist-stat-val">${fmtNum(stats.median, col)}</span><span class="dist-stat-lbl">median</span></span>
        <span class="dist-stat"><span class="dist-stat-val">${fmtNum(stats.std, col)}</span><span class="dist-stat-lbl">std</span></span>
        <span class="dist-stat"><span class="dist-stat-val">${fmtNum(stats.min, col)}</span><span class="dist-stat-lbl">min</span></span>
        <span class="dist-stat"><span class="dist-stat-val">${fmtNum(stats.max, col)}</span><span class="dist-stat-lbl">max</span></span>
      </span>
    `;
    tbl.appendChild(row);
  }
}

// ── Segmentation Charts ──────────────────────────────────────────────────────
function makeSegChart(canvasId, items, valueKey, overall) {
  const labels = items.map(r => r[valueKey] ?? r.value ?? "");
  const rates  = items.map(r => r.default_rate);
  const colors = rates.map(r => segColor(r, overall));

  makeChart(canvasId, {
    type: "bar",
    data: {
      labels,
      datasets: [{ data: rates, backgroundColor: colors, borderRadius: 3 }],
    },
    options: {
      indexAxis: "y",
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: ctx => {
          const item = items[ctx.dataIndex];
          return `${(ctx.raw * 100).toFixed(1)}%  (n=${item.n}, ${item.defaults} defaults)`;
        }}}
      },
      scales: {
        x: {
          ticks: { color: C.muted, callback: v => (v * 100).toFixed(0) + "%" },
          grid: { color: C.border },
        },
        y: { ticks: { color: C.muted, font: { size: 10 } }, grid: { display: false } },
      },
    },
  });
}

function renderSegmentation(seg) {
  const overall = seg.overall_default_rate;
  const s = seg.segments;

  makeSegChart("seg-level",       s.level,            "value", overall);
  makeSegChart("seg-gpa",         s.gpa_band,         "value", overall);
  makeSegChart("seg-student-type", s.student_type,    "value", overall);
  makeSegChart("seg-campus",      s.campus,           "value", overall);
  makeSegChart("seg-loan",        s.loan_amount,      "value", overall);
  makeSegChart("seg-status",      s.graduation_status, "value", overall);

  // IDR highlight chart (2 bars only)
  const idrItems = [
    { value: "IDR plans", default_rate: seg.idr_rate, n: seg.idr_n, defaults: Math.round(seg.idr_rate * seg.idr_n) },
    { value: "Non-IDR",  default_rate: seg.non_idr_rate, n: seg.non_idr_n, defaults: Math.round(seg.non_idr_rate * seg.non_idr_n) },
  ];
  makeSegChart("seg-idr", idrItems, "value", overall);

  // Remove pulse if differential is not significant
  if (seg.idr_differential < 0.05) $("seg-idr-card").classList.remove("pulse-red");

  // Top programs (top 12)
  const topPrograms = [...(s.program || [])].sort((a, b) => b.default_rate - a.default_rate).slice(0, 12);
  makeSegChart("seg-program", topPrograms, "value", overall);
}

// ── Static Images ─────────────────────────────────────────────────────────────
function renderImages(sid) {
  $("img-model").src = `/api/static/${sid}/fris_model_results.png`;
  $("img-seg").src   = `/api/static/${sid}/fris_segmentation.png`;
}
