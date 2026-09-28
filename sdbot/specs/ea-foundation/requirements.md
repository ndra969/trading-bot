# Requirements — EA Foundation (Fase 1)

Status: Approved (2026-09-28)
Sumber: PRD-EA §Platform dan arsitektur, §Akun dan koneksi, §Eksekusi order, §Position management, §Risk management, §Data dan database, §Parameter input EA, §Pengujian, §Roadmap Fase 1 · RULES seluruhnya

## Pendahuluan

Fase 1 membangun fondasi pengaman EA SDBot: validasi akun, eksekusi order yang aman, manajemen posisi (breakeven, partial close, trailing), risk management dengan emergency stop, dan log SQLite. Fase ini selesai jika uji fungsi BE, partial, trailing, dan limit risiko lolos di Strategy Tester visual mode (PRD Roadmap Fase 1).

Termasuk juga kerangka yang dibutuhkan fondasi: `Core/` (Types, Constants, Inputs, Utils, State), `Execution/Executor`, skema `shared/schema/data_db.sql` untuk tabel PRD-EA, skrip `tools/link-mt5.ps1`, dan kerangka unit test.

Tidak termasuk (fase lain): pengiriman notifikasi Telegram, push HP, dan heartbeat (Fase 2); analisis, zona S&D, skor, dan entry dari sinyal (Fase 3); filter berita, sesi, spread, dan eksposur mata uang (Fase 4); modul Control dan tabel backoffice (B1, B5, B6). Di Fase 1, alert hanya dicatat ke log terminal dan tabel `alerts`.

Konteks yang sudah diputuskan: day trading, simbol EURUSD, GBPUSD, EURJPY, GBPJPY dengan akhiran `c`, akun cent Exness mode hedging, mata uang USC.

## Glosarium

- **R**: jarak harga antara entry dan SL awal posisi. Profit dalam R = pergerakan harga menguntungkan ÷ R.
- **Posisi EA**: posisi dengan MagicNumber instance ini dan simbol chart ini.
- **Hari server**: hari kalender menurut waktu server broker (`TimeTradeServer`).
- **Puncak equity**: equity tertinggi akun yang pernah tercatat, disimpan di Global Variable terminal.
- **STOPPED**: status emergency stop per akun. Entry diblokir sampai di-reset manual.
- **Pause**: status sementara yang memblokir entry baru. Posisi yang ada tetap dikelola.
- **Error sementara**: requote, harga berubah, server sibuk, tidak ada harga. Error lain dianggap permanen.

## Requirements

### Requirement 1: Struktur proyek dan build

**User story:** Sebagai developer, saya ingin kode EA di repo langsung terbaca MetaEditor dan selalu compile bersih, agar tidak ada salinan file yang berbeda dan warning tidak menumpuk.

#### Acceptance criteria

1.1. Skrip `tools/link-mt5.ps1` WAJIB membuat junction `Experts/SDBot`, `Include/SDBot`, `Scripts/SDBot`, dan `Presets/SDBot` dari folder data MT5 ke `sdbot/ea/src/`, serta junction folder uji (`Scripts/SDBotTests`, `Experts/SDBotTests`) ke `sdbot/ea/tests/`, dengan path folder data sebagai parameter.
1.2. JIKA junction tujuan sudah ada MAKA skrip WAJIB melewatinya tanpa menghapus isi folder MT5.
1.3. EA dan semua script uji WAJIB compile dengan 0 error dan 0 warning.
1.4. Semua deklarasi `input` WAJIB berada di `Core/Inputs.mqh` saja.

### Requirement 2: Validasi akun saat start

**User story:** Sebagai trader, saya ingin EA menolak jalan di akun atau kondisi yang tidak aman, agar tidak ada order tak sengaja di akun yang salah.

#### Acceptance criteria

