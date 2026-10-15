"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const T = (s) => (window.QS_I18N ? QS_I18N.t(s) : s);

const PERCENT = new Set(["total_return", "cagr", "max_drawdown", "win_rate", "exposure", "buy_hold_return", "excess_return"]);
const MONEY = new Set(["avg_trade", "avg_win", "avg_loss", "best_trade", "worst_trade"]);
const METRIC_LABELS = {
  total_return: "總收益率", cagr: "年化 (CAGR)", max_drawdown: "最大回撤", sharpe: "夏普比率",
  sortino: "索提諾比率", calmar: "卡瑪比率", n_trades: "交易次數", win_rate: "勝率",
  profit_factor: "盈虧比", avg_trade: "平均每筆", avg_win: "平均盈利", avg_loss: "平均虧損",
  best_trade: "最佳交易", worst_trade: "最差交易", exposure: "持倉比例",
  buy_hold_return: "買入持有", excess_return: "超額報酬",
};
const READOUT_KEYS = ["total_return", "cagr", "sharpe", "calmar", "max_drawdown", "win_rate", "n_trades"];
const PER_ASSET_KEYS = ["total_return", "cagr", "max_drawdown", "sharpe", "win_rate", "profit_factor", "n_trades", "exposure", "buy_hold_return", "excess_return"];
const UP_KEYS = new Set(["total_return", "cagr", "excess_return"]);

const GITHUB_REPO_URL = "https://github.com/ShEePOAO/quant-studio";

function cssv(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function plotLayout() {
  return {
    margin: { l: 60, r: 60, t: 10, b: 34 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: cssv("--chart-plot"),
    font: { family: "IBM Plex Sans, 'Noto Sans TC', system-ui, sans-serif", size: 11.5, color: cssv("--chart-font") },
    hovermode: "x unified",
    hoverlabel: { font: { family: "Fira Code, monospace", size: 11 } },
    xaxis: { showgrid: false, linecolor: cssv("--chart-axis"), zeroline: false, ticks: "outside", ticklen: 4, tickcolor: cssv("--chart-axis"), tickfont: { size: 10.5 } },
    yaxis: { gridcolor: cssv("--chart-grid"), linecolor: "rgba(0,0,0,0)", zeroline: false, tickformat: ",.0f", tickfont: { size: 10.5 } },
    legend: { orientation: "h", y: 1.04, x: 0, font: { size: 11 } },
  };
}
function fmtAbs(v) { return v == null ? "" : Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
function lastPointMarker(xy, color, text) {
  const i = xy.y.length - 1;
  if (i < 0) return null;
  return {
    x: [xy.x[i]], y: [xy.y[i]], type: "scatter", mode: "markers+text", showlegend: false, name: "最新值",
    marker: { size: 7, color, line: { width: 1.5, color: cssv("--chart-plot") } },
    text: [text], textposition: "middle right", cliponaxis: false,
    textfont: { family: "Fira Code, monospace", size: 11, color: cssv("--ink") },
    hovertemplate: "%{y:,.0f}<extra></extra>",
  };
}
const PLOT_CONFIG = { responsive: true, displaylogo: false, scrollZoom: true, modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"] };

const state = { meta: null, editor: null, mode: "single", selected: new Set(), runToken: 0, equityScale: "linear", priceType: "auto", lastResult: null, ghost: null, strategyNames: [], pins: [], pinSeq: 0, paramDefs: {}, rollingWin: 30 };
const PIN_COLORS = ["#2C9E7E", "#C07A2E", "#8A5CC0", "#3E8FB0", "#B0555C", "#6E8E4A"];
const TIME_FMT = new Intl.DateTimeFormat("zh-TW", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });
function fmtTime(iso) { if (!iso) return ""; const d = new Date(iso); return isNaN(d.getTime()) ? String(iso) : TIME_FMT.format(d); }

/* ---------- utils ---------- */
function fmt(key, val) {
  if (val === null || val === undefined || (typeof val === "number" && !isFinite(val))) return "—";
  if (PERCENT.has(key)) return (val * 100).toFixed(2) + "%";
  if (key === "n_trades") return String(Math.round(val));
  if (MONEY.has(key)) return Number(val).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return Number(val).toFixed(2);
}
function tone(key, val) {
  if (val === null || val === undefined || !isFinite(val)) return "";
  if (UP_KEYS.has(key)) return val >= 0 ? "up" : "down";
  if (key === "max_drawdown") return "down";
  return "";
}
function el(tag, attrs = {}, children = []) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2), v);
    else if (v === true) n.setAttribute(k, "");
    else if (v !== false && v != null) n.setAttribute(k, v);
  }
  for (const c of [].concat(children)) if (c) n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  return n;
}
function showToast(msg, kind = "info") {
  const t = $("#toast");
  t.textContent = msg;
  t.dataset.kind = kind;
  t.hidden = false;
  requestAnimationFrame(() => t.classList.add("is-show"));
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => { t.classList.remove("is-show"); setTimeout(() => (t.hidden = true), 220); }, 3200);
}
function setStatus(stateName, text) {
  $("#status-dot").dataset.state = stateName;
  $("#status").textContent = text;
}

function codeGet() { return state.editor ? state.editor.getValue() : $("#code").value; }
function codeSet(v) { if (state.editor) { state.editor.setValue(v); } else { $("#code").value = v; } }

async function api(path, opts) {
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch (e) { data = null; }
  if (!res.ok || (data && data.ok === false)) {
    const err = new Error((data && data.error) || `HTTP ${res.status}`);
    err.detail = data && data.detail;
    throw err;
  }
  return data;
}

/* ---------- init ---------- */
async function init() {
  if (window.QS_I18N) QS_I18N.init();
  const th = new URLSearchParams(location.search).get("theme");
  if (th) document.documentElement.dataset.theme = th;
  try {
    state.meta = await api("/api/meta");
  } catch (e) {
    setStatus("err", "無法連線後端");
    showToast("無法取得設定，請確認後端已啟動", "err");
    return;
  }
  populateAssets();
  populateIntervals();
  codeSet(state.meta.template);
  initEditor();
  bindEvents();
  setupSymbolCombo();
  setupDual();
  ["source", "interval", "preset", "pm_mode", "opt-metric", "load-select"].forEach((id) => enhanceSelect(document.getElementById(id)));
  updateContext();
  loadStrategyList();
  parseParams();
  initGalaxyFx();
  decorateControls();
  requestAnimationFrame(updateSubnavInd);
  window.addEventListener("load", updateSubnavInd);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(updateSubnavInd);
  document.documentElement.dataset.ready = "1";
}

function initGalaxyFx() {
  if (window.Galaxy && typeof window.Galaxy.create === "function") {
    try {
      window.Galaxy.create("gradient", "#mast-fx", {
        speed: 0.2, colors: ["#EEF1F3", "#E2E7EA", "#EBEEF0", "#EEF1F3"],
      });
    } catch (e) { /* optional */ }
  }
}
function dismissEmptyFx() { /* no-op */ }

function initEditor() {
  const ta = $("#code");
  if (window.CodeMirror) {
    state.editor = CodeMirror.fromTextArea(ta, {
      mode: "python", theme: "quant", lineNumbers: true, indentUnit: 4, tabSize: 4,
      lineWrapping: false, autoCloseBrackets: true, viewportMargin: Infinity,
    });
    state.editor.setSize("100%", 320);
    state.editor.on("change", debounce(() => { parseParams(); markEditorValid(); }, 700));
  } else {
    ta.addEventListener("input", debounce(parseParams, 700));
  }
}
function markEditorValid() { $(".editor-wrap").classList.remove("invalid"); $("#editor-error").hidden = true; }

function populateAssets() {
  const single = $("#symbol");
  single.innerHTML = "";
  for (const a of state.meta.assets) {
    single.appendChild(el("option", { value: a.symbol }, [`${a.symbol} · ${a.label}`]));
  }
  const checks = $("#symbol-checks");
  checks.innerHTML = "";
  const defaults = ["BTC", "ETH", "XRP"];
  for (const a of state.meta.assets) {
    const on = defaults.includes(a.symbol);
    if (on) state.selected.add(a.symbol);
    const cb = el("input", { type: "checkbox", class: "elastic-input", "data-symbol": a.symbol, checked: on, "aria-label": a.label });
    const box = el("div", { class: "elastic-box" });
    box.innerHTML = '<svg class="elastic-checkmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    const txt = el("span", { class: "elastic-text", text: a.symbol });
    const label = el("label", { class: "elastic-checkbox-label", title: a.label }, [cb, box, txt]);
    cb.addEventListener("change", () => {
      if (cb.checked) state.selected.add(a.symbol); else state.selected.delete(a.symbol);
      updateContext();
    });
    checks.appendChild(label);
  }
}
function populateIntervals() {
  const sel = $("#interval");
  sel.innerHTML = "";
  for (const i of state.meta.intervals) sel.appendChild(el("option", { value: i.value }, [i.label]));
  sel.value = "1d";
}

