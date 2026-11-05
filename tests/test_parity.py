"""
test_parity.py -- memastikan engine (backend) menghasilkan fitur & prediksi yang SAMA
dengan pipeline training, memakai halaman HTML nyata dari dataset training final.

Butuh (hanya untuk tes ini): beautifulsoup4, pandas  ->  pip install beautifulsoup4 pandas
Jalankan:  python tests/test_parity.py "<folder MODELS>"
"""
import re
import sys
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup, Comment

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import engine  # noqa: E402

MODELS = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Andra\PycharmProjects\MODELS")
D = MODELS / "training_final" / "data"


def html_to_payload(html, domain, url):
    """Meniru apa yang dikirim scanner.js, tetapi dari HTML mentah (untuk tes)."""
    soup = BeautifulSoup(html, "html.parser")
    # struktur dihitung dari DOM penuh (seperti training); hanya TEKS yang membuang noscript/template
    # (di browser dengan JS aktif, isi <noscript> bukan elemen -> tidak terhitung pun sebagai tautan).
    text_soup = BeautifulSoup(html, "html.parser")
    for t in text_soup(["script", "style", "noscript", "template"]):
        t.decompose()
    for c in text_soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    text = text_soup.get_text(separator=" ")
    for t in soup(["script", "style"]):
        t.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    anchors = soup.find_all("a")
    hrefs = [(a.get("href") or "").strip() for a in anchors if (a.get("href") or "").strip()]
    hid = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)
    has_hidden = any(t.has_attr("hidden") or hid.search(t.get("style") or "") for t in soup.find_all(True))

    def depth(n):
        best, st = 1, [(n, 1)]
        while st:
            x, d = st.pop()
            best = max(best, d)
            st += [(c, d + 1) for c in x.children if getattr(c, "name", None)]
        return best

    metas = " ".join((m.get("content") or "") for m in soup.find_all("meta", attrs={"name": re.compile("^(keywords|description)$", re.I)}))
    return {
        "url": url, "domain": domain, "text": text,
        "links": {"anchor_count": len(anchors), "hrefs": hrefs},
        "structural": {"iframe_count": len(soup.find_all("iframe")), "has_hidden": has_hidden, "dom_depth": depth(soup.find("html") or soup)},
        "meta": {"keywords": metas, "description": ""},
    }


def main():
    sp = pd.read_csv(D / "split_train_test_holdout.csv")
    feat = pd.read_csv(D / "fitur_struktural.csv").set_index("path_key")
    txt = pd.read_csv(D / "teks_bersih.csv", keep_default_na=False).set_index("path_key")
    sample = pd.concat([sp[sp.label == 1].sample(25, random_state=1), sp[sp.label == 0].sample(25, random_state=1)])
    engine.load()
    cols = engine.STRUCT_COLS_ORDER
    n = bad_struct = bad_text = bad_label = 0
    maxdiff = 0.0
    for _, r in sample.iterrows():
        try:
            html = open(r.path_abs, encoding="utf-8").read()
        except OSError:
            continue
        # url training = pseudo-url; di extension url asli -> flag url bisa berbeda, jadi pakai pseudo-url utk paritas
        slug = re.sub(r"_[0-9a-f]{10}$", "", Path(r.path_abs).stem)
        url = f"https://{r.domain}/{'' if slug == 'index' else slug}"
        payload = html_to_payload(html, r.domain, url)
        vals, _, _ = engine.structural_features(payload)
        exp = feat.loc[r.path_key, cols].astype(float).tolist()
        if any(abs(a - b) > 1e-9 for a, b in zip(vals, exp)):
            bad_struct += 1
            print("STRUCT beda:", r.path_key, dict(zip(cols, zip(vals, exp))))
        if engine.normalize_text(payload["text"]) != txt.loc[r.path_key, "teks_bersih"]:
            bad_text += 1
        out = engine.predict(payload, "random_forest", 0.5)
        if out["label_id"] != int(out["ml"]["is_judi"]):  # konsistensi internal
            bad_label += 1
        n += 1
    print(f"halaman diuji: {n} | beda fitur struktural: {bad_struct} | beda teks bersih: {bad_text}")
    assert bad_struct == 0, "fitur struktural backend tidak sama dengan training"
    print("PARITAS OK" if bad_text == 0 else "PARITAS STRUKTURAL OK; teks bersih ada selisih kecil (lihat di atas)")


if __name__ == "__main__":
    main()
