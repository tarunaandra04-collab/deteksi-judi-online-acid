"""
engine.py -- inti inferensi Deteksi Judi Online .ac.id (v2)

Prinsip utama: fitur yang dihitung di sini HARUS sama dengan saat training
(lihat docs/LAPORAN_TRAINING_FINAL.md dan scripts_final/03 + 04 di proyek MODELS):

  * Teks      : script/style/komentar dibuang -> lowercase -> hapus simbol/angka
                -> stopword Sastrawi -> stemming Sastrawi -> maks 5000 kata.
  * Struktural: 8 fitur urutan STRUCT_COLS_ORDER, dihitung dari data mentah DOM
                yang dikirim extension (anchor, iframe, atribut hidden, dsb).
  * Flag meta/url memakai LEKSIKON LENGKAP (91 kata, sama dengan main.KEYWORDS
    saat training). model_loader.py versi lama memakai 17 kata saja sehingga
    nilai meta_judi_flag/url_flag bisa melenceng dari distribusi training.

Selain label dari model (ML), engine menghasilkan BUKTI berbasis aturan
(kata kunci utuh, elemen tersembunyi, tautan ke domain bernama judi) untuk
transparansi dan untuk status "waspada" ketika model dan bukti tidak sejalan.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent
MODEL_DIR = BASE / "models"
MAX_WORDS = 5000

with open(BASE / "lexicon.json", encoding="utf-8") as _f:
    LEX = json.load(_f)

KEYWORDS: list[str] = LEX["keywords"]
WEAK: set[str] = set(LEX["weak"])
NAME_TOKENS_MODEL: list[str] = LEX["judi_name_tokens_model"]
NAME_TOKENS_STRICT: list[str] = LEX["judi_name_tokens_strict"]
STRUCT_COLS_ORDER: list[str] = LEX["struct_cols_order"]

_HIDDEN_STYLE_RE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)


def _kw_pattern(words):
    parts = [re.escape(w).replace(r"\ ", r"\s+") for w in sorted(words, key=len, reverse=True)]
    return re.compile(r"(?<![a-z0-9])(" + "|".join(parts) + r")(?![a-z0-9])", re.I)


KW_RE = _kw_pattern(KEYWORDS)

# ---------------------------------------------------------------- model state
_state = {
    "loaded": False,
    "models": {},
    "vectorizer": None,
    "scaler": None,
    "stemmer": None,
    "stopword": None,
    "info": {},
    "feature_names": None,
    "error": None,
}


def load():
    """Muat model sekali saat server start. Aman dipanggil berulang."""
    if _state["loaded"]:
        return _state
    import joblib
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

    try:
        _state["vectorizer"] = joblib.load(MODEL_DIR / "vectorizer.pkl")
        _state["scaler"] = joblib.load(MODEL_DIR / "scaler.pkl")
        _state["models"]["random_forest"] = joblib.load(MODEL_DIR / "model.pkl")
        lgb_path = MODEL_DIR / "model_lightgbm.pkl"
        if lgb_path.exists():
            _state["models"]["lightgbm"] = joblib.load(lgb_path)
        _load_stem_cache()
        _state["stemmer"] = StemmerFactory().create_stemmer()
        _state["stopword"] = StopWordRemoverFactory().create_stop_word_remover()
        info_path = MODEL_DIR / "model_info.json"
        _state["info"] = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}
        _state["feature_names"] = list(_state["vectorizer"].get_feature_names_out())
        _state["loaded"] = True
        _state["error"] = None
        # pemanasan: stemmer & vectorizer lambat pada panggilan pertama (memengaruhi waktu respons TC-06)
        normalize_text("universitas program studi penerimaan mahasiswa baru slot gacor situs resmi berita seminar")
    except Exception as e:  # noqa: BLE001 - dilaporkan lewat /health
        _state["error"] = f"{type(e).__name__}: {e}"
        raise
    return _state


def status() -> dict:
    info = _state["info"] or {}
    return {
        "model_loaded": _state["loaded"],
        "models": sorted(_state["models"]),
        "error": _state["error"],
        "trained_with": info.get("versi", {}),
        "status_label": info.get("status", ""),
        "n_lexicon": len(KEYWORDS),
    }


# ---------------------------------------------------------------- text
_STEM_CACHE: dict[str, str] = {}
_STEM_NEW: dict[str, str] = {}
_STEM_SEED = MODEL_DIR / "stem_cache.json"          # dibangun scripts/build_stem_cache.py (ikut repo)
_STEM_USER = BASE / ".stem_cache_user.json"         # kata baru saat server dipakai (diabaikan git)


def _load_stem_cache():
    """Cache kata->stem. Stemming Sastrawi ~10 ms/kata; tanpa cache, halaman baru bisa >2 detik.
    Isi cache = keluaran stemmer yang sama, jadi prediksi tidak berubah."""
    for f in (_STEM_SEED, _STEM_USER):
        if f.exists():
            try:
                _STEM_CACHE.update(json.loads(f.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass


def _flush_stem_cache():
    try:
        old = {}
        if _STEM_USER.exists():
            old = json.loads(_STEM_USER.read_text(encoding="utf-8"))
        old.update(_STEM_NEW)
        _STEM_USER.write_text(json.dumps(old, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        _STEM_NEW.clear()
    except (OSError, ValueError):
        pass


def _stem(word: str) -> str:
    s = _STEM_CACHE.get(word)
    if s is None:
        s = _state["stemmer"].stem(word)
        _STEM_CACHE[word] = s
        _STEM_NEW[word] = s
        if len(_STEM_NEW) >= 300:
            _flush_stem_cache()
    return s


def normalize_text(text: str) -> str:
    """Replika 03_cleaning_normalisasi.normalize_text (urutan sama)."""
    text = (text or "").lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = _state["stopword"].remove(text)
    return " ".join(_stem(w) for w in text.split()[:MAX_WORDS])


# ---------------------------------------------------------------- structural
def _host(href: str) -> str:
    try:
        return urlparse(href.strip()).netloc.lower().split("@")[-1].split(":")[0]
    except ValueError:
        return ""


def structural_features(data: dict) -> list[float]:
    """Hitung 8 fitur struktural persis seperti 04_fitur_struktural.extract_structural."""
    domain = (data.get("domain") or "").lower()
    url = data.get("url") or ""
    links = data.get("links") or {}
    st = data.get("structural") or {}
    meta = data.get("meta") or {}

    hrefs = links.get("hrefs") or []
    link_count = int(links.get("anchor_count", len(hrefs)))  # semua <a>, bukan hanya yang ber-href
    ext = gamb = 0
    for h in hrefs:
        host = _host(h)
        if not host or host == domain or host.endswith("." + domain):
            continue
        ext += 1
        name_norm = host.replace("-", "").replace(".", "")
        if any(t in name_norm for t in NAME_TOKENS_MODEL):
            gamb += 1
    ext_ratio = ext / link_count if link_count > 0 else 0.0

    meta_text = " ".join([meta.get("keywords") or "", meta.get("description") or ""]).lower()
    meta_flag = int(any(k in meta_text for k in KEYWORDS))
    url_norm = url.lower().replace("-", "").replace("_", "")
    url_flag = int(any(k.replace(" ", "") in url_norm for k in KEYWORDS))

    vals = {
        "FLNK_01_link_count": link_count,
        "FLNK_02_ext_ratio": ext_ratio,
        "FLNK_03_gamb_link": gamb,
        "FSTR_01_iframe_count": int(st.get("iframe_count", 0)),
        "FSTR_02_has_hidden": int(bool(st.get("has_hidden"))),
        "FSTR_03_dom_depth": int(st.get("dom_depth", 0)),
        "FMETA_01_meta_judi_flag": meta_flag,
        "FURL_01_url_flag": url_flag,
    }
    return [vals[c] for c in STRUCT_COLS_ORDER], ext, gamb


# ---------------------------------------------------------------- evidence
def keyword_evidence(text: str, url: str = "") -> dict:
    """Kata kunci utuh (word-boundary) -> hitungan; dipisah kuat/lemah.

    Beda dengan pelabelan training (substring): 'toto' tidak lagi cocok pada
    'fitotoksisitas' atau 'Rusmanto'. Dipakai hanya sebagai bukti tambahan.
    """
    counts: dict[str, int] = {}
    for m in KW_RE.finditer((text or "") + " " + (url or "")):
        k = re.sub(r"\s+", " ", m.group(1).lower())
        counts[k] = counts.get(k, 0) + 1
    strong = {k: v for k, v in counts.items() if k not in WEAK}
    weak = {k: v for k, v in counts.items() if k in WEAK}
    return {
        "strong": dict(sorted(strong.items(), key=lambda x: -x[1])),
        "weak": dict(sorted(weak.items(), key=lambda x: -x[1])),
        "strong_total": sum(strong.values()),
        "weak_total": sum(weak.values()),
    }


def judi_links(hrefs: list[str], domain: str, limit: int = 20) -> list[str]:
    out = []
    for h in hrefs:
        host = _host(h)
        if not host or host == domain or host.endswith("." + domain):
            continue
        name_norm = host.replace("-", "").replace(".", "")
        if any(t in name_norm for t in NAME_TOKENS_STRICT) and host not in out:
            out.append(host)
            if len(out) >= limit:
                break
    return out


def top_terms(model, x_text_row, k: int = 8) -> list[dict]:
    """Istilah TF-IDF paling berpengaruh pada halaman ini = bobot TF-IDF x importance global.
    Bersifat INDIKATIF (bukan atribusi kausal seperti SHAP)."""
    imp = getattr(model, "feature_importances_", None)
    if imp is None:
        return []
    names = _state["feature_names"]
    row = x_text_row.tocoo()
    scored = []
    for j, v in zip(row.col, row.data):
        if j < len(names):
            scored.append((float(v) * float(imp[j]), names[j], float(v)))
    scored.sort(reverse=True)
    return [{"term": t, "weight": round(w, 4), "tfidf": round(v, 3)} for w, t, v in scored[:k] if w > 0]


# ---------------------------------------------------------------- predict
def predict(data: dict, model_name: str = "random_forest", threshold: float = 0.5) -> dict:
    import numpy as np
    import scipy.sparse as sp

    st = load()
    if model_name not in st["models"]:
        model_name = "random_forest"
    model = st["models"][model_name]
    threshold = min(max(float(threshold), 0.05), 0.95)

    t0 = time.perf_counter()
    raw_text = data.get("text") or ""
    clean = normalize_text(raw_text)
    t1 = time.perf_counter()

    X_text = st["vectorizer"].transform([clean])
    struct_raw, ext_count, gamb = structural_features(data)
    struct_scaled = st["scaler"].transform(np.array([struct_raw], dtype=float))
    X = sp.hstack([X_text, sp.csr_matrix(struct_scaled)]).tocsr()
    proba = model.predict_proba(X)[0]
    p_judi = float(proba[1])
    t2 = time.perf_counter()

    kw = keyword_evidence(raw_text, data.get("url", ""))
    hrefs = (data.get("links") or {}).get("hrefs") or []
    jl = judi_links(hrefs, (data.get("domain") or "").lower())
    client_ev = data.get("client_evidence") or {}
    hidden = [h for h in (client_ev.get("hidden") or []) if isinstance(h, dict)][:10]

    reasons: list[str] = []
    ml_judi = p_judi >= threshold
    if ml_judi:
        label = "judi"
        risk = "tinggi" if p_judi >= 0.8 else "sedang"
        reasons.append(f"Model {model_name.replace('_', ' ')} menilai peluang konten judi {p_judi:.0%} (ambang {threshold:.0%}).")
    else:
        label, risk = "aman", "rendah"
        reasons.append(f"Model {model_name.replace('_', ' ')} menilai peluang konten judi hanya {p_judi:.0%} (ambang {threshold:.0%}).")

    if kw["strong_total"]:
        top = ", ".join(f"{k} ({v}x)" for k, v in list(kw["strong"].items())[:4])
        reasons.append(f"Kata kunci judi yang kuat ditemukan: {top}.")
    if kw["weak_total"]:
        top = ", ".join(f"{k} ({v}x)" for k, v in list(kw["weak"].items())[:4])
        reasons.append(f"Kata kunci ambigu (bisa wajar di konteks akademik): {top}.")
    if hidden:
        reasons.append(f"{len(hidden)} elemen tersembunyi memuat kata kunci judi.")
    if jl:
        reasons.append(f"{len(jl)} tautan keluar menuju domain bernama judi: {', '.join(jl[:3])}.")

    if not ml_judi and (kw["strong_total"] or hidden or jl):
        label, risk = "waspada", "perlu-cek"
        reasons.append("Model menilai aman, tetapi ada bukti aturan yang tidak sejalan. Periksa manual.")

    structural = dict(zip(STRUCT_COLS_ORDER, struct_raw))
    return {
        "status": "success",
        "label": label,
        "risk": risk,
        "label_id": 1 if label == "judi" else 0,
        "ml": {
            "model": model_name,
            "p_judi": round(p_judi, 4),
            "p_aman": round(float(proba[0]), 4),
            "threshold": threshold,
            "is_judi": bool(ml_judi),
        },
        "confidence": round(max(p_judi, 1 - p_judi), 4),
        "reasons": reasons,
        "evidence": {
            "keywords_strong": kw["strong"],
            "keywords_weak": kw["weak"],
            "hidden": hidden,
            "judi_links": jl,
            "external_links": ext_count,
        },
        "features": structural,
        "top_terms": top_terms(model, X_text),
        "timing_ms": {
            "preprocess": round((t1 - t0) * 1000, 1),
            "predict": round((t2 - t1) * 1000, 1),
            "total": round((time.perf_counter() - t0) * 1000, 1),
        },
        "n_words_clean": len(clean.split()),
        "model_version": f"{model_name}-final",
    }