function bindEvents() {
  $("#source").addEventListener("change", updateContext);
  $("#interval").addEventListener("change", updateContext);
  $("#preset").addEventListener("change", onPreset);
  $("#symbol").addEventListener("change", updateContext);
  $("#mode-seg").addEventListener("click", (e) => {
    const b = e.target.closest(".seg-item"); if (!b) return;
    setMode(b.dataset.mode);
  });
  $("#run-btn").addEventListener("click", run);
  $("#use-sltp").addEventListener("change", () => { $("#sltp-row").hidden = !$("#use-sltp").checked; });
  $("#use-vt").addEventListener("change", () => { $("#vt-row").hidden = !$("#use-vt").checked; });
  $("#pm_mode").addEventListener("change", () => { $("#pm-fields").hidden = $("#pm_mode").value === "fixed"; });
  $("#load-btn").addEventListener("click", loadStrategy);
  $("#save-btn").addEventListener("click", saveStrategy);
  $("#delete-btn").addEventListener("click", deleteStrategy);
  $("#strategy-file").addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    try {
      codeSet(await f.text());
      parseParams();
      showToast(`已載入 ${f.name}`, "ok");
    } catch (err) { showToast("讀取檔案失敗", "err"); }
    e.target.value = "";
  });
  document.querySelector(".subnav").addEventListener("click", (e) => {
    const b = e.target.closest(".subnav-item"); if (!b) return;
    setView(b.dataset.view);
  });
  $("#equity-seg").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    state.equityScale = b.dataset.t;
    for (const x of e.currentTarget.querySelectorAll("button")) x.classList.toggle("is-active", x === b);
    if (state.lastResult) render(state.lastResult);
  });
  $("#price-seg").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    state.priceType = b.dataset.t;
    for (const x of e.currentTarget.querySelectorAll("button")) x.classList.toggle("is-active", x === b);
    if (state.lastResult) render(state.lastResult);
  });
  $("#palette-input").addEventListener("input", () => paletteRender());
  $("#palette-input").addEventListener("keydown", paletteKey);
  $("#palette").addEventListener("mousedown", (e) => { if (e.target.id === "palette") paletteClose(); });
  $("#pin-btn").addEventListener("click", pinCurrent);
  $("#unpin-btn").addEventListener("click", clearPins);
  $("#manual-download").addEventListener("click", downloadManual);
  $("#manual-btn").addEventListener("click", () => setView("manual"));
  $("#opt-run").addEventListener("click", optRun);
  $("#rolling-win").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    state.rollingWin = +b.dataset.w;
    for (const x of e.currentTarget.querySelectorAll("button")) x.classList.toggle("is-active", x === b);
    if (state._lastSingle) renderRolling(state._lastSingle);
  });
  setupSplitter();
  initGithubStar();
  initLang();

  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); run(); }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); paletteOpen(); }
  });
  window.addEventListener("resize", debounce(updateSubnavInd, 150));
}

function setMode(mode) {
  state.mode = mode;
  for (const b of document.querySelectorAll("#mode-seg .seg-item")) {
    const on = b.dataset.mode === mode;
    b.classList.toggle("is-active", on);
    b.setAttribute("aria-selected", on ? "true" : "false");
  }
  $("#single-block").hidden = mode !== "single";
  $("#multi-block").hidden = mode !== "multi";
  updateContext();
}
function setView(view) {
  for (const b of document.querySelectorAll(".subnav-item")) {
    const on = b.dataset.view === view;
    b.classList.toggle("is-active", on);
    b.setAttribute("aria-selected", on ? "true" : "false");
  }
  $("#view-report").hidden = view !== "report";
  $("#view-manual").hidden = view !== "manual";
  $("#view-opt").hidden = view !== "opt";
  if (view === "manual") loadManual();
  if (view === "opt") optBuildParams();
  requestAnimationFrame(updateSubnavInd);
  window.dispatchEvent(new Event("resize"));
}
const RANGE_MIN = new Date(2013, 0, 1);
let RANGE_MAX = 1;
function _today() { const t = new Date(); return new Date(t.getFullYear(), t.getMonth(), t.getDate()); }
function _dayIndex(d) { return Math.round((d - RANGE_MIN) / 86400000); }
function _isoFromIndex(i) { return new Date(RANGE_MIN.getTime() + i * 86400000).toISOString().slice(0, 10); }
function setRangeByIndex(i0, i1) {
  i0 = Math.max(0, Math.min(i0, RANGE_MAX));
  i1 = Math.max(0, Math.min(i1, RANGE_MAX));
  if (i0 > i1) { const t = i0; i0 = i1; i1 = t; }
  $("#rg-start").value = i0; $("#rg-end").value = i1;
  $("#start").value = _isoFromIndex(i0); $("#end").value = _isoFromIndex(i1);
  const p0 = i0 / RANGE_MAX * 100, p1 = i1 / RANGE_MAX * 100;
  const fill = $("#dual-fill"); fill.style.left = p0 + "%"; fill.style.width = (p1 - p0) + "%";
  $("#range-note").textContent = `${$("#start").value} ~ ${$("#end").value}`;
  updateContext();
}
function applyPreset() {
  const preset = $("#preset").value;
  if (preset === "自訂") return;
  const end = _dayIndex(_today());
  let start = 0;
  if (preset !== "全部") {
    const years = { "近 1 年": 1, "近 2 年": 2, "近 3 年": 3, "近 5 年": 5, "近 10 年": 10 };
    const d = _today(); d.setFullYear(d.getFullYear() - (years[preset] || 3));
    start = _dayIndex(d);
  }
  setRangeByIndex(start, end);
}
function onPreset() { applyPreset(); }
function resolveDates() { return { start: $("#start").value || null, end: $("#end").value || null }; }
function setupDual() {
  RANGE_MAX = _dayIndex(_today());
  $("#rg-start").max = RANGE_MAX; $("#rg-end").max = RANGE_MAX;
  $("#rg-start").addEventListener("input", () => {
    let i0 = +$("#rg-start").value, i1 = +$("#rg-end").value;
    if (i0 > i1) { i0 = i1; $("#rg-start").value = i0; }
    $("#preset").value = "自訂"; setRangeByIndex(i0, i1);
  });
  $("#rg-end").addEventListener("input", () => {
    let i0 = +$("#rg-start").value, i1 = +$("#rg-end").value;
    if (i1 < i0) { i1 = i0; $("#rg-end").value = i1; }
    $("#preset").value = "自訂"; setRangeByIndex(i0, i1);
  });
  applyPreset();
}
function updateContext() {
  if (!state.meta) return;
  const src = $("#source").value === "csv" ? "CSV" : "API";
  const iv = $("#interval").value;
  if (state.mode === "single") {
    $("#context").textContent = `${src} · ${$("#symbol").value} · ${iv}`;
  } else {
    $("#context").textContent = `${src} · ${state.selected.size} 幣 · ${iv}`;
  }
}

/* ---------- params ---------- */
let parseSeq = 0;
async function parseParams() {
  const code = codeGet();
  const seq = ++parseSeq;
  try {
    const data = await api("/api/params", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code }) });
    if (seq !== parseSeq) return;
    markEditorValid();
    renderParams(data.param_defs || {});
  } catch (e) {
    if (seq !== parseSeq) return;
    $(".editor-wrap").classList.add("invalid");
    const box = $("#editor-error");
    box.hidden = false;
    box.textContent = e.message;
  }
}
function renderParams(defs) {
  const wrap = $("#params");
  const grp = $("#params-grp");
  const keys = Object.keys(defs);
  state.paramDefs = defs || {};
  state._optSig = null;
  if (!keys.length) { grp.hidden = true; wrap.innerHTML = ""; return; }
  grp.hidden = false;
  const prev = {};
  wrap.querySelectorAll("[data-pkey]").forEach((i) => (prev[i.dataset.pkey] = i.value));
  wrap.innerHTML = "";
  for (const key of keys) {
    const d = defs[key];
    const input = el("input", {
      "data-pkey": key, id: "param-" + key, "data-mix": "1",
      type: d.type === "choice" ? "text" : "number",
      step: d.step != null ? d.step : (d.type === "int" ? 1 : 0.1),
      min: d.min != null ? d.min : null, max: d.max != null ? d.max : null,
    });
    if (prev[key] != null) input.value = prev[key];
    else input.value = d.default != null ? d.default : "";
    if (d.type === "choice") {
      const sel = el("select", { "data-pkey": key, id: "param-" + key });
      for (const ch of d.choices) sel.appendChild(el("option", { value: ch }, [ch]));
      sel.value = prev[key] != null ? prev[key] : d.default;
      wrap.appendChild(el("label", { class: "field" }, [el("span", { class: "field-label", text: d.label || key }), sel]));
    } else {
      wrap.appendChild(el("label", { class: "field" }, [el("span", { class: "field-label", text: d.label || key }), input]));
    }
  }
  decorateControls(wrap);
}
function collectParams() {
  const params = {};
  $("#params").querySelectorAll("[data-pkey]").forEach((i) => {
    const key = i.dataset.pkey;
    const v = i.value;
    params[key] = v !== "" && !isNaN(Number(v)) && i.type === "number" ? Number(v) : v;
  });
  return params;
}

