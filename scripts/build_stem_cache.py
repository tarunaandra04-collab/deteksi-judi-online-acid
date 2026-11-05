"""
build_stem_cache.py -- mempercepat inferensi: stemming Sastrawi ~10 ms/kata dan itulah bottleneck
(halaman baru dengan 500 kata unik bisa >2 detik). Skrip ini men-stem seluruh kosakata HTML training
sekali saja dan menyimpannya ke backend/models/stem_cache.json (dimuat server saat start).

Hasil stem tidak berubah -- hanya disimpan, sehingga prediksi identik dengan training.

    python scripts/build_stem_cache.py "<folder MODELS>"        (butuh: beautifulsoup4, pandas, Sastrawi)
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup, Comment
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

ROOT = Path(__file__).resolve().parent.parent
MODELS = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Andra\PycharmProjects\MODELS")
sp = pd.read_csv(MODELS / "training_final" / "data" / "split_train_test_holdout.csv")
stop = StopWordRemoverFactory().create_stop_word_remover()
stem = StemmerFactory().create_stemmer()

words = {}
for i, path in enumerate(sp.path_abs, 1):
    try:
        soup = BeautifulSoup(open(path, encoding="utf-8").read(), "html.parser")
    except OSError:
        continue
    for t in soup(["script", "style"]):
        t.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    txt = re.sub(r"\s+", " ", re.sub(r"[^a-z\s]", " ", soup.get_text(separator=" ").lower())).strip()
    for w in stop.remove(txt).split()[:5000]:
        words[w] = words.get(w, 0) + 1
    if i % 200 == 0:
        print(f"  baca {i}/{len(sp)}  kata unik: {len(words)}", flush=True)

print("kata unik total:", len(words), "-> stemming…", flush=True)
cache = {}
MIN_COUNT = 3  # kata langka tidak perlu (server menyimpan sendiri kata baru)
keep = [w for w in sorted(words, key=lambda x: -words[x]) if words[w] >= MIN_COUNT]
print("dipakai:", len(keep), flush=True)
for j, w in enumerate(keep, 1):
    cache[w] = stem.stem(w)
    if j % 2000 == 0:
        print(f"  stem {j}/{len(keep)}", flush=True)
out = ROOT / "backend" / "models" / "stem_cache.json"
out.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("tersimpan:", out, f"({out.stat().st_size/1024:.0f} KB)")
