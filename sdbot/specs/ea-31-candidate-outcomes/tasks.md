# Implementation plan — 31 Hasil kandidat dan faktor profit

Status: Approved (2026-10-09), menunggu spec 27 selesai
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Terminal uji dipakai satu proses saja (backtest, ekspor bar, atau skenario), di background dengan CPU ≤ 50% core. Mulai sesudah spec 27 selesai.

- [ ] 1. Telemetri harga kandidat di `context_json`
  - Red: TC-SG-39, TC-SG-40 di `TestSignalRules.mqh` → FAIL.
  - Green: lima kunci di `SignalContextJson`; versi 1.29 (EA + harness).
  - Verifikasi: unit ALL PASS, compile 0/0.
  - _Requirements: 1.1, 1.2, 1.4_ · _Tests: TC-SG-39, TC-SG-40_

- [ ] 2. Skenario SC-31 dan regresi
  - Red: file SC-31 dibuat lebih dulu → FAIL (skenario tak dikenal).
  - Green: `CheckSc31` (kunci baru tidak null, `zone_dist` di sisi SL).
  - Verifikasi: SC-31 PASS; `-All` di background semua PASS.
  - _Requirements: 1.1, 1.3_ · _Tests: SC-31, REG_

- [ ] 3. Script `ExportBars` dan runner `-ExportBars`
  - Green: `Scripts/SDBot/ExportBars.mq5` (potongan 100.000 bar, file status OK/PARTIAL/MISSING); `Invoke-ExportBars` + cek terminal uji sedang dipakai; README tools; `.gitignore` untuk `sdbot_bars`.
  - Verifikasi: compile 0/0; ekspor EURUSDc 1 minggu → CSV dengan jumlah bar sama dengan `CopyRates`, status OK.
  - _Requirements: 2.1_ · _Tests: RUN-02 (sebagian)_

- [ ] 4. Inti simulator: stops, exit, ATR
  - Red: TS-100..108 di `tools/tests/test_outcome_sim.py` → FAIL.
  - Green: `Candidate`, `ExitRules` (dari `inputs_json`), `build_stops`, `simulate`, `m15_atr`, `load_bars` + cache `.npz`.
  - Verifikasi: pytest PASS, ruff/black bersih.
  - _Requirements: 2.1–2.7_ · _Tests: TS-100..108_

- [ ] 5. Kalibrasi dan CLI simulator
  - Red: TS-109, TS-112 → FAIL.
  - Green: `calibrate`, CLI `simulate`/`calibrate`, keluaran `hasil.csv`; TS-112 memakai fixture dari DB harness SC-31.
  - Verifikasi: pytest PASS.
  - _Requirements: 3.1–3.4_ · _Tests: TS-109, TS-112_

- [ ] 6. Laporan faktor dan tahap tolak
  - Red: TS-110, TS-111 di `tools/tests/test_factor_report.py` → FAIL.
  - Green: `factor_report.py factors` (bucket design §3.3, label konsistensi) dan `stages` (+ `--dedup-zone-day`); README tools.
  - Verifikasi: pytest PASS, ruff/black bersih.
  - _Requirements: 4.1–4.3, 5.1–5.3_ · _Tests: TS-110, TS-111_

- [ ] 7. Backtest ulang, ekspor bar, kalibrasi
  - Run: `-Baseline -Period IS`, `OOS`, `REAL` dengan 1.29 dan konfigurasi acuan 1.28 (spec 27: EMA bias 21).
  - Cek: jumlah trade dan R/trade identik dengan acuan (`trade_diff.py` acuan vs ulang: 0 baru/hilang).
  - Run: `-ExportBars` rentang IS..REAL; `outcome_sim.py calibrate` untuk IS/OOS/REAL.
  - Bila kalibrasi gagal: selidiki sebab (catat), perbaiki simulator dengan TS baru (Red dulu), ulangi.
  - _Requirements: 3.1–3.3, 6.1, 6.2_ · _Tests: RUN-01, RUN-02_

- [ ] 8. Laporan dan temuan
  - Run: `outcome_sim.py simulate` semua kandidat; `factor_report.py factors` (trade nyata dan kandidat) dan `stages` (dengan dan tanpa dedup) untuk IS/OOS/REAL.
  - Catat hasil di spec dan ringkasan temuan di `fase-5c-overview.md` (faktor KONSISTEN+/−, tahap tolak yang membuang kandidat bagus).
  - _Requirements: 4, 5, 6.3_ · _Tests: RUN-03_

- [ ] 9. Dokumen dan regresi akhir
  - PC di `docs/PENDING-CHANGES.md` (skill `sdbot-docs-sync`): §Telemetri sinyal, kunci `context_json` baru.
  - CHANGELOG 1.29, README spec dan EA, `docs/flows/signals.md` bila perlu.
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot): hasil kandidat dan faktor profit v1.29 (spec 31)`.
  - _Requirements: 6.3_ · _Tests: semua, REG_

## Validasi manual (di luar tasks)

- Pasang 1.29 di Broker B hanya bila Fase 6 sudah memutuskan versi replay (telemetri tidak mengubah keputusan entry, tetapi versi live dan replay harus sama).
- Bila temuan menunjukkan perbaikan, buat spec perbaikan baru dengan aturan uji Fase 5b.
