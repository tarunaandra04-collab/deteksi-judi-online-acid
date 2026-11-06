"""
skripsi_isi.py -- ISI Bab 4 dan Bab 5 (data + teks). Dibaca oleh revisi_bab45.py.
Semua angka hasil uji dibaca dari docs/hasil_uji/*.json (hasil eksekusi nyata); angka training dari laporan final.

Penanda teks:  *miring*   **tebal**   {T:kunci} -> "Tabel 4.n"   {G:kunci} -> "Gambar 4.n"
Jenis blok: ("h2",t) ("h3",t) ("p",t) ("np","1)",t) ("table",kunci,caption,header,rows,lebar,rata)
            ("code",kunci,caption,baris) ("img",kunci,caption,berkas,lebar_cm) ("ph",kunci,caption,instruksi)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
H = ROOT / "docs" / "hasil_uji"
IMGD = ROOT / "docs" / "gambar_skripsi"

M = json.loads((H / "hasil_model.json").read_text(encoding="utf-8"))
EE = json.loads((H / "hasil_ekstensi_msedge.json").read_text(encoding="utf-8"))
EC = json.loads((H / "hasil_ekstensi_chromium.json").read_text(encoding="utf-8"))
VS = json.loads((H / "ekstensi_vs_offline.json").read_text(encoding="utf-8"))["msedge"]


def f(x, d=3):
    return f"{x:.{d}f}".replace(".", ",")


def n(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=1):
    return f"{x * 100:.{d}f}%".replace(".", ",")


m = M["tc01_02_03"]
rf, lg = m["random_forest"], m["lightgbm"]
mc = M["tc04_mcnemar"]
t5 = M["tc05_inference"]
nd = M["tc06_nondork"]
c1, c2, c3, c4, c5, c6, c7 = (EE["tc"][k] for k in ("TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06", "TC-07"))
cc6 = EC["tc"]["TC-06"]
dyn, rob = EE["tc"]["KONTEN_DINAMIS"], EE["tc"]["KETAHANAN"]
kon = EE["konfusi_ekstensi"]
UA = EE["browser"]["user_agent"]
EDGE = UA.split("Edg/")[1] if "Edg/" in UA else "156.0.0.0"
EDGE_MAJOR = EDGE.split(".")[0]
REPO = "https://github.com/tarunaandra04-collab/deteksi-judi-online-acid"

B = []  # daftar blok Bab 4
a = B.append

# =====================================================================================================
a(("p", "Bab ini memaparkan pelaksanaan seluruh tahapan yang dirancang pada Bab III, mulai dari pengumpulan data, pelabelan, praprosesing, ekstraksi fitur, pembagian data, pelatihan model Random Forest dan LightGBM, hingga implementasi model ke dalam *browser extension* Microsoft Edge, dilanjutkan dengan hasil pengujian dan pembahasan yang menjawab ketiga rumusan masalah pada Bab I. Seluruh angka pada bab ini berasal dari data akhir penelitian dan hasil eksekusi pengujian yang berkas keluarannya disimpan pada repositori penelitian."))

# ------------------------------------------------------------------------------------------ 4.1
a(("h2", "Implementasi"))
a(("h3", "Lingkungan Pengembangan"))
a(("p", "Seluruh proses pengumpulan data, praprosesing, pelatihan, dan pengujian dilaksanakan pada satu komputer berbasis Windows 11 dengan lingkungan yang ditunjukkan pada {T:env}. Versi pustaka dicatat karena model yang tersimpan dalam format *pickle* hanya dapat dimuat kembali secara andal pada versi scikit-learn yang sama, sehingga lingkungan Flask pada sisi *extension* dikunci pada versi tersebut."))
a(("table", "env", "Lingkungan Pengembangan dan Pengujian",
   ["Komponen", "Versi / Keterangan"],
   [["Bahasa pemrograman", "Python 3.14.0"],
    ["Pembelajaran mesin", "scikit-learn 1.9.1, imbalanced-learn 0.14.2, LightGBM 4.7.0, NumPy 2.5.4"],
    ["Pengolahan teks", "Sastrawi 1.0.1 (stopword dan stemming), BeautifulSoup 4.15.0"],
    ["Server inferensi", "Flask 3.1.3 (alamat 127.0.0.1:5000)"],
    ["Pengumpulan data", "Requests, cloudscraper, Playwright (render headless)"],
    ["Browser pengujian", f"Microsoft Edge {EDGE} dan Chromium 156 (Playwright 1.64.1)"],
    ["Ekstensi", "Manifest V3, JavaScript (ES2022)"]],
   [1900, 3936], ["l", "l"]))

a(("h3", "Implementasi Pengumpulan Data"))
a(("p", "Pengumpulan data dilaksanakan dalam beberapa putaran sejak 23 Oktober hingga 6 November 2026 dan berpegang pada pendekatan *domain-first* yang dirancang pada subbab 3.5. Titik awalnya adalah domain sampel dari penelusuran Google Dork (Tabel 3.1). Penelusuran tersebut ternyata menghasilkan domain dalam jumlah terbatas, sehingga pada putaran berikutnya sumber penemuan ditambah dengan urlscan.io, Common Crawl, arsip Wayback Machine, dan enumerasi subdomain pada institusi yang sudah terbukti terinfeksi. Pada enumerasi subdomain, nama domain yang me-resolve seluruh nama acak (*wildcard* DNS) dibuang agar tidak menghasilkan domain palsu. Setiap kandidat disaring terlebih dahulu dengan leksikon kata kunci (Tabel 3.6) sebelum diambil secara penuh; hasil saringan dengan bukti lemah, misalnya satu kata kunci generik seperti *toto*, tidak langsung dimasukkan tetapi ditandai untuk ditinjau manual."))
a(("p", "Domain Label 1 (terindikasi judi) yang terkumpul berjumlah 215 domain. Rincian sumber penemuannya ditunjukkan pada {T:sumber}. Sumber yang bukan Google Dork menyumbang sebagian besar domain, yang berarti dataset tidak hanya berisi domain yang mudah ditemukan mesin pencari."))
a(("table", "sumber", "Sumber Penemuan Domain Label 1",
   ["Sumber penemuan", "Domain"],
   [["urlscan.io", "60"], ["Enumerasi subdomain", "43"], ["Wayback Machine per institusi", "36"],
    ["Common Crawl", "27"], ["Google Dork (mesin pencari)", "18"], ["Wayback Machine per kata kunci", "12"],
    ["Lainnya (lateral dalam institusi, arsip, temuan manual, tidak terdokumentasi)", "19"],
    ["Total", "215"]],
   [4636, 1200], ["l", "c"]))
a(("p", "Untuk keperluan evaluasi, setiap domain diberi kelompok independensi. Sebanyak 99 domain ditemukan oleh sumber yang tidak bergantung pada Google (INDEPENDEN_NON_GOOGLE), 83 domain adalah turunan dari institusi yang lebih dahulu ditemukan (subdomain atau halaman lain pada institusi yang sama), 18 domain berasal dari Google Dork, 13 tidak terdokumentasi, dan 2 berasal dari audit Label 0. Pengelompokan ini dipakai pada pengujian TC-06 untuk menilai model pada domain yang tidak ditemukan lewat Google Dork. Perlu dicatat bahwa sumber seperti urlscan.io dan Common Crawl juga ditelusuri dengan kata kunci judi sehingga \"independen dari Google\" tidak berarti independen dari leksikon."))
a(("p", "Pengambilan halaman dilakukan secara bertingkat. Modul pengambilan mencoba beberapa metode secara berurutan sampai salah satunya berhasil, mulai dari permintaan HTTP dengan *User-Agent* Googlebot, *User-Agent* Chrome, cloudscraper, hingga render *headless* untuk halaman yang memerlukan eksekusi JavaScript, dan terakhir arsip Wayback Machine. Logika inti modul ditunjukkan pada {G:fetch}. Setiap halaman yang berhasil diambil disimpan sebagai berkas HTML di dalam folder bernama sesuai domainnya, sedangkan halaman galat server (*soft 404*) dikenali dari judulnya dan dikeluarkan."))
a(("code", "fetch", "Coding Fungsi Pengambilan Halaman Bertingkat", [
    "def fetch_multi_method(url, session_googlebot,",
    "                       session_chrome, quick_mode=False):",
    "    errors = []",
    "    resp, m, err = _attempt(lambda u: session_googlebot.get(",
    "        u, timeout=TIMEOUT, verify=VERIFY_SSL), url,",
    "        \"googlebot_ua\")",
    "    if resp is not None:",
    "        return resp.text, m, \"live\", None",
    "    errors.append(f\"{m}: {err}\")",
    "    # ... metode 2: browser_ua (User-Agent Chrome), pola sama",
    "    if HAS_CLOUDSCRAPER:",
    "        # ... metode 3: cloudscraper, pola sama",
    "    if HAS_PLAYWRIGHT and ENABLE_HEADLESS_RENDER:",
    "        html_r, err_r = fetch_headless_render(url)",
    "        if html_r is not None:",
    "            return html_r, \"headless_render\", \"live\", None",
    "        errors.append(f\"headless_render: {err_r}\")",
    "    if quick_mode:",
    "        return None, None, None, \" | \".join(errors)",
    "    time.sleep(BACKOFF_SECONDS)",
    "    # ... ulang googlebot_ua dan browser_ua",
    "    if ENABLE_WAYBACK_FALLBACK:",
    "        html, err = fetch_wayback_snapshot(url, session_chrome)",
    "        if html is not None:",
    "            return html, \"wayback_archive\", \"archived\", None",
    "    return None, None, None, \" | \".join(errors)"]))
a(("p", "Dataset kelas normal (Label 0) dikumpulkan secara terpisah dengan tiga kategori. Kategori A berisi domain yang bersih total, yaitu tidak muncul pada log penemuan mana pun. Kategori B berisi host yang bersih tetapi berinduk pada institusi yang memiliki subdomain terinfeksi, sehingga model dilatih membedakan halaman bersih dan halaman terinfeksi dari institusi yang sama. Kategori C adalah *hard negative*, yaitu artikel atau berita kampus yang membahas bahaya judi online sehingga memuat kata kunci tetapi bukan promosi judi. Halaman Label 0 dipilih secara terarah (beranda, profil, berita, pengumuman) dan bukan melalui penelusuran menyeluruh, kemudian diperiksa judulnya secara manual. Pemeriksaan ini menyingkirkan dua domain yang lolos leksikon tetapi berisi SEO *spam* non-judi, dan halaman blokir seperti *Application Blocked* yang bukan konten institusi."))
a(("p", "Sebagai Layer 2, domain hasil pengumpulan dicocokkan dengan basis data TrustPositif Komdigi. Berkas TrustPositif memuat 175 entri `.ac.id` yang sebagian disamarkan, dan 0 dari 115 domain berstatus dimasukkan yang cocok pada saat pengecekan (5 November 2026). Hasil ini tidak dipakai untuk menentukan label karena ketiadaan sebuah domain pada daftar bukan bukti bahwa domain tersebut bersih. Domain Label 1 yang berasal dari satu infeksi yang sama dikelompokkan menjadi klaster berdasarkan kemiripan teks, kata kunci, dan tautan keluar, sehingga 215 domain terbagi menjadi 182 klaster infeksi independen. Klaster inilah yang dipakai sebagai satuan pembagian data pada subbab 4.1.6."))
a(("p", "Rekapitulasi dataset akhir ditunjukkan pada {T:dataset}. Dari 757 halaman Label 1 yang berhasil dimuat, 516 halaman memuat sedikitnya satu kata kunci pada teksnya dan dipakai sebagai kelas judi. Sebanyak 241 halaman tanpa kata kunci, misalnya halaman login, halaman tipis, atau konten yang baru muncul setelah render, dikeluarkan dari pelatihan dan tidak dijadikan kelas normal. Keputusan ini mencegah halaman berlabel judi tanpa bukti teks mengotori kelas normal, tetapi konsekuensinya model tidak pernah diuji pada konten judi yang tidak memuat kata kunci (dibahas pada subbab 4.3.4). Struktur penyimpanan dataset ditunjukkan pada {G:folder}."))
a(("table", "dataset", "Rekapitulasi Dataset Akhir",
   ["Kelas", "Domain", "Halaman", "Keterangan"],
   [["Judi (Label 1)", "215", "516", "757 dimuat; 241 tanpa kata kunci dikeluarkan"],
    ["Normal (Label 0)", "115", "522", "A: 275, B: 233, C: 14 halaman"],
    ["Total", "330", "1.038", "49,7% judi; 50,3% normal"]],
   [1400, 1000, 1000, 2436], ["l", "c", "c", "l"]))
a(("img", "folder", "Struktur Folder Dataset Hasil Pengumpulan", "struktur_folder.png", 10.0))

a(("h3", "Implementasi Pelabelan Heuristik"))
a(("p", "Pelabelan Layer 1 dilakukan dengan aturan heuristik berbasis leksikon 91 kata kunci judi online (Tabel 3.6). Sebuah halaman diberi label 1 apabila ditemukan sedikitnya satu kata kunci pada teks halaman atau pada alamatnya, dan label 0 apabila tidak ditemukan. Karena alamat asli halaman tidak tersimpan pada nama berkas, pencocokan alamat memakai alamat bentukan dari domain dan nama berkas. Aturan yang sama dipakai oleh *extension* untuk bendera meta dan alamat sehingga perilaku pelabelan dan inferensi konsisten. Kode aturan ditunjukkan pada {G:label}. Pencocokan memakai *substring* sehingga kata pendek seperti *toto* dapat cocok pada kata lain; karena itu 12 halaman Label 0 (kategori C) yang memuat kata kunci tetap dipertahankan sebagai kelas normal, sesuai ketentuan pengumpulan, dan halaman judi dengan bukti tunggal rawan salah label."))
a(("code", "label", "Coding Fungsi Pelabelan Heuristik", [
    "KEYWORDS = [",
    "    \"slot gacor\", \"slot online\", \"demo slot\", \"slot88\",",
    "    \"mahjong ways\", \"scatter hitam\", \"togel\", \"toto\",",
    "    \"maxwin\", \"jackpot\", \"pragmatic play\", \"pg soft\",",
    "    # ... 91 kata kunci lengkap pada Tabel 3.6",
    "]",
    "",
    "def heuristic_label(text, url):",
    "    text_lower, url_lower = text.lower(), url.lower()",
    "    hits = [k for k in KEYWORDS",
    "            if k in text_lower or k in url_lower]",
    "    return len(hits), hits",
    "",
    "def pseudo_url(domain, path):",
    "    slug = re.sub(r\"_[0-9a-f]{10}$\", \"\", Path(path).stem)",
    "    slug = \"\" if slug == \"index\" else slug",
    "    return f\"https://{domain}/{slug}\"",
    "",
    "n, hits = heuristic_label(text, pseudo_url(domain, p))",
    "label = 1 if n >= 1 else 0"]))

a(("h3", "Implementasi Praprosesing Teks"))
a(("p", "Praprosesing diterapkan pada setiap berkas HTML untuk menghasilkan teks bersih yang siap divektorisasi. Pembersihan HTML menghapus elemen *script*, *style*, dan komentar sebelum teks diambil, kemudian teks diseragamkan menjadi huruf kecil, simbol dan angka dihapus, spasi dirapikan, kata henti dibuang, dan setiap kata dikembalikan ke bentuk dasarnya dengan algoritma Nazief-Adriani melalui Sastrawi. Jumlah kata dibatasi 5.000 kata per halaman, sama dengan batas pada *extension*. Setelah praprosesing tidak ada halaman dengan teks kosong, dan seluruh 516 halaman judi masih memuat kata kunci. Median panjang teks halaman judi adalah 958,5 kata dibandingkan 474 kata pada halaman normal, perbedaan yang dapat menjadi isyarat tersamar bagi model. Contoh hasil setiap tahap ditunjukkan pada {T:praproses} dan kodenya pada {G:bersih}."))
a(("table", "praproses", "Contoh Hasil Praprosesing pada Satu Halaman",
   ["Tahapan", "Cuplikan Teks"],
   [["Teks mentah", "PAB IOM ITB 2026, Perkuat Sinergi Kampus dan Orang Tua Agar Tidak Ada Mimpi yang Terhenti"],
    ["Setelah pembersihan dan lowercasing", "pab iom itb perkuat sinergi kampus dan orang tua agar tidak ada mimpi yang terhenti"],
    ["Setelah penghapusan stopword", "pab iom itb perkuat sinergi kampus orang tua tidak mimpi terhenti"],
    ["Setelah stemming", "pab iom itb kuat sinergi kampus orang tua tidak mimpi henti"]],
   [1900, 3936], ["l", "l"]))
a(("code", "bersih", "Coding Fungsi Pembersihan dan Normalisasi Teks", [
    "def clean_html(html):",
    "    soup = BeautifulSoup(html, \"html.parser\")",
    "    for tag in soup([\"script\", \"style\"]):",
    "        tag.decompose()",
    "    for c in soup.find_all(",
    "            string=lambda s: isinstance(s, Comment)):",
    "        c.extract()",
    "    return soup.get_text(separator=\" \")",
    "",
    "def normalize_text(text):",
    "    text = (text or \"\").lower()",
    "    text = re.sub(r\"[^a-z\\s]\", \" \", text)",
    "    text = re.sub(r\"\\s+\", \" \", text).strip()",
    "    text = _stopword.remove(text)",
    "    out = []",
    "    for w in text.split()[:MAX_WORDS]:",
    "        if w not in _stem_cache:",
    "            _stem_cache[w] = _stemmer.stem(w)",
    "        out.append(_stem_cache[w])",
    "    return \" \".join(out)"]))

a(("h3", "Ekstraksi Fitur"))
a(("p", "Ekstraksi fitur menghasilkan dua kelompok fitur yang digabung (*feature fusion*). Kelompok pertama adalah fitur teks berbasis N-Gram, yaitu TF-IDF dengan rentang N-Gram satu sampai dua kata dan batas 3.000 fitur terbanyak sebagaimana dirancang pada Tabel 3.10. Penggunaan bigram memungkinkan model menangkap frasa yang lazim pada konten judi seperti *slot gacor*. Parameternya ditunjukkan pada {T:tfidf}."))
a(("table", "tfidf", "Parameter TF-IDF Vectorizer yang Digunakan",
   ["Parameter", "Nilai"],
   [["ngram_range", "(1, 2)"], ["max_features", "3.000"], ["Data yang digunakan untuk fit", "Data latih saja"],
    ["Jumlah fitur teks aktual", "3.000"]],
   [3300, 2536], ["l", "c"]))
a(("p", "Kelompok kedua adalah delapan fitur struktural yang diekstraksi dari tautan dan struktur HTML/DOM (Tabel 3.11), yaitu jumlah tautan, rasio tautan eksternal, jumlah tautan bernama judi, jumlah *iframe*, keberadaan elemen tersembunyi, kedalaman DOM, bendera kata kunci pada meta, dan bendera kata kunci pada alamat. Nilai fitur struktural diskalakan ke rentang 0 sampai 1 dengan MinMaxScaler yang hanya di-*fit* pada data latih lalu diterapkan dengan parameter yang sama pada data uji dan data *holdout* agar tidak terjadi kebocoran informasi. Penggabungan keduanya menghasilkan 3.008 fitur untuk setiap halaman, sehingga matriks data latih berukuran 712 × 3.008 sebagaimana pada {G:fitur}."))
a(("code", "fitur", "Coding Pembentukan Fitur TF-IDF dan Fitur Struktural", [
    "STRUCT_COLS_ORDER = [",
    "    \"FLNK_01_link_count\", \"FLNK_02_ext_ratio\",",
    "    \"FLNK_03_gamb_link\", \"FSTR_01_iframe_count\",",
    "    \"FSTR_02_has_hidden\", \"FSTR_03_dom_depth\",",
    "    \"FMETA_01_meta_judi_flag\", \"FURL_01_url_flag\",",
    "]",
    "",
    "vec = TfidfVectorizer(ngram_range=(1, 2), max_features=3000)",
    "vec.fit(train.teks_bersih)",
    "scaler = MinMaxScaler().fit(",
    "    train[STRUCT_COLS_ORDER].to_numpy(dtype=float))",
    "",
    "def build_X(df, vectorizer, scaler):",
    "    X_text = vectorizer.transform(df[\"teks_bersih\"])",
    "    X_struct = sp.csr_matrix(scaler.transform(",
    "        df[STRUCT_COLS_ORDER].to_numpy(dtype=float)))",
    "    return sp.hstack([X_text, X_struct]).tocsr()",
    "",
    "X = build_X(train, vec, scaler)   # (712 x 3008)"]))

a(("h3", "Pembagian Data"))
a(("p", "Dataset dibagi menjadi data latih, data uji, dan data *holdout* dengan perbandingan 70:20:10 menggunakan *random seed* 42. Pembagian dilakukan pada tingkat kelompok, bukan halaman: untuk kelas judi satuannya adalah klaster infeksi, dan untuk kelas normal satuannya adalah domain. Dengan demikian seluruh halaman satu infeksi atau satu domain berada pada himpunan yang sama dan model diuji pada domain yang belum pernah dilihat. Pembagian dilakukan terpisah untuk tiap kelas dan dipenuhi secara serakah pada urutan acak. Untuk memperkaya data *holdout* sesuai subbab 3.7, klaster yang seluruh domainnya berstatus non-Google diprioritaskan masuk ke *holdout*. Hasilnya ditunjukkan pada {T:split} dan tidak ada domain atau klaster yang terbagi lebih dari satu himpunan; kodenya ada pada {G:split}."))
a(("table", "split", "Hasil Pembagian Data",
   ["Himpunan", "Domain", "Klaster", "Halaman", "Judi", "Normal"],
   [["Data latih", "230", "202", "712", "348", "364"],
    ["Data uji", "70", "65", "221", "116", "105"],
    ["Data holdout", "30", "30", "105", "52", "53"],
    ["Total", "330", "297", "1.038", "516", "522"]],
   [1236, 900, 900, 1000, 800, 1000], ["l", "c", "c", "c", "c", "c"]))
a(("p", "Seluruh halaman judi pada data *holdout* (52 halaman) berasal dari klaster non-Google, sehingga *holdout* tidak memuat halaman judi \"reguler\". Sebagai akibatnya, pembanding reguler untuk TC-06 diambil dari data uji, bukan dari *holdout*."))
a(("code", "split", "Coding Alokasi Pembagian Data per Klaster dan Domain", [
    "def alokasi(groups, target, rng, prioritas=()):",
    "    pri = [g for g in groups if g in set(prioritas)]",
    "    rest = [g for g in groups if g not in set(prioritas)]",
    "    rng.shuffle(pri); rng.shuffle(rest)",
    "    chosen, total = [], 0",
    "    for g in pri + rest:",
    "        if total >= target:",
    "            break",
    "        if chosen and total + groups[g] > target * 1.5:",
    "            continue",
    "        chosen.append(g); total += groups[g]",
    "    return chosen",
    "",
    "# per label: holdout 10% (non-dork diprioritaskan),",
    "# test 20%, sisanya train; grup = klaster / domain",
    "hold = alokasi(groups, 0.10 * n, rng, prioritas=murni)",
    "test = alokasi(rest, 0.20 * n, rng)",
    "...",
    "assert df.groupby([\"label\", \"group_id\"]).split.nunique().max() == 1",
    "assert df.groupby(\"domain\").split.nunique().max() == 1"]))

a(("h3", "Penanganan Ketidakseimbangan Kelas"))
a(("p", "Proporsi kelas judi pada data latih adalah 48,9% (348 halaman judi dan 364 halaman normal), sehingga berada di atas ambang 40% yang ditetapkan pada rancangan. Oleh karena itu SMOTE tidak diterapkan dan kedua model dilatih pada data asli tanpa data sintetis. Pada model dipakai pembobotan kelas (*class_weight*) sebagai salah satu hyperparameter yang disetel."))

a(("h3", "Pelatihan dan Penyetelan Hyperparameter Random Forest"))
a(("p", "Model Random Forest dilatih dengan menyetel hyperparameter melalui GridSearchCV menggunakan StratifiedKFold lima lipatan dan F1-score kelas judi sebagai metrik pemilihan. Ruang pencarian mengikuti Tabel 3.12 dengan 648 kombinasi, sehingga terdapat 3.240 kali pelatihan yang selesai dalam sekitar 12,2 menit. Kombinasi terbaik beserta skor validasi silangnya ditunjukkan pada {T:rf} dan kodenya pada {G:rf}. Skor validasi silang sebesar 0,9898 perlu dibaca hati-hati karena StratifiedKFold tidak mengelompokkan data per domain, sehingga halaman satu domain dapat berada pada lipatan latih dan lipatan validasi; skor tersebut cenderung optimistis, sedangkan data uji dan *holdout* tidak terpengaruh karena dipisahkan per kelompok."))
a(("table", "rf", "Hasil Penyetelan Hyperparameter Random Forest",
   ["Parameter", "Ruang Pencarian", "Nilai Terbaik"],
   [["n_estimators", "[100, 200, 300]", "200"], ["max_depth", "[None, 10, 20, 30]", "20"],
    ["min_samples_split", "[2, 5, 10]", "10"], ["min_samples_leaf", "[1, 2, 4]", "1"],
    ["max_features", "[sqrt, log2, None]", "sqrt"], ["class_weight", "[balanced, None]", "balanced"],
    ["F1-score validasi silang", "–", "0,9898"]],
   [2036, 2300, 1500], ["l", "l", "c"]))
a(("code", "rf", "Coding Pipeline dan GridSearchCV Random Forest", [
    "use_smote = minority_ratio < SMOTE_THRESHOLD   # 0.40",
    "steps = ([(\"smote\", SMOTE(k_neighbors=5, random_state=SEED))]",
    "         if use_smote else [])    # tidak diterapkan (48,9%)",
    "steps.append((\"rf\", RandomForestClassifier(",
    "    random_state=SEED, n_jobs=1)))",
    "",
    "PARAM_GRID = {",
    "    \"rf__n_estimators\": [100, 200, 300],",
    "    \"rf__max_depth\": [None, 10, 20, 30],",
    "    \"rf__min_samples_split\": [2, 5, 10],",
    "    \"rf__min_samples_leaf\": [1, 2, 4],",
    "    \"rf__max_features\": [\"sqrt\", \"log2\", None],",
    "    \"rf__class_weight\": [\"balanced\", None],",
    "}",
    "gs = GridSearchCV(Pipeline(steps), PARAM_GRID, scoring=\"f1\",",
    "    cv=StratifiedKFold(n_splits=5, shuffle=True,",
    "                       random_state=SEED),",
    "    n_jobs=-1, refit=True, verbose=1)",
    "gs.fit(X, y)",
    "",
    "rf = gs.best_estimator_.named_steps[\"rf\"]",
    "joblib.dump(rf, MODEL_DIR / \"model.pkl\")",
    "joblib.dump(vec, MODEL_DIR / \"vectorizer.pkl\")",
    "joblib.dump(scaler, MODEL_DIR / \"scaler.pkl\")"]))

a(("h3", "Implementasi LightGBM sebagai Model Pembanding"))
a(("p", "Sesuai rancangan pada subbab 3.8.2, LightGBM dilatih sebagai model pembanding dengan data latih, fitur, dan skema validasi silang yang sama dengan Random Forest sehingga perbandingan dilakukan pada kondisi yang setara. Bab III tidak menetapkan ruang pencarian LightGBM, sehingga ruang pencarian 108 kombinasi pada {T:lgb} ditetapkan oleh penulis. Penyetelan selesai dalam sekitar 4,3 menit dengan skor validasi silang 0,9884. Kode pelatihan ditunjukkan pada {G:lgb}."))
a(("table", "lgb", "Hasil Penyetelan Hyperparameter LightGBM",
   ["Parameter", "Ruang Pencarian", "Nilai Terbaik"],
   [["n_estimators", "[100, 200, 300]", "300"], ["learning_rate", "[0,05; 0,1]", "0,1"],
    ["num_leaves", "[15, 31, 63]", "15"], ["max_depth", "[-1, 10, 20]", "-1"],
    ["class_weight", "[balanced, None]", "balanced"], ["F1-score validasi silang", "–", "0,9884"]],
   [2036, 2300, 1500], ["l", "l", "c"]))
a(("code", "lgb", "Coding Pelatihan LightGBM", [
    "PARAM_GRID = {",
    "    \"lgbm__n_estimators\": [100, 200, 300],",
    "    \"lgbm__learning_rate\": [0.05, 0.1],",
    "    \"lgbm__num_leaves\": [15, 31, 63],",
    "    \"lgbm__max_depth\": [-1, 10, 20],",
    "    \"lgbm__class_weight\": [\"balanced\", None],",
    "}",
    "steps = [(\"lgbm\", LGBMClassifier(random_state=SEED,",
    "                                n_jobs=1, verbose=-1))]",
    "gs = GridSearchCV(Pipeline(steps), PARAM_GRID, scoring=\"f1\",",
    "    cv=StratifiedKFold(n_splits=5, shuffle=True,",
    "                       random_state=SEED),",
    "    n_jobs=-1, refit=True, verbose=1)",
    "gs.fit(X, y)   # X, y = data latih yang sama dengan RF",
    "print(gs.best_params_, gs.best_score_)",
    "",
    "model = gs.best_estimator_.named_steps[\"lgbm\"]",
    "joblib.dump(model, MODEL_DIR / \"model_lightgbm.pkl\")"]))

a(("h3", "Implementasi Browser Extension"))
a(("p", "Model hasil pelatihan diekspor menggunakan joblib bersama vectorizer TF-IDF dan scaler fitur struktural, sehingga inferensi mengikuti tahapan yang sama dengan pelatihan. Berkas-berkas tersebut dimuat satu kali oleh server Flask lokal. *Browser extension* dibangun dengan standar Manifest V3 dan terdiri atas komponen pada {T:komponen}. Seluruh kode, termasuk skrip instalasi dan peluncuran satu perintah (`jalankan.ps1`) yang memasang dependensi, menyalakan server, dan membuka Microsoft Edge dengan *extension* termuat, disimpan pada repositori GitHub di " + REPO + ". Skrip ini mewujudkan arahan pembimbing agar *extension* dapat langsung dicoba di komputer laboratorium."))
a(("table", "komponen", "Komponen Sistem Browser Extension",
   ["Komponen", "Fungsi"],
   [["manifest.json", "Konfigurasi Manifest V3: izin storage, activeTab, scripting; domain .ac.id"],
    ["scanner.js, content.js", "Mengekstraksi teks, tautan, struktur DOM, dan elemen tersembunyi; menampilkan lencana dan sorotan di halaman"],
    ["background.js", "Service worker: mengirim data ke Flask, mengatur lencana ikon, menyimpan riwayat"],
    ["popup.html/js", "Antarmuka hasil: label, peluang judi, alasan, bukti, dan struktur halaman"],
    ["options.html/js", "Pengaturan: model, ambang, domain dikecualikan, riwayat dan ekspor CSV"],
    ["backend/app.py, engine.py", "Server Flask: praprosesing, 8 fitur struktural, TF-IDF, prediksi RF atau LightGBM"]],
   [1700, 4136], ["l", "l"]))
a(("p", "Alur kerjanya adalah sebagai berikut. Ketika pengguna membuka halaman, *content script* memeriksa apakah domain berakhiran .ac.id; jika bukan, *extension* pasif, tetapi pengguna dapat memindai halaman mana pun secara manual lewat tombol pada *popup* dengan izin *activeTab*. Pada domain .ac.id, *content script* mengekstraksi teks, tautan, dan struktur DOM, lalu *service worker* mengirimkannya ke Flask API. Server menghitung fitur, memprediksi peluang kelas judi, menyusun bukti berbasis aturan, dan mengembalikan hasil dalam format JSON. Hasil ditampilkan sebagai *popup*, lencana ikon, serta lencana dan sorotan pada halaman. *Extension* juga memindai ulang halaman bila isinya berubah, karena konten judi sering disisipkan melalui JavaScript setelah halaman dimuat."))
a(("p", "Dibandingkan rancangan pada Bab III, implementasi disempurnakan pada beberapa hal. Pertama, keluaran dikelompokkan menjadi tiga status: Aman, Waspada (model menilai aman tetapi ada bukti aturan), dan Terindikasi judi. Kedua, hasil disertai alasan dan bukti, yaitu kata kunci utuh, elemen tersembunyi yang memuat kata kunci (CSS *display:none*, *visibility:hidden*, *opacity:0*, *font-size:0*, atau di luar layar), dan tautan keluar bernama judi. Ketiga, fitur dihitung dengan cara yang sama dengan pelatihan: teks mencakup elemen tersembunyi, tautan dikirim dalam bentuk mentah, dan bendera meta dan alamat memakai 91 kata kunci, bukan 17 kata pada versi purwarupa awal. Keempat, ditambahkan halaman pengaturan, riwayat dengan ekspor CSV, dan ringkasan laporan yang dapat disalin untuk pengelola situs. Kelima, ditambahkan anggaran waktu *stemming* pada server agar respons tetap di bawah dua detik pada halaman yang panjang."))
a(("code", "manifest", "Coding Konfigurasi Manifest V3", [
    "{",
    "  \"manifest_version\": 3,",
    "  \"name\": \"Deteksi Judi Online .ac.id\",",
    "  \"version\": \"2.0.0\",",
    "  \"action\": { \"default_popup\": \"popup.html\" },",
    "  \"options_page\": \"options.html\",",
    "  \"background\": { \"service_worker\": \"background.js\",",
    "                  \"type\": \"module\" },",
    "  \"content_scripts\": [{",
    "    \"matches\": [\"*://*.ac.id/*\", \"*://ac.id/*\"],",
    "    \"js\": [\"lexicon.js\", \"scanner.js\", \"content.js\"],",
    "    \"run_at\": \"document_idle\"",
    "  }],",
    "  \"permissions\": [\"storage\", \"activeTab\", \"scripting\"],",
    "  \"host_permissions\": [",
    "    \"*://*.ac.id/*\", \"*://ac.id/*\",",
    "    \"http://localhost/*\", \"http://127.0.0.1/*\"",
    "  ]",
    "}"]))
a(("code", "scanner", "Coding Ekstraksi Teks dan Deteksi Elemen Tersembunyi pada Content Script", [
    "function extractText() {          // termasuk teks tersembunyi",
    "  const out = []; let len = 0;",
    "  const w = textWalker(document.documentElement);",
    "  let n;",
    "  while ((n = w.nextNode())) {",
    "    const v = n.nodeValue.trim();",
    "    if (!v) continue;",
    "    out.push(v); len += v.length + 1;",
    "    if (len >= MAX_CHARS) break;   // 60.000 karakter",
    "  }",
    "  return out.join(\" \").slice(0, MAX_CHARS);",
    "}",
    "",
    "function concealReason(el) {",
    "  if (el.getClientRects().length === 0)",
    "    return \"display:none / tidak dirender\";",
    "  const cs = getComputedStyle(el);",
    "  if (cs.visibility === \"hidden\") return \"visibility:hidden\";",
    "  if (parseFloat(cs.fontSize) === 0) return \"font-size:0\";",
    "  // ... opacity:0 pada leluhur, di luar layar, ukuran 0",
    "  return null;",
    "}"]))
a(("code", "engine", "Coding Inti Prediksi pada Server Flask", [
    "def predict(data, model_name=\"random_forest\", threshold=0.5):",
    "    clean, stem_approx = normalize_text_ex(raw_text)",
    "    X_text = vectorizer.transform([clean])",
    "    struct_raw, ext, gamb = structural_features(data)",
    "    struct = scaler.transform(np.array([struct_raw]))",
    "    X = sp.hstack([X_text, sp.csr_matrix(struct)]).tocsr()",
    "    p_judi = float(model.predict_proba(X)[0][1])",
    "",
    "    kw = keyword_evidence(raw_text, url)   # kata utuh",
    "    if p_judi >= threshold:",
    "        label = \"judi\"",
    "    elif kw[\"strong_total\"] or hidden or judi_links:",
    "        label = \"waspada\"   # model aman, bukti aturan ada",
    "    else:",
    "        label = \"aman\"",
    "    return {\"label\": label, \"ml\": {\"p_judi\": p_judi, ...},",
    "            \"reasons\": reasons, \"evidence\": evidence, ...}"]))
a(("img", "popup", "Tampilan Popup Extension pada Halaman Normal (kiri) dan Halaman Terindikasi Judi (kanan)", "popup_aman_judi.png", 9.0))
a(("img", "lencana", "Lencana dan Panel Penjelasan pada Halaman yang Menyembunyikan Teks Judi dengan CSS", "halaman_lencana.png", 8.5))
a(("img", "pengaturan", "Halaman Pengaturan dan Riwayat Extension", "pengaturan.png", 6.5))
a(("ph", "github", "Halaman Repositori GitHub Penelitian",
   "Tangkapan layar halaman repositori GitHub (setelah repo dijadikan Public): " + REPO + " . Tampilkan daftar folder (backend, docs, extension, scripts, tests), berkas jalankan.ps1, dan README."))

# ------------------------------------------------------------------------------------------ 4.2
a(("h2", "Pengujian dan Hasil"))
a(("h3", "Skenario Pengujian"))
a(("p", f"Pengujian dilakukan dalam dua lapisan sesuai subbab 3.9. Lapisan pertama adalah pengujian model secara luring pada data uji (221 halaman, 70 domain) dan data *holdout* (105 halaman, 30 domain) dengan skenario Tabel 3.15. Lapisan kedua adalah pengujian fungsional dan kinerja *browser extension* dengan skenario Tabel 3.16. Pengujian *extension* dijalankan pada Microsoft Edge {EDGE} dan diulang pada Chromium 156 dengan 50 halaman nyata (25 judi dan 25 normal) yang diambil acak dari data uji dan *holdout*. Halaman tersebut disajikan pada alamat aslinya (misalnya https://domain.ac.id/...) melalui intersepsi jaringan, sehingga *content script* .ac.id berjalan otomatis tanpa internet. Evaluasi model memakai *accuracy*, *precision*, *recall*, F1-score, dan ROC-AUC dengan kelas judi sebagai kelas positif, dengan *recall* diprioritaskan karena halaman judi yang lolos berdampak lebih besar daripada kesalahan sebaliknya. Seluruh pengujian dilakukan oleh skrip otomatis pada repositori sehingga dapat diulang."))
a(("p", "Model yang dipasang pada *extension* diperiksa identik dengan hasil pelatihan (nilai hash berkas sama), dan evaluasi ulang pada data uji dan *holdout* menghasilkan angka yang sama persis dengan laporan pelatihan."))

a(("h3", "Hasil Pengujian Model"))
a(("p", "Hasil evaluasi kedua model pada data uji dan data *holdout* ditunjukkan pada {T:metrik} (skenario TC-01 dan TC-02). Pada data uji, Random Forest memperoleh F1-score " + f(rf["test"]["f1"]) + " dan LightGBM " + f(lg["test"]["f1"]) + "; pada data *holdout* masing-masing " + f(rf["holdout"]["f1"]) + " dan " + f(lg["holdout"]["f1"]) + ". Seluruh nilai metrik tersedia sehingga TC-01 dan TC-02 berhasil."))
rows = []
for nm, lab in (("random_forest", "Random Forest"), ("lightgbm", "LightGBM")):
    for s, sl in (("test", "Uji"), ("holdout", "Holdout")):
        r = m[nm][s]
        rows.append([lab if s == "test" else "", sl, f(r["accuracy"]), f(r["precision"]), f(r["recall"]), f(r["f1"]), f(r["roc_auc"], 4)])
a(("table", "metrik", "Hasil Evaluasi Random Forest dan LightGBM pada Data Uji dan Data Holdout",
   ["Model", "Data", "Acc.", "Prec.", "Recall", "F1", "ROC-AUC"], rows,
   [1300, 900, 700, 700, 750, 700, 786], ["l", "l", "c", "c", "c", "c", "c"]))
a(("p", "Rincian prediksi disajikan dalam bentuk *confusion matrix* pada {T:cm} yang sekaligus memuat *false positive rate* (FPR) untuk skenario TC-03, dan divisualisasikan pada {G:cm}. Random Forest tidak menghasilkan *false positive* pada data uji (FPR 0,0%) dan satu pada data *holdout* (FPR " + pct(rf["holdout"]["fpr"]) + "), sedangkan LightGBM tidak menghasilkan *false positive* sama sekali. Kesalahan yang lebih penting adalah *false negative*: Random Forest melewatkan " + str(rf["test"]["fn"]) + " halaman judi pada data uji dan " + str(rf["holdout"]["fn"]) + " pada data *holdout*, sedangkan LightGBM masing-masing " + str(lg["test"]["fn"]) + " dan " + str(lg["holdout"]["fn"]) + "."))
rows = []
for nm, lab in (("random_forest", "Random Forest"), ("lightgbm", "LightGBM")):
    for s, sl in (("test", "Uji"), ("holdout", "Holdout")):
        r = m[nm][s]
        rows.append([lab if s == "test" else "", sl, str(r["tn"]), str(r["fp"]), str(r["fn"]), str(r["tp"]), pct(r["fpr"])])
a(("table", "cm", "Confusion Matrix dan False Positive Rate",
   ["Model", "Data", "TN", "FP", "FN", "TP", "FPR"], rows,
   [1436, 1000, 650, 650, 700, 700, 700], ["l", "l", "c", "c", "c", "c", "c"]))
a(("img", "cm", "Confusion Matrix Random Forest (atas) dan LightGBM (bawah) pada Data Uji (kiri) dan Data Holdout (kanan)", "cm_2x2.png", 8.5))

a(("h3", "Analisis Kesalahan Klasifikasi"))
a(("p", "Kesalahan Random Forest berjumlah sepuluh halaman dan dirinci pada {T:salah}. Seluruh *false negative* adalah halaman yang hanya memuat satu sampai tiga kata kunci, padahal median halaman judi memuat lima kata kunci, sehingga bukti teksnya lemah dan probabilitas judinya tertahan di bawah 0,5 (0,29–0,49). Empat halaman pada data *holdout* berasal dari satu domain (ununtb.ac.id), sehingga pada tingkat domain terdapat lebih sedikit kesalahan daripada jumlah halamannya. Satu-satunya *false positive* adalah artikel literasi digital pencegahan judi online (*hard negative* kategori C) dengan probabilitas 0,52, yang menunjukkan bahwa model sulit membedakan artikel edukasi dan promosi ketika keduanya memuat kata yang sama."))
a(("table", "salah", "Rincian Kesalahan Klasifikasi Random Forest",
   ["Jenis", "Domain", "Halaman", "P(judi)"],
   [["FN (uji)", "dapen.uhamka.ac.id; fisip.uhamka.ac.id", "2", "0,46; 0,49"],
    ["FN (uji)", "hope.poltekparmedan.ac.id; www.stkipkieraha.ac.id", "2", "0,32; 0,39"],
    ["FN (holdout)", "ununtb.ac.id", "4", "0,29–0,32"],
    ["FN (holdout)", "jurnal.staim-probolinggo.ac.id", "1", "0,40"],
    ["FP (holdout)", "apiksibba.ac.id", "1", "0,52"]],
   [1100, 2336, 1100, 1300], ["l", "l", "c", "c"]))

a(("h3", "Analisis Fitur Penting"))
a(("p", "Kontribusi fitur dianalisis melalui nilai *feature importance* Random Forest pada {T:fitur_penting} dan {G:fi}. Berbeda dengan percobaan awal pada dataset lebih kecil, kontribusi kini tersebar: fitur teratas, yaitu bigram *slot gacor*, hanya bernilai 0,037, dan tidak ada fitur yang mendominasi. Sebagian besar fitur teratas adalah istilah judi (*slot gacor*, *slot*, *gacor*, *togel*, *deposit*, *toto*), tetapi muncul pula kata yang menandai pola halaman promosi seperti *login*, *daftar*, *rp*, dan *com*. Fitur struktural tertinggi adalah rasio tautan eksternal (peringkat 6), disusul bendera meta (peringkat 21) dan jumlah tautan bernama judi (peringkat 28), sehingga fitur tautan dan struktur memberi kontribusi tambahan, tetapi bukan penentu utama. Karena label berasal dari kata kunci yang sama dengan fitur teks, nilai-nilai ini menunjukkan bahwa model sebagian besar mempelajari ulang leksikon pelabelan dan tidak membuktikan kemampuan mendeteksi judi tanpa kata kunci."))
a(("table", "fitur_penting", "Fitur dengan Kontribusi Terbesar pada Random Forest",
   ["Peringkat", "Fitur", "Importance", "Jenis"],
   [["1", "slot gacor", "0,0367", "Teks"], ["2", "slot", "0,0352", "Teks"], ["3", "gacor", "0,0303", "Teks"],
    ["4", "gacor slot", "0,0212", "Teks"], ["5", "login", "0,0182", "Teks"],
    ["6", "FLNK_02_ext_ratio", "0,0168", "Struktural"], ["7", "situs", "0,0153", "Teks"],
    ["8", "com", "0,0149", "Teks"], ["9", "slot slot", "0,0130", "Teks"], ["10", "menang", "0,0125", "Teks"]],
   [1100, 2136, 1500, 1100], ["c", "l", "c", "l"]))
a(("img", "fi", "Fitur dengan Kontribusi Terbesar pada Random Forest (merah: struktural, biru: TF-IDF)", "feature_importance.png", 8.0))

a(("h3", "Perbandingan Random Forest dan LightGBM"))
a(("p", "Perbandingan dilakukan pada data uji dan *holdout* yang identik sesuai Tabel 3.13, dengan hasil pada {T:metrik}. Untuk menilai apakah selisih kinerja bermakna secara statistik dilakukan uji McNemar eksak pada prediksi kedua model (skenario TC-04), dan hasilnya ditunjukkan pada {T:mcnemar}. Pada kedua himpunan selisihnya tidak bermakna pada taraf 0,05. Jumlah halaman yang diprediksi berbeda (b + c) sangat kecil, sehingga daya uji rendah dan hasil ini bersifat indikatif."))
a(("table", "mcnemar", "Hasil Uji McNemar Random Forest dan LightGBM",
   ["Data", "b", "c", "p-value", "Kesimpulan"],
   [["Uji", str(mc["test"]["b_rf_benar_lgbm_salah"]), str(mc["test"]["c_rf_salah_lgbm_benar"]), f(mc["test"]["p_value"]), "Tidak bermakna"],
    ["Holdout", str(mc["holdout"]["b_rf_benar_lgbm_salah"]), str(mc["holdout"]["c_rf_salah_lgbm_benar"]), f(mc["holdout"]["p_value"], 4), "Tidak bermakna"]],
   [1100, 600, 600, 1236, 2300], ["l", "c", "c", "c", "l"]))
a(("p", "Keterangan: b adalah jumlah halaman yang diprediksi benar oleh Random Forest tetapi salah oleh LightGBM, sedangkan c adalah kebalikannya. Hasil dinyatakan bermakna apabila p-value kurang dari 0,05. Kode evaluasi ditunjukkan pada {G:eval}."))
a(("code", "eval", "Coding Evaluasi Model dan Uji McNemar", [
    "for split in [\"test\", \"holdout\"]:",
    "    d = df[df.split == split].reset_index(drop=True)",
    "    X, y = build_X(d, vec, scaler), d.label.to_numpy()",
    "    proba = model.predict_proba(X)[:, 1]",
    "    pred = (proba >= 0.5).astype(int)",
    "    rep = classification_report(y, pred, labels=[0, 1],",
    "        target_names=[\"normal\", \"judi\"], output_dict=True)",
    "    cm = confusion_matrix(y, pred, labels=[0, 1])",
    "    auc = roc_auc_score(y, proba)",
    "",
    "    # --- uji McNemar RF vs LightGBM ---",
    "    rf_ok = d.pred_random_forest == d.label",
    "    lg_ok = d.pred_lightgbm == d.label",
    "    a = int((rf_ok & lg_ok).sum())     # keduanya benar",
    "    b = int((rf_ok & ~lg_ok).sum())    # RF benar, LGBM salah",
    "    c = int((~rf_ok & lg_ok).sum())    # RF salah, LGBM benar",
    "    e = int((~rf_ok & ~lg_ok).sum())   # keduanya salah",
    "    p_value = mcnemar([[a, b], [c, e]], exact=True).pvalue"]))

a(("h3", "Pengukuran Waktu Inferensi dan Evaluasi pada Halaman Non-Google Dork"))
rfi, lgi = t5["random_forest"], t5["lightgbm"]
a(("p", f"Skenario TC-05 mengukur waktu prediksi server Flask melalui HTTP pada {t5['jumlah_halaman']} halaman data uji dan *holdout* dengan teks dibatasi 60.000 karakter seperti pada *extension*. Hasilnya ditunjukkan pada {{T:inferensi}}. Pada lintasan pertama, yang mewakili kondisi terburuk karena kata baru harus di-*stem*, Random Forest membutuhkan rata-rata {n(rfi['server_total_ms']['rata_rata'])} ms dan paling lama {n(rfi['server_total_ms']['maks'])} ms, tidak ada halaman yang melebihi 2.000 ms. Waktu prediksi model itu sendiri hanya {n(rfi['predict_ms']['rata_rata'], 1)} ms; sebagian besar waktu dipakai untuk *stemming* Sastrawi. Perbandingan kedua model pada tabel ini tidak setara karena lintasan kedua memanfaatkan cache *stemming* yang terisi pada lintasan pertama. Label yang dihasilkan server dari HTML mentah sama dengan prediksi luring pada {rfi['paritas_label_dengan_offline']} halaman untuk kedua model."))
a(("table", "inferensi", "Waktu Respons Server per Halaman (ms)",
   ["Model dan kondisi", "Rata-rata", "Median", "P95", "Maks"],
   [["Random Forest, lintasan 1 (cache dingin)", n(rfi["server_total_ms"]["rata_rata"]), n(rfi["server_total_ms"]["median"]), n(rfi["server_total_ms"]["p95"]), n(rfi["server_total_ms"]["maks"])],
    ["LightGBM, lintasan 2 (cache hangat)", n(lgi["server_total_ms"]["rata_rata"]), n(lgi["server_total_ms"]["median"]), n(lgi["server_total_ms"]["p95"]), n(lgi["server_total_ms"]["maks"])]],
   [2536, 900, 800, 800, 800], ["l", "c", "c", "c", "c"]))
r1, r2, r3, r4 = (nd["random_forest"][k] for k in ("recall_nondork_gabungan", "recall_reguler_test", "recall_nondork_test", "recall_nondork_holdout"))
l1, l2 = nd["lightgbm"]["recall_nondork_gabungan"], nd["lightgbm"]["recall_reguler_test"]
a(("p", f"Skenario TC-06 menguji model pada halaman judi dari klaster non-Google (102 halaman pada data uji dan *holdout*) dibandingkan halaman judi reguler pada data uji (66 halaman). Hasilnya ditunjukkan pada {{T:nondork}}. Tidak ada penurunan yang signifikan pada taraf 0,05 untuk kedua model, tetapi Random Forest cenderung menurun dari {pct(r2['recall'])} menjadi {pct(r1['recall'])} (p = {f(nd['random_forest']['fisher_p_gabungan_vs_reguler'])}), sedangkan LightGBM tidak menurun ({pct(l1['recall'])} berbanding {pct(l2['recall'])}). Dengan jumlah data sekecil ini, penurunan sebesar itu tidak dapat dikesampingkan. Perlu ditegaskan bahwa kelompok non-Google di sini bukan sampel berlabel manual terpisah seperti dirancang pada subbab 3.9, melainkan halaman dari dataset yang sama dengan label kata kunci."))
a(("table", "nondork", "Recall Kelas Judi pada Halaman Non-Google Dork dan Reguler",
   ["Model", "Non-dork", "Reguler (uji)", "p (Fisher)"],
   [["Random Forest", f"{r1['tp']}/{r1['n']} = {pct(r1['recall'])}", f"{r2['tp']}/{r2['n']} = {pct(r2['recall'])}", f(nd["random_forest"]["fisher_p_gabungan_vs_reguler"])],
    ["LightGBM", f"{l1['tp']}/{l1['n']} = {pct(l1['recall'])}", f"{l2['tp']}/{l2['n']} = {pct(l2['recall'])}", f(nd["lightgbm"]["fisher_p_gabungan_vs_reguler"])]],
   [1500, 1700, 1500, 1136], ["l", "c", "c", "c"]))

a(("h3", "Rekapitulasi Pengujian Model"))
a(("p", "Hasil pengujian model terhadap kriteria keberhasilan pada Tabel 3.15 dirangkum pada {T:rekap_model}."))
a(("table", "rekap_model", "Hasil Pengujian Model Machine Learning",
   ["Kode", "Skenario", "Hasil", "Status"],
   [["TC-01", "Evaluasi data uji", f"Acc. {f(rf['test']['accuracy'])}; F1 {f(rf['test']['f1'])}; ROC-AUC {f(rf['test']['roc_auc'],4)} (RF)", "Berhasil"],
    ["TC-02", "Evaluasi data holdout", f"Acc. {f(rf['holdout']['accuracy'])}; F1 {f(rf['holdout']['f1'])}; ROC-AUC {f(rf['holdout']['roc_auc'],3)} (RF)", "Berhasil"],
    ["TC-03", "False positive rate", f"FPR RF {pct(rf['test']['fpr'])} (uji), {pct(rf['holdout']['fpr'])} (holdout)", "Berhasil"],
    ["TC-04", "Uji McNemar", f"p = {f(mc['test']['p_value'])} (uji); {f(mc['holdout']['p_value'],4)} (holdout)", "Berhasil"],
    ["TC-05", "Waktu inferensi Flask", f"Rata-rata {n(rfi['server_total_ms']['rata_rata'])} ms; maks. {n(rfi['server_total_ms']['maks'])} ms", "Berhasil"],
    ["TC-06", "Independent validation set", f"Recall RF {pct(r1['recall'])} vs {pct(r2['recall'])}; tidak signifikan", "Berhasil dengan catatan"]],
   [800, 1500, 2336, 1200], ["l", "l", "l", "l"]))

a(("h3", "Hasil Pengujian Browser Extension"))
a(("p", f"Hasil pengujian *browser extension* pada Microsoft Edge {EDGE_MAJOR} ditunjukkan pada {{T:ext}} dengan skenario Tabel 3.16. Hasil pada Chromium identik: label yang dihasilkan sama pada seluruh 50 halaman. Pada TC-01, {c1['terdeteksi_judi']} dari {c1['halaman']} halaman judi berlabel *Terindikasi konten judi* dan {c1['waspada']} halaman berlabel *Waspada*; tidak ada halaman judi yang lolos sebagai Aman. Keempat halaman Waspada adalah halaman yang sama yang juga dilewatkan model pada pengujian luring (probabilitas 0,29–0,41), sehingga lapisan aturan menangkap kasus yang luput dari model. Pada TC-02, {c2['aman']} dari {c2['halaman']} halaman normal berlabel Aman dan satu berlabel Waspada, yaitu artikel blog fakultas yang membahas hukum judi dan pinjaman online; tidak ada halaman normal yang salah dilabeli judi. Jika hanya label *Terindikasi* dihitung sebagai deteksi, *recall* *extension* adalah {pct(kon['judi_saja_sebagai_positif']['recall'], 0)}, dan jika *Waspada* ikut dihitung, {pct(kon['judi_atau_waspada_sebagai_positif']['recall'], 0)} dengan satu peringatan palsu."))
a(("p", f"Pada TC-03, lima teknik penyembunyian teks (*display:none*, *visibility:hidden*, *opacity:0*, *font-size:0*, dan posisi di luar layar) pada halaman uji seluruhnya terdeteksi dan dilaporkan di *popup*, sedangkan menu seluler tersembunyi tanpa kata kunci tidak menimbulkan peringatan. Pada TC-04, ketika server dimatikan, *popup* menampilkan pesan \"Tidak bisa terhubung ke server lokal\" beserta tombol coba lagi, lencana ikon berubah menjadi tanda silang, dan *extension* maupun halaman tidak mengalami *crash*. Pada TC-05, persentase peluang judi (contoh {c5['nilai']}) tampil bersama label pada seluruh 10 *popup* yang diperiksa. Pada TC-07, *extension* berjalan pada Edge {EDGE} dengan Manifest V3 tanpa galat pada *service worker*, *popup*, maupun halaman pengaturan."))
a(("table", "ext", "Hasil Pengujian Browser Extension",
   ["Kode", "Skenario", "Hasil Pengamatan", "Status"],
   [["TC-01", "Deteksi halaman judi aktif", f"{c1['terdeteksi_judi']}/{c1['halaman']} Terindikasi; {c1['waspada']} Waspada; 0 lolos", "Berhasil dengan catatan"],
    ["TC-02", "Deteksi halaman akademik normal", f"{c2['aman']}/{c2['halaman']} Aman; {c2['waspada']} Waspada; 0 salah judi", "Berhasil dengan catatan"],
    ["TC-03", "Deteksi elemen tersembunyi", f"{c3['terdeteksi']}/{c3['blok_tersembunyi_berkata_kunci']} teknik terdeteksi; 0 alarm palsu", "Berhasil"],
    ["TC-04", "Error koneksi ke Flask API", "Pesan informatif; tanpa crash", "Berhasil"],
    ["TC-05", "Tampilan confidence score", f"Persentase tampil bersama label ({c5['nilai']})", "Berhasil"],
    ["TC-06", "Waktu respons end-to-end", f"Rata-rata {n(c6['e2e_ms']['rata_rata'])} ms (target < 2.000)", "Berhasil"],
    ["TC-07", "Kompatibilitas Manifest V3", f"Edge {EDGE}: {c7['jumlah_galat_total']} galat", "Berhasil"]],
   [800, 1600, 2336, 1100], ["l", "l", "l", "l"]))
a(("p", f"Waktu respons dari permintaan hingga hasil tersimpan (TC-06) ditunjukkan pada {{T:waktu}}. Rata-rata {n(c6['e2e_ms']['rata_rata'])} ms pada Edge dan {n(cc6['e2e_ms']['rata_rata'])} ms pada Chromium, dan seluruh halaman selesai di bawah 2.000 ms bahkan bila dihitung sejak halaman selesai dimuat (maksimum {n(c6['load_ke_hasil_ms']['maks'])} ms, sudah termasuk jeda 400 ms sebelum pemindaian). *Popup* tampil dalam sekitar {n(c6['popup_tampil_ms']['rata_rata'])} ms. Pengukuran ini dilakukan ketika cache *stemming* server sudah terisi sehingga mewakili kondisi hangat; kondisi terburuk telah diukur pada TC-05 model."))
a(("table", "waktu", "Waktu Respons Extension pada 50 Halaman Nyata (ms)",
   ["Tahap", "Rata-rata", "Median", "P95", "Maks"],
   [["Ekstraksi di halaman", n(c6["ekstraksi_ms"]["rata_rata"]), n(c6["ekstraksi_ms"]["median"]), n(c6["ekstraksi_ms"]["p95"]), n(c6["ekstraksi_ms"]["maks"])],
    ["Server (praproses + prediksi)", n(c6["server_ms"]["rata_rata"]), n(c6["server_ms"]["median"]), n(c6["server_ms"]["p95"]), n(c6["server_ms"]["maks"])],
    ["End-to-end (Edge)", n(c6["e2e_ms"]["rata_rata"]), n(c6["e2e_ms"]["median"]), n(c6["e2e_ms"]["p95"]), n(c6["e2e_ms"]["maks"])],
    ["Sejak halaman dimuat (Edge)", n(c6["load_ke_hasil_ms"]["rata_rata"]), n(c6["load_ke_hasil_ms"]["median"]), n(c6["load_ke_hasil_ms"]["p95"]), n(c6["load_ke_hasil_ms"]["maks"])]],
   [2236, 1000, 950, 800, 850], ["l", "c", "c", "c", "c"]))
a(("p", f"Dua pengujian tambahan dilakukan di luar Tabel 3.16. Pertama, sebuah halaman normal yang menyisipkan blok teks judi 2,5 detik setelah dimuat berubah dari Aman menjadi Terindikasi judi melalui pemindaian ulang otomatis dalam sekitar {str(dyn['waktu_deteksi_s']).replace('.', ',')} detik; jeda ini berasal dari peredam 3 detik dan jarak minimum 8 detik antarpemindaian yang sengaja dipasang agar halaman dinamis tidak membebani *browser*. Kedua, uji ketahanan terhadap masukan tidak sempurna (HTML rusak, halaman kosong, respons bukan HTML, halaman dengan 14.000 tautan, dan DOM bersarang 1.500 tingkat) seluruhnya diproses tanpa galat dan *service worker* tetap hidup. Terakhir, untuk 50 halaman nyata yang sama, label model yang dihitung *extension* di *browser* sama dengan prediksi luring pada {VS['label_ml_sama_dengan_offline']} dari {VS['n']} halaman dengan selisih peluang rata-rata {f(VS['selisih_p_rata2'],4)}, sehingga perbedaan cara menghitung fitur antara pelatihan dan inferensi praktis dapat diabaikan."))

a(("h3", "Rekapitulasi Pengujian Extension"))
a(("p", "Hasil pengujian *browser extension* terhadap kriteria Tabel 3.16 telah dirangkum pada {T:ext}. Dua skenario berstatus berhasil dengan catatan karena kriteria \"notifikasi *Terindikasi Konten Judi*\" dan \"notifikasi *Aman*\" terpenuhi pada 21 dari 25 halaman judi dan 24 dari 25 halaman normal, sedangkan sisanya tetap diberi peringatan Waspada."))
a(("img", "edge", "Extension Termuat dan Aktif pada Halaman edge://extensions Microsoft Edge", "edge_extensions_crop.png", 10.0))

# ------------------------------------------------------------------------------------------ 4.3
a(("h2", "Pembahasan"))
a(("h3", "Pembangunan Model Klasifikasi"))
a(("p", f"Rumusan masalah pertama menanyakan bagaimana model klasifikasi konten judi online pada halaman .ac.id dibangun dengan kombinasi fitur teks N-Gram TF-IDF, fitur tautan, dan fitur struktur HTML. Subbab 4.1 menunjukkan bahwa model berhasil dibangun melalui rangkaian tahapan yang runtut: 1.038 halaman dari 330 domain dikumpulkan dari berbagai sumber penemuan, dilabeli, dibersihkan, dan direpresentasikan sebagai 3.008 fitur, dibagi per klaster dan domain menjadi data latih, data uji, dan data *holdout*, lalu dilatih dengan Random Forest yang disetel melalui GridSearchCV. Model mencapai F1-score {f(rf['test']['f1'],2)} pada data uji dan {f(rf['holdout']['f1'],2)} pada data *holdout* dengan ROC-AUC {f(rf['test']['roc_auc'],3)} dan {f(rf['holdout']['roc_auc'],3)}, sehingga tujuan pertama penelitian tercapai."))
a(("p", f"Pembagian per klaster membuat kedua himpunan evaluasi berisi domain yang tidak pernah muncul pada pelatihan, sehingga hasilnya mencerminkan kemampuan pada domain baru dan bukan sekadar pada halaman lain dari domain yang sama. *Recall* kelas judi sebesar {f(rf['test']['recall'],3)} pada data uji dan {f(rf['holdout']['recall'],3)} pada data *holdout* sejalan dengan prioritas penelitian untuk meminimalkan halaman judi yang lolos, dengan *precision* {f(rf['test']['precision'],3)} dan {f(rf['holdout']['precision'],3)}. Penelitian Perdana dkk. (2024) melaporkan kombinasi TF-IDF dan Random Forest dengan *precision* 0,966 dan *recall* 0,958 pada data media sosial; hasil penelitian ini berada pada rentang yang sebanding, meskipun objek dan ukuran datanya berbeda sehingga perbandingan angka hanya bersifat indikatif. Fitur tautan dan struktur memberi kontribusi tambahan, tetapi fitur teks tetap dominan ({{T:fitur_penting}})."))
a(("h3", "Perbandingan Random Forest dan LightGBM"))
a(("p", f"Rumusan masalah kedua menanyakan perbandingan kinerja Random Forest dan LightGBM berdasarkan *precision*, *recall*, dan F1-score. Berdasarkan {{T:metrik}}, pada data uji LightGBM memperoleh F1-score {f(lg['test']['f1'])} dan Random Forest {f(rf['test']['f1'])}, sedangkan pada data *holdout* LightGBM {f(lg['holdout']['f1'])} dan Random Forest {f(rf['holdout']['f1'])}. LightGBM lebih tinggi pada kedua himpunan, tetapi uji McNemar pada {{T:mcnemar}} menunjukkan selisih tersebut tidak bermakna (p = {f(mc['test']['p_value'])} pada data uji dan {f(mc['holdout']['p_value'],4)} pada data *holdout*), dan seluruh *false negative* Random Forest adalah halaman dengan bukti kata kunci yang lemah. Pada halaman non-Google Dork, LightGBM juga tidak menurun sedangkan Random Forest cenderung menurun, meskipun tidak signifikan. Temuan ini sejalan dengan Widiyanto dkk. (2025) yang menemukan LightGBM stabil pada data terbatas. Dengan demikian tidak ada dasar angka untuk menyatakan Random Forest lebih unggul; pemilihan Random Forest sebagai model utama bertumpu pada rancangan penelitian, kesederhanaan, dan kemudahan interpretasi melalui *feature importance*, sedangkan *extension* menyediakan pilihan LightGBM pada halaman pengaturan."))
a(("h3", "Implementasi Browser Extension"))
a(("p", "Rumusan masalah ketiga menanyakan bagaimana model diimplementasikan ke dalam *browser extension* Microsoft Edge untuk mendeteksi konten judi secara *real-time*. Subbab 4.1.10 dan 4.2 menunjukkan bahwa *extension* Manifest V3 yang berkomunikasi dengan Flask API lokal berhasil dibangun dan lulus seluruh tujuh skenario pengujian, dengan waktu respons rata-rata di bawah dua detik. Dua keputusan rancangan terbukti penting. Pertama, fitur pada sisi inferensi harus dihitung sama dengan sisi pelatihan; hasilnya, label model di *browser* sama dengan prediksi luring pada seluruh halaman uji. Kedua, teks yang dikirim harus mencakup elemen tersembunyi, karena konten judi yang disisipkan justru sering disembunyikan dari pengunjung; pada halaman uji, teks yang disembunyikan tidak tampak oleh pengunjung tetapi terdeteksi dan dilaporkan oleh *extension*. Tingkat Waspada menambah kemampuan menangkap halaman yang luput dari model, dengan harga satu peringatan pada artikel yang membahas judi. Keterbatasan arsitektur adalah ketergantungan pada server Flask lokal: *extension* tidak dapat mendeteksi bila server tidak berjalan, dan setiap komputer harus menjalankan servernya sendiri, yang dipermudah oleh skrip peluncuran pada repositori."))
a(("h3", "Keterbatasan Penelitian"))
a(("p", "Beberapa keterbatasan perlu diperhatikan dalam membaca hasil penelitian ini. Pertama, label berasal dari kecocokan kata kunci (Layer 1) dan fitur TF-IDF memuat kata yang sama, sehingga metrik yang tinggi tidak membuktikan kemampuan mendeteksi judi tanpa kata kunci; halaman judi tanpa kata kunci (241 halaman) dikeluarkan dari data sehingga performa pada kasus tersebut tidak teruji. Layer 2 dengan TrustPositif tidak dapat dipakai sebagai verifikasi karena daftar publiknya parsial dan disamarkan, dan verifikasi manual belum dilakukan. Kedua, data uji dan *holdout* kecil dan berkelompok (65 dan 30 kelompok), sehingga satu domain dapat mengubah metrik secara besar dan seluruh nilai p serta rentang kepercayaan bersifat indikatif. Ketiga, validasi silang tidak mengelompokkan data per domain sehingga skor validasi (0,9898) cenderung optimistis. Keempat, *holdout* seluruhnya berisi halaman judi dari klaster non-Google tanpa pembanding reguler. Kelima, kelas normal dipilih secara terarah dan berbeda cara pengumpulannya dengan kelas judi, sehingga perbedaan distribusi halaman (misalnya panjang teks yang berbeda) dapat menjadi isyarat bagi model. Keenam, pengujian *extension* memakai halaman dari dataset dan halaman sintetis pada satu komputer; belum ada pengujian pada situs .ac.id yang sedang terinfeksi di internet maupun pengujian kegunaan oleh pengguna."))
a(("h3", "Penyimpangan dari Rancangan"))
a(("p", "Selama pelaksanaan terdapat penyimpangan dari rancangan Bab III yang perlu dicatat. Sumber penemuan domain diperluas dari Google Dork saja menjadi urlscan.io, Common Crawl, Wayback Machine, dan enumerasi subdomain karena Google Dork menghasilkan domain yang terlalu sedikit. Layer 2 diimplementasikan sebagai pencocokan domain terhadap TrustPositif, bukan verifikasi tautan keluar. Kelas normal dikumpulkan secara terarah dalam tiga kategori. Pembagian data dilakukan per klaster infeksi dan domain. Halaman judi tanpa kata kunci dikeluarkan dari pelatihan. SMOTE tidak diterapkan karena kelas telah seimbang. Ruang pencarian LightGBM ditetapkan oleh penulis. Terakhir, *extension* disempurnakan melampaui wireframe pada Gambar 3.9."))

# ===================================================================================================== BAB 5
B5 = []
b = B5.append
b(("p", "Bab ini memuat simpulan yang menjawab rumusan masalah pada Bab I berdasarkan hasil implementasi dan pengujian pada Bab IV, serta saran bagi pengembangan penelitian selanjutnya."))
b(("h2", "Simpulan"))
b(("p", "Berdasarkan hasil penelitian yang telah dilakukan, dapat ditarik simpulan sebagai berikut:"))
b(("np", "1)", f"Model klasifikasi konten judi online pada halaman website berdomain .ac.id berhasil dibangun dengan Random Forest menggunakan kombinasi 3.000 fitur TF-IDF N-Gram (unigram dan bigram) dan delapan fitur struktural, dilatih pada 712 halaman dari dataset 1.038 halaman (516 judi dan 522 normal) dari 330 domain yang dibagi per klaster infeksi dan domain. Model memperoleh F1-score kelas judi sebesar {f(rf['test']['f1'])} pada data uji dan {f(rf['holdout']['f1'])} pada data *holdout*, dengan *recall* {f(rf['test']['recall'])} dan {f(rf['holdout']['recall'])}."))
b(("np", "2)", f"Dibandingkan dengan LightGBM, Random Forest tidak lebih unggul: F1-score kelas judi pada data uji {f(rf['test']['f1'])} (Random Forest) berbanding {f(lg['test']['f1'])} (LightGBM), dan pada data *holdout* {f(rf['holdout']['f1'])} berbanding {f(lg['holdout']['f1'])}. Uji McNemar menunjukkan selisih tidak bermakna pada kedua himpunan (p = {f(mc['test']['p_value'])} dan {f(mc['holdout']['p_value'],4)})."))
b(("np", "3)", f"Model berhasil diimplementasikan ke dalam *browser extension* Microsoft Edge berbasis Manifest V3 yang berkomunikasi dengan Flask API lokal untuk mendeteksi konten judi online pada halaman .ac.id. Seluruh tujuh skenario pengujian *extension* terpenuhi, dengan waktu respons rata-rata {n(c6['e2e_ms']['rata_rata'])} ms, deteksi seluruh lima teknik penyembunyian teks, dan {c1['terdeteksi_judi']} dari {c1['halaman']} halaman judi nyata berlabel Terindikasi (seluruhnya mendapat peringatan bila Waspada dihitung)."))
b(("np", "4)", "Hasil di atas perlu dibaca dengan memperhatikan bahwa label berasal dari kecocokan kata kunci, sehingga kemampuan model pada konten judi tanpa kata kunci belum teruji, dan bahwa data evaluasi berukuran kecil sehingga perbedaan antarmodel bersifat indikatif."))
b(("h2", "Saran"))
b(("p", "Berdasarkan keterbatasan yang ditemukan, saran untuk penelitian selanjutnya adalah sebagai berikut:"))
b(("np", "1)", "Melakukan verifikasi manual pada label hasil pelabelan kata kunci dan menyusun *independent validation set* berlabel manual, termasuk halaman judi yang tersamar dan tidak memuat kata kunci leksikon, agar kemampuan generalisasi model dapat diuji sebenarnya."))
b(("np", "2)", "Memperluas dataset, terutama jumlah domain kelas normal yang beragam jenis institusinya dan *hard negative* berupa artikel edukasi tentang judi, agar evaluasi lebih stabil dan dapat dilengkapi interval kepercayaan."))
b(("np", "3)", "Mengurangi ketergantungan fitur pada leksikon yang sama dengan aturan pelabelan, misalnya dengan fitur kontekstual atau representasi teks yang lebih kaya seperti *embedding*."))
b(("np", "4)", "Menggunakan validasi silang yang mengelompokkan data per domain atau klaster (*group k-fold*) pada penyetelan hyperparameter agar skor validasi lebih mencerminkan generalisasi ke domain baru."))
b(("np", "5)", "Mengembangkan *extension* lebih lanjut, misalnya menjalankan inferensi tanpa server lokal, menerbitkannya melalui toko ekstensi, menambah pemindaian seluruh situs lewat *sitemap*, dan menguji kegunaannya pada pengelola situs .ac.id."))
b(("np", "6)", "Memperluas Layer 2 dengan sumber verifikasi lain selain TrustPositif, misalnya pemeriksaan tautan keluar ke domain judi terkonfirmasi, dan memantau perubahan teknik penyamaran konten seiring berkembangnya modus penyisipan."))
