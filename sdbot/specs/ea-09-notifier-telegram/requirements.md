# Requirements — 09 Notifier Telegram

Status: Done (2026-10-02)
Use case: UC-25, UC-26, UC-27, UC-28, UC-29, UC-30 ([overview](../fase-2-overview.md))
Asal: PRD-EA §Notifikasi (Telegram, push HP, heartbeat, kuota), §Parameter input EA (`TelegramToken`, `TelegramChatID`, `HeartbeatMinutes`), §Instalasi 3–4, §Roadmap Fase 2; RULES §Aturan wajib (hanya Notify memanggil `WebRequest`/`SendNotification`, rahasia tidak di-commit); PC-06 (bot dan chat sama dengan bot Python, format bot Python); PC-13 (aturan notifier spec 08); python-bot-lessons §2–3
Butuh: spec 08

## Pendahuluan

Spec ini menyambungkan notifier spec 08 ke Telegram dan push HP, lalu menambah pesan berjadwal: heartbeat dan laporan harian (satu per akun lewat instance pemimpin), serta pesan start dan stop per instance. Termasuk skrip yang membuat preset pribadi `*.local.set` dari `.env` bot Python, dan penutup Fase 2 (versi `1.08`, dokumen induk).

Tidak termasuk: perintah dari Telegram ke EA (EA hanya mengirim), notifikasi sinyal (Fase 3), email.

Selesai jika suite TelegramRules ALL PASS, skenario SC-11 PASS, pytest skrip kredensial lulus, regresi SC-00..SC-10 tetap PASS, checklist manual Telegram (MC-TG) dicek di akun cent, dan dokumen induk memuat PC-13 serta keputusan spec ini.

## Glosarium

- **Pemimpin**: satu instance SDBot per akun yang mengirim heartbeat dan laporan harian, dipilih lewat lease di Global Variable.
- **Lease**: hak pemimpin yang harus diperbarui berkala; bila tidak diperbarui dalam batas waktu, instance lain boleh mengambil alih.
- **Telegram nonaktif**: keadaan sesi setelah error konfigurasi (URL belum diizinkan, token atau chat salah); pesan tidak dikirim ke Telegram sampai EA di-init ulang.
- **Hari server**: tanggal menurut waktu server broker, sama dengan batas rugi harian spec 05.

## Requirements

### Requirement 1: Input dan kredensial

**User story:** Sebagai trader, saya ingin memakai bot dan chat Telegram bot Python tanpa menyalin token secara manual dan tanpa token masuk repo.

#### Acceptance criteria

1.1. EA WAJIB punya input `InpTelegramToken` dan `InpTelegramChatID` (default kosong) dan `InpHeartbeatMinutes` (default 60; 0 = heartbeat mati; selain 0 wajib 5–1440).
1.2. BILA token atau chat ID kosong EA WAJIB berjalan normal dengan notifikasi Telegram nonaktif dan satu WARN saat init; pesan tetap tercatat dan dicetak ke log seperti spec 08.
1.3. EA WAJIB tidak pernah menulis token ke log, DB, atau pesan; URL yang dicatat log menyamarkan token.
1.4. Skrip `sdbot/tools/make_local_presets.py` WAJIB membaca `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID` dari `.env` bot Python dan membuat `SDBot_DAY_<SIMBOL>c.local.set` untuk setiap preset repo, berisi preset itu plus token dan chat ID.
1.5. JIKA `.env` tidak ada atau salah satu nilai kosong MAKA skrip WAJIB berhenti dengan pesan jelas tanpa menulis file.
1.6. JIKA file `.local.set` sudah ada dan isinya berbeda dari hasil skrip MAKA skrip WAJIB tidak menimpanya kecuali dengan `--force`.
1.7. Skrip WAJIB memastikan file hasilnya diabaikan git, dan gagal bila tidak.
1.8. Preset repo (`SDBot_DAY_<SIMBOL>c.set`) WAJIB memuat ketiga input baru dengan token dan chat ID kosong.

### Requirement 2: Kirim ke Telegram

**User story:** Sebagai trader, saya ingin pesan SDBot sampai di chat Telegram yang sama dengan bot Python, tanpa mengganggu trading.

#### Acceptance criteria

