# Implementation plan — 05 Risk management

Status: Done (2026-09-30), validasi manual MC-RK-01..02 tertunda
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `run-ea-tests.ps1 -Scenario SC-xx`. Setiap task: Red (tes + stub → FAIL) → Green (ALL PASS, compile 0/0) → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.04 di task 10.

- [x] 1. Kontrak: enum, tipe, konstanta, konfigurasi reset
  - `shared/schema/enums.md` + `RISK_PER_TRADE` → `schema.py build` (hanya `SchemaEnums.mqh` berubah) → `schema.py check`, pytest `sdbot/tools`
  - `Core/Types.mqh`: `ENUM_SDB_DD_LEVEL`, `ENUM_SDB_LOT_FLAG`, `CloseAllResult`; `Core/Constants.mqh`: konstanta design §5
  - `SdbAppConfig.resetEmergencyStop` + `CurrentAppConfig` mengisinya dari `InpResetEmergencyStop`
  - Red: TC-IR tambahan di suite CoreUtils: `CurrentAppConfig` membawa `resetEmergencyStop` → FAIL; Green: unit ALL PASS, build 0/0
  - _Requirements: 2.2, 5.5_ · _Tests: TC-IR (reset config)_
  - Hasil (2026-09-30): Red = compile error (`resetEmergencyStop` belum ada). Green: unit 217/217, build 0/0, `schema.py build` hanya mengubah `SchemaEnums.mqh`, `check` OK. TC-IR-02 ditempatkan di suite App (suite yang meng-include `Inputs.mqh`), bukan CoreUtils. Tambahan konstanta `SDB_RISK_EPS` (toleransi perbandingan persen).

- [x] 1b. Kontrak batas posisi per kategori (PC-10, ditambahkan setelah task 1 selesai)
  - `enums.md` + `CLASS_POSITION_LIMIT` → `schema.py build`/`check`; `ENUM_SDB_ASSET_CLASS`; konstanta design §5
  - Input `InpMaxPosForexMajor`/`ForexCross`/`Commodity`/`Crypto` di `Inputs.mqh`, `InputValues`, `DefaultInputValues`, `CurrentInputs`, `CurrentInputsJson`; batas 1–20 di `ValidateInputValues`; tabel input `sdbot/README.md`
  - Red: TC-CU tambahan (default 5/3/1/1 lolos, 0 dan 21 ditolak dengan nama input) → FAIL; Green: unit ALL PASS
  - _Requirements: 2.2, 2.8_ · _Tests: TC-CU (batas kategori)_
  - Hasil (2026-09-30): Red = compile error (field `maxPos*` belum ada). Green: suite CoreUtils 32/32, unit 231/231, build 0/0, `schema.py build`/`check` OK (hanya `SchemaEnums.mqh`). TC-SU-04c (jumlah input di JSON sesi) diubah 17 → 21. Tabel input `sdbot/README.md` diperbarui.

- [x] 2. `RiskMath` bagian lot dan risiko
  - Red: suite `TestRiskMath` TC-RM-01..13 terhadap stub `Risk/RiskMath.mqh`
  - Green: `RoundLotDown`, `CalcLotSize`, `EffectiveRiskPct`, `RiskPctOf`, `PositionRiskMoney`
  - _Requirements: 1.1–1.6, 2.3–2.5_ · _Tests: TC-RM-01..13_
  - Hasil (2026-09-30): Red = 13 FAIL (stub mengembalikan -1). Green: RiskMath 13/13, unit 230/230, build 0/0. Tambahan: `StepDigits` untuk menormalkan hasil kali step; `CalcLotSize` juga INVALID untuk balance/risiko/step ≤ 0.

