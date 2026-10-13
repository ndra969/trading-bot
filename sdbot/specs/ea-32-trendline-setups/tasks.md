# Implementation plan — 32 Lab setup trendline H1 + PA M15

Status: Done (2026-10-13)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`. Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Tidak memakai terminal uji kecuali bila bar M1 perlu diekspor ulang.

- [x] 1. Data dan port swing, ATR, bias
  - Red: TS-116 (aggregate), TS-117 (find_swings), TS-120 (bias) di `tools/tests/test_trendline_lab.py` → FAIL.
  - Green: `aggregate`, `atr_series`, `find_swings`, `structure_dir`, `ema_dir`, `bias`.
  - _Requirements: 1.1, 1.2_ · _Tests: TS-116, TS-117, TS-120_
  - Hasil (2026-10-13): Red (modul belum ada); Green `aggregate`, `closed_count`, `wilder_atr` (AtrSeries), `find_swings`, `structure_dir`, `ema_dir`, `bias_of`/`bias_at` dengan jendela EA (H4 105, H1 156, M15 45). TS-116/117/120 PASS. TS-123 sempat salah di test (cek sebelum bar tutup), diperbaiki di test.

- [x] 2. Port pola PA dan trendline
  - Red: TS-118 (pola, fixture dari `TestPatterns`), TS-119 (trendline) → FAIL.
  - Green: `detect_pattern` + `Is*`, `trendline` (tanpa zona) dan `tl_vs_zone`.
  - _Requirements: 1.1_ · _Tests: TS-118, TS-119_
  - Hasil (2026-10-13): `detect_pattern` (urutan STAR → ENGULF_STRONG → PIN → ENGULF → TWEEZER → OUTSIDE), `trendline` dan `tl_vs_zone` (TlEvaluate). TS-118/119 PASS; fixture engulfing kuat di test diperbaiki (close harus melewati low bar sebelumnya, aturan EA).

- [x] 3. Setup A dan C, simulasi berurutan
  - Red: TS-121, TS-122, TS-123, TS-124 → FAIL.
  - Green: `setups_a`, `setups_c` (filter sesi, SL min/max, varian bias), `run_symbol` (berurutan per simbol, `outcome_sim.simulate`).
  - _Requirements: 1.2, 2.1–2.6_ · _Tests: TS-121..124_
  - Hasil (2026-10-13): `setup_a_signal`, `BreakTracker`, `candidates`, `run_symbol` (satu posisi per setup per simbol), `sequential`; `outcome_sim.Outcome.closed_at` ditambahkan. TS-121..124 PASS; pytest semua PASS, ruff/black/mypy bersih.

- [x] 4. Verifikasi port terhadap EA
  - Green: CLI `verify`; jalankan pada IS acuan (1968–1979).
  - Bila di bawah ambang design §5: selidiki, perbaiki port dengan TS baru (Red dulu), ulangi.
  - _Requirements: 1.3_ · _Tests: RUN-01_
  - Hasil (2026-10-13): `verify` pada 31.104 kandidat IS acuan 1.31 (sesi 1968–1979): pola PA 31.104/31.104 (100,0%), bias 31.000/31.104 (99,7%), trendline (sentuhan + jarak ≤ 0,02 ATR) 19.948/19.948 (100,0%) → LOLOS.

- [x] 5. Laporan IS, setup B, pilihan
  - Green: CLI `run` (laporan per setup × varian × simbol), setup B dari data spec 31; README tools.
  - Run IS; aturan design §5.
  - _Requirements: 3.1, 4.1, 4.2_ · _Tests: RUN-02_
  - Hasil (2026-10-13), IS 12 simbol, bar M1 (trade, /bulan, R/trade, total, PF): A bias 3.809, 141, −0,209, −794,7R, 0,65; A tanpa bias 8.536, 317, −0,194, −1.652R, 0,68; C bias 2.039, 76, −0,133, −270,9R, 0,77; C tanpa bias 5.387, 200, −0,183, −984,5R, 0,70. Semua simbol negatif di A dan C (terbaik XAUUSD −0,02, USDJPY −0,02/+0,02, XAUUSD C bias +0,07).
  - Setup B (trade EA 1.31 IS 1968–1979 dengan trendline ≤ 0,2 ATR dari zona, ≥ 2 sentuhan): 71 trade, +0,273R, PF 1,64 (seluruh trade 1.31: +0,164R). Berbeda dengan temuan spec 31 pada 1.29 (trendline di zona negatif); dengan zona lawan wajib, trendline di zona tidak lagi merugikan. Sampel kecil, tidak dijadikan aturan.
  - Aturan §5: tidak ada varian A/C lolos IS (R per trade negatif). **Setup trendline tanpa zona DITOLAK.**

- [x] 6. Konfirmasi OOS dan REAL, keputusan, dokumen
  - Varian lolos IS: OOS + REAL; aturan §5.2.
  - Catat hasil di spec dan `fase-5c-overview.md`; CHANGELOG; README spec.
  - Regresi: pytest, ruff/black/mypy.
  - Tandai spec Done; commit `feat(sdbot/tools): lab setup trendline (spec 32)`.
  - _Requirements: 4.3–4.5_ · _Tests: RUN-03_
  - Hasil (2026-10-13): OOS/REAL tidak dijalankan (tidak ada varian lolos IS). Dokumen: `fase-5c-overview.md` §8, CHANGELOG, README spec dan tools. pytest PASS, ruff/black/mypy bersih.

## Validasi manual (di luar tasks)

- Setup yang lolos menjadi spec EA baru (entry tambahan di samping strategi zona), dengan backtest EA IS/OOS/REAL seperti spec lain.