2.1. KETIKA EA di-init MAKA EA WAJIB membaca `TERMINAL_CONNECTED`, `TERMINAL_TRADE_ALLOWED`, `MQL_TRADE_ALLOWED`, `ACCOUNT_TRADE_MODE`, dan `ACCOUNT_MARGIN_MODE`.
2.2. JIKA akun bertipe real (termasuk cent) dan `InpAllowLiveTrading = false` MAKA EA WAJIB menghentikan diri, menulis log CRITICAL, dan mencatat alert.
2.3. JIKA mode margin akun bukan hedging MAKA EA WAJIB menghentikan diri dengan pesan yang menyebut mode margin akun.
2.4. JIKA simbol chart ditambah `InpSymbolSuffix` tidak tersedia di Market Watch MAKA EA WAJIB menghentikan diri dengan pesan yang menyebut nama simbol.
2.5. JIKA nilai input di luar batas PRD (misalnya `InpRiskPerTradePct` > 1.0 atau ≤ 0) MAKA EA WAJIB menghentikan diri dan menyebut input serta batasnya.
2.6. KETIKA validasi lolos MAKA EA WAJIB menyimpan atau memperbarui baris akun (login, server, tipe, mata uang, balance, equity, puncak equity) di tabel `accounts`.

### Requirement 3: Koneksi saat berjalan

**User story:** Sebagai trader, saya ingin EA berhenti membuka posisi saat koneksi bermasalah, agar tidak ada keputusan dari data basi.

#### Acceptance criteria

3.1. SELAMA terminal tidak terkoneksi atau trading tidak diizinkan EA WAJIB menahan setiap entry baru.
3.2. KETIKA terputus lebih dari 5 menit MAKA EA WAJIB mencatat alert severity Medium, maksimal sekali per 5 menit.
3.3. KETIKA koneksi pulih MAKA EA WAJIB mencatat alert Info sekali dan melanjutkan tanpa restart.

### Requirement 4: Rekonsiliasi dan restart aman

**User story:** Sebagai trader, saya ingin EA melanjutkan pengelolaan posisi dengan benar setelah restart, update versi, atau PC menyala lagi, agar BE, partial, dan trailing tidak terulang atau terlewat.

#### Acceptance criteria

4.1. KETIKA EA di-init MAKA EA WAJIB mencatat ke log setiap posisi EA yang terbuka di MT5 tetapi belum ada di tabel `trades`.
4.2. KETIKA EA di-init MAKA EA WAJIB memperbarui posisi di tabel `trades` yang sudah tertutup di MT5 menjadi closure, dari history deal.
4.3. EA WAJIB menyimpulkan status BE dari posisi SL relatif terhadap harga entry, dan status partial dari volume saat ini dibanding volume awal.
4.4. EA WAJIB dapat menentukan R awal setiap posisi EA setelah restart, walau SL sudah dipindah ke BE atau trailing. SL awal disimpan di komentar order saat entry, dengan tabel `trades` sebagai cadangan.
4.5. KETIKA EA di-restart saat ada posisi yang sudah BE dan sudah partial MAKA EA WAJIB tidak menggeser BE ulang dan tidak melakukan partial kedua.

### Requirement 5: Perhitungan lot

**User story:** Sebagai trader, saya ingin lot dihitung dari risiko persen dan nilai uang yang sebenarnya, agar risiko per trade benar untuk pair USD dan JPY di akun cent.

#### Acceptance criteria

5.1. EA WAJIB menghitung lot = balance × risiko% ÷ nilai uang jarak SL per 1 lot, dengan nilai uang dari `OrderCalcProfit()` pada harga yang akan dieksekusi.
5.2. EA WAJIB membulatkan lot ke bawah sesuai `SYMBOL_VOLUME_STEP`.
5.3. JIKA lot hasil pembulatan < `SYMBOL_VOLUME_MIN` MAKA EA WAJIB menolak order dan mencatat alasannya, tanpa membulatkan ke atas.
5.4. JIKA lot hasil perhitungan > `SYMBOL_VOLUME_MAX` MAKA EA WAJIB memakai `SYMBOL_VOLUME_MAX`.
5.5. SELAMA flag drawdown 10% aktif EA WAJIB mengalikan risiko per trade dengan 0.5 sebelum menghitung lot.
5.6. EA WAJIB tidak memakai nilai uang tetap dalam kode. Semua batas risiko dalam persen.

