# Implementation plan — 02 Core dan akun

Status: Done (2026-09-29), validasi manual MC-01..06 tertunda
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

Setiap task memakai TDD: test case ditulis dulu dan terbukti FAIL lewat `tools/run-ea-tests.ps1 -Unit`, lalu implementasi sampai ALL PASS dengan compile 0/0. Hasil verifikasi ditulis di baris "Hasil" tiap task.

- [x] 1. Tipe dasar, konstanta, dan event sink
  - Red: suite `TestEventSink` (TC-LG-02 versi dasar: `CFakeSink` menyimpan `AlertEvent` yang dikirim; TC-LG-03 versi dasar: `CNullSink` tidak melakukan apa pun) terhadap stub yang tidak menyimpan event
  - Green: `Core/Types.mqh` (enum §4.1, `AccountSnapshot`, `AlertEvent`, struct event lain minimal), `Core/Constants.mqh` (§4.4), `Core/EventSink.mqh` (`ISdbEventSink`, `CNullSink`), `tests/.../FakeSink.mqh`
  - _Requirements: 6.1, 6.2, 6.3_ · _Tests: TC-LG-02a..g, TC-LG-03a_
  - Hasil (2026-09-29): Red = 6 FAIL (TC-LG-02a..f, `CFakeSink` stub). Green = EventSink 8/8, total 24/24, build 0/0. `Constants.mqh` juga berisi batas blok magic (`SDB_MAGIC_MIN/MAX/HARNESS`) untuk task 2. Struct event selain `AccountSnapshot` dan `AlertEvent` masih satu field, dilengkapi spec 03–06.

- [x] 2. Input dan aturan validasinya
  - Red: suite `TestCoreUtils` bagian input (TC-CU-01..08c) terhadap `ValidateInputValues` yang selalu lolos
  - Green: `Core/InputRules.mqh` (`InputValues`, `ValidateInputValues` menggabungkan semua kesalahan) dan `Core/Inputs.mqh` (17 input §4.3 dengan default PRD dan magic `2026091901`, `CurrentInputs()`)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_ · _Tests: TC-CU-01..08d_
  - Hasil (2026-09-29): Red = 11 FAIL (stub selalu lolos). Green = CoreUtils 13/13, total 37/37, build 0/0. Default input ditulis sekali sebagai `SDB_DEF_*` di `Constants.mqh` dan dipakai `Inputs.mqh` maupun `DefaultInputValues()`; TC-CU-01b memastikan keduanya sama. Tambahan: TC-CU-01c (magic default di blok), TC-CU-08d (batas ATR, buffer BE, rugi harian).

- [x] 3. Log terminal, throttle, dan util murni
  - Red: TC-CU-09..15 dan TC-LG-01 terhadap stub
  - Green: `Core/Utils.mqh`: `FormatLogLine`, level log (`SdbSetLogLevel`, `LogDebug` … `LogCritical`), `ThrottleAllow` + `LogThrottled` (64 slot LRU, jumlah yang ditahan), `NormalizePriceTo`, `StyleTimeframes`, `ErrText`; hook uji untuk menangkap baris yang dicetak (TC-LG-01)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 7.1, 7.2_ · _Tests: TC-CU-09..16, TC-LG-01a..c_
  - Hasil (2026-09-29): Red = 14 FAIL. Green = CoreUtils 30/30, total 54/54, build 0/0. Throttle berupa kelas `CLogThrottle` (64 slot, LRU) agar bisa diuji dengan waktu buatan; `LogThrottled` memakai satu instance internal dan `TimeLocal()`. Nilai uji pembulatan diganti dari 1.082345 (ambigu di floating point) ke 1.082346 / 1.082344.

- [x] 4. Status bersama di Global Variables
  - Red: suite `TestState` (TC-ST-01..05) terhadap stub
  - Green: `Core/State.mqh` `CState` (prefix, `Key`, `GetOrInit`, `Set` dengan flush, `TouchAll`, `DeleteAll`)
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_ · _Tests: TC-ST-00..06_
  - Hasil (2026-09-29): Red = 7 FAIL. Green = State 9/9, total 63/63, build 0/0. Keterbatasan: di tester Global Variables disimulasikan, jadi ketahanan `GlobalVariablesFlush` terhadap crash terminal (EC-06) hanya bisa dicek manual (MC-06).

