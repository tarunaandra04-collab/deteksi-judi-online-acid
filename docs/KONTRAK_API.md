# Kontrak API (ekstensi ⇄ Flask)

Basis: `http://127.0.0.1:5000`

## `GET /health`
```json
{"status":"ok","model_loaded":true,"models":["lightgbm","random_forest"],"error":null,
 "trained_with":{"python":"3.14.0","sklearn":"1.9.1","numpy":"2.5.4"},"status_label":"FINAL -- ...","n_lexicon":91}
```

## `POST /predict`

Permintaan (dibentuk `scanner.js`):
```json
{
  "url": "https://contoh.ac.id/halaman",
  "domain": "contoh.ac.id",
  "title": "…",
  "text": "semua teks node di <html> kecuali script/style/noscript (termasuk elemen tersembunyi), maks 60.000 karakter",
  "links": {"anchor_count": 120, "hrefs": ["/a", "https://situs-lain.com/x"]},
  "structural": {"iframe_count": 0, "has_hidden": true, "hidden_elements_count": 3, "dom_depth": 17},
  "meta": {"keywords": "", "description": ""},
  "client_evidence": {"hidden": [{"reason":"display:none","tag":"div","keywords":["slot gacor"],"snippet":"…"}],
                      "judi_links": [{"host":"slotgacor.xyz","text":"…","concealed":false}], "keyword_total": 7},
  "options": {"model": "random_forest", "threshold": 0.5}
}
```
Catatan kesesuaian dengan training: `anchor_count` = semua `<a>`; `hrefs` mentah (belum di-resolve) agar host
eksternal dihitung dengan aturan yang sama dengan `04_fitur_struktural.py`; `has_hidden` hanya dari atribut
`hidden` / gaya inline `display:none|visibility:hidden`; `dom_depth` dihitung dari `<html>`.

Respons sukses:
```json
{
  "status": "success",
  "label": "judi | waspada | aman",
  "risk": "tinggi | sedang | perlu-cek | rendah",
  "label_id": 1,
  "ml": {"model":"random_forest","p_judi":0.93,"p_aman":0.07,"threshold":0.5,"is_judi":true},
  "confidence": 0.93,
  "reasons": ["…alasan dalam bahasa Indonesia…"],
  "evidence": {"keywords_strong":{"slot gacor":5},"keywords_weak":{"toto":1},"hidden":[],"judi_links":[],"external_links":12},
  "features": {"FLNK_01_link_count":120, "…": "8 fitur struktural mentah (sebelum scaling)"},
  "top_terms": [{"term":"slot gacor","weight":0.0312,"tfidf":0.85}],
  "timing_ms": {"preprocess":410.2,"predict":6.1,"total":416.3},
  "n_words_clean": 812,
  "model_version": "random_forest-final"
}
```

`label`:
- **judi** — peluang model ≥ ambang.
- **waspada** — model < ambang, tetapi ada kata kunci kuat (kata utuh), elemen tersembunyi bermuatan kata kunci, atau tautan keluar bernama judi.
- **aman** — tidak satu pun di atas.

Galat: `{"status":"error","message":"…"}` dengan kode 400 (payload) atau 500 (inferensi).
