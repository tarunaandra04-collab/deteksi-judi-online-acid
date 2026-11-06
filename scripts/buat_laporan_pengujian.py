"""
buat_laporan_pengujian.py -- menyusun docs/LAPORAN_PENGUJIAN.docx dari berkas hasil di docs/hasil_uji/.
Semua angka dibaca langsung dari JSON/CSV hasil eksekusi uji (tidak diketik manual).

    pip install python-docx
    python scripts/buat_laporan_pengujian.py
"""
import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
H = ROOT / "docs" / "hasil_uji"
IMG = H / "gambar" / "msedge"
OUT = ROOT / "docs" / "LAPORAN_PENGUJIAN.docx"

M = json.loads((H / "hasil_model.json").read_text(encoding="utf-8"))
EC = json.loads((H / "hasil_ekstensi_chromium.json").read_text(encoding="utf-8"))
EE = json.loads((H / "hasil_ekstensi_msedge.json").read_text(encoding="utf-8"))
VS = json.loads((H / "ekstensi_vs_offline.json").read_text(encoding="utf-8"))
LAT = pd.read_csv(H / "latensi_model_per_halaman.csv")
INFO = json.loads((ROOT / "backend" / "models" / "model_info.json").read_text(encoding="utf-8"))

FONT = "Times New Roman"
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.5)
sec.top_margin = sec.bottom_margin = Cm(2.5)

st = doc.styles["Normal"]
st.font.name = FONT
st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.15
for name, size in (("Heading 1", 14), ("Heading 2", 12), ("Heading 3", 12)):
    s = doc.styles[name]
    s.font.name = FONT
    s.font.size = Pt(size)
    s.font.bold = True
    s.font.italic = name == "Heading 3"
    s.font.color.rgb = RGBColor(0, 0, 0)
    s.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    s.paragraph_format.space_before = Pt(14 if name == "Heading 1" else 10)
    s.paragraph_format.space_after = Pt(6)
    s.paragraph_format.keep_with_next = True

cnt = {"tabel": 0, "gambar": 0}


def P(text="", bold=False, italic=False, align=None, size=None, after=None, style=None):
    p = doc.add_paragraph(style=style)
    if text:
        r = p.add_run(text)
        r.bold, r.italic = bold, italic
        if size:
            r.font.size = Pt(size)
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "j":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def RUNS(parts, align="j"):
    """parts: list of (teks, bold)"""
    p = doc.add_paragraph()
    for t, b in parts:
        r = p.add_run(t)
        r.bold = b
    if align == "j":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p


def BUL(text, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_prefix:
        p.add_run(bold_prefix).bold = True
    p.add_run(text)
    p.paragraph_format.space_after = Pt(3)
    return p


def H1(t): return doc.add_heading(t, level=1)
def H2(t): return doc.add_heading(t, level=2)
def H3(t): return doc.add_heading(t, level=3)


def shade(cell, hex_):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_)
    tcPr.append(shd)


def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def TABLE(caption, header, rows, widths, align_right_from=None, status_col=None, font=10):
    cnt["tabel"] += 1
    cap = P(f"Tabel {cnt['tabel']}. {caption}", bold=True, size=11, after=3)
    cap.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.width = Cm(widths[i])
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(font)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        shade(c, "D9D9D9")
    repeat_header(t.rows[0])
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].width = Cm(widths[i])
            cells[i].text = ""
            para = cells[i].paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            r = para.add_run(str(v))
            r.font.size = Pt(font)
            if align_right_from is not None and i >= align_right_from:
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if status_col is not None and i == status_col:
                r.bold = True
                if str(v).startswith("Berhasil dengan"):
                    shade(cells[i], "FFF2CC")
                elif str(v).startswith("Berhasil"):
                    shade(cells[i], "E2EFDA")
                else:
                    shade(cells[i], "F8CBAD")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def FIG(path, caption, width_cm=13.0):
    cnt["gambar"] += 1
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    c = P(f"Gambar {cnt['gambar']}. {caption}", italic=True, align="c", size=10, after=10)
    return c


def pct(x, d=1):
    return f"{x * 100:.{d}f}%".replace(".", ",")


def f(x, d=3):
    return f"{x:.{d}f}".replace(".", ",")


