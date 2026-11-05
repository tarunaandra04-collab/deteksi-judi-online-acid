# Perubahan ekstensi v2 dibanding rancangan Bab 3 (bahan revisi laporan)

Dosen pembimbing mengizinkan improvisasi selama tujuan penelitian tetap terjawab. Ringkasan di bawah dapat
dipakai untuk merevisi **Tabel 3.17** (komponen sistem), **Gambar 3.8** (arsitektur), **Gambar 3.9** (wireframe) dan **Tabel 3.16** (pengujian ekstensi).

| Aspek | Rancangan Bab 3 / ekstensi lama | v2 | Alasan |
|---|---|---|---|
| Permission | `activeTab`, `scripting`, `storage` (Tabel 3.17) tetapi manifest lama memakai `tabs` | `storage`, `activeTab`, `scripting` — **sesuai tabel** | Lebih sedikit hak akses; `tabs` tidak diperlukan |
| Pemindaian | Sekali saat `load` | + pindai ulang saat DOM/URL berubah (MutationObserver, maks 6x/halaman, jeda ≥ 8 s) | Injeksi judi sering dimuat lewat JavaScript setelah `load` |
| Teks yang dikirim | `innerText` (hanya teks terlihat) | Semua node teks di `<html>` **termasuk elemen tersembunyi**, tanpa script/style/noscript | Training memakai `get_text()` pada HTML mentah; `innerText` membuang justru teks yang disembunyikan penyerang |
| Fitur struktural | dihitung dari ringkasan di extension | dihitung di backend dari data mentah dengan rumus yang sama dengan `04_fitur_struktural.py` | Menghilangkan selisih train-vs-serve (lihat `tests/test_parity.py`) |
| Leksikon flag meta/URL | 17 kata (`model_loader.py` lama) | 91 kata (sama dengan pelabelan) | Distribusi `meta_judi_flag`/`url_flag` sama dengan training |
| Keluaran | label + skor + 3 badge | label 3 tingkat (aman/waspada/judi), **alasan**, bukti, istilah berpengaruh, waktu | Transparansi; mengurangi kesan "kotak hitam" saat sidang |
| Penandaan elemen | Disebut di Bab 3.10.1 tetapi belum ada | Sorotan kata kunci + tautan mencurigakan di halaman, lencana melayang | Memenuhi rancangan Bab 3 |
| Elemen tersembunyi | hitung `display:none` saja | `display:none`, `visibility:hidden`, `opacity:0`, `font-size:0`, di luar layar, ukuran 0 — **hanya yang memuat kata kunci** dilaporkan | Mengurangi alarm palsu dari menu/dropdown biasa |
| Domain | Hanya `.ac.id` | Otomatis di `.ac.id`; manual (tombol) di domain lain via `activeTab` | Memudahkan demo/uji tanpa melonggarkan cakupan penelitian |
| Pengaturan | tidak ada | Alamat API (hanya localhost), model RF/LightGBM, ambang, daftar kecualian, tampilan | Perbandingan RF vs LightGBM bisa didemokan langsung |
| Riwayat | tidak ada | Riwayat lokal + ekspor CSV (tanpa isi halaman) | Bahan Bab 4 (TC-05/TC-06) |
| Start di lab | manual (`python app.py` + Load unpacked) | `jalankan.ps1` satu perintah | Permintaan dosen: script di GitHub |

## Dampak pada pengujian (Tabel 3.16)

- **TC-03** (elemen tersembunyi): sekarang diuji pada halaman `tests/halaman_uji/judi_tersembunyi.html` dan otomatis di `tests/e2e_browser.py`.
- **TC-04** (galat koneksi): server dimatikan → popup menampilkan pesan informatif; diuji otomatis.
- **TC-06** (waktu respons end-to-end): terekam di riwayat (`ms_e2e`) dan dapat diekspor.

## Hal yang sengaja TIDAK diubah

- Arsitektur client-server (Flask lokal + model scikit-learn) dan Manifest V3.
- Ruang fitur 3.008 kolom (3.000 TF-IDF + 8 struktural) dan urutan kolom.
- Model, vectorizer, dan scaler hasil training final (`backend/models/`).
