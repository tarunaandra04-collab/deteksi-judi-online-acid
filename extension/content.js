// content.js -- berjalan otomatis di .ac.id; di domain lain hanya lewat pemindaian manual (popup).
(() => {
  if (window.__djoLoaded) return;
  window.__djoLoaded = true;

  const isAc = /(^|\.)ac\.id$/i.test(location.hostname);
  const send = (m) => chrome.runtime.sendMessage(m);

  let settings = null;
  let last = null;                 // {result, ev, lev, timing}
  let scanning = false;
  let autoMode = false;
  let observer = null;
  let debounce = null;
  let rescans = 0;
  let lastScanAt = 0;
  let lastSig = null;
  let lastUrl = location.href;
  let highlightOn = true;
  let marksCount = 0;
  let dismissed = false;
  let ui = null;                   // {host, shadow, ...}

  const MAX_RESCANS = 6;
  const MIN_INTERVAL_MS = 8000;

  const whitelisted = (list) => (list || []).some((d) => {
    d = (d || "").trim().toLowerCase();
    return d && (location.hostname === d || location.hostname.endsWith("." + d));
  });

  function signature() {
    const b = document.body;
    return {
      len: b ? b.textContent.length : 0,
      a: document.getElementsByTagName("a").length,
      f: document.getElementsByTagName("iframe").length,
    };
  }
  function changedEnough(a, b) {
    if (!a || !b) return true;
    const rel = Math.abs(a.len - b.len) / Math.max(1, a.len);
    return rel > 0.05 || a.a !== b.a || a.f !== b.f;
  }

  // ---------------------------------------------------------------- scan
  async function scan(trigger) {
    if (scanning) return { ok: false, error: "Pemindaian sedang berjalan" };
    scanning = true;
    stopObserver();
    try {
      window.DJO.clearHighlights();
      const t0 = performance.now();
      const { payload, ev, lev } = window.DJO.buildPayload();
      const clientMs = Math.round(performance.now() - t0);
      payload.trigger = trigger;
      renderPending();
      const resp = await send({ type: "SCAN", payload, clientMs });
      lastScanAt = Date.now();
      lastUrl = location.href;
      if (resp && resp.ok) {
        last = { result: resp.result, ev, lev, timing: resp.timing };
        dismissed = false;
        applyResult();
      } else {
        last = null;
        renderError((resp && resp.error) || "Gagal memindai");
      }
      lastSig = signature();
      return resp;
    } catch (e) {
      renderError(String(e && e.message || e));
      return { ok: false, error: String(e) };
    } finally {
      scanning = false;
      if (autoMode && settings && settings.watchChanges) startObserver();
    }
  }

  function applyResult() {
    const r = last.result;
    marksCount = 0;
    if (settings.highlight && highlightOn && r.label !== "aman") {
      marksCount = window.DJO.highlight(last.ev, last.lev);
    }
    const show = settings.banner === "always" || (settings.banner === "risk" && r.label !== "aman");
    if (show && !dismissed) renderBanner(); else removeUI();
  }

  // ---------------------------------------------------------------- observer
  function startObserver() {
    if (observer || !document.body) return;
    observer = new MutationObserver(() => {
      clearTimeout(debounce);
      debounce = setTimeout(maybeRescan, 3000);
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }
  function stopObserver() {
    if (observer) { observer.disconnect(); observer = null; }
    clearTimeout(debounce);
  }
  function maybeRescan() {
    if (scanning || rescans >= MAX_RESCANS) return;
    const urlChanged = location.href !== lastUrl;
    if (!urlChanged && !changedEnough(lastSig, signature())) return;
    if (Date.now() - lastScanAt < MIN_INTERVAL_MS) {
      debounce = setTimeout(maybeRescan, MIN_INTERVAL_MS);
      return;
    }
    rescans++;
    scan(urlChanged ? "navigasi" : "perubahan");
  }

  // ---------------------------------------------------------------- UI (shadow DOM)
  const CSS = `
    :host{all:initial}
    *{box-sizing:border-box;font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
    .wrap{position:fixed;right:16px;bottom:16px;z-index:2147483647;max-width:360px;font-size:13px;color:#111827}
    .pill{display:flex;align-items:center;gap:8px;padding:9px 14px;border-radius:999px;cursor:pointer;border:0;color:#fff;
      font-weight:600;box-shadow:0 4px 14px rgba(0,0,0,.28);font-size:13px}
    .danger{background:#dc2626}.warn{background:#d97706}.safe{background:#15803d}.err{background:#4b5563}.load{background:#2563eb}
    .panel{background:#fff;border:1px solid #d1d5db;border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.3);padding:14px;margin-bottom:8px;max-height:60vh;overflow:auto}
    .panel h4{margin:0 0 6px;font-size:14px}
    .panel p{margin:4px 0;line-height:1.4}
    .bar{height:8px;background:#e5e7eb;border-radius:4px;overflow:hidden;margin:6px 0 10px}
    .bar>i{display:block;height:100%}
    .chip{display:inline-block;margin:2px 3px 2px 0;padding:2px 8px;border-radius:10px;background:#fee2e2;color:#991b1b;font-size:12px}
    .chip.w{background:#fef3c7;color:#92400e}
    .hid{border-left:3px solid #d97706;padding:3px 8px;margin:4px 0;background:#fffbeb;font-size:12px}
    .row{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}
    .btn{border:1px solid #9ca3af;background:#f9fafb;border-radius:8px;padding:5px 10px;cursor:pointer;font-size:12px;color:#111827}
    .btn:hover{background:#e5e7eb}
    ul{margin:4px 0 4px 16px;padding:0}
    small{color:#6b7280}
  `;

  function el(tag, props = {}, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k === "class") e.className = v;
      else if (k === "style") e.setAttribute("style", v);
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else e[k] = v;
    }
    for (const kid of kids.flat()) if (kid !== null && kid !== undefined) e.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    return e;
  }

  function ensureUI() {
    if (ui && ui.host.isConnected) return ui;
    const host = document.createElement("div");
    host.id = window.DJO.HOST_ID;
    const shadow = host.attachShadow({ mode: "closed" });
    shadow.append(el("style", {}, CSS));
    const wrap = el("div", { class: "wrap" });
    shadow.append(wrap);
    document.documentElement.appendChild(host);
    ui = { host, shadow, wrap, open: false };
    return ui;
  }
  function removeUI() {
    if (ui) { ui.host.remove(); ui = null; }
  }

  function pill(cls, text) {
    return el("button", { class: "pill " + cls, title: "Klik untuk detail", onclick: () => { ensureUI().open = !ui.open; renderBanner(); } }, "🛡 ", text);
  }
  function renderPending() {
    if (!settings || settings.banner === "never") return;
    if (!ui) return; // jangan memunculkan UI baru saat pemindaian otomatis pertama
    ui.wrap.replaceChildren(el("button", { class: "pill load" }, "🛡 Memindai ulang…"));
  }
  function renderError(msg) {
    if (!settings || settings.banner === "never") return;
    if (!ui && !(trigger_manual)) return; // galat saat auto-scan dibiarkan senyap; status ada di popup
    const u = ensureUI();
    u.wrap.replaceChildren(
      u.open ? el("div", { class: "panel" }, el("h4", {}, "Pemindaian gagal"), el("p", {}, msg),
        el("div", { class: "row" }, el("button", { class: "btn", onclick: () => scan("manual") }, "Coba lagi"))) : null,
      pill("err", "Deteksi judi: tidak terhubung"),
    );
  }
  let trigger_manual = false;

  function renderBanner() {
    if (!last) return;
    const r = last.result;
    const u = ensureUI();
    const cls = r.label === "judi" ? "danger" : r.label === "waspada" ? "warn" : "safe";
    const title = r.label === "judi" ? "Terindikasi konten judi" : r.label === "waspada" ? "Waspada: perlu dicek" : "Aman";
    const p = Math.round(r.ml.p_judi * 100);
    const kids = [];
    if (u.open) {
      const strong = Object.entries(r.evidence.keywords_strong || {});
      const weak = Object.entries(r.evidence.keywords_weak || {});
      const color = r.label === "judi" ? "#dc2626" : r.label === "waspada" ? "#d97706" : "#15803d";
      kids.push(el("div", { class: "panel" },
        el("h4", {}, title),
        el("small", {}, `Peluang judi (model ${r.ml.model.replace("_", " ")}): ${p}% · ambang ${Math.round(r.ml.threshold * 100)}%`),
        el("div", { class: "bar" }, el("i", { style: `width:${p}%;background:${color}` })),
        ...r.reasons.map((t) => el("p", {}, "• ", t)),
        strong.length ? el("p", {}, strong.slice(0, 8).map(([k, v]) => el("span", { class: "chip" }, `${k} ×${v}`))) : null,
        weak.length ? el("p", {}, weak.slice(0, 6).map(([k, v]) => el("span", { class: "chip w" }, `${k} ×${v}`))) : null,
        (r.evidence.hidden || []).length ? el("div", {}, el("p", {}, el("b", {}, "Elemen tersembunyi:")),
          ...r.evidence.hidden.slice(0, 4).map((h) => el("div", { class: "hid" }, `<${h.tag}> ${h.reason} — “${h.snippet}”`))) : null,
        (r.evidence.judi_links || []).length ? el("p", {}, el("b", {}, "Tautan keluar mencurigakan: "), r.evidence.judi_links.slice(0, 4).join(", ")) : null,
        el("small", {}, `Sorotan di halaman: ${marksCount} · analisis ${r.timing_ms.total} ms`),
        el("div", { class: "row" },
          el("button", { class: "btn", onclick: toggleHighlight }, highlightOn ? "Matikan sorotan" : "Tampilkan sorotan"),
          el("button", { class: "btn", onclick: () => scan("manual") }, "Pindai ulang"),
          el("button", { class: "btn", onclick: () => { dismissed = true; removeUI(); } }, "Tutup"),
        ),
      ));
    }
    kids.push(pill(cls, `${title} · ${p}%`));
    u.wrap.replaceChildren(...kids);
  }

  function toggleHighlight() {
    highlightOn = !highlightOn;
    if (!highlightOn) { window.DJO.clearHighlights(); marksCount = 0; }
    else if (last) { stopObserver(); marksCount = window.DJO.highlight(last.ev, last.lev); if (autoMode && settings.watchChanges) startObserver(); }
    if (ui) renderBanner();
  }

  // ---------------------------------------------------------------- pesan dari popup
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (!msg) return false;
    if (msg.type === "RESCAN") {
      trigger_manual = true;
      (async () => {
        if (!settings) settings = await send({ type: "GET_SETTINGS" });
        sendResponse(await scan(msg.manual ? "manual" : "popup"));
      })();
      return true;
    }
    if (msg.type === "TOGGLE_HIGHLIGHT") {
      toggleHighlight();
      sendResponse({ highlightOn, marks: marksCount });
      return false;
    }
    if (msg.type === "GET_UI_STATE") {
      sendResponse({ highlightOn, marks: marksCount, scanned: !!last, ac: isAc });
      return false;
    }
    return false;
  });

  // ---------------------------------------------------------------- init
  (async () => {
    try {
      settings = await send({ type: "GET_SETTINGS" });
    } catch { return; }
    highlightOn = !!settings.highlight;
    if (isAc && settings.autoScan && !whitelisted(settings.whitelist)) {
      autoMode = true;
      const go = () => setTimeout(() => scan("load").then(() => { if (settings.watchChanges) startObserver(); }), 400);
      if (document.readyState === "complete") go(); else window.addEventListener("load", go, { once: true });
      window.addEventListener("popstate", () => { clearTimeout(debounce); debounce = setTimeout(maybeRescan, 1200); });
    }
  })();
})();
