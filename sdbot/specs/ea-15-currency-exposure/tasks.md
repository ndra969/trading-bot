# Implementation plan — 15 Eksposur mata uang

Status: Done (2026-10-05)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.16 di task 4.

- [x] 1. Aturan eksposur (fungsi murni) dan input
  - Red: TC-EXP-01..07 (suite baru `TestExposureRules`) terhadap stub `Risk/ExposureRules.mqh` → FAIL; TS-56 → FAIL.
  - Green:
    - `LegsOf`, `AddLegs`, `SameDirectionCount`, `ExposureAllowed`, `DirText`;
    - input `InpMaxSameDirectionPerCurrency` (Inputs, `InputValues`, validasi, `inputs_json` 44);
    - `gen_presets.py` + 12 preset; tabel input README; TC-SU-04c dan TestPresets menyesuaikan.
  - _Requirements: 1.1, 1.3, 1.4, 2.1, 2.3, 3.1_ · _Tests: TC-EXP-01..07, TS-56_
  - Hasil (2026-10-05): Red = TC-EXP-01..07 gagal compile, TS-56 FAIL. Green: `Risk/ExposureRules.mqh` (`LegsOf`, `AddLegs`, `SameDirectionCount`, `ExposureAllowed`, `DirText`); input `InpMaxSameDirectionPerCurrency` (2; 0-10) di grup Risiko, validasi, `inputs_json` (44); preset 12 simbol; README; TC-SU-04c dan TestPresets diperbarui. Unit 582/582, pytest lulus.

- [x] 2. Langkah eksposur di pre-trade check
  - Red: TC-RK-16..18 (posisi nyata dengan magic SDBot lain dan magic 0 di GBPUSDc/AUDUSDc) → FAIL.
  - Green: `CRiskManager.CollectSdbotLegs`, langkah `CURRENCY_EXPOSURE` setelah batas kategori, WARN untuk mata uang kosong.
  - Regresi: `-All` ALL PASS.
  - _Requirements: 1.1–1.4, 2.1, 2.2_ · _Tests: TC-RK-16..18, SC-00..15b_
  - Hasil (2026-10-05): Red = TC-RK-16 FAIL (2 posisi SDBot lain terbuka dan terhitung kategori 2/5, eksposur belum dicek). Green: `CRiskManager.CollectSdbotLegs` (semua posisi SDBot di akun, mata uang dari `SYMBOL_CURRENCY_BASE/PROFIT`), `CurrencyOf` (WARN throttled bila kosong), langkah `CURRENCY_EXPOSURE` setelah batas kategori dan sebelum margin. TC-RK-16..18 PASS (Risk 19/19). Unit 585/585; `-All` 24 run PASS.

- [x] 3. Skenario eksposur
  - Red: harness input `HarnessExposureSetup`, cabang `CheckScenario` SC-16 + `.ini`/`.set` → jalankan.
  - Green: perbaikan dari temuan skenario (bug dimulai dari test case).
  - _Requirements: 2.4, 4.3_ · _Tests: SC-16_
  - Hasil (2026-10-05): Harness input `HarnessExposureSetup` (bar pertama: BUY GBPUSDc magic ...02 + BUY AUDUSDc magic ...07, lot minimum, SL/TP 5000 point) + SC-16 + `CheckSc16`. Run pertama: penolakan `CURRENCY_EXPOSURE` (`USD short 2/2`, hanya BUY, 0 BUY ACCEPTED, 7 SELL ACCEPTED) benar, tetapi cek "posisi setup masih terbuka 0/2" salah karena `CheckScenario` jalan di `OnDeinit` setelah tester menutup semua posisi; cek diganti histori deal (2 deal IN, 0 tutup SL/TP sebelum akhir). SC-16 PASS.

- [x] 4. Versi 1.16 dan dokumen
  - Versi `1.16` (EA + harness); `docs/flows/order-execution.md` (langkah eksposur); CHANGELOG; README (input harness).
  - Regresi akhir: build 0/0, `-All`, pytest, `schema.py check`.
  - _Requirements: 4.4_ · _Tests: semua_
  - Hasil (2026-10-05): versi 1.16 (EA + harness); `docs/flows/order-execution.md` (langkah eksposur), `flows/README.md`; CHANGELOG; README (versi, input harness, daftar skenario). Regresi akhir: build 0/0, unit 585/585, `-All` 25 run PASS, pytest 85/85, `schema.py check` OK.

## Validasi manual (di luar tasks)

- [ ] MC-EXP-01: di akun cent dengan dua posisi SDBot searah USD terbuka, kandidat ketiga searah USD tercatat `CURRENCY_EXPOSURE` di `signals` dengan detail mata uang.
