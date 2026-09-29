# Implementation plan — 01 Tooling

Status: Draft
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

Setiap task diverifikasi sebelum dicentang. Hasil verifikasi (VT-xx, TC-xx) ditulis di laporan task.

- [x] 1. Spike: buktikan compile CLI dan Strategy Tester lewat `/config` di terminal uji
  - Isi `sdbot/tools/mt5-paths.local.json` (Broker A = terminal uji, Broker B = terminal bot Python yang tidak disentuh) dan tambahkan `*.local.json`, `tools/.tmp/` ke `sdbot/.gitignore`
  - Buat EA spike sementara di `ea/tests/Experts/SDBotTests/Spike.mq5`: di `OnInit` menulis `sdbot_spike_<runId>.txt` ke Common (versi SQLite, `TimeGMT`, `TimeTradeServer`, `MQL_TESTER`), lalu `ExpertRemove()`
  - Buat satu junction sementara `Experts\SDBotTests` di data folder Broker A, compile lewat `MetaEditor64.exe /compile /log`, parse hasilnya
  - Jalankan `terminal64.exe` Broker A dengan ini `[Tester]` + `[Experts] Enabled=0` + `ShutdownTerminal=1`, tunggu proses selesai, baca file hasil di Common
  - Catat temuan di design (§3.4 dan §7): apakah terminal benar-benar menutup sendiri, lama run, lokasi log tester, bentuk error bila data historis tidak ada
  - Hapus EA spike setelah temuan dicatat (framework asli dibuat di task 5)
  - _Requirements: 2.1, 4.1, 5.2, 8.6_

- [x] 2. Kerangka folder dan konfigurasi lokal
  - Buat folder `ea/src/...` dan `ea/tests/...` sesuai design §2 (dengan `.gitkeep`) dan `tools/mt5-paths.example.json`
  - Verifikasi `git check-ignore` untuk `mt5-paths.local.json` dan `tools/.tmp/`
  - _Requirements: 1.1, 7.1, 7.2_

- [x] 3. `link-mt5.ps1`
  - Tulis skrip sesuai design §3.1 (7 junction, lewati yang sudah terhubung, berhenti pada folder biasa atau junction lain)
  - Jalankan untuk data folder Broker A; verifikasi VT-01 (dua kali jalan), VT-02 (folder biasa di data folder sementara), VT-12 (repo salinan di path berspasi, di folder sementara)
  - _Requirements: 1.2, 1.3, 1.4, 1.5, 8.7_
  - Hasil (2026-09-29): VT-01 lolos di Broker A (run 1: 6 dibuat + 1 sudah ada dari spike; run 2: 7 sudah terhubung, exit 0). VT-02 lolos (folder biasa + junction ke tempat lain dilaporkan sekaligus, exit 1, tidak ada perubahan). VT-12 lolos (repo dan data folder berspasi, 7 dibuat lalu 7 sudah terhubung). Catatan: `$PSScriptRoot` kosong di default parameter PowerShell 5.1, default dihitung di badan skrip.

- [x] 4. `Mt5Paths.psm1` dan `build-ea.ps1`
  - Modul membaca dan memvalidasi `mt5-paths.local.json` (path ada, terminal uji ≠ terminal live)
  - `build-ea.ps1` sesuai design §3.3 (target default, compile lewat path junction, parse log UTF-16, kode keluar 0/1/2)
  - Verifikasi VT-03 (file uji sementara yang memicu warning), VT-06 (konfigurasi dihapus)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 7.1_
  - Hasil (2026-09-29): VT-03 lolos (tanpa target: exit 1; file bersih: exit 0; warning 43 konversi dan warning 68 versi: exit 1 dengan baris pesan; error 154: exit 1, pesan tidak ganda). VT-06 lolos (config tidak ada, JSON rusak, test = live, target di luar folder link: exit 2 dengan petunjuk). Catatan: MQL5 tidak memberi warning untuk variabel lokal yang tidak dipakai; `$args` jangan dipakai sebagai nama variabel di skrip PowerShell.

- [x] 5. Framework unit test (TDD pada dirinya sendiri)
  - Red: tulis `Suites/TestFrameworkSelf.mqh` (TC-TF-01..06) dan `AllSuites.mqh` terhadap stub `TestFramework.mqh` yang belum menghitung apa pun → hasil tidak sesuai harapan
  - Green: implementasi `TestFramework.mqh` sesuai design §3.5 (assert, hitungan, `TfMute`, format baris, file hasil ber-`runId`)
  - Entry point `Scripts/SDBotTests/RunUnitTests.mq5` dan `Experts/SDBotTests/RunUnitTestsEA.mq5` (input `InpTestRunId`, `ExpertRemove()` setelah selesai)
  - Verifikasi: build 0/0; script dijalankan sekali di chart Broker A (manual) menampilkan hasil yang sama dengan EA runner di task 6
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_ · _Tests: TC-TF-01..06_
  - Hasil (2026-09-29): Red dengan stub = tidak ada file hasil (runner akan gagal). Green = `RUN … END pass=7 fail=0` lewat EA runner di tester Broker A (runner sementara, sebelum task 6). Cek tambahan: assert gagal sungguhan tercetak `FAIL TC-TMP sengaja gagal | expected=0.31 actual=0.3` dan `fail=1`, lalu dihapus. Build 0/0 untuk kedua entry point. **Tertunda (manual)**: menjalankan script `RunUnitTests` di chart Broker A sekali untuk membandingkan hasil dengan EA runner.

- [ ] 6. `run-ea-tests.ps1`
  - Implementasi design §3.4 dan kondisi tepi §4: lock file, cek proses terminal uji, ini + `.set` sementara, timeout dengan kill, parse hasil, kode keluar 0/1/2/3, validasi `END` dan jumlah test > 0
  - Verifikasi VT-04, VT-05, VT-07, VT-08, VT-09, VT-10, VT-11
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 7. Suite `EnvCheck`
  - Red: TC-ENV-01..07 ditulis dulu dan dijalankan lewat runner (akan FAIL sampai helper DB uji ada)
  - Green: helper buka/hapus `sdbot_envcheck.sqlite`, eksekusi SQL, baca hasil; catat versi SQLite dan hubungan waktu sebagai `INFO`
  - Jalankan juga lewat script di chart Broker A untuk membandingkan `TimeGMT`/`TimeTradeServer` live vs tester
  - Jika ada fitur yang FAIL: berhenti dan laporkan dampaknya ke design spec 03 sebelum lanjut
  - _Requirements: 5.1, 5.2, 5.3_ · _Tests: TC-ENV-01..07_

- [ ] 8. EA kerangka `SDBot.mq5` v1.00
  - `#property version "1.00"`, handler kosong yang aman, log INFO saat init
  - Verifikasi: `build-ea.ps1` 0/0 untuk semua target; `run-ea-tests.ps1 -Unit` exit 0
  - _Requirements: 6.1, 6.2_

## Validasi manual (di luar tasks)

- Pasang `SDBot.mq5` v1.00 di satu chart Broker A, pastikan log INFO muncul dan tidak ada aktivitas lain (6.2).
