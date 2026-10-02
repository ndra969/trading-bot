# Implementation plan — 12 Trigger price action

Status: Done (2026-10-03)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`. Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.11 di task 4.

- [x] 1. Enum, tipe, konstanta
  - Red: pytest enum (`pa_pattern` ada, kolom `signals.context_json`) → FAIL
  - Green: `enums.md` + `schema.py build` (`SDB_PA_PATTERN_*`); `SdbPattern` di Types; konstanta `SDB_PA_*`
  - _Requirements: 2.2_ · _Tests: TS-49_
  - Hasil (2026-10-03): Red = TS-49 FAIL. Green: enum `pa_pattern` (STAR, ENGULF_STRONG, PIN, ENGULF, TWEEZER, OUTSIDE, NONE; kolom `signals.context_json`, tanpa CHECK) + `schema.py build` (data tetap v3, konstanta `SDB_PA_PATTERN_*`); `SdbPattern` di Types; konstanta ambang `SDB_PA_*`. pytest 67/67.

- [x] 2. Pola (fungsi murni)
  - Red: TC-PA-01..22 (suite baru `TestPatterns`) terhadap stub `Strategies/PatternRules.mqh` → FAIL
  - Green: `IsStar`, `IsEngulfStrong`, `IsPin`, `IsEngulf`, `IsTweezer`, `IsOutside`, `DetectPattern`, `PaScore`
  - _Requirements: 1.1–1.5, 2.1, 4.1_ · _Tests: TC-PA-01..22_
  - Hasil (2026-10-03): Red = Patterns pass=3 fail=19 terhadap stub. Green: `Strategies/PatternRules.mqh` (`IsStar`, `IsEngulfStrong`, `IsPin`, `IsEngulf`, `IsTweezer`, `IsOutside`, `DetectPattern`, `PaScore`; toleransi `SDB_PA_EPS` x ATR). Unit 529/529 (30 suite), build 0/0. Di luar rencana: `tools/run-ea-tests.ps1` run unit kini mulai di Selasa..Jumat (mulai Sabtu membuat 14 uji pembuka posisi gagal "market closed").

- [x] 3. `CPaTrigger` dan rangkaian App
  - Red: TC-PAX-01..02 (suite baru `TestPaTrigger`, tester) → FAIL
  - Green: `Strategies/PaTrigger.mqh`; `CSdbApp`: member, `InitAnalysis` (LTF dari gaya), `OnTick`, accessor `Trigger()`
  - Regresi: `run-ea-tests.ps1 -All` ALL PASS
  - _Requirements: 3.1, 3.2_ · _Tests: TC-PAX-01..02, SC-00..13x_
  - Hasil (2026-10-03): Red = TC-PAX-01..02 FAIL terhadap stub. Green: `Strategies/PaTrigger.mqh` (`CPaTrigger`, `CBarCache` 45 bar, ATR Wilder, hasil BUY/SELL, WARN throttled bila histori kurang); `CSdbApp`: member `m_trigger`, init di `InitAnalysis` (LTF dari gaya), `OnTick` setelah zona, accessor `Trigger()`. Unit 531/531 (31 suite); `-All` 20 run PASS, build 0/0.

- [x] 4. Versi 1.11 dan dokumen
  - Versi `1.11`; `docs/flows/` (`pa-trigger.md` baru, tick); `CHANGELOG.md`; README
  - Regresi akhir: `run-ea-tests.ps1 -All`, pytest, build 0/0
  - _Requirements: 4.2_ · _Tests: semua_
  - Hasil (2026-10-03): versi 1.11 (EA + harness; deskripsi `#property` yang tertinggal v1.09 diperbaiki); `docs/flows/pa-trigger.md` baru, `tick.md`, `flows/README.md`; CHANGELOG; README. Regresi akhir: build 0/0, unit 531/531 (31 suite), `-All` 20 run PASS, pytest 67/67, `schema.py check` OK.

## Validasi manual (di luar tasks)

- [ ] MC-PA-01: EA v1.11 di chart EURUSDc M15 akun cent: log DEBUG pola per bar cocok dengan pembacaan visual beberapa candle (engulfing, pin bar).
