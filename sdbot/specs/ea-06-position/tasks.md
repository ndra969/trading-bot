# Implementation plan — 06 Manajemen posisi dan closure

Status: Done (2026-09-30), validasi manual MC-PS-01..04 tertunda (Fase 3)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `run-ea-tests.ps1 -Scenario SC-xx`. Setiap task: Red (tes + stub → FAIL) → Green (ALL PASS, compile 0/0) → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.05 di task 10.

- [x] 1. Kontrak: enum, tipe, konstanta, `alertOnFail` di `CExecutor`
  - `enums.md` + `alert_type` `BE_MOVED`, `PARTIAL_CLOSED`, `SL_MISSING` → `schema.py build` (hanya `SchemaEnums.mqh`) → `schema.py check`, pytest `sdbot/tools`
  - `Core/Types.mqh`: `PositionCacheEntry`, `ENUM_SDB_SL_SOURCE`, `ENUM_SDB_POS_ACTION`; `Core/Constants.mqh`: konstanta design §5
  - `CExecutor::ModifySl` / `ClosePartial` + parameter `alertOnFail = true`
  - Red: TC-PS-02 (suite `TestPosition`, hanya tester) terhadap stub → FAIL; Green: TC-PS-02 lolos, TC-APP-08d/e tetap lolos, unit ALL PASS
  - _Requirements: 2.3, 3.3, 5.3, 5.5_ · _Tests: TC-PS-02_
  - Hasil (2026-09-30): Red = compile error (`SetForceRetcodeForTest`, parameter `alertOnFail` belum ada). Green: suite Position 1/1, unit 276/276 (TC-APP-08d/e tetap lolos), build 0/0; `schema.py build` hanya `SchemaEnums.mqh`, `check` OK, pytest 36/36. Tambahan dari design: hook uji `CExecutor::SetForceRetcodeForTest` (modify/close tidak dikirim, retcode paksaan dipakai), karena penolakan broker tidak bisa dipicu di tester; `PositionCacheEntry` juga menyimpan `failAlerted` per aksi.

- [x] 2. `PositionMath` bagian R, BE, partial
  - Red: suite `TestPositionMath` TC-PM-01..16 terhadap stub `Position/PositionMath.mqh`
  - Green: `ProfitInR`, `IsBreakevenActive`, `CommissionPoints`, `BreakevenSl`, `ShouldBreakeven`, `ShouldPartial`, `PartialVolume`
  - _Requirements: 1.1, 1.3, 1.4, 2.1, 3.1, 3.2, 3.4_ · _Tests: TC-PM-01..16 (termasuk 08b, 08c)_
  - Hasil (2026-09-30): Red = 25 FAIL untuk seluruh suite (3 tes negatif kebetulan lolos terhadap stub `false`). Green task ini: TC-PM-01..16 (termasuk 08b XAU dan 08c komisi) lolos, build 0/0. `CommissionPoints` memakai nilai absolut (komisi MT5 negatif) dan dibulatkan ke atas; `PartialVolume` memakai `RoundLotDown` dari spec 05.

- [x] 3. `PositionMath` bagian trailing, pilihan SL, restore, retry
  - Red: TC-PM-17..26 terhadap stub
  - Green: `TrailingSl`, `IsSlImprovement`, `PickBestSl`, `RestoreSl`, `IsTrailingActive`, `RetryDue`
  - _Requirements: 4.1, 4.2, 5.2, 5.3, 5.5, 6.6_ · _Tests: TC-PM-17..26_
  - Hasil (2026-09-30): Green: TC-PM-17..26 lolos, PositionMath 28/28, unit 304/304, build 0/0. `IsSlImprovement` membulatkan selisih ke point (menghindari 4.9999 point) dan menganggap SL lama 0 selalu bisa diperbaiki; `RestoreSl` berlaku simetris untuk sell.

- [x] 4. `ClosureRules`
  - Red: suite `TestClosure` TC-CL-01..14 terhadap stub `Position/ClosureRules.mqh`
  - Green: `DealEntryText`, `DealTypeText`, `DealReasonText`, `MapCloseReason`, `ResultInR`, `MfeMaeInR`
  - _Requirements: 6.1, 6.3–6.5, 6.7_ · _Tests: TC-CL-01..14_
  - Hasil (2026-09-30): Red = 14 FAIL. Green: Closure 14/14, unit 318/318, build 0/0. Level SL di antara harga buka dan titik BE + toleransi = `BE_STOP`; `beSl` 0 (BE belum pernah dipasang) memakai harga buka.

