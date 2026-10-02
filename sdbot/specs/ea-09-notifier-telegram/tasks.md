# Implementation plan — 09 Notifier Telegram

Status: Done (2026-10-02)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`, skenario lewat `run-ea-tests.ps1 -Scenario SC-xx`, pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`. Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.08 di task 10.

- [x] 1. Input, enum, dan preset
  - Red: TC-SU-30 dan TC-SU-04c baru (suite `CoreUtils`), TC-PR-02 (suite `Presets`), TS-46 (`test_presets.py`) → FAIL
  - Green: `InpTelegramToken`, `InpTelegramChatID`, `InpHeartbeatMinutes` di `Inputs.mqh`; `heartbeatMinutes` di `InputValues` + validasi; token/chat di `SdbAppConfig`; JSON sesi tanpa rahasia + `InpTelegramConfigured`; konstanta design §4.6 (`SDB_NT_DRAIN_MS` 2000); `enums.md` (tipe dan alasan baru) + `schema.py build`; `gen_presets.py` + 12 preset
  - _Requirements: 1.1, 1.3, 1.8_ · _Tests: TC-SU-30, TC-SU-04c, TC-PR-02, TS-46_
  - Hasil (2026-10-02): Red = TC-SU-04c/04d, TC-SU-30, TC-IN-04 (TC-PR-02) FAIL dan TS-46 FAIL. Green: input `InpTelegramToken`, `InpTelegramChatID`, `InpHeartbeatMinutes` (grup Notifikasi) + validasi 0 atau 5-1440; token/chat hanya di `SdbAppConfig`; JSON sesi tanpa rahasia, dengan `InpHeartbeatMinutes` dan `InpTelegramConfigured`; konstanta spec 09, `SDB_NT_DRAIN_MS` 2000; `enums.md` (EA_START, EA_STOP, HEARTBEAT, DAILY_REPORT, TELEGRAM_OFF, PUSH_SENT, PUSH_FAILED, PLAIN_TEXT) + build (data tetap v3); `gen_presets.py` + 12 preset. `test_tp04` kini mengecualikan `*.local.set`. Unit 405/405, pytest 58/58, build 0/0.

- [x] 2. Skrip `make_local_presets.py`
  - Red: TS-40..45 (`test_make_local_presets.py`, repo git tiruan di folder sementara) → FAIL
  - Green: parser `.env`, penulisan `.local.set`, `--force`, `git check-ignore`, output tanpa token
  - _Requirements: 1.4–1.7, 1.3_ · _Tests: TS-40..45_
  - Hasil (2026-10-02): Red = TS-40..45 FAIL (stub). Green: `tools/make_local_presets.py` (parser `.env` dengan `export`/kutip/komentar, satu `.local.set` per preset repo, `.local.set` tidak dibaca sebagai sumber, tidak menimpa yang disunting tanpa `--force`, `git check-ignore` wajib, token tidak dicetak). pytest 64/64, black/ruff bersih. Di repo asli `*.local.set` diabaikan `sdbot/.gitignore`.

- [x] 3. Aturan Telegram dan push (fungsi murni)
  - Red: TC-TG-01..14 (suite baru `TestTelegramRules`) terhadap stub `Notify/TelegramRules.mqh` → FAIL
  - Green: `TgJsonEscape`, `TgBody`, `TgUrl`, `TgMask`, `TgRetryAfter`, `TgClassify`, `TgIsParseError`, `NtPlainText`, `NtPushText`, `PushAllowed`
  - _Requirements: 1.3, 2.1–2.4, 3.1, 3.4_ · _Tests: TC-TG-01..14_
  - Hasil (2026-10-02): Red = 14 FAIL (stub). Green: `Notify/TelegramRules.mqh` (`TgJsonEscape`, `TgBody`, `TgUrl`, `TgMask`, `TgRetryAfter`, `TgIsParseError`, `TgClassify` dengan `ERR_FUNCTION_NOT_ALLOWED`/`ERR_WEBREQUEST_*`, `NtPlainText`, `NtPushText`, `PushAllowed`); enum `ENUM_SDB_TG_OUTCOME` di Types. TelegramRules 14/14, unit 419/419, build 0/0.

- [x] 4. Jadwal, lease, dan statistik harian (fungsi murni)
  - Red: TC-SC-01..10 (suite baru `TestSchedule`) terhadap stub `Notify/Schedule.mqh` → FAIL
  - Green: `LeaseEncode`/`Decode`/`CanTake`, `HeartbeatDue`, `ReportDays`, `ServerDayStart`, `DayStats`; `IsSdbotMagic` pindah ke `Core/Utils.mqh` (RiskMath memakainya, suite RiskMath tetap ALL PASS)
  - _Requirements: 4.1, 4.2, 5.1, 6.1–6.4_ · _Tests: TC-SC-01..10_
  - Hasil (2026-10-02): Red = 10 FAIL (stub). Green: `Notify/Schedule.mqh` (`LeaseEncode`/`Decode`/`CanTake`, `HeartbeatDue`, `ServerDayStart`, `ReportDays`, `DayStats`, `DayHasActivity`); struct `SdbDealRow`, `SdbDayStats` (array simbol tetap 16) di Types; `IsSdbotMagic` pindah ke `Core/Utils.mqh`. Schedule 10/10, RiskMath 33/33, unit 429/429, build 0/0.

