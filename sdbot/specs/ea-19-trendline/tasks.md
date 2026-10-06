# Implementation plan — 19 Skor trendline (mode bayangan)

Status: Done (2026-10-06)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.21 di task 4. Backtest dijalankan dengan satu agen tester di background.

- [x] 1. Aturan trendline (fungsi murni) dan input
  - Red: TC-TL-01..11 (suite baru `TestTrendlineRules`) terhadap stub `Strategies/TrendlineRules.mqh` → FAIL.
  - Green:
    - `TlValueAt`, `TlTouches`, `TlBroken`, `TlEvaluate`; `SdbTrendlineResult`; konstanta `SDB_TL_*`, `SDB_SCORE_MAX_TRENDLINE`;
    - input `InpScoreTrendlineMode` (SHADOW), validasi, `inputs_json` (50), preset, README; TC-SU-04c, TestPresets, TS presets.
  - _Requirements: 1.1–1.4, 2.1–2.3, 3.1_ · _Tests: TC-TL-01..11_
  - Hasil (2026-10-06): Red = TC-TL-01..11 gagal compile (`SdbTrendlineResult`, input belum ada). Green: `Strategies/TrendlineRules.mqh` (`TlValueAt`, `TlTouches`, `TlBroken`, `TlDistToZone`, `TlEvaluate`); `SdbTrendlineResult` di `Core/Types.mqh`; konstanta `SDB_TL_*`, `SDB_SCORE_MAX_TRENDLINE`; input `InpScoreTrendlineMode` (SHADOW), validasi, `inputs_json` (50); preset 12 simbol; README; TC-SU-04c (50), TestPresets, TS-73. Menyimpang dari design (sudah diperbarui): sentuhan dihitung dari semua swing sesisi di jendela yang ada di garis, bukan hanya sejak titik pertama, dan cek patah dimulai dari sentuhan paling awal. Hitung "sejak i1" membuat garis yang sama bernilai beda menurut pasangan titiknya (TC-TL-08 gagal). Unit 627/627, pytest 104/104.

- [x] 2. Skor gerbang, konteks, dan pencatatan
  - Red: TC-SG-30, TC-SG-22c, JSON baru TC-SG-21/22, TC-SG-24c → FAIL.
  - Green:
    - `ActiveConfirmations`, `EvaluateSignal` (FIB dan TL ACTIVE ke skor dan maksimum);
    - `SignalContextJson` (`tl_dist`, `tl_slope`, `tl_touches`);
    - `SdbSignalFacts.tlMode`/`tl`, `SdbDecision.tlScore`, `SignalRecord.scoreTrendline`/`trendlineMode`;
    - Logger mencatat TRENDLINE dengan `active` sesuai mode.
  - _Requirements: 2.4, 3.2–3.4_ · _Tests: TC-SG-21, 22, 22c, 24c, 30_
  - Hasil (2026-10-06): Red = TC-SG-22c/24c/30 dan JSON baru TC-SG-21/22 gagal compile (`tlMode`, `tl`, `scoreTrendline`). Green: `SdbSignalFacts.tlMode`/`tl`, `SdbDecision.tlScore`, `SignalRecord.scoreTrendline`/`trendlineMode`; `ActiveConfirmations` (FIB dan TRENDLINE ACTIVE ke skor dan maksimum: 55 / 70 / 85); `SignalContextJson` (`tl_dist` 2 desimal, `tl_slope` 3 desimal, `tl_touches`; null bila OFF atau tanpa garis); Logger mencatat TRENDLINE dengan `active` sesuai mode; `CSignalEngine.Record` meneruskan skor dan mode. Unit 630/630.

- [x] 3. `CConfirmations` dan rangkaian engine
  - Red: SC-19 (harness pipeline, FIB dan TRENDLINE bayangan, `tl_touches`) → FAIL.
  - Green: `Strategies/Confirmations.mqh` (Fibonacci dipindah dari `CollectFib` tanpa perubahan perilaku, trendline baru); `CSignalEngine.Init` menerima mode trendline dan memakai `CConfirmations`; `CSdbApp` meneruskan input; TestSignalEngine menyesuaikan.
  - Verifikasi: SC-18 dan SC-19 PASS; unit ALL PASS; compile 0/0.
  - _Requirements: 1.1, 1.5, 3.2, 3.5_ · _Tests: SC-18, SC-19_
  - Hasil (2026-10-06): Red = SC-19 FAIL ("skenario tidak dikenal harness", file skenario dibuat lebih dulu). Green: `Strategies/Confirmations.mqh` (`CConfirmations`: mode Fibonacci + trendline, satu salinan bar MTF untuk semua komponen); `CollectFib` dihapus dari engine, Fibonacci dipindah tanpa perubahan perilaku; `CSignalEngine.Init(..., fibMode, tlMode)`; `CSdbApp` meneruskan `InpScoreTrendlineMode`; TestSignalEngine; `CheckSc19`. SC-18 dan SC-19 PASS. Distribusi FIB di SC-19 identik dengan SC-18 sebelumnya (173 nol, nilai sama). TRENDLINE SC-19: 0 / 7 / 15 = 114 / 41 / 61 dari 216 kandidat; ACCEPTED 6 dari 9 bernilai 15 (sampel kecil, dinilai di task 4). Unit 630/630, compile 0/0.

- [x] 4. Pengukuran IS/OOS, versi 1.21, dokumen
  - Run: `-Baseline -Period ALL` v1.21 (background); bandingkan trade per simbol dengan acuan 964–987; `component_report.py` dan `--candidates`.
  - Dokumen: versi 1.21 (EA + harness); `docs/flows/signals.md`; CHANGELOG (hasil TRENDLINE IS/OOS); README spec.
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot/ea): skor trendline bayangan v1.21 (spec 19)`; git push.
  - Bila trade tidak identik dengan acuan, atau distribusi TRENDLINE di luar batas Req 4.3 (> 60% ACCEPTED bernilai 15 atau < 2% bernilai > 0), temuan dibahas dulu.
  - _Requirements: 4.1–4.3_ · _Tests: RUN-01, RUN-02, semua_

  - Hasil (2026-10-06): `-Baseline -Period ALL` v1.21 (sesi 1027–1051, 1 jam 35 menit, naik dari 1 jam 10 menit karena perhitungan trendline): jumlah trade dan profit kotor identik dengan v1.20 di semua simbol (IS 493 PF 1,06; OOS 52 PF 1,07). `component_report.py`: TRENDLINE IS 0 / 7 / 15 = 199 trade +0,045R / 119 +0,020R / 175 +0,016R; OOS 22 +0,476R / 12 −0,326R / 18 −0,261R; status `SAMPEL KURANG`. ACCEPTED dengan TL 15 = 35,4%, TL > 0 = 59,4% (dalam batas Req 4.3). Trade dengan trendline tidak lebih baik di IS dan lebih buruk di OOS. Dokumen: versi 1.21, `docs/flows/signals.md` dan indeks flows, CHANGELOG, README spec. Regresi: build 0/0, unit 630/630, 28 skenario PASS (18:13), pytest 104/104, `schema.py check` OK.
