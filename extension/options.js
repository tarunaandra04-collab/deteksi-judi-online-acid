import { DEFAULTS, getSettings, saveSettings } from "./defaults.js";

const $ = (id) => document.getElementById(id);
const TEXT = ["apiUrl", "model", "banner"];
const CHECK = ["autoScan", "watchChanges", "highlight", "saveHistory"];

function isLocalUrl(u) {
  try {
    const x = new URL(u);
    return x.protocol === "http:" && (x.hostname === "127.0.0.1" || x.hostname === "localhost");
  } catch { return false; }
}

async function load() {
  const s = await getSettings();
  TEXT.forEach((k) => { $(k).value = s[k]; });
  CHECK.forEach((k) => { $(k).checked = !!s[k]; });
  $("threshold").value = s.threshold;
  $("thrv").textContent = Math.round(s.threshold * 100) + "%";
  $("whitelist").value = (s.whitelist || []).join("\n");
  renderHistory();
}

$("threshold").addEventListener("input", () => { $("thrv").textContent = Math.round($("threshold").value * 100) + "%"; });

$("saveHistory").addEventListener("change", () => saveSettings({ saveHistory: $("saveHistory").checked }));

$("save").addEventListener("click", async () => {
  const url = $("apiUrl").value.trim() || DEFAULTS.apiUrl;
  if (!isLocalUrl(url)) { alert("Alamat API harus http://127.0.0.1 atau http://localhost (data halaman hanya boleh dikirim ke komputer ini)."); return; }
  const patch = {
    apiUrl: url,
    model: $("model").value,
    banner: $("banner").value,
    threshold: parseFloat($("threshold").value),
    whitelist: $("whitelist").value.split(/\r?\n/).map((x) => x.trim().toLowerCase()).filter(Boolean),
  };
  CHECK.forEach((k) => { patch[k] = $(k).checked; });
  await saveSettings(patch);
  $("saved").classList.add("on");
  setTimeout(() => $("saved").classList.remove("on"), 1800);
});

$("testBtn").addEventListener("click", async () => {
  const box = $("srv");
  box.hidden = false;
  box.textContent = "Menghubungi server…";
  const url = $("apiUrl").value.trim().replace(/\/+$/, "");
  if (!isLocalUrl(url)) { box.textContent = "Alamat harus localhost."; return; }
  try {
    const t0 = performance.now();
    const res = await fetch(url + "/health");
    const j = await res.json();
    const ms = Math.round(performance.now() - t0);
    const tw = j.trained_with || {};
    box.textContent = [
      `✔ Terhubung (${ms} ms)`,
      `Model dimuat : ${j.model_loaded ? j.models.join(", ") : "TIDAK — " + (j.error || "periksa log server")}`,
      `Dilatih pada : Python ${tw.python || "?"}, scikit-learn ${tw.sklearn || "?"}`,
      `Leksikon     : ${j.n_lexicon} kata kunci`,
      j.status_label ? `Status model  : ${j.status_label}` : "",
    ].filter(Boolean).join("\n");
  } catch (e) {
    box.textContent = "✖ Tidak terhubung. Jalankan jalankan.ps1 atau python backend/app.py.\n" + e.message;
  }
});

async function getHistory() {
  return (await chrome.storage.local.get("history")).history || [];
}

async function renderHistory() {
  const hist = await getHistory();
  const n = (l) => hist.filter((x) => x.label === l).length;
  const avg = hist.length ? Math.round(hist.reduce((a, x) => a + (x.ms_e2e || 0), 0) / hist.length) : 0;
  const stat = (v, l) => { const d = document.createElement("div"); d.className = "stat"; d.innerHTML = ""; const b = document.createElement("b"); b.textContent = v; const s = document.createElement("span"); s.textContent = l; d.append(b, s); return d; };
  $("stats").replaceChildren(stat(hist.length, "pemindaian"), stat(n("judi"), "terindikasi judi"), stat(n("waspada"), "waspada"), stat(n("aman"), "aman"), stat(avg + " ms", "rata-rata E2E"));
  const tb = $("hist");
  tb.replaceChildren();
  for (const x of hist.slice(0, 200)) {
    const tr = document.createElement("tr");
    const cells = [
      new Date(x.t).toLocaleString("id-ID"), x.url, x.label, (x.p_judi * 100).toFixed(1) + "%", x.model,
      x.kw_strong, x.hidden, x.ms_e2e,
    ];
    cells.forEach((c, i) => {
      const td = document.createElement("td");
      td.textContent = c;
      if (i === 1) { td.className = "u"; td.title = x.url; }
      if (i === 2) td.className = x.label;
      tr.append(td);
    });
    tb.append(tr);
  }
}

$("csv").addEventListener("click", async () => {
  const hist = await getHistory();
  const cols = ["t", "url", "host", "label", "risk", "p_judi", "model", "kw_strong", "hidden", "judi_links", "ms_api", "ms_e2e", "trigger"];
  const q = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lines = [cols.join(",")].concat(hist.map((x) => cols.map((c) => q(c === "t" ? new Date(x[c]).toISOString() : x[c])).join(",")));
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `riwayat-deteksi-judi-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
});

$("clear").addEventListener("click", async () => {
  if (confirm("Hapus seluruh riwayat pemindaian?")) { await chrome.storage.local.set({ history: [] }); renderHistory(); }
});

chrome.storage.onChanged.addListener((_c, area) => { if (area === "local") renderHistory(); });
load();
