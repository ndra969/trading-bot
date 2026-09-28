# Requirements — 04 Eksekusi, orkestrasi, dan harness

Status: Draft
Use case: UC-07 (kirim order), UC-08 ([overview](../fase-1-overview.md))
Asal: ea-foundation R6, R4.4 (komentar), R19.3–19.4, design `CSdbApp` dan harness
Butuh: spec 02, spec 03

## Pendahuluan

Spec ini membangun satu-satunya pintu ke broker (`CExecutor`), orkestrasi event yang dipakai bersama EA dan harness (`CSdbApp`), `SDBot.mq5` yang memakai orkestrasi itu, dan harness uji yang membuka posisi terjadwal di Strategy Tester. Setelah spec ini, spec risk dan position bisa diuji dengan posisi sungguhan.

Di spec ini harness memakai lot tetap dari input. Mulai spec 05, lot dihitung `CRiskManager` dan setiap entry harness lewat pre-trade check.

Selesai jika suite `Execution` ALL PASS, skenario SC-00 dan SC-06 PASS lewat runner, dan EA terpasang di terminal live tanpa membuka posisi apa pun.

## Glosarium

- **Retcode ambigu**: hasil kirim yang tidak memastikan order tereksekusi atau tidak (timeout, koneksi putus, tanpa jawaban). Order mungkin sudah terisi.
- **ID permintaan**: kode pendek unik per permintaan order, ditulis di komentar order untuk mendeteksi eksekusi ganda.
- **Skenario**: konfigurasi harness + tester dengan assert otomatis, diberi ID `SC-nn`.

## Requirements

### Requirement 1: Validasi sebelum kirim

**User story:** Sebagai trader, saya ingin order yang tidak aman ditolak sebelum sampai ke broker, agar tidak pernah ada posisi tanpa SL atau dengan SL yang tidak masuk akal.

#### Acceptance criteria

1.1. JIKA permintaan tidak membawa SL atau TP MAKA Executor WAJIB menolaknya dengan alasan `SL_TOO_CLOSE`/`OTHER` yang jelas, tanpa memanggil broker.
1.2. JIKA SL atau TP berada di sisi yang salah (buy dengan SL ≥ harga atau TP ≤ harga, dan kebalikannya untuk sell) MAKA Executor WAJIB menolaknya.
1.3. Executor WAJIB menormalkan SL dan TP ke digit simbol memakai harga ask/bid terbaru.
1.4. JIKA jarak SL atau TP dari harga lebih kecil dari stops level + spread, atau harga berada di dalam freeze level, MAKA Executor WAJIB menolak dengan alasan `SL_TOO_CLOSE`.
1.5. JIKA volume di luar `SYMBOL_VOLUME_MIN`–`SYMBOL_VOLUME_MAX`, tidak kelipatan step, atau melewati `SYMBOL_VOLUME_LIMIT` bersama posisi yang ada, MAKA Executor WAJIB menolak.
1.6. Executor WAJIB memanggil `OrderCheck` sebelum mengirim. JIKA margin tidak cukup atau `OrderCheck` menolak MAKA order WAJIB tidak dikirim dan alasannya dicatat.

### Requirement 2: Pengiriman dan retry

**User story:** Sebagai trader, saya ingin error sementara broker ditangani otomatis tanpa pernah membuka posisi ganda.

#### Acceptance criteria

2.1. Executor WAJIB mengirim market order dengan MagicNumber, SL, TP, deviasi maksimum, filling mode yang didukung simbol, dan komentar berisi SL awal dan ID permintaan.
2.2. KETIKA broker mengembalikan retcode sementara (requote, harga berubah, tanpa harga) MAKA Executor WAJIB mengulang maksimal 3 kali dengan jeda, dan memvalidasi ulang SL/TP terhadap harga baru sebelum setiap ulangan.
2.3. KETIKA broker mengembalikan retcode ambigu MAKA Executor WAJIB memeriksa posisi terbuka dengan ID permintaan yang sama sebelum mengulang. Jika ditemukan, order dianggap berhasil dan tidak diulang.
2.4. JIKA retcode permanen (pasar tutup, volume tidak valid, dana tidak cukup, trading dimatikan) atau ulangan habis MAKA Executor WAJIB berhenti, mencatat log ERROR dengan retcode dan deskripsinya, dan mengirim alert Medium `ORDER_FAILED`.
2.5. Executor WAJIB tidak mengirim order ketika `CAccount::CanTrade` bernilai false.

### Requirement 3: Pencatatan hasil

**User story:** Sebagai trader, saya ingin harga isi, slippage, dan risiko aktual setiap order tercatat, agar kualitas eksekusi broker bisa dinilai.

#### Acceptance criteria

3.1. KETIKA order terisi MAKA Executor WAJIB mengirim `TradeRecord` ke event sink: position ID, magic, simbol, arah, volume terisi, harga diminta, harga isi, slippage entry (point, negatif jika merugikan), spread saat entry, SL awal, TP awal, risiko uang dari harga isi dan volume terisi, signal ID, versi EA.
3.2. JIKA volume terisi lebih kecil dari yang diminta (partial fill) MAKA Executor WAJIB mencatat volume terisi dan risiko dari volume itu, serta log WARN.
3.3. JIKA harga isi tidak tersedia di hasil `OrderSend` MAKA Executor WAJIB membacanya dari deal di history, dan menandai record bila tetap tidak tersedia.

### Requirement 4: Satu pintu ke broker

**User story:** Sebagai developer, saya ingin semua perubahan posisi lewat satu kelas yang menegakkan aturan keamanan, agar modul lain tidak bisa melanggarnya.

#### Acceptance criteria

