// defaults.js -- pengaturan bawaan + helper (ES module; dipakai background, popup, options).
export const DEFAULTS = {
  apiUrl: "http://127.0.0.1:5000",
  model: "random_forest",   // random_forest | lightgbm
  threshold: 0.5,           // ambang peluang judi untuk label "judi"
  autoScan: true,           // pindai otomatis di domain .ac.id
  watchChanges: true,       // pindai ulang bila konten halaman berubah (SPA / injeksi dinamis)
  banner: "risk",           // risk = hanya bila ada temuan | always | never
  highlight: true,          // sorot kata kunci & tautan di halaman
  saveHistory: true,        // simpan riwayat (tanpa isi halaman) di perangkat ini
  whitelist: [],            // domain yang tidak dipindai otomatis
  historyMax: 300,
};

export async function getSettings() {
  const { settings } = await chrome.storage.local.get("settings");
  return { ...DEFAULTS, ...(settings || {}) };
}

export async function saveSettings(patch) {
  const cur = await getSettings();
  const next = { ...cur, ...patch };
  await chrome.storage.local.set({ settings: next });
  return next;
}

export const isAcId = (host) => /(^|\.)ac\.id$/i.test(host || "");

export function isWhitelisted(host, list) {
  host = (host || "").toLowerCase();
  return (list || []).some((d) => {
    d = (d || "").trim().toLowerCase();
    return d && (host === d || host.endsWith("." + d));
  });
}

export const RISK_META = {
  judi:    { text: "Terindikasi konten judi", badge: "!",  color: "#dc2626", cls: "danger" },
  waspada: { text: "Waspada — perlu dicek",   badge: "?",  color: "#d97706", cls: "warn" },
  aman:    { text: "Aman",                    badge: "OK", color: "#15803d", cls: "safe" },
};
