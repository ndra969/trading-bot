# Requirements — 01 Tooling (build, uji, lingkungan)

Status: Approved (2026-09-29)
Use case: UC-01, UC-02 ([overview](../fase-1-overview.md))
Asal: ea-foundation R1, R20.1, R20.4, keputusan design runner otomatis

## Pendahuluan

Spec ini menyiapkan semua alat sebelum kode trading pertama ditulis: kerangka folder EA di repo, junction ke MT5, compile dari command line, framework unit test, runner yang menjalankan uji di Strategy Tester secara otomatis, dan pengecekan kemampuan SQLite bawaan MT5. Tidak ada logika trading di spec ini.

Spec ini selesai jika `build-ea` meng-compile kerangka EA dengan 0 error dan 0 warning, dan `run-ea-tests` menjalankan self-test framework serta cek lingkungan dengan hasil yang benar (termasuk mendeteksi test yang sengaja gagal).

## Glosarium

- **Terminal live**: instalasi MT5 yang login ke akun cent dan menjalankan EA di chart.
- **Terminal uji**: instalasi MT5 terpisah dari terminal yang menjalankan bot/EA live, hanya dipakai runner untuk Strategy Tester. Di mesin ini: `C:\Program Files\MetaTrader 5\Broker A`.
- **Suite**: kumpulan test case dalam satu file `.mqh`.
- **Runner**: skrip yang meng-compile, menjalankan suite di Strategy Tester, dan membaca hasilnya.

## Requirements

### Requirement 1: Kerangka folder dan junction

**User story:** Sebagai developer, saya ingin kode EA dan kode uji di repo langsung terbaca MetaEditor, agar tidak ada salinan file yang berbeda.

#### Acceptance criteria

1.1. Repo WAJIB berisi kerangka folder `sdbot/ea/src/` dan `sdbot/ea/tests/` sesuai RULES dan design §2.
1.2. Skrip `tools/link-mt5.ps1` WAJIB membuat junction dari folder data MT5 yang diberikan sebagai parameter ke `Experts/SDBot`, `Include/SDBot`, `Scripts/SDBot`, `Presets/SDBot`, `Experts/SDBotTests`, `Include/SDBotTests`, dan `Scripts/SDBotTests` di repo.
1.3. JIKA junction tujuan sudah ada dan menunjuk ke repo MAKA skrip WAJIB melewatinya dan melaporkannya sebagai "sudah terhubung".
1.4. JIKA di lokasi tujuan ada folder biasa (bukan junction) MAKA skrip WAJIB berhenti tanpa menghapus atau memindahkan isinya, dan menyebut path-nya.
1.5. Skrip WAJIB bisa dijalankan untuk lebih dari satu folder data (terminal live dan terminal uji).

### Requirement 2: Build dari command line

**User story:** Sebagai developer, saya ingin compile EA dari terminal dengan hasil yang tegas, agar warning tidak lolos dan build bisa dipakai di siklus TDD.

#### Acceptance criteria

2.1. Skrip `tools/build-ea.ps1` WAJIB meng-compile target yang diminta (default: EA utama dan semua entry point uji) lewat `metaeditor64.exe` dengan path dari `tools/mt5-paths.local.json`.
2.2. KETIKA compile selesai MAKA skrip WAJIB menampilkan jumlah error dan warning per target beserta baris pesannya.
2.3. JIKA ada error atau warning pada target mana pun MAKA skrip WAJIB keluar dengan kode 1.
2.4. JIKA file konfigurasi atau MetaEditor tidak ditemukan MAKA skrip WAJIB keluar dengan kode 2 dan menampilkan cara mengisinya.

### Requirement 3: Framework unit test

**User story:** Sebagai developer, saya ingin framework assert sederhana yang hasilnya bisa dibaca manusia dan mesin, agar TDD di MQL5 bisa dijalankan.

#### Acceptance criteria

3.1. Framework WAJIB menyediakan assert untuk angka dengan toleransi, boolean, integer, dan string, masing-masing dengan ID test case dan deskripsi.
3.2. KETIKA assert gagal MAKA framework WAJIB mencetak ID, deskripsi, nilai harapan, dan nilai aktual.
3.3. Framework WAJIB menghitung PASS dan FAIL per suite dan total, lalu mencetak ringkasan `ALL PASS` atau `FAILED: <n>`.
3.4. Framework WAJIB menulis hasil ke file di folder Common dengan format baris per test case yang bisa dibaca runner, beserta ID run.
3.5. Suite WAJIB bisa dijalankan dari script (manual, di chart) dan dari EA runner (otomatis, di Strategy Tester) tanpa menulis ulang test case.
3.6. Framework WAJIB punya self-test yang membuktikan assert yang gagal benar-benar terhitung sebagai FAIL.

