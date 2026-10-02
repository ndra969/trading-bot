# Implementation plan — 10 Market structure dan bias HTF

Status: Done (2026-10-02)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `run-ea-tests.ps1 -Scenario SC-xx`, pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`. Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.09 di task 6.

- [x] 1. Input analisis
  - Red: TC-SU-31 (suite `CoreUtils`), TC-SU-04c 24 → 28 (suite `Codec`), TC-IN-04 dengan kunci baru (suite `Presets`), `test_presets.py` → FAIL
  - Green: tipe `ENUM_SDB_DIR` dan struct design §4.1 di `Types.mqh`; konstanta §4.2; 4 input di `Inputs.mqh` + `InputValues` + validasi + JSON sesi; `gen_presets.py` + 12 preset; tabel input README
  - _Requirements: 7.3_ · _Tests: TC-SU-31, TC-SU-04c, TC-IN-04_
  - Hasil (2026-10-02): Red = TC-SU-04c, TC-SU-31, TC-IN-04 FAIL + TS-47 FAIL. Green: `ENUM_SDB_DIR` dan struct analisis di `Types.mqh`; konstanta analisis; `InpSwingStrength`, `InpStructureLookback`, `InpEmaPeriod`, `InpEmaSlopeBars` (grup Analisis) + `InputValues` + `IrCheckAnalysis`; JSON sesi 28 kunci; `gen_presets.py` + 12 preset; tabel input README. Helper edit scratchpad kini mengikuti akhir baris file (sebagian file kerja CRLF). Unit 452/452, pytest 65/65, build 0/0.

- [x] 2. Swing dan struktur (fungsi murni)
  - Red: TC-MS-01..11 (suite baru `TestStructure`) terhadap stub `Analysis/StructureRules.mqh` → FAIL
  - Green: `IsSwingHigh`, `IsSwingLow`, `FindSwings`, `StructureOf`
  - _Requirements: 2.1–2.3, 3.1–3.3_ · _Tests: TC-MS-01..11_
  - Hasil (2026-10-02): Red = 9 FAIL (stub). Green: `Analysis/StructureRules.mqh`: `IsSwingHigh`/`IsSwingLow` (kiri ketat, kanan tidak lebih tinggi: high sama = bar lebih awal), `FindSwings`, `StructureOf` (swing aktif = terbaru yang terkonfirmasi sebelum bar, ditembus sekali; riwayat tembusan dari bar pertama agar tidak bergantung lebar jendela). TC-MS-10 di design diganti uji `lastHigh`/`lastLow` karena kasus "tembus di bar konfirmasi" tidak mungkin secara geometris. Structure 11/11, unit 463/463, build 0/0.

- [x] 3. EMA, bias, skor tren, analisis per TF (fungsi murni)
  - Red: TC-MS-12..21 → FAIL
  - Green: `EmaSeries`, `EmaDirectionOf`, `BiasOf`, `TrendScore`, `BarsNeeded`, `AnalyzeTf`
  - _Requirements: 1.1, 1.3, 4.1–4.3, 5.1, 5.2, 6.1, 6.2, 7.1_ · _Tests: TC-MS-12..21_
  - Hasil (2026-10-02): Red = 8 FAIL (stub; stub pertama crash karena EmaSeries true dengan array kosong, diganti false agar Red gagal bersih). Green: `EmaSeries` (benih SMA, minimal 3 x periode), `EmaDirectionOf`, `BiasOf`, `TrendScore`, `BarsNeeded` (default 154), `AnalyzeTf`. Structure 21/21, unit 473/473, build 0/0.

- [x] 4. `CBarCache` dan `CMarketStructure`
  - Red: TC-MSX-01..03 (suite baru `TestMarketStructure`, tester) → FAIL
  - Green: `Analysis/BarCache.mqh`, `Analysis/MarketStructure.mqh` (hitung ulang per bar baru, log perubahan bias, WARN data kurang throttled); `CSdbApp`: member, init, `OnTick`, accessor `Structure()`
  - Regresi: `run-ea-tests.ps1 -All` (unit + SC-00..11) ALL PASS
  - _Requirements: 1.1–1.4, 5.3, 5.4_ · _Tests: TC-MSX-01..03, SC-00..11_
  - Hasil (2026-10-02): Red = TC-MSX-01..03 FAIL (stub). Green: `Analysis/BarCache.mqh` (`CopyRates` mulai shift 1 hanya saat bar tertutup berubah; gagal/kurang = tidak siap, dicoba lagi), `Analysis/MarketStructure.mqh` (HTF/MTF dihitung ulang per bar baru, bias + alasan OK/STRUCTURE/EMA/CONFLICT/DATA, log INFO saat bias berubah, WARN data kurang throttled); `CSdbApp`: `InitAnalysis` dari gaya trading, `OnTick` memanggil struktur sebelum gerbang akun, accessor `Structure()`. MarketStructure 3/3 (histori H4 tester 2787 bar: jalur siap teruji), unit 476/476, `-All` 16 run PASS (2 menit 22 detik).

- [x] 5. Skenario SC-12
  - Red: `SC-12_structure_eurusd.ini/.set` dan `SC-12x_structure_xauusd.ini/.set`, input harness `HarnessRecordAnalysis`, cabang `CheckScenario("SC-12")` dengan 4 assert design §6.3 → FAIL sebelum harness merekam sampel
  - Green: perekaman `SdbAnalysisSample` di harness dan recorder; pembanding `CopyRates` berbasis waktu + `AnalyzeTf` di `OnDeinit`
  - _Requirements: 1.2, 5.1, 7.1, 7.2_ · _Tests: SC-12, SC-12x_
  - Hasil (2026-10-02): Red = SC-12 FAIL 3 (perekaman mati, 0 sampel). Green: `SC-12_structure_eurusd` (EURUSDc 2026.06.01-09.26) dan `SC-12x_structure_xauusd`, input harness `HarnessRecordAnalysis` (satu sampel per bar H4/H1 baru, lintas restart), `SdbAnalysisSample` di recorder, `CheckSc12` (pembanding `CopyRates` berbasis waktu + `AnalyzeTf`, satu sampel per bar H4, bias BULL dan BEAR, sampel sesudah restart). Temuan: histori XAUUSDc di terminal uji berakhir 2026.05.27 (0 tick Juni-September), SC-12x memakai 2026.01.05-05.20. SC-12 4/4 (51 detik), SC-12x 4/4 (65 detik).

- [x] 6. Versi 1.09 dan dokumen
  - Versi `1.09` di `SDBot.mq5` dan harness; diagram `docs/flows/` (tick + `structure.md` baru); `CHANGELOG.md`; README (input, SC-12)
  - Regresi akhir: `run-ea-tests.ps1 -All`, pytest, build 0/0
  - _Requirements: 7.3_ · _Tests: semua_
  - Hasil (2026-10-02): Versi `1.09` (EA + harness); `docs/flows/` (tick + `structure.md` baru); `CHANGELOG.md` 1.09; README (status, input harness `HarnessRecordAnalysis`, SC-12/SC-12x); penyimpangan di design §7a. Regresi akhir: build 0/0, unit 476/476 (27 suite), SC-00..SC-12x PASS (18 run, 4 menit 20 detik), pytest 65/65, `schema.py check` OK.

## Validasi manual (di luar tasks)

- [ ] MC-MS-01: EA v1.09 di chart EURUSDc akun cent: log bias muncul saat init dan saat berubah, sesuai pembacaan visual H4 (struktur + EMA 50).
- PC-15 dan PC-16 disinkronkan ke dokumen induk di akhir Fase 3 (bersama keputusan spec 11–13), atau lebih awal bila Anda minta.
