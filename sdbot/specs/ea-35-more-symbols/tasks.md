# Implementation plan — 35 Simbol tambahan (H8)

Status: Done (2026-10-13)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Satu proses terminal uji, CPU ≤ 50% core.

- [x] 1. Preset kandidat
  - Red: TS-115 (29 preset, magic unik, spread maks tabel design §3), `TPR_EXPECTED` 29, `EXPECTED_MAGIC` 29 → FAIL.
  - Green: 17 simbol di `gen_presets.py` (magic 2026091913–29, kategori, spread maks); generate preset; README tabel simbol.
  - Verifikasi: pytest PASS, unit ALL PASS (TestPresets).
  - _Requirements: 1.1_ · _Tests: TS-115, TestPresets_
  - Hasil (2026-10-13): Red TS-115 + test preset lama FAIL (file belum ada); Green 17 simbol di `gen_presets.py`, 29 preset; pytest PASS; unit TestPresets 29 file PASS (685/0).

- [x] 2. Kategori aset kandidat
  - Red: kasus `AssetClassOf` (USD/USD → OTHER, ETH/USD → CRYPTO, CAD/JPY dan EUR/CAD → CROSS) dan `LegsOf` base = quote → 0, bila belum ada di suite → FAIL.
  - Green: tidak ada perubahan kode yang diharapkan; bila uji gagal, perbaiki aturan.
  - _Requirements: 1.2, 1.3_ · _Tests: TC-RK baru_
  - Hasil (2026-10-13): TC-RK-21 (ETH kripto; CADJPY/AUDCHF/EURCAD/GBPNZD cross; USD/USD OTHER batas 1) langsung PASS, tanpa perubahan kode (LegsOf base = quote sudah diuji TC lama). Red tidak terjadi karena perilaku sudah benar.

- [x] 3. Baseline kandidat dan runner `-BaselineSet`
  - Green: 17 `ea/tests/baseline/kandidat/BL-<SIMBOL>.ini`; `-BaselineSet` di runner untuk `-Baseline` dan `-ProbeHistory`; README tools.
  - Verifikasi: parse runner OK; `-Baseline -BaselineSet kandidat -Symbols US30c -FromDate 2026.09.01 -ToDate 2026.09.15` berjalan dan membuat sesi.
  - _Requirements: 1.4, 2.1_ · _Tests: RUN-00 (sebagian)_
  - Hasil (2026-10-13): 17 file `baseline/kandidat/BL-*.ini`; `-BaselineSet` di runner (folder tidak ada → keluar 2); uji asap US30c 2026.09.01–15: sesi 2141, 10 kandidat, 1 trade, 0 log ERROR.

- [x] 4. Histori dan IS kandidat
  - Run: `-ProbeHistory -BaselineSet kandidat`; catat kandidat yang historinya tidak menutup IS.
  - Run: `-Baseline -Period IS -BaselineSet kandidat` untuk kandidat yang siap.
  - Laporan per kandidat (`baseline_report`, `exit_report`); seleksi design §5.
  - _Requirements: 1.4, 2.1–2.4_ · _Tests: RUN-00, RUN-01_
  - Hasil (2026-10-13): `-ProbeHistory` 17 kandidat (6 menit); IS (sesi 2142–2157) berjalan untuk 16 kandidat, ETHUSDc gagal (tester tidak membuat sesi, histori tester ETH tidak tersedia), dicatat tidak teruji.
  - IS per kandidat (trade, R/trade, PF): GBPAUD 8, +0,547, 3,15 **lolos**; USTEC 14, +0,354, 1,98 **lolos**; NZDJPY 2, +0,273 (sampel kurang); USOIL 11, −0,013, 0,97; EURNZD 7, −0,091; US30 10, −0,109, 0,81; EURAUD 10, −0,118, 0,80; UKOIL 12, −0,140, 0,71; AUDJPY 10, −0,245, 0,65; GBPCAD 6, −0,348; US500 16, −0,352, 0,53; EURCAD 13, −0,407, 0,47; CHFJPY 10, −0,413, 0,41; GBPNZD 4, −0,647; AUDCHF 5, −0,718; CADJPY 1, −1,000.
  - Total 16 kandidat: 139 trade, −21,7R (sekitar −0,16R per trade). Strategi tidak membawa keunggulannya ke sebagian besar simbol baru.
  - Aturan §5: lolos 2 (< 3) → **H8 DITOLAK di IS**.

- [x] 5. Konfirmasi OOS dan REAL, lot minimum, keputusan
  - Bila ≥ 3 simbol lolos: `-Period OOS` dan `REAL` kelompok terpilih; aturan design §5.3.
  - Run 12 bulan `-Deposit 1801.37` risk 0,5% kelompok terpilih (Req 1.5).
  - Keputusan H8.
  - _Requirements: 1.5, 3.1–3.4_ · _Tests: RUN-02, RUN-03_
  - Hasil (2026-10-13): tidak dijalankan (H8 ditolak di IS). Preset kandidat tetap di repo, tidak dipakai live.

- [x] 6. Dokumen dan regresi akhir
  - PC (bila diterima: §Simbol); CHANGELOG; README spec dan EA; `fase-5c-overview.md` §8.
  - Regresi akhir: `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot): simbol tambahan (H8) (spec 35)`.
  - _Requirements: 3.5_ · _Tests: semua, REG_
  - Hasil (2026-10-13): tanpa PC (H8 ditolak, PRD §Simbol tidak berubah); CHANGELOG; README spec; `fase-5c-overview.md` §8 + catatan sesudah spec 34–35. `-All` 36 run PASS (unit 685/0); pytest 155 passed; `schema.py check` OK.

## Validasi manual (di luar tasks)

- Bila diterima: buat preset lokal simbol baru (`make_local_presets.py --env .env.prd --live --risk 0.5 --force`, lalu XAU/XAG 1), buka chart baru per simbol di Broker B (M15, EA SDBotLive), muat preset, cek sesi di DB.