2.1. SELAMA live dengan Telegram aktif EA WAJIB mengirim notifikasi lewat `sendMessage` Bot API (`parse_mode` HTML, `disable_notification` untuk pesan tanpa bunyi) dengan timeout 3 detik.
2.2. EA WAJIB menggolongkan hasil: HTTP 200 dengan `ok: true` = terkirim; HTTP 429 = dibatasi selama `retry_after` detik; HTTP 5xx, timeout, dan error jaringan = gagal sementara; HTTP 400, 401, 403, 404 = gagal permanen.
2.3. JIKA `WebRequest` gagal karena URL belum diizinkan (error 4014), atau Telegram menjawab 401, 403, 404, atau 400 "chat not found" MAKA EA WAJIB menonaktifkan Telegram untuk sesi itu, mencatat satu log CRITICAL dengan cara memperbaikinya, dan mengirim satu push HP.
2.4. JIKA Telegram menjawab 400 karena HTML tidak bisa di-parse MAKA EA WAJIB mengirim ulang pesan itu sekali sebagai teks polos (tag dibuang, entitas dikembalikan) dan mencatat ERROR.
2.5. Jarak antar kiriman ke Telegram dari semua instance SDBot di akun WAJIB minimal 1 detik, dan waktu tunggu 429 WAJIB berlaku untuk semua instance itu.
2.6. SELAMA kiriman terakhir gagal sementara EA WAJIB mengirim paling banyak 1 pesan per 10 detik per instance, agar `OnTimer` tidak tertahan berulang kali oleh timeout.
2.7. SELAMA Strategy Tester EA WAJIB tidak memanggil `WebRequest` maupun `SendNotification`; pesan dicetak ke log seperti spec 08.

### Requirement 3: Push HP untuk Critical

**User story:** Sebagai trader, saya ingin alert Critical tetap sampai ke HP walau Telegram bermasalah.

#### Acceptance criteria

3.1. KETIKA notifikasi Critical berstatus `FAILED` di Telegram, atau Telegram nonaktif, MAKA EA WAJIB mengirimnya lewat `SendNotification` sebagai teks polos maksimal 255 karakter berisi penanda SDBot, simbol, judul, dan awal isi.
3.2. Hasil push WAJIB tercatat di status baris `alerts` (alasan `PUSH_SENT` atau `PUSH_FAILED`).
3.3. JIKA push gagal karena belum dikonfigurasi MAKA EA WAJIB mencatat satu log CRITICAL per sesi berisi cara mengaktifkannya, tanpa mengulang tiap pesan.
3.4. Push WAJIB dibatasi agar tidak melebihi batas terminal (2 per detik, 10 per menit); push yang melebihi batas ditunda, bukan dibuang.

### Requirement 4: Pemimpin per akun

**User story:** Sebagai trader dengan 12 chart, saya ingin satu heartbeat dan satu laporan harian per akun, bukan dua belas.

#### Acceptance criteria

4.1. Instance WAJIB menjadi pemimpin hanya lewat compare-and-set pada Global Variable lease akun, dan memperbarui lease tiap 30 detik.
4.2. KETIKA lease tidak diperbarui selama 120 detik MAKA instance lain WAJIB bisa mengambil alih, tanpa heartbeat ganda di menit yang sama.
4.3. KETIKA pemimpin berhenti normal MAKA ia WAJIB melepas lease agar instance lain mengambil alih di siklus berikutnya.
4.4. Setiap instance WAJIB menandai dirinya hidup di Global Variable akun tiap 30 detik, agar pemimpin bisa menghitung instance hidup.

### Requirement 5: Heartbeat

**User story:** Sebagai trader, saya ingin tahu tiap jam bahwa SDBot masih berjalan dan keadaan akun aman, tanpa bunyi.

#### Acceptance criteria

5.1. SELAMA `InpHeartbeatMinutes` > 0 pemimpin WAJIB mengirim heartbeat tanpa bunyi tiap `InpHeartbeatMinutes` menit, dihitung dari heartbeat terakhir akun (Global Variable), bukan dari start instance.
5.2. Heartbeat WAJIB berisi: balance dan equity (mata uang akun), drawdown dari puncak (%), status risiko (normal, lot × 0.5, pause harian, STOPPED), jumlah posisi SDBot terbuka di akun, jumlah instance hidup, dan jumlah pesan yang ditahan kuota di jam sebelumnya.
5.3. Heartbeat dan laporan harian WAJIB tidak terkena cooldown maupun kuota 20 per jam, karena jadwalnya sudah teratur.

### Requirement 6: Laporan harian

**User story:** Sebagai trader, saya ingin ringkasan hasil kemarin setiap hari server berganti.

#### Acceptance criteria

