# Implementation plan — 41 USTEC sebagai simbol ke-13 (H15)

Status: Done (2026-10-19)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

Tanpa kode. Backtest satu proses terminal uji BelowNormal, CPU ≤ 50% core. Commit sekali di akhir spec, lalu push.

- [x] 1. IS dengan konfigurasi live dan uji saldo kecil
  - Run: RUN-01 (`-Baseline -BaselineSet kandidat -Symbols USTECc -Period IS -SkipBuild`) dan RUN-03 (`… -Deposit 1777.78 -SetInput InpRiskPerTradePct=1`).
  - Laporan: `exit_report`, tahap tolak, query lot (design §3); aturan Req 2.1 dan 2.4.
  - _Requirements: 1.1–1.4, 2.1, 2.4_ · _Tests: RUN-01, RUN-03_
  - Hasil (2026-10-19): RUN-01 (sesi 2619, saldo baseline ±1.801 USC, risk 0,5%): 14 trade, 0,5/bulan, +0,297R, total +4,16R, PF 1,69, DD 2,0R (IS lama 1.32: +0,354R). Alasan tutup: SL 6, BE 1, trailing 6, TP 1. **Lolos Req 2.1.**
  - RUN-03 (sesi 2620, saldo 1.777,78, risk 1%): 14 dari 14 kandidat tahap lot terbuka, 0 tolak lot/risk/OTHER, lot 10,57–64,41. **Lolos Req 2.4.** Tahap tolak teratas IS: zona tidak valid, tanpa PA.

- [x] 2. Konfirmasi OOS dan REAL (hanya bila task 1 lolos IS)
  - Run: RUN-02 `-Period OOS` dan `-Period REAL`; aturan Req 2.2, 2.3.
  - _Requirements: 2.2, 2.3_ · _Tests: RUN-02_
  - Hasil (2026-10-19): OOS (sesi 2621) 2 trade, +13,06R, DD 0; REAL real ticks (sesi 2622) 4 trade, +12,38R, PF 13,7, DD 1,0R. Gabungan 6 trade +4,24R per trade. **Lolos Req 2.2 dan 2.3.**
  - Catatan kekuatan bukti: REAL tumpang tindih dengan IS (2 trade April 2026 sama) dan OOS (2 trade September sama), jadi hanya 2 trade yang benar-benar di luar IS. OOS didominasi 1 trade +9,5R (2026-09-16, TP zona lawan 11,9R); tanpa trade itu OOS +3,5R.

- [x] 3. Keputusan dan dokumen
  - Keputusan H15 di tasks; `fase-5c-overview.md` §8; CHANGELOG; README spec. Bila lolos: kandidat chart ke-13 dan PC §Simbol menunggu persetujuan user.
  - Tandai Done; commit `docs(sdbot): uji USTEC simbol ke-13 (H15) (spec 41)`; push.
  - _Requirements: 2.5, 2.6_
  - Hasil (2026-10-19): **H15 LOLOS** semua aturan. USTECc (magic 2026091914, preset spec 35) menjadi kandidat chart ke-13; pemasangan live dan PC §Simbol menunggu persetujuan user. Perkiraan tambahan ±0,5 trade per bulan.
