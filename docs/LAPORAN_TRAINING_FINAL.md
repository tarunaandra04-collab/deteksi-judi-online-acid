# LAPORAN TRAINING FINAL (data_final) — 2026-11-06

> Label tetap **Layer 1 (keyword matching)**; belum ada verifikasi manual Layer 2. Arsip percobaan awal
> (`model_layer1_preliminary/`, `hasil_evaluasi_layer1_preliminary/`, `data/`, `scripts/`) **tidak diubah**.
> Kode: `scripts_final/` (01–08). Output: `training_final/{data,model,hasil_evaluasi}/`. Angka di bawah dibaca dari file hasil run.

## 1. Pemuatan data (`01_load_data.py`)
Aturan sumber persis instruksi: Label 1 = domain `Label1` di `metode_penemuan.csv` (filter CSV, bukan glob) + 3 domain reklasifikasi
dari `_temuan_hit` (unima, stikesmedikacikarang → `kategori_a`; akperkaltara → `kategori_c`); Label 0 = hanya `dataset_baru_negatif/kategori_{a,b,c}`.

| | domain | halaman |
|---|---|---|
| Label 1 dimuat | 215 (212 `dataset_baru` + 3 reklasifikasi) | 757 (750 + 7) |
| Label 0 dimuat | 115 (a:56, b:45, c:14) | 522 (275 / 233 / 14) |

- Domain resmi yang gagal ditemukan filenya: **0**. 53 folder sisa di `dataset_baru/` (termasuk 6 kosong) tidak disentuh.
- Dilewati (404 server, kriteria sama dengan percobaan awal): 3 halaman — `itri.ac.id/api_*`, `jolimpic.uho.ac.id/js-kqris_*`, `jurnal-wins.uho.ac.id/public-totox_*` (`data/file_rusak_dilewati.csv`).
- Label 1 = 182 cluster (168 cluster berisi 1 domain).
- Selisih dengan `cluster_infeksi.csv`: stikesmedikacikarang.ac.id tercatat 6 halaman tetapi hanya 1 HTML ditemukan; unima.ac.id tercatat 6, ditemukan 5.

## 2. Keputusan label halaman (ditanyakan ke pemilik, dijawab)
Dari 757 halaman Label 1, **516** mengandung ≥1 keyword leksikon dan **241 tidak**. Keputusan pemilik: Label 1 = hanya halaman dengan ≥1 hit;
241 halaman tanpa hit **dikeluarkan dari training** (bukan Label 0), dicatat di `data/label1_halaman_dikeluarkan_tanpa_hit.csv`. Tidak ada domain Label 1 yang kehilangan semua halamannya.

**Dataset akhir: 1.038 halaman** — 516 judi (cluster/domain: 182 cluster, 215 domain) + 522 normal (115 domain).

## 3. Split (`02_split_data.py`) — 70:20:10, seed 42
Unit: `cluster_id` (Label 1), domain (Label 0); dialokasikan terpisah per label (= stratifikasi label di level grup), target 10% holdout / 20% test dari halaman tiap label, greedy pada urutan acak.
Assert: tidak ada grup/domain yang terbelah antar split.

| split | halaman | domain | grup | judi | normal | % judi | halaman judi non-dork |
|---|---|---|---|---|---|---|---|
| train | 712 (68,6%) | 230 | 202 | 348 | 364 | 48,9% | 115 |
| test | 221 (21,3%) | 70 | 65 | 116 | 105 | 52,5% | 50 |
| holdout | 105 (10,1%) | 30 | 30 | 52 | 53 | 49,5% | 52 |

**Holdout non-dork (Bab 3.7):** cluster yang seluruh domainnya `INDEPENDEN_NON_GOOGLE` diprioritaskan masuk holdout; pool-nya besar (95 cluster murni, 4 campuran), sehingga **100% halaman judi holdout (52/52) dan 49,5% seluruh holdout** berasal dari grup non-dork. Konsekuensi: holdout **tidak memuat halaman judi "reguler"** (lihat bagian 7, PERLU REVIEW 2).

