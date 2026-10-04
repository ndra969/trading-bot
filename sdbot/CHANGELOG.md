# Changelog SDBot

Format: satu bagian per rilis EA dan backoffice (RULES §Git). Versi EA `MAJOR.MINOR`: MAJOR = memengaruhi posisi terbuka atau skema DB lintas fase; Fase 1 memakai `1.00`–`1.06`, `2.00` setelah validasi Fase 6 (PC-03).

## EA

### 1.15 — 2026-10-04 — spec 14 filter sesi dan spread (Fase 4)

- Lapisan baru `Filters/FilterRules.mqh` (fungsi murni):
  - sesi UTC dengan batas bot Python: Tokyo 00–08, London 08–17, New York 13–22, overlap termasuk keduanya, 22–24 di luar sesi;
  - selisih server–UTC: live dari `TimeTradeServer − TimeGMT`, tester dari input;
  - batas spread.
- Pipeline: kandidat di luar sesi ditolak `OUTSIDE_SESSION`, kandidat dengan spread (ask − bid) di atas batas ditolak `SPREAD_TOO_WIDE`; keduanya sesudah pre-filter risiko dan sebelum `POSITION_OPEN`. Konteks sinyal mendapat `session` dan `max_spread`. Manajemen posisi tidak berubah.
- Input `InpSessionTokyo` (false), `InpSessionLondon` (true), `InpSessionNewYork` (true), `InpMaxSpreadPoints` (preset: 3 × median spread live, EURUSD 24 … XAU 720, BTC 3000), `InpTesterUtcOffsetHours` (0). Keputusan PC-21, PC-22.
- Alat: `baseline_report.py` default kriteria Fase 4 (≥ 200 trade, ≥ 10 per simbol) dan pembanding `--compare-from/--compare-to`; `run-ea-tests.ps1 -Baseline -CompareFrom/-CompareTo`. Skenario SC-15 (hanya Tokyo) dan SC-15b (spread ketat).

Backtest dasar dengan filter (12 simbol, 2025.10.01–2026.10.01, OHLC M1): **LOLOS**, 241 trade (11–32 per simbol), tanpa log ERROR/CRITICAL. Dibanding Fase 3: trade 351 → 241, expectancy +0,024R → +0,035R per trade, total R +8,58 → +8,42; 6 simbol membaik, 6 memburuk (sampel kecil).

Regresi (`run-ea-tests.ps1 -All`, 2026-10-04): build 0 error / 0 warning (4 target); unit 575/575 di 38 suite; 23 skenario PASS (SC-00..SC-15b); durasi 11 menit 41 detik. pytest `sdbot/tools` 84/84, `schema.py check` OK (data versi 3).

### 1.14 — 2026-10-04 — perbaikan: Critical CLOSE_ALL_FAILED palsu saat pasar tutup

- Bug: emergency close all menghitung posisi sebagai **gagal** bila broker menjawab 10018 "market closed" padahal jadwal sesi bilang buka (misalnya pukul 21:00 server), atau saat jeda 60 detik v1.13 aktif. Setelah 3 kali, `CRiskMonitor` mengirim Critical `CLOSE_ALL_FAILED` palsu.
- Perbaikan: `CloseAnyPosition` membedakan tutup / ditunda / gagal. Ditunda (jadwal tutup, jeda, atau 10018) dihitung `closedMarket`, bukan `failed`. Hook uji retcode kini juga berlaku untuk close all.
- Satu sumber jadwal sesi `SymbolSessionOpen` (waktu `TimeTradeServer`) untuk close all dan penahan request; `InTradeSession` mendukung sesi lewat tengah malam; fungsi duplikat dari v1.13 dihapus. Broker tanpa jadwal sesi sama sekali dianggap selalu buka.
- Uji: TC-RK-15 (10018 dan jeda = `closedMarket`, tanpa kiriman saat jeda); TC-EX-34 kini memakai `InTradeSession`.

Regresi (2026-10-04): build 0 error / 0 warning; unit 565/565; 21 skenario PASS (SC-00..SC-14x).

### 1.13 — 2026-10-03 — perbaikan: request saat pasar tutup