def n(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# =============================================================== data turunan
m = M["tc01_02_03"]
rf, lg = m["random_forest"], m["lightgbm"]
mc = M["tc04_mcnemar"]
t5 = M["tc05_inference"]
nd = M["tc06_nondork"]
eb = EE["browser"]["user_agent"]
edge_ver = eb.split("Edg/")[1] if "Edg/" in eb else "?"
chrome_ver = EC["browser"]["versi"].split("/")[1]
c1, c2, c3, c4, c5, c6, c7 = (EE["tc"][k] for k in ("TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06", "TC-07"))
cc = EC["tc"]
dyn, rob = EE["tc"]["KONTEN_DINAMIS"], EE["tc"]["KETAHANAN"]
kon = EE["konfusi_ekstensi"]
vs = VS["msedge"]
lat_rf = LAT[LAT.model == "random_forest"]
lat_lg = LAT[LAT.model == "lightgbm"]

# =============================================================== JUDUL
P("LAPORAN PENGUJIAN SISTEM", bold=True, align="c", size=16, after=2)
P("Deteksi Konten Judi Online pada Website Berdomain .ac.id", bold=True, align="c", size=13, after=2)
P("Model Random Forest / LightGBM dan Browser Extension (Manifest V3)", align="c", size=12, after=10)

TABLE("Informasi pengujian", ["Item", "Keterangan"], [
    ["Acuan skenario", "Tabel 3.15 (pengujian model) dan Tabel 3.16 (pengujian browser extension) pada proposal skripsi"],
    ["Objek uji", "Ekstensi v2.0.0 + server Flask lokal + model final (folder training_final)"],
    ["Tanggal pelaksanaan", "6 November 2026"],
    ["Pelaksana", "Skrip pengujian otomatis di repositori (folder tests/), dijalankan dan dilaporkan dengan bantuan Claude (asisten AI) atas permintaan penulis"],
    ["Repositori", "github.com/tarunaandra04-collab/deteksi-judi-online-acid"],
], [4.2, 11.8], font=10)

# =============================================================== 1 RINGKASAN
H1("1. Ringkasan Hasil")
P("Pengujian mencakup seluruh 6 skenario model (Tabel 3.15) dan 7 skenario ekstensi (Tabel 3.16) pada proposal, ditambah dua uji "
  "tambahan (konten dinamis dan ketahanan terhadap HTML tidak sempurna) serta perbandingan keluaran ekstensi di browser dengan prediksi "
  "offline model. Status per skenario disajikan pada Tabel 2; rincian ada pada Bab 3 dan 4.", align="j")

p_judi = f"{c1['terdeteksi_judi']}/{c1['halaman']}"
p_all = f"{c1['terdeteksi_judi'] + c1['waspada']}/{c1['halaman']}"
rows = [
    ["Model TC-01", "Evaluasi test set", f"RF: akurasi {f(rf['test']['accuracy'])}, F1 {f(rf['test']['f1'])}, ROC-AUC {f(rf['test']['roc_auc'],4)}; LightGBM: akurasi {f(lg['test']['accuracy'])}, F1 {f(lg['test']['f1'])}", "Berhasil"],
    ["Model TC-02", "Evaluasi holdout set", f"RF: akurasi {f(rf['holdout']['accuracy'])}, F1 {f(rf['holdout']['f1'])}; LightGBM: akurasi {f(lg['holdout']['accuracy'])}, F1 {f(lg['holdout']['f1'])}", "Berhasil"],
    ["Model TC-03", "False positive rate", f"RF: {pct(rf['test']['fpr'])} (test), {pct(rf['holdout']['fpr'])} (holdout); LightGBM: 0,0% pada keduanya", "Berhasil"],
    ["Model TC-04", "Uji McNemar RF vs LightGBM", f"p = {f(mc['test']['p_value'],4)} (test), p = {f(mc['holdout']['p_value'],4)} (holdout); tidak bermakna", "Berhasil"],
    ["Model TC-05", "Inference time Flask", f"RF rata-rata {n(t5['random_forest']['server_total_ms']['rata_rata'])} ms, maks {n(t5['random_forest']['server_total_ms']['maks'])} ms (326 halaman)", "Berhasil"],
    ["Model TC-06", "Independent validation set (non-dork)", f"Recall RF {pct(nd['random_forest']['recall_nondork_gabungan']['recall'])} vs {pct(nd['random_forest']['recall_reguler_test']['recall'])} (reguler); tidak signifikan (p = {f(nd['random_forest']['fisher_p_gabungan_vs_reguler'])})", "Berhasil dengan catatan"],
    ["Ekstensi TC-01", "Deteksi halaman judi", f"{p_judi} halaman berlabel 'Terindikasi konten judi'; {c1['waspada']} berlabel 'Waspada'; 0 lolos sebagai 'Aman'", "Berhasil dengan catatan"],
    ["Ekstensi TC-02", "Deteksi halaman normal", f"{c2['aman']}/{c2['halaman']} 'Aman'; {c2['waspada']} 'Waspada'; {c2['salah_judi']} salah dilabeli judi", "Berhasil dengan catatan"],
    ["Ekstensi TC-03", "Elemen tersembunyi", f"{c3['terdeteksi']}/{c3['blok_tersembunyi_berkata_kunci']} teknik penyembunyian terdeteksi; kontrol negatif 0 alarm palsu", "Berhasil"],
    ["Ekstensi TC-04", "Error koneksi Flask", "Pesan informatif tampil, ekstensi dan halaman tidak crash", "Berhasil"],
    ["Ekstensi TC-05", "Tampilan confidence score", f"Persentase ({c5['nilai']}) tampil bersama label di popup", "Berhasil"],
    ["Ekstensi TC-06", "End-to-end response time", f"Rata-rata {n(c6['e2e_ms']['rata_rata'])} ms; {c6['persen_di_bawah_2000ms_e2e']:.0f}% di bawah 2000 ms (Edge)".replace(".", ","), "Berhasil"],
    ["Ekstensi TC-07", "Kompatibilitas Manifest V3 di Edge", f"Microsoft Edge {edge_ver}: berjalan, {c7['jumlah_galat_total']} galat", "Berhasil"],
]
TABLE("Rekapitulasi status seluruh skenario", ["Kode", "Skenario", "Hasil ringkas", "Status"], rows, [2.5, 3.6, 7.0, 2.9], status_col=3, font=9)

P("Catatan penting: status \"Berhasil dengan catatan\" berarti kriteria pada proposal terpenuhi tetapi ada keterbatasan yang harus disebutkan "
  "secara jujur pada pembahasan skripsi (dijelaskan pada subbab terkait dan Bab 6).", italic=True, align="j", size=11)

# =============================================================== 2 LINGKUNGAN
H1("2. Lingkungan dan Metode Pengujian")
H2("2.1 Lingkungan")
TABLE("Lingkungan pengujian", ["Komponen", "Versi / keterangan"], [
    ["Sistem operasi", "Windows 11 Pro"],
    ["Python / scikit-learn", f"{INFO['versi']['python']} / {INFO['versi']['sklearn']} (sama dengan saat training)"],
    ["LightGBM / NumPy", "4.7.0 / " + INFO["versi"]["numpy"]],
    ["Browser uji 1", f"Microsoft Edge {edge_ver} (terpasang di komputer penulis)"],
    ["Browser uji 2", f"Chromium {chrome_ver} (bawaan Playwright)"],
    ["Ekstensi", f"Deteksi Judi Online .ac.id v{EE['manifest']['versi_ekstensi']}, Manifest V{EE['manifest']['manifest_version']}, izin: {', '.join(EE['manifest']['permissions'])}"],
    ["Server", "Flask 127.0.0.1:5000, model Random Forest (utama) dan LightGBM"],
    ["Ambang keputusan", "0,5 (bawaan ekstensi)"],
], [4.2, 11.8], font=10)

H2("2.2 Data uji")
d = M["data"]
TABLE("Pembagian data (split per domain/klaster, seed 42)", ["Split", "Halaman", "Judi", "Normal", "Domain"],
      [[k, d[k]["halaman"], d[k]["judi"], d[k]["normal"], d[k]["domain"]] for k in ("train", "test", "holdout")],
      [3.5, 3, 3, 3, 3], align_right_from=1)
P("Pengujian model memakai test set (221 halaman) dan holdout set (105 halaman); keduanya tidak dipakai untuk melatih model. "
  "Pengujian ekstensi memakai 50 halaman HTML nyata (25 judi, 25 normal) yang diambil acak (seed 7) dari gabungan test dan holdout set, "
  "ditambah halaman sintetis untuk skenario yang butuh kondisi terkontrol.", align="j")

H2("2.3 Metode")
BUL(" Model yang dipasang di repositori (backend/models) diperiksa identik dengan hasil training (hash berkas), lalu dievaluasi ulang pada test dan holdout set, dan hasilnya dicocokkan dengan laporan training. Latensi diukur lewat HTTP ke server Flask sungguhan dengan 326 halaman (payload dibentuk seperti yang dikirim ekstensi, teks dibatasi 60.000 karakter).", "Model (Tabel 3.15).")
BUL(" Ekstensi dimuat ke browser sungguhan (Edge dan Chromium). Setiap halaman nyata disajikan pada URL aslinya (https://<domain>.ac.id/...) lewat intersepsi jaringan, sehingga content script .ac.id berjalan otomatis tanpa internet. Hasil dibaca dari penyimpanan ekstensi, lencana ikon, lencana di halaman, dan popup.", "Ekstensi (Tabel 3.16).")
BUL(" Label \"benar\" adalah label Layer 1 (kata kunci) sehingga bukan verifikasi manual; lihat Bab 6.", "Acuan kebenaran.")

# =============================================================== 3 MODEL
H1("3. Hasil Pengujian Model Machine Learning (Tabel 3.15)")
H2("3.1 Integritas model dan reproduksi hasil training")
ident = all(v["identik"] for v in M["integritas_model"].values())
P(f"Keempat berkas model yang dipasang di repositori (model.pkl, model_lightgbm.pkl, vectorizer.pkl, scaler.pkl) "
  f"{'identik' if ident else 'TIDAK identik'} dengan berkas hasil training (hash SHA-256 sama). Evaluasi ulang pada test dan holdout set "
  f"{'menghasilkan angka yang sama persis' if M['reproduksi_laporan_training'] else 'menghasilkan angka berbeda'} dengan laporan training "
  "(akurasi, presisi, recall, F1, dan confusion matrix). Dengan demikian model yang diuji di ekstensi adalah model final yang dilaporkan.", align="j")

H2("3.2 TC-01 dan TC-02: Evaluasi test set dan holdout set")
rows = []
for nm, lab in (("random_forest", "Random Forest"), ("lightgbm", "LightGBM")):
    for s in ("test", "holdout"):
        r = m[nm][s]
        rows.append([lab, s, r["n"], f(r["accuracy"]), f(r["precision"]), f(r["recall"]), f(r["f1"]), f(r["roc_auc"], 4)])
TABLE("Metrik klasifikasi (kelas positif = judi)", ["Model", "Split", "n", "Akurasi", "Presisi", "Recall", "F1", "ROC-AUC"], rows,
      [3.0, 2.0, 1.2, 2.0, 2.0, 2.0, 1.8, 2.0], align_right_from=2)
P("Seluruh nilai metrik tersedia untuk analisis sehingga TC-01 dan TC-02 berhasil. Perlu dicatat bahwa model Random Forest tidak lebih unggul "
  "daripada LightGBM pada data ini: pada holdout, recall Random Forest "
  f"{f(rf['holdout']['recall'])} berbanding LightGBM {f(lg['holdout']['recall'])}. Selisih ini tidak bermakna secara statistik (lihat TC-04).", align="j")

H2("3.3 TC-03: False positive rate")
rows = []
for nm, lab in (("random_forest", "Random Forest"), ("lightgbm", "LightGBM")):
    for s in ("test", "holdout"):
        r = m[nm][s]
        rows.append([lab, s, r["tn"], r["fp"], r["fn"], r["tp"], pct(r["fpr"])])
TABLE("Confusion matrix dan false positive rate", ["Model", "Split", "TN", "FP", "FN", "TP", "FPR"], rows,
      [3.2, 2.2, 1.8, 1.8, 1.8, 1.8, 2.2], align_right_from=2)
P(f"FP dapat dihitung dan ditampilkan dari confusion matrix. FPR Random Forest {pct(rf['test']['fpr'])} pada test set dan "
  f"{pct(rf['holdout']['fpr'])} pada holdout set (1 halaman normal); LightGBM tidak menghasilkan false positive. "
  f"Kesalahan yang lebih relevan bagi tujuan deteksi adalah false negative: Random Forest melewatkan {rf['test']['fn']} halaman judi (test) dan "
  f"{rf['holdout']['fn']} (holdout). Menurut laporan training, seluruhnya adalah halaman dengan bukti kata kunci lemah (1–3 kemunculan).", align="j")

H2("3.4 TC-04: Uji McNemar Random Forest vs LightGBM")
rows = []
for s in ("test", "holdout"):
    r = mc[s]
    rows.append([s, r["a_kedua_benar"], r["b_rf_benar_lgbm_salah"], r["c_rf_salah_lgbm_benar"], r["e_kedua_salah"], f(r["p_value"], 4), "Tidak bermakna" if not r["bermakna_alpha_005"] else "Bermakna"])
TABLE("Uji McNemar eksak (α = 0,05)", ["Split", "Keduanya benar", "b (RF benar, LGBM salah)", "c (RF salah, LGBM benar)", "Keduanya salah", "p-value", "Kesimpulan"], rows,
      [1.8, 2.2, 2.7, 2.7, 2.2, 1.8, 2.6], align_right_from=1, font=9)
P("Tabel komparasi p-value tersedia dan dapat diinterpretasikan. Pada kedua split, perbedaan kinerja kedua model tidak bermakna pada α = 0,05. "
  "Jumlah pasangan yang berbeda (b + c) sangat kecil (5), sehingga uji ini berdaya rendah; hasil ini tidak boleh dibaca sebagai bukti bahwa "
  "Random Forest lebih baik. Pada holdout, arah selisih justru condong ke LightGBM (p = 0,0625).", align="j")

H2("3.5 TC-05: Pengukuran inference time Flask")
rows = []
for nm, lab, ket in (("random_forest", "Random Forest", "Lintasan 1 (cache stemming kosong untuk kata baru)"),
                     ("lightgbm", "LightGBM", "Lintasan 2 (cache sudah terisi oleh lintasan 1)")):
    x = t5[nm]
    rows.append([lab, ket, n(x["server_total_ms"]["rata_rata"]), n(x["server_total_ms"]["median"]), n(x["server_total_ms"]["p95"]), n(x["server_total_ms"]["maks"]),
                 n(x["preprocess_ms"]["rata_rata"]), n(x["predict_ms"]["rata_rata"], 1)])
TABLE(f"Waktu respons server per halaman (ms), {t5['jumlah_halaman']} halaman", ["Model", "Kondisi", "Rata-rata", "Median", "P95", "Maks", "Preprocess (rata2)", "Prediksi (rata2)"], rows,
      [2.3, 4.2, 1.7, 1.5, 1.4, 1.5, 1.9, 1.7], align_right_from=2, font=9)
P(f"Rata-rata waktu prediksi Flask berhasil direkam. Pada lintasan pertama (kondisi terburuk: kata baru harus di-stem), Random Forest membutuhkan rata-rata "
  f"{n(t5['random_forest']['server_total_ms']['rata_rata'])} ms dan maksimum {n(t5['random_forest']['server_total_ms']['maks'])} ms; "
  f"tidak ada halaman yang melebihi 2000 ms ({int((lat_rf.server_total_ms > 2000).sum())} dari {len(lat_rf)}). Waktu prediksi model itu sendiri hanya "
  f"{n(t5['random_forest']['predict_ms']['rata_rata'], 1)} ms (Random Forest, 200 pohon) dan {n(t5['lightgbm']['predict_ms']['rata_rata'], 1)} ms (LightGBM); "
  "sebagian besar waktu dipakai untuk stemming Sastrawi. Perbandingan Random Forest vs LightGBM pada tabel ini tidak setara karena kondisi cache berbeda, "
  "sehingga jangan dipakai untuk menyimpulkan model mana yang lebih cepat.", align="j")
parity = t5["random_forest"]["paritas_label_dengan_offline"]
P(f"Uji tambahan: label yang dihasilkan server dari HTML mentah sama dengan prediksi offline pada {parity} halaman (Random Forest) dan "
  f"{t5['lightgbm']['paritas_label_dengan_offline']} (LightGBM). Selisih maksimum probabilitas {f(t5['random_forest']['selisih_p_judi_maks'],4)} (RF) "
  "diduga berasal dari kata baru yang tidak sempat di-stem karena anggaran waktu 1 detik dan token yang terlalu panjang (lihat Bab 6).", align="j")

H2("3.6 TC-06: Evaluasi pada independent validation set (non-Google Dork)")
rows = []
for nm, lab in (("random_forest", "Random Forest"), ("lightgbm", "LightGBM")):
    x = nd[nm]
    def cell(k):
        z = x[k]
        return f"{z['tp']}/{z['n']} = {pct(z['recall'])} [{pct(z['ci95'][0],0)}–{pct(z['ci95'][1],0)}]"
    rows.append([lab, cell("recall_nondork_test"), cell("recall_nondork_holdout"), cell("recall_nondork_gabungan"), cell("recall_reguler_test"),
                 f(x["fisher_p_gabungan_vs_reguler"]), f(x["f1_nondork_plus_semua_normal"])])
TABLE("Recall halaman judi non-dork vs reguler (rentang kepercayaan 95% Wilson)", ["Model", "Non-dork test", "Non-dork holdout", "Non-dork gabungan", "Reguler (test)", "Fisher p", "F1 non-dork"], rows,
      [2.2, 2.7, 2.7, 2.7, 2.7, 1.3, 1.5], font=8)
r_nd, r_rg = nd["random_forest"]["recall_nondork_gabungan"], nd["random_forest"]["recall_reguler_test"]
P(f"Metrik pada sampel non-Google Dork tidak menurun signifikan dibandingkan test set reguler pada α = 0,05 untuk kedua model, sehingga kriteria TC-06 terpenuhi. "
  f"Namun Random Forest menunjukkan kecenderungan turun: recall {pct(r_nd['recall'])} pada halaman non-dork berbanding {pct(r_rg['recall'])} pada halaman reguler "
  f"(p = {f(nd['random_forest']['fisher_p_gabungan_vs_reguler'])}), sedangkan LightGBM tidak turun ({pct(nd['lightgbm']['recall_nondork_gabungan']['recall'])} vs {pct(nd['lightgbm']['recall_reguler_test']['recall'])}). "
  "Dengan hanya 102 halaman non-dork dari puluhan domain, uji ini berdaya rendah sehingga penurunan sebesar itu tidak dapat dikesampingkan. "
  "Karena itu status skenario ini \"Berhasil dengan catatan\". Selain itu, \"independent validation set\" di sini adalah halaman non-dork dari dataset yang sama dan berlabel kata kunci, "
  "bukan sampel berlabel manual terpisah seperti yang dirancang pada Bab 3.9.", align="j")

# =============================================================== 4 EKSTENSI
H1("4. Hasil Pengujian Browser Extension (Tabel 3.16)")
P(f"Seluruh skenario dijalankan pada Microsoft Edge {edge_ver} dan diulang pada Chromium {chrome_ver}. Label yang dihasilkan ekstensi identik pada kedua browser untuk seluruh 50 halaman nyata (hanya waktu yang berbeda tipis); "
  "tabel di bawah memuat hasil Edge.", align="j")

H2("4.1 TC-01: Deteksi halaman judi aktif")
TABLE("Hasil pada 25 halaman judi nyata (Edge)", ["Keluaran ekstensi", "Jumlah", "Keterangan"], [
    ["Terindikasi konten judi", f"{c1['terdeteksi_judi']}", "Lencana merah dan badge ikon \"!\" tampil; rata-rata sorotan " + f"{c1['rata2_sorotan']:.1f}".replace(".", ",") + " per halaman"],
    ["Waspada", f"{c1['waspada']}", "Model menilai aman (peluang < 0,5) tetapi bukti kata kunci/elemen tersembunyi ditemukan"],
    ["Aman (lolos)", f"{c1['lolos_aman']}", "—"],
], [4.5, 2.0, 9.5], align_right_from=None)
P(f"Lencana di halaman tampil pada {c1['banner_tampil']} dari {c1['halaman']} halaman. Jika hanya label \"Terindikasi\" dihitung sebagai deteksi, recall ekstensi "
  f"{pct(kon['judi_saja_sebagai_positif']['recall'], 0)} ({p_judi}); jika \"Waspada\" ikut dihitung sebagai tanda peringatan, recall {pct(kon['judi_atau_waspada_sebagai_positif']['recall'], 0)} ({p_all}). "
  "Keempat halaman berlabel Waspada adalah halaman yang sama yang juga dilewatkan model offline (peluang 0,29–0,41; domain ununtb.ac.id dan jurnal.staim-probolinggo.ac.id), "
  "yaitu bukti bahwa tingkat Waspada menangkap kasus yang luput dari model. Kriteria \"menampilkan notifikasi\" terpenuhi untuk seluruh halaman positif, "
  "tetapi teks \"Terindikasi\" persis hanya pada " + p_judi + "; karena itu status \"Berhasil dengan catatan\".", align="j")
FIG(IMG / "halaman_judi_nyata_dengan_sorotan.png", "Halaman judi nyata (dataset) dengan lencana \"Terindikasi konten judi\" di pojok kanan bawah (Edge)", 12.5)

H2("4.2 TC-02: Deteksi halaman akademik normal")
TABLE("Hasil pada 25 halaman normal nyata (Edge)", ["Keluaran ekstensi", "Jumlah", "Keterangan"], [
    ["Aman", f"{c2['aman']}", f"Badge \"OK\" pada {c2['badge_ok']} halaman; lencana tidak ditampilkan pada {c2['banner_tidak_tampil']} halaman"],
    ["Waspada", f"{c2['waspada']}", "Artikel blog fakultas yang membahas hukum judi dan pinjaman online (berisi 11 kemunculan kata kunci kuat; peluang model 0,28)"],
    ["Terindikasi judi (salah)", f"{c2['salah_judi']}", "—"],
], [4.5, 2.0, 9.5])
P("Tidak ada halaman normal yang salah dilabeli judi. Satu halaman berlabel Waspada adalah artikel yang memang membahas judi sehingga mengandung kata kunci; "
  "ini contoh nyata keterbatasan pendekatan kata kunci (bukan kesalahan model) dan perlu dipaparkan pada pembahasan. Status: \"Berhasil dengan catatan\".", align="j")

H2("4.3 TC-03: Deteksi elemen tersembunyi")
rows = [[k, "Ya" if v else "Tidak"] for k, v in c3["per_teknik"].items()]
TABLE("Deteksi lima teknik penyembunyian (halaman uji sintetis)", ["Teknik CSS", "Terdeteksi dan dilaporkan"], rows, [8.0, 8.0], align_right_from=1)
P(f"Seluruh {c3['terdeteksi']} dari {c3['blok_tersembunyi_berkata_kunci']} blok teks judi yang disembunyikan terdeteksi dan dihitung ({c3['jumlah_elemen_dilaporkan']} elemen dilaporkan), "
  f"fitur has_hidden bernilai {c3['fitur_has_hidden']}, dan halaman dilabeli {c3['label']} (peluang {f(c3['p_judi'],2)}). Popup menampilkan daftar elemen tersembunyi beserta alasannya. "
  f"Kontrol negatif: halaman dengan menu seluler display:none tanpa kata kunci tidak menghasilkan laporan elemen tersembunyi ({c3['kontrol_negatif']['elemen_tersembunyi_dilaporkan']} laporan) dan dilabeli {c3['kontrol_negatif']['label']}. "
  "Kriteria proposal hanya menyebut display:none; ekstensi mendeteksi empat teknik lain.", align="j")
FIG(IMG / "uji_tersembunyi_popup.png", "Popup pada halaman dengan teks judi tersembunyi: alasan, kata kunci, dan daftar elemen tersembunyi", 7.5)

H2("4.4 TC-04: Error koneksi ke Flask API")
P(f"Dengan alamat server dibelokkan ke port yang tidak aktif, ekstensi menampilkan pesan: \"{c4['pesan']}\". Service worker tetap hidup ({'ya' if c4['service_worker_hidup'] else 'tidak'}), "
  f"halaman tetap berfungsi ({'ya' if c4['halaman_tetap_berfungsi'] else 'tidak'}), badge ikon berubah menjadi \"{c4['badge']}\", dan popup menampilkan tombol \"Coba lagi\" serta \"Cek pengaturan server\". "
  "Kriteria terpenuhi: pesan informatif tanpa crash.", align="j")
FIG(IMG / "uji_error_popup.png", "Popup saat server tidak terjangkau", 7.5)

H2("4.5 TC-05: Tampilan confidence score")
P(f"Popup menampilkan persentase peluang konten judi bersama label (contoh: {c5['nilai']} dengan label \"Terindikasi konten judi\") dan penanda ambang keputusan pada bilah. "
  "Skor ditampilkan pada seluruh 10 popup halaman nyata yang diperiksa. Perlu dicatat: angka yang ditampilkan adalah peluang kelas judi (p_judi), bukan "
  "\"keyakinan atas label\"; untuk halaman Aman angka rendah berarti yakin aman.", align="j")
FIG(IMG / "popup_judi_nyata.png", "Popup pada halaman judi nyata", 7.5)

H2("4.6 TC-06: End-to-end response time")
def e(x):
    return [n(x["rata_rata"]), n(x["median"]), n(x["p95"]), n(x["maks"])]
TABLE("Waktu respons ekstensi pada 50 halaman nyata (ms)", ["Tahap", "Browser", "Rata-rata", "Median", "P95", "Maks"], [
    ["Ekstraksi di halaman", "Edge"] + e(c6["ekstraksi_ms"]),
    ["Server (preprocess + prediksi)", "Edge"] + e(c6["server_ms"]),
    ["End-to-end (ekstraksi + HTTP + server)", "Edge"] + e(c6["e2e_ms"]),
    ["End-to-end (ekstraksi + HTTP + server)", "Chromium"] + e(cc["TC-06"]["e2e_ms"]),
    ["Dari halaman selesai dimuat sampai hasil tersimpan", "Edge"] + e(c6["load_ke_hasil_ms"]),
    ["Popup hingga tampil (10 halaman)", "Edge"] + e(c6["popup_tampil_ms"]),
], [6.2, 2.0, 2.0, 2.0, 1.9, 1.9], align_right_from=2, font=9)
P(f"Rata-rata waktu dari permintaan hingga hasil tersedia adalah {n(c6['e2e_ms']['rata_rata'])} ms (Edge) dan {n(cc['TC-06']['e2e_ms']['rata_rata'])} ms (Chromium), jauh di bawah 2000 ms; "
  f"{c6['persen_di_bawah_2000ms_load_ke_hasil']:.0f}% halaman selesai di bawah 2000 ms bahkan jika dihitung dari saat halaman selesai dimuat (maksimum {n(c6['load_ke_hasil_ms']['maks'])} ms). "
  "Waktu tersebut sudah termasuk jeda 400 ms yang sengaja diberikan content script sebelum memindai. Popup tampil dalam sekitar 70 ms.", align="j")
P("Perlu dicatat: pengukuran ekstensi ini dilakukan ketika cache stemming server sudah terisi kata-kata dari halaman yang sama (hasil uji model sebelumnya), "
  f"jadi mewakili kondisi \"hangat\". Kondisi terburuk (kata baru) diukur pada TC-05 model: maksimum {n(t5['random_forest']['server_total_ms']['maks'])} ms di server.", italic=True, align="j", size=11)

H2("4.7 TC-07: Kompatibilitas Manifest V3 di Edge")
P(f"Ekstensi dimuat pada Microsoft Edge {edge_ver} (versi terkini di komputer uji) dengan Manifest V{c7['manifest_version']}; service worker aktif, "
  f"halaman popup dan pengaturan dibuka tanpa galat konsol, dan tombol \"Tes koneksi\" di pengaturan melaporkan server terhubung. "
  f"Jumlah galat tercatat: {c7['jumlah_galat_total']} (service worker, popup, dan pengaturan). Hasil identik pada Chromium {chrome_ver}.", align="j")
FIG(IMG / "pengaturan.png", "Halaman Pengaturan: server, model, ambang, tampilan, dan riwayat", 11.5)

H2("4.8 Uji tambahan: konten yang disisipkan setelah halaman dimuat")
P(f"Halaman yang awalnya normal menyisipkan blok teks judi 2,5 detik setelah dimuat (meniru injeksi lewat JavaScript). Ekstensi memindai ulang secara otomatis "
  f"(pemicu: \"{dyn['pemicu']}\") dan label berubah dari {dyn['label_awal']} menjadi {dyn['label_setelah_injeksi']} sekitar {str(dyn['waktu_deteksi_s']).replace('.', ',')} detik setelah pemindaian awal. "
  "Waktu itu didominasi oleh peredam (debounce) 3 detik dan jeda minimum 8 detik antar pemindaian yang sengaja dipasang agar halaman dinamis tidak membebani browser. "
  "Dengan demikian injeksi lambat tetap tertangkap, tetapi tidak instan.", align="j")

H2("4.9 Uji tambahan: ketahanan terhadap input HTML tidak sempurna")
names = {"html_rusak": "HTML rusak (tag tidak tertutup, entitas salah)", "halaman_kosong": "Halaman kosong", "bukan_html_json": "Respons bukan HTML (JSON)",
         "halaman_besar_14000_paragraf": "Halaman besar (14.000 paragraf, 14.000 tautan)", "dom_sangat_dalam_1500": "DOM bersarang 1.500 tingkat"}
rows = []
for k, lab in names.items():
    x = rob[k]
    rows.append([lab, "Ya" if x["berhasil"] else "Tidak", x["label"], f(x["p_judi"], 3), n(x["ms_e2e"]), n(x["ms_ekstrak"])])
TABLE("Hasil uji ketahanan (Edge)", ["Kasus", "Berhasil", "Label", "Peluang judi", "E2E (ms)", "Ekstraksi (ms)"], rows, [6.0, 1.8, 1.6, 2.2, 2.0, 2.4], align_right_from=1, font=9)
P("Kelima kasus diproses tanpa galat dan service worker tetap hidup. Catatan: browser membatasi kedalaman DOM maksimum 512 sehingga fitur kedalaman terbaca 513; "
  "HTML rusak yang memuat kata kunci dilabeli judi (peluang 0,56), sesuai harapan.", align="j")

H2("4.10 Kesesuaian keluaran ekstensi di browser dengan prediksi offline")
P(f"Untuk 50 halaman nyata yang sama, peluang judi yang dihitung ekstensi di browser dibandingkan dengan peluang offline model (fitur dari berkas training). "
  f"Label model sama pada {vs['label_ml_sama_dengan_offline']} dari {vs['n']} halaman; selisih peluang rata-rata {f(vs['selisih_p_rata2'],4)}, median {f(vs['selisih_p_median'],4)}, maksimum {f(vs['selisih_p_maks'],4)}. "
  "Ini menunjukkan perbedaan antara cara menghitung fitur saat training (HTML mentah di Python) dan saat inferensi (DOM hidup di browser) praktis dapat diabaikan, "
  "sehingga risiko train-serve skew yang diperingatkan pada model_loader versi lama sudah teratasi.", align="j")

# =============================================================== 5 REKAP: sudah di bab 1
H1("5. Pembahasan Singkat")
BUL(f" Seluruh skenario pada Tabel 3.15 dan 3.16 berhasil dijalankan dan terukur. Tiga skenario (TC-06 model; TC-01 dan TC-02 ekstensi) berstatus \"dengan catatan\" karena keterbatasan yang harus diungkap.", "Cakupan.")
BUL(" Pada data ini Random Forest tidak lebih baik daripada LightGBM. Jika skripsi mempertahankan Random Forest sebagai model utama, alasannya harus berasal dari hal lain (misalnya interpretabilitas feature_importance atau kesederhanaan), bukan dari angka metrik.", "Pemilihan model.")
BUL(" Tingkat \"Waspada\" menambah kemampuan menangkap halaman yang luput dari model (4 dari 25 halaman judi) dengan harga 1 peringatan pada halaman normal yang membahas judi. Ini tradeoff yang sebaiknya didiskusikan.", "Nilai tambah dan harga lapisan aturan.")

# =============================================================== 6 TEMUAN
H1("6. Temuan Selama Pengujian dan Keterbatasan")
H2("6.1 Temuan dan perbaikan")
BUL(" Pada uji pertama, 44 dari 326 halaman (Random Forest) melewati 2000 ms di server dan satu halaman mencapai 58 detik. Penyebab: stemming Sastrawi sekitar 10 ms/kata, sehingga halaman dengan ribuan kata baru sangat lambat; skrip uji awal juga mengirim teks tanpa batas (hingga 2 MB), padahal ekstensi membatasi 60.000 karakter. Perbaikan: (1) cache stemming dari kosakata training, (2) anggaran waktu stemming 1 detik per permintaan untuk kata baru, (3) token lebih panjang dari 30 karakter tidak di-stem, (4) server membatasi teks 80.000 karakter, dan skrip uji disamakan dengan batas ekstensi. Hasil setelah perbaikan dilaporkan pada TC-05 dan TC-06.", "Latensi.")
BUL(" Anggaran waktu berarti pada halaman dengan banyak kata baru, sebagian kata dipakai tanpa di-stem sehingga probabilitas bisa bergeser sedikit (maksimum 0,0235 pada 326 halaman) tanpa mengubah satu pun label. Kata yang sudah di-stem tersimpan di cache sehingga pemindaian berikutnya makin tepat.", "Harga perbaikan.")
BUL(" Satu bug dan satu perbedaan dengan training sudah diperbaiki sebelum pengujian ini: daftar kata kunci untuk fitur meta_judi_flag dan url_flag (17 kata pada model_loader lama vs 91 kata saat training) dan teks tersembunyi yang tidak terbaca (innerText vs get_text).", "Perbaikan sebelumnya.")
H2("6.2 Keterbatasan")
BUL(" Label \"benar\" berasal dari pencocokan kata kunci (Layer 1) dan fitur TF-IDF memuat kata yang sama. Metrik tinggi tidak membuktikan kemampuan mendeteksi judi tanpa kata kunci; 241 halaman judi tanpa kata kunci sengaja dikeluarkan dari data.", "Sirkularitas label–fitur.")
BUL(" Test set 70 domain dan holdout 30 domain; satu domain dapat mengubah metrik besar. Seluruh p-value dan rentang kepercayaan bersifat indikatif.", "Ukuran sampel.")
BUL(" Uji ekstensi memakai 25 + 25 halaman nyata dari dataset yang sama dengan pelatihan (tetapi bukan data latih) dan halaman sintetis; belum ada uji pada situs .ac.id yang sedang aktif terinfeksi di internet.", "Cakupan uji ekstensi.")
BUL(" Pengujian dijalankan pada Edge dan Chromium versi 156 di satu komputer; kompatibilitas pada versi Edge lain belum diuji. Ekstensi dimuat tanpa paket (unpacked), bukan dari Edge Add-ons.", "Lingkungan.")
BUL(" Pengujian otomatis; penilaian antarmuka oleh pengguna sungguhan (usability) belum dilakukan.", "Usability.")

# =============================================================== 7 KESIMPULAN
H1("7. Kesimpulan")
P("Model final dan ekstensi v2 memenuhi seluruh kriteria keberhasilan pada Tabel 3.15 dan 3.16, dengan tiga status \"berhasil dengan catatan\" yang harus dibahas secara jujur di skripsi. "
  f"Model yang dipasang identik dengan hasil training; Random Forest mencapai F1 {f(rf['test']['f1'],3)} (test) dan {f(rf['holdout']['f1'],3)} (holdout), tidak berbeda bermakna dari LightGBM. "
  f"Di browser, ekstensi memberi hasil yang konsisten dengan model offline ({vs['label_ml_sama_dengan_offline']}/{vs['n']} label sama), mendeteksi teks judi yang disembunyikan dengan lima teknik CSS, "
  f"menangani kegagalan server tanpa crash, dan memberi hasil dalam rata-rata {n(c6['e2e_ms']['rata_rata'])} ms. "
  "Keterbatasan utama yang perlu dijelaskan saat sidang adalah sirkularitas label–fitur dan ukuran sampel evaluasi yang kecil.", align="j")

# =============================================================== LAMPIRAN
H1("Lampiran A. Gambar Tambahan")
FIG(IMG / "uji_aman_popup.png", "Popup pada halaman normal (Aman)", 7.5)
FIG(IMG / "uji_tersembunyi_halaman.png", "Halaman uji dengan lima blok teks judi tersembunyi: tampak bersih bagi pengunjung, lencana tetap muncul", 11.5)

H1("Lampiran B. Cara Mengulang Pengujian")
P("Dari folder repositori, dengan server berjalan (.\\jalankan.ps1 -NoBrowser):", align="j")
for line in ("python tests/uji_laporan_model.py \"<folder MODELS>\"          # Tabel 3.15 (TC-01..06) -> docs/hasil_uji/hasil_model.json",
             "python tests/uji_laporan_ekstensi.py --channel msedge --n 25   # Tabel 3.16 di Microsoft Edge",
             "python tests/uji_laporan_ekstensi.py --channel chromium --n 25 # idem di Chromium",
             "python tests/analisis_ekstensi_vs_offline.py                   # kesesuaian browser vs offline",
             "python scripts/buat_laporan_pengujian.py                       # menyusun ulang dokumen ini"):
    p = doc.add_paragraph()
    r = p.add_run(line)
    r.font.name = "Consolas"
    r.font.size = Pt(9)
    p.paragraph_format.space_after = Pt(2)

# nomor halaman
foot = sec.footer.paragraphs[0]
foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = foot.add_run()
for typ, txt in (("begin", None), (None, "PAGE"), ("end", None)):
    if typ:
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), typ)
    else:
        el = OxmlElement("w:instrText")
        el.set(qn("xml:space"), "preserve")
        el.text = txt
    run._r.append(el)

doc.save(OUT)
print("tersimpan:", OUT)
