# Perubahan PRD/RULES yang belum masuk ke dokumen induk

Dokumen induk ada di claude.ai (Claude Docs). Salinan di folder ini tidak diedit langsung. Setiap keputusan yang sudah disetujui dan mengubah isi PRD atau RULES dicatat di sini, lalu diterapkan ke dokumen induk dan diekspor ulang ke repo lewat skill `sdbot-docs-sync`.

## Open

### PC-24: Filter berita (input, sumber kalender, degrade)
- Status: Open
- Tanggal disetujui: 2026-10-05
- Dokumen: PRD-EA §Pipeline analisis (pre-filter berita), §Parameter input EA, §Notifikasi (tipe alert); PRD-Backoffice §Database (enum `alert_type`)
- Sumber: spec `ea-16-news` requirements, keputusan 1–6
- Perubahan:
    - Input `NewsBlockMinutes` diganti `NewsFilter` (true), `NewsHighMinutes` (15) dan `NewsMediumMinutes` (0); 0 = dampak itu tidak diblokir. Default 15/0 (bukan PRD ±30) disetujui 2026-10-05 setelah backtest dasar: ±30/±10 hanya menyisakan 187 trade (< 200, PC-22) dan trade yang terblokir bersih +1,24R, karena kalender MT5 menandai HIGH juga untuk rilis kecil (New Home Sales, EIA, lelang obligasi). Kandidat di jendela event berdampak untuk mata uang simbol ditolak `NEWS_BLACKOUT` (detail: event, mata uang, dampak, menit ke rilis); XAU/XAG/BTC hanya kaki USD.
    - Live: kalender MT5 di-cache dan disegarkan tiap 15 menit. Tester: CSV `Common\Files\sdbot_calendar.csv` dari script `ExportCalendar` (jadwal saja, tanpa nilai `actual`).
    - Kalender tidak terbaca → entry tidak diblokir, satu alert `NEWS_FILTER_OFF` (High) per sesi EA; status filter (`ON`/`OFF`/`DISABLED`) dan event terdekat dicatat di konteks sinyal.
    - Enum `alert_type` + `NEWS_FILTER_OFF`.

### PC-23: Input eksposur mata uang
- Status: Open
- Tanggal disetujui: 2026-10-05
- Dokumen: PRD-EA §Risk management (eksposur per mata uang), §Parameter input EA
- Sumber: spec `ea-15-currency-exposure` requirements (replay 241 trade backtest berfilter v1.15), keputusan 1–4
- Perubahan:
    - Input `MaxSameDirectionPerCurrency` (default 2, 0 = mati, 0–10). Dihitung atas semua posisi SDBot di akun, per kaki mata uang dengan arah (BUY = dasar long + kuotasi short); posisi bukan SDBot tidak dihitung; long dan short dihitung terpisah.
    - Detail tolak `CURRENCY_EXPOSURE`: mata uang, arah, jumlah (contoh `USD short 2/2`). Tanpa kunci antar-instance untuk order yang hampir bersamaan.

### PC-22: Input sesi dan spread; kriteria backtest dasar Fase 4
- Status: Open
- Tanggal disetujui: 2026-10-04
- Dokumen: PRD-EA §Parameter input EA, §Pipeline analisis (pre-filter), §Roadmap (Fase 4)
- Sumber: spec `ea-14-session-spread` requirements (spread tick live 7 hari, 12 simbol), keputusan 1–4
- Perubahan:
    - `TradingSessions` menjadi tiga input `SessionTokyo` (false), `SessionLondon` (true), `SessionNewYork` (true); semua false = filter sesi mati. Jam 22:00–24:00 UTC tidak termasuk sesi mana pun.
    - `MaxSpreadPoints` per simbol, default 3 × median spread live akun cent: EURUSD 24, GBPUSD 30, USDJPY 30, USDCHF 39, AUDUSD 27, USDCAD 48, NZDUSD 42, EURJPY 48, GBPJPY 66, XAUUSD 720, XAGUSD 90, BTCUSD 3000; 0 = mati.
    - Input `TesterUtcOffsetHours` (default 0): selisih server–UTC di Strategy Tester.
    - Urutan tahap kandidat: pre-filter risiko → `OUTSIDE_SESSION` → `SPREAD_TOO_WIDE` → `POSITION_OPEN` → trigger PA → skor → SL/TP → lot/pre-trade → eksekusi.
    - Kriteria backtest dasar dengan filter Fase 4: total ≥ 200 trade dan setiap simbol ≥ 10 trade (menggantikan ≥ 300 / ≥ 15 PC-19 untuk backtest berfilter).