- [x] 5. Format pesan berjadwal
  - Red: TC-NF-20..24 (suite `NotifyFormat`) → FAIL
  - Green: `NtFormatHeartbeat`, `NtFormatDailyReport`, `NtFormatStart`, `NtFormatStop`, `NtMoneyGrouped`
  - _Requirements: 5.2, 6.2, 7.1, 7.2_ · _Tests: TC-NF-20..24_
  - Hasil (2026-10-02): Red = 5 FAIL (stub). Green: `NtMoneyGrouped`, `NtSigned`, `NtHeaderWith`, `NtFormatHeartbeat`, `NtFormatDailyReport`, `NtFormatStart`, `NtFormatStop`; `SdbHeartbeat`, `SdbStartInfo`, `SdbNtContext.login` di Types. Heartbeat dan laporan berpenanda `AKUN <login>`; laporan menampilkan "Balance" (saldo saat laporan dibuat) karena laporan bisa terlambat beberapa hari. NotifyFormat 25/25, unit 434/434, build 0/0.

- [x] 6. Notifier: push, Telegram nonaktif, jadwal, start/stop
  - Red: `CFakePush`, `CFakeStatusSource` (tests), TC-NR-30..40 (suite `Notifier`) → FAIL; TC-NR-17 menyesuaikan `Drain`
  - Green: `Notify/Push.mqh` (`ISdbPush`, `CPushSender`, `CLogPush`), `Notify/StatusSource.mqh`, `Notify/DailyStats.mqh`; `CNotifier`: `SendStart`/`SendStop`/`Drain`/`ReleaseLeader`, bypass aturan, `silent`, push untuk Critical, `TELEGRAM_OFF`, jeda `retryAfterSec` pada TEMP, alasan `note`, `RunSchedule` (alive, lease, heartbeat, laporan), `NT_HELD` per akun
  - _Requirements: 2.3, 2.4, 2.6, 3.1–3.4, 4.1–4.4, 5.1–5.3, 6.1–6.4, 7.2–7.4_ · _Tests: TC-NR-17, TC-NR-30..40_
  - Hasil (2026-10-02): Red = TC-NR-30..40 FAIL (11, stub). Green: `Notify/Push.mqh` (`ISdbPush`, `CPushSender` dengan `PushAllowed` dan error notifikasi MT5, `CLogPush`), `Notify/StatusSource.mqh`, `Notify/DailyStats.mqh` (posisi SDBot dari deal pembuka, karena penutupan manual bermagic 0), `Notify/NotifySchedule.mqh` (`CNotifySchedule`: penanda hidup, lease, klaim heartbeat dan hari laporan, `NT_HELD`; dipisah agar Notifier tidak membengkak); `CNotifier`: bypass aturan + `silent`, push untuk Critical gagal (antre bila dibatasi), Telegram nonaktif (1 CRITICAL + 1 push), jeda `retryAfterSec` pada TEMP, alasan `note`, `RunHeartbeat`, `RunReports`, `SendStart`/`SendStop`, `Drain` (Critical lalu stop, ganti `DrainCritical`). `SendStop` menerima teks alasan karena `SdbDeinitReasonText` ada di Storage. `tests/FakePush.mqh` (push + sumber status palsu), `CFakeTransport` mendukung `TEMP:n`, `OK:NOTE`, `CONFIG`. Notifier 33/33, unit 445/445, build 0/0.

- [x] 7. `CTelegramTransport`
  - Red: TC-TG-15..17 (suite `TelegramRules`): langkah `Send` yang bisa diuji tanpa jaringan — nonaktif → `PERMANENT TELEGRAM_OFF`; GV `NT_TG_NEXT` di masa depan → `LIMITED` tanpa `WebRequest`; token kosong → tidak pernah memanggil `WebRequest` → FAIL
  - Green: `Notify/TelegramTransport.mqh` (WebRequest JSON UTF-8, klasifikasi, 429 bersama, teks polos sekali, nonaktif, log tersamar); di tester dan unit test `WebRequest` tidak dipanggil (dijaga `MQL_TESTER`)
  - _Requirements: 1.3, 2.1–2.5, 2.7_ · _Tests: TC-TG-15..17, MC-TG-02..04_
  - Hasil (2026-10-02): Red = TC-TG-15..17 FAIL (stub). Green: `Notify/TelegramTransport.mqh` (`WebRequest` POST JSON UTF-8 timeout 3 detik, `TgClassify`, 429 menggeser `NT_TG_NEXT` untuk semua instance, jarak 1 detik dengan compare-and-set (cadangan lokal sebelum akun PASSED), kirim ulang teks polos sekali saat HTML ditolak, nonaktif saat error konfigurasi, TEMP dengan jeda 10 detik, token disamarkan di semua pesan). Temuan: penjaga tester harus jadi pemeriksaan terakhir sebelum jaringan agar jarak kirim tetap teruji di tester. TelegramRules 17/17, unit 448/448, build 0/0.