### Requirement 6: Eksekusi order aman

**User story:** Sebagai trader, saya ingin setiap order selalu terlindungi dan hasilnya diperiksa, agar tidak ada posisi tanpa SL atau order gagal yang tidak ketahuan.

#### Acceptance criteria

6.1. JIKA permintaan order tidak membawa SL atau TP MAKA EA WAJIB menolaknya sebelum dikirim.
6.2. EA WAJIB mengirim setiap order dengan MagicNumber, SL, TP, dan komentar, dengan SL dan TP dinormalisasi ke digit simbol.
6.3. JIKA jarak SL atau TP dari harga lebih kecil dari stops level + spread, atau harga berada dalam freeze level, MAKA EA WAJIB menolak order dan mencatat alasannya.
6.4. EA WAJIB memilih filling mode dari `SYMBOL_FILLING_MODE`.
6.5. KETIKA broker mengembalikan error sementara MAKA EA WAJIB mencoba ulang maksimal 3 kali dengan jeda.
6.6. JIKA broker mengembalikan error permanen atau retry habis MAKA EA WAJIB mencatat log ERROR dengan retcode dan alert Medium, tanpa retry lagi.
6.7. KETIKA order terisi MAKA EA WAJIB mencatat ke `trades`: ticket, magic, simbol, arah, lot, harga diminta, harga isi, slippage entry (point, negatif jika merugikan), spread saat entry (point), SL, TP, dan risiko uang yang dihitung ulang dari harga isi.
6.8. EA WAJIB hanya mengirim order, close, dan modify lewat satu modul Execution.

### Requirement 7: Breakeven

**User story:** Sebagai trader, saya ingin SL pindah ke titik impas setelah profit 1R, agar trade yang sudah jalan tidak berubah jadi rugi.

#### Acceptance criteria

7.1. KETIKA profit posisi EA ≥ `InpBreakevenR` (default 1.0) R dan BE belum aktif MAKA EA WAJIB memindahkan SL ke harga entry + buffer searah posisi.
7.2. EA WAJIB menghitung buffer BE = spread saat ini + `InpBreakevenBufferPoints` (default 2 point).
7.3. JIKA SL baru tidak lebih baik dari SL sekarang MAKA EA WAJIB tidak mengirim modifikasi.

### Requirement 8: Partial close

**User story:** Sebagai trader, saya ingin mengamankan sebagian profit di 1.5R, agar sebagian hasil terkunci sambil sisa posisi berjalan.

#### Acceptance criteria

8.1. KETIKA profit posisi EA ≥ `InpPartialR` (default 1.5) R dan partial belum dilakukan MAKA EA WAJIB menutup `InpPartialPct` (default 50) persen volume awal, dibulatkan ke bawah sesuai volume step.
8.2. JIKA volume yang akan ditutup atau sisa volume < lot minimum MAKA EA WAJIB melewati partial untuk posisi itu dan mencatatnya sekali ke log.
8.3. KETIKA partial berhasil MAKA EA WAJIB mencatat event `partial` ke `position_events` dengan volume dan spread saat itu.

### Requirement 9: Trailing stop

**User story:** Sebagai trader, saya ingin SL mengikuti harga berdasarkan volatilitas setelah BE, agar profit besar ikut terkunci.

#### Acceptance criteria

