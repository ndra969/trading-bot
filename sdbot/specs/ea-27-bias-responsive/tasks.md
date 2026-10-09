# Implementation plan — 27 Bias HTF lebih responsif (H5)

Status: Done (2026-10-10)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Backtest dijalankan dengan satu agen tester di background, CPU ≤ 50% core.

- [x] 1. Aturan bias per mode (fungsi murni)
  - Red: TC-MS-22..24 di `TestStructure.mqh` dengan signature baru `BiasOf(st, ema, mode)` dan `BiasReasonOf(htf, mode)` → build FAIL.
  - Green: `ENUM_SDB_BIAS_MODE` di `Core/Types.mqh`; `BiasOf` dan `BiasReasonOf` per tabel design §3.1; pemanggil di `CMarketStructure` sementara memakai `SDB_BIAS_AND_EMA`.
  - Verifikasi: unit ALL PASS (TC-MS lama tetap PASS), compile 0/0.
  - _Requirements: 1.2–1.6_ · _Tests: TC-MS-22..24_
  - Hasil (2026-10-09): Red build 21 error; Green compile 0/0, unit pass=672 fail=0. `BiasReasonOf` dan konstanta alasan dipindah dari `MarketStructure.mqh` ke `StructureRules.mqh` agar teruji sebagai fungsi murni; `ScSampleMatches` (SC-12) memakai `SDB_BIAS_AND_EMA`.

- [x] 2. Input mode dan periode EMA bias
  - Red: TC-IR-03, TC-SU-04c (56 kunci), TestPresets, TS-91 → FAIL.
  - Green: konstanta default; `InputValues.biasMode` / `biasEmaPeriod` + validasi + `EffectiveBiasEmaPeriod`; `InpBiasMode`, `InpBiasEmaPeriod` + `inputs_json`; `gen_presets.py` + 12 preset; README tabel konfigurasi.
  - Verifikasi: unit ALL PASS, compile 0/0, pytest PASS.
  - _Requirements: 1.1, 1.7, 2.1, 2.4_ · _Tests: TC-IR-03, TC-SU-04c, TestPresets, TS-91_
  - Hasil (2026-10-09): Red build 19 error + TS-91 FAIL; Green compile 0/0, unit pass=673 fail=0, pytest PASS; preset 12 simbol `InpBiasMode=0`, `InpBiasEmaPeriod=0`; README tabel konfigurasi.

- [x] 3. Parameter HTF/MTF terpisah di `CMarketStructure`
  - Red: TC-MS-25, TC-MS-26 → FAIL.
  - Green: `Init(symbol, htf, mtf, htfP, mtfP, mode)`; cache per timeframe dengan `BarsNeeded` masing-masing; `BarsRequired()` = maksimum; log bias menambah `mode=`; `CSdbApp` mengisi `htfP` (EMA efektif) dan `mtfP` (`InpEmaPeriod`) dan meneruskan mode.
  - Verifikasi: unit ALL PASS, compile 0/0.
  - _Requirements: 2.2, 2.3, 1.6_ · _Tests: TC-MS-25, TC-MS-26_
  - Hasil (2026-10-09): Red build 2 error (signature `Init`); Green compile 0/0, unit pass=675 fail=0 (TC-MS-26: HTF EMA 21 1,13254 vs EMA 50 1,13738, MTF identik). `Params()` mengembalikan parameter MTF (dipakai `Confirmations`); SC-12 (`ScSampleMatches`) memakai parameter HTF/MTF dan mode dari input.

- [x] 4. Skenario, versi, dan regresi default
  - Red: SC-27 (file skenario dibuat lebih dulu) → FAIL.
  - Green: `CheckSc27`; versi 1.27 (EA + harness); `docs/flows/signals.md` (node bias menyebut mode).
  - Verifikasi: SC-27 PASS; `-All` di background semua PASS dan skenario lama identik.
  - _Requirements: 1.4, 1.6, 2.4, 2.5_ · _Tests: SC-27, REG_
  - Hasil (2026-10-09): Red SC-27 FAIL (skenario tak dikenal); Green SC-27 pass=2 fail=0, SC-12 pass=4; versi 1.27 (EA + harness); `docs/flows/signals.md` node bias menyebut mode. `-All` 34 run PASS (unit 675/0, SC-00..SC-27), 36 menit.

- [x] 5. Alat `trade_diff.py`
  - Red: TS-92, TS-93 di `tools/tests/test_trade_diff.py` → FAIL.
  - Green: `diff_trades` + CLI (`--db`, `--base`, `--variant`), memakai fungsi R yang sama dengan `exit_report.py`; README tools.
  - Verifikasi: pytest PASS, ruff/black bersih. Uji asap: `--base 1396-1407 --variant 1396-1407` → semua trade "sama".
  - _Requirements: 3.2_ · _Tests: TS-92, TS-93_
  - Hasil (2026-10-09): Red (modul belum ada); Green pytest 123 passed, ruff/black bersih. Definisi trade tutup (`CLOSED_EA_FROM`/`CLOSED_EA_WHERE`) dipindah ke konstanta `exit_report.py` dan dipakai keduanya. Uji asap acuan vs acuan: 341 sama, +0,046R, 0 baru/hilang.

