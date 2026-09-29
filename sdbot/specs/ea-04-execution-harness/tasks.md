# Implementation plan — 04 Eksekusi, orkestrasi, dan harness

Status: Approved (2026-09-29)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `run-ea-tests.ps1 -Scenario SC-xx`. Setiap task: Red (tes + stub → FAIL) → Green (ALL PASS, compile 0/0) → catat baris "Hasil" → commit. Versi EA naik ke 1.03 di task 7.

- [x] 1. Kontrak: enum alasan tolak, tipe, konstanta, validasi magic harness
  - `shared/schema/enums.md` + `INVALID_STOPS`, `INVALID_VOLUME` → `schema.py build` (hanya `SchemaEnums.mqh` berubah) → `schema.py check`
  - `Core/Types.mqh`: `OrderRequest`, `OrderResult`, `SdbAppConfig`, `ENUM_SDB_RETCODE_CLASS`, `ENUM_SDB_NEXT_STEP`, `ENUM_SDB_EXEC`, `ENUM_SDB_APP_MODE`; `Core/Constants.mqh`: konstanta design §5
  - Red: TC-IR magic 2026091900 dengan/tanpa `allowHarnessMagic` di suite CoreUtils → FAIL
  - Green: `ValidateInputValues(v, allowHarnessMagic, errors)`; pemanggil lama (`SDBot.mq5`, suite) disesuaikan
  - _Requirements: 1.1, 1.5, 7.3_ · _Tests: TC-IR (magic harness), EC-19_
  - Hasil (2026-09-29): Red = 1 FAIL (TC-IR-01, flag belum dipakai). Green: unit 153/153, build 0/0. `schema.py build` hanya mengubah `SchemaEnums.mqh` (+ `SDB_REJECT_STAGE_INVALID_STOPS`/`_INVALID_VOLUME`), `check` OK, tanpa migrasi. Penyimpangan design: `SdbAppConfig` diletakkan di `Core/InputRules.mqh` (setelah `InputValues`, yang dipakainya), bukan `Types.mqh`; `InputRules.mqh` kini meng-include `Types.mqh`. `OrderResult` ditambah `detail` (teks alasan untuk log).

- [x] 2. Aturan eksekusi murni: validasi order dan volume
  - Red: suite `TestExecution` TC-EX-01..11b terhadap stub `ExecutionRules.mqh`
  - Green: `ValidateOrderSides`, `CheckStops`, `CheckVolume` (perbandingan volume toleran floating point)
  - _Requirements: 1.1–1.5_ · _Tests: TC-EX-01..11b_
  - Hasil (2026-09-29): Red = 12 FAIL (4 kasus tolak kebetulan cocok dengan stub `false`). Green: suite `Execution` 16/16, unit 169/169, build 0/0. Tambahan kasus: TC-EX-04b (sell valid), TC-EX-09b (JPY 30 point < spread 35), TC-EX-11c (limit 0 = tanpa batas, tepat di limit lolos). Jarak point dibulatkan (`PriceDistancePoints`) agar batas tepat 28 point tidak jatuh ke 27,999.

- [ ] 3. Aturan eksekusi murni: retcode, retry, filling, komentar, ID, slippage, modify, partial
  - Red: TC-EX-12..32 terhadap stub
  - Green: `PickFillingMode`, `ClassifyRetcode`, `NextStep`, `BuildOrderComment`, `ParseOrderComment`, `MakeRequestId`, `SlippagePoints`, `IsModifySlAllowed`, `IsPartialVolumeValid`
  - _Requirements: 2.1–2.4, 3.1, 4.2–4.5, 5.1–5.3_ · _Tests: TC-EX-12..32_

- [ ] 4. `CExecutor`
  - `Execution/Executor.mqh`: `Init`, `OpenMarket` (alur design §4.2: `CanTrade`, ID permintaan dari GV, normalisasi, validasi, `OrderCheck`, kirim, `NextStep`, cari posisi/deal berdasarkan ID, harga isi, `OrderCalcProfit`, `TradeRecord`, alert sekali), `ModifySl`, `ClosePartial`, `ClosePosition`, `CountOwnPositions`, `SendCount`
  - Red → Green lewat TC-APP-06 (ditulis di task 5) dan skenario task 6–7; di task ini: compile 0/0 dan suite unit tetap ALL PASS
  - _Requirements: 1.3, 1.6, 1.7, 2.1–2.5, 3.1–3.4, 4.1, 4.3, 4.4, 4.6, 4.7, 5.3_

- [ ] 5. `CTeeSink` dan `CSdbApp`
  - Red: suite `TestApp` TC-APP-01..07 terhadap stub `CSdbApp`
  - Green: `App/TeeSink.mqh`, `App/SdbApp.mqh` (urutan init §4.4, urutan event §4.5, snapshot akun 60 detik, `OnDeinit` aman dipanggil dua kali); `Inputs.mqh` + `CurrentAppConfig(mode, eaVersion)`
  - _Requirements: 1.7, 6.1–6.5, 7.3_ · _Tests: TC-APP-01..07_

- [ ] 6. Harness, perekam, dan skenario SC-06
  - `tests/Include/SDBotTests/ScenarioRecorder.mqh`, `Scenarios.mqh` (`CheckScenario`, ID tak dikenal → FAIL), `tests/Experts/SDBotTests/SDBotHarness.mq5` (cek tester, jadwal entry, restart, hasil lewat `TfBeginRun`/`TfEndRun`)
  - `tests/scenarios/SC-06_stops.ini/.set`
  - Red: SC-06 dijalankan dengan `HarnessScenario=SC-99` → FAIL "skenario tidak dikenal" (bukti 7.7); lalu SC-06 sebelum `CheckScenario` SC-06 diisi → FAIL
  - Green: `run-ea-tests.ps1 -Scenario SC-06` PASS
  - _Requirements: 1.4, 7.1, 7.2, 7.4, 7.6, 7.7_ · _Tests: SC-06_

- [ ] 7. `SDBot.mq5` v1.03, skenario SC-00 dan SC-08
  - `SDBot.mq5`: hanya meneruskan event ke `CSdbApp` (`CurrentAppConfig(SDB_APP_LIVE, "1.03")`)
  - `tests/scenarios/SC-00_smoke.ini/.set`, `SC-08_restart.ini/.set`; `CheckScenario` SC-00 dan SC-08 (termasuk pemeriksaan `sdbot_tester.sqlite` per ID sesi)
  - Verifikasi: build 0/0, `run-ea-tests.ps1 -All` (unit + SC-00, SC-06, SC-08) PASS; `sdbot/README.md` diperbarui (status v1.03, input harness, cara menjalankan skenario)
  - _Requirements: 2.1, 3.1, 5.1, 5.3, 6.1, 6.5–6.7, 7.5_ · _Tests: SC-00, SC-08_

## Validasi manual (di luar tasks)

- [ ] MC-EX-01: `SDBot.mq5` v1.03 di chart EURUSDc akun cent selama 1 jam → tidak ada order, sesi LIVE tercatat, `accounts.updated_at` diperbarui tiap menit
- [ ] MC-EX-02: harness dipasang di chart live terminal uji → gagal init dengan CRITICAL