9.1. SELAMA BE aktif EA WAJIB menghitung SL trailing = harga saat ini − ATR(`InpTrailATRPeriod`) × `InpTrailATRMult` untuk buy, dan + untuk sell (default 14 dan 2.0), dengan ATR dari timeframe LTF gaya trading (M15 untuk day trading).
9.2. EA WAJIB hanya mengirim SL trailing jika lebih baik dari SL sekarang minimal sebesar langkah minimum (default 5 point).
9.3. EA WAJIB memakai nilai ATR dari bar yang sudah tutup, dengan handle indikator dibuat saat init.

### Requirement 10: Aturan umum modifikasi posisi

**User story:** Sebagai trader, saya ingin semua perubahan SL aman dan tercatat, agar SL tidak pernah memburuk dan kegagalan terlihat.

#### Acceptance criteria

10.1. EA WAJIB memeriksa BE, partial, dan trailing secara independen di setiap tick untuk setiap posisi EA, bukan sebagai rantai if-else.
10.2. JIKA SL baru lebih buruk dari SL sekarang MAKA EA WAJIB menolak modifikasi.
10.3. JIKA SL baru melanggar stops level atau posisi dalam freeze level MAKA EA WAJIB tidak mengirim modifikasi pada tick itu.
10.4. JIKA modifikasi gagal MAKA EA WAJIB mencoba ulang maksimal 3 kali dengan cooldown 30 detik, lalu mencatat event `modify_gagal` dan alert Medium.
10.5. KETIKA BE atau trailing berhasil MAKA EA WAJIB mencatat event ke `position_events` dengan SL lama, SL baru, volume, dan spread.
10.6. EA WAJIB tidak pernah menutup posisi karena SL atau TP tersentuh. Penutupan itu dilakukan server broker.

### Requirement 11: Risk monitor dan drawdown

**User story:** Sebagai trader, saya ingin drawdown dan margin dipantau terus, agar kerugian besar dihentikan otomatis walau tidak ada sinyal baru.

#### Acceptance criteria

11.1. EA WAJIB menjalankan risk monitor setiap 1 detik di `OnTimer`, terpisah dari logika entry.
11.2. KETIKA equity melebihi puncak equity MAKA EA WAJIB memperbarui puncak equity di Global Variable `SDB_<login>_PEAK_EQUITY`.
11.3. KETIKA drawdown dari puncak ≥ 5% MAKA EA WAJIB mencatat alert Info sekali per perubahan level.
11.4. KETIKA drawdown ≥ `InpDDReducePct` (default 10%) MAKA EA WAJIB mengaktifkan flag lot × 0.5 dan mencatat alert High.
11.5. KETIKA flag lot × 0.5 aktif dan drawdown turun di bawah 8% MAKA EA WAJIB menonaktifkan flag dan mencatat alert Info.
11.6. KETIKA drawdown ≥ `InpDDStopPct` (default 15%) MAKA EA WAJIB menutup semua posisi EA di akun, menyetel status STOPPED, dan mencatat alert Critical.
11.7. JIKA margin level < 300% MAKA EA WAJIB mencatat alert High saat status berubah.
11.8. SELAMA margin level < 200% EA WAJIB memblokir entry baru.

### Requirement 12: Batas rugi harian

**User story:** Sebagai trader, saya ingin entry berhenti setelah rugi harian 3%, agar satu hari buruk tidak merusak akun.

#### Acceptance criteria

12.1. KETIKA rugi hari server ini (realized + floating) ≥ `InpDailyLossPct` (default 3%) dari balance saat pergantian hari server MAKA EA WAJIB menyetel pause harian dan mencatat alert High.
12.2. SELAMA pause harian aktif EA WAJIB memblokir entry baru dan tetap mengelola posisi terbuka.
12.3. KETIKA hari server berganti MAKA EA WAJIB mencabut pause harian dan menyimpan balance saat itu sebagai dasar rugi harian di Global Variable.

### Requirement 13: Emergency stop

**User story:** Sebagai trader, saya ingin emergency stop bertahan sampai saya sendiri yang membukanya, agar EA tidak kembali trading setelah drawdown besar tanpa saya tahu.