- [x] 3. `RiskMath` bagian drawdown, hari, reset, saldo, magic, sesi, close all
  - Red: TC-RM-14..30 terhadap stub
  - Green: `DrawdownPct`, `DailyLossPct`, `DrawdownLevel`, `EffectiveMarginLevel`, `IsNewServerDay`, `ServerDayStart`, `ResetRequested`, `BalanceOpType`, `IsSdbotMagic`, `InTradeSession`, `CloseAllDue`, `CloseAllAlertDue`, `AssetClassOf`, `ClassPositionLimit`
  - _Requirements: 2.6, 2.8, 3.3–3.6, 4.1, 4.3, 4.4, 5.1–5.3, 5.5–5.8, 7.1_ · _Tests: TC-RM-14..32_
  - Hasil (2026-09-30): Red = 19 FAIL. Green: RiskMath 32/32 (TC-RM-01..32), unit 250/250, build 0/0. `AssetClassOf` juga mengembalikan OTHER bila quote adalah logam/crypto atau kode bukan 3 huruf; helper `CsvHas`.

- [x] 4. `CRiskState`
  - Red: suite `TestRiskState` TC-RS-01..09 (prefix `SDBTEST`, dua objek = dua instance) terhadap stub
  - Green: `Risk/RiskState.mqh`: nilai awal aman spec 02 §4.5 + GV §5, getter tanpa cache, CAS lewat `GlobalVariableSetOnCondition`, CAS retry untuk puncak/awal hari, `RESET_SEEN` per magic
  - _Requirements: 3.2, 3.9, 4.3, 5.5, 5.6, 6.1–6.3, 7.1, 7.3, 7.5_ · _Tests: TC-RS-01..09_
  - Hasil (2026-09-30): Red = 9 FAIL. Green: RiskState 9/9, unit 259/259, build 0/0. Tambahan dari design: `BalanceBaselineNeeded` (GV `LAST_BAL_DEAL` hilang, bukan hanya `PEAK_EQUITY`) dan `SetBalanceBaseline`; `Init` menerima equity, balance, dan waktu server sebagai parameter agar bisa diuji tanpa akun. Nama GV di konstanta `SDB_GV_*` di `RiskState.mqh`.

- [x] 5. `CExecutor` tambahan dan `CRiskManager`
  - Red: suite `TestRisk` (hanya di tester) TC-RK-01..06, 08, 10, 11 terhadap stub
  - Green: `CExecutor::MarginLevelAfter`, `CExecutor::CloseAllSdbot`; `Risk/RiskManager.mqh` (`CalcVolume`, `PreTradeCheck` urutan 2.1, `OpenRiskMoney` atas semua posisi SDBot, `CountSdbotPositionsInClass`)
  - _Requirements: 1.1–1.6, 2.1–2.8, 5.8_ · _Tests: TC-RK-01..06, 08, 10, 11_
  - Hasil (2026-09-30): Red = 10 FAIL (stub). Green: suite Risk 10/10 (TC-RK-11 menguji XAUUSDc dan BTCUSDc sungguhan di tester: XAU 49.96 lot = 0.500%, BTC dibatasi VOLUME_MAX 200 lot = 0.2%), unit 269/269, build 0/0. Tambahan: `CExecutor::CloseAllowedNow` (mode trading + sesi trade simbol) dan `CloseAnyPosition` private tanpa alert per posisi; hook uji `CRiskManager::SetMarginLevelForTest` (margin < 200% tidak bisa dipicu di tester tanpa lebih dulu melanggar batas risiko); margin level asli order normal 3494%.

