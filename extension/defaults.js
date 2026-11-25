// defaults.js -- konfigurasi tetap ekstensi (tanpa halaman pengaturan; ES module untuk background dan popup).
// Nilai dapat diganti lewat chrome.storage.local.settings hanya oleh pengujian otomatis (misalnya alamat server palsu untuk TC-04).
export const DEFAULTS = {
  apiUrl: "http://127.0.0.1:5000",
  model: "random_forest",   // model bawaan; LightGBM tersedia di server untuk pembanding
  threshold: 0.5,           // ambang peluang judi untuk label "judi"
  autoScan: true,           // pindai otomatis di domain .ac.id
  watchChanges: true,       // pindai ulang bila konten halaman berubah (SPA / injeksi dinamis)
  banner: "risk",           // lencana hanya muncul bila ada temuan
  highlight: true,          // sorot kata kunci dan tautan di halaman
};

export async function getSettings() {
  const { settings } = await chrome.storage.local.get("settings");
  return { ...DEFAULTS, ...(settings || {}) };
}

export const isAcId = (host) => /(^|\.)ac\.id$/i.test(host || "");

export const RISK_META = {
  judi:    { badge: "!",  color: "#dc2626" },
  waspada: { badge: "?",  color: "#d97706" },
  aman:    { badge: "OK", color: "#15803d" },
};