### PC-21: Aturan Fase 4 (pembagian spec, sesi UTC, eksposur, blackout berita, kalender tester)
- Status: Open
- Tanggal disetujui: 2026-10-04
- Dokumen: PRD-EA §Pipeline analisis (pre-filter), §Risk management (eksposur), §Parameter input EA, §Roadmap (Fase 4)
- Sumber: [fase-4-overview.md](../specs/fase-4-overview.md) §7, keputusan 1–6
- Perubahan:
    - Fase 4 dibagi tiga spec: sesi + spread (1.15), eksposur mata uang (1.16), berita (1.17, Fase 4 selesai).
    - Sesi trading dalam UTC (batas bot Python): Tokyo 00:00–08:00, London 08:00–17:00, New York 13:00–22:00; default London + New York (08:00–22:00 UTC). Kandidat di luar sesi ditolak `OUTSIDE_SESSION`.
    - `MaxSpreadPoints` per simbol diambil dari spread live akun cent, bukan dari tester; kandidat dengan spread lebih lebar ditolak `SPREAD_TOO_WIDE`.
    - Eksposur: maks 2 posisi SDBot searah per mata uang di akun, dihitung dengan arah (BUY EURUSD = long EUR + short USD); XAU, XAG, BTC dihitung sebagai mata uang sendiri vs USD.
    - Blackout berita: high ±15 menit, medium tidak diblokir secara default (diubah dari ±30/±10, lihat PC-24), low tidak pernah diblokir; event dipetakan ke mata uang simbol.
    - Di tester, kalender dibaca dari CSV hasil script `ExportCalendar`; tanpa CSV, filter berita mati + satu alert per sesi, entry tidak diblokir.

## Done

### PC-20: Lot pas dengan rugi broker; request saat pasar tutup
- Status: Done (2026-10-03, PRD-EA rev 48)
- Tanggal disetujui: 2026-10-03
- Dokumen: PRD-EA §Eksekusi order (Kebutuhan)
- Sumber: perbaikan bug spec 13 (TC-RK-14, TC-EX-33, TC-PS-05) dan v1.13 (TC-EX-34, TC-PS-06); permintaan user 2026-10-03
- Perubahan:
    - Lot: setelah dibulatkan ke bawah, rugi lot akhir dihitung ulang dengan `OrderCalcProfit` (broker membulatkan uang ke sen). Bila melebihi risiko per trade, lot diturunkan satu step sampai pas; di bawah lot minimum = tolak `LOT_BELOW_MIN`.
    - Pasar tutup: retcode 10018 bukan kegagalan permanen. Request (order, modify, partial, close) tidak dikirim di luar jadwal sesi trading simbol, dan ditahan 60 detik setelah 10018. Modify/partial dicoba lagi tanpa dihitung gagal; order ditolak `NOT_TRADABLE` tanpa alert `ORDER_FAILED`.

### PC-15: Aturan Fase 3 (ambang skor, TP cadangan, parameter relatif ATR, kriteria backtest dasar)
- Status: Done (2026-10-03, PRD-EA rev 47)
- Tanggal disetujui: 2026-10-02
- Dokumen: PRD-EA §Skor konfluensi, §Eksekusi order, §Parameter input EA, §Roadmap (Fase 3 "selesai jika")
- Sumber: [fase-3-overview.md](../specs/fase-3-overview.md) §7, keputusan 1–5
- Perubahan:
    - §Skor konfluensi: `MinConfluenceScore` diartikan persen dari skor maksimum komponen yang aktif. Fase 3 hanya zona (30), keselarasan tren (15), price action (10), jadi maksimum 55 dan ambang default 65% ≈ 36; saat komponen Fase 5 aktif, maksimum kembali 100. Semua komponen tetap dicatat per sinyal.
    - §Eksekusi order: bila tidak ada zona lawan dalam jangkauan, TP = entry ± `MinRR` × jarak SL (2R), dicatat di konteks sinyal.
    - §Parameter input / katalog: ukuran zona minimum dan maksimum, buffer SL di luar zona, serta jarak SL minimum dan maksimum dinyatakan relatif ATR MTF (input, default dari distribusi histori 12 simbol yang diukur di requirements spec 11 dan 13). Filter candle klimaks ditunda ke Fase 5.
    - §Roadmap Fase 3 "selesai jika": backtest dasar 12 simbol × 12 bulan terakhir berjalan tanpa error kritis, minimal 30 trade per simbol dengan `signal_id` lengkap, dan query kalibrasi menghasilkan data; profit dinilai di Fase 5–6.
    - Pembagian Fase 3 menjadi empat spec (struktur, zona, trigger PA, sinyal + entry); versi EA 1.09–1.12.

