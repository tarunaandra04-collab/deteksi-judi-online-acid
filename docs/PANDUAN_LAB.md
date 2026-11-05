# Panduan demo di komputer lab

## A. Cara tercepat (satu perintah)

1. Pastikan Python 3.11+ terpasang (`python --version`). Jika belum: https://www.python.org/downloads/ (centang *Add python.exe to PATH*).
2. Ambil repo: `git clone https://github.com/tarunaandra04-collab/deteksi-judi-online-acid.git` (atau unduh ZIP dari GitHub lalu ekstrak).
3. Buka PowerShell di folder repo, jalankan:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\jalankan.ps1
   ```

   Pertama kali butuh ±3–6 menit (pasang dependensi). Setelahnya hanya beberapa detik.
4. Edge terbuka dengan ekstensi termuat. Buka situs `.ac.id` → lencana muncul di pojok kanan bawah bila ada temuan; ikon perisai di toolbar menunjukkan status.
5. Selesai demo: `.\jalankan.ps1 -Stop`.

## B. Jika ekstensi tidak termuat otomatis

Versi baru Edge/Chrome dapat membatasi `--load-extension`. Muat manual (1 menit):

1. Pastikan server hidup: `.\jalankan.ps1 -NoBrowser` (atau buka http://127.0.0.1:5000/health → `"model_loaded": true`).
2. Buka `edge://extensions`, aktifkan **Developer mode** (kiri bawah).
3. Klik **Load unpacked** → pilih folder `extension` di repo.
4. (Opsional) pin ikon perisai ke toolbar.

## C. Skenario uji (cocok dengan Tabel 3.16 proposal)

| Kode | Langkah | Hasil yang diharapkan |
|---|---|---|
| TC-01 | Buka halaman `.ac.id` yang terinfeksi judi | Lencana merah "Terindikasi konten judi", kata kunci tersorot |
| TC-02 | Buka beranda universitas normal (mis. ui.ac.id) | Tidak ada lencana (atau "Aman" jika mode *Selalu tampilkan*), badge ikon `OK` |
| TC-03 | Halaman dengan teks `display:none` berisi kata kunci | Panel menampilkan "Elemen tersembunyi" beserta alasan |
| TC-04 | Matikan server (`-Stop`), muat ulang halaman | Popup: "Tidak bisa menganalisis… jalankan jalankan.ps1", ekstensi tidak crash |
| TC-05 | Buka popup | Persentase peluang judi tampil bersama label dan penanda ambang |
| TC-06 | Pengaturan → Riwayat | Kolom *E2E (ms)* terisi; rata-rata < 2000 ms |
| TC-07 | `edge://extensions` | Ekstensi aktif tanpa galat (Manifest V3) |

Halaman uji lokal tanpa internet ada di `tests/halaman_uji/` (jalankan `python -m http.server 8080` di folder itu,
lalu pindai manual lewat tombol *Pindai halaman ini* — mode manual bekerja di domain mana pun).

## D. Masalah umum

| Gejala | Penyebab / solusi |
|---|---|
| Popup: "Tidak bisa terhubung ke server lokal" | Server belum jalan → `.\jalankan.ps1 -NoBrowser`; cek `backend.log.err` |
| `/health` menunjukkan `model_loaded: false` | Versi scikit-learn tidak sama dengan saat training → `.\scripts\install.ps1 -Force` |
| `jalankan.ps1 cannot be loaded… ExecutionPolicy` | Jalankan dengan `powershell -ExecutionPolicy Bypass -File .\jalankan.ps1` |
| Port 5000 dipakai aplikasi lain | `.\jalankan.ps1 -Port 5050`, lalu ubah *Alamat API* di Pengaturan ekstensi |
| Lencana tidak muncul di halaman aman | Memang bawaannya hanya muncul bila ada temuan; ubah di Pengaturan → *Selalu tampilkan* |