## 4. Preprocessing & fitur (`03`, `04`)
Sastrawi sesuai skrip lama; 1.038 halaman, 0 teks kosong; pada seluruh 516 halaman judi keyword masih ada setelah cleaning HTML. Median panjang teks: judi 958,5 kata vs normal 474.
Fitur: TF-IDF ngram (1,2) max_features=3000 (+ 8 fitur struktural urutan `STRUCT_COLS_ORDER` dari `model_loader.py` via `ast`) = 3.008 kolom; MinMaxScaler fit hanya di train. Perbedaan cara hitung vs extension tercatat di docstring `04_fitur_struktural.py`.

## 5. SMOTE
Rasio minoritas **train = 48,88%** (judi 348 / normal 364) ≥ 40% → **SMOTE DILEWATI** (Gambar 3.7). RF dan LightGBM dilatih tanpa oversampling.

## 6. Training
| | grid | CV | best params | CV F1 judi | waktu |
|---|---|---|---|---|---|
| Random Forest | Tabel 3.12 (648 kombinasi) | StratifiedKFold(5, shuffle, seed 42) | n_estimators=200, max_depth=20, min_samples_split=10, min_samples_leaf=1, max_features=sqrt, class_weight=balanced | 0,9898 | 12,2 mnt |
| LightGBM | grid pilihan penulis skrip (108 kombinasi; Bab 3 tidak menetapkan) | sama | n_estimators=300, learning_rate=0,1, num_leaves=15, max_depth=-1, class_weight=balanced | 0,9884 | 4,3 mnt |

## 7. Evaluasi (`07_evaluasi.py`)
| model | split | n | Acc | Prec | Rec | F1 | ROC-AUC | FPR | CM [[TN FP][FN TP]] |
|---|---|---|---|---|---|---|---|---|---|
| RF | test | 221 | 0,982 | 1,000 | 0,966 | 0,983 | 0,9995 | 0,000 | [[105 0][4 112]] |
| RF | holdout | 105 | 0,943 | 0,979 | 0,904 | 0,940 | 0,988 | 0,019 | [[52 1][5 47]] |
| LightGBM | test | 221 | 0,986 | 1,000 | 0,974 | 0,987 | 0,996 | 0,000 | [[105 0][3 113]] |
| LightGBM | holdout | 105 | 0,990 | 1,000 | 0,981 | 0,990 | 1,000 | 0,000 | [[53 0][1 51]] |

**McNemar eksak RF vs LightGBM:** test b=2, c=3, p=1,0 (tidak bermakna); holdout b=0, c=5, p=0,0625 (tidak bermakna, tetapi condong ke LightGBM).

**Kesalahan** (`kesalahan_klasifikasi.csv`): semua kesalahan halaman judi adalah halaman dengan bukti keyword lemah (1–3 hit; median halaman judi = 5 hit). RF holdout: 4 FN dari satu domain (`ununtb.ac.id`) + 1 FN `jurnal.staim-probolinggo.ac.id`, 1 FP `apiksibba.ac.id` (halaman Label 0 yang memuat 1 keyword).

**Independensi (non-dork) — `metrik_ringkas.json`:**
| model | recall judi non-dork (test) | recall judi reguler (test) | Fisher p (test) | recall non-dork pooled (test+holdout) | vs reguler | Fisher p (pooled) |
|---|---|---|---|---|---|---|
| RF | 47/50 = 0,940 [CI95 0,838–0,979] | 65/66 = 0,985 [0,919–0,997] | 0,313 | 94/102 = 0,922 | 0,985 | 0,091 |
| LightGBM | 49/50 = 0,980 | 64/66 = 0,970 | 1,000 | 100/102 = 0,980 | 0,970 | 0,646 |

Recall holdout (100% non-dork): RF 47/52 = 0,904; LightGBM 51/52 = 0,981.
**Kesimpulan:** tidak ada penurunan *signifikan* pada α=0,05 untuk kedua model. LightGBM tidak turun sama sekali; RF menunjukkan kecenderungan turun ±4–6 poin recall pada halaman non-dork (RF: 0,92 vs 0,985 pooled, p=0,09) — tidak bermakna dengan n sekecil ini, tetapi tidak bisa dikesampingkan. Pembanding "reguler" diambil dari **test set** karena holdout tidak punya halaman judi reguler.

Feature importance RF (top-5): `slot gacor` 0,037, `slot` 0,035, `gacor` 0,030, `gacor slot` 0,021, `login` 0,018; fitur struktural teratas `FLNK_02_ext_ratio` (0,017, peringkat 6). Importance tersebar (tidak lagi satu fitur dominan seperti percobaan awal).

