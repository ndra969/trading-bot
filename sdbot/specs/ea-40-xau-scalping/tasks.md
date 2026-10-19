# Implementation plan — 40 Riset scalping XAUUSD (H14)

Status: Done (2026-10-19)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD dengan pytest (`sdbot/tools/tests/test_strategy_lab.py`). Setiap task: Red → Green → "Hasil". Tanpa perubahan EA. Backtest satu proses terminal uji BelowNormal, CPU ≤ 50% core. Commit sekali di akhir spec, lalu push.

- [x] 1. Entry M5 di simulator
  - Red: TS-150 (`bar_sec=300` → entry t + 300) → FAIL.
  - Green: parameter `bar_sec` di `osim.simulate` (default 900).
  - Verifikasi: semua pytest tools PASS (kalibrasi spec 31, TS-145).
  - _Requirements: 2.3_ · _Tests: TS-150_
  - Hasil (2026-10-19): Red TypeError; Green `simulate(bar_sec=)`; semua pytest tools PASS.

- [x] 2. Indikator dan keputusan mean reversion
  - Red: TS-151 (`bollinger`, `rsi_wilder`), TS-152 (`mr_decision`), TS-153 (`filter_mr`) → FAIL.
  - Green: konstanta X2, `bollinger`, `rsi_wilder`, `mr_decision`, `filter_mr`; `Signal.tp`, `to_candidate(tp=)`; aturan exit X2.
  - _Requirements: 2.2, 2.4, 2.5, 2.6_ · _Tests: TS-151..153_
  - Hasil (2026-10-19): Red AttributeError; Green `bollinger`, `rsi_wilder`, `mr_decision`, `filter_mr` (R:R sebelum pembulatan), `MR_RULES`, `Signal.tp`, `to_candidate(tp=)`. PASS.

- [x] 3. Sinyal M5, pembanding acak, tanpa lookahead
  - Red: TS-154, TS-155 → FAIL.
  - Green: `load_xau5` (M5 + ATR M5), `mr_signals`, `random_signals`.
  - _Requirements: 2.1, 2.3, 3.3_ · _Tests: TS-154, TS-155_
  - Hasil (2026-10-19): Red AttributeError; Green `Xau5`, `load_xau5`, `truncate_xau5`, `atr_series`, `mr_signals`, `random_signals`, `run_xau`. TS-154 pada XAUUSDc 2–14 Mar 2026 identik sesudah data dipotong. PASS.

- [x] 4. Laporan EA dan CLI `xau`
  - Red: TS-156 (`ea_report` pada DB sintetis) → FAIL.
  - Green: `ea_report`; sub-perintah `xau` (baris X1 dari `--ea`, X2, ACAK; tanda lolos Req 3.1/3.2); ruff + black.
  - _Requirements: 1.2, 1.3, 3.1–3.3_ · _Tests: TS-156_
  - Hasil (2026-10-19): Red AttributeError; Green `ea_report`, `passes_xau_is`, `cmd_xau` (`stats(entry_lag=)`). pytest tools semua PASS, ruff bersih, black.

- [x] 5. Pengukuran IS, konfirmasi, keputusan
  - Run X1: `-Baseline -Period IS -Symbols XAUUSDc -SetInput InpTradingStyle=0`; X2 + ACAK: `xau --period IS --ea IS=<sesi X1>`.
  - Setup yang lolos IS: OOS + REAL (X1 di tester, X2 di lab), aturan Req 3.2.
  - Catat tabel hasil di tasks dan `fase-5c-overview.md` §8; keputusan H14 per setup.
  - _Requirements: 1.1, 3.1–3.5_ · _Tests: RUN-01..03_
  - Hasil (2026-10-19), IS 2024-04-01..2026-07-01, XAUUSDc:

    | Setup | Trade | /bulan | Win% | R/trade | Total R | PF | DD R | Spread/R | Lama (jam) |
    |---|---|---|---|---|---|---|---|---|---|
    | Acuan DAY 1.31 (sesi 1979) | 17 | 0,6 | — | +0,587 | +10,0 | 2,98 | — | — | 11,3 |
    | X1 S&D SCALPING M15/M5/M1 (sesi 2618) | 128 | 4,7 | 28,9 | −0,321 | −41,1 | 0,55 | 42,7 | 0,084 | 1,2 |
    | X2 mean reversion BB/RSI M5 | 449 | 16,6 | 18,5 | −0,020 | −8,8 | 0,98 | 51,9 | 0,063 | 1,0 |
    | ACAK (SL 1 ATR M5, TP 1,5R) | 2.495 | 92,5 | 37,6 | −0,060 | −150,4 | 0,90 | 162,2 | 0,059 | 0,5 |

  - X1: 71% trade kena SL penuh (91 dari 128); zona M5 jauh lebih sering tembus, sama dengan pola spec 34/36. Tolak terbanyak: zona tidak valid 23.480, di luar sesi 3.486, tanpa PA 2.971.
  - X2: sedikit di atas acak (−0,02R vs −0,06R) tetapi tidak positif; 597 kandidat dilewati karena SL < 0,5 ATR (close di luar band biasanya dekat ekstrem bar).
  - **H14 DITOLAK di IS** untuk X1 dan X2 (frekuensi < 20/bulan dan R/trade < +0,10). OOS/REAL tidak dijalankan.

- [x] 6. Dokumen dan penutupan
  - CHANGELOG (Tools), README spec; bila ada setup lolos: catatan kandidat spec EA.
  - Tandai Done; commit `feat(sdbot/tools): riset scalping XAUUSD (H14) (spec 40)`; push.
  - _Requirements: 3.4, 3.5_
  - Hasil (2026-10-19): CHANGELOG (Tools); README spec; `fase-5c-overview.md` §8. Tidak ada kandidat spec EA.

Validasi manual (di luar tasks): tidak ada; riset tidak menyentuh live.
