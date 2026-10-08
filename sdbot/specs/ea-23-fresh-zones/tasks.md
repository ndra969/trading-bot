# Implementation plan — 23 Entry hanya dari zona Fresh (H1)

Status: Draft
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Backtest dijalankan dengan satu agen tester di background.

- [ ] 1. Input dan gerbang zona Tested
  - Red: TC-SG-35..37, TC-SU-04c (53), TestPresets, TS-81 → FAIL.
  - Green: `InputValues.allowTestedZones`, `InpAllowTestedZones` (default true), `inputs_json`; `SdbSignalParams.allowTestedZones` + `CSdbApp`; cabang `NO_VALID_ZONE` di `EvaluateSignal`; `gen_presets.py` + preset; README.
  - _Requirements: 1.1–1.5_ · _Tests: TC-SG-35..37, TC-SU-04c, TS-81_

- [ ] 2. Skenario dan versi
  - Red: SC-22 (file skenario dibuat lebih dulu) → FAIL.
  - Green: `CheckSc22`; versi 1.25 (EA + harness); `docs/flows/signals.md` (gerbang zona Tested).
  - Verifikasi: SC-22 PASS; unit ALL PASS; compile 0/0.
  - _Requirements: 1.2, 1.5_ · _Tests: SC-22_

- [ ] 3. Pengukuran dan keputusan H1
  - Run: `-Period IS -SetInput 'InpAllowTestedZones=false'`; bandingkan dengan acuan IS 1157–1168 (trade, R per trade, PF, DD, jumlah per simbol).
  - Bila IS lolos (R per trade > acuan, ≥ 325 trade, ≥ 13 per simbol): `-Period OOS` dan `-Period REAL` dengan input sama; bandingkan dengan acuan OOS 1169–1180 dan REAL 1260–1271.
  - Keputusan Req 3.1. Bila DITERIMA: default `false`, preset, test default, README, PC-29. Bila DITOLAK: default tetap, hasil dicatat.
  - _Requirements: 2.1–2.4, 3.1–3.3_ · _Tests: RUN-01, RUN-02_

- [ ] 4. Dokumen dan regresi
  - CHANGELOG 1.25 (hasil H1), README spec, README EA (status Fase 5b).
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot/ea): zona Fresh saja (H1) v1.25 (spec 23)`; git push.
  - _Requirements: 2.4_ · _Tests: semua_