### PC-16: Definisi struktur, EMA, dan bias HTF; input analisis
- Status: Done (2026-10-03, PRD-EA rev 47)
- Tanggal disetujui: 2026-10-02
- Dokumen: PRD-EA §Pipeline analisis (alur, bias HTF), §Skor konfluensi (keselarasan tren), §Parameter input EA
- Sumber: spec `ea-10-market-structure` requirements, keputusan 1–6
- Perubahan:
    - Swing = fractal dengan kekuatan `SwingStrength` (default 2) dari bar tertutup, diakui setelah `SwingStrength` bar di kanannya tutup; high/low sama persis: bar lebih awal. BOS = close bar tertutup melewati swing terkonfirmasi terakhir; arah struktur = BOS terakhir dalam `StructureLookback` bar (default 100).
    - Arah EMA (`EmaPeriod` default 50): bullish bila close > EMA dan EMA naik dibanding `EmaSlopeBars` bar sebelumnya (default 3); bearish kebalikannya; selain itu netral.
    - Bias HTF bullish/bearish hanya bila arah struktur dan arah EMA HTF sama; selain itu netral (termasuk data kurang).
    - Skor keselarasan tren (15) dinilai di MTF: struktur dan EMA MTF searah sinyal = 15, salah satu = 7, tidak ada = 0.
    - Input baru di tabel parameter: `SwingStrength` 2 (1–5), `StructureLookback` 100 (20–500), `EmaPeriod` 50 (10–400), `EmaSlopeBars` 3 (1–20).

### PC-17: Definisi zona S&D dan input zona
- Status: Done (2026-10-03, PRD-EA rev 47)
- Tanggal disetujui: 2026-10-02
- Dokumen: PRD-EA §Aturan zona Supply & Demand, §Parameter input EA
- Sumber: spec `ea-11-zones` requirements (ukuran histori H1 12 simbol 2025-10..2026-10), keputusan 1–6
- Perubahan:
    - Zona dari satu candle swing MTF: demand = low sampai max(open, close) candle swing low; supply = high sampai min(open, close) candle swing high. Lebar wajib 0,3–2,0 × ATR(14) MTF dan gerak keluar (close terjauh dari batas dekat) ≥ 1,5 × ATR dalam 10 bar; zona aktif sejak swing terkonfirmasi dan gerak keluar tercapai.
    - Sentuhan = bar MTF tertutup yang masuk zona setelah bar sebelumnya di luar; status Fresh (0), Tested (1), Lemah (≥ 2, tidak dipakai), Invalid (close melewati batas jauh, final), Kedaluwarsa (> `MaxZoneAgeBars` bar), Used (sudah dipakai entry, penanda di Global Variable per magic, dibersihkan setelah kedaluwarsa).
    - Peta zona dibangun ulang penuh dari histori setiap bar MTF baru (tidak dari DB); zona bertumpuk tidak digabung, pipeline memilih Fresh lalu terbaru.
    - Input baru: `ZoneMinWidthAtr` 0,3, `ZoneMaxWidthAtr` 2,0, `ZoneMinLegAtr` 1,5, `ZoneLegBars` 10; `MaxZoneAgeBars` 100 (sudah di PRD).

### PC-18: Definisi trigger price action
- Status: Done (2026-10-03, PRD-EA rev 47, PRD-Backoffice rev 17)
- Tanggal disetujui: 2026-10-03
- Dokumen: PRD-EA §Pipeline analisis (trigger PA), §Skor konfluensi (kekuatan PA); PRD-Backoffice §Database (enum)
- Sumber: spec `ea-12-pa-trigger` requirements (ukuran M15 12 simbol 2026-04..2026-10), keputusan 1–4
- Perubahan:
    - Trigger PA = pola terarah pertama yang cocok di bar LTF tertutup, urutan: bintang pagi/sore, engulfing kuat, pin bar, engulfing biasa, tweezer, outside bar terarah. Pola netral (inside bar, doji, harami) tidak pernah menjadi trigger.
    - Definisi relatif ATR(14) LTF: engulfing kuat = badan menelan badan sebelumnya, badan ≥ 60% rentang dan ≥ 0,8 ATR, close melewati high/low sebelumnya; pin bar = badan ≤ 35% rentang, sumbu ≥ 2 × badan, ≥ 60% rentang, > 2 × sumbu lain, rentang ≥ 0,8 ATR; tweezer = selisih low/high ≤ 0,1 ATR; bintang = badan pertama > 0,5 ATR, badan tengah < 0,3 × badan pertama, bar ketiga close melewati titik tengah badan pertama. Ambang sebagai konstanta.
    - Skor: engulfing kuat 10, pin bar 7, pola terarah lain 3 (PRD). Kode pola (enum `pa_pattern`): `STAR`, `ENGULF_STRONG`, `PIN`, `ENGULF`, `TWEEZER`, `OUTSIDE`, `NONE`.
    - Tidak ada aturan khusus logam/crypto; sekitar 40% bar M15 punya pola terarah.

