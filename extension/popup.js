import { getSettings, isAcId, isWhitelisted } from "./defaults.js";

const root = document.getElementById("content");
let tab = null;
let settings = null;

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
const status = (cls, title, sub) => h("div", { class: "status " + cls }, h("div", { class: "t" }, title), sub ? h("div", { class: "s" }, sub) : null);

document.getElementById("openOptions").addEventListener("click", () => chrome.runtime.openOptionsPage());

async function sendToTab(msg) {
  return chrome.tabs.sendMessage(tab.id, msg);
}

async function manualScan() {
  show(status("info", "Memindai…", "Mengambil data halaman dan menghubungi server lokal."));
  try {
    try {
      await sendToTab({ type: "GET_UI_STATE" });
    } catch {
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["lexicon.js", "scanner.js", "content.js"] });
    }
    await sendToTab({ type: "RESCAN", manual: true });
  } catch (e) {
    show(status("neutral", "Halaman ini tidak bisa dipindai", "Ekstensi tidak dapat berjalan di halaman khusus browser (edge://, Web Store, PDF viewer, dsb)."),
      h("div", { class: "footnote" }, String(e.message || e)));
  }
}

function reportText(rec) {
  const r = rec.result;
  const lines = [
    "LAPORAN DETEKSI KONTEN JUDI ONLINE",
    `Halaman : ${rec.url}`,
    `Waktu   : ${new Date(rec.at).toLocaleString("id-ID")}`,
    `Hasil   : ${r.label.toUpperCase()} (peluang judi ${(r.ml.p_judi * 100).toFixed(1)}%, model ${r.ml.model}, ambang ${r.ml.threshold})`,
    "",
    "Alasan:",
    ...r.reasons.map((x) => " - " + x),
  ];
  const kw = Object.entries(r.evidence.keywords_strong || {}).map(([k, v]) => `${k} x${v}`).join(", ");
  if (kw) lines.push("", "Kata kunci kuat: " + kw);
  if ((r.evidence.hidden || []).length) {
    lines.push("", "Elemen tersembunyi:");
    r.evidence.hidden.forEach((x) => lines.push(` - <${x.tag}> ${x.reason}: "${x.snippet}"`));
  }
  if ((r.evidence.judi_links || []).length) lines.push("", "Tautan keluar mencurigakan: " + r.evidence.judi_links.join(", "));
  lines.push("", "Catatan: ini hasil prediksi model (prototipe skripsi), bukan keputusan akhir. Mohon verifikasi manual.");
  return lines.join("\n");
}