/* ---------- strategies ---------- */
async function loadStrategyList() {
  try {
    const data = await api("/api/strategies");
    state.strategyNames = data.names || [];
    const sel = $("#load-select");
    sel.innerHTML = "";
    sel.appendChild(el("option", { value: "" }, ["載入既有策略…"]));
    for (const n of data.names) sel.appendChild(el("option", { value: n }, [n]));
    sel.dispatchEvent(new Event("dd-refresh"));
  } catch (e) { /* silent */ }
}
async function loadStrategy() {
  const name = $("#load-select").value;
  if (!name) { showToast("請先選擇策略檔", "err"); return; }
  try {
    const data = await api("/api/strategies/" + encodeURIComponent(name));
    codeSet(data.code);
    parseParams();
    showToast(`已載入 ${name}`, "ok");
  } catch (e) { showToast(e.message, "err"); }
}
async function saveStrategy() {
  const name = $("#save-name").value.trim();
  if (!name) { showToast("請輸入檔名", "err"); return; }
  try {
    const data = await api("/api/strategies", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, code: codeGet() }) });
    await loadStrategyList();
    $("#load-select").value = data.name;
    $("#load-select").dispatchEvent(new Event("dd-refresh"));
    showToast(`已儲存 ${data.name}`, "ok");
  } catch (e) { showToast(e.message, "err"); }
}
async function deleteStrategy() {
  const name = $("#load-select").value;
  if (!name) { showToast("請先在下方選擇要刪除的策略檔", "err"); return; }
  const msg = `確定刪除策略檔「${name}」？此動作無法復原。`;
  let ok;
  if (window.Galaxy && typeof window.Galaxy.confirm === "function") {
    try { ok = await window.Galaxy.confirm(msg); } catch (e) { ok = window.confirm(msg); }
  } else { ok = window.confirm(msg); }
  if (!ok) return;
  try {
    await api("/api/strategies/" + encodeURIComponent(name), { method: "DELETE" });
    await loadStrategyList();
    showToast(`已刪除 ${name}`, "ok");
  } catch (e) { showToast(e.message, "err"); }
}

/* ---------- manual ---------- */
let manualLoaded = false;
let manualMarkdown = "";
async function loadManual() {
  if (manualLoaded) return manualMarkdown;
  const box = $("#manual");
  box.innerHTML = "<p>載入中…</p>";
  try {
    const data = await api("/api/manual");
    manualMarkdown = data.markdown || "";
    if (window.marked) { marked.setOptions({ gfm: true, breaks: false }); box.innerHTML = marked.parse(manualMarkdown); }
    else box.innerHTML = "<pre>" + escapeHtml(manualMarkdown) + "</pre>";
    manualLoaded = true;
  } catch (e) { box.innerHTML = "<p>無法載入手冊：" + escapeHtml(e.message) + "</p>"; }
  return manualMarkdown;
}
async function downloadManual() {
  const text = manualMarkdown || (await loadManual());
  if (!text) { showToast("手冊尚未載入", "err"); return; }
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "Quant-Studio-使用手冊.md";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  showToast("已下載手冊", "ok");
}
function escapeHtml(s) { return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

/* ---------- run ---------- */
function settingsPayload() {
  const useSltp = $("#use-sltp").checked;
  const mgmt = $("#pm_mode").value;
  const s = {
    initial_capital: Number($("#capital").value),
    fee_rate: Number($("#fee_rate").value),
    slippage: Number($("#slippage").value),
    position_pct: Number($("#position_pct").value),
    leverage: Number($("#leverage").value),
    vol_target: $("#use-vt").checked ? Number($("#vt_target").value) / 100 : null,
    stop_loss_pct: useSltp ? Number($("#stop_loss").value) / 100 : null,
    take_profit_pct: useSltp ? Number($("#take_profit").value) / 100 : null,
    risk_mgmt: null,
  };
  if (mgmt !== "fixed") {
    const up = Number($("#pm_up").value), down = Number($("#pm_down").value);
    s.risk_mgmt = {
      mode: mgmt,
      win: mgmt === "anti" ? up : down,
      loss: mgmt === "anti" ? down : up,
      cap: Number($("#pm_cap").value), floor: Number($("#pm_floor").value),
      lookback: Number($("#pm_lookback").value), decay: Number($("#pm_decay").value),
      min_pos: Number($("#pm_min_pos").value), max_pos: Number($("#pm_max_pos").value),
    };
  }
  return s;
}

async function run() {
  const btn = $("#run-btn");
  const dates = resolveDates();
  const payload = {
    code: codeGet(),
    params: collectParams(),
    settings: settingsPayload(),
    mode: state.mode,
    interval: $("#interval").value,
    start: dates.start, end: dates.end,
    source: $("#source").value,
    refresh: $("#refresh").checked,
    use_hedge: $("#use_hedge").checked,
  };
  if (state.mode === "single") {
    payload.symbol = $("#symbol").value;
  } else {
    payload.symbols = Array.from(state.selected);
    if (!payload.symbols.length) { showToast("請至少選擇一種資產", "err"); return; }
    const wtxt = $("#weights").value.trim();
    if (wtxt) {
      const parts = wtxt.replace(/，/g, ",").split(",").map((p) => p.trim()).filter((p) => p !== "");
      const vals = parts.map(Number);
      if (vals.length === payload.symbols.length && vals.every((v) => !isNaN(v))) {
        payload.weights = Object.fromEntries(payload.symbols.map((s, i) => [s, vals[i]]));
      } else { showToast(`權重數量須等於資產數（${payload.symbols.length}），改用等權`, "info"); }
    }
  }

  const token = ++state.runToken;
  btn.disabled = true;
  setStatus("busy", "回測中…");
  $("#empty-state").classList.add("hidden");
  $("#report").hidden = true;
  $("#skeleton").classList.remove("hidden");
  showProgress(0, 1, "");

  try {
    const res = await fetch("/api/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!res.ok) {
      let d = null; try { d = await res.json(); } catch (e) { /* ignore */ }
      const err = new Error((d && d.error) || `HTTP ${res.status}`); err.detail = d && d.detail; throw err;
    }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    let result = null;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl).trim();
        buf = buf.slice(nl + 1);
        if (!line) continue;
        const ev = JSON.parse(line);
        if (ev.type === "progress") showProgress(ev.done, ev.total, ev.label);
        else if (ev.type === "result") result = ev.result;
        else if (ev.type === "error") { const err = new Error(ev.error); err.detail = ev.detail; throw err; }
      }
    }
    if (token !== state.runToken) return;
    if (!result) throw new Error("沒有回傳結果");
    hideProgress();
    state.ghost = state.lastResult ? { mode: state.lastResult.mode, symbol: state.lastResult.symbol, equity: state.lastResult.equity } : null;
    state.lastResult = result;
    render(result);
    setStatus("ok", "完成");
    if (window.innerWidth <= 1024) {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      requestAnimationFrame(() => $(".subnav").scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" }));
    }
  } catch (e) {
    if (token !== state.runToken) return;
    setStatus("err", "執行失敗");
    renderError(e);
  } finally {
    if (token === state.runToken) {
      btn.disabled = false;
      $("#skeleton").classList.add("hidden");
      hideProgress();
    }
  }
}

function showProgress(done, total, label) {
  const wrap = $("#run-progress");
  if (!wrap) return;
  wrap.hidden = false;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  $("#run-progress-fill").style.transform = `scaleX(${pct / 100})`;
  if (total > 1) setStatus("busy", `回測 ${Math.min(done + 1, total)}/${total}${label ? " · " + label : ""}`);
  else setStatus("busy", "回測中…");
}
function hideProgress() {
  const wrap = $("#run-progress");
  if (!wrap) return;
  wrap.hidden = true;
  $("#run-progress-fill").style.transform = "scaleX(0)";
}

/* ---------- render ---------- */
function renderError(e) {
  $("#empty-state").classList.add("hidden");
  dismissEmptyFx();
  const rep = $("#report");
  rep.hidden = false;
  const notice = $("#notice");
  notice.hidden = false;
  notice.dataset.kind = "err";
  notice.innerHTML = "";
  notice.appendChild(el("span", { class: "ic", html: svgIcon("alert") }));
  notice.appendChild(el("div", { html: `<b>${escapeHtml(e.message)}</b>` + (e.detail ? `<pre style="margin:8px 0 0;max-height:220px;overflow:auto;background:#FBE9E7;padding:10px;border-radius:6px;font-size:11.5px">${escapeHtml(e.detail)}</pre>` : "") }));
  $("#readout").innerHTML = "";
  ["#chart-equity", "#chart-drawdown", "#chart-price", "#trades", "#per-asset", "#metrics-full", "#hedge-stats"].forEach((s) => { const n = $(s); if (n) n.innerHTML = ""; });
  $("#block-price").hidden = false;
  $("#block-perasset").hidden = true;
  showToast(e.message, "err");
}

function render(r) {
  const rep = $("#report");
  rep.hidden = false;
  rep.classList.remove("reveal"); void rep.offsetWidth; rep.classList.add("reveal");
  $("#empty-state").classList.add("hidden");
  dismissEmptyFx();

  const badge = $("#engine-badge");
  badge.hidden = false;
  badge.textContent = "引擎 · " + r.engine;

  renderNotices(r);
  renderReadout(r.metrics);
  renderHedgeStats(r);
  renderEquity(r);
  renderDrawdown(r);
  const isMulti = r.mode === "multi";
  $("#block-price").hidden = isMulti;
  $("#block-perasset").hidden = !isMulti;
  if (!isMulti) renderPrice(r);
  if (isMulti) renderPerAsset(r);
  $("#block-rolling").hidden = isMulti;
  $("#block-cost").hidden = isMulti;
  $("#block-exposure").hidden = isMulti;
  if (!isMulti) { state._lastSingle = r; renderRolling(r); renderCost(r); renderExposure(r); }
  renderTrades(r);
  renderMetricsTable(r.metrics);
}

