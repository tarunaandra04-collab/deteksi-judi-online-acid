// scanner.js -- ekstraksi data halaman + bukti (dipakai content.js).
// Prinsip: data yang dikirim ke backend harus bisa menghasilkan fitur yang SAMA
// dengan saat training (BeautifulSoup pada HTML mentah):
//   - teks  : semua node teks di <html> (TERMASUK elemen tersembunyi, karena
//             training memakai get_text() pada HTML mentah), tanpa script/style/noscript.
//   - link  : semua <a> dihitung; href mentah (belum di-resolve) dikirim agar
//             host eksternal dihitung backend dengan aturan yang sama.
//   - has_hidden: hanya atribut [hidden] atau style inline display:none / visibility:hidden.
//   - dom_depth : dari <html>, hanya elemen.
(() => {
  if (self.DJO) return;

  const LEX = self.DJO_LEXICON || { keywords: [], weak: [], judi_name_tokens_strict: [] };
  const HOST_ID = "djo-root";
  const MAX_CHARS = 60000;        // ~5000 kata, sama dengan batas MAX_WORDS training
  const MAX_HREFS = 3000;
  const MAX_MARKS = 300;
  const WEAK = new Set(LEX.weak);
  const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"]);
  const HIDDEN_STYLE_RE = /display\s*:\s*none|visibility\s*:\s*hidden/i;

  const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const kwSorted = [...LEX.keywords].sort((a, b) => b.length - a.length);
  const KW_SRC = "(?<![a-z0-9])(" + kwSorted.map((k) => esc(k).replace(/ /g, "\\s+")).join("|") + ")(?![a-z0-9])";
  const newKwRe = () => new RegExp(KW_SRC, "gi");

  const normKw = (s) => s.toLowerCase().replace(/\s+/g, " ");

  function textWalker(root) {
    return document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
      acceptNode(n) {
        if (n.nodeType === 1) {
          if (SKIP_TAGS.has(n.tagName) || n.id === HOST_ID) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_SKIP;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });
  }

  function extractText() {
    const out = [];
    let len = 0;
    const w = textWalker(document.documentElement);
    let n;
    while ((n = w.nextNode())) {
      const v = n.nodeValue.trim();
      if (!v) continue;
      out.push(v);
      len += v.length + 1;
      if (len >= MAX_CHARS) break;
    }
    return out.join(" ").slice(0, MAX_CHARS);
  }

  function domDepth() {
    let best = 1;
    const stack = [[document.documentElement, 1]];
    while (stack.length) {
      const [el, d] = stack.pop();
      if (el.id === HOST_ID) continue;
      if (d > best) best = d;
      for (const c of el.children) stack.push([c, d + 1]);
    }
    return best;
  }

  function structural() {
    let hasHidden = false, hiddenAttr = 0;
    for (const el of document.querySelectorAll("[hidden],[style]")) {
      if (el.closest("#" + HOST_ID)) continue;
      if (el.hasAttribute("hidden") || HIDDEN_STYLE_RE.test(el.getAttribute("style") || "")) {
        hasHidden = true;
        hiddenAttr++;
      }
    }
    return {
      iframe_count: document.getElementsByTagName("iframe").length,
      has_hidden: hasHidden,
      hidden_elements_count: hiddenAttr,
      dom_depth: domDepth(),
    };
  }

  function links() {
    const anchors = Array.from(document.getElementsByTagName("a")).filter((a) => !a.closest("#" + HOST_ID));
    const hrefs = [];
    for (const a of anchors) {
      const h = (a.getAttribute("href") || "").trim();
      if (h && hrefs.length < MAX_HREFS) hrefs.push(h.slice(0, 300));
    }
    return { anchor_count: anchors.length, hrefs };
  }

  function meta() {
    const g = (n) => (document.querySelector(`meta[name="${n}"]`) || {}).content || "";
    return { keywords: g("keywords"), description: g("description") };
  }

  // ---- elemen tersembunyi --------------------------------------------------
  function concealReason(el) {
    // Mengembalikan alasan teks bila elemen (atau leluhurnya) tidak terlihat pengguna, atau null.
    if (!el || !el.isConnected) return null;
    if (el.getClientRects().length === 0) return "display:none / tidak dirender";
    const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.visibility === "collapse") return "visibility:hidden";
    if (parseFloat(cs.fontSize) === 0) return "font-size:0";
    for (let a = el, i = 0; a && a !== document.body && i < 12; a = a.parentElement, i++) {
      if (parseFloat(getComputedStyle(a).opacity) === 0) return "opacity:0";
    }
    const r = el.getBoundingClientRect();
    const sx = window.scrollX, sy = window.scrollY;
    if (r.right + sx <= 0 || r.bottom + sy <= 0) return "di luar layar (posisi negatif)";
    if (r.width <= 1 && r.height <= 1) return "ukuran 0/1px";
    return null;
  }

  // ---- bukti ---------------------------------------------------------------
  function collectEvidence() {
    const re = newKwRe();
    const keywords = {};            // kata -> jumlah
    const nodes = [];               // {node, ranges:[[s,e]], hidden:reason|null}
    const hidden = [];              // sampel elemen tersembunyi
    const seenHiddenEl = new Set();
    const w = textWalker(document.body || document.documentElement);
    let n, total = 0;
    while ((n = w.nextNode())) {
      const v = n.nodeValue;
      if (!v || v.length < 3) continue;
      re.lastIndex = 0;
      const ranges = [];
      let m;
      while ((m = re.exec(v))) {
        ranges.push([m.index, m.index + m[0].length, normKw(m[1])]);
        if (m.index === re.lastIndex) re.lastIndex++;
      }
      if (!ranges.length) continue;
      const parent = n.parentElement;
      const reason = concealReason(parent);
      for (const r of ranges) keywords[r[2]] = (keywords[r[2]] || 0) + 1;
      total += ranges.length;
      nodes.push({ node: n, ranges, hidden: reason });
      if (reason && parent && !seenHiddenEl.has(parent) && hidden.length < 10) {
        seenHiddenEl.add(parent);
        hidden.push({
          reason,
          tag: parent.tagName.toLowerCase(),
          keywords: [...new Set(ranges.map((r) => r[2]))].slice(0, 4),
          snippet: v.trim().replace(/\s+/g, " ").slice(0, 140),
        });
      }
      if (nodes.length >= 800) break;
    }
    return { keywords, nodes, hidden, total };
  }

  function collectLinkEvidence() {
    const domain = location.hostname.toLowerCase();
    const tokens = LEX.judi_name_tokens_strict || [];
    const re = newKwRe();
    const out = [];
    for (const a of document.getElementsByTagName("a")) {
      if (a.closest("#" + HOST_ID)) continue;
      let host = "";
      try { host = new URL(a.href).hostname.toLowerCase(); } catch { continue; }
      if (!host) continue;
      const external = !(host === domain || host.endsWith("." + domain));
      const name = host.replace(/[-.]/g, "");
      const byHost = external && tokens.some((t) => name.includes(t));
      re.lastIndex = 0;
      const byText = re.test((a.textContent || "").slice(0, 200));
      if (byHost || (external && byText)) {
        out.push({ el: a, host, text: (a.textContent || "").trim().slice(0, 80), external, concealed: !!concealReason(a) });
        if (out.length >= 60) break;
      }
    }
    return out;
  }

  // ---- penyorotan ----------------------------------------------------------
  function ensureStyle() {
    if (document.getElementById("djo-style")) return;
    const s = document.createElement("style");
    s.id = "djo-style";
    s.textContent = `
      mark.djo-mark{background:rgba(220,38,38,.18)!important;color:inherit!important;outline:1px solid #dc2626;border-radius:3px;padding:0 1px;}
      mark.djo-mark.djo-weak{background:rgba(217,119,6,.18)!important;outline-color:#d97706;}
      a.djo-link{outline:2px dashed #dc2626!important;outline-offset:2px;}
    `;
    document.documentElement.appendChild(s);
  }

  function highlight(evidence, linkEvidence) {
    clearHighlights();
    ensureStyle();
    let marks = 0;
    for (const item of evidence.nodes) {
      if (marks >= MAX_MARKS) break;
      const node = item.node;
      if (!node.isConnected || item.hidden) continue; // elemen tersembunyi tidak bisa disorot; ditampilkan di panel
      let cur = node;
      const ranges = [...item.ranges].sort((a, b) => b[0] - a[0]);
      for (const [s, e, kw] of ranges) {
        if (marks >= MAX_MARKS) break;
        try {
          const tail = cur.splitText(e);
          const mid = cur.splitText(s);
          const mk = document.createElement("mark");
          mk.className = "djo-mark" + (WEAK.has(kw) ? " djo-weak" : "");
          mk.dataset.djo = "1";
          mk.title = `Kata kunci: ${kw}`;
          mid.parentNode.replaceChild(mk, mid);
          mk.appendChild(mid);
          marks++;
          void tail;
        } catch { /* node berubah di tengah jalan; lewati */ }
      }
    }
    for (const l of linkEvidence) {
      if (l.el.isConnected) {
        l.el.classList.add("djo-link");
        l.el.title = (l.el.title ? l.el.title + " | " : "") + "Tautan keluar ke domain bernama judi (ditandai ekstensi)";
      }
    }
    return marks;
  }

  function clearHighlights() {
    for (const mk of Array.from(document.querySelectorAll("mark.djo-mark"))) {
      const p = mk.parentNode;
      if (!p) continue;
      while (mk.firstChild) p.insertBefore(mk.firstChild, mk);
      p.removeChild(mk);
      p.normalize();
    }
    for (const a of document.querySelectorAll("a.djo-link")) a.classList.remove("djo-link");
  }

  function buildPayload() {
    const ev = collectEvidence();
    const lev = collectLinkEvidence();
    const payload = {
      url: location.href,
      domain: location.hostname.toLowerCase(),
      title: document.title.slice(0, 200),
      text: extractText(),
      links: links(),
      structural: structural(),
      meta: meta(),
      client_evidence: {
        hidden: ev.hidden,
        judi_links: lev.map((l) => ({ host: l.host, text: l.text, concealed: l.concealed })).slice(0, 20),
        keyword_total: ev.total,
      },
    };
    return { payload, ev, lev };
  }

  self.DJO = { buildPayload, highlight, clearHighlights, HOST_ID };
})();
