# Implementation plan — 31 Hasil kandidat dan faktor profit

Status: Done (2026-10-11)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Terminal uji dipakai satu proses saja (backtest, ekspor bar, atau skenario), di background dengan CPU ≤ 50% core. Mulai sesudah spec 27 selesai.

- [x] 1. Telemetri harga kandidat di `context_json`
  - Red: TC-SG-39, TC-SG-40 di `TestSignalRules.mqh` → FAIL.
  - Green: lima kunci di `SignalContextJson`; versi 1.29 (EA + harness).
  - Verifikasi: unit ALL PASS, compile 0/0.
  - _Requirements: 1.1, 1.2, 1.4_ · _Tests: TC-SG-39, TC-SG-40_
  - Hasil (2026-10-10): Red unit 673/4 (TC-SG-21/22 dengan kunci baru, TC-SG-39/40); Green compile 0/0, unit pass=677 fail=0; versi 1.29 (EA + harness).

- [x] 2. Skenario SC-31 dan regresi
  - Red: file SC-31 dibuat lebih dulu → FAIL (skenario tak dikenal).
  - Green: `CheckSc31` (kunci baru tidak null, `zone_dist` di sisi SL).
  - Verifikasi: SC-31 PASS; `-All` di background semua PASS.
  - _Requirements: 1.1, 1.3_ · _Tests: SC-31, REG_
  - Hasil (2026-10-10): Red SC-31 FAIL (skenario tak dikenal); Green SC-31 pass=2 fail=0; `-All` 35 run PASS (unit 677/0, SC-00..SC-31), 38 menit.

- [x] 3. EA `ExportBars` dan runner `-ExportBars`
  - Green: `Experts/SDBot/ExportBars.mq5` (EA di Strategy Tester, status OK/PARTIAL; deviasi dari script, design §3.1); run `Kind = export` di runner; README tools.
  - Verifikasi: compile 0/0; ekspor EURUSDc 1 minggu → CSV terbaca `load_bars`, jumlah bar wajar (≈ 5 × 1.440 minus jam tutup), status OK.
  - _Requirements: 2.1_ · _Tests: RUN-02 (sebagian)_
  - Hasil (2026-10-11): compile 0/0 (6 target); `-ExportBars -Symbols EURUSDc` 2026.09.21–26: status OK 7.009 bar (16 detik), terbaca `load_bars` (point 0.00001, digits 5) dan `m15_atr`. Deviasi dari design awal (script) dicatat di design §3.1.

- [x] 4. Inti simulator: stops, exit, ATR
  - Red: TS-100..108 di `tools/tests/test_outcome_sim.py` → FAIL.
  - Green: `Candidate`, `ExitRules` (dari `inputs_json`), `build_stops`, `simulate`, `m15_atr`, `load_bars` + cache `.npz`.
  - Verifikasi: pytest PASS, ruff/black bersih.
  - _Requirements: 2.1–2.7_ · _Tests: TS-100..108_
  - Hasil (2026-10-10): pytest TS-100..108 PASS, ruff/black/mypy bersih. Catatan: test dan kode ditulis bersamaan (modul belum ada = Red trivial), tidak dijalankan Red terpisah.

- [x] 5. Kalibrasi dan CLI simulator
  - Red: TS-109, TS-112 → FAIL.
  - Green: `calibrate`, CLI `simulate`/`calibrate`, keluaran `hasil.csv`; TS-112 memakai fixture dari DB harness SC-31.
  - Verifikasi: pytest PASS.
  - _Requirements: 3.1–3.4_ · _Tests: TS-109, TS-112_
  - Hasil (2026-10-10): Red TS-109 FAIL (calibrate belum ada); TS-112 langsung PASS: `build_stops` sama dengan sl/tp 5 sinyal ACCEPTED run harness 1.29 (fixture `tests/fixtures/sc31_accepted.json`). Green: `BarStore`, `load_rows`, `calibrate`, `render_calibration`, `simulate_all`, CLI `simulate`/`calibrate` (kode keluar 3 bila kalibrasi gagal); ruff/black/mypy bersih.

- [x] 6. Laporan faktor dan tahap tolak
  - Red: TS-110, TS-111 di `tools/tests/test_factor_report.py` → FAIL.
  - Green: `factor_report.py factors` (bucket design §3.3, label konsistensi) dan `stages` (+ `--dedup-zone-day`); README tools.
  - Verifikasi: pytest PASS, ruff/black bersih.
  - _Requirements: 4.1–4.3, 5.1–5.3_ · _Tests: TS-110, TS-111_
  - Hasil (2026-10-10): Red (modul belum ada, koleksi gagal); Green pytest 152 passed, ruff/black/mypy bersih. Uji asap `factors --source trades` pada sesi 1.28 (IS 1691–1702, OOS 1715–1726, REAL 1727–1738): 523 trade, label tampil.