### PC-19: Pipeline sinyal, entry, dan kriteria backtest dasar
- Status: Done (2026-10-03, PRD-EA rev 47, PRD-Backoffice rev 17)
- Tanggal disetujui: 2026-10-03
- Dokumen: PRD-EA §Pipeline analisis (alur), §Skor konfluensi, §Eksekusi order, §Data dan database (`signals`), §Parameter input EA, §Roadmap Fase 3; PRD-Backoffice §Database (enum)
- Sumber: spec `ea-13-signal-entry` requirements (simulasi pipeline 12 simbol 2025-10..2026-10), keputusan 1–9
- Perubahan:
    - Kandidat = bar LTF tertutup yang menyentuh zona valid searah bias HTF; satu baris `signals` per kandidat. Bar tanpa bias atau tanpa zona hanya dihitung di ringkasan log harian. Urutan tahap untuk kandidat: pre-filter risiko (STOPPED, pause harian, tidak bisa trading) → posisi instance terbuka (`POSITION_OPEN`) → trigger PA (`NO_PA_TRIGGER`) → skor (`SCORE_TOO_LOW`) → SL/TP dan R:R → lot dan pre-trade check → eksekusi. Bar dinilai sekali (penanda bar di Global Variable per magic); bar yang lebih tua dari 2 × LTF tidak dinilai.
    - Skor: `score_total` = skor mentah; persen = skor ÷ maksimum komponen aktif (Fase 3: 55) dibanding `MinConfluenceScore`; komponen `ZONE`, `TREND`, `PA` selalu dicatat di `signal_scores` (enum `score_component`, cadangan `FIB`, `TRENDLINE`, `BREAKOUT`, `RSI`).
    - Eksekusi: Fase 3 hanya market order (`EntryMode` limit ditunda ke Fase 5). SL = batas jauh zona ∓ `SlBufferAtr` (0,1) × ATR(14) MTF, SELL ditambah spread. Jarak SL wajib ≥ max(stops level + spread, `MinSlAtr` 0,3 × ATR MTF) dan ≤ `MaxSlAtr` 3,0 × ATR MTF (`SL_TOO_CLOSE` / `SL_TOO_FAR`). TP = batas dekat zona lawan valid terdekat, atau `MinRR` × R bila tidak ada (sumber TP dicatat). Maksimal satu posisi terbuka per instance (simbol). Zona menjadi Used hanya setelah order terisi.
    - Input baru: `MinConfluenceScore` 65 (persen dari maksimum aktif), `MinRR` 2,0 (sudah di PRD), `SlBufferAtr` 0,1, `MinSlAtr` 0,3, `MaxSlAtr` 3,0.
    - Enum `reject_stage` + `POSITION_OPEN`, `SL_TOO_FAR`.
    - Koreksi PC-15, Roadmap Fase 3 "selesai jika": backtest dasar 12 simbol × 12 bulan terakhir tanpa error kritis, **total ≥ 300 trade dan setiap simbol ≥ 15 trade**, semua trade punya `signal_id` dengan skor lengkap, query kalibrasi menghasilkan data; profit dinilai di Fase 5–6. (Simulasi: gerbang skor 65% memberi 19–37 trade per simbol per tahun, total 312.)

### PC-13: Aturan notifier dan status alert (skema v3)
- Status: Done (2026-10-02, PRD-EA rev 42, PRD-Backoffice rev 16)
- Tanggal disetujui: 2026-10-01
- Dokumen: PRD-EA §Notifikasi, §Data dan database; PRD-Backoffice §Database dan kontrak data
- Sumber: spec `ea-08-notifier-core` requirements, keputusan 1–10
- Perubahan:
    - §Notifikasi, tabel event: Info dari alert memakai cooldown 5 menit per tipe (sama dengan Medium); event trade (buka, tutup, BE, partial) tanpa cooldown. Posisi tutup profit = SUCCESS ✅, rugi atau impas = Info.
    - Cooldown tipe lingkup akun (`CONN_*`, `DD_*`, `DAILY_LOSS`, `MARGIN_*`, `BALANCE_OP`, `STATE_RESET`, `EMERGENCY_RESET`) dan kuota non-Critical 20 pesan berlaku per akun untuk semua instance SDBot (Global Variables, compare-and-set); kuota dihitung per jam server berjalan; event trade ikut kuota. Pesan yang ditahan tidak diringkas, cukup tercatat `SKIPPED` dengan alasan.
    - Umur pesan, cooldown, dan kuota memakai waktu server berjalan (`TimeTradeServer()`), agar tetap berjalan saat pasar tutup.
    - Antrean notifikasi maksimal 100 (non-Critical tertua digeser), maksimal 2 pesan per siklus `OnTimer`, retry 3 kali untuk gagal sementara.
    - Restart: baris `PENDING` milik instance > 30 menit menjadi `SKIPPED`; Critical ≤ 30 menit dikirim ulang (bisa dobel bila EA crash setelah kirim); non-Critical muda `SKIPPED`. Saat deinit, Critical di antrean dikirim (maks 3 detik).
    - §Data: migrasi `0003` menambah kolom `alerts.notify_key` (kunci notifikasi untuk pembaruan status) dan `alerts.status_reason` (`COOLDOWN`, `QUOTA`, `STALE`, `OVERFLOW`, `RESTART`, kode error transport). Event trade juga tercatat di `alerts` (tipe `TRADE_OPENED`, `TRADE_CLOSED`).

