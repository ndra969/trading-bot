# Implementation plan — 36 Zona M30 (H9)

Status: Done (2026-10-14)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: suite MQL5 `-Unit`, skenario `-Scenario`, pytest. Setiap task: Red → Green → "Hasil". Commit sekali di akhir spec. Satu proses terminal uji, CPU ≤ 50% core.

- [x] 1. Input timeframe dan `ResolveTimeframes`
  - Red: TC-CU-19, TC-IR-05, TC-SU-04c (60), TestPresets, TS-125 → FAIL.
  - Green: `ResolveTimeframes`, `InputValues` + validasi, 3 input + `inputs_json`, `CSdbApp`, `gen_presets.py` + preset, README.
  - Verifikasi: unit ALL PASS, compile 0/0, pytest PASS.
  - _Requirements: 1.1–1.5_ · _Tests: TC-CU-19, TC-IR-05, TC-SU-04c, TestPresets, TS-125_
  - Hasil (2026-10-13): Red build 30 error + TS-125 FAIL; Green compile 0/0, unit pass=687 fail=0, pytest PASS; preset 29 dengan tiga input = 0; README.

- [x] 2. Skenario SC-36, versi, regresi
  - Red: file SC-36 lebih dulu → FAIL (skenario tak dikenal).
  - Green: `CheckSc36`; versi 1.33 (EA + harness).
  - Verifikasi: SC-36 PASS; `-All` background PASS.
  - _Requirements: 1.2, 1.5_ · _Tests: SC-36, REG_
  - Hasil (2026-10-13): Red SC-36 FAIL (skenario tak dikenal); Green SC-36 PASS (H1/M30/M15 di `inputs_json`, sinyal bertimeframe M30); versi 1.33; `-All` PASS (unit + 37 skenario).

- [x] 3. Pengukuran IS
  - Run: `-Baseline -Period IS` V1 (H1/M30/M15) dan V2 (H4/M30/M15); amandemen: V3 (H4/H1/M30) dan V4 (M30/M15/M5).
  - Laporan `exit_report` (frekuensi, lama posisi), per simbol; aturan design §4.
  - _Requirements: 2.1–2.4_ · _Tests: RUN-01_
  - Hasil (2026-10-14), acuan 1.31 (1968–1979): 121 trade, 4,5/bulan, +0,164R, PF 1,39, +19,8R.

    | Varian | Sesi | Trade | /bulan | R/trade | PF | Total R | SL |
    |---|---|---|---|---|---|---|---|
    | V1 H1/M30/M15 | 2247–2258 | 41 | 1,5 | −0,288 | 0,55 | −11,8 | 63% |
    | V2 H4/M30/M15 | 2259–2270 | 54 | 2,0 | −0,173 | 0,71 | −9,3 | 59% |
    | V3 H4/H1/M30 | 2271–2282 | 22 | 0,8 | −0,334 | 0,47 | −7,3 | 64% |
    | V4 M30/M15/M5 | 2319–2323, 2325–2331 | 189 | 7,0 | −0,280 | 0,56 | −52,9 | 64% |

  - Tidak ada varian yang lolos (frekuensi ≥ 182 trade dan R/trade ≥ +0,05): H9 ditolak di IS. V4 satu-satunya yang memenuhi frekuensi (189 trade, lama posisi 1,5 hari vs 5,4), tetapi rugi terbesar. Sesi 2324 (GBPUSDc) terputus saat runner berhenti dan tidak dihitung; GBPUSDc diulang di 2325. Zona M30 justru menghasilkan **lebih sedikit** trade daripada acuan: kandidat sampai tahap pemicu PA tidak bertambah (tolak PA V2 2.936 vs acuan 3.207; V1 2.425), lebih sedikit yang lolos gerbang akhir, dan yang masuk lebih sering kena SL (59–64% vs 43%).

- [x] 4. Konfirmasi OOS dan REAL, keputusan
  - Bila ada varian terpilih: OOS + REAL; aturan §4.3.
  - DITERIMA: default timeframe + preset (Red dulu pada TS-125), versi 1.34. DITOLAK: default tetap, 1.33.
  - _Requirements: 3.1–3.4_ · _Tests: RUN-02_
  - Hasil (2026-10-14): tidak ada varian terpilih, OOS/REAL tidak dijalankan. H9 DITOLAK: default tetap (`PERIOD_CURRENT` = ikut gaya), input timeframe tetap ada untuk eksperimen, versi 1.33.

- [x] 5. Dokumen dan regresi akhir
  - PC (input timeframe; dan bila diterima §Gaya dan timeframe); CHANGELOG; README spec dan EA; `fase-5c-overview.md` §8.
  - Regresi akhir; tandai Done; commit `feat(sdbot/ea): input timeframe, zona M30 (H9) v1.3x (spec 36)`; push.
  - _Requirements: 3.5_ · _Tests: semua, REG_
  - Hasil (2026-10-14): PC-36; CHANGELOG 1.33; README spec; `fase-5c-overview.md` §8. Regresi `-All` PASS (task 2, kode tidak berubah sesudahnya).