- [x] 7. Backtest ulang, ekspor bar, kalibrasi
  - Run: `-Baseline -Period IS`, `OOS`, `REAL` dengan 1.29 dan konfigurasi acuan 1.28 (spec 27: EMA bias 21).
  - Cek: jumlah trade dan R/trade identik dengan acuan (`trade_diff.py` acuan vs ulang: 0 baru/hilang).
  - Run: `-ExportBars` rentang IS..REAL; `outcome_sim.py calibrate` untuk IS/OOS/REAL.
  - Bila kalibrasi gagal: selidiki sebab (catat), perbaiki simulator dengan TS baru (Red dulu), ulangi.
  - _Requirements: 3.1–3.3, 6.1, 6.2_ · _Tests: RUN-01, RUN-02_
  - Hasil (2026-10-11): backtest ulang 1.29 IS (sesi 1848–1859) 356 trade +0,079R PF 1,17; OOS (1860–1871) 41 trade +0,163R PF 1,39; REAL (1872–1883) 126 trade +0,080R PF 1,17. `trade_diff` vs 1.28 (1691–1702, 1715–1726, 1727–1738): 0 baru, 0 hilang di ketiga periode (REAL +0,080 vs +0,081R: variasi eksekusi real ticks).
  - `-ExportBars` 2024.03.26–2026.10.02: 12 simbol OK, 886.519–936.056 bar M1 per simbol, 1,5 menit total.
  - Kalibrasi: IS 99,2% alasan sama, |selisih| 0,038R, R nyata +0,079 vs sim +0,059 (LOLOS); OOS 97,6%, 0,084R, +0,163 vs +0,183 (LOLOS); REAL 98,4%, 0,040R, +0,080 vs +0,117 (selisih agregat 0,036R > 0,03R, GAGAL).
  - Sebab REAL (Req 3.4, dijelaskan): 2 dari 126 trade (XAGUSDc +2,03R, USDJPYc +1,19R) tutup BE_STOP di real ticks tetapi mencapai TP di simulasi M1: urutan tick di dalam satu menit tidak terlihat dari bar M1. Tanpa keduanya selisih REAL sekitar +0,011R. Di IS simulasi sedikit pesimis (−0,020R). Simulator dipakai dengan catatan: hasil real ticks sedikit optimis; keputusan memakai konsistensi tiga periode.

- [x] 8. Laporan dan temuan
  - Run: `outcome_sim.py simulate` semua kandidat; `factor_report.py factors` (trade nyata dan kandidat) dan `stages` (dengan dan tanpa dedup) untuk IS/OOS/REAL.
  - Catat hasil di spec dan ringkasan temuan di `fase-5c-overview.md` (faktor KONSISTEN+/−, tahap tolak yang membuang kandidat bagus).
  - _Requirements: 4, 5, 6.3_ · _Tests: RUN-03_
  - Hasil (2026-10-11): `simulate` 29.652 / 3.127 / 10.330 kandidat (IS/OOS/REAL), 0 dilewati, 37 detik.
  - Tahap tolak (dedup zona per hari, R/trade hipotetis IS / OOS / REAL): ACCEPTED +0,041 / +0,180 / +0,039; NO_PA_TRIGGER −0,099 / −0,182 / −0,088; NO_VALID_ZONE (zona TESTED) −0,138 / −0,181 / −0,219; OUTSIDE_SESSION −0,135 / −0,176 / −0,082; NEWS_BLACKOUT −0,087 / −0,086 / −0,065. Gerbang utama membuang kandidat yang rugi di ketiga periode: EA tidak terlalu ketat. Tahap kecil (SCORE_TOO_LOW 4–23, SL_TOO_FAR 3–34, SPREAD_TOO_WIDE) tidak konsisten atau sampel kurang.
  - Faktor trade nyata, KONSISTEN+: tanpa trendline di zona (+0,108 / +0,400 / +0,141), pola PIN, jam 13–17 UTC (+0,199 / +0,430 / +0,295), BUY, TP ke zona lawan (+0,161 / +0,422 / +0,224), R:R 2–3, ATR tersier tengah. KONSISTEN−: trendline ≤ 0,1 ATR dari zona (+0,062 / −0,212 / −0,021), skor ≥ 85%, SELL (+0,019 / +0,100 / −0,119), TP 2R tetap (+0,036 / −0,109 / −0,031).
  - Faktor kandidat (semua tahap): trendline 3+ sentuhan di zona KONSISTEN− (−0,378 / −0,186 / −0,279); EURJPYc (−0,311 / −0,330 / −0,391) dan GBPJPYc (−0,297 / −0,276 / −0,488) KONSISTEN−: zona di dua cross JPY paling sering gagal.

- [x] 9. Dokumen dan regresi akhir
  - PC di `docs/PENDING-CHANGES.md` (skill `sdbot-docs-sync`): §Telemetri sinyal, kunci `context_json` baru.
  - CHANGELOG 1.29, README spec dan EA, `docs/flows/signals.md` bila perlu.
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot): hasil kandidat dan faktor profit v1.29 (spec 31)`.
  - _Requirements: 6.3_ · _Tests: semua, REG_
  - Hasil (2026-10-11): PC-33 (Open); CHANGELOG 1.29; README spec dan EA; temuan di `fase-5c-overview.md` §7; build 0/0 (6 target); `-All` 35 run PASS (unit 677/0); pytest 152 passed; `schema.py check` OK; ruff bersih (black: hanya `component_report.py` lama, di luar spec ini).

## Validasi manual (di luar tasks)

- Pasang 1.29 di Broker B hanya bila Fase 6 sudah memutuskan versi replay (telemetri tidak mengubah keputusan entry, tetapi versi live dan replay harus sama).
- Bila temuan menunjukkan perbaikan, buat spec perbaikan baru dengan aturan uji Fase 5b.
