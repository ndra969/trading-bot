# Requirements — 08 Notifier core

Status: Done (2026-10-01)
Use case: UC-20, UC-21, UC-22, UC-23, UC-24 ([overview](../fase-2-overview.md))
Asal: PRD-EA §Notifikasi (tabel event, diagram alur, kebutuhan), §Data dan database (`alerts`); RULES §Lapisan (Notify), §Aturan wajib (hanya Storage menulis DB, hanya Notify memanggil `WebRequest`/`SendNotification`); PC-06 (format bot Python, penanda SDBot); python-bot-lessons §2 (escape HTML), §3 (antrean, tanda mode)
Butuh: spec 01–07

## Pendahuluan

Spec ini membangun notifier tanpa jaringan: menerima event yang sudah dikirim modul Fase 1, memutuskan apakah dikirim (severity, cooldown, kuota, pesan basi), memformat pesan seperti bot Python, mengantrekan dengan prioritas Critical, menyerahkan ke transport di `OnTimer`, dan mencatat hasilnya di tabel `alerts`. Transport yang ada di spec ini hanya transport log (live dan tester) serta transport palsu untuk uji.

Tidak termasuk (spec 09): `WebRequest` ke Telegram, klasifikasi respons HTTP, push HP, heartbeat, laporan harian, pesan start/stop, pemimpin per akun, skrip `.local.set`. Notifikasi sinyal masuk di Fase 3.

Selesai jika suite NotifyRules ALL PASS, skenario SC-10 PASS, seluruh regresi Fase 1 tetap PASS, compile 0/0, dan EA naik ke versi `1.07`.

## Glosarium

- **Notifikasi**: satu pesan yang akan dikirim ke trader, berasal dari satu `AlertEvent` atau satu event trade.
- **Event trade**: posisi dibuka (`TradeRecord`) atau posisi tutup (`ClosureRecord`). BE, partial, dan SL dipasang kembali sudah berupa `AlertEvent` sejak spec 06.
- **Transport**: penerus pesan yang sudah diformat (log, Telegram di spec 09, palsu di uji). Hasilnya: terkirim, gagal sementara, dibatasi (dengan waktu tunggu), atau gagal permanen.
- **Lingkup akun / lingkup instance**: tipe alert tentang akun (drawdown, rugi harian, margin, koneksi, operasi saldo, status bersama) berlaku sekali per akun; tipe tentang posisi atau order instance berlaku per instance.
- **Jam kuota**: jam server berjalan (misalnya 14:00–14:59) tempat kuota 20 pesan dihitung.
- **Waktu notifier**: `TimeTradeServer()` di live (tetap berjalan saat pasar tutup), `TimeCurrent()` di tester.

## Requirements

### Requirement 1: Menerima event

**User story:** Sebagai trader, saya ingin semua alert dan event trade yang sudah dicatat EA juga sampai ke saya, tanpa mengubah modul yang menghasilkannya.

#### Acceptance criteria

1.1. EA WAJIB meneruskan setiap `AlertEvent` (semua tipe di `enums.md`) ke notifier, di samping pencatatan ke DB yang sudah ada.
1.2. KETIKA posisi instance dibuka MAKA notifier WAJIB membuat satu notifikasi Info berisi simbol, arah, volume, harga isi, SL, TP, dan risiko (% dan mata uang akun).
1.3. KETIKA posisi instance tutup MAKA notifier WAJIB membuat satu notifikasi berisi simbol, arah, alasan tutup, profit bersih dalam mata uang akun, R hasil (atau "-" bila tidak diketahui), dan lama posisi; level SUCCESS bila profit bersih > 0, Info bila ≤ 0.
1.4. Posisi yang tercatat lewat rekonsiliasi (`RECONCILED`) WAJIB tidak menghasilkan notifikasi "posisi dibuka".
1.5. Kegagalan apa pun di notifier WAJIB tidak menghentikan atau menunda trading, risk monitor, maupun pencatatan DB.

### Requirement 2: Aturan kirim

**User story:** Sebagai trader, saya ingin pesan penting selalu sampai dan pesan rutin tidak membanjiri chat yang juga dipakai bot Python.

#### Acceptance criteria

