# Requirements — 04 Eksekusi, orkestrasi, dan harness

Status: Approved (2026-09-29)
Use case: UC-07 (kirim order), UC-08 ([overview](../fase-1-overview.md))
Asal: ea-foundation R6, R4.4 (komentar), R19.3–19.4, design `CSdbApp` dan harness
Butuh: spec 02 (akun, state, event sink), spec 03 (`CLogger`, sesi, `SchemaEnums.mqh`)

## Pendahuluan

Spec ini membangun satu-satunya pintu ke broker (`CExecutor`), orkestrasi event yang dipakai bersama EA dan harness (`CSdbApp`), `SDBot.mq5` v1.03 yang hanya meneruskan event ke orkestrasi itu, dan harness uji yang membuka posisi terjadwal di Strategy Tester. Setelah spec ini, spec risk dan position bisa diuji dengan posisi sungguhan.

Tidak termasuk: perhitungan lot dan pre-trade check (spec 05), pencatatan deal, event posisi, dan closure (spec 06), pencatatan sinyal (Fase 3). Di spec ini harness memakai lot tetap dari input.

Selesai jika suite `Execution` dan `App` ALL PASS, skenario SC-00, SC-06, dan SC-08 PASS lewat runner, EA v1.03 terpasang di terminal live tanpa membuka posisi apa pun (MC-EX-01), dan harness menolak dipasang di chart live (MC-EX-02).

## Glosarium

- **Retcode ambigu**: hasil kirim yang tidak memastikan order tereksekusi atau tidak (timeout, koneksi putus, tanpa jawaban). Order mungkin sudah terisi.
- **ID permintaan**: kode 4 karakter unik per permintaan order, ditulis di komentar order untuk mendeteksi eksekusi ganda.
- **Alasan tolak**: kode dari enum `reject_stage` di `shared/schema/enums.md`.
- **Skenario**: konfigurasi harness + tester dengan assert otomatis, diberi ID `SC-nn`.

## Requirements

### Requirement 1: Validasi sebelum kirim

**User story:** Sebagai trader, saya ingin order yang tidak aman ditolak sebelum sampai ke broker, agar tidak pernah ada posisi tanpa SL atau dengan SL yang tidak masuk akal.

#### Acceptance criteria

1.1. JIKA permintaan tidak membawa SL atau TP MAKA Executor WAJIB menolaknya dengan alasan `INVALID_STOPS`, tanpa memanggil broker.
1.2. JIKA SL atau TP berada di sisi yang salah (buy dengan SL ≥ ask atau TP ≤ ask, sell dengan SL ≤ bid atau TP ≥ bid) MAKA Executor WAJIB menolaknya dengan alasan `INVALID_STOPS`.
1.3. Executor WAJIB menormalkan SL dan TP ke digit simbol, dan memakai harga ask (buy) atau bid (sell) terbaru untuk semua pemeriksaan jarak.
1.4. JIKA jarak SL atau TP dari harga lebih kecil dari stops level + spread, atau lebih kecil dari freeze level, MAKA Executor WAJIB menolak dengan alasan `SL_TOO_CLOSE`.
1.5. JIKA volume di luar `SYMBOL_VOLUME_MIN`–`SYMBOL_VOLUME_MAX`, bukan kelipatan `SYMBOL_VOLUME_STEP`, atau bersama posisi simbol yang ada melewati `SYMBOL_VOLUME_LIMIT`, MAKA Executor WAJIB menolak dengan alasan `INVALID_VOLUME`.
1.6. Executor WAJIB memanggil `OrderCheck` sebelum setiap pengiriman. JIKA margin tidak cukup MAKA order WAJIB ditolak dengan alasan `MARGIN_LOW`; JIKA `OrderCheck` menolak karena hal lain MAKA alasannya `BROKER_REJECTED` dengan retcode `OrderCheck`.
1.7. SELAMA `CAccount::CanTrade` bernilai false Executor WAJIB menolak setiap order dengan alasan `NOT_TRADABLE`, tanpa memanggil broker.

