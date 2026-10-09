# Implementation plan — 26 Trailing lebih longgar (H4)

Status: Done (2026-10-09)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`; suite MQL5 dan regresi lewat `tools/run-ea-tests.ps1` (bila default berubah).

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Backtest dijalankan dengan satu agen tester di background.

- [x] 1. Kolom give-back di `exit_report.py`
  - Red: TS-90 di `tools/tests/test_exit_report.py` → FAIL.
  - Green: `trail_mfe_avg`, `trail_giveback_avg` dan dua kolom di `render` sampai PASS; README tools.
  - Verifikasi: acuan v1.25 IS menunjukkan TRAIL MFE ≈ +1,62 dan give-back ≈ 0,72.
  - _Requirements: 1.2_ · _Tests: TS-90_
  - Hasil (2026-10-09): Red TS-90 FAIL; Green pytest 120 passed, ruff/black bersih. Acuan TRAIL MFE / give-back: IS +1,62 / 0,72; OOS +1,69 / 0,57; REAL +1,57 / 0,70.

- [x] 2. Pengukuran IS dan pilihan varian
  - Run: `-Baseline -Period IS -SetInput 'InpTrailATRMult=3.0'` lalu `'=4.0'`.
  - Laporan: `baseline_report.py` dan `exit_report.py` (acuan 1396–1407 + kedua varian).
  - Aturan pilih design §4; catat hasil dan varian terpilih (atau H4 ditolak).
  - _Requirements: 1.1–1.5_ · _Tests: RUN-01_
  - Hasil (2026-10-09): mult 3,0 (sesi 1586–1597) 341 trade, +0,045R, PF 1,09, DD terbesar 6,5%; mult 4,0 (1598–1609) 340 trade (`exit_report`; laporan dasar 341), +0,064R, PF 1,13, DD 6,5%, min per simbol 19; acuan 2,0 341 trade, +0,046R, PF 1,10.
  - Alasan tutup (n × R) acuan / 3,0 / 4,0: SL 166 / 166 / 166 (−1,00); BE_STOP 33 × +0,26 / 51 × +0,29 / 65 × +0,34; TRAIL_STOP 97 × +0,90 / 70 × +0,90 / 44 × +0,85; TP 45 / 54 / 65 (+1,93 / +1,93 / +1,98). TRAIL MFE / give-back: +1,62 / 0,72 → +1,75 / 0,85 → +1,70 / 0,85.
  - Pilihan (design §4): 3,0 tidak lebih baik dari acuan; 4,0 lolos → **mult 4,0**. Trailing longgar memindahkan 20 trade ke TP; sisanya kembali ke BE (BE_STOP naik 33 → 65).

- [x] 3. Konfirmasi OOS dan REAL, keputusan
  - Bila ada varian terpilih: `-Period OOS` dan `-Period REAL` dengan input sama; bandingkan dengan acuan 1408–1419 dan 1420–1431.
  - Keputusan Req 2.2. Bila DITERIMA: `SDB_DEF_TRAIL_ATR_MULT`, `gen_presets.py` + 12 preset, TS-91 (Red dulu), versi 1.27 (EA + harness), README input, PC baru. Bila DITOLAK: default tetap, hasil dicatat.
  - _Requirements: 2.1–2.5_ · _Tests: RUN-02, TS-91_
  - Hasil (2026-10-09): mult 4,0 OOS (sesi 1610–1621) 37 trade, +0,116R, PF 1,26 (acuan +0,156R, 1,36); REAL (1622–1633) 116 trade, +0,019R, PF 1,04 (acuan +0,030R, 1,06). Alasan tutup REAL: TP 15 → 20, TRAIL_STOP 31 × +0,87 → 15 × +0,79, BE_STOP 13 × +0,24 → 24 × +0,34; give-back 0,70 → 0,77.
  - Keputusan Req 2.2/2.4: **H4 DITOLAK** (OOS dan REAL lebih buruk). Default `InpTrailATRMult` tetap 2,0, preset dan versi (1.26) tidak berubah; TS-91 tidak dibuat.

- [x] 4. Dokumen dan regresi
  - CHANGELOG, README spec, README EA, `fase-5b-overview.md` §7.
  - Regresi: pytest, `schema.py check`; bila default berubah juga build 0/0 dan `-All` (background).
  - Tandai spec Done; commit sesuai keputusan; git push.
  - _Requirements: 2.3–2.5_ · _Tests: semua, REG_
  - Hasil (2026-10-09): CHANGELOG, README spec dan EA, `fase-5b-overview.md` §7 diperbarui; pytest 120 passed; `schema.py check` OK. Build dan `-All` tidak dijalankan karena kode EA, default, dan preset tidak berubah (regresi terakhir spec 25: 33 run PASS).
