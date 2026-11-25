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
      const resp = await send({ type: "SCAN", payload, clientMs, client: ev.visible });
      lastScanAt = Date.now();
      lastUrl = location.href;
      if (resp && resp.ok) {
        last = { result: resp.result, ev, lev, timing: resp.timing, client: ev.visible };
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
    const show = r.label !== "aman";
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
    .wrap{position:fixed;right:16px;bottom:16px;z-index:2147483647;width:300px;font-size:14px;color:#111827;display:flex;flex-direction:column;align-items:flex-end;gap:8px}
    .dot{width:48px;height:48px;border-radius:50%;border:0;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 12px rgba(0,0,0,.3)}
    .dot.danger{background:#dc2626;box-shadow:0 0 0 5px #dc262644,0 3px 12px rgba(0,0,0,.3)}
    .dot.warn{background:#f59e0b;box-shadow:0 0 0 5px #f59e0b44,0 3px 12px rgba(0,0,0,.3)}
    .dot.err{background:#6b7280}.dot.load{background:#2563eb}
    .panel{width:100%;background:#fff;border:1px solid #e5e7eb;border-radius:14px;box-shadow:0 8px 28px rgba(0,0,0,.3);padding:14px 16px}
    .word{font-size:19px;font-weight:800;letter-spacing:.03em}
    .sent{color:#374151;margin:2px 0 8px}
    .chk{display:flex;align-items:center;gap:9px;padding:7px 0;border-top:1px solid #e5e7eb}
    .chk i{width:22px;height:22px;border-radius:50%;color:#fff;font-style:normal;font-weight:800;font-size:12px;display:flex;align-items:center;justify-content:center;flex:none}
    .chk span{flex:1}.chk b{font-weight:700}
    .row{display:flex;gap:8px;margin-top:10px}
    .btn{flex:1;border:1px solid #d1d5db;background:#fff;border-radius:9px;padding:8px 10px;cursor:pointer;font-size:13px;font-weight:600;color:#111827}
    .btn.p{background:#0f766e;border-color:#0f766e;color:#fff}
    .note{margin-top:8px;color:#6b7280;font-size:11.5px}
  `;
  const COL = ["#15803d", "#b45309", "#dc2626"];
  const SHIELD_SVG = '<svg width="26" height="26" viewBox="0 0 24 24"><path fill="#fff" d="M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5z"/><path d="M12 7v6M12 16v.5" stroke="COLOR" stroke-width="2.4" fill="none" stroke-linecap="round"/></svg>';

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

  function dot(cls, title, color) {
    const b = el("button", { class: "dot " + cls, title, "aria-label": title, onclick: () => { ensureUI().open = !ui.open; renderBanner(); } });
    b.innerHTML = SHIELD_SVG.replace("COLOR", color || "#6b7280");
    return b;
  }
  function renderPending() {
    if (!settings || settings.banner === "never") return;
    if (!ui) return; // jangan memunculkan UI baru saat pemindaian otomatis pertama
    ui.wrap.replaceChildren(dot("load", "Memeriksa ulang…", "#2563eb"));
  }
  function renderError(msg) {
    if (!settings || settings.banner === "never") return;
    if (!ui && !(trigger_manual)) return; // galat saat auto-scan dibiarkan senyap; status ada di popup
    const u = ensureUI();
    u.wrap.replaceChildren(
      u.open ? el("div", { class: "panel" }, el("div", { class: "word", style: "color:#4b5563" }, "Tidak bisa memeriksa"), el("p", {}, msg),
        el("div", { class: "row" }, el("button", { class: "btn p", onclick: () => scan("manual") }, "Coba lagi"))) : null,
      dot("err", "Tidak terhubung ke server", "#6b7280"),
    );
  }
  let trigger_manual = false;

  function renderBanner() {
    if (!last) return;
    const u = ensureUI();
    const sm = window.DJOSUM.summarize({ result: last.result, client: last.client });
    const cls = sm.lvl === 2 ? "danger" : "warn";
    const kids = [];
    if (u.open) {
      kids.push(el("div", { class: "panel" },
        el("div", { class: "word", style: `color:${sm.color}` }, sm.word),
        el("div", { class: "sent" }, sm.sentence),
        ...sm.rows.map((x) => el("div", { class: "chk" }, el("i", { style: `background:${COL[x.level]}` }, ["✓", "!", "✕"][x.level]), el("span", {}, x.name), el("b", { style: `color:${COL[x.level]}` }, x.text))),
        el("div", { class: "row" },
          el("button", { class: "btn p", onclick: toggleHighlight }, highlightOn ? "Sembunyikan tanda" : "Lihat di halaman"),
          el("button", { class: "btn", onclick: () => { dismissed = true; removeUI(); } }, "Tutup")),
        el("div", { class: "note" }, "Hasil ini perkiraan komputer, bukan keputusan akhir."),
      ));
    }
    kids.push(dot(cls, `${sm.word} — klik untuk detail`, sm.color));
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
    if (isAc && settings.autoScan) {
      autoMode = true;
      const go = () => setTimeout(() => scan("load").then(() => { if (settings.watchChanges) startObserver(); }), 400);
      if (document.readyState === "complete") go(); else window.addEventListener("load", go, { once: true });
      window.addEventListener("popstate", () => { clearTimeout(debounce); debounce = setTimeout(maybeRescan, 1200); });
    }
  })();
})();
