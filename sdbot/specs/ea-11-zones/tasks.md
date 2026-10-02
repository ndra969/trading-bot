# Implementation plan — 11 Zona Supply & Demand

Status: Done (2026-10-02)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `run-ea-tests.ps1 -Scenario SC-xx`, pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`. Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.10 di task 6.

- [x] 1. Input zona
  - Red: TC-SU-32 (suite `CoreUtils`), TC-SU-04c 28 → 33 (suite `Codec`), TC-IN-04 dengan kunci baru (suite `Presets`), pytest preset → FAIL
  - Green: tipe design §4.1, konstanta §4.2, 5 input + `InputValues` + validasi (`min < max`) + JSON sesi; `gen_presets.py` + 12 preset; tabel input README
  - _Requirements: 5.2_ · _Tests: TC-SU-32, TC-SU-04c, TC-IN-04_
  - Hasil (2026-10-02): Red = TC-SU-04c, TC-SU-32, TC-IN-04 FAIL + TS-48 FAIL. Green: `ENUM_SDB_ZONE_STATUS`, `SdbZoneParams`, `SdbZone` di Types; konstanta zona; `InpZoneMinWidthAtr` 0.3, `InpZoneMaxWidthAtr` 2.0, `InpZoneMinLegAtr` 1.5, `InpZoneLegBars` 10, `InpMaxZoneAgeBars` 100 + validasi (`IrCheckZones`, min < max); JSON sesi 33 kunci; `gen_presets.py` + 12 preset; tabel input README. Catatan: skrip Python pengukuran zona meninggalkan terminal uji terbuka (runner menolak jalan), ditutup rapi dengan CloseMainWindow. Unit 477/477, pytest 66/66, build 0/0.

- [x] 2. ATR, ID, calon zona (fungsi murni)
  - Red: TC-ZN-01..10 (suite baru `TestZones`) terhadap stub `Analysis/ZoneRules.mqh` → FAIL
  - Green: `AtrSeries`, `ZoneId`, `ZoneCandidate`
  - _Requirements: 1.1–1.5_ · _Tests: TC-ZN-01..10_
  - Hasil (2026-10-02): Red = 9 FAIL (stub). Green: `Analysis/ZoneRules.mqh`: `AtrSeries` (Wilder, benih rata-rata TR, minimal 3 x periode), `ZoneId` (`H1-<epoch>-D/S`), `ZoneCandidate` (batas dari candle swing, lebar dan gerak keluar relatif ATR di bar swing dengan batas inklusif, bar aktif = max(konfirmasi, gerak keluar tercapai), `legAtr` = gerak di bar tercapai agar stabil). Zones 10/10, unit 487/487, build 0/0.

- [x] 3. Status, peta, pemilihan, skor (fungsi murni)
  - Red: TC-ZN-11..25 → FAIL
  - Green: `ZoneStatus`, `BuildZones`, `ZonesNeeded`, `ZoneValid`, `TouchedZone`, `OppositeZone`, `ZoneScore`, `ZoneMapText`
  - _Requirements: 2.1–2.5, 3.1, 4.1–4.3_ · _Tests: TC-ZN-11..25_
  - Hasil (2026-10-02): Red = 14 FAIL (stub; TC-ZN-18 lolos kosong). Green: `ZoneStatus` (invalid lebih dulu dan final, sentuhan = masuk setelah bar sebelumnya di luar, keadaan awal dari bar aktif, kedaluwarsa > maxAge), `BuildZones`, `ZonesNeeded` (156), `ZoneValid`, `TouchedZone` (Fresh lalu terbaru), `OppositeZone` (batas dekat terdekat di depan harga), `ZoneScore`, `ZoneMapText`. Zones 25/25, unit 502/502, build 0/0.

- [x] 4. `CZoneBook` dan rangkaian App
  - Red: TC-ZB-01..04 (suite baru `TestZoneBook`, tester) → FAIL
  - Green: `Analysis/ZoneBook.mqh` (cache MTF sendiri, bangun ulang per bar, GV Used baca/tulis/bersihkan, `SetState`, jumlah per status); `CSdbApp`: member, `InitAnalysis`, `OnTick`, `EnsureState`, accessor `Zones()`
  - Regresi: `run-ea-tests.ps1 -All` ALL PASS
  - _Requirements: 3.1–3.5, 4.4_ · _Tests: TC-ZB-01..04, SC-00..12x_
  - Hasil (2026-10-02): Red = TC-ZB-01..04 FAIL (stub). Green: `Analysis/ZoneBook.mqh` (cache H1 156 bar, bangun ulang penuh per bar atau saat penanda berubah, GV `<magic>_ZU_<epoch>_<D|S>` dibaca saat `SetState`, ditulis dengan flush oleh `MarkUsed` lalu bangun ulang segera, dibersihkan bila lebih tua dari maxAge bar, log DEBUG jumlah per status, WARN data kurang); `CSdbApp`: `CZoneBook` di `InitAnalysis`, `OnTick` setelah struktur, `SetState` di `EnsureState`, accessor `Zones()`. ZoneBook 4/4, unit 506/506, `-All` 18 run PASS (4 menit 19 detik).

- [x] 5. Skenario SC-13 / SC-13x
  - Red: `SC-13_zones_eurusd` dan `SC-13x_zones_xauusd` (`.ini`/`.set`), input harness `HarnessRecordZones`, `HarnessMarkUsedAtBar`, `CheckSc13` dengan 4 assert design §6.3 → FAIL sebelum harness merekam
  - Green: perekaman sidik peta + penandaan Used di harness; pembanding `BuildZones` atas `CopyRates` berbasis waktu
  - _Requirements: 3.1, 3.3, 5.1_ · _Tests: SC-13, SC-13x_
  - Hasil (2026-10-02): Red = SC-13 FAIL 3 (perekaman mati). Green: `SC-13_zones_eurusd` dan `SC-13x_zones_xauusd`, input harness `HarnessRecordZones` dan `HarnessMarkUsedAtBar`, `CheckSc13` (sidik peta vs `BuildZones` atas `CopyRates` berbasis waktu, satu sampel per bar H1, semua status muncul, Used bertahan sesudah restart). Temuan bug: pembersihan GV Used memakai jam kalender sehingga di gap akhir pekan penanda zona yang masih aktif terhapus (zona bisa dipakai lagi); TC-ZN-26 mereproduksi, diperbaiki dengan `ZoneUsedCutoff` berbasis bar dan dipakai juga oleh pembanding. Harness kini menandai zona valid terbaru (zona tertua memang sudah kedaluwarsa saat restart). SC-13 4/4 (51 detik), SC-13x 4/4 (63 detik), unit 507/507.

- [x] 6. Versi 1.10 dan dokumen
  - Versi `1.10`; `docs/flows/` (`zones.md` baru, tick); `CHANGELOG.md`; README (input, SC-13)
  - Regresi akhir: `run-ea-tests.ps1 -All`, pytest, build 0/0
  - _Requirements: 5.2_ · _Tests: semua_
  - Hasil (2026-10-02): Versi `1.10` (EA + harness); `docs/flows/` (tick + `zones.md` baru); `CHANGELOG.md` 1.10; README (status, input harness SC-13); penyimpangan di design §7a. Regresi akhir: build 0/0, unit 507/507 (29 suite), SC-00..SC-13x PASS (20 run, 6 menit 14 detik), pytest 66/66, `schema.py check` OK.

## Validasi manual (di luar tasks)

- [ ] MC-ZN-01: EA v1.10 di chart EURUSDc H1 akun cent: log DEBUG jumlah zona per status masuk akal dibanding pembacaan visual zona di chart.