- [x] 6. Pengukuran IS dan pilihan varian
  - Run: `-Baseline -Period IS` dengan `-SetInput 'InpBiasMode=2'` (V-a), `'InpBiasEmaPeriod=21'` (V-b), `'InpBiasMode=1'` (V-c).
  - Laporan: `baseline_report.py`, `exit_report.py`, `trade_diff.py` terhadap acuan 1396–1407.
  - Aturan pilih design §5; catat hasil dan varian terpilih, atau H5 ditolak.
  - _Requirements: 3.1–3.4_ · _Tests: RUN-01_
  - Hasil (2026-10-10): V-a `STRUCTURE_ONLY` (sesi 1679–1690) 440 trade, +0,039R, PF 1,08, DD 7,9%, min per simbol 27; V-b EMA bias 21 (1691–1702) 356 trade, +0,079R, PF 1,17, DD 7,2%, min 20; V-c `NOT_OPPOSED` (1703–1714) 364 trade, +0,024R, PF 1,05, DD 6,5%, min 20; acuan (1396–1407) 341 trade, +0,046R, PF 1,10.
  - `trade_diff` vs acuan: V-a 341 sama + 99 baru (+0,013R); V-c 341 sama + 23 baru (−0,305R); V-b 319 sama (+0,059R), 37 baru (+0,251R), 22 hilang (−0,137R). Bias lebih longgar (V-a, V-c) hanya menambah trade yang lebih buruk; EMA 21 menukar trade rugi dengan trade baru yang untung.
  - Alasan tutup tidak bergeser (SL −1,00, BE +0,24–0,26, TRAIL +0,90–0,95, TP +1,93); perbedaan datang dari pilihan entry.
  - XAUUSDc: acuan 24 × +0,29R; V-a 34 × +0,34R; V-b 30 × +0,28R; V-c 26 × +0,25R.
  - Pilihan (design §5): hanya V-b lolos (R > +0,046, ≥ 325 trade, ≥ 13 per simbol) → **V-b `InpBiasEmaPeriod=21`**.

- [x] 7. Konfirmasi OOS dan REAL, keputusan
  - Bila ada varian terpilih: `-Period OOS` dan `-Period REAL`; bandingkan dengan acuan 1408–1419 dan 1420–1431 (ketiga laporan).
  - Keputusan Req 4.2. Bila DITERIMA: konstanta default, preset, TS-91 (Red dulu: nilai baru), versi 1.28. Bila DITOLAK: default tetap, versi 1.27.
  - _Requirements: 4.1–4.4_ · _Tests: RUN-02, TS-91_
  - Hasil (2026-10-10): V-b OOS (sesi 1715–1726) 41 trade, +0,163R, PF 1,39 (acuan 37, +0,156R, 1,36); REAL (1727–1738) 126 trade, +0,081R, PF 1,18, DD 7,34R (acuan 116, +0,030R, 1,06).
  - `trade_diff`: OOS 36 sama, 5 baru +0,291R, 1 hilang +0,579R; REAL 110 sama, 16 baru +0,389R, 6 hilang −0,072R. Pola IS terulang: EMA 21 menambah trade searah tren baru yang untung.
  - Keputusan Req 4.2: **H5 DITERIMA** (OOS dan REAL ≥ acuan). `SDB_DEF_BIAS_EMA_PERIOD` 21, preset 12 simbol `InpBiasEmaPeriod=21`, TS-91 dan TC-IR-03 (Red dulu: TS-91 FAIL, unit 674/1) lalu Green; versi 1.28 (EA + harness); README.

- [x] 8. Dokumen dan regresi akhir
  - PC baru di `docs/PENDING-CHANGES.md` (skill `sdbot-docs-sync`): §Parameter input, dan §Struktur dan bias HTF bila diterima.
  - CHANGELOG (1.27, dan 1.28 bila diterima), README spec, README EA.
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot/ea): mode bias HTF (H5) v1.2x (spec 27)`.
  - _Requirements: 4.3–4.5_ · _Tests: semua, REG_
  - Hasil (2026-10-10): PC-32 (Open, sinkron ke Claude Docs lewat `sdbot-docs-sync`); CHANGELOG 1.27 dan 1.28; README spec, README EA, ringkasan Fase 5b (§7); build 0/0; `-All` 34 run PASS (unit 675/0, SC-00..SC-27) dengan default baru; pytest PASS; `schema.py check` OK.

## Validasi manual (di luar tasks)

- Bila H5 diterima: pasang 1.28 di Broker B (timpa ex5, restart terminal), cek `sessions.ea_version` dan log perubahan bias dengan `mode=`.
- Pantau ringkasan gerbang harian live (`tanpa_bias`) 1–2 minggu dibanding sebelum perubahan.