### Requirement 4: Runner otomatis

**User story:** Sebagai developer, saya ingin satu perintah yang meng-compile dan menjalankan semua uji lalu memberi hasil lulus/gagal, agar Claude bisa menjalankan siklus Red/Green tanpa saya membuka MT5.

#### Acceptance criteria

4.1. Skrip `tools/run-ea-tests.ps1` WAJIB meng-compile lewat `build-ea.ps1`, menjalankan EA runner di Strategy Tester terminal uji lewat file konfigurasi, menunggu terminal selesai, lalu membaca file hasil run tersebut.
4.2. Skrip WAJIB keluar dengan kode 0 jika semua test lulus, 1 jika ada yang gagal atau compile gagal, 2 jika lingkungan belum siap, dan 3 jika melewati batas waktu.
4.3. Skrip WAJIB memakai ID run unik, sehingga hasil run sebelumnya tidak pernah terbaca sebagai hasil run sekarang.
4.4. Skrip WAJIB menolak memakai folder data terminal live sebagai terminal uji.
4.5. BILA parameter skenario diberikan skrip WAJIB menjalankan harness dengan konfigurasi skenario itu (dipakai mulai spec 04).

### Requirement 5: Cek lingkungan MT5

**User story:** Sebagai developer, saya ingin tahu pasti fitur SQLite dan waktu yang tersedia di MT5, agar desain storage tidak bergantung pada asumsi.

#### Acceptance criteria

5.1. Suite `EnvCheck` WAJIB mencetak versi SQLite bawaan MT5 dan menguji fitur yang dipakai spec 03: `CHECK`, `UNIQUE`, `INSERT ... ON CONFLICT DO NOTHING/UPDATE`, mode WAL di folder Common, dan transaksi `BEGIN IMMEDIATE`.
5.2. Suite `EnvCheck` WAJIB mencatat hubungan `TimeGMT()` dan `TimeTradeServer()` di Strategy Tester dan di terminal live.
5.3. JIKA fitur yang dibutuhkan tidak tersedia MAKA hasilnya WAJIB FAIL dengan nama fiturnya, sehingga design spec 03 diubah sebelum dikerjakan.

### Requirement 6: Kerangka EA

**User story:** Sebagai developer, saya ingin EA kerangka yang sudah compile bersih, agar pipeline build diuji dengan file nyata sejak awal.

#### Acceptance criteria

6.1. `Experts/SDBot/SDBot.mq5` WAJIB compile 0 error 0 warning dengan `#property version "1.00"` dan handler event kosong yang aman (tidak mengirim order).
6.2. KETIKA EA kerangka dipasang di chart MAKA EA WAJIB mencatat log INFO bahwa ini versi kerangka, lalu tidak melakukan apa pun.

### Requirement 7: Konfigurasi lokal

**User story:** Sebagai developer, saya ingin path mesin lokal tidak masuk git, agar repo tetap bersih dan tidak membocorkan info akun.

#### Acceptance criteria

7.1. Path MetaEditor, terminal live, dan terminal uji WAJIB dibaca dari `tools/mt5-paths.local.json` yang diabaikan git.
7.2. Repo WAJIB berisi `tools/mt5-paths.example.json` tanpa nilai asli.

### Requirement 8: Kondisi tepi runner dan build

**User story:** Sebagai developer, saya ingin runner tidak pernah melaporkan "lulus" palsu, agar hasil TDD bisa dipercaya.

#### Acceptance criteria

8.1. JIKA terminal uji sudah berjalan saat runner dimulai MAKA runner WAJIB keluar dengan kode 2 dan meminta terminal itu ditutup, tanpa mematikannya sendiri.
8.2. JIKA dua runner dijalankan bersamaan MAKA runner kedua WAJIB keluar dengan kode 2 (file kunci di `tools/.tmp/`).
8.3. JIKA data historis simbol uji tidak tersedia di terminal uji MAKA runner WAJIB keluar dengan kode 1 dan menyebut simbol serta rentang tanggalnya.
8.4. JIKA file hasil ada tetapi tidak berisi baris `END` (EA uji crash di tengah) MAKA runner WAJIB menganggapnya gagal.
8.5. JIKA jumlah test case yang dijalankan 0 MAKA runner WAJIB menganggapnya gagal.
8.6. KETIKA runner dihentikan karena timeout MAKA runner WAJIB memastikan proses terminal uji ikut berhenti.
8.7. Skrip WAJIB bekerja dengan path yang mengandung spasi.