2.1. Notifikasi Critical WAJIB selalu masuk antrean, tanpa cooldown dan tanpa kuota.
2.2. Notifikasi High WAJIB masuk antrean setiap kali diterima (modul penghasilnya sudah mengirim hanya saat status berubah), dan dihitung dalam kuota.
2.3. Notifikasi Medium WAJIB tidak dikirim ulang untuk tipe yang sama dalam 5 menit (cooldown per tipe).
2.4. Notifikasi Info dari alert WAJIB memakai cooldown 5 menit per tipe; notifikasi event trade (buka, tutup, BE, partial) WAJIB dikirim untuk setiap event tanpa cooldown.
2.5. Cooldown untuk tipe lingkup akun WAJIB berlaku untuk semua instance SDBot di akun (satu pesan per akun per cooldown); cooldown tipe lingkup instance berlaku per instance.
2.6. Notifikasi non-Critical WAJIB dibatasi 20 pesan per jam kuota untuk semua instance SDBot di akun bersama-sama; pesan yang melebihi kuota tidak dikirim.
2.7. JIKA notifikasi non-Critical belum terkirim setelah 30 menit sejak event MAKA notifier WAJIB membuangnya.
2.8. Setiap notifikasi yang tidak dikirim karena 2.3–2.7 WAJIB tercatat dengan alasannya (`COOLDOWN`, `QUOTA`, `STALE`).
2.9. Cooldown, kuota, dan umur pesan WAJIB dihitung dengan waktu notifier, sehingga tetap berjalan saat pasar tutup.

### Requirement 3: Antrean dan pengiriman

**User story:** Sebagai trader, saya ingin pesan Critical sampai lebih dulu dan pengiriman tidak pernah mengganggu proses order.

#### Acceptance criteria

3.1. Notifikasi WAJIB hanya diserahkan ke transport dari `OnTimer`, tidak pernah dari `OnTick`, `OnTradeTransaction`, atau di tengah proses order.
3.2. Notifikasi Critical WAJIB diambil sebelum notifikasi lain; sesama prioritas mengikuti urutan masuk.
3.3. Setiap siklus `OnTimer` WAJIB menyerahkan paling banyak 2 notifikasi ke transport, setelah risk monitor selesai.
3.4. JIKA transport melaporkan gagal sementara MAKA notifikasi WAJIB dicoba lagi di siklus berikutnya, maksimal 3 percobaan total; setelah itu statusnya `FAILED`.
3.5. JIKA transport melaporkan dibatasi dengan waktu tunggu MAKA notifier WAJIB tidak mengirim apa pun sampai waktu tunggu habis, dan percobaan itu tidak dihitung gagal.
3.6. JIKA transport melaporkan gagal permanen MAKA notifikasi WAJIB berstatus `FAILED` tanpa dicoba ulang.
3.7. JIKA antrean berisi 100 notifikasi MAKA notifikasi baru WAJIB menggeser notifikasi non-Critical tertua (dicatat `SKIPPED` alasan `OVERFLOW`); Critical tidak pernah digeser.

### Requirement 4: Format pesan

**User story:** Sebagai trader, saya ingin pesan SDBot mudah dibedakan dari pesan bot Python di chat yang sama dan tidak gagal kirim karena karakter khusus.

#### Acceptance criteria

4.1. Setiap pesan WAJIB diawali emoji level (Critical 🚨, High ❌, Medium ⚠️, Info ℹ️, SUCCESS ✅) diikuti penanda `SDBot`, simbol, tipe akun (`CENT`, `REAL`, `DEMO`, atau `TESTER`), dan versi EA.
4.2. Baris kedua pesan WAJIB berisi judul tipe event yang mudah dibaca, lalu isi pesan, mengikuti gaya bot Python (label tebal, nilai sebagai `code`).
4.3. Pesan WAJIB berformat HTML Telegram, dan teks dari luar template (isi alert, nama simbol, alasan) WAJIB di-escape (`&`, `<`, `>`).
4.4. Harga WAJIB ditulis dengan jumlah digit simbol (misalnya 3 digit untuk pair JPY cent), uang dengan 2 desimal plus mata uang akun (misalnya `USC`), R dengan 2 desimal.
4.5. JIKA pesan lebih dari 4096 karakter MAKA pesan WAJIB dipotong di batas itu dengan penanda `… (dipotong)` tanpa merusak tag HTML.
4.6. Setiap pesan WAJIB membawa tanda bunyi; di spec ini semua pesan berbunyi (heartbeat tanpa bunyi di spec 09).

### Requirement 5: Status di tabel `alerts`

