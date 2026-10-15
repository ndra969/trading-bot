# Implementation plan — 38 Lab strategi kedua untuk frekuensi (H11)

Status: Done (2026-10-15)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD dengan pytest (`sdbot/tools/tests/`). Setiap task: Red → Green → "Hasil". Tanpa perubahan EA. Proses berat (run lab 12 simbol) dijalankan BelowNormal, CPU ≤ 50% core. Commit sekali di akhir spec, lalu push.

- [x] 1. Penutupan Jumat di simulator
  - Red: TS-145 (`close_after` → `FRIDAY`; tanpa parameter = hasil fixture kalibrasi spec 31 tetap), TS-146 (`friday_close`) → FAIL.
  - Green: parameter opsional `close_after` di `outcome_sim.simulate`; `friday_close` di `strategy_lab.py` (modul baru dengan konstanta).
  - Verifikasi: seluruh pytest tools PASS (uji kalibrasi spec 31 tidak berubah).
  - _Requirements: 5.4_ · _Tests: TS-145, TS-146_
  - Hasil (2026-10-15): Red ImportError; Green `simulate(close_after=)` + `friday_close`; TS-145/146 dan `test_outcome_sim.py` PASS.

- [x] 2. Range sesi dan breakout (S1, S2)
  - Red: TS-137 (server = UTC dari bar ekspor; dilewati bila CSV tidak ada), TS-138, TS-139, TS-140 → FAIL.
  - Green: `session_range`, `breakout_signal`, `setup_s1`, `setup_s2`.
  - _Requirements: 1.2, 2.1–2.3, 3.1–3.3_ · _Tests: TS-137..140_
  - Hasil (2026-10-15): Red AttributeError; Green `session_range`, `range_signal` dengan `RangeSpec` S1/S2 (ATR H1 diberikan pemanggil, deviasi kecil dari `atr_h1_of` di design). TS-137 diperbaiki: pembukaan Senin 00:00 April 2024 (histori Minggu kosong) dan celah libur ternyata ada; uji memakai penutupan Jumat 20:5x/21:5x UTC (bukti server = UTC) + ≥ 90% pembukaan Minggu 21/22. PASS.

- [x] 3. Pullback EMA H1 (S3) dan tanpa lookahead
  - Red: TS-141, TS-142 → FAIL.
  - Green: `ema_series`, `setup_s3_at` (memakai `bias_at`, `detect_pattern`, `wilder_atr` spec 32).
  - _Requirements: 1.1, 1.3, 4.1–4.3_ · _Tests: TS-141, TS-142_
  - Hasil (2026-10-15): Red AttributeError; Green `LabData` (cache ATR/EMA/bias), `ema_last`, `s3_decision` (murni), `setup_s3_at`, `signals`, `truncate`; TS-142 pada EURUSDc 2–21 Mar 2026: S1/S2/S3 muncul dan identik sesudah data dipotong. PASS.

- [x] 4. Kandidat, filter, simulasi berurutan, gabungan, aturan lolos
  - Red: TS-143, TS-144, TS-147, TS-148 → FAIL.
  - Green: `to_candidate`, `filter_candidate`, `run_sequential`, `combine`, `ea_trades`, `passes_is`, `passes_confirm`.
  - _Requirements: 1.4, 5.1–5.3, 5.5, 6.2–6.4_ · _Tests: TS-143, TS-144, TS-147, TS-148_
  - Hasil (2026-10-15): Red AttributeError; Green `to_candidate`, `filter_candidate`, `spread_share`, `run_sequential`, `combine`, `ea_trades`, `passes_is`, `passes_confirm`. PASS.

- [x] 5. CLI dan laporan
  - Red: uji CLI kecil (`run` pada fixture 2 simbol sintetis → tabel memuat kolom Req 6.1 dan baris per simbol) → FAIL.
  - Green: `main` dengan sub-perintah `run`, `confirm`, `combine`; opsi `--out` CSV.
  - Verifikasi: pytest PASS; `ruff`/`black` bersih untuk `sdbot/tools`.
  - _Requirements: 6.1_ · _Tests: TS-149_
  - Hasil (2026-10-15): Red AttributeError; Green `run_symbol`, `stats`, `run` (beberapa `--period`; sub-perintah `confirm` digabung ke `run`, deviasi design), `combine`, `--out`. pytest tools semua PASS, ruff bersih, black diterapkan.

