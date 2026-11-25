import { getSettings, isAcId } from "./defaults.js";

const root = document.getElementById("content");
let tab = null;
let settings = null;
const S = self.DJOSUM;

function h(tag, props = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null) e[k] = v;
  }
  for (const kid of kids.flat(Infinity)) if (kid !== null && kid !== undefined && kid !== false) e.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  return e;
}
const show = (...nodes) => root.replaceChildren(...nodes.flat(Infinity).filter(Boolean));
const msg = (title, sub) => h("div", { class: "msg" }, h("div", { class: "t" }, title), sub ? h("div", { class: "s" }, sub) : null);
const hostOf = () => { try { return new URL(tab.url).hostname; } catch { return ""; } };

const sendToTab = (m) => chrome.tabs.sendMessage(tab.id, m);

async function scanNow() {
  show(msg("Memeriksa halaman…", "Mohon tunggu sebentar."));
  try {
    try { await sendToTab({ type: "GET_UI_STATE" }); }
    catch { await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["lexicon.js", "scanner.js", "ringkas.js", "content.js"] }); }
    await sendToTab({ type: "RESCAN", manual: true });
  } catch (e) {
    show(msg("Halaman ini tidak bisa diperiksa", "Ekstensi tidak dapat berjalan di halaman khusus browser (edge://, toko ekstensi, PDF)."));
  }
}

function lampRow(lamp) {
  return h("div", { class: "lamps" },
    ["g", "y", "r"].map((c, i) => h("div", { class: `lamp ${c}` + (i === lamp ? " on" : "") })));
}

function renderResult(rec, ui) {
  const sm = S.summarize(rec);
  const cls = sm.lvl === 2 ? "danger" : sm.lvl === 1 ? "warn" : "safe";
  const nodes = [
    h("div", { class: "host" }, new URL(rec.url).hostname),
    h("div", { class: "hero" }, lampRow(sm.lamp), h("div", { class: `word ${cls}` }, sm.word), h("div", { class: "sentence" }, sm.sentence)),
    h("h3", {}, "Hasil pemeriksaan"),
    ...sm.rows.map((x) => h("div", { class: `check l${x.level}` },
      h("div", { class: "mark" }, ["✓", "!", "✕"][x.level]), h("div", { class: "name" }, x.name), h("div", { class: "val" }, x.text))),
  ];
  if (sm.lvl > 0) {
    const on = ui && ui.highlightOn;
    nodes.push(h("button", { class: "btn primary", onclick: toggleHighlight }, on ? "Sembunyikan tanda di halaman" : "Lihat di halaman"));
    nodes.push(h("button", { class: "link", onclick: async (e) => {
      try { await navigator.clipboard.writeText(S.reportText(rec)); e.target.textContent = "Laporan disalin ✓"; } catch { e.target.textContent = "Gagal menyalin"; }
    } }, "Salin laporan untuk admin"));
  } else {
    nodes.push(h("button", { class: "btn", onclick: rescan }, "Periksa ulang"));
  }
  nodes.push(h("div", { class: "note" }, "Hasil ini perkiraan komputer, bukan keputusan akhir."));
  show(...nodes);
}

async function rescan() {
  show(msg("Memeriksa ulang…"));
  try { await sendToTab({ type: "RESCAN" }); } catch { await scanNow(); }
}
async function toggleHighlight() {
  try { await sendToTab({ type: "TOGGLE_HIGHLIGHT" }); } catch { /* abaikan */ }
  render();
}

async function render() {
  const key = `state_${tab.id}`;
  const stored = (await chrome.storage.session.get(key))[key];
  const host = hostOf();
  const ac = isAcId(host);

  if (!stored || stored.url !== tab.url) {
    if (ac && settings.autoScan) {
      show(msg("Menunggu pemeriksaan…", "Halaman sedang dimuat."), h("button", { class: "btn primary", onclick: scanNow }, "Periksa sekarang"));
      return;
    }
    show(msg("Ini bukan situs .ac.id", "Ekstensi bekerja otomatis di situs .ac.id. Anda tetap bisa memeriksa halaman ini."),
      h("button", { class: "btn primary", onclick: scanNow }, "Periksa halaman ini"));
    return;
  }
  if (stored.status === "loading") { show(msg("Memeriksa halaman…", "Mohon tunggu sebentar.")); return; }
  if (stored.status === "error") {
    show(msg("Tidak bisa memeriksa halaman", stored.error), h("button", { class: "btn primary", onclick: rescan }, "Coba lagi"));
    return;
  }
  let ui = null;
  try { ui = await sendToTab({ type: "GET_UI_STATE" }); } catch { /* content script tidak ada */ }
  renderResult(stored, ui);
}

(async function main() {
  // ?tab=<id> hanya untuk pengujian otomatis (popup dibuka sebagai tab biasa)
  const forced = new URLSearchParams(location.search).get("tab");
  if (forced) tab = await chrome.tabs.get(parseInt(forced, 10));
  else [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  settings = await getSettings();
  if (!tab || !tab.url || !/^https?:/i.test(tab.url)) {
    show(msg("Halaman tidak didukung", "Buka situs web biasa, misalnya halaman .ac.id."));
    return;
  }
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "session" && changes[`state_${tab.id}`]) render();
  });
  render();
})();
