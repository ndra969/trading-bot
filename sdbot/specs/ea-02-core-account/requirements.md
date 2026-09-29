# Requirements — 02 Core dan akun

Status: Draft
Use case: UC-03 (validasi), UC-04 ([overview](../fase-1-overview.md))
Asal: ea-foundation R1.4, R2, R3, R15.1, R18.1–18.3
Butuh: spec 01

## Pendahuluan

Spec ini membangun lapisan Core yang dipakai semua modul (tipe, konstanta, input, fungsi umum, log terminal, status bersama di Global Variables, dan interface pencatat event), serta modul Account yang memutuskan apakah EA boleh jalan dan boleh trading.

Selesai jika suite `CoreUtils`, `AccountRules`, `State`, dan `Log` ALL PASS lewat runner, EA kerangka memakai modul ini dan compile 0/0, dan MC-01..04 dicek di terminal live.

## Glosarium

- **Validasi tertunda**: EA sudah di-init tetapi akun belum bisa divalidasi karena terminal belum terkoneksi. Tidak ada entry dan manajemen posisi sampai validasi selesai.
- **Boleh trading**: terkoneksi, trading diizinkan terminal dan EA, dan simbol bisa ditradingkan.
- **Event sink**: interface tempat modul mengirim event untuk dicatat (implementasinya di spec 03).

## Requirements

### Requirement 1: Input dan validasinya

**User story:** Sebagai trader, saya ingin EA menolak input yang berbahaya atau tidak masuk akal, agar salah ketik tidak berubah jadi risiko besar.

#### Acceptance criteria

1.1. Semua deklarasi `input` WAJIB berada di `Core/Inputs.mqh`, dengan nama `Inp` + nama di PRD dan nilai default dari PRD.
1.2. KETIKA EA di-init MAKA EA WAJIB memvalidasi input terhadap batas di design §4.3 sebelum langkah lain.
1.3. JIKA ada input di luar batas MAKA EA WAJIB gagal init (`INIT_PARAMETERS_INCORRECT`) dan menyebut semua input yang salah beserta batasnya dalam satu pesan.
1.4. JIKA `InpMaxOpenRiskPct` < `InpRiskPerTradePct`, atau `InpBreakevenR` ≥ `InpPartialR`, atau `InpDDReducePct` ≥ `InpDDStopPct` MAKA validasi WAJIB gagal dengan alasan hubungan antar-input tersebut.
1.5. KETIKA trader mengubah input saat EA berjalan MAKA EA WAJIB memvalidasi ulang seluruh input pada init berikutnya.
1.6. JIKA `InpMagicNumber` berada di luar blok SDBot `2026091900`–`2026091999` MAKA validasi WAJIB gagal dan menyebut rentang yang benar. Nomor `…00` dicadangkan untuk harness uji (keputusan R2-1, disetujui 2026-09-29).

### Requirement 2: Validasi akun dan simbol

**User story:** Sebagai trader, saya ingin EA menolak akun, mode margin, atau simbol yang salah, agar tidak ada order di tempat yang tidak dimaksud.

#### Acceptance criteria

2.1. KETIKA terminal terkoneksi dan login akun tersedia MAKA EA WAJIB memvalidasi `ACCOUNT_TRADE_MODE`, `ACCOUNT_MARGIN_MODE`, dan simbol chart.
2.2. JIKA akun bertipe real (termasuk cent) dan `InpAllowLiveTrading = false` MAKA EA WAJIB berhenti, menulis log CRITICAL, dan mengirim alert Critical ke event sink.
2.3. JIKA mode margin bukan hedging MAKA EA WAJIB berhenti dengan pesan yang menyebut mode margin akun.
2.4. JIKA `InpSymbolSuffix` tidak kosong dan simbol chart tidak berakhiran suffix itu MAKA EA WAJIB berhenti dengan pesan yang menyebut simbol dan suffix.
2.5. JIKA simbol chart tidak ada di Market Watch MAKA EA WAJIB mencoba menambahkannya (`SymbolSelect`), dan berhenti jika gagal.
2.6. JIKA saat init terminal belum terkoneksi atau login akun = 0 MAKA EA WAJIB masuk validasi tertunda, bukan gagal init, lalu memvalidasi pada siklus timer pertama setelah terkoneksi.
2.7. SELAMA validasi tertunda EA WAJIB tidak membuka posisi dan tidak mengelola posisi.
2.8. JIKA validasi tertunda gagal MAKA EA WAJIB melepas dirinya dari chart (`ExpertRemove`) dengan log dan alert yang sama seperti 2.2–2.5.
2.9. KETIKA trader login ke akun lain saat EA terpasang MAKA EA WAJIB menjalankan validasi ulang untuk akun baru.
2.10. KETIKA validasi lolos MAKA EA WAJIB mengirim snapshot akun (login, server, perusahaan, tipe, mode margin, mata uang, leverage, balance, equity) ke event sink.

### Requirement 3: Izin trading dan koneksi

**User story:** Sebagai trader, saya ingin EA berhenti mengirim order saat trading tidak mungkin atau tidak diizinkan, agar tidak ada order dari data basi dan log tidak dibanjiri error.

#### Acceptance criteria