4.1. `CExecutor` WAJIB menjadi satu-satunya pemilik `CTrade` dan satu-satunya pemanggil fungsi trading di EA.
4.2. `ModifySl` WAJIB menolak SL yang tidak lebih baik dari SL sekarang, SL yang melanggar stops/freeze level, dan SL di sisi harga yang salah.
4.3. JIKA broker mengembalikan "tidak ada perubahan" untuk modifikasi MAKA Executor WAJIB menganggapnya berhasil.
4.4. JIKA posisi sudah tidak ada saat modify atau close MAKA Executor WAJIB mengembalikan status "posisi tidak ada" tanpa retry dan tanpa alert.
4.5. `ClosePartial` WAJIB menolak volume ≤ 0, volume ≥ volume posisi, dan volume yang membuat sisa < lot minimum.
4.6. Setiap operasi Executor hanya boleh menyentuh posisi dengan magic dan simbol instance ini, kecuali operasi emergency lintas pair yang diputuskan di spec 05 (R2-1).

### Requirement 5: Komentar order

**User story:** Sebagai developer, saya ingin komentar order membawa informasi yang dibutuhkan untuk restart aman dan deteksi order ganda, dalam batas panjang MT5.

#### Acceptance criteria

5.1. Komentar WAJIB berformat `SDB|<SL awal>|<ID permintaan>` dan tidak lebih dari 31 karakter.
5.2. Parser WAJIB mengembalikan SL awal dan ID permintaan dari komentar yang valid, dan gagal untuk komentar lain (termasuk komentar yang diubah broker).

### Requirement 6: Orkestrasi event

**User story:** Sebagai developer, saya ingin EA utama dan harness menjalankan urutan init, tick, timer, dan transaksi yang sama persis.

#### Acceptance criteria

6.1. `CSdbApp` WAJIB menjalankan urutan init: validasi input → state → akun → storage dan sesi → modul → timer 1 detik.
6.2. JIKA langkah init yang wajib gagal MAKA `CSdbApp` WAJIB mengembalikan kode init yang sesuai dan melepas semua yang sudah dibuat.
6.3. `CSdbApp` WAJIB meneruskan `OnTick`, `OnTimer`, `OnTradeTransaction`, `OnTester`, dan `OnDeinit` ke modul dalam urutan di design §3.4, dengan risk monitor sebelum flush storage di setiap timer.
6.4. KETIKA EA di-deinit MAKA `CSdbApp` WAJIB mencatat alasan deinit, menutup sesi, flush storage, melepas handle, dan menghapus semua objek yang dibuat.
6.5. `SDBot.mq5` WAJIB hanya meneruskan event ke `CSdbApp` dan tidak berisi logika lain.
6.6. EA utama WAJIB tidak berisi kode pembuka posisi uji. Sebelum Fase 3, EA utama tidak membuka posisi sama sekali.

### Requirement 7: Harness uji

**User story:** Sebagai developer, saya ingin harness yang membuka posisi terjadwal dan mengecek hasil skenario otomatis, agar setiap spec berikutnya bisa dibuktikan di Strategy Tester.

#### Acceptance criteria

7.1. JIKA harness tidak berjalan di Strategy Tester MAKA harness WAJIB gagal init dengan log CRITICAL.
7.2. Harness WAJIB memakai `CSdbApp` dan modul yang sama dengan EA utama, ditambah jadwal entry dari input (setiap N bar LTF, arah, jarak SL dan TP dalam point, jumlah posisi maksimum).
7.3. Entry harness WAJIB lewat `CExecutor::OpenMarket`. Mulai spec 05, entry juga lewat pre-trade check dan perhitungan lot `CRiskManager`.
7.4. Harness WAJIB bisa mensimulasikan restart: di bar tertentu, instance `CSdbApp` dihapus lalu dibuat dan di-init ulang, dengan Global Variables dan posisi tetap ada.
7.5. Harness WAJIB merekam event yang dikirim ke sink (tanpa mengubah penulisan ke DB) dan, di `OnDeinit`, mengecek harapan skenario yang dipilih lewat input, lalu menulis `SC-nn PASS/FAIL` beserta alasan ke file hasil yang dibaca runner.
7.6. JIKA skenario yang dipilih tidak dikenal harness MAKA hasilnya WAJIB FAIL, bukan PASS.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Timeout saat kirim, padahal order terisi di server | Posisi dengan ID permintaan ditemukan, tidak dikirim ulang | 2.3 |
| EC-02 | Requote 3 kali berturut-turut | Berhenti setelah ulangan ke-3, alert Medium | 2.2, 2.4 |
| EC-03 | Harga bergerak saat requote sehingga SL jadi terlalu dekat | Ulangan dibatalkan dengan `SL_TOO_CLOSE` | 2.2 |
| EC-04 | Pasar tutup (akhir pekan) saat order | Tolak tanpa retry, satu alert | 2.4 |
| EC-05 | Filling FOK tidak didukung simbol | Memakai IOC atau RETURN yang didukung | 2.1 |
| EC-06 | Partial fill | Volume terisi dan risiko dari volume itu tercatat | 3.2 |
| EC-07 | Posisi sudah ditutup broker saat EA mencoba modify | Status "posisi tidak ada", tanpa alert | 4.4 |
| EC-08 | Modify ke SL yang sama | Dianggap berhasil (tidak ada perubahan) | 4.3 |
| EC-09 | Margin tidak cukup | Ditolak di `OrderCheck`, tidak dikirim | 1.6 |
| EC-10 | Harness di-attach ke chart live | Gagal init | 7.1 |
| EC-11 | Nama skenario salah ketik di input harness | FAIL "skenario tidak dikenal" | 7.6 |
| EC-12 | Dua instance di akun yang sama membuat ID permintaan | ID tetap unik (menyertakan magic dan penghitung) | 5.1 |