- [x] 6. `CRiskMonitor` dan integrasi `CSdbApp`
  - Red: TC-RK-07 dan TC-RK-09 terhadap stub
  - Green: `Risk/RiskMonitor.mqh` (`OnStateReady`: baseline, `STATE_RESET`, reset input, saldo tertunda; `Run`: urutan design §4.4); `CSdbApp`: init langkah 6, `EnsureState` → `OnStateReady`, `OnTimer` akun → state → monitor → snapshot (puncak dari GV, snapshot langsung saat state siap) → touch → flush; akses `RiskManager()`, `RiskState()`
  - Suite App dan Logger tetap ALL PASS
  - _Requirements: 3.1–3.9, 4.1–4.4, 5.1–5.7, 6.2, 7.1–7.5_ · _Tests: TC-RK-07, TC-RK-09_
  - Hasil (2026-09-30): Red = 4 FAIL (TC-RK-07, 09, 12, 13). Green: suite Risk 13/13, App 17/17, unit 273/273, build 0/0. Tambahan di luar katalog: TC-RK-12 (drawdown ≥ batas lewat GV puncak buatan → STOPPED, `DD_STOP` sekali, posisi SDBot ditutup) dan TC-RK-13 (rugi harian → pause, `DAILY_LOSS` sekali), keduanya memanggil `Run()` dua kali untuk membuktikan alert tidak ganda. `STATE_RESET` hanya bila akun punya deal dengan magic SDBot (bukan sekadar deposit), agar pemasangan pertama tidak memicu alert. `CFakeSink::CountAlertType`. Di `CSdbApp`, `EnsureState` dipindah setelah init modul risiko.

- [x] 7. Harness lewat jalur risiko, regresi, dan SC-05
  - Harness: `TryEntry` = lot tetap atau `CalcVolume` → `PreTradeCheck` → `OpenMarket`, penolakan risiko dicatat; perekam menyimpan waktu percobaan
  - `SC-00`/`SC-08` `.set`: `HarnessFixedLot=0`; `SC-06` tetap 0.01
  - `tests/scenarios/SC-05_lot_min.ini/.set` + `CheckScenario` SC-05
  - Red: SC-05 sebelum pemeriksanya diisi → FAIL "tidak dikenal"; Green: SC-05, SC-00, SC-06, SC-08 PASS
  - _Requirements: 1.3, 2.7, 8.1, 8.2, 8.4_ · _Tests: SC-05, SC-00, SC-06, SC-08_
  - Hasil (2026-09-30): Red: SC-05 FAIL "tidak dikenal"; regresi menemukan dua hal: (1) SC-06 ditolak `MARGIN_LOW` alih-alih `SL_TOO_CLOSE`, karena `MarginLevelAfter` mengirim SL/TP ke `OrderCheck` dan stop yang terlalu dekat membuat margin level 0. Diperbaiki (cek margin tanpa SL/TP) + TC-RK-06b sebagai regresi unit. (2) SC-00 jeda snapshot 0 detik saat init: snapshot kedua dengan puncak equity memang disengaja (design §4.6), sehingga pemeriksa mengabaikan pasangan snapshot saat init. Green: unit 274/274, SC-00 8/8, SC-05 4/4, SC-06 5/5, SC-08 8/8, build 0/0. SC-05 memakai risiko 0.001% dengan SL 2000 point (0.01% masih menghasilkan 0.05 lot). Default `HarnessFixedLot` sekarang 0 (= `CalcVolume`).

- [x] 8. Skenario rugi harian dan drawdown
  - Perekam: sampel per timer (waktu, STOPPED, jumlah posisi SDBot); pemeriksa membaca GV tester di `OnDeinit`
  - `SC-02_daily_loss`, `SC-03_dd`, `SC-03r_dd_restart` `.ini/.set` + `CheckScenario` masing-masing
  - Red: ketiganya FAIL "tidak dikenal" → Green: PASS (rentang tanggal diperpanjang bila kondisi tidak tercapai; dicatat di Hasil)
  - _Requirements: 1.5, 3.4, 3.6, 4.1–4.4, 5.1, 5.4, 5.7_ · _Tests: SC-02, SC-03, SC-03r_
  - Hasil (2026-09-30): Red: ketiga skenario FAIL "tidak dikenal". Lalu SC-03 menemukan bug: flag lot x 0.5 berkedip ratusan kali karena ambang pulih tetap 8% padahal `InpDDReducePct` 1% (histeresis hilang bila batas REDUCE < 8). Perbaikan: `DdRecoverPct = min(8, InpDDReducePct x 0.8)` (default PRD tetap 8%) + TC-RM-19b (Red → Green); design §9.10. Pemeriksa SC-03 menghitung risiko yang diharapkan per trade dari alert REDUCE/RECOVERED terakhir, dan memeriksa invariant histeresis dari angka drawdown di pesan alert. Green: SC-02 5/5 (8 hari DAILY_LOSS, 93 tolak DAILY_PAUSE semuanya di hari yang sama), SC-03 7/7 (STOPPED → posisi habis dalam 0 detik simulasi), SC-03r 5/5 (155 percobaan sesudah restart ditolak STOPPED), unit 275/275. Rentang tanggal diperpanjang jadi 2026.09.14–26. Harness: input `HarnessRestartBarsAfterStop` (bar restart tidak bisa ditebak dari tanggal), sampel STOPPED per timer di perekam.