### PC-14: Telegram, push HP, heartbeat, laporan harian, start/stop
- Status: Done (2026-10-02, PRD-EA rev 42, PRD-Backoffice rev 16)
- Tanggal disetujui: 2026-10-02
- Dokumen: PRD-EA §Notifikasi, §Parameter input EA, §Instalasi 4, §Pengujian dan kriteria penerimaan; PRD-Backoffice §Database dan kontrak data (nilai enum)
- Sumber: spec `ea-09-notifier-telegram` requirements, keputusan 1–11
- Perubahan:
    - Respons Telegram: 200 terkirim; 429 tunggu `retry_after` untuk semua instance; 5xx/timeout/jaringan gagal sementara (maks 1 kiriman per 10 detik per instance selama gagal); 400/401/403/404 permanen. URL belum diizinkan (4014), token salah, bot dikeluarkan, atau chat salah: Telegram nonaktif sampai init ulang + 1 log CRITICAL + 1 push HP. Pesan yang ditolak parser HTML dikirim ulang sekali sebagai teks polos. Jarak kiriman ≥ 1 detik untuk semua instance SDBot di akun. Token tidak pernah ditulis ke log, DB, atau pesan.
    - Push HP (`SendNotification`, teks polos ≤ 255 karakter) untuk Critical yang gagal di Telegram atau saat Telegram nonaktif; dibatasi 2/detik dan 10/menit (ditunda, bukan dibuang); belum dikonfigurasi = 1 CRITICAL per sesi.
    - Heartbeat dan laporan harian dikirim satu instance pemimpin per akun (lease Global Variable 120 detik, diperbarui tiap 30 detik, dilepas saat berhenti). Heartbeat tanpa bunyi tiap `HeartbeatMinutes` (0 = mati, selain itu 5–1440): balance, equity, drawdown dari puncak, status risiko, posisi SDBot terbuka di akun, instance hidup, pesan yang ditahan kuota jam sebelumnya.
    - Laporan harian saat hari server berganti, dari history deal MT5 posisi SDBot: P&L bersih, jumlah posisi tutup, win rate, P&L per simbol, operasi saldo, balance akhir; tidak dikirim untuk hari tanpa posisi tutup dan tanpa operasi saldo; hari yang terlewat (EA mati, akhir pekan di tester) dikirim kemudian, sekali per hari.
    - Pesan start dan stop per instance tanpa bunyi; start memuat akhir sesi sebelumnya. Heartbeat, laporan harian, start, dan stop tidak terkena cooldown dan kuota 20/jam.
    - Batas kirim saat deinit 2 detik (MT5 menghentikan `OnDeinit` setelah 2.5 detik), menggantikan 3 detik PC-13.
    - Instalasi 4: preset pribadi dibuat dengan `python sdbot/tools/make_local_presets.py` dari `.env` bot Python (tidak menimpa `.local.set` yang sudah disunting tanpa `--force`).
    - Enum: `alert_status_reason` + `TELEGRAM_OFF`, `PUSH_SENT`, `PUSH_FAILED`, `PLAIN_TEXT`; `alert_type` + `EA_START`, `EA_STOP`, `HEARTBEAT`, `DAILY_REPORT`.