#### Acceptance criteria

13.1. KETIKA close all dipicu MAKA EA WAJIB mencoba menutup setiap posisi EA yang tersisa setiap 5 detik sampai habis atau pasar tutup.
13.2. JIKA close all gagal 3 kali berturut-turut MAKA EA WAJIB mencatat alert Critical.
13.3. SELAMA status STOPPED EA WAJIB memblokir entry baru, termasuk setelah EA atau terminal di-restart.
13.4. EA WAJIB membuka status STOPPED hanya ketika `InpResetEmergencyStop = true`, lalu menyetel puncak equity ke equity saat itu dan mencatat alert Info.
13.5. EA WAJIB tidak pernah membuka status STOPPED secara otomatis.

### Requirement 14: Pre-trade check

**User story:** Sebagai developer, saya ingin satu pintu pemeriksaan risiko sebelum setiap entry, agar strategi di fase berikutnya tidak bisa melewati aturan risiko.

#### Acceptance criteria

14.1. EA WAJIB menyediakan satu pemeriksaan pre-trade yang dipanggil sebelum setiap entry, dengan urutan: STOPPED/pause, risiko per trade, total risiko terbuka, eksposur mata uang (slot kosong sampai Fase 4), margin.
14.2. JIKA total risiko posisi terbuka ditambah risiko order baru > `InpMaxOpenRiskPct` (default 3%) MAKA pemeriksaan WAJIB menolak, dengan posisi yang sudah BE dihitung 0%.
14.3. KETIKA pemeriksaan menolak MAKA EA WAJIB mengembalikan alasan tolak yang bisa dicatat ke tabel `signals`.

### Requirement 15: Status bersama antar-EA

**User story:** Sebagai trader, saya ingin beberapa EA di satu akun (satu per pair) berbagi status risiko, agar batas akun berlaku untuk semua pair sekaligus.

#### Acceptance criteria

15.1. EA WAJIB menyimpan puncak equity, status STOPPED, pause harian, dan flag lot × 0.5 di Global Variables dengan nama `SDB_<login>_<NAMA>`.
15.2. KETIKA satu instance menyetel STOPPED atau pause MAKA instance lain di akun yang sama WAJIB memblokir entry pada siklus `OnTimer` berikutnya.
15.3. KETIKA emergency stop dipicu MAKA setiap instance WAJIB menutup posisi dengan magic miliknya sendiri.

### Requirement 16: Deteksi posisi tertutup

**User story:** Sebagai trader, saya ingin setiap posisi yang tertutup tercatat dengan alasan dan hasil dalam R, agar performa bisa dievaluasi.

#### Acceptance criteria

16.1. KETIKA deal penutupan posisi EA terjadi MAKA EA WAJIB mendeteksinya di `OnTradeTransaction` dan membaca alasannya dari `DEAL_REASON` (SL, TP, manual, stop out, EA).
16.2. EA WAJIB mencatat ke `closures`: ticket, waktu, alasan, harga SL/TP, harga isi exit, slippage exit (point), profit bersih, komisi, swap, dan R hasil.
16.3. EA WAJIB menghitung R hasil dari profit bersih termasuk komisi dan swap dibanding risiko uang awal.

### Requirement 17: Log SQLite

**User story:** Sebagai trader, saya ingin data trade tersimpan lengkap di satu file SQLite, agar bisa dianalisis dan dibaca backoffice.

#### Acceptance criteria

