# Implementation plan — 16 Filter berita

Status: Done (2026-10-05)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `-Scenario SC-xx`;
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.17 di task 6 (Fase 4 selesai). Backtest dasar dijalankan dengan satu agen tester (beban CPU rendah).

- [x] 1. Aturan berita (fungsi murni), enum, dan input
  - Red: TC-NW-01..11 (suite baru `TestNewsRules`) terhadap stub `Filters/NewsRules.mqh` → FAIL; TS-57, TS-58 → FAIL.
  - Green:
    - fungsi `NewsRules`;
    - `enums.md` + `NEWS_FILTER_OFF` + `schema.py build`;
    - 4 input (`InpNewsFilter`, `InpNewsHighMinutes`, `InpNewsMediumMinutes`, `InpNewsCsvFile`), validasi, `inputs_json`;
    - preset 12 simbol, tabel input README; TC-SU-04c dan TestPresets menyesuaikan.
  - _Requirements: 1.1–1.3, 2.2, 4.1, 4.2, 5.1_ · _Tests: TC-NW-01..11, TS-57, TS-58_
  - Hasil (2026-10-05): Red = TS-57, TS-58 FAIL; TC-NW-01..11 gagal compile. Green: `Filters/NewsRules.mqh` (`ImpactFromText`, `ImpactText`, `ParseCalendarLine`, `CalendarLine`, `EventForSymbol`, `WindowMinutes`, `MinutesToEvent`, `FindBlackout`, `NearestUpcoming`, `BlackoutDetail`); `enums.md` `alert_type` + `NEWS_FILTER_OFF` + `schema.py build` (data v3); 4 input (`InpNewsFilter`, `InpNewsHighMinutes`, `InpNewsMediumMinutes`, `InpNewsCsvFile`), validasi, `inputs_json` (48); preset 12 simbol; README; TC-SU-04c dan TestPresets diperbarui. Unit 596/596, pytest lulus.

- [x] 2. Tahap tolak di aturan sinyal
  - Red: TC-SG-27 dan JSON baru TC-SG-21/22 → FAIL.
  - Green: `SdbSignalFacts` (`newsBlocked`, `newsDetail`, `newsStatus`, `newsNext`); `EvaluateSignal` (`NEWS_BLACKOUT` setelah pre-filter risiko); `SignalContextJson` (`news`, `news_next`).
  - _Requirements: 1.4, 3.3, 4.1_ · _Tests: TC-SG-21, 22, 27_
  - Hasil (2026-10-05): Red = TC-SG-27 dan JSON baru TC-SG-21/22 gagal compile. Green: `SdbSignalFacts` (`newsBlocked`, `newsDetail`, `newsStatus`, `newsNext`); `EvaluateSignal` menolak `NEWS_BLACKOUT` setelah pre-filter risiko dan sebelum sesi; `SignalContextJson` + `news`, `news_next` (null bila kosong). SignalRules 26/26, unit 597/597.

- [x] 3. `CNewsFilter` dan rangkaian App
  - Green:
    - `Filters/NewsFilter.mqh` (live: kalender MT5 + cache 15 menit; tester: CSV; status dan alert sekali);
    - `CSignalEngine` memakai filter; `CSdbApp` membuat dan meneruskannya.
  - Regresi: `-All` ALL PASS. Skenario lama di tester tanpa CSV → filter `OFF` + satu alert; skenario yang menghitung alert disesuaikan bila perlu, dengan alasan dicatat.
  - _Requirements: 1.5, 2.1–2.3, 3.1, 3.2_ · _Tests: SC-00..16_
  - Hasil (2026-10-05): Green: `Filters/NewsFilter.mqh` (`CNewsFilter`: live `CalendarValueHistory` + `CalendarEventById`, jendela -1..+2 hari, muat ulang 15 menit / 60 detik setelah gagal; tester CSV FILE_COMMON sekali saat init, baris rusak dihitung; status ON/OFF/DISABLED; alert `NEWS_FILTER_OFF` High sekali per sesi lewat event sink); `CSignalEngine` mengisi fakta berita; `CSdbApp` membuat filter hanya bila pipeline aktif (skenario notifier lama tidak mendapat alert baru). Build pertama gagal (`ArrayCopy` tidak bisa untuk struct berisi string) -> salin per elemen. Unit 597/597; `-All` 25 run PASS (SC-14..16: filter OFF tanpa CSV).

