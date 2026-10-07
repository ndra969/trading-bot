# Implementation plan — 21 Skor RSI divergence (mode bayangan)

Status: Done (2026-10-07)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.23 di task 4. Backtest dijalankan dengan satu agen tester di background.

- [x] 1. Aturan RSI divergence (fungsi murni) dan input
  - Red: TC-RSI-01..10 (suite baru `TestRsiRules`) terhadap stub `Strategies/RsiRules.mqh` → FAIL.
  - Green:
    - `RsiLastTwoSwings`, `RsiEvaluate`; `SdbRsiResult`; konstanta `SDB_RSI_*`, `SDB_SCORE_MAX_RSI`;
    - input `InpScoreRsiMode` (SHADOW), validasi, `inputs_json` (52), preset, README; TC-SU-04c, TestPresets, TS presets.
  - _Requirements: 1.2, 2.1–2.4, 4.1_ · _Tests: TC-RSI-01..10_
  - Hasil (2026-10-07): Red = TC-RSI-01..10 gagal compile (`SdbRsiResult`, input belum ada). Green: `Strategies/RsiRules.mqh` (`RsiLastTwoSwings`, `RsiEvaluate`: lower low / higher high ketat, selisih RSI ≥ 2, swing kedua ≤ 20 bar, telemetri diisi juga saat skor 0); `SdbRsiResult` di `Core/Types.mqh`; konstanta `SDB_RSI_*`, `SDB_SCORE_MAX_RSI`; input `InpScoreRsiMode` (SHADOW), validasi, `inputs_json` (52); preset 12 simbol; README; TC-SU-04c (52), TestPresets, TS-75. Unit 655/655, pytest 106/106.

- [x] 2. Skor gerbang, konteks, dan pencatatan
  - Red: TC-SG-33, TC-SG-34, TC-SG-22e, JSON baru TC-SG-21/22, TC-SG-24e → FAIL.
  - Green: `ActiveConfirmations` (+ RSI), `EvaluateSignal` (`rsiScore`, tanpa tahap tolak), `SignalContextJson` (`rsi_age`, `rsi_diff`, `rsi_pdiff`), field `rsiMode`/`rsi`/`rsiScore`/`scoreRsi`, Logger RSI.
  - _Requirements: 2.5, 3.1, 3.2, 4.2–4.4_ · _Tests: TC-SG-21, 22, 22e, 24e, 33, 34_
  - Hasil (2026-10-07): Red = TC-SG-22e/24e/33/34 dan JSON baru TC-SG-21/22 gagal compile (`rsiMode`, `rsi`, `scoreRsi`). Green: field `SdbSignalFacts.rsiMode`/`rsi`, `SdbDecision.rsiScore`, `SignalRecord.scoreRsi`/`rsiMode`; `ActiveConfirmations` + RSI (maks 100 bila empat komponen aktif); `EvaluateSignal` tanpa cabang tahap tolak RSI; `SignalContextJson` (`rsi_age`, `rsi_diff` 1 desimal, `rsi_pdiff` 2 desimal; null bila OFF atau tanpa dua swing); Logger RSI (`max_score` 5) dengan `active` sesuai mode. TC-SG-34: RSI 0/5 di SHADOW tidak mengubah tahap; kandidat SCORE_TOO_LOW tetap ditolak walau RSI 5. Unit 659/659.

- [x] 3. Handle `iRSI`, `CConfirmations`, dan skenario
  - Red: TC-RSI-11 (handle nyata di tester) dan SC-21 (file skenario dibuat lebih dulu) → FAIL.
  - Green: `CSdbApp` membuat dan melepas `m_rsiHandle`; `CConfirmations.Init(..., rsiMode, rsiHandle, ...)` + `CopyBuffer` berdasarkan waktu bar + WARN tertahan; `CSignalEngine.Init` meneruskan; TestSignalEngine; `CheckSc21`.
  - Verifikasi: SC-18..21 PASS; unit ALL PASS; compile 0/0.
  - _Requirements: 1.1–1.4, 3.2, 4.2, 4.4_ · _Tests: TC-RSI-11, SC-18..21_
  - Hasil (2026-10-07): Red = TC-RSI-11 gagal compile (`RsiCopyAligned` belum ada); SC-21 FAIL ("skenario tidak dikenal harness"). Green: `RsiCopyAligned` (CopyBuffer berdasarkan waktu r[0]..r[n-1], wajib n nilai) dan `CConfirmations.EvaluateRsi` (handle tidak valid / tidak sejajar: skor 0 "data kurang", WARN tertahan 1 hari); `CConfirmations.Init(..., rsiMode, rsiHandle, ...)`; `CSdbApp.m_rsiHandle` dibuat bila sinyal aktif dan mode bukan OFF (gagal = WARN, degrade aman), dilepas di `OnDeinit`; `CSignalEngine.Init` meneruskan; TestSignalEngine (RSI OFF); `CheckSc21` (empat komponen bayangan, tidak ada penolakan yang menyebut RSI). Unit 660/660, SC-18..21 PASS. SC-21: komponen lain identik dengan run sebelumnya; RSI 0 / 5 = 208 / 8 dari 216 kandidat (3,7%); ACCEPTED 0 dari 9 bernilai 5.

- [x] 4. Pengukuran IS/OOS, versi 1.23, dokumen
  - Run: `-Baseline -Period ALL` v1.23 (background); bandingkan trade per simbol dengan acuan 1091–1114; `component_report.py` dan `--candidates`.
  - Dokumen: versi 1.23; `docs/flows/signals.md` dan `docs/flows/init.md` (handle RSI); CHANGELOG; README spec.
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot/ea): skor RSI divergence bayangan v1.23 (spec 21)`; git push.
  - Bila trade tidak identik dengan acuan, atau ACCEPTED bernilai 5 di luar 2–60%, temuan dibahas dulu.
  - _Requirements: 5.1–5.3_ · _Tests: RUN-01, RUN-02, semua_

  - Hasil (2026-10-07): `-Baseline -Period ALL` v1.23 (sesi 1157–1180, 1 jam 13 menit): waktu entry, arah, SL/TP, harga close identik dengan v1.22 (1091–1114). Tarif swap server berubah lagi, jadi saldo bergeser beberapa sen dan sebagian lot berbeda satu step (9 dari 43 trade EURUSD, 13 dari 51 USDCHF; misalnya 53,94 → 53,95); profit total berbeda sen. Ini sesuai pengecualian swap di Req 5.1, bukan perubahan keputusan EA. `component_report.py`: RSI IS 0 / 5 = 477 trade +0,039R / 16 trade −0,274R; OOS 50 −0,015R / 2 +1,314R; status `SAMPEL KURANG`. ACCEPTED bernilai 5 = 3,3% (dalam batas 2–60%). Dokumen: versi 1.23, `docs/flows/signals.md`, `docs/flows/init.md` (handle RSI), indeks flows, CHANGELOG, README spec. Regresi: build 0/0, unit 660/660, 30 skenario PASS (19:58), pytest 106/106, `schema.py check` OK.