**User story:** Sebagai trader, saya ingin bisa memeriksa di DB pesan mana yang terkirim, ditahan, atau gagal, dan alasannya.

#### Acceptance criteria

5.1. Setiap notifikasi, termasuk event trade, WAJIB punya satu baris di `alerts`.
5.2. Status baris WAJIB berakhir sebagai `SENT` (dengan `sent_at` dan `attempts`), `FAILED` (dengan `attempts` dan alasan), atau `SKIPPED` (dengan alasan); `PENDING` hanya selama notifikasi di antrean.
5.3. Notifier WAJIB tidak menulis DB sendiri; hasil kirim diteruskan ke Storage lewat event sink.
5.4. JIKA DB tidak tersedia MAKA notifikasi WAJIB tetap dikirim, dan hilangnya status dicatat lewat WARN DB yang sudah ada.

### Requirement 6: Restart dan deinit

**User story:** Sebagai trader, saya ingin pesan penting tidak hilang saat EA restart, tetapi pesan basi tidak dikirim terlambat.

#### Acceptance criteria

6.1. KETIKA EA init MAKA baris `alerts` milik instance (login, magic, simbol) yang masih `PENDING` dan lebih tua dari 30 menit WAJIB ditandai `SKIPPED` alasan `STALE`.
6.2. KETIKA EA init MAKA baris Critical milik instance yang masih `PENDING` dan berumur ≤ 30 menit WAJIB dimasukkan lagi ke antrean; non-Critical yang masih muda ditandai `SKIPPED` alasan `RESTART`.
6.3. KETIKA EA deinit MAKA notifier WAJIB menyerahkan notifikasi Critical yang masih di antrean ke transport (paling lama 3 detik total); sisanya tetap `PENDING` di DB.
6.4. Alert yang muncul sebelum timer berjalan (misalnya init gagal karena akun ditolak) WAJIB ikut diproses menurut 6.3.

### Requirement 7: Tester dan uji otomatis

**User story:** Sebagai developer, saya ingin perilaku notifier terbukti di Strategy Tester tanpa jaringan.

#### Acceptance criteria

7.1. SELAMA Strategy Tester EA WAJIB memakai transport log: setiap notifikasi yang terkirim dicetak ke log tester dalam format akhirnya, berstatus `SENT`.
7.2. SELAMA optimasi EA WAJIB tidak membuat notifikasi apa pun.
7.3. SELAMA live di spec ini (sebelum spec 09) EA WAJIB memakai transport log ke log Experts.
7.4. Harness WAJIB bisa memasang transport palsu yang hasilnya bisa diprogram (sukses, gagal sementara, dibatasi, permanen) dan merekam pesan yang diterimanya untuk di-assert.
7.5. Skenario SC-10 WAJIB membuktikan dari event nyata di tester: posisi dibuka dan tutup menghasilkan pesan yang benar; DD STOP Critical keluar sebelum pesan lain yang sudah antre; Medium berulang ditahan cooldown; kuota 20 per jam berlaku; retry 3x lalu `FAILED`; status di `sdbot_tester.sqlite` sesuai.

### Requirement 8: Versi dan dokumen