- Bug: setelah perbaikan 1.12, modify SL / partial yang ditolak "market closed" (retcode 10018) dikirim ulang setiap tick selama pasar tutup. Di live ini bisa membanjiri broker dengan request.
- Perbaikan di `CExecutor`, berlaku untuk open, modify, partial, close, dan close all:
  - request tidak dikirim di luar jadwal sesi trading simbol (`SymbolInfoSessionTrade`; broker tanpa jadwal sama sekali dianggap selalu buka);
  - setelah retcode 10018, semua request simbol ditahan 60 detik (`SDB_MARKET_CLOSED_BACKOFF_SEC`).
- Modify dan partial yang tertahan mengembalikan `SKIPPED` (dicoba lagi tanpa dihitung gagal). Order ditolak `NOT_TRADABLE`. Peringatan dicetak WARN dengan throttle.
- Uji: TC-EX-34 (jam sesi, termasuk jeda harian emas dan sesi lewat tengah malam), TC-PS-06 (satu kiriman lalu tertahan; sesi tutup = 0 kiriman); TC-PS-05 disesuaikan (partial sesudah 10018 tidak dikirim).

Regresi (2026-10-03): build 0 error / 0 warning; unit 564/564; 21 skenario PASS (SC-00..SC-14x). Backtest dasar ulang GBPUSDc, NZDUSDc, XAUUSDc (tiga simbol yang sebelumnya kena 10018): 0 log ERROR/CRITICAL, jumlah trade sama (28/31/31).

### 1.12 — 2026-10-03 — spec 13 sinyal dan entry (Fase 3 selesai)

- EA utama **membuka posisi sendiri**. `CSignalEngine` menilai setiap bar M15 tertutup sekali (penanda bar di Global Variable, bar basi dilewati). Kandidat = bar yang menyentuh zona H1 valid searah bias H4. Kandidat dinilai berurutan: pre-filter risiko → posisi instance terbuka (`POSITION_OPEN`) → trigger PA → skor ≥ 65% dari 55 (zona 30/15, tren 15/7/0, PA 10/7/3) → SL/TP. Bila lolos: lot dan pre-trade check Fase 1 → `OpenMarket` dengan `signal_id` → zona Used.
- SL = batas jauh zona ∓ 0,1 × ATR(14) H1 (SELL ditambah spread). Jarak SL wajib ≥ max(stops + spread, 0,3 ATR) dan ≤ 3 ATR. TP = zona lawan terdekat, atau 2R bila tidak ada; R:R ≥ 2.
- Telemetri: satu baris `signals` per kandidat + 3 baris `signal_scores`. ID sinyal dari SHA-256 (login, run_key, magic, bar), sehingga `trades.signal_id` terisi sebelum order dan restart tidak membuat baris ganda. Bar bukan kandidat diringkas di log harian.
- Input `InpMinConfluenceScore`, `InpMinRR`, `InpSlBufferAtr`, `InpMinSlAtr`, `InpMaxSlAtr`; preset diperbarui. Enum `POSITION_OPEN`, `SL_TOO_FAR`, `score_component`, `tp_source`. Keputusan PC-19 (mengoreksi kriteria backtest dasar PC-15).
- Alat: 6 query kalibrasi, `run-ea-tests.ps1 -Baseline` + `baseline_report.py`, skenario SC-14 / SC-14x.
- Perbaikan Fase 1 yang ditemukan uji:
  - `CalcVolume` kini menurunkan lot per step bila rugi `OrderCalcProfit` lot akhir (dibulatkan ke sen) melewati batas risiko. Sebelumnya order sinyal yang sah bisa ditolak `RISK_PER_TRADE` (TC-RK-14).
  - Retcode 10018 "market closed" tidak lagi dianggap gagal permanen. Modify/partial ditunda ke tick berikutnya tanpa ERROR dan tanpa dihitung gagal; order ditolak `NOT_TRADABLE` tanpa alert (TC-EX-33, TC-PS-05).

Backtest dasar (`-Baseline`, 12 simbol, 2025.10.01–2026.10.01, OHLC M1): **LOLOS**.
- 351 trade (18–43 per simbol), 13.742 kandidat.
- Tanpa log ERROR/CRITICAL; semua trade punya `signal_id` dan skor lengkap.
- Expectancy +0,024R per trade (5 simbol positif). Profit dinilai di Fase 5–6.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-03): build 0 error / 0 warning (4 target); unit 562/562 di 37 suite; 21 skenario PASS (SC-00..SC-14x). pytest `sdbot/tools` 82/82, `schema.py check` OK (data versi 3).