- [x] 5. Aturan akun, izin trading, dan koneksi (fungsi murni)
  - Red: suite `TestAccountRules` (TC-AC-01..21) terhadap stub
  - Green: `Account/AccountRules.mqh`: `AccountTypeOf`, `EvaluateAccount`, `SymbolMatchesSuffix`, `TradePermission`, `ConnectionStep`
  - _Requirements: 2.2, 2.3, 2.4, 2.10, 3.1, 3.3, 3.4, 3.5, 3.6_ · _Tests: TC-AC-01..21 (+05b, 08b/c, 12b, 15b/c)_
  - Hasil (2026-09-29): Red = 19 FAIL. Green = AccountRules 27/27, total 90/90, build 0/0. Keputusan: hanya `SYMBOL_TRADE_MODE_FULL` yang boleh trading. Deteksi cent mencocokkan mata uang utuh dari `SDB_CENT_CURRENCIES` (USC, EUC).

- [x] 6. Kelas `CAccount`
  - Red: suite `TestAccount` di tester (akun tester): `Validate()` mengembalikan PASSED dan mengirim satu `AccountSnapshot` ke `CFakeSink`; `CanTrade()` di tester true; sink `NULL` memakai `CNullSink` (TC-LG-03)
  - Green: `Account/Account.mqh`: state machine validasi (PENDING/CHECK/PASSED/REJECTED), `SymbolSelect`, `CanTrade` dengan alasan, `OnTimer` (koneksi lewat `ConnectionStep`, izin berubah, ganti akun, validasi tertunda), `Snapshot`
  - _Requirements: 2.1, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 3.2, 6.4_ · _Tests: TC-AC-22a..c, 23, 24, 25, 25b_
  - Hasil (2026-09-29): Red = 6 FAIL. Green = Account 7/7, total 97/97, build 0/0. `Init` menerima simbol, suffix, allowLive, dan magic sebagai parameter (bukan membaca `Inp*`) agar kasus suffix salah bisa diuji. Kode alert sementara di `Constants.mqh` (`SDB_ALERT_*`), dipindah ke `SchemaEnums.mqh` di spec 03. Jalur validasi tertunda, ganti akun, dan alert koneksi di terminal sungguhan dibuktikan lewat MC-03..05.

- [x] 7. Pasang di `SDBot.mq5` v1.01
  - `OnInit`: validasi input (`INIT_PARAMETERS_INCORRECT`) → `CState.Init` → `CAccount.Validate` (`INIT_FAILED` saat REJECTED, lanjut saat PENDING) → `EventSetTimer(1)`; `OnTimer` → `CAccount.OnTimer` (+ `ExpertRemove()` bila validasi tertunda ditolak); `OnDeinit` membersihkan; sink = `CNullSink` sampai spec 03
  - Verifikasi: build 0/0; `run-ea-tests.ps1 -Unit` ALL PASS; smoke run di tester (log init, validasi PASSED, tanpa deal)
  - _Requirements: 1.2, 1.3, 1.5, 2.6, 2.8_
  - Hasil (2026-09-29): build 3 target 0/0; unit 97/97. Smoke run `SDBot.ex5` di tester Broker A: (a) input benar → `akun valid` + `SDBot v1.01 aktif … validasi=SDB_VAL_PASSED`, tanpa deal, balance tetap; (b) `InpRiskPerTradePct=2` → CRITICAL `input tidak valid`, tester: "OnInit reports incorrect input parameters"; (c) `InpSymbolSuffix=zz` → CRITICAL suffix, "OnInit returns non-zero code 1"; (d) magic 20260919 + BE R 2 → satu pesan berisi tiga kesalahan. `CState` diinisialisasi setelah validasi PASSED (login > 0), termasuk bila validasi tertunda lolos lewat timer.
  - Temuan: akun di Strategy Tester terbaca **demo** (validasi lolos walau `InpAllowLiveTrading=false`), jadi penolakan akun real/cent hanya bisa dibuktikan lewat MC-01. Array parameter tidak bisa dikirim lewat `powershell -File`; skrip smoke memakai string dipisah `;`.

## Validasi manual (di luar tasks)

Di akun cent (terminal tempat SDBot live nanti, diputuskan di Fase 3) atau Broker A:

- [ ] MC-01: `InpAllowLiveTrading = false` di akun cent → gagal init, CRITICAL
- [ ] MC-02: `.set` benar di chart EURUSDc → init sukses, snapshot akun di log
- [ ] MC-03: tutup MT5 dengan EA terpasang lalu buka lagi → validasi tertunda lalu lolos
- [ ] MC-04: matikan Algo Trading 1 menit → satu WARN, satu INFO saat hidup lagi
- [ ] MC-05: cabut jaringan 6 menit → WARN, alert Medium di menit ke-5, Info saat pulih
- [ ] MC-06: setel GV uji lewat EA (flush), lalu matikan paksa `terminal64.exe` dari Task Manager; buka lagi → GV tetap ada (EC-06)