### Requirement 2: Pengiriman dan retry

**User story:** Sebagai trader, saya ingin error sementara broker ditangani otomatis tanpa pernah membuka posisi ganda.

#### Acceptance criteria

2.1. Executor WAJIB mengirim market order secara sinkron dengan magic instance, SL, TP, deviasi maksimum 10 point, filling mode yang didukung simbol, dan komentar berisi SL awal dan ID permintaan.
2.2. KETIKA broker mengembalikan retcode sementara (requote, harga berubah, tanpa harga) MAKA Executor WAJIB mengulang maksimal 3 kali dengan jeda 500 ms, dan memvalidasi ulang SL/TP (Req 1.2–1.4) terhadap harga baru sebelum setiap ulangan.
2.3. KETIKA broker mengembalikan retcode ambigu MAKA Executor WAJIB mencari posisi terbuka atau deal dalam 5 menit terakhir dengan ID permintaan yang sama sebelum mengulang. JIKA ditemukan MAKA order WAJIB dianggap berhasil dan tidak dikirim ulang.
2.4. JIKA retcode permanen (pasar tutup, volume tidak valid, dana tidak cukup, trading dimatikan, ditolak) atau ulangan habis MAKA Executor WAJIB berhenti, mencatat log ERROR dengan retcode dan deskripsinya, dan mengirim alert Medium `ORDER_FAILED` satu kali per permintaan.
2.5. Semua ulangan satu permintaan WAJIB memakai ID permintaan yang sama.

### Requirement 3: Pencatatan hasil

**User story:** Sebagai trader, saya ingin harga isi, slippage, dan risiko aktual setiap order tercatat, agar kualitas eksekusi broker bisa dinilai.

#### Acceptance criteria

3.1. KETIKA order terisi MAKA Executor WAJIB mengirim satu `TradeRecord` ke event sink dengan sumber `EA`: position ID, magic, simbol, arah, volume terisi, harga diminta, harga isi, slippage entry (point, negatif jika merugikan), spread saat entry (point), SL awal, TP awal, risiko uang dari harga isi, volume terisi, dan SL awal, risiko dalam % balance, signal ID (kosong sebelum Fase 3), versi EA, dan waktu isi.
3.2. JIKA volume terisi lebih kecil dari yang diminta (partial fill) MAKA Executor WAJIB mencatat volume terisi dan risiko dari volume itu, serta log WARN.
3.3. JIKA harga isi tidak tersedia di hasil kirim MAKA Executor WAJIB membacanya dari deal di history. JIKA tetap tidak tersedia MAKA harga isi dicatat sama dengan harga diminta, slippage dicatat kosong, dan log WARN.
3.4. Executor WAJIB mengembalikan hasil ke pemanggil (berhasil/tolak, alasan tolak, retcode, position ID, harga isi, volume terisi) sehingga pemanggil tidak perlu membaca state broker sendiri.

### Requirement 4: Satu pintu ke broker

**User story:** Sebagai developer, saya ingin semua perubahan posisi lewat satu kelas yang menegakkan aturan keamanan, agar modul lain tidak bisa melanggarnya.

#### Acceptance criteria

4.1. `CExecutor` WAJIB menjadi satu-satunya pemilik `CTrade` dan satu-satunya pemanggil fungsi trading di EA.
4.2. Ubah SL WAJIB menolak SL yang tidak lebih baik dari SL sekarang (untuk buy: lebih rendah atau sama; untuk sell: lebih tinggi atau sama), SL yang melanggar stops/freeze level, dan SL di sisi harga yang salah.
4.3. JIKA broker mengembalikan "tidak ada perubahan" untuk modifikasi MAKA Executor WAJIB menganggapnya berhasil.
4.4. JIKA posisi sudah tidak ada saat modify atau close MAKA Executor WAJIB mengembalikan status "posisi tidak ada" tanpa retry dan tanpa alert.
4.5. Tutup sebagian WAJIB menolak volume ≤ 0, volume ≥ volume posisi, volume yang bukan kelipatan step, dan volume yang membuat sisa < lot minimum.
4.6. KETIKA modify atau close mendapat retcode sementara atau ambigu MAKA Executor WAJIB mengulang maksimal 3 kali dengan jeda 500 ms, memeriksa ulang posisi sebelum setiap ulangan. JIKA tetap gagal MAKA log ERROR dan alert Medium `MODIFY_FAILED` (modify) atau `ORDER_FAILED` (close).
4.7. Setiap operasi Executor WAJIB hanya menyentuh posisi dengan magic dan simbol instance ini. Operasi emergency lintas pair diputuskan di spec 05 (R2-1).

