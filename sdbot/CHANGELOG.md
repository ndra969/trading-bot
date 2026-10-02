# Changelog SDBot

Format: satu bagian per rilis EA dan backoffice (RULES §Git). Versi EA `MAJOR.MINOR`: MAJOR = memengaruhi posisi terbuka atau skema DB lintas fase; Fase 1 memakai `1.00`–`1.06`, `2.00` setelah validasi Fase 6 (PC-03).

## EA

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
