# Implementation plan — 13 Sinyal dan entry

Status: Done (2026-10-03)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.12 di task 7 (Fase 3 selesai).

- [x] 1. Enum, tipe, konstanta, input
  - Red:
    - TS-50 (enum) dan TS-51 (preset) → FAIL;
    - TC-SG-23 (validasi input, suite baru `TestSignalRules`) terhadap input yang belum ada → compile/FAIL.
  - Green:
    - `enums.md` (`reject_stage` + `POSITION_OPEN`, `SL_TOO_FAR`; `score_component`; `tp_source`) + `schema.py build`;
    - struct `SdbSignalParams`, `SdbSignalFacts`, `SdbStops`, `SdbDecision`, `SignalRecord` di Types; konstanta;
    - 5 input baru di `Inputs.mqh` / `InputValues` / validasi / `inputs_json`;
    - `SdbAppConfig.signalsOn`;
    - `gen_presets.py` + 12 preset; tabel input README.
  - _Requirements: 6.2, 7.2_ · _Tests: TS-50, TS-51, TC-SG-23_
  - Hasil (2026-10-03): Red = TS-50, TS-51 FAIL; TC-SG-23 gagal compile. Green: `enums.md` (`reject_stage` + `POSITION_OPEN`, `SL_TOO_FAR`; enum `score_component`, `tp_source`) + `schema.py build` (data tetap v3); struct `SdbSignalParams`, `SdbSignalFacts`, `SdbStops`, `SdbDecision`, `SignalRecord`; konstanta `SDB_*` sinyal; 5 input (grup "Entry"), `InputValues`, `IrCheckSignals`, `inputs_json` (38 input); `SdbAppConfig.signalsOn` (EA utama true); 12 preset; tabel input README. TC-SU-04c dan TestPresets diperbarui untuk input baru. Unit 532/532, pytest 69/69.

- [x] 2. Aturan sinyal (fungsi murni)
  - Red: TC-SG-01..22 terhadap stub `Signals/SignalRules.mqh` → FAIL.
  - Green: `StaleLtfBar`, `ScorePct`, `BuildStops`, `EvaluateSignal`, `SignalIdOf`, `SignalContextJson`.
  - _Requirements: 1.3, 2.2–2.4, 3.1, 3.3, 4.1–4.6, 5.1, 6.1, 9.1_ · _Tests: TC-SG-01..22_
  - Hasil (2026-10-03): Red = SignalRules pass=1 fail=22 terhadap stub. Green: `Signals/SignalRules.mqh` (`StaleLtfBar`, `ScorePct`, `ZoneStatusText`, `BuildStops`, `EvaluateSignal`, `SignalIdOf`, `SignalContextJson`). Unit 554/554 (35 suite), build 0/0.

- [x] 3. Pencatatan sinyal
  - Red: TC-SG-24 (Logger, DB uji) dan kasus `OnSignal` di `TestEventSink` (tee meneruskan ke semua sink) → FAIL.
  - Green:
    - `OnSignal` di `ISdbEventSink`, `CNullSink`, `CTeeSink`, `CNotifier`, `CFakeSink`, `CScenarioRecorder`;
    - `CLogger`: antrean `SDB_Q_SIGNAL` dan `SDB_Q_SIGNAL_SCORE` (insert idempoten), accessor `RunKey()`.
  - _Requirements: 3.2, 6.1_ · _Tests: TC-SG-24_
  - Hasil (2026-10-03): Red = compile gagal (`OnSignal` belum ada). Green: `OnSignal` di `ISdbEventSink`, `CNullSink`, `CTeeSink`, `CNotifier` (abaikan), `CFakeSink`, `CScenarioRecorder`; `CLogger`: antrean `SDB_Q_SIGNAL` (insert `signals` dengan `id` eksplisit, `ON CONFLICT(id) DO NOTHING`) dan `SDB_Q_SIGNAL_SCORE` (3 komponen, prioritas rendah). TC-SG-24 dan TC-ES-13 PASS. Unit 556/556.

- [x] 4. `CSignalEngine` dan rangkaian App
  - Red: TC-SGX-01..03 (suite baru `TestSignalEngine`, tester) → FAIL.
  - Green:
    - `Signals/SignalEngine.mqh` (alur design §3.2, GV `SIGBAR`, hitungan harian);
    - `CZoneBook.LastAtr()`;
    - `CSdbApp`: member, init, `SetState` di `EnsureState`, `OnTick` setelah trigger, `LogDaySummary` di deinit;
    - `SDBot.mq5` `signalsOn = true`;
    - harness: input `HarnessPipeline`.
  - Regresi: `-All` ALL PASS. Skenario lama memakai entry terjadwal tanpa pipeline, jadi hasilnya harus tetap.
  - _Requirements: 1.1, 1.2, 1.4, 1.5, 2.1, 4.7, 5.1–5.5, 6.4, 7.1, 7.3_ · _Tests: TC-SGX-01..03, SC-00..13x_
  - Hasil (2026-10-03): Red = TC-SGX-01, TC-SGX-03 FAIL terhadap stub. Green: `Signals/SignalEngine.mqh` (`CSignalEngine`: penanda bar GV `<magic>_SIGBAR` sebelum penilaian, bar basi dan analisis belum siap dilewati, hitungan harian, fakta kandidat, `EvaluateSignal`, `CalcVolume` -> `PreTradeCheck` -> `OpenMarket` -> `MarkUsed`, `SignalRecord` ke sink); `CZoneBook.LastAtr()` (`Ready` juga butuh ATR > 0); `CSdbApp`: member, init setelah analisis, `SetState` di `EnsureState` (login + run_key), `OnTick` setelah trigger bila `signalsOn` dan risiko siap, ringkasan harian di deinit, accessor `Signals()`; EA utama `signalsOn = true` (dari `CurrentAppConfig` mode LIVE); harness input `HarnessPipeline`. Unit 559/559 (37 suite); `-All` 20 run PASS, build 0/0.