### Requirement 5: Komentar order dan ID permintaan

**User story:** Sebagai developer, saya ingin komentar order membawa informasi yang dibutuhkan untuk restart aman dan deteksi order ganda, dalam batas panjang MT5.

#### Acceptance criteria

5.1. Komentar WAJIB berformat `SDB|<SL awal>|<ID permintaan>` dengan SL awal sesuai digit simbol dan panjang ≤ 31 karakter.
5.2. Parser WAJIB mengembalikan SL awal dan ID permintaan dari komentar yang valid, dan gagal untuk komentar lain (termasuk komentar yang dipotong atau diubah broker).
5.3. ID permintaan WAJIB berbeda antar-instance pada akun yang sama dan tidak berulang setelah restart EA (penghitung disimpan di Global Variable per login dan magic).

### Requirement 6: Orkestrasi event

**User story:** Sebagai developer, saya ingin EA utama dan harness menjalankan urutan init, tick, timer, dan transaksi yang sama persis.

#### Acceptance criteria

6.1. `CSdbApp` WAJIB menjalankan urutan init: validasi input → storage dan sesi → validasi akun (hasil PENDING diperbolehkan) → state bersama (setelah akun lolos) → executor → modul spec berikutnya → timer 1 detik.
6.2. JIKA langkah init yang wajib gagal MAKA `CSdbApp` WAJIB mengembalikan kode init yang sesuai (`INIT_PARAMETERS_INCORRECT` untuk input, `INIT_FAILED` untuk akun/timer) dan tidak meninggalkan timer, handle, atau objek.
6.3. `CSdbApp` WAJIB meneruskan `OnTick`, `OnTimer`, `OnTradeTransaction`, `OnTester`, dan `OnDeinit` ke modul dalam urutan tetap, dengan pemeriksaan akun dan risk monitor sebelum flush storage di setiap timer.
6.4. KETIKA EA di-deinit (termasuk setelah init gagal) MAKA `CSdbApp` WAJIB menghentikan timer, mencatat alasan deinit, mengakhiri sesi, melakukan flush terakhir, melepas handle, dan menghapus semua objek yang dibuat.
6.5. SELAMA akun lolos validasi `CSdbApp` WAJIB mengirim snapshot akun ke event sink setiap 60 detik.
6.6. `SDBot.mq5` WAJIB hanya meneruskan event ke `CSdbApp` dan tidak berisi logika lain.
6.7. EA utama WAJIB tidak berisi kode pembuka posisi uji. Sebelum Fase 3, EA utama tidak membuka posisi sama sekali.

### Requirement 7: Harness uji

**User story:** Sebagai developer, saya ingin harness yang membuka posisi terjadwal dan mengecek hasil skenario otomatis, agar setiap spec berikutnya bisa dibuktikan di Strategy Tester.

#### Acceptance criteria

