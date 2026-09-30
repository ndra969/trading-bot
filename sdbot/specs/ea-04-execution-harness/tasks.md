# Implementation plan — 04 Eksekusi, orkestrasi, dan harness

Status: Done (2026-09-30), validasi manual MC-EX-01..02 tertunda
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

- [x] 3. Aturan eksekusi murni: retcode, retry, filling, komentar, ID, slippage, modify, partial
  - Red: TC-EX-12..32 terhadap stub
  - Green: `PickFillingMode`, `ClassifyRetcode`, `NextStep`, `BuildOrderComment`, `ParseOrderComment`, `MakeRequestId`, `SlippagePoints`, `IsModifySlAllowed`, `IsPartialVolumeValid`
  - _Requirements: 2.1–2.4, 3.1, 4.2–4.5, 5.1–5.3_ · _Tests: TC-EX-12..32_
  - Hasil (2026-09-29): Red = 26 FAIL. Green: suite `Execution` 45/45, unit 198/198, build 0/0. TC-EX-15 memeriksa 22 retcode sekaligus. Kasus tambahan: TC-EX-19 juga menolak ID huruf besar, SL 0, dua titik, dan prefix lain; TC-EX-20c (ID buatan selalu lolos parser); TC-EX-24d/e (stops level dan freeze level untuk modify); TC-EX-27c (volume 0/negatif). Design §4.1 diperbaiki: `NextStep` memakai `attempt ≤ SDB_MAX_RETRY` (1 kirim + 3 ulangan), sesuai TC-EX-30. `IsPartialVolumeValid` juga menolak volume tutup < lot minimum.

- [x] 4. `CExecutor`
  - `Execution/Executor.mqh`: `Init`, `OpenMarket` (alur design §4.2: `CanTrade`, ID permintaan dari GV, normalisasi, validasi, `OrderCheck`, kirim, `NextStep`, cari posisi/deal berdasarkan ID, harga isi, `OrderCalcProfit`, `TradeRecord`, alert sekali), `ModifySl`, `ClosePartial`, `ClosePosition`, `CountOwnPositions`, `SendCount`
  - Red → Green lewat TC-APP-06 (ditulis di task 5) dan skenario task 6–7; di task ini: compile 0/0 dan suite unit tetap ALL PASS
  - _Requirements: 1.3, 1.6, 1.7, 2.1–2.5, 3.1–3.4, 4.1, 4.3, 4.4, 4.6, 4.7, 5.3_
  - Hasil (2026-09-29): `Execution/Executor.mqh` dikompilasi lewat suite `TestExecution` (belum ada pemakai lain): build 0/0, unit 198/198. Perilaku broker baru diuji di task 5–7. Tambahan: `CState::IsReady()` agar penghitung ID tidak ditulis ke GV sebelum state di-init (cadangan: penghitung memori + ERROR throttled). Modify/close yang diulang memeriksa dulu apakah kiriman sebelumnya ternyata sudah diterapkan (SL sudah sama, volume sudah berkurang, posisi sudah tertutup) → `OK`. Log `CTrade` dimatikan (`LOG_LEVEL_NO`) agar semua log lewat `Utils.mqh`.

- [x] 5. `CTeeSink` dan `CSdbApp`
  - Red: suite `TestApp` TC-APP-01..07 terhadap stub `CSdbApp`
  - Green: `App/TeeSink.mqh`, `App/SdbApp.mqh` (urutan init §4.4, urutan event §4.5, snapshot akun 60 detik, `OnDeinit` aman dipanggil dua kali); `Inputs.mqh` + `CurrentAppConfig(mode, eaVersion)`
  - _Requirements: 1.7, 6.1–6.5, 7.3_ · _Tests: TC-APP-01..07_
  - Hasil (2026-09-30): suite `App` 14/14, unit 212/212, build 0/0 (3 target). Suite App hanya jalan di Strategy Tester (runner `RunUnitTestsEA`); di script chart live suite dilewati dengan INFO karena memasang timer dan mengirim order. Tambahan di luar katalog: TC-APP-07b (snapshot ke observer dan DB) dan TC-APP-08a..f, jalur broker `CExecutor` sungguhan di tester (buy lot minimum terisi dengan risiko > 0, komentar ter-parse, baris `trades`, modify lebih buruk `SKIPPED` / lebih baik `OK` / tiket asing `GONE`, partial seluruh volume `SKIPPED`, close `OK` lalu `GONE`, SL 3 point `SL_TOO_CLOSE` tanpa kiriman). Penyimpangan design: `SdbDbTargetForRuntime()` dipindah dari `Storage/Logger.mqh` ke `Core/Utils.mqh`, karena `CurrentAppConfig` di Core tidak boleh meng-include Storage. Mode `UNITTEST` memakai prefix GV `SDBTEST` dan tidak memanggil `ExpertRemove`.

