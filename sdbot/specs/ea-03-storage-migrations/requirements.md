# Requirements — 03 Storage dan migrasi skema

Status: Draft
Use case: UC-03 (DB), UC-05, UC-06, UC-19 ([overview](../fase-1-overview.md))
Asal: ea-foundation R17, R18.4, review skema 2026-09-28, [python-bot-lessons.md](../python-bot-lessons.md) §2–3
Butuh: spec 01 (runner, cek SQLite), spec 02 (event sink, tipe)

## Pendahuluan

Spec ini membangun penyimpanan log EA di SQLite: skema baru hasil review, migrasi skema yang dibuat dan dibangun lewat skrip (tidak pernah manual), penerapan migrasi otomatis oleh EA, pemisahan DB live dan tester, serta `CLogger` sebagai implementasi event sink.

Prinsip dari PRD tetap: DB adalah log, bukan sumber kebenaran posisi; kegagalan DB tidak boleh menghambat trading; hanya EA yang menulis `sdbot.sqlite`.

Selesai jika pytest `schema.py` dan suite `Storage` ALL PASS, `schema.py check` jalan di pre-commit, dan EA kerangka membuat serta memigrasi DB live dan tester.

## Glosarium

- **Migrasi**: file SQL bernomor di `shared/schema/migrations/data/` yang mengubah skema dari versi N−1 ke N.
- **Migrasi rilis**: migrasi yang sudah ikut rilis EA. Isinya tidak boleh berubah lagi.
- **File hasil generate**: file yang dibuat `schema.py build` dan tidak boleh diedit tangan (`Storage/Migrations.mqh`, `Core/SchemaEnums.mqh`, `shared/schema/data_db.sql`, fixture).
- **Sesi**: satu siklus hidup EA dari init sampai deinit (live), atau satu run Strategy Tester.
- **Antrean tulis**: buffer event di memori yang ditulis ke DB dalam satu transaksi di `OnTimer`.

## Requirements

### Requirement 1: Pemilihan file database

**User story:** Sebagai trader, saya ingin data live tidak pernah tercampur data backtest atau uji, agar statistik dan panel hanya menampilkan trading sungguhan.

#### Acceptance criteria

1.1. SELAMA berjalan di terminal (bukan tester) EA WAJIB menulis ke `sdbot.sqlite` di folder Common.
1.2. SELAMA berjalan di Strategy Tester (bukan optimasi) EA WAJIB menulis ke `sdbot_tester.sqlite` di folder Common, dengan skema yang sama.
1.3. SELAMA optimasi (`MQL_OPTIMIZATION`) EA WAJIB tidak membuka file database apa pun.
1.4. Suite unit test WAJIB memakai file `sdbot_unittest.sqlite` yang dihapus sebelum dan sesudah suite.

### Requirement 2: Ketahanan koneksi

**User story:** Sebagai trader, saya ingin masalah database tidak pernah menghentikan atau memperlambat trading.

#### Acceptance criteria

2.1. KETIKA database dibuka MAKA EA WAJIB menyetel `journal_mode=WAL` dan busy timeout sesuai design §4.
2.2. JIKA file tidak bisa dibuka atau dibuat MAKA EA WAJIB melanjutkan tanpa DB, mencatat log ERROR, dan mengirim alert High sekali.
2.3. JIKA penulisan gagal karena file terkunci (misalnya DB Browser sedang menulis) MAKA EA WAJIB menyimpan event di antrean dan mencoba lagi di siklus berikutnya, tanpa error berulang tiap detik.
2.4. JIKA DB tidak bisa ditulis selama 5 menit berturut-turut MAKA EA WAJIB mengirim alert High sekali, dan alert Info saat pulih.
2.5. EA WAJIB tidak pernah menulis ke database dari dalam proses pengiriman order.

### Requirement 3: Antrean tulis

**User story:** Sebagai developer, saya ingin semua penulisan DB dikumpulkan dan ditulis sekaligus, agar empat instance yang menulis file yang sama tidak saling menahan dan tidak memperlambat tick.

#### Acceptance criteria

3.1. Event dari event sink WAJIB masuk antrean di memori, lalu ditulis dalam satu transaksi per flush di `OnTimer`.
3.2. JIKA antrean mencapai kapasitas maksimum MAKA EA WAJIB membuang event tertua dengan prioritas terendah terlebih dulu (sinyal, lalu event posisi), tidak pernah membuang alert Critical, trade, deal, atau closure, dan mencatat jumlah yang dibuang.
3.3. KETIKA EA di-deinit MAKA EA WAJIB mencoba satu flush terakhir sebelum menutup database.
3.4. JIKA terminal crash sebelum flush MAKA trade, deal, dan closure yang hilang WAJIB terekam ulang oleh rekonsiliasi dari history MT5 saat start berikutnya (spec 06). Kehilangan sinyal dan event posisi dalam satu detik terakhir diterima.

### Requirement 4: Migrasi saat EA berjalan