7.1. JIKA harness tidak berjalan di Strategy Tester MAKA harness WAJIB gagal init dengan log CRITICAL.
7.2. Harness WAJIB memakai `CSdbApp` dan modul yang sama dengan EA utama, ditambah jadwal entry dari input (setiap N bar LTF, arah, jarak SL dan TP dalam point, jumlah posisi maksimum, lot tetap).
7.3. Harness WAJIB memakai magic cadangan harness (2026091900), yang hanya diterima dalam mode harness.
7.4. Entry harness WAJIB lewat Executor. Mulai spec 05, entry juga lewat pre-trade check dan perhitungan lot.
7.5. Harness WAJIB bisa mensimulasikan restart: di bar tertentu, orkestrasi dihapus lalu dibuat dan di-init ulang, dengan Global Variables dan posisi tetap ada, dan sesi baru tercatat.
7.6. Harness WAJIB merekam event yang dikirim ke sink tanpa mengubah penulisan ke DB, dan di akhir tes mengecek harapan skenario yang dipilih lewat input, lalu menulis `SC-nn PASS/FAIL` beserta alasan ke file hasil yang dibaca runner.
7.7. JIKA skenario yang dipilih tidak dikenal harness MAKA hasilnya WAJIB FAIL, bukan PASS.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Timeout saat kirim, padahal order terisi di server | Posisi dengan ID permintaan ditemukan, tidak dikirim ulang | 2.3 |
| EC-02 | Requote 3 kali berturut-turut | Berhenti setelah ulangan ke-3, satu alert Medium | 2.2, 2.4 |
| EC-03 | Harga bergerak saat requote sehingga SL jadi terlalu dekat | Ulangan dibatalkan dengan `SL_TOO_CLOSE` | 2.2 |
| EC-04 | Pasar tutup (akhir pekan) saat order | Tolak tanpa retry, satu alert | 2.4 |
| EC-05 | Filling FOK tidak didukung simbol | Memakai IOC atau RETURN yang didukung | 2.1 |
| EC-06 | Partial fill | Volume terisi dan risiko dari volume itu tercatat | 3.2 |
| EC-07 | Posisi sudah ditutup broker saat EA mencoba modify | Status "posisi tidak ada", tanpa alert | 4.4 |
| EC-08 | Modify ke SL yang sama | Dianggap berhasil (tidak ada perubahan) | 4.3 |
| EC-09 | Margin tidak cukup | Ditolak di `OrderCheck` dengan `MARGIN_LOW`, tidak dikirim | 1.6 |
| EC-10 | Harness di-attach ke chart live | Gagal init | 7.1 |
| EC-11 | Nama skenario salah ketik di input harness | FAIL "skenario tidak dikenal" | 7.7 |
| EC-12 | Dua instance di akun yang sama membuat ID permintaan | ID berbeda (magic masuk ke ID) | 5.3 |
| EC-13 | Timeout, order terisi lalu langsung kena SL sebelum dicek | Deal dengan ID permintaan ditemukan di history, tidak dikirim ulang | 2.3 |
| EC-14 | EA restart di tengah urutan ulangan | Penghitung ID dari Global Variable, ID baru tidak bentrok dengan posisi lama | 5.3 |
| EC-15 | Pair JPY 3 digit (EURJPYc, GBPJPYc) | SL/TP, jarak point, dan komentar memakai digit 3 | 1.3, 1.4, 5.1 |
| EC-16 | Lot minimum akun cent 0.01 dan permintaan 0.015 | Tolak `INVALID_VOLUME` (bukan dibulatkan diam-diam) | 1.5 |
| EC-17 | Broker memotong atau mengganti komentar | Parser gagal; restart memakai sumber SL awal lain (DB, spec 06) | 5.2 |
| EC-18 | Terminal belum login saat init | Init lolos dengan akun PENDING, executor menolak `NOT_TRADABLE` sampai akun lolos | 1.7, 6.1 |
| EC-19 | Input magic 2026091900 di EA utama | Init ditolak `INIT_PARAMETERS_INCORRECT` | 7.3 |
| EC-20 | Tutup sebagian 0.025 dari 0.05 dengan step 0.01 | Tolak | 4.5 |

## Keputusan

- **[Disetujui 2026-09-29]** Alasan tolak baru `INVALID_STOPS` dan `INVALID_VOLUME` ditambahkan ke enum `reject_stage` (kolom tanpa CHECK, jadi cukup `enums.md` + `schema.py build`, tanpa migrasi).
