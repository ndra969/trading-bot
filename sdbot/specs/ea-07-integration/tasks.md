# Implementation plan — 07 Integrasi dan penutup Fase 1

Status: Done (2026-10-01)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `run-ea-tests.ps1 -Scenario SC-xx`, pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`. Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.06 di task 7.

- [x] 1. Metrik `OnTester`
  - Red: TC-IN-01..03 (suite baru `TestIntegration`) terhadap stub `App/TesterMetric.mqh`; TC-IN-06 (suite `Position`, tester) terhadap stub `TotalR`/`TradesWithR` → FAIL
  - Green: `TesterMetric`, konstanta `SDB_TESTER_MIN_TRADES`; `CClosureTracker` menjumlahkan R closure yang diketahui; `CSdbApp::OnTester`
  - _Requirements: 1.1, 1.2, 1.4_ · _Tests: TC-IN-01..03, TC-IN-06_
  - Hasil (2026-10-01): Red = 4 FAIL (stub). Green: Integration 3/3, Position 5/5 (TC-IN-06), unit 325/325, build 0/0. `CClosureTracker::NoteResult` dipanggil setiap closure; `CSdbApp::OnTester` memakai `TesterStatistics(STAT_EQUITY_DDREL_PERCENT)`.

- [x] 2. Penanda preset
  - Red: TC-IN-05 terhadap stub `PresetMatchesSymbol` → FAIL
  - Green: `PresetMatchesSymbol` di `Core/Utils.mqh`; input `InpPresetTag` (`Inputs.mqh`, `CurrentInputsJson`, `SdbAppConfig.presetTag`); WARN sekali di `CSdbApp::OnInit`; TC-SU-04c 21 → 22; tabel input README
  - _Requirements: 2.6_ · _Tests: TC-IN-05_
  - Hasil (2026-10-01): Red = TC-IN-05 FAIL (stub). Green: Integration 4/4, unit 326/326, build 0/0. Input `InpPresetTag` di grup Umum, masuk JSON sesi (TC-SU-04c 21 → 22) dan tabel input README; WARN di `CSdbApp::OnInit` setelah storage dibuka.

- [x] 3. Preset 12 simbol
  - Red: pytest `test_presets.py` TP-01..05 → FAIL (preset belum ada)
  - Green: `tools/gen-presets.py` (tabel simbol, kategori, magic PC-10, komentar referensi bot Python) → `ea/src/Presets/SDBot_DAY_<SIMBOL>c.set` (ASCII); pytest ALL PASS
  - _Requirements: 2.1–2.5_ · _Tests: TP-01..05_
  - Hasil (2026-10-01): Red = pytest 4 FAIL (TP-04 lolos kosong karena belum ada file). Green: `tools/gen_presets.py` membangkitkan 12 preset ASCII; pytest 41/41 (TP-01..05). Penyimpangan design: nama generator `gen_presets.py` (garis bawah) agar bisa di-import pytest. Nilai referensi bot Python disalin ke tabel generator (alat `sdbot/tools` hanya pustaka standar, tanpa PyYAML).

- [x] 4. Validasi preset dengan aturan EA
  - Red: suite `TestPresets` TC-IN-04 tanpa salinan preset → FAIL "preset tidak ditemukan"
  - Green: runner menyalin preset ke `Common\Files\sdbot_presets\` sebelum unit run dan menghapusnya sesudahnya; suite membaca kunci=nilai ke `InputValues` dan memanggil `ValidateInputValues`
  - _Requirements: 2.5_ · _Tests: TC-IN-04_
  - Hasil (2026-10-01): Red = TC-IN-04 FAIL "0 file" (belum disalin). Green: runner menyalin `ea/src/Presets/*.set` (kecuali `*.local.set`) ke `Common\Files\sdbot_presets\` sebelum unit run dan menghapusnya di `finally`; Presets 1/1 (12 file lolos `ValidateInputValues`, semua kunci adalah nama input EA), unit 327/327. Tambahan: suite juga menolak kunci yang bukan input EA (salah ketik).

- [x] 5. Query analisis dasar
  - Red: pytest `test_queries.py` TQ-01..08 → FAIL (query dan data v2 belum ada)
  - Green: `seed_sample.sql` blok `-- @version 2` (sesi tester + trade + closure BE_STOP/SL + operasi saldo), `schema.py build`; `tools/queries/*.sql` (8 file, join `login + run_key + position_id`); `test_seed_blocks_are_split_per_version` → `{1, 2}`
  - _Requirements: 3.1–3.3_ · _Tests: TQ-01..08_
  - Hasil (2026-10-01): Red = pytest 10 FAIL (query dan data v2 belum ada). Green: 8 query di `tools/queries/` (join posisi selalu `login + run_key + position_id`), blok seed `-- @version 2` (dua run backtest dengan position_id kecil yang sama), `schema.py build`; pytest 52/52 (TQ-01..08 + pemisahan run + join run_key). Temuan di alat spec 03: `schema.py write_fixture` menerapkan semua blok seed walau migrasinya belum ada; kini hanya blok <= versi migrasi terakhir. Fixture uji `project` (proyek tiruan dengan migrasi 0001) kini hanya membawa blok seed v1. `black` merapikan 3 file Python baru.

- [x] 6. Runner: optimasi dan SC-09
  - Red: `SC-09_optimization.ini/.set` dijalankan sebelum runner mendukung optimasi → FAIL (tidak ada file hasil)
  - Green: `run-ea-tests.ps1` mendeteksi `Optimization=1`: cek ukuran dan `LastWriteTime` `sdbot_tester.sqlite` sebelum/sesudah, laporan XML berisi ≥ 2 pass dengan hasil custom terisi, hasil PASS/FAIL per pemeriksaan; durasi total di ringkasan `-All`
  - _Requirements: 1.3, 4.1–4.3_ · _Tests: SC-09, REG_
  - Hasil (2026-10-01): Red = SC-09 FAIL (runner memperlakukannya sebagai skenario biasa; harness: "tidak dikenal"). Green: runner mendeteksi `Optimization=1`, menambah `Report=sdbot_opt_<runId>`, memeriksa stempel `sdbot_tester.sqlite` (ukuran + waktu tulis) sebelum/sesudah, membaca laporan XML (kolom `Result`), lalu menghapus laporan dan menyalinnya ke `.tmp`. Run pertama lolos tetapi kedua pass bernilai 0 (trade < 30, sesuai aturan metrik) sehingga tidak membuktikan metrik dihitung; SC-09 diubah (entry tiap 2 bar, SL 100/150, TP 150) dan pemeriksaan `-metric` mewajibkan >= 1 pass dengan hasil != 0. Akhir: SC-09 4/4 (2 pass, Result 0 dan -0.01, DB tidak berubah). `-All` mencetak durasi total. `CheckScenario` SC-09 hanya INFO (harness tidak menilai optimasi).

- [x] 7. Versi 1.06 dan dokumen repo
  - `SDBot.mq5` dan harness `1.06`
  - `ea/tests/manual-checklist.md`, `sdbot/docs/flows/{init,tick,timer,order-execution,risk-monitor,closure}.md`, `sdbot/CHANGELOG.md`, `sdbot/README.md` (status v1.06, preset, query, SC-09)
  - Verifikasi: build 0/0, `run-ea-tests.ps1 -All` PASS dengan durasi < 30 menit, pytest PASS, `schema.py check` OK
  - _Requirements: 4.1, 4.3, 5.1–5.3, 5.5_ · _Tests: REG_
  - Hasil (2026-10-01): `SDBot.mq5` dan harness v1.06; `ea/tests/manual-checklist.md` (MC spec 01–07 + uji fungsi wajib PRD, dipisah Fase 1 / Fase 3), `docs/flows/` (README + init, tick, timer, order-execution, risk-monitor, closure), `CHANGELOG.md` (EA 1.00–1.06), README (status Fase 1 selesai, preset/generator, query, SC-09, tautan checklist dan alur). Verifikasi: build 0/0 (4 target), `run-ea-tests.ps1 -All` exit 0 (unit 327/327 di 21 suite, 13 skenario PASS) dengan durasi total 1:55 (< 30 menit), pytest 52/52, `schema.py check` OK.

- [x] 8. Sinkron dokumen induk
  - Skill `sdbot-docs-sync`: terapkan PC-01..PC-12 ke PRD-EA, PRD-Backoffice, dan RULES di claude.ai, ekspor ulang salinan `sdbot/docs/`, pindahkan entri ke "Done"
  - _Requirements: 5.4_
  - Hasil (2026-10-01): PC-01..PC-12 diterapkan ke dokumen induk claude.ai (PRD-EA rev 40, PRD-Backoffice rev 14, RULES rev 19), salinan `sdbot/docs/` diekspor ulang (diff hanya perubahan PC + header), semua entri dipindah ke Done.

## Validasi manual (di luar tasks)

- [ ] Checklist `ea/tests/manual-checklist.md` (MC spec 01–06 dan skenario uji fungsi wajib PRD) yang bisa dicek di Fase 1; item Fase 3 tetap terbuka
- [ ] Preset dimuat lewat dialog Inputs → Load MT5 di satu chart akun cent (encoding ASCII terbaca)