function renderResult(rec, uiState) {
  const r = rec.result;
  const cls = r.label === "judi" ? "danger" : r.label === "waspada" ? "warn" : "safe";
  const title = r.label === "judi" ? "⚠ Terindikasi konten judi" : r.label === "waspada" ? "Waspada — perlu dicek" : "✓ Aman";
  const sub = r.label === "judi" ? "Model menilai halaman ini memuat konten judi online."
    : r.label === "waspada" ? "Model menilai aman, tetapi ada bukti aturan yang perlu diperiksa."
    : "Tidak ada indikasi konten judi online yang cukup kuat.";
  const p = r.ml.p_judi * 100;
  const strong = Object.entries(r.evidence.keywords_strong || {});
  const weak = Object.entries(r.evidence.keywords_weak || {});
  const f = r.features;
  const tm = rec.timing || {};

  const hl = uiState && uiState.ac !== false;
  const nodes = [
    h("div", { class: "host" }, new URL(rec.url).hostname),
    status(cls, title, sub),
    h("div", { class: "meter-label" }, h("span", {}, "Peluang konten judi"), h("span", {}, p.toFixed(1) + "%")),
    h("div", { class: "meter " + cls }, h("i", { style: `width:${Math.max(2, p)}%` }), h("span", { class: "thr", style: `left:${r.ml.threshold * 100}%`, title: "Ambang keputusan" })),
    h("h3", {}, "Mengapa hasilnya begini"),
    h("ul", { class: "reasons" }, r.reasons.map((x) => h("li", {}, x))),
  ];

  if (strong.length || weak.length) {
    nodes.push(h("h3", {}, "Kata kunci ditemukan"),
      h("div", { class: "chips" }, strong.slice(0, 10).map(([k, v]) => h("span", { class: "chip" }, `${k} ×${v}`)),
        weak.slice(0, 6).map(([k, v]) => h("span", { class: "chip weak", title: "Kata ambigu" }, `${k} ×${v}`))));
  }
  if ((r.evidence.hidden || []).length) {
    nodes.push(h("h3", {}, "Elemen tersembunyi memuat kata kunci"),
      r.evidence.hidden.slice(0, 4).map((x) => h("div", { class: "hid" }, `<${x.tag}> · ${x.reason}`, h("br"), `“${x.snippet}”`)));
  }
  if ((r.evidence.judi_links || []).length) {
    nodes.push(h("h3", {}, "Tautan keluar bernama judi"), h("div", { class: "chips" }, r.evidence.judi_links.slice(0, 6).map((x) => h("span", { class: "chip" }, x))));
  }
  if ((r.top_terms || []).length) {
    nodes.push(h("h3", {}, "Istilah yang paling memengaruhi model"),
      h("div", { class: "chips" }, r.top_terms.slice(0, 8).map((t) => h("span", { class: "chip term", title: `bobot TF-IDF ${t.tfidf}` }, t.term))));
  }

  nodes.push(h("h3", {}, "Struktur halaman"),
    h("div", { class: "grid" },
      stat(f.FLNK_01_link_count, "tautan"), stat(Math.round(f.FLNK_02_ext_ratio * 100) + "%", "tautan keluar"),
      stat(f.FLNK_03_gamb_link, "tautan nama judi (model)"), stat(f.FSTR_01_iframe_count, "iframe"),
      stat(f.FSTR_02_has_hidden ? "Ya" : "Tidak", "atribut/gaya tersembunyi"), stat(f.FSTR_03_dom_depth, "kedalaman DOM")));

  nodes.push(h("div", { class: "buttons" },
    h("button", { class: "btn primary", onclick: () => rescan() }, "Pindai ulang"),
    uiState && uiState.scanned ? h("button", { class: "btn", onclick: toggleHighlight }, uiState.highlightOn ? "Matikan sorotan" : "Tampilkan sorotan") : null,
    h("button", { class: "btn", onclick: async (e) => {
      try { await navigator.clipboard.writeText(reportText(rec)); e.target.textContent = "Laporan disalin ✓"; } catch { e.target.textContent = "Gagal menyalin"; }
    } }, "Salin laporan"),
  ));

  nodes.push(h("details", {}, h("summary", {}, "Detail teknis"),
    h("table", { class: "mini" },
      row("Model", r.ml.model.replace("_", " ")), row("Ambang", r.ml.threshold),
      row("Kata setelah preprocessing", r.n_words_clean),
      row("Ekstraksi di halaman", (tm.client_extract ?? "–") + " ms"),
      row("Preprocess + prediksi server", r.timing_ms.total + " ms"),
      row("Bolak-balik ke server", (tm.api_roundtrip ?? "–") + " ms"),
      row("Total end-to-end", (tm.end_to_end ?? "–") + " ms"),
      row("Pemicu", rec.trigger))));
  nodes.push(h("div", { class: "footnote" }, "Prototipe skripsi. Label model dilatih dari kata kunci (Layer 1); hasil adalah indikasi awal, bukan vonis."));
  show(...nodes);
  void hl;
}
const stat = (v, label) => h("div", { class: "stat" }, h("b", {}, v), h("span", {}, label));
const row = (k, v) => h("tr", {}, h("td", {}, k), h("td", {}, String(v)));

async function rescan() {
  show(status("info", "Memindai ulang…"));
  try { await sendToTab({ type: "RESCAN" }); } catch { await manualScan(); }
}
async function toggleHighlight() {
  try { await sendToTab({ type: "TOGGLE_HIGHLIGHT" }); } catch { /* abaikan */ }
  render();
}

async function render() {
  const key = `state_${tab.id}`;
  const stored = (await chrome.storage.session.get(key))[key];
  let host = "";
  try { host = new URL(tab.url).hostname; } catch { /* url khusus */ }
  const ac = isAcId(host);

  if (!stored || stored.url !== tab.url) {
    if (ac && settings.autoScan && !isWhitelisted(host, settings.whitelist)) {
      show(status("info", "Menunggu pemindaian…", "Halaman sedang dimuat atau belum selesai dipindai."),
        h("div", { class: "buttons" }, h("button", { class: "btn primary", onclick: manualScan }, "Pindai sekarang")));
      return;
    }
    show(
      status("neutral", ac ? "Pemindaian otomatis nonaktif" : "Di luar domain .ac.id",
        ac ? "Domain ini dikecualikan atau pemindaian otomatis dimatikan di Pengaturan." : "Ekstensi aktif otomatis hanya di .ac.id. Kamu bisa memindai halaman ini secara manual."),
      h("div", { class: "buttons" }, h("button", { class: "btn primary", onclick: manualScan }, "Pindai halaman ini")),
      h("div", { class: "footnote" }, "Mode manual memakai izin activeTab: hanya berlaku untuk tab ini, saat kamu menekan tombol."));
    return;
  }
  if (stored.status === "loading") { show(status("info", "Menganalisis halaman…", "Menghubungi server lokal.")); return; }
  if (stored.status === "error") {
    show(status("neutral", "Tidak bisa menganalisis", stored.error),
      h("div", { class: "buttons" }, h("button", { class: "btn primary", onclick: rescan }, "Coba lagi"),
        h("button", { class: "btn", onclick: () => chrome.runtime.openOptionsPage() }, "Cek pengaturan server")));
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
    show(status("neutral", "Halaman tidak didukung", "Buka situs web biasa (http/https), misalnya halaman .ac.id."));
    return;
  }
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "session" && changes[`state_${tab.id}`]) render();
  });
  render();
})();
