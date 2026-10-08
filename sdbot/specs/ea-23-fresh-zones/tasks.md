# Implementation plan — 23 Entry hanya dari zona Fresh (H1)

Status: Done (2026-10-08)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Backtest dijalankan dengan satu agen tester di background.

- [x] 1. Input dan gerbang zona Tested
  - Red: TC-SG-35..37, TC-SU-04c (53), TestPresets, TS-81 → FAIL.
  - Green: `InputValues.allowTestedZones`, `InpAllowTestedZones` (default true), `inputs_json`; `SdbSignalParams.allowTestedZones` + `CSdbApp`; cabang `NO_VALID_ZONE` di `EvaluateSignal`; `gen_presets.py` + preset; README.
  - _Requirements: 1.1–1.5_ · _Tests: TC-SG-35..37, TC-SU-04c, TS-81_
  - Hasil (2026-10-08): Red build gagal + TS-81 FAIL; Green compile 0/0, unit pass=664 fail=0, pytest 114 passed; preset 12 simbol `InpAllowTestedZones=true`.

- [x] 2. Skenario dan versi
  - Red: SC-22 (file skenario dibuat lebih dulu) → FAIL.
  - Green: `CheckSc22`; versi 1.25 (EA + harness); `docs/flows/signals.md` (gerbang zona Tested).
  - Verifikasi: SC-22 PASS; unit ALL PASS; compile 0/0.
  - _Requirements: 1.2, 1.5_ · _Tests: SC-22_
  - Hasil (2026-10-08): Red SC-22 FAIL (skenario tak dikenal); Green SC-22 pass=2 fail=0; versi 1.25; `docs/flows/signals.md` node gerbang zona Tested.

- [x] 3. Pengukuran dan keputusan H1
  - Run: `-Period IS -SetInput 'InpAllowTestedZones=false'`; bandingkan dengan acuan IS 1157–1168 (trade, R per trade, PF, DD, jumlah per simbol).
  - Bila IS lolos (R per trade > acuan, ≥ 325 trade, ≥ 13 per simbol): `-Period OOS` dan `-Period REAL` dengan input sama; bandingkan dengan acuan OOS 1169–1180 dan REAL 1260–1271.
  - Keputusan Req 3.1. Bila DITERIMA: default `false`, preset, test default, README, PC-29. Bila DITOLAK: default tetap, hasil dicatat.
  - _Requirements: 2.1–2.4, 3.1–3.3_ · _Tests: RUN-01, RUN-02_
  - Hasil IS (2026-10-08, sesi 1396–1407): 341 trade (acuan 493), R/trade +0,046 (acuan +0,029), PF 1,10 (acuan 1,06), R total +15,68, DD terbesar 6,3%; min per simbol 19 (AUDUSDc). Kriteria IS LOLOS (> acuan, ≥ 325, ≥ 13/simbol). Per simbol positif: GBPUSDc +0,466, USDJPYc +0,330, XAUUSDc +0,285, AUDUSDc +0,236; negatif terbesar GBPJPYc −0,530, EURJPYc −0,188.
  - Hasil OOS (sesi 1408–1419): 37 trade (acuan 52), R/trade +0,156 (acuan +0,036), PF 1,36 (acuan 1,07). REAL (sesi 1420–1431): 116 trade (acuan 167), R/trade +0,030 (acuan −0,045), PF 1,06 (acuan 0,91).
  - Keputusan Req 3.1: **H1 DITERIMA** (lebih baik di IS, OOS, dan REAL). Default `SDB_DEF_ALLOW_TESTED_ZONES = false`, preset 12 simbol `InpAllowTestedZones=false`, TS-81 diperbarui, README, PC-29.

- [x] 4. Dokumen dan regresi
  - CHANGELOG 1.25 (hasil H1), README spec, README EA (status Fase 5b).
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot/ea): zona Fresh saja (H1) v1.25 (spec 23)`; git push.
  - _Requirements: 2.4_ · _Tests: semua_
  - Hasil (2026-10-08): build 0/0; `-All` 32 run PASS (unit 664/0, SC-00..SC-22); pytest 114 passed; `schema.py check` OK (data versi 4).