function renderNotices(r) {
  const box = $("#notice");
  box.hidden = true;
  box.innerHTML = "";
  const items = [];
  const la = r.lookahead;
  if (la.status === "pass") items.push(["ok", "未來函數檢查通過：截斷重算與全樣本一致。"]);
  else if (la.status === "fail") {
    const ex = la.bad.slice(0, 3).map((b) => `${b[0]}（全=${b[1]}, 截=${b[2]}）`).join("；");
    items.push(["err", `偵測到未來函數（look-ahead），共 ${la.bad.length} 處不一致。範例：${ex}。常見原因：shift(-n)、rolling(center=True)、整段 mean/std/z-score。`]);
  } else items.push(["info", "未來函數檢查無法完成（策略無法在截斷資料上重算）。"]);
  if (r.metrics.liquidated) items.push(["err", "爆倉：槓桿下權益歸零，回測於該點停止。請降低槓桿或倉位。"]);
  if (r.engine && r.engine.includes("多空") && $("#use-sltp").checked) items.push(["warn", "多空（反手）引擎不支援止損/止盈，已忽略這兩個設定。"]);
  if (r.engine && r.engine.includes("網格鎖倉")) items.push(["info", "已送入網格鎖倉引擎：結果含加單 / 鎖倉 / 解鎖與資金費率。"]);
  if (!items.length) return;
  box.hidden = false;
  for (const [kind, text] of items) {
    const ic = kind === "ok" ? "check" : kind === "err" ? "alert" : kind === "warn" ? "warn" : "info";
    box.appendChild(el("div", { class: "notice", "data-kind": kind }, [el("span", { class: "ic", html: svgIcon(ic) }), el("div", { text })]));
  }
}

function renderReadout(m) {
  const wrap = $("#readout");
  wrap.innerHTML = "";
  for (const key of READOUT_KEYS) {
    const kEl = el("div", { class: "k" });
    kEl.textContent = METRIC_LABELS[key];
    if (METRIC_TIPS[key]) { kEl.dataset.tip = METRIC_TIPS[key]; kEl.tabIndex = 0; }
    const vEl = el("div", { class: "v " + tone(key, m[key]) });
    const cell = el("div", { class: "cell" }, [kEl, vEl]);
    wrap.appendChild(cell);
    countUp(vEl, key, m[key]);
  }
}

function renderHedgeStats(r) {
  const box = $("#hedge-stats");
  box.innerHTML = "";
  if (!r.hedge) { box.hidden = true; return; }
  box.hidden = false;
  const s = r.hedge.stats;
  const cells = [
    ["加單次數", s.add_opens], ["鎖倉次數", s.hedge_events], ["解鎖次數", s.unlock_events],
    ["網格開倉", s.grid_opens], ["總手續費", (s.fees_paid || 0).toLocaleString("en-US", { maximumFractionDigits: 0 })],
    ["爆倉次數", s.liquidations], ["保證金略過", s.margin_skips],
  ];
  for (const [k, v] of cells) {
    box.appendChild(el("div", { class: "cell" }, [el("div", { class: "k", text: k }), el("div", { class: "v", text: String(v) })]));
  }
}

function seriesXY(s, scale = 1) {
  const x = s.t.map((t) => t);
  const y = s.v.map((v) => (v == null ? null : v * scale));
  return { x, y };
}
function to100(s) {
  const base = s.v.find((v) => v != null) || 1;
  return s.v.map((v) => (v == null ? null : (v / base) * 100));
}
function baseTrace(name, xy, color, opts = {}) {
  return Object.assign({ x: xy.x, y: xy.y, name, type: "scatter", mode: "lines", line: { width: opts.width || 1.7, color }, hovertemplate: "%{y:,.0f}<extra>" + name + "</extra>" }, opts.extra || {});
}

function renderEquity(r) {
  const traces = [];
  const eq = seriesXY(r.equity);
  const ghost = state.ghost && state.ghost.mode === r.mode ? state.ghost : null;
  if (r.mode === "multi") {
    const layout = plotLayout();
    layout.yaxis.type = state.equityScale === "log" ? "log" : "linear";
    layout.yaxis.title = { text: "起點 = 100", font: { size: 10.5 } };
    const bh = seriesXY(r.buy_hold);
    const syms = Object.keys(r.equity_curves);
    syms.forEach((sym, i) => {
      traces.push({
        x: r.equity_curves[sym].t, y: to100(r.equity_curves[sym]), name: sym, type: "scatter", mode: "lines",
        line: { width: 1, color: cssv("--chart-asset") }, hovertemplate: "%{y:.1f}<extra>" + sym + "</extra>",
      });
    });
    traces.push({ x: bh.x, y: to100(r.buy_hold), name: "等權買入持有", type: "scatter", mode: "lines", line: { width: 1.8, color: cssv("--chart-bh"), dash: "dash" }, hovertemplate: "%{y:.1f}<extra>買入持有</extra>" });
    if (ghost && ghost.equity) { const g = seriesXY(ghost.equity); traces.push({ x: g.x, y: to100(ghost.equity), name: "上次回測", type: "scatter", mode: "lines", line: { width: 1.2, color: cssv("--chart-font"), dash: "dot" }, opacity: 0.5, hovertemplate: "%{y:.1f}<extra>上次</extra>" }); }
    state.pins.filter((p) => p.mode === "multi").forEach((p) => {
      traces.push({ x: p.equity.t, y: to100(p.equity), name: p.label, type: "scatter", mode: "lines", line: { width: 1.2, color: p.color, dash: "dot" }, opacity: 0.85, hovertemplate: "%{y:.1f}<extra>" + p.label + "</extra>" });
    });
    traces.push({ x: eq.x, y: to100(r.equity), name: "組合權益", type: "scatter", mode: "lines", line: { width: 2.2, color: cssv("--chart-line") }, hovertemplate: "%{y:.1f}<extra>組合權益</extra>" });
    const eff = to100(r.equity);
    const lmM = lastPointMarker({ x: eq.x, y: eff }, cssv("--chart-line"), String(eff[eff.length - 1] == null ? "" : eff[eff.length - 1].toFixed(1)));
    if (lmM) traces.push(lmM);
    Plotly.newPlot("chart-equity", traces, layout, PLOT_CONFIG);
    wipeEl("chart-equity");
    $("#equity-note").textContent = `${syms.length} 幣 · 起點 = 100 可比較`;
    return;
  }
  const bh = seriesXY(r.buy_hold);
  traces.push({ x: bh.x, y: bh.y, name: "買入持有", type: "scatter", mode: "lines", line: { width: 1.8, color: cssv("--chart-bh"), dash: "dash" }, hovertemplate: "%{y:,.0f}<extra>買入持有</extra>" });
  if (r.hedge && r.hedge.stop_equity) {
    const st = seriesXY(r.hedge.stop_equity);
    traces.push({ x: st.x, y: st.y, name: "直接停損", type: "scatter", mode: "lines", line: { width: 1.4, color: cssv("--chart-stop"), dash: "dash" }, hovertemplate: "%{y:,.0f}<extra>直接停損</extra>" });
  }
  if (ghost && ghost.equity) { const g = seriesXY(ghost.equity); traces.push({ x: g.x, y: g.y, name: "上次回測", type: "scatter", mode: "lines", line: { width: 1.2, color: cssv("--chart-font"), dash: "dot" }, opacity: 0.5, hovertemplate: "%{y:,.0f}<extra>上次</extra>" }); }
  state.pins.filter((p) => p.mode === "single").forEach((p) => {
    traces.push({ x: p.equity.t, y: p.equity.v, name: p.label, type: "scatter", mode: "lines", line: { width: 1.2, color: p.color, dash: "dot" }, opacity: 0.85, hovertemplate: "%{y:,.0f}<extra>" + p.label + "</extra>" });
  });
  traces.push({ x: eq.x, y: eq.y, name: "策略權益", type: "scatter", mode: "lines", line: { width: 2.2, color: cssv("--chart-line") }, hovertemplate: "%{y:,.0f}<extra>策略權益</extra>" });
  $("#equity-note").textContent = `${r.symbol} · ${r.bars} 根 K 線`;
  const lmS = lastPointMarker(eq, cssv("--chart-line"), fmtAbs(eq.y[eq.y.length - 1]));
  if (lmS) traces.push(lmS);
  const layoutS = plotLayout();
  layoutS.yaxis.type = state.equityScale === "log" ? "log" : "linear";
  Plotly.newPlot("chart-equity", traces, layoutS, PLOT_CONFIG);
  wipeEl("chart-equity");
}

