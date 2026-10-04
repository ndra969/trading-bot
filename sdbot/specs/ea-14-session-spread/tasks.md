# Implementation plan — 14 Filter sesi dan spread

Status: Done (2026-10-04)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.15 di task 5. Backtest dasar dijalankan dengan satu agen tester (beban CPU terbatas).

- [x] 1. Aturan filter (fungsi murni) dan input
  - Red: TC-FL-01..08 (suite baru `TestFilterRules`) terhadap stub `Filters/FilterRules.mqh` → FAIL; TS-54 → FAIL.
  - Green:
    - `SessionOfUtc`, `SessionText`, `SessionFilterOn`, `SessionAllowed`, `UtcSecOfDay`, `ServerUtcOffsetSec`, `SpreadAllowed`;
    - 5 input baru di `Inputs.mqh` / `InputValues` / validasi / `inputs_json`;
    - `gen_presets.py` (spread per simbol PC-22, sesi, offset) + 12 preset; tabel input README; TC-SU-04c dan TestPresets menyesuaikan.
  - _Requirements: 1.1–1.4, 2.1, 2.3, 4.1, 4.2_ · _Tests: TC-FL-01..08, TS-54_
  - Hasil (2026-10-04): Red = TC-FL-01..08 gagal compile, TS-54 FAIL. Green: `Filters/FilterRules.mqh` (`SessionOfUtc`, `SessionText`, `SessionFilterOn`, `SessionAllowed`, `UtcSecOfDay`, `ServerUtcOffsetSec`, `SpreadAllowed`); 5 input (grup "Filter"), validasi, `inputs_json` (43 input); `gen_presets.py` (spread per simbol PC-22, sesi, offset) + 12 preset; tabel input README; TC-SU-04c dan TestPresets diperbarui. Unit 573/573, pytest lulus.

- [x] 2. Tahap tolak di aturan sinyal
  - Red: TC-SG-25, TC-SG-26, dan string baru TC-SG-21/22 → FAIL.
  - Green:
    - `SdbSignalFacts` (`session`, `sessionAllowed`, `spreadPoints`) dan `SdbSignalParams` (`maxSpreadPoints`);
    - `EvaluateSignal` (`OUTSIDE_SESSION`, `SPREAD_TOO_WIDE` setelah pre-filter risiko);
    - `SignalContextJson` (`max_spread`, `session`).
  - _Requirements: 2.2, 3.1, 3.2_ · _Tests: TC-SG-21, 22, 25, 26_
  - Hasil (2026-10-04): Red = TC-SG-25/26 dan JSON baru TC-SG-21/22 gagal compile. Green: `SdbSignalFacts` (`session`, `sessionAllowed`, `spreadPoints`), `SdbSignalParams.maxSpreadPoints`; `EvaluateSignal` menolak `OUTSIDE_SESSION` lalu `SPREAD_TOO_WIDE` setelah pre-filter risiko; `SignalContextJson(f, d, p, bias)` + `max_spread`, `session`. Unit 575/575.

- [x] 3. Rangkaian engine dan App
  - Green:
    - `CSignalEngine.Init` + `CollectFacts`: offset → sesi UTC bar, spread ask − bid;
    - INFO sekali bila filter sesi mati;
    - `CSdbApp` meneruskan parameter; WARN sekali bila spread 0 di live.
  - Regresi: `-All` ALL PASS (TC-SGX dan SC-14 tetap lolos dengan default).
  - _Requirements: 1.2–1.4, 2.2, 3.3_ · _Tests: TC-SGX-01..03, SC-00..14x_
  - Hasil (2026-10-04): Green: `CSignalEngine.Init` + `SdbSessionParams` dan offset tester; `CollectFacts`: selisih server-UTC (`UtcOffsetNow`: tester dari input, live `TimeTradeServer - TimeGMT`, WARN bila GMT tidak ada) -> sesi UTC bar + diizinkan, spread ask - bid (point); INFO sekali bila filter sesi mati; `CSdbApp` meneruskan sesi, spread, offset; WARN sekali bila spread 0 di live. `-All` 22 run PASS (SC-14/14x dengan sesi default), unit 575/575.

- [x] 4. Skenario dan laporan pembanding
  - Red: cabang `CheckScenario` SC-15 / SC-15b + `.ini`/`.set` → jalankan; TS-55 → FAIL.
  - Green:
    - perbaikan dari temuan skenario (bug dimulai dari test case);
    - `baseline_report.py` default 200/10 + `--compare-from/--compare-to`;
    - `run-ea-tests.ps1 -Baseline -CompareFrom/-CompareTo`.
  - Verifikasi: `-Baseline` 12 simbol dibandingkan dengan backtest dasar Fase 3 (sesi 500–512). Bila kriteria 5.3 gagal, temuan dibahas dulu sebelum mengubah ambang.
  - _Requirements: 5.2, 5.3_ · _Tests: SC-15, SC-15b, TS-55, backtest dasar_
  - Hasil (2026-10-04): SC-15 (hanya Tokyo: entry hanya 00-08 UTC, OUTSIDE_SESSION tercatat) dan SC-15b (batas spread 1 point: 0 trade, SPREAD_TOO_WIDE, tidak ada tahap sesudahnya) PASS pertama kali. TS-55 Red lalu Green: `baseline_report.py` default 200/10 (PC-22) + `--compare-from/--compare-to`; runner `-Baseline -CompareFrom/-CompareTo`. Backtest dasar 12 simbol dengan filter (OHLC M1, 21 menit, CPU ~13%): LOLOS, 241 trade (11-32 per simbol), tanpa log ERROR/CRITICAL; vs Fase 3 (sesi 500-512): trade 351 -> 241, expectancy +0.024R -> +0.035R/trade, total R +8.58 -> +8.42; 6 simbol membaik, 6 memburuk (sampel kecil). Tahap tolak terbanyak: NO_PA_TRIGGER, OUTSIDE_SESSION, SCORE_TOO_LOW; SPREAD_TOO_WIDE 25-91 per simbol di EURJPY/GBPJPY/NZDUSD/USDJPY. pytest 83/83.

- [x] 5. Versi 1.15 dan dokumen
  - Versi `1.15` (EA + harness); `docs/flows/signals.md` (tahap baru); CHANGELOG; README.
  - Regresi akhir: build 0/0, `-All`, pytest, `schema.py check`.
  - _Requirements: 5.4_ · _Tests: semua_
  - Hasil (2026-10-04): versi 1.15 (EA + harness); `docs/flows/signals.md` (tahap sesi dan spread), `flows/README.md`; CHANGELOG; README. Regresi akhir: build 0/0, unit 575/575 (38 suite), `-All` 24 run PASS, pytest 84/84, `schema.py check` OK.

## Validasi manual (di luar tasks)

- [ ] MC-FL-01: EA v1.15 di akun cent EURUSDc. Log INFO/DEBUG di luar 08:00–22:00 UTC menunjukkan kandidat ditolak `OUTSIDE_SESSION`; jam UTC di detail cocok dengan jam dunia.