- [x] 6. Harness, perekam, dan skenario SC-06
  - `tests/Include/SDBotTests/ScenarioRecorder.mqh`, `Scenarios.mqh` (`CheckScenario`, ID tak dikenal → FAIL), `tests/Experts/SDBotTests/SDBotHarness.mq5` (cek tester, jadwal entry, restart, hasil lewat `TfBeginRun`/`TfEndRun`)
  - `tests/scenarios/SC-06_stops.ini/.set`
  - Red: SC-06 dijalankan dengan `HarnessScenario=SC-99` → FAIL "skenario tidak dikenal" (bukti 7.7); lalu SC-06 sebelum `CheckScenario` SC-06 diisi → FAIL
  - Green: `run-ea-tests.ps1 -Scenario SC-06` PASS
  - _Requirements: 1.4, 7.1, 7.2, 7.4, 7.6, 7.7_ · _Tests: SC-06_
  - Hasil (2026-09-30): Red digabung jadi satu run: SC-06 dijalankan saat `CheckScenario` hanya punya cabang "tidak dikenal" → `FAIL SC-06 skenario tidak dikenal harness` (jalur kode yang sama dengan SC-99, jadi sekaligus bukti 7.7; runner menolak `-Scenario SC-99` karena tidak ada file `.ini`-nya). Green: SC-06 5/5 (46 percobaan entry, semuanya `SL_TOO_CLOSE`, 0 `OrderSend`, 1 sesi TESTER, 0 baris `trades` untuk sesi itu), build 0/0 (4 target). Skenario memakai tanggal tetap 2026.09.21–26 dan model 1 (OHLC M1) agar hasilnya bisa diulang. Tambahan: pemeriksa mewajibkan ≥ 3 percobaan agar skenario tanpa entry tidak lulus kosong. `SendCount` dijumlahkan perekam dari semua `CExecutor` (bertahan melewati restart). Versi harness `1.03`.

- [x] 7. `SDBot.mq5` v1.03, skenario SC-00 dan SC-08
  - `SDBot.mq5`: hanya meneruskan event ke `CSdbApp` (`CurrentAppConfig(SDB_APP_LIVE, "1.03")`)
  - `tests/scenarios/SC-00_smoke.ini/.set`, `SC-08_restart.ini/.set`; `CheckScenario` SC-00 dan SC-08 (termasuk pemeriksaan `sdbot_tester.sqlite` per ID sesi)
  - Verifikasi: build 0/0, `run-ea-tests.ps1 -All` (unit + SC-00, SC-06, SC-08) PASS; `sdbot/README.md` diperbarui (status v1.03, input harness, cara menjalankan skenario)
  - _Requirements: 2.1, 3.1, 5.1, 5.3, 6.1, 6.5–6.7, 7.5_ · _Tests: SC-00, SC-08_
  - Hasil (2026-09-30): Red: SC-00 dan SC-08 FAIL "skenario tidak dikenal", lalu dengan pemeriksa terisi SC-00 FAIL `dbtrades` (db=0, ok=12) dan SC-08 FAIL `dbtrades` (db=0, ok=6). Penyebabnya: position ID tester berulang di setiap run, dan `ON CONFLICT (login, position_id) DO NOTHING` membuang baris run kedua dan seterusnya. Diputuskan user: skema v2 `run_key` (design §9.7, PC-08): migrasi `0002_run_key`, `SessionInfo.runKey`, `CLogger` (SQL, bind `?80`, `FindInitialSl`), `CSdbApp` (GV `SDB_<login>_RUN_KEY`); pytest TS-20..24 Red 5 FAIL → Green, TC-DB-23..25 Red (semua tulis Logger gagal) → Green. Temuan lain: jeda snapshot 59/31 detik ternyata artefak pengukuran (`AccountSnapshot.time` = waktu tick terakhir), sehingga perekam kini memakai jam timer. Bug `OnInit` ulang pada objek global yang sama (ganti timeframe) dibuktikan TC-APP-04b (Red FAIL → Green). Akhir: build 0/0 (4 target), `run-ea-tests.ps1 -All` exit 0: unit 216/216, SC-00 8/8, SC-06 5/5, SC-08 8/8; pytest `sdbot/tools` 36/36, `schema.py check` OK (data versi 2). DB tester yang sudah ada termigrasi ke v2 dan baris lamanya diisi `run_key`. `CHANGELOG.md` dan `docs/flows/` belum ada di repo; tidak dibuat di spec ini.

## Validasi manual (di luar tasks)

- [ ] MC-EX-01: `SDBot.mq5` v1.03 di chart EURUSDc akun cent selama 1 jam → tidak ada order, sesi LIVE tercatat, `accounts.updated_at` diperbarui tiap menit
- [ ] MC-EX-02: harness dipasang di chart live terminal uji → gagal init dengan CRITICAL
