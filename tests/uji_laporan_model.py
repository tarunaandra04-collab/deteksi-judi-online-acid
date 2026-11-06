"""
uji_laporan_model.py -- menjalankan skenario Tabel 3.15 (TC-01..TC-06) dengan model yang BENAR-BENAR dipasang
di repo (backend/models), lalu menulis docs/hasil_uji/hasil_model.json untuk laporan.

Prasyarat: server hidup (jalankan.ps1 -NoBrowser); paket: pandas, scikit-learn, scipy, lightgbm, beautifulsoup4.
    python tests/uji_laporan_model.py "<folder MODELS>"
"""
import hashlib
import json
import math
import statistics
import sys
import time
import urllib.request
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.stats import binomtest, fisher_exact
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend"))
MODELS = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Andra\PycharmProjects\MODELS")
sys.argv = sys.argv[:1] + [str(MODELS)]
from test_parity import html_to_payload  # noqa: E402

OUT = ROOT / "docs" / "hasil_uji"
OUT.mkdir(parents=True, exist_ok=True)
D = MODELS / "training_final" / "data"
BM = ROOT / "backend" / "models"
STRUCT = json.loads((ROOT / "backend" / "lexicon.json").read_text(encoding="utf-8"))["struct_cols_order"]
API = "http://127.0.0.1:5000/predict"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))


