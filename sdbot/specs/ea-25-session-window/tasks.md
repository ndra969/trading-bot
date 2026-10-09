# Implementation plan — 25 Jendela entry dipersempit (H3)

Status: Done (2026-10-09)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Backtest dijalankan dengan satu agen tester di background.

- [x] 1. Input dan aturan jam akhir
  - Red: TC-FL-09..12, TC-SG-38, TC-SU-04c (54), TestPresets, TS-89 → FAIL.
  - Green: konstanta, `InputValues.sessionEndHourUtc` + validasi, `InpSessionEndHourUtc` (default 22) + `inputs_json`; `SdbSessionParams.endHourUtc`, `SessionAllowedAt`; fakta `sessionInWindow`/`sessionEndHour`, engine, detail `jam_akhir` di `EvaluateSignal`; `CSdbApp`; `gen_presets.py` + preset; README.
  - Verifikasi: unit ALL PASS, compile 0/0, pytest PASS.
  - _Requirements: 1.1–1.5, 1.7_ · _Tests: TC-FL-09..12, TC-SG-38, TC-SU-04c, TS-89_
  - Hasil (2026-10-09): Red build 48 error + TS-89 FAIL; Green compile 0/0, unit pass=669 fail=0, pytest 119 passed; preset 12 simbol `InpSessionEndHourUtc=22`. `TseSessions()` (TestSignalEngine) diberi `endHourUtc` default agar uji engine deterministik.

- [x] 2. Skenario dan versi
  - Red: SC-23 (file skenario dibuat lebih dulu) → FAIL.
  - Green: `CheckSc23`; versi 1.26 (EA + harness); `docs/flows/signals.md` (node sesi + jam akhir).
  - Verifikasi: SC-23 PASS; SC-15 PASS; unit ALL PASS; compile 0/0.
  - _Requirements: 1.2, 1.6_ · _Tests: SC-23_
  - Hasil (2026-10-09): Red SC-23 FAIL (skenario tak dikenal); Green SC-23 pass=2 fail=0; SC-15 PASS; unit pass=669 fail=0; compile 0/0; versi 1.26; `docs/flows/signals.md` node sesi + jam akhir.

- [x] 3. Pengukuran IS dan pilihan varian
  - Run: `-Baseline -Period IS -SetInput 'InpSessionEndHourUtc=17'` lalu `=19`.
  - Laporan: `baseline_report.py` (PF, DD, per simbol) dan `exit_report.py` (acuan 1396–1407 + kedua varian).
  - Aturan pilih design §5 (PC-30); catat hasil dan varian terpilih (atau H3 ditolak).
  - _Requirements: 2.1–2.4_ · _Tests: RUN-01_
  - Hasil (2026-10-09): jam akhir 17 (sesi 1498–1509) 280 trade, +0,068R, PF 1,15, DD terbesar 5,8%, min per simbol 14 (AUDUSDc); jam akhir 19 (1510–1521) 318 trade, +0,066R, PF 1,14, DD 6,3%, min 18 (AUDUSDc); acuan 22 (1396–1407) 341 trade, +0,046R, PF 1,10.
  - Alasan tutup (n × R): acuan / 17 / 19: SL 166 / 132 / 152 (−1,00); BE_STOP 33 / 31 / 32 (+0,26); TRAIL_STOP 97 / 80 / 90 (+0,89–0,90); TP 45 / 37 / 44 (+1,93–1,96). Rata-rata R per alasan tidak berubah: perbaikan datang dari membuang trade jam 17–22, bukan dari exit.
  - Pilihan (design §5): keduanya lolos (R > +0,046, ≥ 260 trade, ≥ 13 per simbol); selisih 0,002R < 0,01R → **jam akhir 19**.

- [x] 4. Konfirmasi OOS dan REAL, keputusan
  - Bila ada varian terpilih: `-Period OOS` dan `-Period REAL` dengan input yang sama; bandingkan dengan acuan 1408–1419 dan 1420–1431.
  - Keputusan Req 3.2. Bila DITERIMA: `SDB_DEF_SESSION_END_HOUR`, preset, TS-89 (Red dulu: nilai baru), versi 1.27, README, PC-31. Bila DITOLAK: default 22, versi tetap 1.26, hasil dicatat.
  - _Requirements: 3.1–3.5_ · _Tests: RUN-02, TS-89_
  - Hasil (2026-10-09): jam akhir 19, OOS (sesi 1522–1533) 35 trade, +0,125R, PF 1,27 (acuan 37, +0,156R, 1,36); REAL (1534–1545) 107 trade, +0,064R, PF 1,14 (acuan 116, +0,030R, 1,06).
  - OOS lebih buruk karena dua trade acuan sesudah 19:00 yang menang terpotong (AUDUSDc 2026-07-21 20:30 +0,74R; USDCADc 2026-08-23 21:30 +0,67R). Sampel OOS kecil, tetapi aturan Req 3.2 mewajibkan OOS dan REAL ≥ acuan.
  - Keputusan Req 3.2/3.4: **H3 DITOLAK**. Default `InpSessionEndHourUtc` tetap 22, preset tetap 22 (TS-89 tetap), versi tetap 1.26 (input untuk eksperimen); PC-31 hanya mencatat input baru di PRD.

- [x] 5. Dokumen dan regresi
  - CHANGELOG (1.26, dan 1.27 bila diterima), README spec, README EA (status Fase 5b), ringkasan Fase 5b di overview.
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot/ea): jam akhir entry (H3) v1.2x (spec 25)`; git push.
  - _Requirements: 3.3–3.5_ · _Tests: semua, REG_
  - Hasil (2026-10-09): CHANGELOG 1.26, README spec dan EA, ringkasan Fase 5b (`fase-5b-overview.md` §7); build 0/0; `-All` 33 run PASS (unit 669/0, SC-00..SC-23); pytest 119 passed; `schema.py check` OK.