### 1.11 — 2026-10-03 — spec 12 trigger price action

- `PatternRules` (fungsi murni): enam pola candle terarah relatif ATR(14) LTF dan rentang bar, diperiksa dalam urutan bintang pagi/sore, engulfing kuat, pin bar, engulfing, tweezer, outside bar; pola pertama yang cocok menang. Pola netral (inside bar, doji, harami) tidak pernah menjadi trigger (python-bot-lessons §1). Skor kekuatan PA 10/7/3/0.
- `CPaTrigger`: 45 bar M15 tertutup, dihitung sekali per bar baru, hasil BUY dan SELL; dipasang di `CSdbApp.OnTick` setelah zona, belum dipakai untuk entry.
- Enum `pa_pattern` (kode stabil untuk konteks sinyal), ambang sebagai konstanta. Keputusan PC-18.
- Alat uji: run unit `run-ea-tests.ps1` kini mulai di Selasa..Jumat (mulai di akhir pekan membuat uji pembuka posisi gagal "market closed"). Deskripsi `#property` EA sempat masih menulis v1.09 di rilis 1.10; diperbaiki.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-03): build 0 error / 0 warning (4 target); unit 531/531 di 31 suite; 19 skenario PASS (SC-00..SC-13x); durasi total 6 menit 10 detik. pytest `sdbot/tools` 67/67, `schema.py check` OK (data versi 3).

### 1.10 — 2026-10-02 — spec 11 zona S&D

- `ZoneRules` (ATR Wilder, calon zona dari candle swing H1 dengan lebar 0,3–2,0 ATR dan gerak keluar ≥ 1,5 ATR dalam 10 bar, status, peta, zona disentuh, zona lawan, skor 30/15) dan `CZoneBook` (bangun ulang penuh tiap bar H1, penanda Used di Global Variable per magic).
- Input `InpZoneMinWidthAtr`, `InpZoneMaxWidthAtr`, `InpZoneMinLegAtr`, `InpZoneLegBars`, `InpMaxZoneAgeBars` (default dari ukuran histori H1 12 simbol, preset diperbarui).
- Perbaikan sebelum rilis: penanda Used zona dibersihkan berdasarkan jumlah bar, bukan jam kalender (gap akhir pekan sempat membuat zona yang masih aktif bisa dipakai lagi; temuan SC-13).
- Skenario SC-13 (EURUSDc) dan SC-13x (XAUUSDc): peta zona tanpa repaint, penanda Used lintas restart. Keputusan PC-17.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-02): build 0 error / 0 warning (4 target); unit 507/507 di 29 suite; 19 skenario PASS (SC-00..SC-13x); durasi total 6 menit 14 detik. pytest `sdbot/tools` 66/66, `schema.py check` OK (data versi 3).

### 1.09 — 2026-10-02 — spec 10 struktur pasar

- Lapisan Analysis: `CBarCache` (bar tertutup per TF, salin ulang hanya saat bar baru), `StructureRules` (swing fractal berjeda, BOS, EMA, bias, skor keselarasan tren), `CMarketStructure` (HTF/MTF dari gaya trading, bias HTF dengan alasan, log saat berubah).
- Input `InpSwingStrength` 2, `InpStructureLookback` 100, `InpEmaPeriod` 50, `InpEmaSlopeBars` 3 (preset diperbarui). `IsSdbotMagic` sudah di Core sejak 1.08.
- Skenario SC-12 (EURUSDc) dan SC-12x (XAUUSDc): analisis selama run = analisis dari histori, termasuk setelah restart. Belum ada entry dari sinyal. Keputusan PC-15, PC-16.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-02): build 0 error / 0 warning (4 target); unit 476/476 di 27 suite; 17 skenario PASS (SC-00..SC-12x); durasi total 4 menit 20 detik. pytest `sdbot/tools` 65/65, `schema.py check` OK (data versi 3).

### 1.08 — 2026-10-02 — Fase 2 selesai (spec 09 notifier Telegram)