def metrics(y, pred, proba):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "n": int(len(y)), "n_judi": int(sum(y)),
        "accuracy": round(accuracy_score(y, pred), 4),
        "precision": round(precision_score(y, pred, zero_division=0), 4),
        "recall": round(recall_score(y, pred, zero_division=0), 4),
        "f1": round(f1_score(y, pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y, proba), 4) if len(set(y)) == 2 else None,
        "fpr": round(fp / (fp + tn), 4) if (fp + tn) else None,
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def main():
    res = {"dibuat": time.strftime("%Y-%m-%d %H:%M:%S")}

    # ---- integritas model yang dipasang == model hasil training -----------------------------
    same = {}
    for f in ("model.pkl", "model_lightgbm.pkl", "vectorizer.pkl", "scaler.pkl"):
        same[f] = {"repo": sha(BM / f), "training_final": sha(MODELS / "training_final" / "model" / f)}
        same[f]["identik"] = same[f]["repo"] == same[f]["training_final"]
    res["integritas_model"] = same

    vec, scaler = joblib.load(BM / "vectorizer.pkl"), joblib.load(BM / "scaler.pkl")
    models = {"random_forest": joblib.load(BM / "model.pkl"), "lightgbm": joblib.load(BM / "model_lightgbm.pkl")}

    df = pd.read_csv(D / "split_train_test_holdout.csv")
    df = df.merge(pd.read_csv(D / "teks_bersih.csv", keep_default_na=False)[["path_key", "teks_bersih"]], on="path_key")
    df = df.merge(pd.read_csv(D / "fitur_struktural.csv"), on="path_key")

    def X_of(d):
        return sp.hstack([vec.transform(d["teks_bersih"]), sp.csr_matrix(scaler.transform(d[STRUCT].to_numpy(dtype=float)))]).tocsr()

    res["data"] = {s: {"halaman": int((df.split == s).sum()), "judi": int(((df.split == s) & (df.label == 1)).sum()),
                       "normal": int(((df.split == s) & (df.label == 0)).sum()), "domain": int(df[df.split == s].domain.nunique())}
                   for s in ("train", "test", "holdout")}

    # ---- TC-01, TC-02, TC-03 ------------------------------------------------------------------
    pred, proba = {}, {}
    res["tc01_02_03"] = {}
    for name, m in models.items():
        res["tc01_02_03"][name] = {}
        for s in ("test", "holdout"):
            d = df[df.split == s].reset_index(drop=True)
            X = X_of(d)
            p = m.predict_proba(X)[:, 1]
            yhat = (p >= 0.5).astype(int)  # sama dengan ambang bawaan ekstensi
            pred[(name, s)], proba[(name, s)] = yhat, p
            res["tc01_02_03"][name][s] = metrics(d.label.to_numpy(), yhat, p)

    # reproduksi angka laporan training
    rep = json.loads((MODELS / "training_final" / "hasil_evaluasi" / "metrik_ringkas.json").read_text(encoding="utf-8"))
    cocok = True
    for name in models:
        for s in ("test", "holdout"):
            a, b = res["tc01_02_03"][name][s], rep[name][s]
            for k_mine, k_rep in (("accuracy", "accuracy"), ("precision", "precision_judi"), ("recall", "recall_judi"), ("f1", "f1_judi")):
                if abs(a[k_mine] - round(b[k_rep], 4)) > 1e-4:
                    cocok = False
            if (a["tn"], a["fp"], a["fn"], a["tp"]) != (b["tn"], b["fp"], b["fn"], b["tp"]):
                cocok = False
    res["reproduksi_laporan_training"] = cocok

    # ---- TC-04 McNemar eksak ----------------------------------------------------------------
    res["tc04_mcnemar"] = {}
    for s in ("test", "holdout"):
        d = df[df.split == s].reset_index(drop=True)
        y = d.label.to_numpy()
        rf_ok = pred[("random_forest", s)] == y
        lg_ok = pred[("lightgbm", s)] == y
        b = int((rf_ok & ~lg_ok).sum())
        c = int((~rf_ok & lg_ok).sum())
        p = 1.0 if b + c == 0 else float(binomtest(min(b, c), b + c, 0.5).pvalue * (1 if min(b, c) * 2 == b + c else 1))
        p = min(1.0, p) if b + c else 1.0
        # p dua sisi eksak = 2 * P(X <= min) ; binomtest(alternative='two-sided') sudah melakukannya
        p = float(binomtest(b, b + c, 0.5).pvalue) if b + c else 1.0
        res["tc04_mcnemar"][s] = {"a_kedua_benar": int((rf_ok & lg_ok).sum()), "b_rf_benar_lgbm_salah": b,
                                  "c_rf_salah_lgbm_benar": c, "e_kedua_salah": int((~rf_ok & ~lg_ok).sum()),
                                  "p_value": round(p, 4), "bermakna_alpha_005": bool(p < 0.05)}

    # ---- TC-06 independent validation set (non-dork) -----------------------------------------
    res["tc06_nondork"] = {}
    for name in models:
        t = df[df.split == "test"].reset_index(drop=True)
        h = df[df.split == "holdout"].reset_index(drop=True)
        yt, yh = t.label.to_numpy(), h.label.to_numpy()
        pt, ph = pred[(name, "test")], pred[(name, "holdout")]
        nd_t = (t.label == 1) & (t.nondork == 1)
        rg_t = (t.label == 1) & (t.nondork == 0)
        nd_h = (h.label == 1) & (h.nondork == 1)
        nd_tp = int(pt[nd_t.to_numpy()].sum()); nd_n = int(nd_t.sum())
        rg_tp = int(pt[rg_t.to_numpy()].sum()); rg_n = int(rg_t.sum())
        ndh_tp = int(ph[nd_h.to_numpy()].sum()); ndh_n = int(nd_h.sum())
        pool_tp, pool_n = nd_tp + ndh_tp, nd_n + ndh_n
        fisher_test = fisher_exact([[nd_tp, nd_n - nd_tp], [rg_tp, rg_n - rg_tp]])[1] if nd_n and rg_n else None
        fisher_pool = fisher_exact([[pool_tp, pool_n - pool_tp], [rg_tp, rg_n - rg_tp]])[1] if pool_n and rg_n else None
        # precision/F1 untuk subset non-dork: seluruh halaman normal tetap dihitung sebagai negatif
        sub_t = (nd_t | (t.label == 0)).to_numpy()
        sub_h = (nd_h | (h.label == 0)).to_numpy()
        y_sub = np.concatenate([yt[sub_t], yh[sub_h]])
        p_sub = np.concatenate([pt[sub_t], ph[sub_h]])
        res["tc06_nondork"][name] = {
            "recall_nondork_test": {"tp": nd_tp, "n": nd_n, "recall": round(nd_tp / nd_n, 4), "ci95": wilson(nd_tp, nd_n)},
            "recall_reguler_test": {"tp": rg_tp, "n": rg_n, "recall": round(rg_tp / rg_n, 4), "ci95": wilson(rg_tp, rg_n)},
            "recall_nondork_holdout": {"tp": ndh_tp, "n": ndh_n, "recall": round(ndh_tp / ndh_n, 4), "ci95": wilson(ndh_tp, ndh_n)},
            "recall_nondork_gabungan": {"tp": pool_tp, "n": pool_n, "recall": round(pool_tp / pool_n, 4), "ci95": wilson(pool_tp, pool_n)},
            "fisher_p_test": None if fisher_test is None else round(float(fisher_test), 4),
            "fisher_p_gabungan_vs_reguler": None if fisher_pool is None else round(float(fisher_pool), 4),
            "precision_nondork_plus_semua_normal": round(precision_score(y_sub, p_sub, zero_division=0), 4),
            "f1_nondork_plus_semua_normal": round(f1_score(y_sub, p_sub, zero_division=0), 4),
        }

    # ---- TC-05 inference time Flask (HTTP, HTML mentah -> payload seperti ekstensi) ------------
    try:
        urllib.request.urlopen("http://127.0.0.1:5000/health", timeout=3).read()
    except Exception as e:  # noqa: BLE001
        print("SERVER TIDAK HIDUP -> TC-05 dilewati:", e)
        (OUT / "hasil_model.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        sys.exit(2)

    ev = df[df.split.isin(["test", "holdout"])].reset_index(drop=True)
    rows, lat = [], {"random_forest": [], "lightgbm": []}
    agree, pdiff = {"random_forest": 0, "lightgbm": 0}, {"random_forest": [], "lightgbm": []}
    n_ok = 0
    for _, r in ev.iterrows():
        try:
            html = open(r.path_abs, encoding="utf-8").read()
        except OSError:
            continue
        slug = Path(r.path_abs).stem.rsplit("_", 1)[0]
        url = f"https://{r.domain}/{'' if slug == 'index' else slug}"
        payload = html_to_payload(html, r.domain, url)
        payload["text"] = payload["text"][:60000]  # sama dengan batas MAX_CHARS di scanner.js
        n_ok += 1
        for name in models:
            body = json.dumps({**payload, "options": {"model": name, "threshold": 0.5}}).encode()
            t0 = time.perf_counter()
            out = json.load(urllib.request.urlopen(urllib.request.Request(API, body, {"Content-Type": "application/json"}), timeout=60))
            rt = (time.perf_counter() - t0) * 1000
            lat[name].append({"roundtrip_ms": rt, "server_total_ms": out["timing_ms"]["total"], "preprocess_ms": out["timing_ms"]["preprocess"],
                              "predict_ms": out["timing_ms"]["predict"], "n_words": out["n_words_clean"]})
            # paritas dengan prediksi offline (fitur dari CSV training)
            idx = ev.index[ev.path_key == r.path_key][0]
            s = r.split
            d = df[df.split == s].reset_index(drop=True)
            j = d.index[d.path_key == r.path_key][0]
            p_off = float(proba[(name, s)][j])
            pdiff[name].append(abs(out["ml"]["p_judi"] - p_off))
            agree[name] += int((out["ml"]["p_judi"] >= 0.5) == (p_off >= 0.5))

    def summ(v):
        v = sorted(v)
        return {"rata_rata": round(statistics.mean(v), 1), "median": round(statistics.median(v), 1),
                "p95": round(v[int(0.95 * (len(v) - 1))], 1), "maks": round(max(v), 1), "min": round(min(v), 1)}

    res["tc05_inference"] = {"jumlah_halaman": n_ok}
    for name in models:
        res["tc05_inference"][name] = {
            "roundtrip_http_ms": summ([x["roundtrip_ms"] for x in lat[name]]),
            "server_total_ms": summ([x["server_total_ms"] for x in lat[name]]),
            "preprocess_ms": summ([x["preprocess_ms"] for x in lat[name]]),
            "predict_ms": summ([x["predict_ms"] for x in lat[name]]),
            "paritas_label_dengan_offline": f"{agree[name]}/{n_ok}",
            "selisih_p_judi_maks": round(max(pdiff[name]), 4),
            "selisih_p_judi_rata2": round(statistics.mean(pdiff[name]), 5),
        }
    pd.DataFrame([{**x, "model": n} for n in models for x in lat[n]]).to_csv(OUT / "latensi_model_per_halaman.csv", index=False)

    (OUT / "hasil_model.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