- [x] 5. `CPositionCache`
  - Red: TC-PS-01 terhadap stub (hook uji mematikan pembacaan komentar)
  - Green: `Position/PositionCache.mqh`: kepemilikan dari deal pembuka, SL awal berurutan (komentar → `ORDER_SL` → `FindInitialSl`), volume awal, risiko awal, penghitung retry per aksi dengan reset saat SL/volume berubah, `Remove`
  - _Requirements: 1.1–1.3, 5.3, 7.4_ · _Tests: TC-PS-01_
  - Hasil (2026-09-30): Red = FAIL (stub). Green: TC-PS-01 lolos (SL awal komentar = ORDER_SL = 1.14725, volume awal 0.03, risiko 0.08, posisi asing bukan milik), unit 319/319, build 0/0. Tambahan field `PositionCacheEntry.commission` (pulang-pergi, positif) dan `symbol`. Deal pembuka yang belum tersinkron di history -> `Get` false, dicoba lagi berikutnya.

- [x] 6. `CClosureTracker` dan `CReconciler`
  - Red: TC-PS-03..04 terhadap stub
  - Green: `Position/ClosureTracker.mqh` (`OnTransaction`, `ProcessDeal`: filter saldo, kepemilikan, `DealRecord`, GV `LAST_DEAL`, closure dengan alasan, R, MFE/MAE M1, flag dari cache atau history), `Position/Reconciler.mqh` (`TradeRecord` `RECONCILED`, scan history sejak `LAST_DEAL` atau 30 hari)
  - _Requirements: 6.1–6.7, 7.1, 7.2, 7.4_ · _Tests: TC-PS-03..04_
  - Hasil (2026-09-30): Red = 2 FAIL (stub). Green: Position 4/4, unit 321/321, build 0/0. TC-PS-03 membuktikan premis EC-15 di tester: deal penutup close all membawa magic instance penutup (2026091901), pemilik tetap mencatat closure `EA_CLOSE`. Penyimpangan design: `CReconciler::Init` tidak menerima `CState` (GV `LAST_DEAL` dibaca lewat tracker); tiket history dikumpulkan dulu sebelum diproses karena `HistorySelectByPosition` mengganti seleksi history. Tambahan GV `<magic>_LAST_DEAL_TIME` untuk jendela scan.

- [x] 7. `CPositionManager` dan integrasi `CSdbApp`
  - Green: `Position/PositionManager.mqh` (alur design §4.4: cek akun, restore SL, partial, kandidat BE dan trailing, `PickBestSl`, retry 30 detik × 3 lalu `MODIFY_FAILED` + satu alert, event dan alert Info/High/Critical, event trailing sekali per bar LTF); `CSdbApp`: handle ATR LTF (gagal → `INIT_FAILED`, dilepas di `OnDeinit`), cache, manajer, tracker, reconciler di `EnsureState`, `OnTick`, `OnTradeTransaction`
  - Red → Green lewat skenario task 8; di task ini: compile 0/0, unit ALL PASS, SC-00..08 tetap PASS
  - _Requirements: 2.1–2.3, 3.1–3.4, 4.1–4.5, 5.1–5.6, 7.3_
  - Hasil (2026-09-30): Green (tanpa Red sendiri, sesuai rencana: perilaku dibuktikan skenario task 8–9): build 0/0; `run-ea-tests.ps1 -All` exit 0, yaitu unit 321/321 dan SC-00, 02, 03, 03r, 05, 06, 07, 08 tetap PASS dengan manajemen posisi aktif. Compile pertama gagal karena method `RestoreSl` menutupi fungsi murni bernama sama (warning 89); method diganti `TryRestoreSl`. Tambahan: struct `PmMarket` (harga, spread, stops, ATR bar tutup dibaca sekali per tick); komisi per volume sekarang diskalakan dari komisi volume awal; trailing hanya bila BE sudah aktif di posisi (PRD). Di `CSdbApp`: handle ATR dibuat di init (gagal -> `INIT_FAILED`) dan dilepas di `OnDeinit`, rekonsiliasi di `EnsureState`, tick/transaksi diteruskan hanya setelah status siap.

