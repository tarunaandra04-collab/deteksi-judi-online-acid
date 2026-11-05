"""
app.py -- Flask API lokal untuk extension Deteksi Judi Online .ac.id (v2)

Endpoint:
  GET  /health      -> status server + model
  GET  /model-info  -> metadata model (versi sklearn saat training, daftar model)
  POST /predict     -> klasifikasi satu halaman (lihat docs/KONTRAK_API.md)

Server hanya mendengarkan 127.0.0.1 dan hanya menerima permintaan dari
extension (origin chrome-extension:// / extension://) atau localhost.
"""
import os
import re

from flask import Flask, jsonify, request
from flask_cors import CORS

import engine

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB cukup untuk teks 60k karakter + 3000 href

CORS(app, origins=[re.compile(r"^(chrome|moz|ms-browser)?-?extension://.*$"),
                   re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?$")])

REQUIRED = ["url", "domain", "text", "links", "structural", "meta"]

try:
    engine.load()
    print(f"[server] model dimuat: {engine.status()['models']}")
except Exception as exc:  # server tetap hidup agar /health bisa menjelaskan masalahnya
    print(f"[server] GAGAL memuat model: {exc}")


@app.get("/health")
def health():
    return jsonify({"status": "ok", **engine.status()})


@app.get("/model-info")
def model_info():
    return jsonify(engine.status())


@app.post("/predict")
def predict():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Body JSON tidak valid"}), 400
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        return jsonify({"status": "error", "message": f"Field hilang: {missing}"}), 400
    opts = data.get("options") or {}
    try:
        result = engine.predict(
            data,
            model_name=str(opts.get("model", "random_forest")),
            threshold=float(opts.get("threshold", 0.5)),
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"status": "error", "message": f"{type(exc).__name__}: {exc}"}), 500
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("DJO_PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
