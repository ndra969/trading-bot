# Implementation plan — 34 Gaya intraday H1/M15/M5 (H7)

Status: Done (2026-10-13)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`;
- skema lewat `uv run python sdbot/tools/schema.py check`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Satu proses terminal uji, CPU ≤ 50% core.

- [x] 1. Gaya INTRADAY di EA
  - Red: TC `StyleTimeframes(INTRADAY)` + gaya lama, TC `SdbStyleText`, TC-IR-04 (bila ada validasi rentang) → FAIL.
  - Green: `SDB_STYLE_INTRADAY = 4`, pemetaan H1/M15/M5, teks `INTRADAY`, rentang validasi.
  - Verifikasi: unit ALL PASS, compile 0/0.
  - _Requirements: 1.1, 1.2_ · _Tests: TC-CU, TC-SE, TC-IR-04_
  - Hasil (2026-10-12): TC-CU-18 (H1/M15/M5, nilai 4) dan TC-SGX-04 (teks gaya) PASS; `InpTradingStyle` tidak divalidasi rentang (input enum), jadi TC-IR-04 tidak dibuat. Red tidak dijalankan terpisah: terminal uji dipakai backtest saat kode ditulis.

- [x] 2. Skema v5: `INTRADAY` di `signals.style`
  - Red: `enums.md` + `INTRADAY` → `schema.py check` FAIL (enum tidak cocok dengan CHECK).
  - Green: `schema.py new data "style intraday"`; SQL rebuild `signals` (design §3); `schema.py build`; seed bila perlu.
  - Verifikasi: `schema.py check` OK (baris `signals` sama sebelum/sesudah pada seed), pytest PASS, compile 0/0, unit ALL PASS (Migrations).
  - _Requirements: 1.4_ · _Tests: TS schema, Migrations suite_
  - Hasil (2026-10-12): Red `schema.py check` GAGAL (CHECK != enums.md); Green migrasi `0005_style_intraday.sql` (rebuild `signals`, indeks dibuat ulang), `schema.py build` v5 (SchemaEnums, Migrations, data_db.sql, fixture), `check` OK. Fixture `conftest.py` proyek v1 membuang nilai enum yang datang belakangan (`V1_LATER_VALUES`). TC-DB-01e diubah ke `>= 4`, TC-DB-01g baru (INTRADAY diterima, nilai lain ditolak, 2 indeks). Unit 684/0, pytest PASS.

- [x] 3. Skenario SC-34, versi, regresi
  - Red: file SC-34 dibuat lebih dulu → FAIL (skenario tak dikenal).
  - Green: `CheckSc34`; versi 1.32 (EA + harness); README tabel konfigurasi; `docs/flows/`.
  - Verifikasi: SC-34 PASS; `-All` di background semua PASS.
  - _Requirements: 1.3, 1.4, 1.5_ · _Tests: SC-34, REG_
  - Hasil (2026-10-12, sebagian): `CheckSc34`, versi 1.32 (EA + harness), README. SC-34 periode awal 2026.08.01–09.26 gagal `-entry` (519 kandidat INTRADAY, 0 ACCEPTED: prasyarat periode), diperpanjang ke 2026.04.01–09.26 → SC-34 pass=2. DB tester termigrasi ke v5 oleh harness (schema_migrations 5). Red SC-34 tidak dijalankan terpisah (checker ditulis bersama file skenario). `-All` 36 run PASS (unit 684/0), 42 menit.

- [x] 4. Laporan frekuensi dan lama posisi
  - Red: TS baru untuk frekuensi per bulan dan lama posisi rata-rata (di `exit_report.py` atau `baseline_report.py`, yang paling dekat) → FAIL.
  - Green: kolom baru + README tools.
  - _Requirements: 2.2_ · _Tests: TS baru_
  - Hasil (2026-10-12): Red TS-114 FAIL; Green `exit_report.py` kolom `TRADE/BLN` (trade ÷ bulan rentang tester sesi) dan `HOLD j` (rata-rata `holding_sec`); TS-90 disesuaikan (kolom give-back bukan kolom terakhir lagi); pytest PASS. Acuan 1.31 IS: 4,5 trade per bulan, posisi rata-rata 5,4 jam.

- [x] 5. Pengukuran IS
  - Run: `-Baseline -Period IS` untuk V1 (`InpTradingStyle=4`), V2 (`InpTradingStyle=4`, `InpMinRR=1.5`), V3 (`InpMinRR=1.5`); timeout per simbol diperbesar bila perlu.
  - Laporan Req 2.2 vs acuan 1968–1979; aturan design §5.
  - _Requirements: 2.1–2.5_ · _Tests: RUN-01_
  - Hasil (2026-10-13), acuan 1.31 (1968–1979): 121 trade, 4,5/bulan, +0,164R, PF 1,39, +19,8R, DD 6,6R, posisi 5,4 jam.
  - V1 INTRADAY R:R 2 (2105–2116): 255 trade, 9,5/bulan, −0,117R, PF 0,79, −29,8R, DD 42,2R, posisi 1,9 jam.
  - V2 INTRADAY R:R 1,5 (2117–2128): 383 trade, 14,2/bulan, −0,093R, PF 0,83, −35,5R, DD 53,8R, posisi 2,0 jam.
  - V3 DAY R:R 1,5 (2129–2140): 162 trade, 6,0/bulan, +0,036R, PF 1,08, +5,9R, DD 13,4R.
  - Sebab (V1 vs acuan): SL 55% vs 43% trade; kena SL tanpa pernah +0,3R 27% vs 21%; biaya spread 19,8% vs 12,1% dari risiko (SL M15 lebih pendek, spread sama). R:R 1,5 menambah trade tetapi TP lebih kecil tidak menutup SL yang lebih sering.
  - Aturan §5: tidak ada varian lolos (V1/V2 R per trade dan total R negatif; V3 total R +5,9 < +19,8 dan trade 162 < 242). **H7 DITOLAK di IS**, OOS dan REAL tidak dijalankan.

- [x] 6. Konfirmasi OOS dan REAL, keputusan
  - Bila ada varian terpilih: `-Period OOS` dan `REAL`; aturan design §5.4.
  - Bila DITERIMA: default gaya/R:R, preset 12 simbol, uji default (Red dulu), versi 1.33. Bila DITOLAK: default tetap, versi 1.32.
  - _Requirements: 3.1–3.4_ · _Tests: RUN-02_
  - Hasil (2026-10-13): tidak dijalankan (H7 ditolak di IS). Default tetap DAY dan R:R 2,0; gaya INTRADAY tetap tersedia untuk eksperimen; versi 1.32.

- [x] 7. Dokumen dan regresi akhir
  - PC: §Gaya dan timeframe, §Aturan entry, §Parameter input (bila diterima), skema v5 (`signals.style`).
  - CHANGELOG, README spec dan EA, `fase-5c-overview.md` §8.
  - Regresi akhir: build 0/0, `-All`, pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot/ea): gaya intraday (H7) v1.3x (spec 34)`.
  - _Requirements: 3.5_ · _Tests: semua, REG_
  - Hasil (2026-10-13): PC-35 (Open); CHANGELOG 1.32; README spec, EA, tools; `fase-5c-overview.md` §8. Regresi: `-All` 36 PASS (task 3, kode tidak berubah sesudahnya); pytest PASS; `schema.py check` OK.

## Validasi manual (di luar tasks)

- Bila diterima: pasang di Broker B (timpa ex5, restart, muat ulang preset lokal dengan risk 0,5% / XAU-XAG 1%); EA memigrasi `sdbot.sqlite` ke v5 saat start; cek `schema_migrations` dan `sessions`.
