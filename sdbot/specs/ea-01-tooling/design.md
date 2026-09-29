# Design — 01 Tooling

Status: Approved (2026-09-29), dengan perubahan §7 (terminal uji = instalasi "Broker A")
Requirements: [requirements.md](requirements.md)

## 1. Overview

Semua alat ditulis sebagai skrip PowerShell di `sdbot/tools/` (sesuai RULES) ditambah framework uji MQL5 di `sdbot/ea/tests/`. Runner menjalankan uji di **terminal uji portable** lewat `terminal64.exe /config:<ini>`, karena terminal live sedang dipakai trading dan tidak bisa menerima konfigurasi tester dari command line saat berjalan.

Risiko utama: mekanisme `/config` + `ShutdownTerminal` dan pembacaan file hasil di folder Common belum dicoba di mesin ini. Task pertama spec ini adalah spike untuk membuktikannya. Jika gagal, fallback-nya script `RunUnitTests` dijalankan manual di chart (Requirement 3.5 tetap terpenuhi), dan design ini diperbarui.

## 2. Struktur file

```
sdbot/
  ea/src/
    Experts/SDBot/SDBot.mq5              kerangka v1.00 (Req 6)
    Include/SDBot/{Core,Account,Risk,Analysis,Strategies,Signals,Filters,
                   Execution,Position,Control,Notify,Storage,UI,App}/   (.gitkeep)
    Scripts/SDBot/                       (.gitkeep)
    Presets/                             (.gitkeep)
  ea/tests/
    Include/SDBotTests/TestFramework.mqh
    Include/SDBotTests/Suites/TestFrameworkSelf.mqh
    Include/SDBotTests/Suites/TestEnvCheck.mqh
    Include/SDBotTests/AllSuites.mqh      daftar suite yang dijalankan (bertambah tiap spec)
    Scripts/SDBotTests/RunUnitTests.mq5   entry manual
    Experts/SDBotTests/RunUnitTestsEA.mq5 entry runner (OnInit menjalankan AllSuites)
    scenarios/                            (.gitkeep, diisi mulai spec 04)
  tools/
    link-mt5.ps1
    build-ea.ps1
    run-ea-tests.ps1
    lib/Mt5Paths.psm1                     baca & validasi mt5-paths.local.json
    mt5-paths.example.json
```

`sdbot/.gitignore` ditambah `*.local.json` dan `tools/.tmp/`.

## 3. Komponen

### 3.1 `link-mt5.ps1`

```
.\link-mt5.ps1 -DataDir "C:\Users\<u>\AppData\Roaming\MetaQuotes\Terminal\<ID>"
               [-RepoEa "D:\Workspaces\trading-bot\sdbot\ea"]
```