- [x] 4. Skenario berita
  - Red: fixture `ea/tests/fixtures/common/sdbot_calendar_sc17.csv` + TS-59; runner menyalin fixture ke Common\Files; cabang `CheckScenario` SC-17 / SC-17b + `.ini`/`.set` → jalankan.
  - Green: perbaikan dari temuan skenario (bug dimulai dari test case).
  - _Requirements: 2.2, 3.1, 6.2, 6.3_ · _Tests: SC-17, SC-17b, TS-59_
  - Hasil (2026-10-05): Fixture `ea/tests/fixtures/common/sdbot_calendar_sc17.csv` (170 event: USD HIGH 12:30, EUR MEDIUM 09:00 tiap hari kerja 2026-06-01..09-26) + TS-59; runner menyalin `tests/fixtures/common/*` ke Common\Files sebelum skenario; SC-17 (InpNewsCsvFile fixture) dan SC-17b (CSV tidak ada) + `CheckSc17/17b`. SC-17: NEWS_BLACKOUT hanya di jendela dengan detail event, 0 ACCEPTED di jendela, konteks news ON, ada trade. SC-17b: ada trade, tepat 1 alert NEWS_FILTER_OFF, konteks OFF, 0 NEWS_BLACKOUT. Keduanya PASS pertama kali. pytest 88 lulus.

- [x] 5. ExportCalendar dan backtest dasar
  - Green:
    - `Scripts/SDBot/ExportCalendar.mq5`;
    - runner `-ExportCalendar` (terminal uji, startup script, cek CSV).
  - Verifikasi:
    - `-ExportCalendar` menghasilkan CSV dengan jumlah event per mata uang × dampak tercatat di baris Hasil;
    - `-Baseline` 12 simbol dengan semua filter, dibandingkan dengan backtest v1.15.
    - Bila terminal uji tidak tersambung atau kriteria PC-22 gagal, temuan dibahas dulu.
  - _Requirements: 5.1–5.3, 6.4_ · _Tests: backtest dasar_
  - Hasil (2026-10-05): `ExportCalendar.mq5` + runner `-ExportCalendar` (startup script di terminal uji, tunggu sinkron kalender sampai 120 detik bila err 5401, file status `sdbot_calendar_status.txt`). Ekspor: 18.787 event 2025.01.01..2026.10.12; USD high 872 / medium 2.283 / low 3.329; EUR 265/2.047/3.283; GBP 135/852/656; JPY 105/645/1.278; CHF 17/109/360; AUD 15/398/423; CAD 21/436/492; NZD 25/159/582. Backtest dasar pertama dengan 30/10: 187 trade (< 200, PC-22 GAGAL); dari 241 trade v1.15, 53 terblokir berita (30 untung, bersih +1,24R; 41 dari USD HIGH termasuk rilis kecil). Dibahas dengan user: default diubah ke HIGH ±15, MEDIUM 0 (PC-24; SC-17 tetap 30/10 eksplisit). Backtest ulang: **LOLOS**, 215 trade (11–31 per simbol), 0 log ERROR/CRITICAL; vs v1.15 (sesi 634–645): trade 241 → 215, expectancy +0,035R → +0,058R, total R +8,42 → +12,55.

- [x] 6. Versi 1.17 dan dokumen (Fase 4 selesai)
  - Versi `1.17` (EA + harness); `docs/flows/signals.md` (tahap berita) dan `docs/flows/news.md` baru; CHANGELOG; README (status Fase 4 selesai, alat `-ExportCalendar`, input); `fase-4-overview.md` Done; `manual-checklist.md` (MC-FL-01, MC-EXP-01, MC-NW-01..02).
  - Regresi akhir: build 0/0, `-All`, pytest, `schema.py check`.
  - _Requirements: 6.5_ · _Tests: semua_
  - Hasil (2026-10-05): versi 1.17 (EA + harness); `docs/flows/signals.md` (tahap berita) dan `docs/flows/news.md` baru, indeks flows v1.17; CHANGELOG 1.17; README (Fase 4 selesai, `-ExportCalendar`, default 15/0); `fase-4-overview.md` Done; `manual-checklist.md` MC-FL-01, MC-EXP-01, MC-NW-01..02. Regresi: build 0/0 (5 target); unit 597/597; 26 skenario PASS (SC-00..SC-17b, 14:54); pytest 88/88; `schema.py check` OK.

## Validasi manual (di luar tasks)

- [ ] MC-NW-01, MC-NW-02 (design §6.5).
- [ ] Sinkron PC-21..24 ke dokumen induk Claude Docs setelah spec selesai.