### PC-01: Skema data baru menggantikan tabel PRD
- Status: Done (2026-10-01, PRD-EA rev 40, PRD-Backoffice rev 14)
- Tanggal disetujui: 2026-09-29
- Dokumen: PRD-EA §Data dan database; PRD-Backoffice §Arsitektur integrasi, §Database dan kontrak data
- Sumber: spec `ea-03-storage-migrations` design §2–§3, keputusan §9.1
- Perubahan:
    - Tabel `sdbot.sqlite` menjadi: `sessions`, `accounts`, `signals` + `signal_scores`, `trades` (kunci `login + position_id`), `deals`, `position_events`, `closures` (alasan `TP`/`SL`/`BE_STOP`/`TRAIL_STOP`/`MANUAL`/`STOP_OUT`/`EA_CLOSE`/`ROLLOVER`/`OTHER`, plus `mfe_r`, `mae_r`, `holding_sec`, flag BE/partial/trailing), `balance_ops`, `alerts` (+ `attempts`, `sent_at`), view `v_trade_results`, dan `schema_migrations` menggantikan `schema_version`.
    - Semua waktu UTC epoch detik; `accounts.server_utc_offset_sec` menyimpan selisih waktu server.
    - Backtest menulis ke file terpisah `sdbot_tester.sqlite`; optimasi tidak menulis DB. Backoffice hanya membaca `sdbot.sqlite`.
    - Tabel ringkas di PRD-EA diganti tabel versi baru (nama tabel + isi utama); DDL lengkap dirujuk ke `shared/schema/data_db.sql`.

### PC-02: Blok magic SDBot
- Status: Done (2026-10-01, PRD-EA rev 40, RULES rev 19)
- Tanggal disetujui: 2026-09-29
- Dokumen: PRD-EA §Parameter input EA, §Risk management, §Instalasi 5; RULES §Aturan wajib keamanan trading
- Sumber: spec `ea-05-risk` keputusan R2-1, spec `ea-02-core-account` kriteria 1.6
- Perubahan:
    - `MagicNumber` default `2026091901`, wajib di rentang `2026091901`–`2026091999`, satu nomor per pair (EURUSDc …01, GBPUSDc …02, EURJPYc …03, GBPJPYc …04); `2026091900` dicadangkan untuk harness uji.
    - Risk management: saat emergency stop, setiap instance menutup **semua posisi SDBot** (magic di blok) di simbol mana pun; total risiko terbuka 3% dihitung atas semua posisi SDBot di akun.
    - RULES: "setiap loop posisi memfilter magic serta simbol" tetap berlaku, dengan pengecualian tertulis untuk emergency close dan perhitungan risiko terbuka akun.

### PC-03: Skema versi EA
- Status: Done (2026-10-01, RULES rev 19)
- Tanggal disetujui: 2026-09-29 (dipaksa compiler, temuan spike spec 01)
- Dokumen: RULES §Git, versi, dan rahasia
- Sumber: spec `ea-01-tooling` design §8
- Perubahan: format `MAJOR.MINOR` dengan MAJOR ≥ 1, karena MetaEditor memberi warning 68 untuk versi `0.x` dan aturan compile adalah 0 warning. Fase 1 memakai `1.00`–`1.06` (naik `0.01` per spec), `2.00` setelah validasi Fase 6.

### PC-04: Migrasi skema lewat skrip
- Status: Done (2026-10-01, RULES rev 19)
- Tanggal disetujui: 2026-09-29
- Dokumen: RULES §Struktur folder repo, §Kontrak lintas bagian, §Definition of done
- Sumber: spec `ea-03-storage-migrations` Req 4–6
- Perubahan:
    - `shared/schema/` berisi `migrations/data/NNNN_*.sql`, `migrations.lock.json`, `enums.md`, snapshot `data_db.sql` (hasil generate), `fixtures/`.
    - Perubahan skema: `python sdbot/tools/schema.py new data "<deskripsi>"` → tulis SQL → `schema.py build` (menghasilkan `Storage/Migrations.mqh`, `Core/SchemaEnums.mqh`, snapshot, fixture) → commit (pre-commit menjalankan `schema.py check`). EA menerapkan migrasi sendiri saat start. Migrasi hanya maju; migrasi rilis tidak boleh diedit.
    - Kalimat lama "ubah `shared/schema/*.sql`, naikkan `schema_version`" diganti alur di atas.

### PC-05: Alat build dan uji
- Status: Done (2026-10-01, RULES rev 19)
- Tanggal disetujui: 2026-09-29
- Dokumen: RULES §Struktur folder repo, §Menghubungkan repo ke MT5, §Testing
- Sumber: spec `ea-01-tooling` (approved)
- Perubahan:
    - `tools/` bertambah `build-ea.ps1`, `run-ea-tests.ps1`, `lib/Mt5Paths.psm1`, `mt5-paths.example.json` (`mt5-paths.local.json` tidak di-commit).
    - `link-mt5.ps1` juga membuat junction `Experts/SDBotTests`, `Include/SDBotTests`, `Scripts/SDBotTests` ke `ea/tests/`.
    - Unit test ditulis sebagai suite `.mqh` di `ea/tests/Include/SDBotTests/Suites/`, dijalankan otomatis oleh `run-ea-tests.ps1` di Strategy Tester terminal uji (terpisah dari terminal live), atau manual lewat script `RunUnitTests`.