function renderDrawdown(r) {
  const s = r.equity;
  let peak = -Infinity;
  const y = s.v.map((v) => { if (v == null) return null; peak = Math.max(peak, v); return (v / peak - 1) * 100; });
  const trace = { x: s.t, y, type: "scatter", mode: "lines", fill: "tozeroy", line: { color: cssv("--chart-down"), width: 1.2 }, fillcolor: cssv("--chart-fill"), hovertemplate: "%{y:.2f}%<extra>回撤</extra>" };
  const layout = plotLayout();
  layout.yaxis.ticksuffix = "%";
  layout.yaxis.tickformat = ".0f";
  layout.showlegend = false;
  Plotly.newPlot("chart-drawdown", [trace], layout, PLOT_CONFIG);
  wipeEl("chart-drawdown");
}

function renderPrice(r) {
  const p = r.price;
  const n = p.t.length;
  const pt = state.priceType || "auto";
  const dense = pt === "line" ? true : pt === "candle" ? false : n > 500;
  const traces = [];
  if (dense) {
    traces.push({
      x: p.t, y: p.c, type: "scatter", mode: "lines", name: "收盤",
      line: { color: cssv("--chart-line"), width: 1.2 }, hovertemplate: "%{y:,.4g}<extra>收盤</extra>",
    });
    $("#price-note").textContent = `${n} 根 · K 線過密，改收盤線`;
  } else {
    traces.push({
      x: p.t, open: p.o, high: p.h, low: p.l, close: p.c,
      type: "candlestick", name: "價格",
      increasing: { line: { color: cssv("--chart-up") }, fillcolor: cssv("--chart-up") },
      decreasing: { line: { color: cssv("--chart-down") }, fillcolor: cssv("--chart-down") },
    });
    $("#price-note").textContent = `${n} 根 K 線`;
  }
  if (r.buy_marks && r.buy_marks.length) traces.push(markTrace(r.buy_marks, "買入", cssv("--chart-up"), "triangle-up"));
  if (r.sell_marks && r.sell_marks.length) traces.push(markTrace(r.sell_marks, "賣出", cssv("--chart-down"), "triangle-down"));
  const layout = plotLayout();
  layout.showlegend = true;
  Plotly.newPlot("chart-price", traces, layout, PLOT_CONFIG);
  wipeEl("chart-price");
}
function markTrace(marks, name, color, symbol) {
  return {
    x: marks.map((m) => m.t), y: marks.map((m) => m.v),
    type: "scatter", mode: "markers", name,
    marker: { symbol, size: 9, color, line: { color: cssv("--chart-markup"), width: 1 } },
    hovertemplate: "%{x|%Y-%m-%d %H:%M}<br>%{y:,.4g}<extra>" + name + "</extra>",
  };
}