**User story:** Sebagai trader, saya ingin skema database diperbarui otomatis saat saya memasang versi EA baru, tanpa langkah manual di MT5 atau di file DB.

#### Acceptance criteria

4.1. KETIKA database dibuka MAKA EA WAJIB membuat tabel `schema_migrations` jika belum ada, lalu menerapkan setiap migrasi yang versinya lebih tinggi dari versi DB, berurutan.
4.2. EA WAJIB menerapkan setiap migrasi dalam satu transaksi `BEGIN IMMEDIATE` dan mencatatnya di `schema_migrations` (versi, nama, checksum, waktu, versi EA) dalam transaksi yang sama.
4.3. JIKA beberapa instance membuka DB bersamaan MAKA setiap migrasi WAJIB diterapkan tepat sekali: versi dibaca ulang di dalam transaksi dan migrasi yang sudah ada dilewati.
4.4. JIKA migrasi gagal MAKA EA WAJIB me-rollback transaksi itu, membiarkan DB di versi sebelumnya, melanjutkan trading tanpa menulis DB, dan mengirim alert High.
4.5. JIKA versi DB lebih tinggi dari versi skema yang dikenal EA MAKA EA WAJIB tidak menulis ke DB sama sekali dan mengirim alert High yang menyebut kedua versi.
4.6. JIKA checksum migrasi yang tercatat di DB berbeda dengan yang dibawa EA MAKA EA WAJIB mencatat log WARN dengan nomor versinya dan tetap berjalan.
4.7. Migrasi WAJIB hanya maju. Pembatalan perubahan dilakukan dengan migrasi baru.

### Requirement 5: Pembuatan migrasi lewat skrip

**User story:** Sebagai developer, saya ingin membuat dan membangun migrasi dengan perintah, agar tidak ada file hasil generate yang diedit tangan atau lupa diperbarui.

#### Acceptance criteria

5.1. `schema.py new <db> "<deskripsi>"` WAJIB membuat file migrasi dengan nomor berikutnya dan nama slug dari deskripsi, berisi template.
5.2. `schema.py build` WAJIB menerapkan semua migrasi ke database kosong, lalu menghasilkan `Storage/Migrations.mqh`, `Core/SchemaEnums.mqh`, snapshot `shared/schema/data_db.sql`, fixture DB, dan memperbarui `migrations.lock.json`.
5.3. JIKA salah satu langkah build gagal MAKA skrip WAJIB tidak mengubah file hasil generate apa pun.
5.4. Dua kali `build` tanpa perubahan input WAJIB menghasilkan file yang identik byte per byte.
5.5. `schema.py check` WAJIB gagal jika: nomor migrasi tidak berurutan atau duplikat; migrasi rilis berubah isinya; ada migrasi yang tidak ada di lock; file hasil generate tidak sama dengan hasil build; migrasi gagal diterapkan ke DB kosong atau ke DB versi sebelumnya yang berisi data contoh; migrasi berisi pernyataan terlarang; atau nilai enum di skema dan `enums.md` tidak cocok.
5.6. Pre-commit WAJIB menjalankan `schema.py check` dan pytest skrip skema bila ada perubahan di `sdbot/shared/schema/`, `sdbot/tools/schema*`, atau file hasil generate.
5.7. `schema.py release` WAJIB menandai semua migrasi di lock sebagai rilis. Migrasi yang belum rilis boleh diedit dan di-build ulang.
5.8. File hasil generate WAJIB diawali komentar "GENERATED oleh sdbot/tools/schema.py — jangan diedit".

### Requirement 6: Kontrak enum

**User story:** Sebagai developer, saya ingin nilai teks status dan alasan hanya didefinisikan di satu tempat, agar EA, skema, dan backoffice tidak pernah berbeda ejaan.

#### Acceptance criteria

6.1. `shared/schema/enums.md` WAJIB menjadi satu-satunya sumber nilai teks enum (arah, mode sesi, tipe akun, severity, status alert, jenis event posisi, alasan tutup, alasan tolak sinyal, jenis deal, jenis operasi saldo).
6.2. `schema.py build` WAJIB menghasilkan konstanta string MQL5 di `Core/SchemaEnums.mqh` dari `enums.md`. Kode EA WAJIB memakai konstanta itu, bukan literal.
6.3. Kolom dengan himpunan nilai yang stabil (arah, mode, tipe akun, severity, status alert, entry deal, jenis operasi saldo) WAJIB dibatasi `CHECK` di skema.
6.4. Kolom dengan himpunan nilai yang akan bertambah (alasan tolak, alasan tutup, jenis event posisi, jenis alert) WAJIB tanpa `CHECK`, divalidasi oleh konstanta hasil generate dan `schema.py check`.

### Requirement 7: Isi skema versi 1

**User story:** Sebagai trader, saya ingin data yang cukup untuk menilai strategi dan eksekusi, agar keputusan tuning berdasarkan data (UC-19).

#### Acceptance criteria