- [x] 5. Skenario sinyal
  - Red: cabang `CheckScenario` SC-14 / SC-14x dan pasangan `.ini`/`.set` → jalankan → FAIL sampai engine benar (atau PASS bila task 4 sudah benar; temuan dicatat).
  - Green: perbaikan dari temuan skenario (setiap bug dimulai dari test case).
  - Regresi: `-All` ALL PASS.
  - _Requirements: 5.1–5.4, 6.1, 9.2, EC-15_ · _Tests: SC-14, SC-14x_
  - Hasil (2026-10-03): SC-14 (EURUSDc 2026.04-09) dan SC-14x (XAUUSDc 2026.01-05) + `CheckSc14`: trade EA dengan `signal_id` ACCEPTED, 3 skor per kandidat, satu baris per bar, satu entry per zona, closure, tahap tolak beragam. Temuan: 4 kandidat EURUSD ditolak `RISK_PER_TRADE` karena `OrderCalcProfit` membulatkan rugi ke sen (balance 9973.92, SELL SL 166 pt, 30.04 lot: 49.8664 dibulatkan 49.87 > batas 49.8696). Bug Fase 1 di `CRiskManager.CalcVolume`: direproduksi TC-RK-14 (sapuan balance 9900-10075, 172/2050 ditolak), diperbaiki (lot turun per step sampai rugi sebenarnya <= batas, `SDB_LOT_FIT_STEPS`; hook uji `SetBalanceForTest`; detail tolak memuat rugi dan balance); SC-14 kini juga memeriksa tanpa `RISK_PER_TRADE`. `-All` 22 run PASS, unit 560/560.

- [x] 6. Backtest dasar dan query kalibrasi
  - Red: TS-52 (`baseline_report.py` di DB fixture) dan TS-53 (6 query) → FAIL.
  - Green:
    - `tools/queries/*.sql` (design §3.3);
    - `tools/baseline_report.py`;
    - `ea/tests/baseline/BL-<SIMBOL>.ini` × 12;
    - `run-ea-tests.ps1 -Baseline [simbol,...]`.
  - Verifikasi: `-Baseline` 12 simbol, laporan memenuhi kriteria 8.2. Bila gagal, temuan dibahas dengan Anda sebelum mengubah ambang.
  - _Requirements: 8.1–8.3_ · _Tests: TS-52, TS-53, backtest dasar_
  - Hasil (2026-10-03): Red = TS-52 (modul belum ada) dan TS-53 FAIL. Green: 6 query `tools/queries/` (`signal_rejects`, `score_vs_r`, `pattern_vs_r`, `zone_status_vs_r`, `tp_source_vs_r`, `candidates_per_day`; hanya sinyal ber-`context_json`); `tools/baseline_report.py`; seed contoh sinyal Fase 3 (fixture dibangun ulang, data tetap v3); 12 `ea/tests/baseline/BL-*.ini`; `run-ea-tests.ps1 -Baseline [-Symbols]` (EA utama + preset, baris log ERROR/CRITICAL dari jurnal tester, laporan di akhir). pytest 82/82. Backtest dasar pertama GAGAL: 16 log ERROR "market closed" (retcode 10018 diperlakukan PERMANENT saat jeda harian/penutupan Jumat) -> TC-EX-33 + TC-PS-05 (Red), kelas retcode `MARKET_CLOSED` -> langkah `DEFER`: modify/partial `SKIPPED` tanpa dihitung gagal, order `NOT_TRADABLE` tanpa alert, close all WARN. Backtest dasar ulang (2025.10.01-2026.10.01, OHLC M1, 25 menit): LOLOS, 351 trade (18-43 per simbol), 13.742 kandidat, tanpa log ERROR/CRITICAL, signal_id dan skor lengkap; expectancy +0.024R/trade (profit bukan syarat Fase 3). `-All` 22 run PASS, unit 562/562.

- [x] 7. Versi 1.12 dan dokumen (Fase 3 selesai)
  - Versi `1.12` (EA + harness), lalu dokumen:
    - `docs/flows/signals.md` baru, `tick.md`, `flows/README.md`;
    - `CHANGELOG.md`; README (status Fase 3 selesai);
    - `fase-3-overview.md` (status);
    - `ea/tests/manual-checklist.md` (MC-SG-01..02).
  - Regresi akhir: build 0/0, `-All`, pytest, `schema.py check`.
  - _Requirements: 9.3_ · _Tests: semua_
  - Hasil (2026-10-03): versi 1.12 (EA + harness; komentar dan deskripsi EA kini menyebut entry); `docs/flows/signals.md` baru, `tick.md`, `order-execution.md`, `flows/README.md`; CHANGELOG; README (status Fase 3 selesai, alat `-Baseline`, `HarnessPipeline`, input); `fase-3-overview.md` Done; `manual-checklist.md` MC-SG-01..02. Regresi akhir: build 0/0, unit 562/562 (37 suite), `-All` 22 run PASS, pytest 82/82, `schema.py check` OK.

## Validasi manual (di luar tasks)

- [ ] MC-SG-01: EA v1.12 di akun cent EURUSDc (risiko minimum). Periksa:
  - sinyal pertama tercatat dengan skor;
  - posisi punya SL/TP dari zona;
  - pesan Telegram masuk.
- [ ] MC-SG-02: restart EA di tengah bar M15 setelah kandidat tidak menghasilkan baris atau order ganda.
- [ ] Sinkron PC-15..19 ke dokumen induk Claude Docs (`/sdbot-docs-sync sync`) setelah spec selesai.