function renderPerAsset(r) {
  const wrap = $("#per-asset");
  wrap.innerHTML = "";
  const table = el("table");
  const thead = el("thead");
  const hr = el("tr");
  hr.appendChild(el("th", {}, ["資產"]));
  for (const k of PER_ASSET_KEYS) hr.appendChild(el("th", { class: "num" }, [METRIC_LABELS[k]]));
  thead.appendChild(hr);
  table.appendChild(thead);
  const tbody = el("tbody");
  for (const [sym, m] of Object.entries(r.per_asset)) {
    const tr = el("tr");
    tr.appendChild(el("td", {}, [sym]));
    for (const k of PER_ASSET_KEYS) {
      const td = el("td", { class: "num " + tone(k, m[k]) }, [fmt(k, m[k])]);
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
}

function renderTrades(r) {
  const wrap = $("#trades");
  let cols = r.trade_columns || [];
  if (cols.includes("資產")) cols = ["資產", ...cols.filter((c) => c !== "資產")];
  $("#trades-note").textContent = `${r.trades.length} 筆`;
  if (!r.trades.length) { wrap.innerHTML = '<div class="tw-empty">沒有完成的交易</div>'; return; }
  const table = el("table");
  const thead = el("thead"); const hr = el("tr");
  for (const c of cols) hr.appendChild(el("th", { class: (c === "進場價" || c === "出場價" || c === "數量" || c === "成本" || c === "收入" || c === "盈虧" || c === "收益率") ? "num" : "" }, [c]));
  thead.appendChild(hr); table.appendChild(thead);
  const tbody = el("tbody");
  for (const row of r.trades) {
    const tr = el("tr");
    for (const c of cols) {
      let v = row[c];
      let cls = "";
      if (c === "進場時間" || c === "出場時間") v = fmtTime(v);
      else if (c === "收益率") { cls = v >= 0 ? "up" : "down"; v = v == null ? "—" : (v * 100).toFixed(2) + "%"; }
      else if (c === "盈虧") { cls = v >= 0 ? "up" : "down"; v = v == null ? "—" : Number(v).toLocaleString("en-US", { maximumFractionDigits: 2 }); }
      else if (c === "進場價" || c === "出場價") v = v == null ? "—" : Number(v).toLocaleString("en-US", { maximumFractionDigits: 4 });
      else if (c === "數量") v = v == null ? "—" : Number(v).toLocaleString("en-US", { maximumFractionDigits: 6 });
      else if (c === "成本" || c === "收入") v = v == null ? "—" : Number(v).toLocaleString("en-US", { maximumFractionDigits: 2 });
      const numCls = (c === "進場價" || c === "出場價" || c === "數量" || c === "成本" || c === "收入" || c === "盈虧" || c === "收益率") ? "num " : "";
      tr.appendChild(el("td", { class: numCls + cls, text: v == null ? "" : String(v) }));
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.innerHTML = "";
  wrap.appendChild(table);
}

function renderMetricsTable(m) {
  const wrap = $("#metrics-full");
  wrap.innerHTML = "";
  const keys = ["total_return", "cagr", "max_drawdown", "sharpe", "sortino", "calmar", "n_trades", "win_rate", "profit_factor", "avg_trade", "avg_win", "avg_loss", "best_trade", "worst_trade", "exposure", "buy_hold_return", "excess_return"];
  const table = el("table");
  const tbody = el("tbody");
  for (const k of keys) {
    const tr = el("tr");
    tr.appendChild(el("td", { text: METRIC_LABELS[k] }));
    tr.appendChild(el("td", { class: "num " + tone(k, m[k]), text: fmt(k, m[k]) }));
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.innerHTML = "";
  wrap.appendChild(table);
}

/* ---------- icons ---------- */
function svgIcon(name) {
  const p = {
    check: "<path d='M3 8.5 L6.5 12 L13 4' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/>",
    alert: "<path d='M8 2 L15 14 H1 Z' fill='none' stroke='currentColor' stroke-width='1.7' stroke-linejoin='round'/><path d='M8 6.5 V9.5' stroke='currentColor' stroke-width='1.7' stroke-linecap='round'/><circle cx='8' cy='11.6' r='0.9' fill='currentColor'/>",
    warn: "<circle cx='8' cy='8' r='6.4' fill='none' stroke='currentColor' stroke-width='1.7'/><path d='M8 5 V8.6' stroke='currentColor' stroke-width='1.7' stroke-linecap='round'/><circle cx='8' cy='11' r='0.9' fill='currentColor'/>",
    info: "<circle cx='8' cy='8' r='6.4' fill='none' stroke='currentColor' stroke-width='1.7'/><path d='M8 7.4 V11' stroke='currentColor' stroke-width='1.7' stroke-linecap='round'/><circle cx='8' cy='5' r='0.9' fill='currentColor'/>",
  }[name];
  return `<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true">${p}</svg>`;
}

function debounce(fn, ms) {
  let t; return function (...a) { clearTimeout(t); t = setTimeout(() => fn.apply(this, a), ms); };
}

function prefersReduced() { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; }
const METRIC_TIPS = {
  total_return: "期末權益 ÷ 期初 − 1",
  cagr: "幾何年化報酬",
  sharpe: "報酬 ÷ 波動（越高越好）",
  calmar: "年化報酬 ÷ 最大回撤",
  max_drawdown: "由高點回落的最大幅度",
  win_rate: "獲利交易 ÷ 總交易數",
  n_trades: "已平倉交易筆數",
};
function countUp(node, key, val) {
  if (val == null || !isFinite(val) || prefersReduced()) { node.textContent = fmt(key, val); return; }
  const dur = 450; const t0 = performance.now();
  (function step(t) {
    const p = Math.min(1, (t - t0) / dur);
    const e = 1 - Math.pow(1 - p, 3);
    node.textContent = fmt(key, val * e);
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}
function wipeEl(sel) {
  const n = $(sel); if (!n) return;
  n.classList.remove("wipe"); void n.offsetWidth;
  if (!prefersReduced()) n.classList.add("wipe");
}
function updateSubnavInd() {
  const ind = $("#subnav-ind");
  const active = document.querySelector(".subnav-item.is-active");
  if (!ind || !active) return;
  ind.style.width = active.offsetWidth + "px";
  ind.style.transform = `translateX(${active.offsetLeft}px)`;
}

const MIX_IDS = new Set(["position_pct", "leverage", "stop_loss", "take_profit", "fee_rate", "slippage",
  "vt_target", "pm_up", "pm_down", "pm_cap", "pm_floor", "pm_lookback", "pm_decay", "pm_min_pos", "pm_max_pos"]);
const UNITS = { capital: "USDT", position_pct: "×", leverage: "×", vt_target: "%", stop_loss: "%", take_profit: "%",
  pm_up: "×", pm_down: "×", pm_cap: "×", pm_floor: "×", pm_min_pos: "×", pm_max_pos: "×" };
function decorateControls(root = document) {
  root.querySelectorAll("input[type=number]").forEach((inp) => {
    if (inp.dataset.decorated) return;
    const field = inp.closest(".field");
    if (!field) return;
    let ctl = field.querySelector(".field-ctl");
    if (!ctl) {
      ctl = el("div", { class: "field-ctl" });
      field.appendChild(ctl);
      ctl.appendChild(inp);
    }
    const min = Number(inp.min), max = Number(inp.max);
    const okRange = inp.min !== "" && inp.max !== "" && isFinite(min) && isFinite(max) && (max - min) > 0 && (max - min) <= 5000;
    if (okRange && (MIX_IDS.has(inp.id) || inp.dataset.mix === "1") && !ctl.querySelector(".mix")) {
      const r = el("input", { type: "range", class: "mix", min: inp.min, max: inp.max, step: inp.step || "any", value: inp.value, "aria-hidden": "true", tabindex: "-1" });
      ctl.insertBefore(r, inp);
      r.addEventListener("input", () => { inp.value = r.value; inp.dispatchEvent(new Event("input", { bubbles: true })); });
      const sync = () => { r.value = inp.value; };
      inp.addEventListener("input", sync);
      inp.addEventListener("change", sync);
      ctl.classList.add("has-mix");
    }
    const u = UNITS[inp.id];
    if (u && !ctl.querySelector(".unit")) { ctl.appendChild(el("span", { class: "unit", text: u })); ctl.classList.add("has-unit"); }
    attachScrub(inp);
    inp.dataset.decorated = "1";
  });
}

/* ---------- asset combobox ---------- */
function setupSymbolCombo() {
  const input = $("#symbol-input"), menu = $("#symbol-menu"), sel = $("#symbol");
  function setActive(i) {
    const btns = Array.from(menu.querySelectorAll("button"));
    btns.forEach((b, k) => b.classList.toggle("is-active", k === i));
    menu._active = i;
  }
  function render(filter) {
    const f = (filter || "").trim().toLowerCase();
    const items = state.meta.assets.filter((a) => !f || a.symbol.toLowerCase().includes(f) || String(a.label || "").toLowerCase().includes(f));
    menu.innerHTML = "";
    if (!items.length) { menu.appendChild(el("div", { class: "empty", text: "找不到資產" })); return; }
    items.forEach((a) => {
      const b = el("button", { type: "button", role: "option" }, [el("span", { class: "sym", text: a.symbol }), el("span", { class: "lbl", text: a.label || "" })]);
      b.addEventListener("mouseenter", () => setActive(Array.from(menu.querySelectorAll("button")).indexOf(b)));
      b.addEventListener("click", () => selectSymbol(a.symbol));
      menu.appendChild(b);
    });
    setActive(0);
  }
  function open() { render(""); menu.hidden = false; input.setAttribute("aria-expanded", "true"); }
  function close() { menu.hidden = true; input.setAttribute("aria-expanded", "false"); }
  function selectSymbol(sym) {
    sel.value = sym;
    const a = state.meta.assets.find((x) => x.symbol === sym);
    input.value = a ? `${sym} · ${T(a.label || "")}` : sym;
    close(); updateContext();
  }
  document.addEventListener("qs-langchange", () => { const a = state.meta.assets.find((x) => x.symbol === sel.value); if (a) input.value = `${sel.value} · ${T(a.label || "")}`; updateContext(); });
  input.addEventListener("focus", () => { input.select(); open(); });
  input.addEventListener("input", () => { render(input.value); menu.hidden = false; input.setAttribute("aria-expanded", "true"); });
  input.addEventListener("keydown", (e) => {
    const btns = Array.from(menu.querySelectorAll("button"));
    if (e.key === "Escape") { close(); input.blur(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); if (btns.length) setActive(Math.min((menu._active ?? 0) + 1, btns.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); if (btns.length) setActive(Math.max((menu._active ?? 0) - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); const b = btns[menu._active ?? 0]; if (b) b.click(); }
  });
  document.addEventListener("mousedown", (e) => { if (!e.target.closest(".combo")) close(); });
  selectSymbol(sel.value || (state.meta.assets[0] && state.meta.assets[0].symbol));
}

function enhanceSelect(sel) {
  if (!sel || sel.dataset.dd === "1") return;
  sel.dataset.dd = "1";
  const wrap = el("span", { class: "dd", "data-for": sel.id });
  const btn = el("button", { type: "button", class: "dd-btn", "aria-haspopup": "listbox", "aria-expanded": "false" });
  const lbl = el("span", { class: "dd-label" });
  btn.appendChild(lbl);
  btn.insertAdjacentHTML("beforeend", '<svg class="dd-caret" viewBox="0 0 12 12" aria-hidden="true"><path d="M2 4.5 L6 8.5 L10 4.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>');
  const menu = el("div", { class: "dd-menu", role: "listbox" });
  wrap.appendChild(btn); wrap.appendChild(menu);
  sel.parentNode.insertBefore(wrap, sel);
  sel.style.display = "none";

  function update() {
    const cur = sel.options[sel.selectedIndex];
    lbl.textContent = cur ? cur.text : "";
    menu.querySelectorAll("button").forEach((b) => b.classList.toggle("is-sel", b.dataset.value === sel.value));
  }
  function open() {
    menu.innerHTML = "";
    Array.from(sel.options).forEach((opt, i) => {
      const b = el("button", { type: "button", role: "option" });
      b.textContent = opt.text;
      b.dataset.value = opt.value;
      b.style.setProperty("--i", i);
      b.addEventListener("click", () => { sel.value = opt.value; sel.dispatchEvent(new Event("change", { bubbles: true })); close(); update(); });
      menu.appendChild(b);
    });
    update();
    wrap.classList.add("open");
    btn.setAttribute("aria-expanded", "true");
  }
  function close() { wrap.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); }
  btn.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); if (wrap.classList.contains("open")) close(); else open(); });
  sel.addEventListener("change", update);
  sel._ddUpdate = update;
  sel.addEventListener("dd-refresh", update);
  document.addEventListener("mousedown", (e) => { if (!wrap.contains(e.target)) close(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  update();
}

/* ---------- command palette ---------- */
let paletteItems = [], paletteActive = 0;
function paletteCommands() {
  const cmds = [
    { label: "執行回測", k: "⏎", run: () => run() },
    { label: "切換 · 單一資產", run: () => setMode("single") },
    { label: "切換 · 多籌組合", run: () => setMode("multi") },
    { label: "檢視 · 回測結果", run: () => setView("report") },
    { label: "檢視 · 使用手冊", run: () => setView("manual") },
    { label: "切換 · 波動目標", run: () => $("#use-vt").click() },
    { label: "切換 · 網格鎖倉", run: () => $("#use_hedge").click() },
    { label: "複製程式碼", run: () => copyCode() },
    { label: "主題 · 冷灰", run: () => setTheme("slate") },
    { label: "主題 · 冷白", run: () => setTheme("paper") },
    { label: "主題 · 暖紙", run: () => setTheme("warm") },
  ];
  state.strategyNames.forEach((n) => cmds.push({ label: `載入策略 · ${n}`, run: () => { $("#load-select").value = n; loadStrategy(); } }));
  return cmds;
}
function paletteHighlight() { $("#palette-list").querySelectorAll("button").forEach((b, i) => b.classList.toggle("is-active", i === paletteActive)); }
function paletteRender() {
  const q = $("#palette-input").value.trim().toLowerCase();
  paletteItems = paletteCommands().filter((c) => !q || c.label.toLowerCase().includes(q));
  paletteActive = 0;
  const list = $("#palette-list");
  list.innerHTML = "";
  if (!paletteItems.length) { list.appendChild(el("div", { class: "palette-empty", text: "沒有符合的指令" })); return; }
  paletteItems.forEach((c, i) => {
    const b = el("button", { type: "button" }, [el("span", { text: c.label }), c.k ? el("span", { class: "k", text: c.k }) : null]);
    b.addEventListener("mouseenter", () => { paletteActive = i; paletteHighlight(); });
    b.addEventListener("click", () => { paletteClose(); c.run(); });
    list.appendChild(b);
  });
  paletteHighlight();
}
function paletteKey(e) {
  if (e.key === "Escape") paletteClose();
  else if (e.key === "ArrowDown") { e.preventDefault(); paletteActive = Math.min(paletteActive + 1, Math.max(paletteItems.length - 1, 0)); paletteHighlight(); }
  else if (e.key === "ArrowUp") { e.preventDefault(); paletteActive = Math.max(paletteActive - 1, 0); paletteHighlight(); }
  else if (e.key === "Enter") { e.preventDefault(); const c = paletteItems[paletteActive]; if (c) { paletteClose(); c.run(); } }
}
function paletteOpen() { $("#palette").hidden = false; $("#palette-input").value = ""; paletteRender(); $("#palette-input").focus(); }
function paletteClose() { $("#palette").hidden = true; }
function setTheme(t) { if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; if (state.lastResult) render(state.lastResult); }

async function copyCode() {
  try { await navigator.clipboard.writeText(codeGet()); showToast("已複製程式碼", "ok"); }
  catch (e) { showToast("複製失敗（瀏覽器未允許）", "err"); }
}

function pinCurrent() {
  if (!state.lastResult) { showToast("先執行回測再釘選", "err"); return; }
  const r = state.lastResult;
  const label = r.mode === "multi" ? `${r.symbols.length} 幣` : (r.symbol || "");
  state.pinSeq += 1;
  state.pins.push({ mode: r.mode, equity: r.equity, color: PIN_COLORS[(state.pinSeq - 1) % PIN_COLORS.length], label: `釘選${state.pinSeq} · ${label}` });
  showToast("已釘選目前結果", "ok");
  render(state.lastResult);
}
function clearPins() {
  if (!state.pins.length) { showToast("沒有釘選", "info"); return; }
  state.pins = [];
  showToast("已清除釘選", "ok");
  if (state.lastResult) render(state.lastResult);
}
function initGithubStar() {
  const a = $("#gh-star");
  if (!a) return;
  const num = $("#gh-count-num");
  const url = GITHUB_REPO_URL.trim();
  if (!url) { a.href = "#"; a.title = "尚未設定 GitHub 專案網址（設定 GITHUB_REPO_URL 即可）"; a.addEventListener("click", (e) => { e.preventDefault(); showToast("尚未設定 GitHub 專案網址", "err"); }); return; }
  a.href = url;
  const m = url.match(/github\.com\/([^/]+)\/([^/?#]+)/);
  if (m && num) {
    fetch(`https://api.github.com/repos/${m[1]}/${m[2]}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d && typeof d.stargazers_count === "number") num.textContent = d.stargazers_count.toLocaleString(); })
      .catch(() => {});
  }
}

function initLang() {
  const dd = $("#lang-dd");
  if (!dd) return;
  const btn = dd.querySelector(".dd-btn");
  const label = $("#lang-label");
  const menu = dd.querySelector(".dd-menu");
  const KEY = "qs-lang";
  function apply(lang) {
    const item = menu.querySelector(`[data-lang="${lang}"]`);
    menu.querySelectorAll("button").forEach((b) => b.classList.toggle("is-sel", b === item));
    if (label && item) label.textContent = item.dataset.name;
  }
  function open() { dd.classList.add("open"); btn.setAttribute("aria-expanded", "true"); }
  function close() { dd.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); }
  btn.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); if (dd.classList.contains("open")) close(); else open(); });
  menu.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    const lang = b.dataset.lang;
    close();
    if (window.QS_I18N) QS_I18N.setLang(lang);
    localStorage.setItem(KEY, lang);
    apply(lang);
    showToast(lang === "en-US" ? "Language switched to English (USA)" : "語言：台灣（繁體中文）", "ok");
  }));
  document.addEventListener("mousedown", (e) => { if (!dd.contains(e.target)) close(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  apply(localStorage.getItem(KEY) || "zh-Hant");
}

function setupSplitter() {
  const wb = document.querySelector(".workbench");
  const sp = $("#splitter");
  const grip = $("#split-toggle");
  const bench = $(".bench");
  if (!wb || !sp || !bench) return;
  const KEY = "qs-bench-w", CKEY = "qs-bench-collapsed";
  const saved = localStorage.getItem(KEY);
  if (saved) wb.style.setProperty("--bench-w", `${saved}px`);
  if (localStorage.getItem(CKEY) === "1") { wb.classList.add("collapsed"); grip.textContent = "›"; }
  let dragging = false, startX = 0, startW = 0;
  const benchW = () => bench.getBoundingClientRect().width;
  sp.addEventListener("pointerdown", (e) => {
    if (e.target === grip || wb.classList.contains("collapsed")) return;
    dragging = true; startX = e.clientX; startW = benchW();
    sp.classList.add("dragging"); document.body.style.cursor = "col-resize";
    try { sp.setPointerCapture(e.pointerId); } catch (_) { /* ignore */ }
    e.preventDefault();
  });
  sp.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const w = Math.max(300, Math.min(660, startW + (e.clientX - startX)));
    wb.style.setProperty("--bench-w", `${w}px`);
  });
  const end = () => {
    if (!dragging) return;
    dragging = false; sp.classList.remove("dragging"); document.body.style.cursor = "";
    localStorage.setItem(KEY, Math.round(benchW()));
    requestAnimationFrame(updateSubnavInd);
  };
  sp.addEventListener("pointerup", end);
  sp.addEventListener("pointercancel", end);
  sp.addEventListener("dblclick", () => { wb.style.removeProperty("--bench-w"); localStorage.removeItem(KEY); requestAnimationFrame(updateSubnavInd); });
  grip.addEventListener("click", () => {
    const c = wb.classList.toggle("collapsed");
    grip.textContent = c ? "›" : "‹";
    localStorage.setItem(CKEY, c ? "1" : "0");
    window.dispatchEvent(new Event("resize"));
  });
}

/* ---------- analysis charts ---------- */
const PPY = { "5m": 105120, "15m": 35040, "30m": 17520, "1h": 8760, "4h": 2190, "6h": 1460, "12h": 730, "1d": 365, "1w": 52 };
function renderRolling(r) {
  const v = (r.equity && r.equity.v) || [];
  if (v.length < 5) return;
  const w = Math.min(state.rollingWin || 30, Math.max(5, v.length - 1));
  const ppy = PPY[r.interval] || 365;
  const rets = v.map((x, i) => (i && v[i - 1] ? x / v[i - 1] - 1 : 0));
  let sum = 0, sum2 = 0;
  const sharpe = [], vol = [];
  for (let i = 0; i < v.length; i++) {
    const x = rets[i]; sum += x; sum2 += x * x;
    if (i >= w) { const o = rets[i - w]; sum -= o; sum2 -= o * o; }
    const n = Math.min(i + 1, w);
    const m = sum / n;
    const sd = Math.sqrt(Math.max(0, sum2 / n - m * m));
    sharpe.push(sd > 0 ? (m / sd) * Math.sqrt(ppy) : null);
    vol.push(sd * Math.sqrt(ppy) * 100);
  }
  const traces = [
    { x: r.equity.t, y: sharpe, name: "滾動夏普", type: "scatter", mode: "lines", line: { width: 1.6, color: cssv("--chart-line") }, hovertemplate: "%{y:.2f}<extra>夏普</extra>" },
    { x: r.equity.t, y: vol, name: "年化波動", type: "scatter", mode: "lines", yaxis: "y2", line: { width: 1.4, color: cssv("--chart-up") }, hovertemplate: "%{y:.1f}%<extra>波動</extra>" },
  ];
  const layout = plotLayout();
  layout.yaxis.title = { text: "夏普", font: { size: 10.5 } };
  layout.yaxis2 = { overlaying: "y", side: "right", showgrid: false, ticksuffix: "%", tickfont: { size: 10.5 } };
  Plotly.newPlot("chart-rolling", traces, layout, PLOT_CONFIG);
  wipeEl("chart-rolling");
  $("#rolling-note").textContent = `視窗 ${w} 根`;
}
function renderCost(r) {
  if (!r.gross_equity) return;
  const net = seriesXY(r.equity), gross = seriesXY(r.gross_equity);
  const traces = [
    { x: gross.x, y: gross.y, name: "毛權益（無成本）", type: "scatter", mode: "lines", line: { width: 1.5, color: cssv("--chart-up") }, hovertemplate: "%{y:,.0f}<extra>毛</extra>" },
    { x: net.x, y: net.y, name: "淨權益", type: "scatter", mode: "lines", line: { width: 1.8, color: cssv("--chart-line") }, hovertemplate: "%{y:,.0f}<extra>淨</extra>" },
  ];
  Plotly.newPlot("chart-cost", traces, plotLayout(), PLOT_CONFIG);
  wipeEl("chart-cost");
  const g = gross.y[gross.y.length - 1], n = net.y[net.y.length - 1];
  const fees = (r.fees_cum && r.fees_cum.v.length) ? r.fees_cum.v[r.fees_cum.v.length - 1] : 0;
  $("#cost-note").textContent = `總成本 ≈ ${fmtAbs(g - n)}（手續費 ≈ ${fmtAbs(fees)}）`;
}
function renderExposure(r) {
  if (!r.exposure) return;
  const e = seriesXY(r.exposure);
  const trace = { x: e.x, y: e.y, type: "scatter", mode: "lines", fill: "tozeroy", line: { width: 1, color: cssv("--chart-line") }, fillcolor: "rgba(44,71,150,.18)", hovertemplate: "%{y:.0f}<extra>持倉</extra>" };
  const layout = plotLayout();
  layout.showlegend = false;
  layout.yaxis.range = [0, 1.05];
  layout.yaxis.tickformat = ".0f";
  Plotly.newPlot("chart-exposure", [trace], layout, PLOT_CONFIG);
  wipeEl("chart-exposure");
  const avg = e.y.length ? e.y.reduce((a, b) => a + b, 0) / e.y.length : 0;
  $("#exposure-note").textContent = `持倉時間 ${(avg * 100).toFixed(1)}%`;
}

/* ---------- optimizer ---------- */
function optBuildParams() {
  const defs = state.paramDefs || {};
  const keys = Object.keys(defs).filter((k) => defs[k].type === "int" || defs[k].type === "float");
  const box = $("#opt-params");
  const sig = keys.join("|");
  if (state._optSig === sig && box.children.length) return;
  state._optSig = sig;
  box.innerHTML = "";
  if (!keys.length) { box.innerHTML = '<p class="hint">目前策略沒有可掃描的數值參數（需定義 PARAM_DEFS）。</p>'; return; }
  const hdr = el("div", { class: "opt-param" });
  hdr.innerHTML = '<span></span><span class="nm">參數</span><span class="hdr">最小</span><span class="hdr">最大</span><span class="hdr">步長</span>';
  box.appendChild(hdr);
  keys.forEach((k) => {
    const d = defs[k], isInt = d.type === "int", def = Number(d.default);
    const mn = isInt ? Math.max(Math.round(d.min), Math.round(def * 0.5)) : Math.max(Number(d.min), def * 0.5);
    const mx = isInt ? Math.min(Math.round(d.max), Math.round(def * 1.5)) : Math.min(Number(d.max), def * 1.5);
    const st = isInt ? Math.max(1, Math.round(def * 0.25)) : ((def * 0.25) || 0.1);
    const row = el("div", { class: "opt-param", "data-k": k });
    row.appendChild(el("input", { type: "checkbox", "data-k": k }));
    row.appendChild(el("span", { class: "nm", text: `${d.label || k} (${k})` }));
    row.appendChild(el("input", { type: "number", "data-f": "min", value: mn, step: st }));
    row.appendChild(el("input", { type: "number", "data-f": "max", value: mx, step: st }));
    row.appendChild(el("input", { type: "number", "data-f": "step", value: st, step: st, min: isInt ? 1 : 0.000001 }));
    box.appendChild(row);
  });
}
async function optRun() {
  const rows = $("#opt-params").querySelectorAll("div.opt-param[data-k]");
  const grid = {};
  rows.forEach((row) => {
    const k = row.dataset.k;
    const cb = row.querySelector('input[type="checkbox"]');
    if (!cb || !cb.checked) return;
    const d = state.paramDefs[k] || {};
    const val = (f) => { const i = row.querySelector(`input[data-f="${f}"]`); return i ? Number(i.value) : null; };
    grid[k] = { min: val("min"), max: val("max"), step: val("step"), int: d.type === "int" };
  });
  if (!Object.keys(grid).length) { showToast("請至少勾選一個參數", "err"); return; }
  if (Object.keys(grid).length > 2) { showToast("最多選 2 個參數（畫熱力圖）", "err"); return; }
  const dates = resolveDates();
  const body = {
    code: codeGet(), params: collectParams(), settings: settingsPayload(),
    symbol: $("#symbol").value, interval: $("#interval").value, start: dates.start, end: dates.end,
    source: $("#source").value, refresh: $("#refresh").checked, use_hedge: $("#use_hedge").checked,
    grid, metric: $("#opt-metric").value,
  };
  const btn = $("#opt-run");
  btn.disabled = true; setStatus("busy", "優化中…");
  $("#opt-output").innerHTML = '<div class="sk sk-block"></div>';
  try {
    const res = await fetch("/api/optimize", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!res.ok) { let d = null; try { d = await res.json(); } catch (e) { /* ignore */ } throw Object.assign(new Error((d && d.error) || `HTTP ${res.status}`), { detail: d && d.detail }); }
    const reader = res.body.getReader(); const dec = new TextDecoder();
    let buf = "", result = null;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1);
        if (!line) continue;
        const ev = JSON.parse(line);
        if (ev.type === "progress") { setStatus("busy", `優化 ${ev.done}/${ev.total}`); $("#opt-note").textContent = `優化 ${ev.done}/${ev.total}`; }
        else if (ev.type === "result") result = ev.result;
        else if (ev.type === "error") throw Object.assign(new Error(ev.error), { detail: ev.detail });
      }
    }
    if (!result) throw new Error("沒有回傳結果");
    renderOptResult(result);
    setStatus("ok", "完成");
    $("#opt-note").textContent = `完成 · ${result.combos} 組`;
  } catch (e) {
    setStatus("err", "失敗");
    $("#opt-output").innerHTML = `<div class="notice" data-kind="err"><div><b>${escapeHtml(e.message)}</b></div></div>`;
    showToast(e.message, "err");
  } finally { btn.disabled = false; }
}
function renderOptResult(o) {
  const out = $("#opt-output");
  out.innerHTML = "";
  const MKEY = { sharpe: "夏普", total_return: "總收益", cagr: "年化", max_drawdown: "回撤", calmar: "卡瑪", profit_factor: "盈虧比", win_rate: "勝率" };
  const metric = o.metric, mlabel = MKEY[metric] || metric, keys = o.keys;
  if (keys.length === 2) {
    const xs = [...new Set(o.rows.map((r) => r.p[keys[0]]))].sort((a, b) => a - b);
    const ys = [...new Set(o.rows.map((r) => r.p[keys[1]]))].sort((a, b) => a - b);
    const z = ys.map((y) => xs.map((x) => {
      const row = o.rows.find((r) => r.p[keys[0]] === x && r.p[keys[1]] === y);
      return row ? row.metrics[metric] : null;
    }));
    const trace = { x: xs, y: ys, z, type: "heatmap", colorscale: [[0, cssv("--chart-down")], [0.5, "#f0f0ee"], [1, cssv("--chart-up")]], hovertemplate: `${keys[0]} %{x}<br>${keys[1]} %{y}<br>${mlabel} %{z:.3f}<extra></extra>` };
    const layout = plotLayout();
    layout.xaxis.title = { text: keys[0] };
    layout.yaxis.title = { text: keys[1] };
    layout.yaxis.tickformat = "";
    const wrap = el("div", { class: "chart" });
    out.appendChild(wrap);
    Plotly.newPlot(wrap, [trace], layout, PLOT_CONFIG);
  } else if (keys.length === 1) {
    const xs = o.rows.map((r) => r.p[keys[0]]);
    const ys = o.rows.map((r) => r.metrics[metric]);
    const trace = { x: xs, y: ys, type: "scatter", mode: "lines+markers", line: { color: cssv("--chart-line"), width: 1.8 }, marker: { size: 6 }, hovertemplate: "%{x} → %{y:.3f}<extra></extra>" };
    const layout = plotLayout();
    layout.xaxis.title = { text: keys[0] };
    layout.yaxis.title = { text: mlabel };
    const wrap = el("div", { class: "chart" });
    out.appendChild(wrap);
    Plotly.newPlot(wrap, [trace], layout, PLOT_CONFIG);
  }
  const asc = metric === "max_drawdown";
  const sorted = [...o.rows].sort((a, b) => {
    const x = a.metrics[metric], y = b.metrics[metric];
    if (x == null) return 1; if (y == null) return -1;
    return asc ? x - y : y - x;
  }).slice(0, 50);
  const table = el("table");
  const thead = el("thead"); const hr = el("tr");
  keys.forEach((k) => hr.appendChild(el("th", { class: "num" }, [k])));
  o.metrics.forEach((m) => hr.appendChild(el("th", { class: "num" }, [MKEY[m] || m])));
  thead.appendChild(hr); table.appendChild(thead);
  const tb = el("tbody");
  sorted.forEach((r) => {
    const tr = el("tr");
    keys.forEach((k) => tr.appendChild(el("td", { class: "num", text: String(r.p[k]) })));
    o.metrics.forEach((m) => tr.appendChild(el("td", { class: "num", text: fmt(m, r.metrics[m]) })));
    tb.appendChild(tr);
  });
  table.appendChild(tb);
  const tw = el("div", { class: "tablewrap" });
  tw.appendChild(table); out.appendChild(tw);
  out.appendChild(el("p", { class: "hint", html: `指標：<b>${mlabel}</b>${asc ? "（越小越好）" : "（越大越好）"}；顯示前 ${sorted.length} 名。找「穩定高原」而非單一尖峰。` }));
}

/* ---------- drag-to-scrub numbers ---------- */
function attachScrub(inp) {
  if (inp.dataset.scrub) return;
  inp.dataset.scrub = "1";
  if (inp.min === "" || inp.max === "") return;
  inp.classList.add("scrub");
  let dragging = false, moved = false, startX = 0, startVal = 0;
  inp.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    dragging = true; moved = false; startX = e.clientX; startVal = parseFloat(inp.value) || 0;
    try { inp.setPointerCapture(e.pointerId); } catch (_) { /* ignore */ }
  });
  inp.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const dx = e.clientX - startX;
    if (!moved && Math.abs(dx) < 4) return;
    moved = true; e.preventDefault();
    const min = Number(inp.min), max = Number(inp.max), step = Number(inp.step) || 1;
    const perPx = (max - min) / 220;
    let val = Math.max(min, Math.min(max, startVal + dx * perPx));
    val = Math.round(val / step) * step;
    const dec = (String(step).split(".")[1] || "").length;
    inp.value = dec ? val.toFixed(dec) : String(val);
    inp.dispatchEvent(new Event("input", { bubbles: true }));
  });
  const endDrag = () => { if (dragging && moved) inp.blur(); dragging = false; };
  inp.addEventListener("pointerup", endDrag);
  inp.addEventListener("pointercancel", endDrag);
}

init();
