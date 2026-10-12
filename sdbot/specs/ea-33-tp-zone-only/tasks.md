# Implementation plan — 33 Entry hanya dengan TP ke zona lawan (H6)

Status: Done (2026-10-12)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Backtest dan regresi di background, satu proses terminal uji, CPU ≤ 50% core.

- [x] 1. Input dan cabang `BuildStops`
  - Red: TC-SG-41..43, TC-SU-04c (57), TestPresets, TS-113 → FAIL.
  - Green: `SdbSignalParams.requireOppositeZone`, konstanta default, `InputValues`, `InpRequireOppositeZone` + `inputs_json`, cabang di `BuildStops`, `CSdbApp`, `SgP0`/`TestSignalEngine`; `gen_presets.py` + 12 preset; README tabel konfigurasi; `docs/flows/signals.md`.
  - Verifikasi: unit ALL PASS, compile 0/0, pytest PASS.
  - _Requirements: 1.1–1.5_ · _Tests: TC-SG-41..43, TC-SU-04c, TestPresets, TS-113_
  - Hasil (2026-10-12): Red build 5 error + TS-113 FAIL; Green compile 0/0, unit pass=680 fail=0 (TC-SG-41 sempat gagal karena test membandingkan string hasil `ZeroMemory` (NULL) dengan ""; diperbaiki di test dengan `StringLen`), pytest PASS; preset 12 simbol `InpRequireOppositeZone=false`; README dan `docs/flows/signals.md`.

- [x] 2. Versi dan regresi default
  - Green: versi 1.30 (EA + harness).
  - Verifikasi: `-All` di background semua PASS (default identik).
  - _Requirements: 1.4, 1.6_ · _Tests: REG_
  - Hasil (2026-10-12): versi 1.30 (EA + harness); `-All` 35 run PASS (unit 680/0), 40 menit.

- [x] 3. Pengukuran IS
  - Run: `-Baseline -Period IS -SetInput 'InpRequireOppositeZone=true'`.
  - Laporan: `baseline_report.py`, `exit_report.py`, `trade_diff.py` vs acuan 1848–1859; aturan design §5.
  - _Requirements: 2.1–2.4_ · _Tests: RUN-01_
  - Hasil (2026-10-12): `InpRequireOppositeZone=true` (sesi 1968–1979) 121 trade, +0,164R, PF 1,39, total +19,8R, DD 6,55R; acuan (1848–1859) 356 trade, +0,079R, PF 1,17, +28,0R, DD 9,06R. `trade_diff`: 121 sama, 0 baru, 235 hilang (+0,036R): tepat trade TP 2R acuan. Per simbol 3–17 trade (XAGUSDc 3).
  - Aturan §5: R per trade dan ≥ 100 trade lolos; ≥ 5 per simbol GAGAL karena XAGUSDc 3 trade.
  - Keputusan user 2026-10-12: XAGUSDc dikecualikan dari syarat per simbol (simbol jarang trade, tidak untung di acuan), lanjut OOS + REAL dengan aturan diterima yang sama. Dicatat sebagai PC bersama kriteria H6. Data OOS/REAL belum dipakai untuk memilih.

- [x] 4. Konfirmasi OOS dan REAL, keputusan
  - Bila lolos IS: `-Period OOS` dan `REAL` dengan input sama; bandingkan dengan 1860–1871 dan 1872–1883.
  - Keputusan design §5. Bila DITERIMA: default `true`, preset, TS-113 (Red dulu), versi 1.31. Bila DITOLAK: default `false`, versi 1.30.
  - _Requirements: 3.1–3.4_ · _Tests: RUN-02, TS-113_
  - Hasil (2026-10-12): OOS (sesi 1980–1991) 21 trade, +0,421R, PF 2,47, total +8,84R, DD 4,34R (acuan 41, +0,163R, 1,39); REAL (1992–2003) 55 trade, +0,224R, PF 1,58, total +12,32R, DD 5,03R (acuan 126, +0,080R, 1,17, +10,1R, DD 7,34R).
  - Run REAL sudah memakai build berisi perbaikan rugi SL dari tick value (commit f5512ca); jalur cadangan tidak pernah aktif di tester (0 peringatan di log agen).
  - Keputusan §5: **H6 DITERIMA** (OOS dan REAL R/trade ≥ acuan, total R REAL +12,3 ≥ +10,1). Default `SDB_DEF_REQUIRE_OPPOSITE_ZONE` true, preset 12 simbol, TS-113 (Red: FAIL dengan preset false; Green sesudah preset), versi 1.31.

- [x] 5. Dokumen dan regresi akhir
  - PC di `docs/PENDING-CHANGES.md`: kriteria jumlah trade H6 dan, bila diterima, §Aturan entry + §Parameter input.
  - CHANGELOG, README spec dan EA, `fase-5c-overview.md` (hasil H6).
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot/ea): syarat zona lawan (H6) v1.3x (spec 33)`.
  - _Requirements: 3.5_ · _Tests: semua, REG_
  - Hasil (2026-10-12): PC-34 (Open); CHANGELOG 1.30 dan 1.31; README spec dan EA; hasil di `fase-5c-overview.md` §8. `-All` dengan default baru: 33 PASS, SC-15 dan SC-23 gagal karena trade di periode pendek hilang (prasyarat skenario, bukan fitur yang diuji); kedua `.set` mengunci `InpRequireOppositeZone=false`, lalu SC-15 dan SC-23 PASS. Unit 681/0, pytest 153 passed, `schema.py check` OK.

## Validasi manual (di luar tasks)

- Bila H6 diterima: pasang 1.31 di Broker B (timpa ex5, muat ulang preset lokal dengan `make_local_presets.py --env .env.prd --live --risk 0.5 --force`, lalu XAU/XAG risk 1), cek `sessions.ea_version` dan `InpRequireOppositeZone` di DB live.
