# Implementation plan — 22 Aktivasi komponen dan kalibrasi ambang (Fase 5 selesai)

Status: Done (2026-10-08)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`;
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`.

Setiap task: Red → Green (bila ada kode) → catat baris "Hasil". Commit sekali di akhir spec. Backtest berjalan di background dengan satu agen tester; urutan langkah dan aturan pemilihan dikunci di design §1 dan §3.3 sebelum OOS dilihat.

- [x] 1. Aturan aktivasi v2 dan runner `-SetInput`
  - Red: TS-76..80 → FAIL.
  - Green:
    - `component_report.py`: `verdict_v2`, ringkasan `> 0 vs 0` per periode (IS/OOS/REAL), opsi `--rule v2|pc25`;
    - `run-ea-tests.ps1 -SetInput 'Kunci=nilai',...` untuk backtest dasar (mengganti kunci preset yang sama).
  - Verifikasi: pytest lulus; run pendek `-Baseline -Period OOS -Symbols EURUSDc -SetInput 'InpMinConfluenceScore=60'` mencatat `InpMinConfluenceScore` 60 di `inputs_json`.
  - _Requirements: 1.1–1.4, 3.1_ · _Tests: TS-76..80_
  - Hasil (2026-10-07): Red = TS-76..80 FAIL (`verdict_v2`, opsi `rule` belum ada). Green: `component_report.py` (`pos_zero`, `verdict_v2` IS ≥ 50 / OOS ≥ 10 / REAL tidak memburuk, ringkasan `> 0 vs 0` per periode, `--rule v2|pc25`, `--sessions` menerima beberapa rentang lewat `merge_groups`); `run-ea-tests.ps1 -SetInput 'Kunci=nilai',...` (mengganti kunci preset). pytest 111/111. Verifikasi: run OOS EURUSDc dengan `-SetInput 'InpMinConfluenceScore=60'` mencatat 60 di `inputs_json` (sesi 1259; 8 trade vs 7 pada 65). Laporan v2 atas acuan v1.23 (IS/OOS, belum REAL): BREAKOUT TERBUKTI, FIB TIDAK, TRENDLINE TIDAK, RSI SAMPEL KURANG.

- [x] 2. Data REAL dan keputusan aktivasi
  - Run: `-Baseline -Period REAL` v1.24 (background).
  - Laporan: `component_report.py --rule v2` atas sesi IS + OOS v1.23 (1157–1180) dan sesi REAL.
  - Hasil: status FIB, TRENDLINE, BREAKOUT, RSI dicatat; daftar komponen TERBUKTI. Bila tidak ada, task 3 dilewati dan task 4 hanya mencatat keputusan "semua SHADOW".
  - _Requirements: 1.2, 1.3, 2.3_ · _Tests: RUN-01, RUN-02_
  - Hasil (2026-10-07): `-Baseline -Period REAL` v1.24 (sesi 1260–1271, 58 menit; XAU ditandai tick buatan sebelum 2026-08-14): 167 trade, −0,045R per trade, PF 0,91 (real ticks Jan–Okt 2026). `component_report.py --rule v2 --sessions 1157-1180,1260-1271`: BREAKOUT TERBUKTI (IS >0 189 +0,097R vs 0 304 −0,014R; OOS 14 +0,356R vs 38 −0,082R; REAL 59 +0,151R vs 108 −0,152R); FIB TIDAK (IS lebih buruk); TRENDLINE TIDAK (IS, OOS, REAL lebih buruk); RSI SAMPEL KURANG (IS 16, OOS 2). Komponen aktif: BREAKOUT saja.

- [x] 3. Sapuan ambang IS dan konfigurasi akhir
  - Run: `-Period IS` untuk `MinConfluenceScore` 55, 60, 65, 70 dengan komponen TERBUKTI ACTIVE (`-SetInput`).
  - Pemilihan: aturan design §3.3 (≥ 433 trade dan ≥ 22 per simbol; R per trade tertinggi; tie < 0,01R ke 65). Ambang dikunci.
  - Green: default input EA (mode komponen TERBUKTI = ACTIVE, `MinConfluenceScore` terpilih), `gen_presets.py` dan preset 12 simbol, README input; test default menyesuaikan (TC-xx-11, TC-SU, TestPresets, TS presets).
  - Verifikasi: unit ALL PASS, pytest lulus.
  - _Requirements: 2.1, 2.2, 3.1–3.3_ · _Tests: RUN-03, unit, TS presets_
  - Hasil (2026-10-08): Sapuan IS dengan BREAKOUT ACTIVE (`-SetInput`, sesi 1272–1319): 55% 610 trade +0,002R PF 1,01 (min 39/simbol); 60% 506 +0,001R PF 1,01 (min 33); 65% 431 −0,011R PF 0,98 (431 < 433); 70% 317 +0,030R PF 1,06 (min 18 < 22). Aturan §3.3: lolos jumlah = 55 dan 60; selisih R/trade 0,0005 < 0,01 → **60% (terdekat ke 65)**, dikunci. Temuan: semua ambang yang lolos lebih buruk dari acuan tanpa aktivasi (IS +0,029R, PF 1,06): aktivasi mengubah komposisi trade (kandidat berbreakout lebih mudah lolos, tanpa breakout lebih sulit karena maksimum 65), sehingga keunggulan breakout di mode bayangan tidak terbawa. Dibahas dengan user: lanjut prosedur. Menyimpang dari urutan task: default dan preset tidak diubah sebelum validasi; validasi memakai `-SetInput` agar tidak ada perubahan yang harus dibalik.

- [x] 4. Validasi akhir, dokumen, Fase 5 selesai
  - Run: `-Period ALL` dan `-Period REAL` konfigurasi akhir (background); PF OOS vs acuan 1,07; status PRD tahap 2–3.
  - Bila PF OOS < acuan: kembali semua SHADOW, temuan dibahas dulu.
  - Dokumen: versi 1.25; PC-27 (aturan aktivasi v2, komponen aktif, ambang, keputusan klimaks/Adaptive ditunda); `fase-5-overview.md` Done; README spec, README EA, CHANGELOG; `docs/flows/signals.md`.
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot/ea): aktivasi komponen dan ambang v1.25, Fase 5 selesai (spec 22)`; git push.
  - _Requirements: 4.1–4.3, 5.1, 6.1, 6.2_ · _Tests: RUN-04, semua_

  - Hasil (2026-10-08): Validasi akhir BREAKOUT ACTIVE + ambang 60% (`-SetInput`, sesi 1320–1355): IS 506 trade +0,001R PF 1,01; OOS 51 −0,016R PF 0,97 (< acuan 1,07); REAL 169 −0,148R PF 0,74 (acuan REAL 0,91). **Gagal (Req 4.2)**: semua komponen tetap SHADOW, ambang tetap 65%; default EA dan preset tidak berubah, versi EA tetap 1.24. Status PRD: PF IS 1,01 dan OOS 0,97 < 1,3; DD ≤ 15%. Keputusan klimaks dan Adaptive/Limit: tidak diterapkan, ditinjau bersama perbaikan strategi inti (PC-27). Dokumen: PC-27, `fase-5-overview.md` Done, README spec, README EA, CHANGELOG. Diagnosis untuk langkah berikutnya (IS/OOS/REAL): zona Fresh positif di ketiga periode, Tested rugi di OOS/REAL; sesi overlap 13–17 UTC positif di ketiganya; sepertiga loser sempat ≥ +0,5R. Regresi: build 0/0, unit 661/661, 30 skenario PASS (21:53), pytest 111/111, `schema.py check` OK.