- [x] 9. Penarikan saldo
  - Harness: `HarnessWithdrawAtBar`, `HarnessWithdrawPct` (`TesterWithdrawal` saat tidak ada posisi sendiri; catat puncak dan level DD sebelum); perekam menyimpan `BalanceOpRecord`
  - `SC-07_withdraw.ini/.set` + `CheckScenario` SC-07 (termasuk baris `balance_ops` untuk `run_key` ini)
  - Red: FAIL "tidak dikenal" → Green: PASS. Bila `TesterWithdrawal` tidak menghasilkan deal BALANCE: jalur alternatif design §9.8, dicatat di Hasil
  - _Requirements: 7.1–7.4, 8.3_ · _Tests: SC-07_
  - Hasil (2026-09-30): Red = FAIL "tidak dikenal". Green: SC-07 7/7: penarikan 1989.70 (20%), tepat 1 operasi saldo BALANCE (deposit awal tester tidak dihitung, EC-17), puncak 10047.00 → 8057.30, level DD tetap, 1 alert `BALANCE_OP`, 1 baris `balance_ops` untuk `run_key` run ini. Asumsi design §9.8 terbukti (`TesterWithdrawal` = deal `DEAL_TYPE_BALANCE`), jalur alternatif tidak dipakai. Harness: `HarnessWithdrawAtBar`, `HarnessWithdrawPct`; perekam menyimpan `BalanceOpRecord` dan sampel puncak/level sebelum dan sesudah.

- [x] 10. `SDBot.mq5` v1.04 dan penutupan spec
  - `#property version` dan `SDB_EA_VERSION` 1.04; harness `1.04`
  - `sdbot/README.md`: status v1.04, daftar 12 simbol dan preset per simbol (PC-10), GV risiko baru, konstanta risiko, input harness baru, skenario baru
  - Verifikasi: build 0/0, `run-ea-tests.ps1 -All` (unit + SC-00, 02, 03, 03r, 05, 06, 07, 08) PASS, pytest `sdbot/tools` PASS, `schema.py check` OK
  - _Requirements: semua (regresi)_ · _Tests: -All_
  - Hasil (2026-09-30): `SDBot.mq5` dan harness v1.04; `sdbot/README.md` diperbarui (status, GV risiko, konstanta risiko, input harness, daftar skenario; 12 simbol dan batas per kategori sudah masuk di task 1b). Verifikasi: build 0/0 (4 target), `run-ea-tests.ps1 -All` exit 0 (unit 275/275; SC-00 8/8, SC-02 5/5, SC-03 7/7, SC-03r 5/5, SC-05 4/4, SC-06 5/5, SC-07 7/7, SC-08 8/8), pytest `sdbot/tools` 36/36, `schema.py check` OK (data versi 2). Tinjauan aturan: Risk tidak memanggil `CTrade` (close all dan cek margin lewat `CExecutor`); `CloseAllSdbot` satu-satunya operasi lintas magic/simbol; input baru hanya di `Inputs.mqh`.

## Validasi manual (di luar tasks)

- [ ] MC-RK-01: dua chart (EURUSDc, GBPUSDc) di akun cent, GV `SDB_<login>_STOPPED` = 1 lewat F3 → kedua instance mencatat STOPPED
- [ ] MC-RK-02: STOPPED aktif, `InpResetEmergencyStop` true lalu init ulang tanpa dikembalikan → reset sekali, init berikutnya WARN