| Junction di `<DataDir>\MQL5\` | Target |
|---|---|
| `Experts\SDBot` | `ea\src\Experts\SDBot` |
| `Include\SDBot` | `ea\src\Include\SDBot` |
| `Scripts\SDBot` | `ea\src\Scripts\SDBot` |
| `Presets\SDBot` | `ea\src\Presets` |
| `Experts\SDBotTests` | `ea\tests\Experts\SDBotTests` |
| `Include\SDBotTests` | `ea\tests\Include\SDBotTests` |
| `Scripts\SDBotTests` | `ea\tests\Scripts\SDBotTests` |

Per baris: jika belum ada, buat junction (`New-Item -ItemType Junction`, tidak butuh Administrator). Jika sudah junction ke target yang sama, lapor "sudah terhubung". Jika junction ke target lain, atau folder biasa, berhenti dengan exit 1 tanpa mengubah apa pun (1.4). `RepoEa` default dihitung dari lokasi skrip. Untuk terminal portable, `DataDir` adalah folder instalasinya sendiri.

### 3.2 `mt5-paths.local.json`

```json
{
  "metaeditor": "C:\\Program Files\\MetaTrader 5\\metaeditor64.exe",
  "liveDataDir": "C:\\Users\\<u>\\AppData\\Roaming\\MetaQuotes\\Terminal\\<ID>",
  "testTerminal": "D:\\MT5-Test\\terminal64.exe",
  "testDataDir": "D:\\MT5-Test",
  "commonFilesDir": "C:\\Users\\<u>\\AppData\\Roaming\\MetaQuotes\\Terminal\\Common\\Files",
  "testSymbol": "EURUSDc",
  "timeoutSec": 600
}
```

`Mt5Paths.psm1` memvalidasi semua path ada, `testDataDir ≠ liveDataDir` (4.4), dan mengembalikan objek konfigurasi. Kesalahan konfigurasi → exit 2 dengan pesan yang menyebut kunci yang salah.

### 3.3 `build-ea.ps1`

```
.\build-ea.ps1 [-Target <path .mq5 relatif ke ea/>] [-Terminal test|live] [-Config <json>]
```

1. Tanpa `-Target`: `src/Experts/SDBot/SDBot.mq5`, `tests/Experts/SDBotTests/*.mq5`, `tests/Scripts/SDBotTests/*.mq5`.
2. Setiap target di-compile lewat path junction-nya di `<DataDir>\MQL5\...` agar `#include <SDBot/...>` dan `<SDBotTests/...>` ter-resolve: `metaeditor64.exe /compile:"<path>" /log:"tools\.tmp\<nama>.log"`.
3. Log dibaca sebagai UTF-16. Baris `error`/`warning` ditampilkan sekali (MetaEditor menulis setiap pesan dua kali), dan baris `Result: N errors, M warnings` diparse. Log tanpa baris `Result` dianggap gagal. Compile memakai `/inc:"<data>\MQL5"` dan log `tools\.tmp\build-<nama>.log`.
4. Exit 0 jika semua target 0/0, 1 jika tidak (2.3), 2 jika lingkungan tidak siap (2.4).

### 3.4 `run-ea-tests.ps1`

```
.\run-ea-tests.ps1 [-Unit] [-Scenario SC-06[,SC-07]] [-All] [-SkipBuild] [-TimeoutSec <n>] [-Config <json>]
```

1. Jalankan `build-ea.ps1 -DataDir test`. Gagal → exit 1.
2. Buat `runId` = `yyyyMMdd-HHmmss-<acak4>`. Hapus `sdbot_test_<runId>.txt` jika ada (4.3).
3. Tulis `tools\.tmp\<runId>.ini`:
   ```ini
   [Tester]
   Expert=SDBotTests\RunUnitTestsEA.ex5
   Symbol=EURUSDc
   Period=M15
   Model=2
   FromDate=2026.09.01
   ToDate=2026.09.02
   Deposit=10000
   Currency=USC
   Leverage=500
   ExpertParameters=<runId>.set
   ShutdownTerminal=1
   ```
   File `.set` sementara berisi `InpTestRunId=<runId>`. Untuk skenario, `Expert` = harness, rentang tanggal dan input dari `scenarios/SC-xx.ini` + `.set` (spec 04).
4. Jalankan `testTerminal /portable /config:<ini>` dan tunggu proses selesai sampai `timeoutSec`. Lewat batas → hentikan proses, exit 3.
5. Baca `commonFilesDir\sdbot_test_<runId>.txt`. Tidak ada → exit 1 dengan isi log tester terakhir. Ada → tampilkan ringkasan, exit 0 jika baris `RUN ... END` berisi `fail=0`.

Model 2 (*Open prices only*) cukup untuk unit test karena semua dijalankan di `OnInit`. Skenario memakai model real ticks.

### 3.5 Framework uji — `TestFramework.mqh`

```cpp
void   TfBeginRun(string runId);                 // buka file hasil (FILE_COMMON|FILE_WRITE|FILE_TXT|FILE_ANSI)
void   TfBeginSuite(string suite);
bool   AssertEq(string id, string desc, double actual, double expected, double tol = 1e-9);
bool   AssertIntEq(string id, string desc, long actual, long expected);
bool   AssertTrue(string id, string desc, bool cond);
bool   AssertStrEq(string id, string desc, string actual, string expected);
void   TfEndSuite();
int    TfEndRun();                               // tulis ringkasan, tutup file, kembalikan jumlah FAIL
int    TfFailCount();  int TfPassCount();        // untuk self-test
void   TfMute(bool mute);                        // self-test: assert yang sengaja gagal tidak mengotori ringkasan
void   TfSetCounts(int pass, int fail);          // self-test: kembalikan hitungan setelah assert yang di-mute
void   TfInfo(string text);                      // baris INFO (misalnya versi SQLite di EnvCheck)
```

Format file hasil (juga dicetak ke log Experts):

```
RUN 20261001-101500-a1b2 START
SUITE CoreUtils
PASS TC-CU-01 RoundLotDown 0.0379 -> 0.03
FAIL TC-CU-02 RoundLotDown 0.29 | expected=0.29 actual=0.28
SUITE_END CoreUtils pass=20 fail=1
RUN 20261001-101500-a1b2 END pass=41 fail=1
```

`AllSuites.mqh` berisi satu fungsi `RunAllSuites()` yang memanggil `Run<Suite>()` setiap suite. Script dan EA runner hanya memanggil `TfBeginRun`, `RunAllSuites()`, `TfEndRun` (3.5). EA runner lalu memanggil `ExpertRemove()` (atau `TesterStop()`) agar tester langsung selesai.

### 3.6 Suite `EnvCheck`

Membuka `sdbot_envcheck.sqlite` di Common (dihapus di akhir), lalu menjalankan test case di §5. Nilai informatif (versi SQLite, selisih waktu) dicetak sebagai baris `INFO`.

### 3.7 `SDBot.mq5` kerangka

`#property version "1.00"`, `#property description`, `OnInit` mencetak log INFO "SDBot kerangka v1.00, tidak ada logika trading" lewat `Print` sementara (fungsi log baru ada di spec 02), `OnDeinit`/`OnTick` kosong. Tidak ada `#include` modul.

## 4. Error handling

| Kegagalan | Tindakan |
|---|---|
| Konfigurasi hilang / path salah | exit 2, sebut kunci JSON dan contoh nilai |
| `testDataDir` sama dengan `liveDataDir` | exit 2 (4.4) |
| Compile error/warning | exit 1, tampilkan baris dari log |
| Terminal uji tidak selesai | kill proses setelah `timeoutSec`, exit 3 |
| File hasil tidak ada | exit 1, tampilkan 50 baris terakhir log tester `testDataDir\Tester\logs\` |
| Junction bentrok | exit 1 tanpa perubahan (1.4) |
| Terminal uji sedang berjalan (`Get-Process` dengan path `testTerminal`) | exit 2, minta ditutup (8.1) |
| Runner lain sedang jalan (`tools/.tmp/run.lock` berisi PID yang masih hidup) | exit 2 (8.2). Lock dengan PID mati dianggap basi dan ditimpa |
| Data historis tidak ada (log tester berisi "no history" / "history not found") | exit 1, sebut simbol dan rentang (8.3) |
| File hasil tanpa baris `END` | exit 1, "EA uji berhenti di tengah" (8.4) |
| `pass + fail = 0` | exit 1, "tidak ada test yang dijalankan" (8.5) |
| Timeout | `Stop-Process` pada PID terminal uji, tunggu keluar, baru exit 3 (8.6) |
| EA runner selesai | suite dijalankan di `OnInit`, hasil ditulis dan file ditutup, lalu `ExpertRemove()` agar tester langsung berakhir tanpa menunggu tick |

## 5. Test case

**TestFrameworkSelf** (dijalankan dengan `TfMute(true)` untuk assert yang sengaja gagal):

| ID | Kasus | Harapan |
|---|---|---|
| TC-TF-01 | `AssertEq(1.0, 1.0)` | PASS, pass +1 |
| TC-TF-02 | `AssertEq(1.0, 1.1)` | FAIL, fail +1 |
| TC-TF-03 | `AssertEq(0.1+0.2, 0.3, 1e-9)` | PASS (toleransi) |
| TC-TF-04 | `AssertStrEq("SDB", "SDB")` dan `("a","b")` | PASS lalu FAIL |
| TC-TF-05 | `AssertIntEq(3, 3)` dan `AssertTrue(false)` | PASS lalu FAIL |
| TC-TF-06 | Hitungan setelah TC-TF-01..05 | pass = 4, fail = 3 (lalu counter dikembalikan) |

**TestEnvCheck**:

| ID | Kasus | Harapan |
|---|---|---|
| TC-ENV-01 | `SELECT sqlite_version()` | ≥ 3.24.0 (syarat UPSERT); versi dicetak |
| TC-ENV-02 | Insert yang melanggar `CHECK (x IN ('A','B'))` | ditolak |
| TC-ENV-03 | Insert duplikat dengan `ON CONFLICT DO NOTHING` | 1 baris |
| TC-ENV-04 | `ON CONFLICT(k) DO UPDATE SET v = excluded.v` | nilai terbarui |
| TC-ENV-05 | `PRAGMA journal_mode=WAL` di file Common | mengembalikan `wal` |
| TC-ENV-06 | `BEGIN IMMEDIATE` … `COMMIT` dan `ROLLBACK` | data sesuai |
| TC-ENV-07 | `TimeGMT()` vs `TimeTradeServer()` | dicetak sebagai INFO; di tester diharapkan sama |

**Verifikasi skrip** (dicek saat task, hasil ditulis di laporan task):

| ID | Langkah | Harapan |
|---|---|---|
| VT-01 | `link-mt5.ps1` dijalankan dua kali | run kedua melapor "sudah terhubung" untuk 7 junction |
| VT-02 | `link-mt5.ps1` ke folder yang berisi folder biasa `Experts\SDBot` | exit 1, folder tidak berubah |
| VT-03 | `build-ea.ps1` pada file uji yang sengaja memicu warning | exit 1, warning tampil |
| VT-04 | `run-ea-tests.ps1 -Unit` dengan satu test sengaja gagal | exit 1, ID test tampil |
| VT-05 | `run-ea-tests.ps1 -Unit` normal | exit 0, `pass=` sesuai jumlah test |
| VT-06 | `mt5-paths.local.json` dihapus | exit 2 dengan petunjuk |
| VT-07 | Terminal uji dibuka manual, lalu runner dijalankan | exit 2, terminal tidak dimatikan |
| VT-08 | Dua runner bersamaan | runner kedua exit 2 |
| VT-09 | `AllSuites` dikosongkan sementara | exit 1 "tidak ada test yang dijalankan" |
| VT-10 | EA uji memanggil `ExpertRemove()` di tengah suite (disimulasikan) | exit 1 "berhenti di tengah" |
| VT-11 | `timeoutSec` = 5 | exit 3, tidak ada proses terminal uji yang tertinggal |
| VT-12 | Repo dipindah ke path berspasi (salinan sementara) | link dan build tetap jalan |

## 6. Traceability

| Requirement | Komponen | Uji |
|---|---|---|
| 1 | folder, `link-mt5.ps1` | VT-01, VT-02 |
| 2 | `build-ea.ps1` | VT-03, VT-06 |
| 3 | `TestFramework.mqh`, `AllSuites.mqh`, entry script/EA | TC-TF-01..06 |
| 4 | `run-ea-tests.ps1`, `Mt5Paths.psm1` | VT-04, VT-05, VT-06 |
| 5 | `TestEnvCheck.mqh` | TC-ENV-01..07 |
| 6 | `SDBot.mq5` | build 0/0, pasang di chart terminal live |
| 7 | `mt5-paths.*.json`, `.gitignore` | `git check-ignore` |
| 8 | `run-ea-tests.ps1`, `build-ea.ps1` | VT-07..12 |

## 7. Terminal uji di mesin ini

Hasil pemeriksaan 2026-09-29:

| Instalasi | Data folder | Login | Pemakaian |
|---|---|---|---|
| `C:\Program Files\MetaTrader 5\Broker B` | `…\Terminal\336EDF3E7DE9B50DE79164ED72A7B9E5` | Exness-MT5Real20 | bot Python (aktif, `config/development.yaml`). **Tidak disentuh runner.** |
| `C:\Program Files\MetaTrader 5\Broker A` | `…\Terminal\A15177F083F06F4EDF29350AB4ECDC24` | Exness-MT5Real20 | terakhir dipakai Mei 2026; tidak ada EA di profil chart, Algo Trading mati. **Dipakai sebagai terminal uji.** |

Keputusan: salinan portable tidak diperlukan; Broker A menjadi terminal uji (disetujui sebagai pengganti opsi portable). Pengaman runner:
- Runner menolak jalan jika proses `terminal64.exe` Broker A sedang berjalan (8.1).
- File konfigurasi runner selalu menyertakan `[Experts] Enabled=0` dan `AllowLiveTrading=0`, sehingga EA di chart (jika kelak ada) tidak jalan saat runner membuka terminal. Strategy Tester tetap bisa menjalankan EA uji (dibuktikan di task 1).
- Terminal tempat SDBot live nanti dijalankan diputuskan di Fase 3 (Broker B dipakai bot Python pada akun yang sama; perlu diputuskan apakah keduanya boleh berjalan bersamaan).

## 8. Temuan spike (task 1, 2026-09-29)

| Temuan | Bukti | Dampak ke design |
|---|---|---|
| Compile CLI jalan lewat path junction; `.ex5` muncul di repo (diabaikan git) | `Result: 0 errors, 1 warnings, 505 ms` untuk EA spike | §3.3 tetap |
| **Exit code MetaEditor tidak bisa dipakai** (1 walau tanpa error) | exit=1 dengan `0 errors` | `build-ea.ps1` hanya membaca baris `Result: N errors, M warnings` di log (sudah di §3.3) |
| **Versi dengan MAJOR 0 selalu memicu warning 68** ("must be xxx.yyy") | `0.0`, `0.00`, `0.01`, `0.1`, `0.10` → warning; `1.0`, `1.00` → bersih | Skema versi diganti: spec 01 = `1.00`, naik `0.01` per spec (spec 07 = `1.06`), `2.00` setelah validasi Fase 6. Diterapkan di README, spec 01 Req 6, spec 04, spec 07 |
| Strategy Tester lewat `/config` + `ShutdownTerminal=1` jalan dan terminal menutup sendiri | run 1 hari M15 model 2: **8 detik** termasuk login; tidak ada proses tersisa | §3.4 tetap; `timeoutSec` 600 cukup longgar |
| File `.set` untuk `ExpertParameters` harus berada di `<data>\MQL5\Profiles\Tester\` | run sukses dengan `.set` di sana | §3.4 langkah 3: `.set` sementara ditulis ke folder itu dan dihapus setelah run |
| File `.ini` dan `.set` UTF-16 LE diterima | run sukses | runner menulis keduanya sebagai UTF-16 LE |
| `FILE_COMMON` dari agen tester menulis ke `%APPDATA%\MetaQuotes\Terminal\Common\Files` | file hasil terbaca | §3.2 `commonFilesDir` benar |
| **SQLite bawaan MT5 versi 3.53.0** | `SELECT sqlite_version()` | UPSERT, `CHECK`, WAL, `BEGIN IMMEDIATE` tersedia; TC-ENV tetap dijalankan di task 7 sebagai pengaman |
| Di tester `TimeGMT() == TimeTradeServer()` | keduanya `2026.09.01 00:00:00` | sesuai asumsi spec 03 §3.2 |
| Kegagalan tester tidak menghasilkan file hasil; alasannya ada di **log terminal** `<data>\logs\yyyymmdd.log` (UTF-16), bukan di `Tester\logs` | `Tester symbol NOSUCHc not exist`, `tester didn't start`, `shutdown with -1000012358 (tester symbol does not exist)` | §3.4 langkah 5 dan §4: saat file hasil tidak ada, runner membaca baris log terminal sejak waktu mulai run yang mengandung `Tester` level 2 atau `shutdown with`, lalu menampilkannya (8.3) |
| Terminal uji login ke akun Exness (`159394302`) saat tester jalan, lalu disconnect saat shutdown | log terminal | aman karena `[Experts] Enabled=0` dan tidak ada EA di chart; tetap dicek setiap run (8.1) |
| Penghapusan file dengan wildcard di `tools/.tmp` diblokir sandbox Claude Code | error "protected from removal" | runner menghapus file sementaranya sendiri per nama file yang ia buat |

### 8.1 Temuan saat membangun runner (task 6)

| Temuan | Penanganan di `run-ea-tests.ps1` |
|---|---|
| Output EA uji dan alasan berhentinya ada di **jurnal tester** `<data>\Tester\logs\yyyymmdd.log` (UTF-16), bukan di folder agen `%APPDATA%\MetaQuotes\Tester\<id>\Agent-*` | Saat baris `END` tidak ada, runner menampilkan 20 baris terakhir jurnal tester |
| `ExpertRemove()` di `OnInit` dicatat tester sebagai "removed itself within OnInit / tester stopped because OnInit failed" | Tidak masalah: hasil sudah ditulis dan di-flush sebelumnya; runner menilai dari file hasil, bukan dari status tester |
| `.ex5` bisa basi bila source dikembalikan tanpa build ulang, lalu `-SkipBuild` menjalankan versi lama (terjadi saat VT-08) | Dengan `-SkipBuild`, runner menolak (exit 2) bila ada `.mq5`/`.mqh` yang lebih baru dari `.ex5` yang akan dijalankan |
| `Get-ChildItem -LiteralPath -Include` di PowerShell 5.1 ikut mencocokkan file lain | Filter ekstensi manual |
| Rentang tanggal tetap bisa tidak punya data di mesin lain | Unit test memakai 7 hari terakhir; skenario menentukan rentangnya sendiri di file `.ini` |
| Unit test 1 minggu model 2: 6–14 detik per run | `timeoutSec` 600 tetap longgar untuk skenario real ticks |