- `CTelegramTransport`: `sendMessage` lewat `WebRequest` (HTML, timeout 3 detik), klasifikasi respons, jarak 1 detik dan jeda 429 dibagi semua instance (GV `NT_TG_NEXT`), teks polos bila HTML ditolak, nonaktif sampai init ulang bila URL belum diizinkan / token / chat salah, maks 1 kiriman per 10 detik saat gagal sementara. Token tidak pernah ditulis ke log, DB, atau JSON input sesi.
- Push HP (`SendNotification`) untuk Critical yang gagal di Telegram atau saat Telegram nonaktif, dibatasi 2/detik dan 10/menit.
- Pemimpin per akun (lease GV) untuk heartbeat tanpa bunyi (`InpHeartbeatMinutes`, default 60) dan laporan harian dari history deal MT5 (hari tanpa aktivitas dilewati, hari yang terlewat dikirim kemudian); pesan start/stop per instance, start menyebut akhir sesi lalu.
- Input `InpTelegramToken`, `InpTelegramChatID`, `InpHeartbeatMinutes`; preset repo memuatnya kosong; `tools/make_local_presets.py` membuat `*.local.set` dari `.env` bot Python.
- `IsSdbotMagic` pindah ke `Core/Utils.mqh`; batas kirim saat deinit 2 detik (MT5 memotong `OnDeinit` di 2.5 detik). Keputusan PC-14.
- Skenario SC-11: heartbeat, laporan harian per hari server (termasuk Jumat yang baru terkirim Senin di tester), start/stop, pemimpin setelah restart.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-02): build 0 error / 0 warning (4 target); unit 451/451 di 25 suite; 15 skenario PASS (SC-00..SC-11); durasi total 2 menit 24 detik. pytest `sdbot/tools` 64/64, `schema.py check` OK (data versi 3).

### 1.07 — 2026-10-01 — spec 08 notifier core

- `CNotifier` (lapisan Notify) sebagai sink di `CTeeSink`: semua alert Fase 1 plus pesan posisi dibuka/ditutup (`TRADE_OPENED`, `TRADE_CLOSED`), tanpa mengubah modul penghasilnya.
- Aturan kirim PRD: Critical lebih dulu tanpa limit; Medium dan Info cooldown 5 menit per tipe (per akun untuk tipe akun, lewat Global Variables); kuota non-Critical 20 per jam server per akun; pesan non-Critical > 30 menit dibuang; maks 2 kiriman per `OnTimer`, retry 3x, jeda sesuai permintaan transport, antrean maks 100.
- Format gaya bot Python: emoji per level, penanda `SDBot` + simbol + akun (`TESTER` di tester) + versi, HTML ter-escape, harga sesuai digit simbol, potong 4096 karakter tanpa merusak tag.
- Status kirim di tabel `alerts` lewat Logger (skema v3: `notify_key`, `status_reason`); restart menandai pesan tertunda dan mengirim ulang Critical muda; deinit mengirim Critical tersisa.
- Pesan masih dicetak ke log Experts/tester (transport log); Telegram dan push HP di spec 09. Keputusan PC-13.
- Skenario SC-10 (transport palsu): event trade, prioritas Critical, cooldown, kuota, retry, status DB, hanya dari timer, maks 2 per siklus.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-01): build 0 error / 0 warning (4 target); unit 403/403 di 24 suite; 14 skenario PASS (SC-00..SC-10); durasi total 2 menit 9 detik. pytest `sdbot/tools` 57/57, `schema.py check` OK (data versi 3).

### 1.06 — 2026-10-01 — Fase 1 selesai (spec 07 integration)

- Metrik `OnTester` PRD: expectancy R per trade ÷ max drawdown relatif equity; 0 bila trade dengan R < 30 atau DD 0.
- Input `InpPresetTag`: WARN bila preset dimuat di chart simbol lain.
- 12 preset `Presets/SDBot_DAY_<SIMBOL>c.set` (simbol bot Python, PC-10/PC-12), dibangkitkan `tools/gen_presets.py`; divalidasi dengan `ValidateInputValues` asli.
- 8 query analisis di `tools/queries/` (join `login + run_key + position_id`), data contoh skema v2.
- Runner: mode optimasi (SC-09: DB tester tidak berubah, metrik custom ada di laporan), durasi total di ringkasan.
- Perbaikan alat: `schema.py` tidak lagi menerapkan blok seed untuk migrasi yang belum ada.
- Dokumen: checklist manual, diagram alur `docs/flows/`, changelog ini.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-01): build 0 error / 0 warning (4 target); unit 327/327 di 21 suite; 13 skenario PASS (SC-00, 01, 01b, 02, 03, 03r, 04, 04b, 05, 06, 07, 08, 09); durasi total 1 menit 55 detik. pytest `sdbot/tools` 52/52, `schema.py check` OK (data versi 2).