6.1. KETIKA hari server berganti MAKA pemimpin WAJIB mengirim laporan hari sebelumnya, sekali per akun (penanda hari terakhir di Global Variable).
6.2. Laporan WAJIB dihitung dari history deal MT5 posisi SDBot (blok magic) di akun: P&L bersih (profit + komisi + swap + fee), jumlah posisi tutup, win rate, P&L per simbol, operasi saldo, dan balance akhir.
6.3. JIKA hari itu tidak ada posisi tutup dan tidak ada operasi saldo MAKA laporan WAJIB tidak dikirim.
6.4. JIKA pemimpin berganti atau EA mati saat hari berganti MAKA laporan hari itu WAJIB dikirim oleh pemimpin berikutnya paling lambat 1 jam setelahnya, tetap sekali.

### Requirement 7: Start dan stop

**User story:** Sebagai trader, saya ingin tahu instance mana yang hidup atau mati.

#### Acceptance criteria

7.1. KETIKA init sukses MAKA setiap instance WAJIB mengirim pesan start tanpa bunyi berisi simbol, magic, versi, tipe akun, preset, status validasi akun, dan akhir sesi sebelumnya (waktu dan alasan, atau "tidak normal" bila sesi lalu tidak ditutup).
7.2. KETIKA deinit MAKA instance WAJIB mencoba mengirim pesan stop tanpa bunyi berisi alasan deinit, dalam batas waktu deinit.
7.3. Pesan start dan stop WAJIB tidak terkena cooldown dan kuota, tetapi tetap mematuhi jarak kirim 1 detik.
7.4. Batas waktu kirim saat deinit WAJIB 2 detik total (Critical dulu, lalu stop), di bawah batas 2.5 detik MT5 untuk `OnDeinit`.

### Requirement 8: Uji dan penutup Fase 2

8.1. Skenario SC-11 WAJIB membuktikan di tester dengan transport palsu: heartbeat terkirim sesuai interval tanpa bunyi; laporan harian sekali per hari server dengan angka yang cocok dengan closure di DB; tidak ada laporan untuk hari tanpa aktivitas; pesan start dan stop ada; pemimpin berganti setelah restart harness tanpa heartbeat ganda.
8.2. Klasifikasi respons Telegram, penyusunan permintaan, teks polos, isi push, lease, jadwal heartbeat, dan isi laporan WAJIB diuji sebagai fungsi murni (suite TelegramRules).
8.3. EA dan harness WAJIB naik ke versi `1.08` (Fase 2 selesai); `docs/flows/`, `CHANGELOG.md`, README, dan checklist manual diperbarui.
8.4. Dokumen induk PRD-EA, PRD-Backoffice, dan RULES WAJIB memuat PC-13 dan keputusan spec ini lewat skill `sdbot-docs-sync`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | URL `https://api.telegram.org` belum diizinkan (4014) | Telegram nonaktif sesi ini, 1 CRITICAL + 1 push, tidak diulang tiap detik | 2.3 |
| EC-02 | Token salah (401) atau bot dikeluarkan dari grup (403) | Sama dengan EC-01 | 2.3 |
| EC-03 | Chat ID salah (400 "chat not found") | Sama dengan EC-01 | 2.3 |
| EC-04 | Bot Python dan SDBot sama-sama mengirim, Telegram membalas 429 retry_after 30 | Semua instance SDBot diam 30 detik, pesan tetap di antrean | 2.5 |
| EC-05 | Internet putus 10 menit | Pesan antre; maks 1 percobaan per 10 detik per instance; non-Critical > 30 menit dibuang (spec 08); Critical gagal 3x lewat push (yang juga butuh internet: tercatat `PUSH_FAILED`) | 2.6, 3.1 |
| EC-06 | Pesan berisi karakter yang lolos escape tetapi ditolak parser Telegram | Kirim ulang sekali sebagai teks polos | 2.4 |
| EC-07 | 12 instance init bersamaan setelah MT5 restart | 12 pesan start tanpa bunyi, berjarak ≥ 1 detik; satu pemimpin | 7.1, 2.5, 4.1 |
| EC-08 | MT5 ditutup dengan 12 instance | Setiap instance mencoba stop maks 2 detik; yang tidak sempat tetap `PENDING`, lalu `RESTART` saat start berikutnya, dan start berikutnya menyebut akhir sesi lalu | 7.2, 7.4, 7.1 |
| EC-09 | Pemimpin dilepas dari chart | Lease dilepas, instance lain memimpin di siklus berikutnya | 4.3 |
| EC-10 | Pemimpin crash (terminal hang) | Lease kedaluwarsa 120 detik, instance lain mengambil alih | 4.2 |
| EC-11 | Hari berganti saat akhir pekan (tidak ada deal) | Tidak ada laporan | 6.3 |
| EC-12 | EA mati melewati pergantian hari, hidup lagi 30 menit kemudian | Laporan hari itu dikirim sekali oleh pemimpin baru | 6.4 |
| EC-13 | Posisi dibuka kemarin dan tutup hari ini | Masuk laporan hari tutup | 6.2 |
| EC-14 | Push HP belum dikonfigurasi (MetaQuotes ID kosong) | 1 CRITICAL per sesi, status `PUSH_FAILED` | 3.3 |
| EC-15 | Banyak Critical bersamaan saat Telegram mati | Push dibatasi 2/detik, 10/menit, sisanya ditunda | 3.4 |
| EC-16 | Token kosong di akun cent | EA jalan, WARN sekali, pesan hanya di log | 1.2 |
| EC-17 | `.env` berisi token dengan spasi atau tanda kutip | Skrip membuang spasi dan kutip pembungkus; nilai kosong setelahnya = gagal | 1.4, 1.5 |
| EC-18 | `.local.set` sudah disunting trader | Tidak ditimpa tanpa `--force` | 1.6 |
| EC-19 | `InpHeartbeatMinutes` = 3 | Init gagal `INIT_PARAMETERS_INCORRECT` | 1.1 |
| EC-20 | Optimasi | Tidak ada notifikasi, lease, maupun heartbeat | 2.7 |
| EC-21 | Log `WebRequest` gagal | Token tersamar di semua log | 1.3 |