- [x] 6. Pengukuran IS, konfirmasi, gabungan, keputusan
  - Run: `run --period IS` (S1/S2/S3 × TP 1,5R/2R) → pilih varian per setup (design §3, Req 6.2); `confirm` OOS + REAL untuk yang lolos; `combine` dengan trade EA 1.35 (2307–2318, 2376–2387, 2388–2399).
  - Catat hasil di tasks (tabel per setup × varian × periode) dan `fase-5c-overview.md` §8; keputusan H11 per setup.
  - _Requirements: 6.2–6.6_ · _Tests: RUN-01..03_
  - Hasil (2026-10-15), IS 2024-04-01..2026-07-01, 12 simbol, satu posisi per simbol per setup:

    | Setup | TP | Trade | /bulan | Win% | R/trade | Total R | PF | DD R | Spread/R | Lama (jam) |
    |---|---|---|---|---|---|---|---|---|---|---|
    | S1 London breakout | 1,5R | 2.285 | 84,7 | 40,4 | −0,015 | −34,0 | 0,97 | 99,6 | 0,045 | 18,2 |
    | S1 | 2R | 2.198 | 81,5 | 35,5 | −0,015 | −32,6 | 0,98 | 100,9 | 0,045 | 22,7 |
    | S2 NY opening range | 1,5R | 5.403 | 200,3 | 39,5 | −0,031 | −170,1 | 0,95 | 201,5 | 0,056 | 14,0 |
    | S2 | 2R | 5.146 | 190,8 | 34,3 | −0,028 | −142,2 | 0,96 | 187,4 | 0,056 | 17,0 |
    | S3 pullback EMA H1 | 1,5R | 2.834 | 105,1 | 36,9 | −0,087 | −245,9 | 0,86 | 251,4 | 0,087 | 3,0 |
    | S3 | 2R | 2.762 | 102,4 | 30,9 | −0,088 | −243,8 | 0,87 | 255,8 | 0,087 | 4,0 |

  - Dilewati: SL di luar 0,3–3 ATR (S1 502, S2 167, S3 705); spread > 15% R (S1 32, S2 458, S3 6.598: SL S3 dari ekstrem satu bar M15 sangat sempit).
  - Simbol positif (TP 1,5R): S1 5 dari 12 (AUDUSD +0,08, USDCHF +0,07 tertinggi), S2 dan S3 lebih sedikit. Tidak ada varian yang memenuhi ≥ +0,10R, PF ≥ 1,20, ≥ 7 simbol positif.
  - **H11 DITOLAK di IS** untuk ketiga setup. OOS/REAL dan simulasi gabungan tidak dijalankan (Req 6.3: hanya varian lolos IS). Breakout sesi (S1/S2) praktis acak (win rate ≈ titik impas R:R 1,5/2 dikurangi spread); pullback EMA (S3) rugi jelas.
  - Bug lab ditemukan dan diperbaiki sebelum keputusan: `filter_candidate` memakai `passes_rules` yang menguji R:R TP yang sudah dibulatkan, sehingga TP 1,5R BUY sering jadi 1,4999R dan kandidat sah tertolak (run pertama: S1 1,5R 1.744 trade). Uji TS-144b, run diulang; kesimpulan tidak berubah.

- [x] 7. Dokumen dan penutupan
  - CHANGELOG (bagian Tools), README spec; bila ada setup lolos: catatan kandidat spec EA (PC menyusul di spec EA-nya).
  - Tandai Done; commit `feat(sdbot/tools): lab strategi kedua (H11) (spec 38)`; push.
  - _Requirements: 6.5, 6.6_
  - Hasil (2026-10-15): CHANGELOG (Tools); README spec; `fase-5c-overview.md` §8. Tidak ada kandidat spec EA.

Validasi manual (di luar tasks): tidak ada; lab tidak menyentuh live.
