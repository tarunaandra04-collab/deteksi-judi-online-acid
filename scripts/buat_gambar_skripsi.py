"""
buat_gambar_skripsi.py -- menyiapkan gambar Bab 4 skripsi dari hasil evaluasi & tangkapan layar uji.
Keluaran: docs/gambar_skripsi/*.png     (butuh: pillow, matplotlib)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MODELS = Path(r"C:\Users\Andra\PycharmProjects\MODELS")
EV = MODELS / "training_final" / "hasil_evaluasi"
SS = ROOT / "docs" / "hasil_uji" / "gambar" / "msedge"
OUT = ROOT / "docs" / "gambar_skripsi"
OUT.mkdir(exist_ok=True)


def grid(paths, cols, out, pad=12, bg="white"):
    ims = [Image.open(p).convert("RGB") for p in paths]
    w, h = max(i.width for i in ims), max(i.height for i in ims)
    rows = (len(ims) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * w + (cols + 1) * pad, rows * h + (rows + 1) * pad), bg)
    for k, im in enumerate(ims):
        r, c = divmod(k, cols)
        canvas.paste(im, (pad + c * (w + pad) + (w - im.width) // 2, pad + r * (h + pad) + (h - im.height) // 2))
    canvas.save(out)


# 1. confusion matrix 2x2: RF (test, holdout) dan LightGBM (test, holdout)
grid([EV / "confusion_matrix_random_forest_test.png", EV / "confusion_matrix_random_forest_holdout.png",
      EV / "confusion_matrix_lightgbm_test.png", EV / "confusion_matrix_lightgbm_holdout.png"], 2, OUT / "cm_2x2.png")

# 2. feature importance (apa adanya)
Image.open(EV / "feature_importance.png").convert("RGB").save(OUT / "feature_importance.png")

# 3. tiga popup berdampingan (aman | hati-hati | ada judi)
grid([SS / "uji_aman_popup.png", SS / "uji_waspada_popup.png", SS / "uji_tersembunyi_popup.png"], 3, OUT / "popup_aman_judi.png", pad=16)
from PIL import ImageChops  # potong ruang putih di bawah popup
_im = Image.open(OUT / "popup_aman_judi.png").convert("RGB")
_bb = ImageChops.difference(_im, Image.new("RGB", _im.size, "white")).getbbox()
if _bb:
    _im.crop((0, 0, _im.width, min(_im.height, _bb[3] + 20))).save(OUT / "popup_aman_judi.png")

# 4. halaman uji dengan lencana (dipotong ke bagian atas agar ringkas) dan pengaturan
im = Image.open(SS / "uji_tersembunyi_halaman.png").convert("RGB")
im.crop((0, 0, im.width, 720)).save(OUT / "halaman_lencana_tanpa_panel.png")
Image.open(SS / "uji_tersembunyi_panel.png").convert("RGB").save(OUT / "halaman_lencana.png")

# 5. struktur folder dataset (dibuat dari angka final)
tree = """data_final/
├── dataset_baru/                    Label 1: 215 domain, 757 halaman
│   ├── <domain>.ac.id/
│   │   ├── index_<hash>.html
│   │   └── <slug>_<hash>.html
│   └── ...
├── dataset_baru_negatif/            Label 0: 115 domain, 522 halaman
│   ├── kategori_a/  (56 domain, 275 halaman)  domain bersih total
│   ├── kategori_b/  (45 domain, 233 halaman)  induk punya subdomain
│   │                                          terinfeksi
│   ├── kategori_c/  (14 domain,  14 halaman)  hard negative
│   └── _temuan_hit/                           ditolak (ada kata kunci)
├── dataset_baru_dikeluarkan/        tidak masuk kelas mana pun
├── metode_penemuan.csv              sumber penemuan tiap domain
├── cluster_infeksi.csv              182 klaster infeksi Label 1
└── runlogs/ , trustpositif/         log & hasil cek TrustPositif"""
fig = plt.figure(figsize=(6.6, 2.75), dpi=200)
fig.text(0.02, 0.97, tree, family="DejaVu Sans Mono", fontsize=6.2, va="top", ha="left", linespacing=1.28)
fig.savefig(OUT / "struktur_folder.png", facecolor="white", bbox_inches="tight", pad_inches=0.08)
print("selesai:", sorted(p.name for p in OUT.iterdir()))