### PC-06: Telegram memakai bot yang sama dengan bot Python
- Status: Done (2026-10-01, PRD-EA rev 40)
- Tanggal disetujui: 2026-09-29
- Dokumen: PRD-EA §Notifikasi, §Instalasi dan pemasangan 4
- Sumber: permintaan user 2026-09-29; catatan Fase 2 di `sdbot/specs/README.md`
- Perubahan:
    - §Instalasi 4 "Siapkan bot Telegram": tidak membuat bot baru lewat @BotFather; token dan chat ID diambil dari `.env` bot Python (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) dan diisi ke input EA lewat preset pribadi `*.local.set`.
    - §Notifikasi: format pesan mengikuti bot Python (emoji per level, HTML, start/stop, heartbeat tanpa bunyi, laporan harian) dengan penanda `SDBot` + pair + tipe akun di setiap pesan; batas kirim Telegram dibagi dengan bot Python.

### PC-07: Lapisan App, komentar order, dan aturan eksekusi
- Status: Done (2026-10-01, PRD-EA rev 40, RULES rev 19)
- Tanggal disetujui: 2026-09-29
- Dokumen: RULES §Struktur folder repo (tabel lapisan), §Aturan wajib keamanan trading; PRD-EA §Eksekusi order
- Sumber: spec `ea-04-execution-harness` design §9
- Perubahan:
    - Lapisan baru `Include/SDBot/App/` (paling atas, hanya orkestrasi: `CSdbApp`, `CTeeSink`); `SDBot.mq5` hanya meneruskan event ke `CSdbApp`.
    - Komentar order `SDB|<SL awal>|<ID permintaan 4 karakter>` untuk deteksi order ganda setelah retcode ambigu.
    - `OrderCheck` wajib sebelum setiap `OrderSend`; deviasi maksimum 10 point (konstanta); modify dan close ikut diulang maksimal 3 kali seperti open.
    - Alasan tolak baru di `reject_stage`: `INVALID_STOPS`, `INVALID_VOLUME`.

### PC-08: run_key memisahkan run backtest (skema v2)
- Status: Done (2026-10-01, PRD-EA rev 40, PRD-Backoffice rev 14)
- Tanggal disetujui: 2026-09-30
- Dokumen: PRD-EA §Data dan database; PRD-Backoffice §Database dan kontrak data
- Sumber: spec `ea-04-execution-harness` task 7 (temuan SC-00: baris `trades` run kedua dan seterusnya hilang di `sdbot_tester.sqlite`), keputusan user 2026-09-30
- Perubahan:
    - Migrasi `0002_run_key`: kolom `run_key INTEGER NOT NULL DEFAULT 0` di `sessions`, `trades`, `deals`, `closures`, `balance_ops`, `position_events`. Kunci unik menjadi `(login, run_key, position_id)` untuk `trades`/`closures` dan `(login, run_key, deal_ticket)` untuk `deals`/`balance_ops`. View `v_trade_results` menggabungkan dengan `run_key` dan menampilkannya.
    - `run_key` = 0 di live (posisi tetap unik per login lintas restart EA). Di Strategy Tester = ID sesi pertama run; disimpan di Global Variable tester `SDB_<login>_RUN_KEY` agar restart di tengah run memakai run yang sama.
    - Alasan: di tester, position ID dan deal ticket mulai dari angka kecil yang sama di setiap run dengan login yang sama, sehingga `ON CONFLICT DO NOTHING` membuang semua baris run berikutnya tanpa error.
    - Backoffice dan query analisis wajib memakai `login + run_key + position_id` sebagai kunci posisi.

### PC-09: Detail risk management yang tidak diatur PRD
- Status: Done (2026-10-01, PRD-EA rev 40)
- Tanggal disetujui: 2026-09-30
- Dokumen: PRD-EA §Risk management
- Sumber: spec `ea-05-risk` requirements, keputusan 1–3
- Perubahan:
    - Pre-trade check urutannya: boleh trading → STOPPED → pause harian → risiko per trade → total risiko terbuka → eksposur mata uang → margin. Langkah "risiko per trade" menolak order yang risikonya (volume, entry, SL) melebihi risiko efektif per trade, dengan alasan tolak baru `RISK_PER_TRADE` (`enums.md`).
    - Close all saat STOPPED: percobaan saat pasar tutup (tiap 60 detik) tidak dihitung gagal; Critical `CLOSE_ALL_FAILED` hanya setelah 3 gagal berturut-turut saat pasar buka, lalu paling sering tiap 15 menit.
    - Posisi SDBot tanpa SL dihitung berisiko 1% balance di total risiko terbuka, dengan log WARN.
    - Operasi saldo yang sudah ada saat status bersama belum ada (akun baru, GV dihapus, awal run tester) dianggap sudah diproses.
    - Ambang kembali normal dari lot × 0.5 = min(8%, `InpDDReducePct` × 0.8), agar histeresis tetap ada bila batas REDUCE disetel di bawah 8% (temuan SC-03; default PRD tetap 8%). Disetujui 2026-09-30.

