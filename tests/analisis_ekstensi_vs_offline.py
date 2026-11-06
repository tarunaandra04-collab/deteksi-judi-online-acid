"""
analisis_ekstensi_vs_offline.py -- membandingkan keluaran ekstensi di browser dengan prediksi OFFLINE model
(fitur dari CSV training) untuk halaman yang sama. Selisih = train-serve skew akibat perbedaan cara menghitung
fitur (DOM hidup di browser vs HTML mentah di Python). Keluaran: docs/hasil_uji/ekstensi_vs_offline.json
    python tests/analisis_ekstensi_vs_offline.py "<folder MODELS>"
"""
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
import scipy.sparse as sp

ROOT = Path(__file__).resolve().parent.parent
MODELS = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Andra\PycharmProjects\MODELS")
D = MODELS / "training_final" / "data"
BM = ROOT / "backend" / "models"
STRUCT = json.loads((ROOT / "backend" / "lexicon.json").read_text(encoding="utf-8"))["struct_cols_order"]
vec, sc, rf = joblib.load(BM / "vectorizer.pkl"), joblib.load(BM / "scaler.pkl"), joblib.load(BM / "model.pkl")
df = pd.read_csv(D / "split_train_test_holdout.csv")
df = df.merge(pd.read_csv(D / "teks_bersih.csv", keep_default_na=False)[["path_key", "teks_bersih"]], on="path_key").merge(pd.read_csv(D / "fitur_struktural.csv"), on="path_key")
X = sp.hstack([vec.transform(df.teks_bersih), sp.csr_matrix(sc.transform(df[STRUCT].to_numpy(dtype=float)))]).tocsr()
df["p_offline"] = rf.predict_proba(X)[:, 1]
out = {}
for ch in ("chromium", "msedge"):
    e = pd.read_csv(ROOT / "docs" / "hasil_uji" / f"ekstensi_halaman_nyata_{ch}.csv")
    e = e[e.status == "done"].merge(df[["path_key", "p_offline", "domain"]], left_on="key", right_on="path_key")
    e["selisih"] = (e.p_judi - e.p_offline).abs()
    e["sama_label"] = (e.p_judi >= 0.5) == (e.p_offline >= 0.5)
    out[ch] = {"n": int(len(e)), "label_ml_sama_dengan_offline": int(e.sama_label.sum()),
               "selisih_p_rata2": round(float(e.selisih.mean()), 4), "selisih_p_median": round(float(e.selisih.median()), 4),
               "selisih_p_maks": round(float(e.selisih.max()), 4),
               "beda_label": e[~e.sama_label][["key", "label_benar", "p_judi", "p_offline"]].round(3).to_dict("records"),
               "waspada": e[e.label_ekstensi == "waspada"][["key", "label_benar", "p_judi", "p_offline", "kw_kuat", "hidden"]].round(3).to_dict("records")}
(ROOT / "docs" / "hasil_uji" / "ekstensi_vs_offline.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(out, indent=1, ensure_ascii=True)[:3500])