7.1. Skema versi 1 WAJIB berisi tabel `sessions`, `accounts`, `signals`, `signal_scores`, `trades`, `deals`, `position_events`, `closures`, `balance_ops`, `alerts`, dan view `v_trade_results` sesuai design §3.
7.2. Setiap tabel event WAJIB membawa `session_id` dan `login`.
7.3. Semua waktu WAJIB disimpan sebagai UTC epoch detik.
7.4. Semua ticket dan ID MT5 WAJIB disimpan sebagai `INTEGER` 64-bit tanpa kehilangan nilai.
7.5. `trades`, `deals`, `closures`, dan `balance_ops` WAJIB punya kunci unik (login + ID MT5) sehingga penulisan ulang yang sama tidak membuat baris ganda.
7.6. `closures` WAJIB menyimpan alasan tutup yang membedakan SL awal, BE-stop, dan trailing-stop, beserta R hasil, MFE dan MAE dalam R, lama posisi, dan flag BE/partial/trailing.
7.7. Skor sinyal per komponen WAJIB disimpan di tabel anak `signal_scores`, agar komponen baru tidak butuh perubahan skema.

### Requirement 8: Sesi

**User story:** Sebagai developer, saya ingin setiap hasil bisa dikelompokkan per versi EA dan per setelan input, agar perubahan setting bisa dibandingkan.

#### Acceptance criteria

8.1. KETIKA EA selesai init (atau tester mulai) MAKA EA WAJIB membuat satu baris `sessions` berisi login, magic, simbol, mode (LIVE/TESTER), versi EA, hash input, nilai input dalam JSON, dan waktu mulai.
8.2. Untuk mode tester, sesi WAJIB juga menyimpan rentang tanggal dan model tester.
8.3. KETIKA EA di-deinit MAKA EA WAJIB mengisi waktu selesai dan alasan deinit.
8.4. JIKA sesi sebelumnya tidak punya waktu selesai (crash) MAKA sesi itu WAJIB tetap tanpa waktu selesai, dan panel/query memperlakukannya sebagai "berakhir tidak normal".
8.5. Hash input WAJIB sama untuk nilai input yang sama, tidak bergantung urutan penulisan.

### Requirement 9: Logger sebagai event sink

**User story:** Sebagai developer, saya ingin satu kelas yang menerima semua event dan menuliskannya, agar modul lain tidak tahu apa pun tentang SQL.

#### Acceptance criteria

9.1. `CLogger` WAJIB mengimplementasikan seluruh method `ISdbEventSink`.
9.2. `CLogger` WAJIB menyimpan alert dengan status `PENDING`, `attempts` 0, untuk dikirim Notifier di Fase 2.
9.3. `FindInitialSl` WAJIB membaca `trades.sl_initial` berdasarkan login dan position ID langsung dari DB (bukan dari antrean) dan mengembalikan `false` jika DB tidak tersedia.
9.4. Semua query WAJIB memakai parameter bind, tanpa menyambung string.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Empat instance start bersamaan pada DB kosong | Migrasi diterapkan sekali, tiga instance lain melihat versi terbaru | 4.3 |
| EC-02 | Trader memasang EA versi lama setelah versi baru memigrasi DB | EA lama tidak menulis DB, alert High menyebut versi | 4.5 |
| EC-03 | DB Browser membuka `sdbot.sqlite` dan sedang menyimpan edit | Flush gagal karena busy, antrean ditahan, dicoba tiap detik | 2.3 |
| EC-04 | DB Browser menahan kunci 10 menit | Alert High sekali di menit ke-5, antrean penuh membuang sinyal dulu | 2.4, 3.2 |
| EC-05 | File DB dihapus saat EA berjalan | Flush berikutnya membuat ulang file lewat migrasi dari awal, alert Info | 2.2, 4.1 |
| EC-06 | Disk penuh | Tulis gagal, trading jalan, alert High sekali | 2.2 |
| EC-07 | Terminal crash dengan 50 event di antrean | Trade/deal/closure direkam ulang dari history saat start; sinyal hilang | 3.4 |
| EC-08 | Developer mengedit migrasi yang sudah rilis | `check` gagal, commit tertahan | 5.5 |
| EC-09 | Migrasi menambah kolom `NOT NULL` tanpa default ke tabel berisi data | `check` gagal di langkah DB versi sebelumnya dengan data contoh | 5.5 |
| EC-10 | Migrasi berisi `BEGIN`, `COMMIT`, `PRAGMA`, atau trigger | `check` dan `build` gagal dengan nama pernyataannya | 5.5 |
| EC-11 | Teks migrasi mengandung `;` di dalam string atau komentar | Pemisah pernyataan tidak memotong di sana | 5.2 |
| EC-12 | Ticket ≥ 2^31 | Tersimpan dan terbaca utuh | 7.4 |
| EC-13 | Backtest dijalankan saat EA live juga berjalan | Keduanya menulis file berbeda, tidak saling mengunci | 1.1, 1.2 |
| EC-14 | Rekonsiliasi mencatat trade yang sudah tercatat | Tidak ada baris ganda | 7.5 |