### PC-10: Simbol mengikuti bot Python, preset per simbol, batas posisi per kategori
- Status: Done (2026-10-01, PRD-EA rev 40, RULES rev 19)
- Tanggal disetujui: 2026-09-30
- Dokumen: PRD-EA §Temuan review dan keputusan (pair), §Risk management, §Parameter input EA, §Instalasi; RULES §Struktur folder (Presets)
- Sumber: permintaan user 2026-09-30; `config/active_symbols.yaml` bot Python; spec `ea-05-risk` kriteria 2.8
- Perubahan:
    - Simbol SDBot = simbol aktif bot Python, versi cent Exness (akhiran `c`): forex major EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD; forex cross EURJPY, GBPJPY; komoditas XAUUSD, XAGUSD; crypto BTCUSD. Menggantikan keputusan 4 pair (EURUSD, GBPUSD, EURJPY, GBPJPY). Ketersediaan NZDUSDc di akun perlu dicek.
    - Magic per simbol (blok PC-02): 01 EURUSD, 02 GBPUSD, 03 EURJPY, 04 GBPJPY (tetap), 05 USDJPY, 06 USDCHF, 07 AUDUSD, 08 USDCAD, 09 NZDUSD, 10 XAUUSD, 11 XAGUSD, 12 BTCUSD.
    - Setting berbeda per kategori lewat preset `.set` per simbol (`SDBot_DAY_<SIMBOL>c.set`) dengan input EA yang sama. Nilai awal per kategori diambil dari config bot Python saat spec pemiliknya dibuat (preset di spec 07, filter sesi/spread di Fase 4). BE/partial/trailing tetap berbasis R dan ATR sesuai PRD.
    - Risk management: batas posisi SDBot per kategori aset di akun (forex major 5, forex cross 3, komoditas 1, crypto 1; input `InpMaxPos*`), langkah pre-trade check setelah total risiko terbuka, alasan tolak `CLASS_POSITION_LIMIT`. Kategori ditentukan dari mata uang base/quote simbol.

### PC-11: Detail manajemen posisi dan closure
- Status: Done (2026-10-01, PRD-EA rev 40)
- Tanggal disetujui: 2026-09-30
- Dokumen: PRD-EA §Position management, §Notifikasi
- Sumber: spec `ea-06-position` requirements, keputusan 1–4
- Perubahan:
    - Posisi milik instance ditentukan dari deal pembukanya (magic + simbol), bukan dari deal penutup; closure dari close all lintas instance tercatat oleh pemilik dengan alasan `EA_CLOSE`.
    - Titik BE = harga buka ± (spread + komisi pulang-pergi dalam point + `InpBreakevenBufferPoints`).
    - Modifikasi/partial gagal: dicoba ulang tiap 30 detik maksimal 3 kali per aksi, lalu satu event `MODIFY_FAILED` + satu alert Medium, berhenti sampai kondisi posisi berubah.
    - SL yang dihapus manual dipasang kembali (SL awal bila valid, atau SL valid terdekat) + alert High; gagal 3x → Critical.
    - Alasan tutup dibedakan `SL` / `BE_STOP` / `TRAIL_STOP` dari level pemicu SL; MFE/MAE dari bar M1 saat posisi tutup.

### PC-12: Preset Fase 1, metrik optimasi, penanda preset
- Status: Done (2026-10-01, PRD-EA rev 40)
- Tanggal disetujui: 2026-10-01
- Dokumen: PRD-EA §Parameter input EA, §Instalasi 5, §Pengujian dan kriteria penerimaan
- Sumber: spec `ea-07-integration` requirements, keputusan 1–5
- Perubahan:
    - Preset `SDBot_DAY_<SIMBOL>c.set` untuk 12 simbol PC-10; isi Fase 1 sama untuk semua simbol kecuali magic dan komentar kategori; nilai per kategori dari bot Python dicantumkan sebagai komentar referensi sampai inputnya ada (Fase 3–4). `InpAllowLiveTrading = false` di preset.
    - Risiko per trade tetap 0.5% (PRD), bukan 0.1% bot Python.
    - Metrik `OnTester` = expectancy R per trade ÷ max drawdown relatif equity (%), 0 bila trade dengan R < 30 atau drawdown 0.
    - Input baru `InpPresetTag` (simbol preset; kosong = tidak dicek): WARN sekali bila berbeda dengan simbol chart.
    - Versi EA `1.06` = Fase 1 selesai.