- [x] 8. Rangkaian App dan Logger
  - Red: TC-LG-34 (suite `Logger`), TC-APP-13..14 (suite `App`) → FAIL
  - Green: `CLogger.PreviousSessionEnd`; `CSdbApp` sebagai `ISdbStatusSource`, pemilihan transport dan push, WARN token kosong, `SendStart` di akhir `OnInit`, `SendStop` → `Drain` → `ReleaseLeader` di `OnDeinit`, `SetState` transport
  - Regresi: `run-ea-tests.ps1 -All` (unit + SC-00..10) ALL PASS
  - _Requirements: 1.2, 2.7, 5.2, 7.1, 7.2, 7.4_ · _Tests: TC-LG-34, TC-APP-13, TC-APP-14_
  - Hasil (2026-10-02): Red = TC-LG-34, TC-APP-13, TC-APP-14 FAIL (stub). Green: `CLogger.PreviousSessionEnd`; `CSdbApp` sebagai `ISdbStatusSource` (balance, equity, DD dari puncak GV, status risiko, posisi SDBot di akun), pilih transport (uji > tester/token kosong = log + WARN > Telegram) dan push (tester `CLogPush`, live `CPushSender`), `SetSchedule`, `login` di konteks, `SendStart` di akhir `OnInit`, `SendStop` + `Drain` + `ReleaseLeader` di `OnDeinit`, `SetState` transport Telegram. TC-APP-07 mengecualikan `EA_*`; TC-APP-09 menjalankan 3 siklus karena closure rekonsiliasi dan start antre lebih dulu. Unit 451/451, `-All` (unit + SC-00..10) PASS 2 menit 15 detik, build 0/0.

- [x] 9. Skenario SC-11
  - Red: `SC-11_heartbeat_report.ini/.set`, cabang `CheckScenario("SC-11")` dengan 7 assert design §6.7 → FAIL sebelum harness menyalakan jadwal (heartbeat 0)
  - Green: set `InpHeartbeatMinutes=60`, restart di hari ketiga; assert terhadap transport palsu, rekaman closure, dan DB
  - _Requirements: 4.1–4.3, 5.1, 5.3, 6.1–6.4, 7.1–7.3, 8.1_ · _Tests: SC-11_
  - Hasil (2026-10-02): Red = SC-11 FAIL dengan `InpHeartbeatMinutes=0` (heartbeat tidak ada). Temuan sungguhan: hari pemasangan tidak pernah dilaporkan karena GV `NT_REPORT_DAY` baru diisi hari ini; diperbaiki jadi kemarin (hari sebelum pemasangan tetap tidak dilaporkan). Green: `SC-11_heartbeat_report.ini/.set` (heartbeat 60, restart bar 250), `CheckSc11` (heartbeat jarak >= 3600 lintas restart dan tanpa bunyi, laporan per hari cocok dengan closure rekaman, tanpa 19-20 Sep, Jumat 18 Sep terkirim, 2 start/2 stop, tidak ada yang SKIPPED). SC-11 7/7 (236 heartbeat, 9 laporan, 2 start, 2 stop, semua SENT); `-All` 16 run PASS (2 menit 22 detik).

- [x] 10. Versi 1.08, dokumen, dan sinkron dokumen induk
  - Versi `1.08` di `SDBot.mq5` dan harness; `docs/flows/` (init, timer, notifier); `CHANGELOG.md`; README (input, instalasi Telegram, skrip, SC-11); checklist MC-TG-01..08; status Fase 2 di `specs/README.md`
  - Skill `sdbot-docs-sync`: terapkan PC-13 dan PC-14 ke PRD-EA, PRD-Backoffice, RULES (claude.ai), ekspor ulang salinan `sdbot/docs/`, pindahkan entri ke Done
  - Regresi akhir: `run-ea-tests.ps1 -All` (unit + SC-00..11), pytest, `schema.py check`, build 0/0
  - _Requirements: 8.3, 8.4_ · _Tests: semua_
  - Hasil (2026-10-02): Versi `1.08` (EA + harness); `docs/flows/` (init, timer, notifier: Telegram, push, jadwal); `CHANGELOG.md` 1.08; README (status Fase 2 selesai, input, bagian Notifikasi Telegram, skrip, SC-11); MC-TG-01..08 di checklist; penyimpangan implementasi di design §7a. Sinkron dokumen induk: PC-13 dan PC-14 ke PRD-EA (rev 42: tabel dan kebutuhan Notifikasi, kolom `alerts`, `HeartbeatMinutes`, Instalasi 4) dan PRD-Backoffice (rev 16: skema v3, `alerts`); salinan diekspor ulang (diff hanya perubahan PC + tanggal header); kedua entri ke Done. Regresi akhir: build 0/0, unit 451/451, SC-00..SC-11 PASS (16 run, 2 menit 24 detik), pytest 64/64, `schema.py check` OK.

## Validasi manual (di luar tasks)

- [ ] MC-TG-01..08 di akun cent (Telegram sungguhan, push HP, dua chart, laporan harian pertama).
- [ ] MC-NT-01 (spec 08) bisa digabung dengan MC-TG-02.
