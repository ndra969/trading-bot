# Implementation plan — 18 Skor Fibonacci (mode bayangan)

Status: Done (2026-10-06)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.20 di task 4. Backtest dijalankan dengan satu agen tester di background.

- [x] 1. Aturan Fibonacci (fungsi murni) dan input
  - Red: TC-FIB-01..11 (suite baru `TestFibRules`) terhadap stub `Strategies/FibRules.mqh` → FAIL.
  - Green:
    - `FibLegEnd`, `RetraceRatio`, `FibScore`, `FibEvaluate`; konstanta `SDB_FIB_*`, `SDB_SCORE_MAX_FIB`;
    - `ENUM_SDB_COMPONENT_MODE`, input `InpScoreFibMode` (default SHADOW), validasi, `inputs_json` (49);
    - preset 12 simbol (`gen_presets.py`), tabel input README; TC-SU-04c, TestPresets, TS presets menyesuaikan.
  - _Requirements: 1.1, 1.3, 2.1–2.5, 3.1_ · _Tests: TC-FIB-01..11_
  - Hasil (2026-10-06): Red = TC-FIB-01..11 gagal compile (`scoreFibMode`, `SDB_COMPONENT_SHADOW` belum ada). Green: `Strategies/FibRules.mqh` (`FibLegEnd`, `RetraceRatio`, `FibScore` level terdekat + tie ke level lebih dalam + linear sampai 0,05, `FibEvaluate` dengan alasan "leg pendek" / "data kurang" / "di luar leg"); konstanta `SDB_FIB_*`, `SDB_SCORE_MAX_FIB`; `ENUM_SDB_COMPONENT_MODE`; input `InpScoreFibMode` (SHADOW), validasi 0–2, `inputs_json` (49); preset 12 simbol (`InpScoreFibMode=1`); README; TC-SU-04c (49), TestPresets, TS-72. Unit 610/610, pytest 103/103.

- [x] 2. Skor gerbang, konteks, dan pencatatan
  - Red: TC-SG-28, TC-SG-29, JSON baru TC-SG-21/22, TC-SG-24 diperluas → FAIL.
  - Green:
    - `SdbSignalFacts.fib`/`fibMode`, `SdbDecision.fibScore`, `SignalRecord.scoreFib`/`fibMode`;
    - `EvaluateSignal` (ACTIVE: total + fib, maksimum + 15);
    - `SignalContextJson` (`fib_level`, `fib_ratio`);
    - Logger: baris FIB dengan `active` sesuai mode, tidak dicatat saat OFF.
  - _Requirements: 2.6, 3.2–3.5_ · _Tests: TC-SG-21, 22, 24, 28, 29_
  - Hasil (2026-10-06): Red = TC-SG-22b/24b/28/29 gagal compile (`scoreFib`, `fibMode`). Green: `SdbFibResult` dipindah ke `Core/Types.mqh` (Core tidak boleh bergantung pada Strategies; menyimpang dari design §3.1, isi sama); `SdbSignalFacts.fibMode`/`fib`, `SdbDecision.fibScore`, `SignalRecord.scoreFib`/`fibMode`; `EvaluateSignal` (ACTIVE: total + fib, maks + 15); `SignalContextJson` (`fib_level` 3 desimal bila ada level, `fib_ratio` 3 desimal, null saat OFF / tidak dihitung); Logger mencatat FIB dengan `active` = mode ACTIVE, tanpa baris saat OFF; `CSignalEngine.Record` meneruskan skor dan mode. TC-SG-21/22 dengan kunci baru. Unit 614/614.

- [x] 3. Rangkaian engine dan skenario
  - Red: SC-18 (harness pipeline, cek baris FIB bayangan dan `score_total`) → FAIL.
  - Green: `CZoneBook.Rates`; `CSignalEngine.Init` + `CollectFacts` memanggil `FibEvaluate` bila mode != OFF; `CSdbApp` meneruskan mode; TestSignalEngine menyesuaikan.
  - Verifikasi: SC-18 PASS; unit ALL PASS; compile 0/0.
  - _Requirements: 1.1, 1.2, 1.4, 3.2, 3.5_ · _Tests: SC-18_
  - Hasil (2026-10-06): Green: `CZoneBook.Rates` (cache bar MTF tertutup pembangun zona); `CSignalEngine.Init(..., fibMode)` + `CollectFib` (mode != OFF: `FibEvaluate` dengan `ZoneMinLegAtr` dan `StructureLookback`); `CSdbApp` meneruskan `InpScoreFibMode`; TestSignalEngine. SC-18 ditulis setelah rangkaian terpasang (tanpa run Red), lalu isinya diperiksa langsung: dengan leg dari batas jauh zona sendiri, rasio selalu 0,60–0,93 (median 0,83, level 0.786 di 185/216), sehingga FIB hanya mengukur lebar zona. Dibahas dengan user, keputusan A: leg = impuls penuh (`FibLegStart`: ekstrem 100 bar sebelum candle swing). TC-FIB-12 (zona tengah impuls, rasio 0.5, skor 15) dan TC-FIB-13 (asal impuls, rasio 0.9, skor 0; jendela lookback) Red lalu Green. SC-18 ulang: 216 sinyal, FIB > 0 di 43, level 0.382 / 0.5 / 0.618 / 0.786 = 65 / 19 / 10 / 19, rasio kuartil 0,19 / 0,26 / 0,39, skor penuh 0 dari 9 ACCEPTED. Unit 616/616, SC-18 PASS, compile 0/0.

- [x] 4. Pengukuran IS/OOS, versi 1.20, dokumen
  - Run: `-Baseline -Period ALL` v1.20 (background); bandingkan trade dan R total per simbol dengan acuan 901–924; `component_report.py` dan `--candidates` atas sesi baru.
  - Dokumen: versi 1.20 (EA + harness); `docs/flows/signals.md` (komponen Fibonacci bayangan); CHANGELOG (hasil FIB IS/OOS); README spec.
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot/ea): skor Fibonacci bayangan v1.20 (spec 18)`; git push.
  - Bila trade tidak identik dengan acuan, atau > 60% kandidat ACCEPTED mendapat FIB penuh, temuan dibahas dulu.
  - _Requirements: 4.1–4.3_ · _Tests: RUN-01, RUN-02, semua_

  - Hasil (2026-10-06): Percobaan pertama `-Period ALL` tidak valid: terminal uji dari run sebelumnya tetap terbuka, sehingga run berikutnya "selesai" 1–16 detik tanpa backtest. Bug runner diperbaiki (tunggu terminal mati sebelum run, GAGAL bila tidak ada sesi DB baru), terminal yang tersisa ditutup atas izin user. Run ulang (sesi 964–987, 1 jam 10 menit): trade identik dengan acuan 901–924 di semua simbol (IS 493 PF 1,06; OOS 52 PF 1,07); selisih satu-satunya swap XAU (−21,69 vs −21,91 USC, tarif server berubah). `component_report.py`: FIB IS 0 = 392 trade +0,032R, FIB > 0 = 101 trade ~+0,015R; OOS 0 = 37 trade −0,152R, > 0 = 15 trade ~+0,57R; status `SAMPEL KURANG`; FIB penuh 3 dari 545 ACCEPTED (0,6%, jauh di bawah ambang 60%). Dokumen: versi 1.20, `docs/flows/signals.md` dan indeks flows, CHANGELOG, README spec. Regresi: build 0/0, unit 616/616, 27 skenario PASS (16:35), pytest 103/103, `schema.py check` OK.