17.1. EA WAJIB membuka satu file `sdbot.sqlite` di folder Common (`DATABASE_OPEN_COMMON`) dengan mode WAL dan busy timeout 2 detik.
17.2. EA WAJIB membuat tabel `accounts`, `signals`, `trades`, `position_events`, `closures`, dan `alerts` sesuai `shared/schema/data_db.sql` jika belum ada.
17.3. SELAMA mode optimasi (`MQL_OPTIMIZATION`) EA WAJIB tidak menulis ke database.
17.4. JIKA penulisan database gagal MAKA EA WAJIB mencatat log ERROR dan melanjutkan trading tanpa berhenti.
17.5. EA WAJIB menyimpan waktu dalam UTC epoch detik.
17.6. EA WAJIB membedakan data per nomor akun, sehingga beberapa akun dan instance bisa memakai file yang sama.

### Requirement 18: Log terminal

**User story:** Sebagai developer, saya ingin log terminal yang seragam dan bisa difilter, agar masalah cepat ditemukan.

#### Acceptance criteria

18.1. EA WAJIB menulis log dengan format `[SDB][LEVEL][Modul][Simbol] pesan | kunci=nilai`.
18.2. EA WAJIB menampilkan log DEBUG hanya jika `InpLogLevel = DEBUG`.
18.3. JIKA error terjadi MAKA log WAJIB menyertakan kode error (`GetLastError()` atau retcode) dan konteksnya.
18.4. EA WAJIB mencatat alert Critical, High, Medium, dan Info ke tabel `alerts` dengan status kirim `PENDING` (pengiriman oleh Notifier di Fase 2).

### Requirement 19: Mode Strategy Tester

**User story:** Sebagai developer, saya ingin EA berjalan benar di Strategy Tester dan optimasi, agar uji fungsi dan backtest bisa dipercaya.

#### Acceptance criteria

19.1. SELAMA berjalan di Strategy Tester EA WAJIB tidak memanggil `WebRequest` atau fungsi kalender.
19.2. EA WAJIB mengembalikan metrik `OnTester` = expectancy per trade dalam R ÷ max drawdown (%).
19.3. Repo WAJIB menyediakan EA harness terpisah di `ea/tests/` yang memakai modul yang sama dengan EA utama dan membuka posisi uji terjadwal, untuk skenario BE, partial, trailing, dan limit risiko.
19.4. JIKA harness tidak berjalan di Strategy Tester MAKA harness WAJIB menolak jalan. EA utama WAJIB tidak berisi kode pembuka posisi uji.

### Requirement 20: Pengujian fondasi

**User story:** Sebagai developer, saya ingin fungsi murni teruji otomatis dan skenario PRD bisa diulang, agar Fase 1 terbukti sebelum strategi ditambahkan.

#### Acceptance criteria

20.1. Setiap fungsi murni (lot, pembulatan, R, profit dalam R, buffer BE, SL trailing, validasi SL lebih baik, drawdown, rugi harian) WAJIB punya unit test di `ea/tests/Scripts/SDBotTests/` yang mencetak `ALL PASS`.
20.2. Repo WAJIB berisi file `.ini` Strategy Tester di `ea/tests/scenarios/` untuk skenario: BE, partial, trailing, rugi harian 3%, drawdown 15% dan STOPPED setelah restart, lot di bawah minimum, posisi ditutup manual, akun real dengan `AllowLiveTrading = false`.
20.3. Repo WAJIB berisi file `.set` contoh untuk day trading tanpa nilai rahasia.

## Keputusan (dijawab 2026-09-28)

1. **Dasar rugi harian**: balance saat pergantian hari server (12.1, 12.3).
2. **Timeframe ATR trailing**: LTF gaya trading, M15 untuk day trading (9.1).
3. **Buffer BE**: spread saat ini + `InpBreakevenBufferPoints` (default 2), karena akun cent Exness tanpa komisi per lot (7.2).
4. **R awal setelah restart**: SL awal di komentar order, tabel `trades` sebagai cadangan (4.4).
5. **Partial dengan lot kecil**: diterima. Jika volume yang ditutup atau sisanya < lot minimum, partial dilewati dan dicatat (8.2).
6. **Posisi uji**: EA harness terpisah di `ea/tests/`, EA utama bersih dari kode uji (19.3, 19.4).