8.1. EA dan harness WAJIB naik ke versi `1.07`.
8.2. Diagram alur `docs/flows/` (timer, init) dan diagram baru notifier WAJIB diperbarui sesuai kode, beserta `CHANGELOG.md`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | 12 instance mencatat `CONN_DOWN` hampir bersamaan | Satu pesan untuk akun; instance lain `SKIPPED` `COOLDOWN` | 2.5, 2.8 |
| EC-02 | Dua instance merebut slot kuota terakhir di detik yang sama | Hanya satu yang lolos (compare-and-set) | 2.6 |
| EC-03 | Kuota jam ini habis lalu muncul `DD_STOP` | Critical tetap terkirim dan tidak mengurangi kuota | 2.1, 2.6 |
| EC-04 | Pasar tutup akhir pekan (`TimeCurrent` berhenti) | Cooldown, kuota, dan umur pesan tetap berjalan dengan waktu server berjalan | 2.9 |
| EC-05 | Isi alert berisi `margin < 300%` atau `R&D` | Di-escape, pesan tidak gagal parse | 4.3 |
| EC-06 | Pesan sangat panjang (misalnya detail error berulang) | Dipotong ≤ 4096 karakter dengan penanda, tag HTML utuh | 4.5 |
| EC-07 | Closure dengan R tidak diketahui (SL awal hilang) | Pesan menulis `R: -` | 1.3 |
| EC-08 | Posisi tutup break-even persis (profit bersih 0) | Level Info | 1.3 |
| EC-09 | Pair JPY cent (3 digit) dan XAUUSD (2–3 digit) | Harga ditulis sesuai digit simbol | 4.4 |
| EC-10 | Antrean penuh karena transport terus gagal | Non-Critical tertua digeser `OVERFLOW`; Critical tetap | 3.7 |
| EC-11 | EA crash setelah pesan terkirim tetapi sebelum status di-flush | Critical bisa terkirim dua kali setelah restart (diterima, lebih baik dobel daripada hilang); non-Critical tidak | 6.2 |
| EC-12 | DB terkunci atau dihapus saat jalan | Pesan tetap terkirim, status hilang dengan WARN DB yang sudah ada | 5.4 |
| EC-13 | Init gagal karena akun ditolak (`ACCOUNT_REJECTED` Critical) | Diserahkan ke transport saat deinit | 6.3, 6.4 |
| EC-14 | Global Variable cooldown atau kuota dihapus trader (F3) | Dianggap tidak ada cooldown / kuota baru; tidak error | 2.5, 2.6 |
| EC-15 | Restart di tengah run tester | Baris `PENDING` run itu diproses menurut 6.1–6.2 | 6.1, 6.2 |
| EC-16 | Transport membatasi dengan waktu tunggu lebih dari 30 menit | Non-Critical di antrean jadi `STALE`; Critical menunggu | 2.7, 3.5 |
| EC-17 | Posisi rekonsiliasi saat init | Tidak ada pesan "dibuka"; closure-nya nanti tetap diberi pesan | 1.4, 1.3 |
| EC-18 | Optimasi | Tidak ada notifikasi, log, maupun baris DB | 7.2 |

## Keputusan yang perlu disetujui

Hal yang tidak diatur PRD, dengan usulan saya (beberapa menjawab pertanyaan terbuka overview):

1. **Cooldown Info 5 menit per tipe**, sama dengan Medium (PRD hanya menyebut "cooldown per tipe"). Event trade tanpa cooldown (PRD "setiap event").
2. **Cooldown dan kuota per akun** lewat Global Variables, bukan per instance, karena sampai 12 instance berbagi satu chat. Tipe lingkup akun: `CONN_DOWN`, `CONN_UP`, `DD_*`, `DAILY_LOSS`, `MARGIN_*`, `BALANCE_OP`, `STATE_RESET`, `EMERGENCY_RESET`. Tipe lain lingkup instance.
3. **Kuota dihitung per jam server berjalan** (14:00–14:59), bukan jendela geser 60 menit, agar cukup satu pasangan Global Variable per akun.
4. **Event trade ikut kuota 20/jam** (PRD: non-Critical). Ditinjau ulang di Fase 3 bila trade per jam mendekati kuota.
5. **Tidak ada pesan ringkasan "N pesan ditahan"** (overview UC-22 menyebutnya). Pesan yang ditahan tercatat `SKIPPED` dengan alasan; jumlah yang ditahan per jam ditampilkan di heartbeat spec 09. Lebih sederhana dan tidak memakan kuota.
6. **Posisi tutup rugi = Info**, profit = SUCCESS ✅ (pertanyaan terbuka 2 overview).
7. **Critical `PENDING` ≤ 30 menit dikirim ulang setelah restart** (pertanyaan terbuka 3 overview); risiko dobel diterima (EC-11).
8. **Skema data v3** untuk `alerts`: kolom kunci notifikasi (agar status bisa diperbarui ke baris yang tepat walau baris belum di-flush), kolom alasan (`COOLDOWN`, `QUOTA`, `STALE`, `OVERFLOW`, `RESTART`, kode error transport), dan level SUCCESS untuk event trade. Dicatat sebagai PC-13 (PRD-EA §Data, PRD-Backoffice §Database) setelah disetujui.
9. **Waktu notifier = `TimeTradeServer()` di live** agar cooldown dan umur pesan berjalan saat akhir pekan (EC-04).
10. Batas antrean 100 dan 2 notifikasi per siklus timer sebagai konstanta di `Core/Constants.mqh`, bukan input.

## Pertanyaan terbuka

- Tidak ada selain keputusan di atas.
