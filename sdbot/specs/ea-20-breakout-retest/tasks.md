# Implementation plan — 20 Skor breakout & retest (mode bayangan)

Status: Done (2026-10-07)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.22 di task 4. Backtest dijalankan dengan satu agen tester di background.

- [x] 1. Aturan breakout (fungsi murni) dan input
  - Red: TC-BO-01..11 (suite baru `TestBreakoutRules`) terhadap stub `Strategies/BreakoutRules.mqh` → FAIL.
  - Green:
    - `BoBreakIndex`, `BoFailed`, `BoEvaluate`; `SdbBreakoutResult`; konstanta `SDB_BO_*`, `SDB_SCORE_MAX_BREAKOUT`;
    - `Strategies/StrategyMath.mqh` (`DistToZone`), `TrendlineRules` memakainya (TC-TL tetap PASS);
    - input `InpScoreBreakoutMode` (SHADOW), validasi, `inputs_json` (51), preset, README; TC-SU-04c, TestPresets, TS presets.
  - _Requirements: 1.1–1.3, 2.1, 2.2, 3.1_ · _Tests: TC-BO-01..11, TC-TL-01..11_
  - Hasil (2026-10-06): Red = TC-BO-01..11 gagal compile (`SdbBreakoutResult`, input belum ada). Green: `Strategies/BreakoutRules.mqh` (`BoBreakIndex` mulai sesudah bar konfirmasi swing, `BoFailed`, `BoEvaluate` memilih breakout terbaru); `Strategies/StrategyMath.mqh` (`DistToZone`, dipindah dari `TlDistToZone`, dipakai trendline dan breakout); `SdbBreakoutResult` di `Core/Types.mqh`; konstanta `SDB_BO_*`, `SDB_SCORE_MAX_BREAKOUT`; input `InpScoreBreakoutMode` (SHADOW), validasi, `inputs_json` (51); preset 12 simbol; README; TC-SU-04c (51), TestPresets, TS-74. Unit 641/641 (TC-TL-01..11 tetap PASS), pytest 105/105.

- [x] 2. Skor gerbang, konteks, dan pencatatan
  - Red: TC-SG-31, TC-SG-32, TC-SG-22d, JSON baru TC-SG-21/22, TC-SG-24d → FAIL.
  - Green: `ActiveConfirmations` (+ BREAKOUT), `EvaluateSignal` (`boScore`), `SignalContextJson` (`bo_age`, `bo_dist`, `bo_level`), field `boMode`/`bo`/`boScore`/`scoreBreakout`/`breakoutMode`, Logger BREAKOUT.
  - _Requirements: 2.3, 3.2–3.4, 4.2_ · _Tests: TC-SG-21, 22, 22d, 24d, 31, 32_
  - Hasil (2026-10-06): Red = TC-SG-22d/24d/31/32 dan JSON baru TC-SG-21/22 gagal compile (`boMode`, `bo`, `scoreBreakout`). Green: field `SdbSignalFacts.boMode`/`bo`, `SdbDecision.boScore`, `SignalRecord.scoreBreakout`/`breakoutMode`; `ActiveConfirmations` + BREAKOUT (maks 95 bila tiga komponen aktif); `SignalContextJson` (`bo_age`, `bo_dist` 2 desimal, `bo_level` digit simbol; null bila OFF atau tidak ada level); Logger mencatat BREAKOUT (`max_score` 10) dengan `active` sesuai mode; `Record` meneruskan skor dan mode. TC-SG-32 membuktikan BREAKOUT ACTIVE mengubah `SCORE_TOO_LOW` (37/65 = 56,9%) menjadi lolos (47/65 = 72,3%). Unit 645/645.

- [x] 3. Rangkaian `CConfirmations` dan skenario
  - Red: SC-20 (file skenario dibuat lebih dulu; harness belum mengenalnya) → FAIL.
  - Green: `CConfirmations.Init/Evaluate` dengan breakout; `CSignalEngine.Init` + `CSdbApp` meneruskan mode; TestSignalEngine; `CheckSc20`.
  - Verifikasi: SC-18, SC-19, SC-20 PASS; unit ALL PASS; compile 0/0.
  - _Requirements: 1.4, 3.2, 4.1_ · _Tests: SC-18, SC-19, SC-20_
  - Hasil (2026-10-06): Red = SC-20 FAIL ("skenario tidak dikenal harness", file skenario dibuat lebih dulu). Green: `CConfirmations` dengan mode breakout (`Init(fibMode, tlMode, boMode, ...)`, `BoEvaluate` memakai salinan bar yang sama); `CSignalEngine.Init` + `CSdbApp` meneruskan `InpScoreBreakoutMode`; TestSignalEngine; `CheckSc20`. Unit 645/645, SC-18/19/20 PASS. SC-20: FIB dan TRENDLINE identik dengan run sebelumnya; BREAKOUT 0 / 10 = 149 / 67 dari 216 kandidat; ACCEPTED 2 dari 9 bernilai 10. Komponen terbukti terhubung di pipeline (Req 4.1).

- [x] 4. Pengukuran IS/OOS, versi 1.22, dokumen
  - Run: `-Baseline -Period ALL` v1.22 (background); bandingkan trade per simbol dengan acuan 1027–1051; `component_report.py` dan `--candidates`.
  - Dokumen: versi 1.22; `docs/flows/signals.md`; CHANGELOG; README spec.
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot/ea): skor breakout & retest bayangan v1.22 (spec 20)`; git push.
  - Bila trade tidak identik dengan acuan, atau ACCEPTED bernilai 10 di luar 2–60%, temuan dibahas dulu.
  - _Requirements: 5.1–5.3_ · _Tests: RUN-01, RUN-02, semua_

  - Hasil (2026-10-07): `-Baseline -Period ALL` v1.22 (sesi 1091–1114, 1 jam 1 menit): trade dan profit kotor identik dengan v1.21 (1027–1050) di 24 run. Catatan: perbandingan pertama memakai rentang yang ikut menghitung sesi skenario harness EURUSDc (1051), lalu diulang dengan rentang tepat. `component_report.py`: BREAKOUT IS 0 / 10 = 304 trade −0,014R / 189 trade +0,097R; OOS 38 −0,083R / 14 +0,356R; status `SAMPEL KURANG` (OOS 10 baru 14 trade). ACCEPTED bernilai 10 = 37,2%. Komponen pertama yang membedakan searah di IS dan OOS. Dokumen: versi 1.22, `docs/flows/signals.md` dan indeks flows, CHANGELOG, README spec. Regresi: build 0/0, unit 645/645, 29 skenario PASS (19:13), pytest 105/105, `schema.py check` OK.