## Keputusan yang perlu disetujui

1. **Heartbeat, laporan harian, start, dan stop dikecualikan dari cooldown dan kuota 20/jam** (tetap mematuhi jarak 1 detik dan 429). Alasan: jadwalnya teratur, dan kuota bisa habis oleh event lain tepat saat heartbeat dibutuhkan untuk tahu EA hidup.
2. **Start dan stop per instance tanpa bunyi** (pertanyaan terbuka overview 1), dengan start memuat akhir sesi lalu, supaya stop yang tidak sempat terkirim saat MT5 ditutup tetap diketahui.
3. **Laporan harian dari history deal MT5** (pertanyaan terbuka overview 4), bukan dari DB: Notify tidak membaca DB dan terminal adalah sumber kebenaran. R per posisi tidak ada di laporan (butuh SL awal dari DB); cukup P&L, jumlah, win rate, per simbol.
4. **Tidak ada laporan untuk hari tanpa posisi tutup dan tanpa operasi saldo** (akhir pekan, libur). Heartbeat sudah menunjukkan EA hidup.
5. **Saat Telegram gagal sementara, maks 1 kiriman per 10 detik per instance**, agar risk monitor tidak tertahan timeout 3 detik di setiap siklus. Batas 2 per siklus spec 08 berlaku saat normal.
6. **Batas kirim saat deinit 2 detik** (bukan 3 detik spec 08) karena MT5 menghentikan `OnDeinit` setelah 2.5 detik saat terminal ditutup. Mengubah konstanta `SDB_NT_DRAIN_MS` spec 08.
7. **Error konfigurasi menonaktifkan Telegram sampai init ulang**, bukan dicoba lagi berkala; mengubah setelan MT5 atau input memang memerlukan init ulang.
8. **Pesan yang ditolak parser HTML dikirim ulang sekali sebagai teks polos**, agar pesan penting tidak hilang karena bug format (pelajaran bot Python).
9. **Skrip `make_local_presets.py` tidak menimpa `.local.set` yang sudah disunting tanpa `--force`.**
10. **Lease pemimpin 120 detik, diperbarui tiap 30 detik**; penanda hidup instance juga tiap 30 detik.
11. Alasan status baru di `enums.md` (`alert_status_reason`): `TELEGRAM_OFF`, `PUSH_SENT`, `PUSH_FAILED`, `PLAIN_TEXT`; tipe alert baru: `EA_START`, `EA_STOP`, `HEARTBEAT`, `DAILY_REPORT`. Tanpa perubahan skema tabel (kolom teks tanpa CHECK).

Keputusan 1–11 dicatat sebagai PC-14 setelah disetujui.

## Pertanyaan terbuka

- Tidak ada selain keputusan di atas.