- [x] 8. Skenario BE → partial → trailing
  - Perekam: `PositionEvent` dan `ClosureRecord`/`DealRecord`; pemeriksa membaca history tester di `OnDeinit`
  - `SC-01_be_partial_trail`, `SC-01b_min_lot` `.ini/.set` + `CheckScenario`
  - Red: FAIL "tidak dikenal" → Green: PASS (rentang tanggal diperpanjang bila urutan BE → PARTIAL → TRAILING belum muncul; dicatat di Hasil)
  - _Requirements: 2–6_ · _Tests: SC-01, SC-01b_
  - Hasil (2026-09-30): Red: kedua skenario FAIL "tidak dikenal". Lalu SC-01 FAIL di dua pemeriksaan, keduanya ternyata salah di sisi harapan, bukan EA: (1) urutan kaku BE -> PARTIAL -> TRAILING di design tidak sesuai PRD (ketiganya dievaluasi terpisah tiap tick); data: posisi 38/41 BE -> TRAILING -> PARTIAL, posisi 16/29 PARTIAL -> BE -> TRAILING di tick yang sama (EC-02). Pemeriksa kini: ketiga event ada dan TRAILING tidak mendahului BE (design §7 diperbarui). (2) Posisi terakhir ditutup paksa tester di akhir run (alasan CLIENT 23:59:58, setelah tick terakhir) tanpa `OnTradeTransaction`; posisi seperti itu dikecualikan. Green: SC-01 7/7 (4 posisi dengan BE, PARTIAL, TRAILING; 31 closure lengkap; 18 BE_STOP/TRAIL_STOP; 67 deal = history), SC-01b 4/4 (PARTIAL_SKIPPED sekali di 4 posisi, 0 PARTIAL, 18 BE). Perekam menyimpan event posisi, deal, dan closure lengkap.

- [x] 9. Skenario restart
  - Harness: `HarnessRestartAfterPartial` (restart N bar setelah partial pertama) dan jeda tanpa app selama N bar untuk SC-04b
  - `SC-04_restart`, `SC-04b_close_at_restart` `.ini/.set` + `CheckScenario`
  - Red: FAIL "tidak dikenal" → Green: PASS
  - _Requirements: 7.1–7.4_ · _Tests: SC-04, SC-04b_
  - Hasil (2026-09-30): Red: kedua skenario FAIL "tidak dikenal". SC-04b langsung PASS 4/4 (app dilepas 01 Sep 00:45–10:45, 1 posisi ditutup broker saat itu: 1 closure, 2 deal, 1 baris `closures`). SC-04 dua kali gagal karena harness, bukan EA: restart 2 bar sesudah partial terjadi setelah posisinya tertutup (tidak menguji apa pun), lalu tidak ada restart sama sekali. Perbaikan harness: restart hanya bila posisi yang terakhir partial masih terbuka, di bar pertama sesudah partial terdeteksi; pemeriksa memastikan posisi terbuka saat restart. Green: SC-04 5/5 (pos 41: tanpa BE/PARTIAL kedua, 1 `RECONCILED` ke sink, baris `trades` tetap 1, closure TRAIL_STOP). Input harness baru: `HarnessRestartAfterPartial` (1 = bar pertama sesudah partial), `HarnessDetachBars`.

- [x] 10. `SDBot.mq5` v1.05 dan penutupan spec
  - `#property version` dan `SDB_EA_VERSION` 1.05; harness 1.05
  - `sdbot/README.md`: status v1.05, GV `LAST_DEAL`, konstanta posisi, input harness baru, skenario baru
  - Verifikasi: build 0/0, `run-ea-tests.ps1 -All` (unit + semua skenario) PASS, pytest `sdbot/tools` PASS, `schema.py check` OK
  - _Requirements: semua (regresi)_ · _Tests: -All_
  - Hasil (2026-09-30): `SDBot.mq5` dan harness v1.05; `sdbot/README.md` diperbarui (status, GV `LAST_DEAL`, konstanta posisi, input harness, 12 skenario). Verifikasi: build 0/0 (4 target), `run-ea-tests.ps1 -All` exit 0 (unit 321/321; SC-00 8/8, SC-01 7/7, SC-01b 4/4, SC-02 5/5, SC-03 7/7, SC-03r 5/5, SC-04 5/5, SC-04b 4/4, SC-05 4/4, SC-06 5/5, SC-07 7/7, SC-08 8/8), pytest `sdbot/tools` 36/36, `schema.py check` OK. Tinjauan aturan: Position hanya memanggil `CExecutor` (tidak `CTrade`); loop posisi memfilter magic + simbol; SL hanya membaik (`PickBestSl` + `IsModifySlAllowed`); handle ATR dibuat di init, dicek, dilepas di deinit.

## Validasi manual (di luar tasks)

- [ ] MC-PS-01..04 (Fase 3, saat ada entry di akun cent): tutup manual dari HP → `MANUAL`; hapus SL → dipasang kembali + alert High; `ORDER_SL` order pembuka Exness tidak 0; posisi kena TP saat MT5 mati → closure `TP` saat init
