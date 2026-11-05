// background.js (service worker, ES module)
// Menjembatani content.js dengan Flask API lokal, mengatur badge ikon, dan menyimpan riwayat.
import { getSettings, RISK_META } from "./defaults.js";

const FETCH_TIMEOUT_MS = 25000;

async function setBadge(tabId, text, color) {
  if (tabId === undefined) return;
  try {
    await chrome.action.setBadgeText({ tabId, text });
    if (color) await chrome.action.setBadgeBackgroundColor({ tabId, color });
  } catch { /* tab mungkin sudah ditutup */ }
}

async function pushHistory(entry, max) {
  const { history = [] } = await chrome.storage.local.get("history");
  history.unshift(entry);
  await chrome.storage.local.set({ history: history.slice(0, max) });
}

async function handleScan(msg, sender) {
  const tabId = sender.tab && sender.tab.id;
  const settings = await getSettings();
  const t0 = performance.now();
  await chrome.storage.session.set({ [`state_${tabId}`]: { status: "loading", url: msg.payload.url, at: Date.now() } });
  await setBadge(tabId, "…", "#2563eb");

  const body = { ...msg.payload, options: { model: settings.model, threshold: settings.threshold } };
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  try {
    const t1 = performance.now();
    const res = await fetch(`${settings.apiUrl.replace(/\/+$/, "")}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });
    const json = await res.json().catch(() => ({}));
    if (!res.ok || json.status !== "success") throw new Error(json.message || `API membalas status ${res.status}`);
    const apiMs = Math.round(performance.now() - t1);
    const totalMs = Math.round((performance.now() - t0) + (msg.clientMs || 0));

    const record = {
      status: "done",
      url: msg.payload.url,
      title: msg.payload.title || "",
      at: Date.now(),
      trigger: msg.payload.trigger || "load",
      result: json,
      timing: { client_extract: msg.clientMs || 0, api_roundtrip: apiMs, end_to_end: totalMs },
    };
    await chrome.storage.session.set({ [`state_${tabId}`]: record });
    const meta = RISK_META[json.label] || RISK_META.aman;
    await setBadge(tabId, meta.badge, meta.color);

    if (settings.saveHistory) {
      await pushHistory({
        t: record.at,
        url: record.url,
        host: msg.payload.domain,
        label: json.label,
        risk: json.risk,
        p_judi: json.ml.p_judi,
        model: json.ml.model,
        kw_strong: Object.values(json.evidence.keywords_strong || {}).reduce((a, b) => a + b, 0),
        hidden: (json.evidence.hidden || []).length,
        judi_links: (json.evidence.judi_links || []).length,
        ms_api: json.timing_ms.total,
        ms_e2e: totalMs,
        trigger: record.trigger,
      }, settings.historyMax);
    }
    return { ok: true, result: json, timing: record.timing };
  } catch (err) {
    const message = err.name === "AbortError"
      ? "Server tidak merespons (timeout). Pastikan backend berjalan."
      : (err.message === "Failed to fetch"
          ? "Tidak bisa terhubung ke server lokal. Jalankan jalankan.ps1 (atau python backend/app.py)."
          : err.message);
    await chrome.storage.session.set({ [`state_${tabId}`]: { status: "error", url: msg.payload.url, at: Date.now(), error: message } });
    await setBadge(tabId, "×", "#6b7280");
    return { ok: false, error: message };
  } finally {
    clearTimeout(timer);
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "GET_SETTINGS") {
    getSettings().then(sendResponse);
    return true;
  }
  if (msg && msg.type === "SCAN" && sender.tab) {
    handleScan(msg, sender).then(sendResponse);
    return true;
  }
  return false;
});

chrome.tabs.onRemoved.addListener((tabId) => {
  chrome.storage.session.remove(`state_${tabId}`);
});
