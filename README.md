# Deteksi Konten Judi Online pada Website `.ac.id`

Browser extension (Manifest V3, Microsoft Edge / Chrome) + server Flask lokal yang
mendeteksi konten judi online yang disisipkan ke website berdomain `.ac.id`.
Model: **Random Forest** (utama) dan **LightGBM** (pembanding) dengan fitur
**TF-IDF n-gram (1,2) + 8 fitur struktural** (tautan, iframe, elemen tersembunyi, kedalaman DOM, meta, URL).

> Proyek skripsi — Program Studi Rekayasa Sistem Komputer, Institut Bisnis dan Teknologi Indonesia (2026).
> Ini **prototipe penelitian**: hasilnya adalah indikasi awal, bukan vonis.

## Mulai cepat (Windows, komputer lab)

Prasyarat: Python 3.11+ (diuji 3.14), Microsoft Edge atau Chrome, koneksi internet saat pertama kali.

```powershell
git clone https://github.com/tarunaandra04-collab/deteksi-judi-online-acid.git
cd deteksi-judi-online-acid
powershell -ExecutionPolicy Bypass -File .\jalankan.ps1
```

Skrip itu akan: (1) membuat `.venv` dan memasang dependensi (sekali saja), (2) menyalakan server model,
(3) membuka Edge dengan ekstensi **sudah termuat**. Buka halaman `.ac.id` mana pun lalu lihat lencana di pojok halaman
dan ikon perisai di toolbar. Hentikan server dengan `.\jalankan.ps1 -Stop`.

Jika browser menolak pemuatan otomatis, muat manual: `edge://extensions` → aktifkan **Developer mode** →
**Load unpacked** → pilih folder `extension/`. Detail ada di [docs/PANDUAN_LAB.md](docs/PANDUAN_LAB.md).

## Apa yang dilakukan ekstensi

Dirancang sederhana untuk pengguna awam (saran pembimbing): cukup tahu apakah halaman berisi judi atau tidak.

| Fitur | Keterangan |
|---|---|
| Pindai otomatis `.ac.id` | Saat halaman selesai dimuat; dipindai ulang bila konten berubah (MutationObserver) atau URL berubah (SPA) |
| Lampu lalu lintas | Popup menampilkan **AMAN** (hijau), **HATI-HATI** (kuning: model bilang aman tetapi ada bukti aturan), atau **ADA JUDI** (merah), dengan satu kalimat penjelasan |
| Tiga pemeriksaan | *Tulisan judi terlihat*, *tulisan judi tersembunyi* (display:none, opacity:0, font-size:0, di luar layar), dan *tautan ke situs judi* — masing-masing bertanda centang, seru, atau silang |
| Lihat di halaman | Tombol untuk menandai kata judi dan tautan mencurigakan langsung di halaman |
| Lencana bulat | Muncul di pojok halaman hanya bila ada temuan; diklik membuka ringkasan yang sama |
| Salin laporan | Ringkasan temuan (termasuk peluang model) siap dikirim ke admin website |
| Mode manual di domain mana pun | Tombol "Periksa halaman ini" (izin `activeTab`, hanya tab aktif) — berguna untuk demo di halaman uji |

Tidak ada halaman pengaturan, riwayat, atau persentase di antarmuka. Model bawaan: Random Forest (LightGBM tersedia di server sebagai pembanding).

## Arsitektur

```
Halaman .ac.id ── content.js + scanner.js ──► background.js (service worker) ──HTTP POST──► Flask :5000 /predict
   ▲   (ekstrak teks, tautan, DOM,                    │ badge ikon                             │ engine.py: normalisasi Sastrawi,
   │    deteksi elemen tersembunyi)                   ▼                                        │ 8 fitur struktural, TF-IDF,
   └── lencana + sorotan ◄──────────── popup.html                                         ▼ RF / LightGBM → JSON
```

- Data halaman **hanya dikirim ke `127.0.0.1`** (ekstensi menolak alamat selain localhost).
- Fitur di backend direplikasi **persis** dari skrip training (lihat `tests/test_parity.py`).
- `backend/lexicon.json` adalah sumber tunggal leksikon; `scripts/build_assets.py` menyalinnya ke `extension/lexicon.js`.

## Struktur repo

```
extension/   manifest.json, content.js, scanner.js, background.js, ringkas.js, popup.*, icons/
backend/     app.py, engine.py, lexicon.json, requirements.txt, models/ (RF, LightGBM, TF-IDF, scaler)
scripts/     install.ps1, build_assets.py
tests/       test_parity.py (paritas fitur dengan training), test_api.py (uji endpoint)
docs/        PANDUAN_LAB.md, KONTRAK_API.md, LAPORAN_TRAINING_FINAL.md, hasil_evaluasi/
jalankan.ps1 satu perintah untuk demo
```

## Hasil model (data final, 1.034 halaman setelah empat berkas gambar dikeluarkan, split per domain/klaster 70:20:10)

| Model | Split | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|---|
| Random Forest | test (219) | 0,982 | 1,000 | 0,965 | 0,982 | 0,9957 |
| Random Forest | holdout (105) | 1,000 | 1,000 | 1,000 | 1,000 | 1,0000 |
| LightGBM | test (219) | 0,986 | 1,000 | 0,974 | 0,987 | 0,9965 |
| LightGBM | holdout (105) | 0,990 | 1,000 | 0,981 | 0,990 | 1,0000 |

Uji McNemar RF vs LightGBM tidak bermakna (test p=1,000; holdout p=1,000). Sumber lengkap: [docs/LAPORAN_TRAINING_FINAL.md](docs/LAPORAN_TRAINING_FINAL.md).

## Keterbatasan (jujur)

1. **Label berasal dari kata kunci (Layer 1)** dan fitur TF-IDF memuat kata yang sama — metrik tinggi tidak membuktikan deteksi
   judi **tanpa** kata kunci. Halaman judi tanpa kata kunci sengaja dikeluarkan dari training (241 halaman).
2. Set uji kecil dan berkelompok (65 grup test, 30 grup holdout); p-value/CI bersifat indikatif.
3. Status **Waspada** dan penyorotan memakai aturan kata kunci utuh sebagai pelengkap, bukan pengganti model.
4. Model dilatih dengan **scikit-learn 1.9.1 / Python 3.14**; `requirements.txt` mengunci versi itu.
5. Elemen yang disembunyikan lewat CSS eksternal terdeteksi dari gaya terhitung (computed style); teknik penyamaran lain mungkin lolos.

## Lisensi & etika

Dipakai untuk riset dan pembelajaran. Data halaman diproses lokal dan tidak disimpan; ekstensi hanya menyimpan hasil pemeriksaan sementara pada tab yang terbuka.
