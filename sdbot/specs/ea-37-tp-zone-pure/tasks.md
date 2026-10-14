# Implementation plan — 37 Manajemen posisi lebih ringan (H10)

Status: Done (2026-10-14)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

Tanpa kode EA kecuali bila diterima. Backtest satu proses terminal uji, CPU ≤ 50% core. Commit sekali di akhir spec, lalu push.

- [x] 1. Pengukuran IS
  - Run: `-Baseline -Period IS` untuk V1 (`InpBreakevenR=9,InpPartialR=10`), V2 (`InpPartialR=10`), V3 (`InpBreakevenR=1.5,InpPartialR=10`).
  - Laporan: `baseline_report`, `exit_report`, `trade_diff` vs 1968–1979; jumlah trade dengan R:R rencana > 9.
  - Aturan design §2.
  - _Requirements: 1.1–1.5_ · _Tests: RUN-01_
  - Hasil (2026-10-14), acuan 1.31 (1968–1979): 121 trade, +0,164R, +19,8R, DD 6,55R.
  - V1 murni (2283–2294): 120 trade, +0,275R, +33,0R, PF 1,39, DD 17,68R → gagal (DD > 9,8R).
  - V2 tanpa partial (2295–2306): 121 trade, +0,185R, +22,4R, PF 1,43, DD 6,54R → lolos.
  - V3 BE 1,5R tanpa partial (2307–2318): 121 trade, +0,205R, +24,9R, PF 1,37, DD 9,22R → lolos.
  - Pilihan §2: V3 (R per trade tertinggi di antara yang lolos; selisih dari V2 0,020R, tidak < 0,02).

- [x] 2. Konfirmasi OOS dan REAL, keputusan
  - Bila ada varian terpilih: OOS + REAL; aturan §2.3.
  - DITERIMA: konstanta default + `gen_presets.py` + preset (uji preset Red dulu), versi naik, regresi `-All`. DITOLAK: default tetap.
  - _Requirements: 2.1–2.4_ · _Tests: RUN-02, TS, REG_
  - Hasil (2026-10-14), V3 (`InpBreakevenR=1.5,InpPartialR=10`):

    | Periode | Acuan 1.31 | V3 | Syarat |
    |---|---|---|---|
    | OOS | 21 trade, +0,421R, PF 2,47 (1980–1991) | 21 trade, **+0,524R**, +11,0R, PF 2,37, DD 4,01R (2376–2387) | ≥ +0,421 ✓ |
    | REAL | 55 trade, +0,224R, PF 1,58 (1992–2003) | 55 trade, **+0,297R**, +16,4R, PF 1,57, DD 6,35R (2388–2399) | ≥ +0,224 ✓ |

  - Jumlah trade sama di kedua periode. SL penuh lebih sering (OOS 8 vs 6, REAL 28 vs 21) karena BE baru di 1,5R, tetapi trailing menutup lebih besar (OOS +1,54R vs +1,16R, REAL +1,35R vs +0,88R) dan TP lebih besar (+2,36 / +2,84R) karena posisi tidak dipotong 50%.
  - H10 **DITERIMA**. Red: TS-135 FAIL (preset 1.0 / 1.5). Green: `SDB_DEF_BREAKEVEN_R` 1.5, `SDB_DEF_PARTIAL_R` 10.0, `gen_presets.py` + 29 preset; SC-01, SC-01b, dan SC-04 mem-pin BE 1R + partial 1,5R (skenario itu menguji urutan BE → partial → trailing dan restart sesudah partial); versi 1.35; pytest PASS; `-All` 36 PASS + SC-04 gagal (tidak ada partial untuk memicu restart), PASS sesudah di-pin.

- [x] 3. Dokumen
  - PC (bila diterima: §Position management); CHANGELOG; README spec; `fase-5c-overview.md` §8.
  - Tandai Done; commit `feat(sdbot): manajemen posisi (H10) (spec 37)`; push.
  - _Requirements: 2.3, 2.4_
  - Hasil (2026-10-14): PC-37; CHANGELOG 1.35; README spec; `fase-5c-overview.md` §8. Input "mati" eksplisit (Req 2.3) tidak dibuat: V3 memakai partial 10R (batas maksimum validasi), BE tetap aktif.