Belum ada logika entry: EA tidak membuka posisi apa pun sampai Fase 3. Uji manual tertunda: [ea/tests/manual-checklist.md](ea/tests/manual-checklist.md).

### 1.05 — 2026-09-30 — spec 06 position

- Breakeven 1R (spread + komisi + buffer), partial 50% di 1.5R (`PARTIAL_SKIPPED` bila lot terlalu kecil), trailing ATR(14) × 2 setelah BE, SL hanya membaik, satu modifikasi SL per tick.
- SL yang dihapus manual dipasang kembali (`SL_RESTORED`, gagal 3x `SL_MISSING` Critical); modify/partial gagal: retry tiap 30 detik maks 3, lalu satu `MODIFY_FAILED`.
- Deal dan closure dengan alasan `TP`/`SL`/`BE_STOP`/`TRAIL_STOP`/`MANUAL`/`STOP_OUT`/`EA_CLOSE`/`ROLLOVER`/`OTHER`, R hasil, MFE/MAE dari bar M1; kepemilikan posisi dari deal pembuka (close all lintas instance tercatat pemilik).
- Rekonsiliasi saat init: posisi terbuka `RECONCILED`, deal dan closure yang terlewat saat EA mati.
- Skenario SC-01, SC-01b, SC-04, SC-04b. Keputusan PC-11.

### 1.04 — 2026-09-30 — spec 05 risk

- Lot dari risiko % lewat `OrderCalcProfit`, dibulatkan ke bawah; pre-trade check berurutan (`NOT_TRADABLE`, `STOPPED`, `DAILY_PAUSE`, `RISK_PER_TRADE`, `MAX_OPEN_RISK`, `CLASS_POSITION_LIMIT`, `MARGIN_LOW`).
- Monitor tiap detik: puncak equity, level drawdown (5% info, 10% lot × 0.5, 15% close all + STOPPED; pulih di bawah min(8%, reduce × 0.8)), rugi harian 3%, margin 300%/200%, operasi saldo; status bersama di Global Variables dengan compare-and-set.
- Batas posisi per kategori aset (forex major 5, cross 3, komoditas 1, crypto 1); simbol mengikuti bot Python (PC-10).
- Skenario SC-02, SC-03, SC-03r, SC-05, SC-07. Keputusan PC-09, PC-10.

### 1.03 — 2026-09-30 — spec 04 execution harness

- `CExecutor` satu-satunya pintu ke broker: validasi SL/TP/volume, `OrderCheck`, retry ≤ 3 untuk retcode sementara, deteksi order ganda lewat ID permintaan di komentar `SDB|SL|ID`.
- `CSdbApp` orkestrasi bersama EA dan harness; `SDBot.mq5` hanya meneruskan event.
- Harness skenario Strategy Tester dengan assert otomatis; SC-00, SC-06, SC-08.
- Skema v2: `run_key` memisahkan run backtest di `sdbot_tester.sqlite` (PC-08). Keputusan PC-07.

### 1.02 — 2026-09-29 — spec 03 storage migrations

- SQLite `sdbot.sqlite` / `sdbot_tester.sqlite` lewat `CLogger` (antrean, satu transaksi per flush, penulisan idempoten), sesi dengan `input_hash`.
- Migrasi maju lewat `tools/schema.py`, diterapkan EA saat start. Keputusan PC-01, PC-04.

### 1.01 — 2026-09-29 — spec 02 core account

- Input dan batas aman, validasi akun (cent, hedging, `InpAllowLiveTrading`), koneksi dan izin, status bersama di Global Variables, log terminal. Keputusan PC-02.

### 1.00 — 2026-09-29 — spec 01 tooling

- Struktur folder, junction MT5, `build-ea.ps1` (0 error / 0 warning), framework unit test MQL5, `run-ea-tests.ps1`. Keputusan PC-03, PC-05.

## Backoffice

Belum dimulai (B1–B6 setelah Fase EA yang membutuhkannya).
