# Implementation plan — 24 Breakeven lebih awal (H2)

Status: Done (2026-10-08)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`;
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, regresi lewat `-All`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Backtest dijalankan dengan satu agen tester di background.

- [x] 1. Alat `exit_report.py`
  - Red: TS-84..87 di `tools/tests/test_exit_report.py` dengan DB fixture → FAIL.
  - Green: `tools/exit_report.py` (`exit_summary`, `render`, CLI `--db`, `--runs NAMA=A-B[,C-D]`) sampai PASS; baris di README tools.
  - Verifikasi: jalankan pada acuan v1.25 (IS 1396–1407); jumlah trade dan R per trade sama dengan `baseline_report.py` (341, +0,046).
  - _Requirements: 1.2, 2.2_ · _Tests: TS-84..87_
  - Hasil (2026-10-08): Red error koleksi (modul belum ada); Green TS-84..87 PASS, pytest 118 passed, ruff/black bersih. Acuan v1.25: IS 341 trade +0,046R PF 1,10 (sama dengan `baseline_report.py`); SL 166 (53 sempat MFE ≥ 0,5R), BE_STOP 33 +0,26, TRAIL_STOP 97 +0,90, TP 45 +1,93; MODIFY_FAILED 0.

- [x] 2. Pengukuran IS dan pilihan varian
  - Run: `-Baseline -Period IS -SetInput 'InpBreakevenR=0.5'` lalu `'InpBreakevenR=0.75'`.
  - Laporan: `baseline_report.py` (PF, DD, per simbol) dan `exit_report.py --runs acuan=1396-1407 --runs be050=… --runs be075=…`.
  - Aturan pilih design §4; catat hasil dan varian terpilih (atau H2 ditolak) di baris "Hasil".
  - _Requirements: 1.1–1.5_ · _Tests: RUN-01_
  - Hasil (2026-10-08): BE 0,5 (sesi 1471–1482) 342 trade, +0,023R, PF 1,07, DD terbesar 5,6%; BE 0,75 (sesi 1483–1494) 342 trade, +0,021R, PF 1,05, DD 5,3%; acuan 1,0 (1396–1407) 341 trade, +0,046R, PF 1,10.
  - Alasan tutup (n × R rata-rata), acuan → BE 0,5 → BE 0,75: SL 166 → 117 → 148 (−1,00); BE_STOP 33 × +0,26 → 116 × +0,13 → 60 × +0,18; TRAIL_STOP 97 × +0,90 → 78 × +0,62 → 94 × +0,72; TP 45 → 31 → 40. SL sempat MFE ≥ 0,5R: 53 → 3 → 34. MODIFY_FAILED 0 di semua run.
  - Pilihan (design §4): tidak ada varian dengan R per trade > acuan → **H2 DITOLAK** (Req 1.5), OOS dan REAL tidak dijalankan. BE lebih awal memotong SL, tetapi trailing ATR yang aktif sesudah BE ikut mulai lebih cepat dan memotong winner (TRAIL_STOP dan TP turun).

- [x] 3. Konfirmasi OOS dan REAL, keputusan
  - Bila ada varian terpilih: `-Period OOS` dan `-Period REAL` dengan input yang sama; bandingkan dengan acuan 1408–1419 dan 1420–1431 (`baseline_report.py` + `exit_report.py`).
  - Keputusan Req 3.1. Bila DITERIMA: `SDB_DEF_BREAKEVEN_R`, `gen_presets.py` + 12 preset, TS-88 (Red dulu), versi 1.26 (EA + harness), README input, PC-30. Bila DITOLAK: default tetap, hasil dicatat.
  - _Requirements: 2.1–2.3, 3.1–3.4_ · _Tests: RUN-02, TS-88_
  - Hasil (2026-10-08): tidak dijalankan karena tidak ada varian terpilih (Req 1.5). Keputusan Req 3.3: default `InpBreakevenR` tetap 1.0, preset dan versi (1.25) tidak berubah; TS-88 tidak dibuat.

- [x] 4. Dokumen dan regresi
  - CHANGELOG (1.26 bila diterima, catatan bila ditolak), README spec, README EA (status Fase 5b).
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot): breakeven lebih awal (H2) (spec 24)` atau `docs(sdbot): H2 ditolak (spec 24)` sesuai keputusan; git push.
  - _Requirements: 2.3, 3.2–3.4_ · _Tests: semua, REG_
  - Hasil (2026-10-08): CHANGELOG, README spec dan EA diperbarui; pytest 118 passed; `schema.py check` OK. Regresi `-All` tidak dijalankan: spec ini tidak mengubah kode EA, preset, atau default (H2 ditolak), sehingga build dan skenario sama dengan regresi spec 23 (32 run PASS).