3.1. EA WAJIB menilai "boleh trading" dari `TERMINAL_CONNECTED`, `TERMINAL_TRADE_ALLOWED`, `MQL_TRADE_ALLOWED`, `ACCOUNT_TRADE_ALLOWED`, `ACCOUNT_TRADE_EXPERT`, dan `SYMBOL_TRADE_MODE`.
3.2. SELAMA tidak boleh trading EA WAJIB menahan entry baru, dan modul lain bisa membaca alasannya.
3.3. KETIKA terputus lebih dari 5 menit MAKA EA WAJIB mengirim alert Medium, lalu paling sering sekali per 5 menit selama masih terputus.
3.4. JIKA putus kurang dari 5 menit MAKA EA WAJIB hanya mencatat log WARN, tanpa alert.
3.5. KETIKA koneksi pulih setelah alert Medium terkirim MAKA EA WAJIB mengirim alert Info sekali.
3.6. JIKA izin trading dimatikan (tombol Algo Trading, izin EA, atau simbol close-only) MAKA EA WAJIB mencatat log WARN sekali per perubahan status dan menyebut izin mana yang mati.
3.7. EA WAJIB tidak menganggap pasar tutup (akhir pekan, libur) sebagai putus koneksi.

### Requirement 4: Status bersama di Global Variables

**User story:** Sebagai trader, saya ingin status risiko akun bertahan saat restart atau crash dan terbaca semua instance, agar emergency stop tidak hilang diam-diam.

#### Acceptance criteria

4.1. EA WAJIB menyimpan status akun di Global Variables bernama `SDB_<login>_<NAMA>` (daftar di design §4.5).
4.2. JIKA sebuah Global Variable belum ada MAKA EA WAJIB memakai nilai awal yang aman di design §4.5 dan langsung menyimpannya.
4.3. KETIKA status STOPPED, pause harian, atau flag lot × 0.5 berubah MAKA EA WAJIB langsung menyimpan Global Variables ke disk (`GlobalVariablesFlush`), agar tidak hilang saat terminal crash.
4.4. EA WAJIB menyentuh setiap Global Variable miliknya minimal sekali sehari, agar tidak dihapus otomatis oleh MT5 karena tidak diakses selama 4 minggu.
4.5. Kelas state WAJIB menerima prefix nama sebagai parameter, agar unit test tidak menyentuh status akun sungguhan.

### Requirement 5: Log terminal

**User story:** Sebagai developer, saya ingin log yang seragam, bisa difilter, dan tidak membanjir, agar masalah cepat ditemukan.

#### Acceptance criteria

5.1. EA WAJIB menulis log dengan format `[SDB][LEVEL][Modul][Simbol] pesan | kunci=nilai`.
5.2. EA WAJIB menampilkan log DEBUG hanya jika `InpLogLevel = DEBUG`, dan log di bawah level yang dipilih tidak dicetak.
5.3. JIKA error terjadi MAKA log WAJIB menyertakan kode error (`GetLastError()` atau retcode) dan konteksnya.
5.4. EA WAJIB menyediakan log dengan kunci throttle: pesan dengan kunci yang sama dicetak paling sering sekali per interval yang ditentukan pemanggil, dengan jumlah pesan yang ditahan disebut di cetakan berikutnya.
5.5. Modul WAJIB menulis log hanya lewat fungsi di `Core/Utils.mqh`, tidak lewat `Print` langsung.

### Requirement 6: Event sink

**User story:** Sebagai developer, saya ingin modul mencatat event tanpa bergantung pada Storage, agar aturan lapisan terjaga dan event bisa di-assert di unit test.

#### Acceptance criteria

6.1. Core WAJIB mendefinisikan interface `ISdbEventSink` dengan method untuk setiap jenis event Fase 1 (design §3.6).
6.2. Core WAJIB menyediakan implementasi `CNullSink` yang tidak melakukan apa pun, dipakai saat storage tidak tersedia.
6.3. Framework uji WAJIB menyediakan `CFakeSink` yang menyimpan event yang diterima untuk di-assert.
6.4. JIKA modul menerima pointer sink `NULL` MAKA modul WAJIB memakai `CNullSink`, tidak crash.

### Requirement 7: Timeframe per gaya

**User story:** Sebagai developer, saya ingin satu sumber tabel timeframe per gaya trading, agar semua modul memakai TF yang sama.

#### Acceptance criteria

7.1. EA WAJIB menurunkan HTF, MTF, dan LTF dari `InpTradingStyle` sesuai tabel PRD (day trading: H4, H1, M15).
7.2. Timeframe chart WAJIB tidak memengaruhi timeframe yang dipakai EA.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | MT5 baru dibuka, EA di-init sebelum login selesai (login = 0) | Validasi tertunda, tidak gagal init | 2.6, 2.7 |
| EC-02 | Trader login ke akun demo lain saat EA terpasang | Validasi ulang, status GV akun baru dipakai | 2.9, 4.1 |
| EC-03 | Tombol Algo Trading dimatikan | Entry ditahan, WARN sekali | 3.6 |
| EC-04 | Koneksi putus-sambung tiap 2 menit selama 20 menit | Tidak ada alert (tidak pernah ≥ 5 menit berturut-turut), WARN per kejadian | 3.3, 3.4 |
| EC-05 | Akhir pekan | Bukan putus koneksi, tidak ada alert | 3.7 |
| EC-06 | Terminal crash tepat setelah STOPPED disetel | STOPPED tetap ada setelah restart karena di-flush | 4.3 |
| EC-07 | EA tidak dijalankan 5 minggu | GV tidak ada; dipakai nilai awal aman (tidak STOPPED, puncak = equity sekarang) dan log WARN "status risiko direset karena GV hilang" | 4.2, 4.4 |
| EC-08 | Chart EURUSD (tanpa `c`) dengan suffix `c` | Berhenti dengan pesan simbol/suffix | 2.4 |
| EC-09 | Beberapa input salah sekaligus | Satu pesan berisi semua kesalahan | 1.3 |
| EC-10 | Pesan "trading tidak diizinkan" setiap tick | Dicetak paling sering sekali per interval, jumlah yang ditahan disebut | 5.4 |
