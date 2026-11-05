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

| Fitur | Keterangan |
|---|---|
| Pindai otomatis `.ac.id` | Saat halaman selesai dimuat; dipindai ulang bila konten berubah (MutationObserver) atau URL berubah (SPA) |
| Label tiga tingkat | **Aman**, **Waspada** (model bilang aman tetapi ada bukti aturan), **Terindikasi judi** |
| Bukti, bukan sekadar skor | Kata kunci utuh + jumlah, elemen **tersembunyi** yang memuat kata kunci (display:none, opacity:0, font-size:0, di luar layar), tautan keluar bernama judi |
| Sorotan di halaman | Kata kunci diberi tanda merah/kuning, tautan mencurigakan diberi garis putus-putus; lencana melayang dengan panel penjelasan |
| Penjelasan model | Istilah TF-IDF yang paling memengaruhi hasil + alasan dalam bahasa Indonesia |
| Mode manual di domain mana pun | Tombol "Pindai halaman ini" (izin `activeTab`, hanya tab aktif) — berguna untuk demo di halaman uji |
| Pengaturan | Pilih model RF/LightGBM, ambang keputusan, domain dikecualikan, tampilan lencana |
| Riwayat + ekspor CSV | Tanpa menyimpan isi halaman; kolom waktu end-to-end mendukung pengujian TC-05/TC-06 |
| Salin laporan | Ringkasan temuan siap dikirim ke admin website |

## Arsitektur

```
Halaman .ac.id ── content.js + scanner.js ──► background.js (service worker) ──HTTP POST──► Flask :5000 /predict
   ▲   (ekstrak teks, tautan, DOM,                    │ badge ikon, riwayat                    │ engine.py: normalisasi Sastrawi,
   │    deteksi elemen tersembunyi)                   ▼                                        │ 8 fitur struktural, TF-IDF,
   └── lencana + sorotan ◄──────────── popup.html / options.html                              ▼ RF / LightGBM → JSON
```

- Data halaman **hanya dikirim ke `127.0.0.1`** (ekstensi menolak alamat selain localhost).
- Fitur di backend direplikasi **persis** dari skrip training (lihat `tests/test_parity.py`).
- `backend/lexicon.json` adalah sumber tunggal leksikon; `scripts/build_assets.py` menyalinnya ke `extension/lexicon.js`.

## Struktur repo

```
extension/   manifest.json, content.js, scanner.js, background.js, popup.*, options.*, icons/
backend/     app.py, engine.py, lexicon.json, requirements.txt, models/ (RF, LightGBM, TF-IDF, scaler)
scripts/     install.ps1, build_assets.py
tests/       test_parity.py (paritas fitur dengan training), test_api.py (uji endpoint)
docs/        PANDUAN_LAB.md, KONTRAK_API.md, LAPORAN_TRAINING_FINAL.md, hasil_evaluasi/
jalankan.ps1 satu perintah untuk demo
```

## Hasil model (data final, 1.038 halaman, split per domain/klaster 70:20:10)

| Model | Split | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|---|
| Random Forest | test (221) | 0,982 | 1,000 | 0,966 | 0,983 | 0,9995 |
| Random Forest | holdout (105) | 0,943 | 0,979 | 0,904 | 0,940 | 0,988 |
| LightGBM | test (221) | 0,986 | 1,000 | 0,974 | 0,987 | 0,996 |
| LightGBM | holdout (105) | 0,990 | 1,000 | 0,981 | 0,990 | 1,000 |

Uji McNemar RF vs LightGBM tidak bermakna (test p=1,0; holdout p=0,0625). Sumber lengkap: [docs/LAPORAN_TRAINING_FINAL.md](docs/LAPORAN_TRAINING_FINAL.md).

## Keterbatasan (jujur)

1. **Label berasal dari kata kunci (Layer 1)** dan fitur TF-IDF memuat kata yang sama — metrik tinggi tidak membuktikan deteksi
   judi **tanpa** kata kunci. Halaman judi tanpa kata kunci sengaja dikeluarkan dari training (241 halaman).
2. Set uji kecil dan berkelompok (65 grup test, 30 grup holdout); p-value/CI bersifat indikatif.
3. Status **Waspada** dan penyorotan memakai aturan kata kunci utuh sebagai pelengkap, bukan pengganti model.
4. Model dilatih dengan **scikit-learn 1.9.1 / Python 3.14**; `requirements.txt` mengunci versi itu.
5. Elemen yang disembunyikan lewat CSS eksternal terdeteksi dari gaya terhitung (computed style); teknik penyamaran lain mungkin lolos.

## Lisensi & etika

Dipakai untuk riset dan pembelajaran. Data halaman diproses lokal; riwayat disimpan hanya di browser pengguna dan dapat dihapus
dari halaman Pengaturan.
