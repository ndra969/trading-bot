# Implementation plan — 03 Storage dan migrasi skema

Status: Draft
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD di dua sisi: pytest untuk `schema.py` (`uv run pytest -c sdbot/tools/pytest.ini`), dan suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`. Hasil verifikasi ditulis di baris "Hasil" tiap task.

- [x] 1. Kontrak data: enum, migrasi awal, data contoh
  - `shared/schema/enums.md` (tabel enum: nilai, CHECK ya/tidak, kolom yang memakai), `migrations/data/0001_initial.sql` (design §3), `migrations/data/seed_sample.sql` (blok per versi), `shared/schema/README.md` (aturan data dan alur migrasi)
  - Verifikasi: SQL diterapkan ke SQLite kosong lewat Python tanpa error
  - _Requirements: 6.1, 6.3, 6.4, 7.1–7.7_
  - Hasil (2026-09-29): `0001_initial.sql` + `seed_sample.sql` diterapkan ke SQLite 3.50 in-memory tanpa error: 10 tabel + view terisi (sessions 2, trades 5, deals 9, closures 4, …); `v_trade_results` menampilkan posisi rekonsiliasi dengan closure NULL; deal ticket 7.000.000.009 (> 2^32) utuh. `enums.md` punya kolom "Kolom" agar `schema.py` bisa mencocokkan CHECK; enum baru `deal_reason`, `deinit_reason`, nilai `SL_RESTORED` (spec 06) dan `MARGIN_OK` (spec 05).

- [x] 2. `schema.py` inti: pemisah pernyataan, validasi, penerapan
  - Red: `tools/tests/test_schema.py` TS-08, TS-09, TS-14, TS-15, TS-16 (dan TS-07 untuk penomoran) terhadap modul kosong
  - Green: tokenizer pemisah pernyataan, larangan pernyataan, pembaca migrasi dan penomoran, penerapan ke DB kosong dan bertahap dengan data contoh
  - _Requirements: 5.5 (sebagian), 7.1, 7.4, 7.5_ · _Tests: TS-07..09, TS-14..16_
  - Hasil (2026-09-29): Red = 16 FAIL (modul stub). Green = 16/16 (`uv run pytest -c sdbot/tools/pytest.ini`). Satu perbaikan saat Green: komentar setelah `;` sempat terbawa ke awal pernyataan berikutnya; komentar di awal pernyataan kini dibuang. Checksum dinormalkan ke LF agar checkout CRLF di Windows tidak mengubahnya. `sdbot/tools/pytest.ini` sendiri agar addopts coverage bot Python tidak ikut.

- [x] 3. `schema.py` build/check/new/release/status dan file hasil generate
  - Red: TS-01..06, TS-10..13 terhadap perintah yang belum ada
  - Green: `new`, `build` (atomik, deterministik), `check`, `release`, `status`; generator `Storage/Migrations.mqh`, `Core/SchemaEnums.mqh`, `data_db.sql`, fixture; lock checksum; pencocokan CHECK dengan `enums.md`
  - Jalankan `build` sungguhan untuk skema v1, commit file hasil generate
  - _Requirements: 5.1–5.8, 6.2, 6.3_ · _Tests: TS-01..06, TS-10..13_
  - Hasil (2026-09-29): Red = 15 FAIL (CLI belum ada). Green = 31/31 (inti 16 + CLI 15; tambahan: migrasi baru tanpa build, CHECK tanpa enum, konstanta/validator SchemaEnums, fixture, status, file hasil berakhir satu newline tanpa spasi akhir). `build` sungguhan skema v1 menghasilkan 6 file dan `check` lolos. Dua bug ditemukan saat build sungguhan dan diperbaiki: `os.replace` tidak bisa lintas drive (TEMP di C:, repo di D:) sehingga staging dipindah ke dalam `sdbot/`; snapshot berakhir dua newline yang akan diubah hook end-of-file-fixer. Fixture dibandingkan lewat `iterdump` (bukan byte) agar tidak bergantung versi SQLite.

- [x] 4. Pre-commit
  - Hook `sdbot-schema-check` dan `sdbot-schema-tests` di `.pre-commit-config.yaml` (design §5)
  - Verifikasi: commit yang mengubah `enums.md` tanpa `build` ditolak hook
  - _Requirements: 5.6_
  - Hasil (2026-09-29): hook `sdbot-schema-check` dan `sdbot-schema-tests` ditambahkan; `pre-commit validate-config` valid. Uji: `enums.md` ditambah nilai tanpa `build` → hook gagal dengan "SchemaEnums.mqh tidak sama dengan hasil build"; setelah dikembalikan kedua hook Passed. Pytest memakai `-c sdbot/tools/pytest.ini` agar coverage bot Python tidak ikut.

- [x] 5. Struct event lengkap, kode enum dari hasil generate, util waktu dan hash
  - Red: suite `TestStorageUtil` (UTC offset, `ServerToUtc`, JSON input kanonik, hash input) terhadap stub
  - Green: lengkapi `TradeRecord`, `DealRecord`, `PositionEvent`, `ClosureRecord`, `BalanceOpRecord` sesuai skema; `SDB_ALERT_*` di `Constants.mqh` diganti konstanta dari `SchemaEnums.mqh`; `ServerUtcOffset`, `ServerToUtc`, `CanonicalJson`, `Sha256Hex`, `CurrentInputsJson`
  - _Requirements: 6.2, 7.3, 8.5_ · _Tests: TC-DB-11, TC-DB-14, TC-SU-xx_
  - Hasil (2026-09-29): Red = 12 FAIL (stub). Green: suite `Codec` 14/14 (TC-SU-01a..d pembulatan offset ke 15 menit, TC-DB-11, TC-SU-02a..c JSON kanonik, TC-SU-03 SHA-256 vektor NIST, TC-DB-14a/b hash input, TC-SU-04a..c `CurrentInputsJson` 17 input); total unit 111/111, build 0/0. Nama akhir: suite `TestCodec` (bukan `TestStorageUtil`) dan `RoundUtcOffset` (fungsi murni; pembacaan `TimeTradeServer()-TimeGMT()` ada di Logger). Struct event mengikuti kolom `data_db.sql`, kolom NULL memakai `SDB_NULL_DOUBLE`/`SDB_NULL_LONG`; `AccountSnapshot.peakEquity` ditambahkan (sementara = equity sampai spec 05). `SDB_ALERT_*` sementara dihapus dari `Constants.mqh`, `CAccount` memakai `SDB_ALERT_TYPE_*` dari `SchemaEnums.mqh`.

- [x] 6. Runner migrasi di EA
  - Red: suite `TestStorage` TC-DB-01..05 terhadap runner kosong
  - Green: `Storage/MigrationRunner.mqh` (buat `schema_migrations`, `BEGIN IMMEDIATE` per migrasi, baca ulang versi di dalam transaksi, rollback, versi DB lebih baru, cek checksum) dengan sumber migrasi berupa interface agar migrasi gagal bisa disuntik di uji
  - _Requirements: 4.1–4.7_ · _Tests: TC-DB-01..05_
  - Hasil (2026-09-29): Red = 13 FAIL (runner stub). Green: suite `Migrations` 17/17, total unit 128/128, build 0/0. `Storage/MigrationSource.mqh` (interface `ISdbMigrationSource`) + `Storage/MigrationRunner.mqh` (`CSdbMigrationRunner::Run` → OK / NEWER_DB / FAILED). Migrasi gagal disuntik lewat `CFailingMigrations` di suite (v2 gagal di pernyataan kedua → pernyataan pertama ikut di-rollback, versi tetap 1, tidak ada transaksi tertinggal; v1 gagal di DB kosong → versi 0). Versi terbaru diambil dari sumber (bukan `SDB_SCHEMA_LATEST`) agar sumber palsu bisa diuji. Baca ulang versi di dalam `BEGIN IMMEDIATE` (4.3) belum diuji dengan dua instance sungguhan; tercakup MC-DB-02.

- [ ] 7. `CLogger`: buka DB, sesi, antrean, flush, event sink
  - Red: TC-DB-06..10, 12, 13, 15, 16 terhadap stub
  - Green: `Storage/Logger.mqh`: target LIVE/TESTER/UNITTEST/NONE, pragma, sesi, antrean berprioritas, flush satu transaksi, penulisan idempoten, NULL lewat nilai penanda, `FindInitialSl`, alert `DB_*`, buka ulang bila file hilang
  - _Requirements: 1.1–1.4, 2.1–2.5, 3.1–3.4, 8.1–8.4, 9.1–9.4_ · _Tests: TC-DB-06..10, 12, 13, 15, 16_

- [ ] 8. Pasang di `SDBot.mq5` v1.02
  - `OnInit`: buka logger (LIVE / TESTER / NONE saat optimasi) dan sesi, logger menjadi sink `CAccount`; `OnTimer`: flush setelah pemeriksaan akun; `OnDeinit`: akhiri sesi dan flush terakhir
  - Verifikasi: build 0/0, unit ALL PASS, smoke run tester membuat `sdbot_tester.sqlite` dengan `sessions` (mode TESTER), `accounts`, dan `schema_migrations` versi 1; `sdbot.sqlite` tidak tersentuh
  - _Requirements: 1.1–1.3, 8.1, 8.3_

## Validasi manual (di luar tasks)

- [ ] MC-DB-01: DB Browser menahan kunci `sdbot.sqlite` 6 menit saat EA live → WARN, alert High di menit ke-5, Info setelah dilepas, tidak ada event hilang
- [ ] MC-DB-02: backtest dijalankan saat EA live berjalan → dua file terpisah, tidak ada error kunci
