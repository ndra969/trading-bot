# Implementation plan — 08 Notifier core

Status: Done (2026-10-01)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `run-ea-tests.ps1 -Scenario SC-xx`, pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`. Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.07 di task 9.

- [x] 1. Skema data v3
  - Red: TS-30..32 (`test_schema_core.py`, `test_queries.py`) mengharapkan migrasi 0003, kolom `notify_key`/`status_reason`, indeks, `notify_key = 'row-<id>'`, seed v3 → FAIL
  - Green: `schema.py new data "alert notify"`, isi `0003_alert_notify.sql`; `enums.md` (`TRADE_OPENED`, `TRADE_CLOSED`, enum `alert_status_reason`); blok `-- @version 3` di `seed_sample.sql`; `schema.py build` (Migrations.mqh, SchemaEnums.mqh, snapshot, fixture); suite `Migrations` tetap ALL PASS
  - _Requirements: 5.1, 5.2_ · _Tests: TS-30..32_
  - Hasil (2026-10-01): Red = 6 pytest FAIL (migrasi 0003, enum, seed v3 belum ada). Green: `0003_alert_notify.sql`, `enums.md` (`TRADE_OPENED`, `TRADE_CLOSED`, `alert_status_reason`), blok seed `@version 3`, `schema.py build` (data versi 3); proyek tiruan di `conftest.py` menyaring enum kolom v3. pytest 57/57, `schema.py check` OK, suite Migrations 17/17.

- [x] 2. Tipe, sink, dan kunci notifikasi
  - Red: TC-ES-10..11 (suite `EventSink`) terhadap stub `CTeeSink::Add`/`NextKey` → FAIL
  - Green: `AlertEvent.key`, `AlertStatus`, enum dan struct notifier di `Core/Types.mqh`; konstanta `SDB_NT_*`, `SDB_GV_NT_*` di `Core/Constants.mqh`; `ISdbEventSink::OnAlertStatus` + implementasi di `CNullSink`, `CFakeSink`, `CScenarioRecorder`, `CLogger` (stub, diisi task 6); `CTeeSink` jadi sampai 4 sink dengan `SetKeyPrefix`/`NextKey`; compile 0/0, unit lama ALL PASS
  - _Requirements: 1.1, 5.1, 6.2_ · _Tests: TC-ES-10, TC-ES-11_
  - Hasil (2026-10-01): Red = suite EventSink tidak compile (`CTeeSink::Add`/`SetKeyPrefix`, `AlertStatus`, `OnAlertStatus` belum ada). Green: `AlertEvent.key`, `AlertStatus`, enum/struct notifier di `Types.mqh`, konstanta `SDB_NT_*`; `OnAlertStatus` di interface, `CNullSink`, `CFakeSink`, `CScenarioRecorder`, `CLogger` (stub); `CTeeSink` sampai 4 sink + kunci. EventSink 13/13 (TC-ES-10..12), unit 332/332, build 0/0.

- [x] 3. Aturan kirim (fungsi murni)
  - Red: TC-NT-01..21 (suite baru `TestNotifyRules`) terhadap stub `Notify/NotifyRules.mqh` → FAIL
  - Green: `NtScopeOf`, `NtIsTradeType`, `NtCooldownSec`, `NtCooldownOk`, `NtQuotaHour`, `NtQuotaTake`, `NtIsStale`, `NtPickNext`, `NtOverflowVictim`, `NtAfterResult`
  - _Requirements: 2.1–2.7, 3.2, 3.4–3.7_ · _Tests: TC-NT-01..21_
  - Hasil (2026-10-01): Red = 19 FAIL (stub; 2 lolos kebetulan). Green: `Notify/NotifyRules.mqh` (lingkup, cooldown, kuota GV jam x 1000 + jumlah, basi, urutan, korban antrean, langkah setelah hasil). NotifyRules 21/21, unit 353/353, build 0/0.

- [x] 4. Format pesan (fungsi murni)
  - Red: TC-NF-01..18 (suite baru `TestNotifyFormat`) terhadap stub `Notify/NotifyFormat.mqh` → FAIL
  - Green: `NtEscape`, `NtLevelEmoji`, `NtLevelOf`, `NtTitle`, `NtHeader`, `NtPrice`, `NtMoney`, `NtR`, `NtDuration`, `NtFormatAlert`, `NtFormatOpened`, `NtFormatClosed`, `NtTruncate` (file UTF-8, emoji sesuai design §4.4)
  - _Requirements: 1.2, 1.3, 4.1–4.6_ · _Tests: TC-NF-01..18_
  - Hasil (2026-10-01): Red = 18 FAIL (stub). Green: `Notify/NotifyFormat.mqh`; emoji, `·`, dan `…` dibangun dari code point (`NtCp`) agar tidak bergantung encoding sumber; `NtTruncate` menutup tag terbuka dan tidak memotong entitas/surrogate. NotifyFormat 20/20, unit 373/373, build 0/0. Menyimpang dari design: penanda potong = fungsi `NtTruncMark()`, bukan konstanta `SDB_NT_TRUNC_MARK`; `NtTruncate(html, maxLen)` tanpa parameter penanda.

- [x] 5. Transport dan `CNotifier`
  - Red: `CFakeTransport` (`ea/tests/Include/SDBotTests/FakeTransport.mqh`), TC-NR-01..21 (suite baru `TestNotifier`) terhadap stub `CNotifier` → FAIL
  - Green: `Notify/Transport.mqh` (`ISdbTransport`, `CLogTransport`), `Notify/Notifier.mqh` (penilaian, GV dengan compare-and-set dan cadangan memori, antrean, `OnTimer`, `DrainCritical`, `Requeue`, event trade dan peta arah posisi, waktu notifier dengan override)
  - Refactor: fungsi ≤ 50 baris; cek tidak ada include Execution/Risk/Position/Storage di `Notify/`
  - _Requirements: 1.1–1.5, 2.1–2.9, 3.1–3.7, 6.2, 6.3_ · _Tests: TC-NR-01..21_
  - Hasil (2026-10-01): Red = 21 FAIL (stub). Green: `Notify/Transport.mqh` (`ISdbTransport`, `CLogTransport`), `Notify/Notifier.mqh` (cooldown/kuota GV dengan compare-and-set dan cadangan memori, antrean prioritas, kirim maks 2 per `OnTimer`, `DrainCritical`, `Requeue`, event trade + peta arah posisi, waktu notifier); `tests/FakeTransport.mqh`. Notifier 21/21, unit 394/394, build 0/0. `Notify/` hanya meng-include Core dan Notify.

- [x] 6. Logger: kunci, status, router, restart
  - Red: TC-LG-30..33 (suite `Logger`) → FAIL
  - Green: `notify_key` di `INSERT alerts`; jenis antrean `SDB_Q_ALERT_STATUS` dengan `UPDATE`; `SetRouter`; `TakeRestartAlerts`
  - _Requirements: 1.1, 2.8, 5.2–5.4, 6.1, 6.2_ · _Tests: TC-LG-30..33_
  - Hasil (2026-10-01): Red = 4 FAIL (stub). Green: `notify_key` di INSERT alerts, jenis antrean `SDB_Q_ALERT_STATUS` (UPDATE per `login + notify_key`), `SetRouter` (alert Logger dan runner migrasi lewat tee, disimpan sekali), `TakeRestartAlerts` (STALE/RESTART, Critical muda dikembalikan, sesi sekarang dan instance lain tidak disentuh); `RaiseAlert` jadi public. Temuan: alert dari modul tidak mengisi `key` sehingga bernilai string NULL dan `key == ""` false; tee dan Logger memakai `StringLen`, TC-ES-10 kini memakai alert tanpa key. Logger 30/30, unit 398/398, build 0/0.

- [x] 7. Rangkaian di `CSdbApp`
  - Red: TC-AP baru di suite `App` (notifier terpasang kecuali optimasi; alert init terkirim lewat transport palsu; deinit setelah init gagal menyerahkan Critical) → FAIL
  - Green: member notifier/transport/tee; `OnInit(cfg, observer, transport)`; notifier sebelum `Logger.Open`; router; `TakeRestartAlerts` → `Requeue`; konteks notifier (tag akun, digit, mata uang, `TESTER`); `SetState` di `EnsureState`; `OnTimer` sebelum flush; `DrainCritical` di `OnDeinit`; accessor `Notifier()`, `Sink()`
  - Regresi: `run-ea-tests.ps1 -All` (unit + SC-00..09) ALL PASS
  - _Requirements: 1.1, 1.5, 3.1, 3.3, 6.3, 6.4, 7.1–7.3_ · _Tests: TC-AP baru, SC-00..09_
  - Hasil (2026-10-01): Red = TC-APP-09 dan TC-APP-11 FAIL (stub `NotifierActive`/transport diabaikan). Green: `CSdbApp` memegang notifier, transport log, dan tee selalu (Logger + Notifier + observer); notifier dipasang sebelum `Logger.Open`, router Logger ke tee, `TakeRestartAlerts` -> `Requeue`, konteks pesan (`TESTER` di tester, selain itu dari jenis akun), `SetState` di `EnsureState`, `OnTimer` sebelum flush, `DrainCritical` di `OnDeinit`; tanpa DB (optimasi) notifier tidak dipasang. TC-APP-07 disesuaikan (tabel alerts kini juga berisi event trade TC-APP-08) dan TC-APP-12 baru membuktikan `TRADE_OPENED`/`TRADE_CLOSED` SENT dari posisi sungguhan. App 21/21, unit 402/402, `-All`: SC-00..09 PASS (2 menit 1 detik), build 0/0.

- [x] 8. Skenario SC-10
  - Red: `SC-10_notifier.ini/.set`, input harness `HarnessTransportScript`, `HarnessAlertBurstAtBar`, cabang `CheckScenario("SC-10")` dengan 8 assert design §6.6; jalankan sebelum harness meneruskan transport palsu → FAIL
  - Green: harness memasang `CFakeTransport` dengan skrip, burst alert lewat `App.Sink()`, perekam sumber panggilan; assert terhadap rekaman transport dan `sdbot_tester.sqlite`
  - _Requirements: 1.2, 1.3, 2.3, 2.6, 3.1–3.4, 5.1, 5.2, 7.4, 7.5_ · _Tests: SC-10_
  - Hasil (2026-10-01): Red = SC-10 5 FAIL (transport palsu belum diteruskan harness). Green: `SC-10_notifier.ini/.set`; input harness `HarnessTransportScript`, `HarnessTransportFailType`, `HarnessAlertBurstAtBar`; `CFakeTransport` merekam hasil, fase (TIMER/DEINIT/TICK/TRADE), dan nomor siklus timer; `CheckSc10` (8 assert + sesi), `CheckScenario` menerima transport. Temuan 1: di tester (Model 1) `TimeCurrent` tidak maju di setiap siklus timer, jadi batas 2 pesan per siklus diperiksa dengan nomor siklus, bukan waktu. Temuan 2: pesan yang ditahan kuota ikut memakai cooldown tipenya; diperbaiki (cooldown dicek, kuota diambil, baru cooldown dipakai) dengan TC-NR-22 lebih dulu (Red terbukti). SC-10 9/9 (9 trade/closure SENT, 6 burst + kuota, TEST_FAIL 3 percobaan, tanpa PENDING), unit 403/403, `-All` 15 run PASS (2 menit 9 detik).

- [x] 9. Versi 1.07 dan dokumen repo
  - Versi `1.07` di `SDBot.mq5` dan harness; diagram `docs/flows/` (init, timer) + `notifier.md` baru; `CHANGELOG.md`; README (alur notifikasi, SC-10); checklist manual MC-NT-01
  - Regresi akhir: `run-ea-tests.ps1 -All` (unit + SC-00..10) dan pytest ALL PASS, build 0/0
  - _Requirements: 8.1, 8.2_ · _Tests: semua_
  - Hasil (2026-10-01): Versi `1.07` di `SDBot.mq5` dan harness; `docs/flows/` (init, timer, README) + `notifier.md` baru; `CHANGELOG.md` 1.07; README (status, input harness SC-10); MC-NT-01 di checklist manual; penyimpangan implementasi dicatat di design (`NtTruncate`/`NtCp`, urutan cooldown-kuota, `CFakeTransport` fase dan siklus, SC-10, tes tambahan). Regresi akhir `-All`: build 0/0, unit + SC-00..SC-10 PASS (15 run, 2 menit 9 detik); pytest 57/57; `schema.py check` OK (data versi 3).

## Validasi manual (di luar tasks)

- [ ] MC-NT-01: EA live di akun cent 1 jam dengan transport log; pesan di log Experts berformat sesuai design §4.4, baris `alerts` berstatus `SENT`.
- PC-13 disinkronkan ke dokumen induk bersama keputusan spec 09 (skill `sdbot-docs-sync`), atau lebih awal bila Anda minta.