## 8. Export & kompatibilitas (`08_uji_model_loader.py`)
`training_final/model/{model,vectorizer,scaler}.pkl` (+ `model_lightgbm.pkl`, `model_info.json`). `model_loader.py` **tidak diubah**; salinannya di `training_final/uji_loader/` memuat model tanpa error, `n_features_in_`=3008 = 3000 TF-IDF + 8 struktural, urutan kolom sama dengan `STRUCT_COLS_ORDER`; 8 halaman uji nyata (4 judi, 4 normal) diprediksi benar, teks sintetis slot→judi (0,772) dan PMB→aman (0,917). Ini uji fungsional, bukan uji kualitas; belum diuji via Flask/`content.js`. Pickle dibuat dengan scikit-learn 1.9.1 / Python 3.14.0 — Flask harus memakai versi yang sama. `model.pkl` = RF terbaik.

## 9. PERLU REVIEW
1. **Circularity label–fitur tetap ada.** Label = ada keyword leksikon; TF-IDF memuat keyword itu, dan `meta_judi_flag`/`url_flag` memakai leksikon sama. Top fitur adalah `slot gacor`/`slot`/`gacor`. Akurasi tinggi tidak membuktikan deteksi judi **tanpa** keyword — halaman tanpa hit sengaja dikeluarkan (241), jadi performa pada konten judi yang tidak memuat leksikon tidak teruji sama sekali.
2. **Holdout 100% judi-nondork**: konsisten dengan instruksi (prioritas non-dork), tetapi menghilangkan pembanding reguler di holdout; pembanding dipindah ke test. Jika perlu pembanding di holdout, kuota non-dork harus dibatasi (mis. ≤50% halaman judi holdout).
3. **CV `StratifiedKFold` (sesuai Bab 3) tidak grup-aware**: halaman satu domain/cluster bisa di fold latih & validasi → CV F1 (0,99) optimistis dan pemilihan hyperparameter bias. Test/holdout aman (dipisah per grup). Usulan: `StratifiedGroupKFold` pada cluster.
4. **Set evaluasi kecil dan berkelompok**: test 65 grup, holdout 30 grup; halaman-halaman satu domain berkorelasi (mis. 4 FN RF holdout dari 1 domain), sehingga CI dan p-value (McNemar, Fisher) bersifat indikatif.
5. **Label Layer 1 berisik.** 12 halaman Label 0 mengandung keyword (10 train, 2 holdout; 12 domain, mis. `apiksibba.ac.id`) dan tetap Label 0 sesuai aturan; salah satunya menjadi FP RF. Sebaliknya, `akperkaltara.ac.id` (Label 1) berisi satu artikel berita penangkapan judi, bukan konten judi — dibiarkan sesuai instruksi.
6. **Panjang teks** (judi median 958 vs normal 474 kata) dapat jadi isyarat tersamar lewat TF-IDF.
7. **Param grid LightGBM** adalah pilihan penulis skrip; hasil LightGBM ≥ RF pada hampir semua metrik (tidak signifikan) — klaim "RF unggul" tidak didukung angka.
8. 241 halaman Label 1 tanpa hit, 3 halaman 404, dan selisih jumlah halaman dengan `cluster_infeksi.csv` dicatat di atas.

## 10. PENYIMPANGAN DARI BAB 3
- CV `StratifiedKFold` (bukan group-aware) — mengikuti Bab 3, lihat PERLU REVIEW 3.
- Param grid LightGBM tidak ditetapkan di Bab 3.
- Urutan normalisasi mengikuti `model_loader.py`/instruksi (lowercase → hapus simbol/angka → stopword → stemming), bukan urutan di Tabel 3.9.
- Pelabelan menggunakan pseudo-URL (URL asli tidak tersimpan); URL hanya mempengaruhi diagnostik jumlah hit dan fitur `url_flag`.
- Split: alokasi greedy per label pada level grup (bukan `GroupShuffleSplit`) agar target 70:20:10 per jumlah halaman terpenuhi; holdout 100% judi non-dork.
- Label 1 dibatasi pada halaman ber-keyword (keputusan pemilik, bagian 2).
