# SDBot

Expert Advisor MQL5 untuk MetaTrader 5 (zona Supply & Demand + skor konfluensi) beserta backoffice lokal. Proyek terpisah dari bot Python di repo yang sama.

- Kebutuhan produk: [docs/PRD-EA.md](docs/PRD-EA.md), [docs/PRD-Backoffice.md](docs/PRD-Backoffice.md)
- Aturan kode dan struktur: [docs/RULES.md](docs/RULES.md)
- Rencana kerja per spec: [specs/README.md](specs/README.md)

Status: Fase 5 (konfirmasi) berjalan: spec 17 (1.19) alat ukur in-sample/out-of-sample, skema v4 (`signal_scores.active` untuk komponen bayangan); acuan IS 2024-04..2026-06 493 trade PF 1,06, OOS 2026-07..2026-10 52 trade PF 1,07 (OHLC M1). Fase 4 (filter) **selesai** di 1.17. Versi EA **1.19** (1.18 perbaikan lot pada pair kuotasi non-USD; filter sesi dan spread di 1.15, eksposur mata uang di 1.16, filter berita di 1.17: kalender MT5 live, CSV `ExportCalendar` di tester, blackout high ±15 menit; backtest dasar berfilter lolos, 215 trade, +0,058R per trade). Fase 3 (strategi inti) **selesai** di 1.12; 1.13–1.14 perbaikan saat pasar tutup. Fase 2 (notifikasi) **selesai** di 1.08. Fase 1 (fondasi) **selesai** di 1.06 (spec 01–07: alat build/uji, input, validasi akun, koneksi, status bersama, database SQLite + migrasi, executor order, orkestrasi `CSdbApp`, harness skenario, risk management: lot dari risiko %, pre-trade check, drawdown, rugi harian, margin, emergency stop, operasi saldo, batas posisi per kategori, manajemen posisi: BE, partial, trailing ATR, SL yang hilang, closure dengan alasan SL/BE_STOP/TRAIL_STOP/EA_CLOSE/..., MFE/MAE, rekonsiliasi setelah restart; metrik `OnTester`, preset 12 simbol, query analisis). Spec 08 (1.07): notifier dengan aturan kirim PRD (Critical lebih dulu, cooldown, kuota 20/jam per akun, pesan basi 30 menit), format pesan gaya bot Python, status kirim di tabel `alerts` (skema v3). Spec 09 (1.08): Telegram (bot dan chat bot Python), push HP untuk Critical, heartbeat dan laporan harian satu per akun, pesan start/stop, preset pribadi dari `.env`. Spec 10 (1.09): analisis struktur HTF/MTF (swing fractal berjeda, BOS, EMA 50, bias HTF) per bar baru, tanpa repaint (SC-12). Spec 11 (1.10): peta zona S&D H1 (candle swing, lebar 0,3–2,0 ATR, gerak keluar ≥ 1,5 ATR, status Fresh/Tested/Lemah/Invalid/Kedaluwarsa/Used) dibangun ulang tiap bar H1, penanda Used di Global Variable (SC-13). Spec 12 (1.11): pola candle terarah M15 (bintang, engulfing kuat, pin bar, engulfing, tweezer, outside bar; pola netral tidak pernah jadi trigger) dengan skor kekuatan PA 10/7/3. Spec 13 (1.12): **EA membuka posisi sendiri**. Pipeline sinyal per bar M15 (bias + zona + trigger PA, skor ≥ 65% dari 55, SL/TP dari zona, R:R ≥ 2) memakai jalur risiko Fase 1, dengan telemetri `signals` + `signal_scores` dan query kalibrasi. Backtest dasar 12 simbol 12 bulan lolos (351 trade; `tools/run-ea-tests.ps1 -Baseline`).

## Konfigurasi dan tuning

PRD mengganti konfigurasi YAML bot Python dengan **input EA** yang disimpan sebagai file `.set`. Setiap jenis konfigurasi punya satu tempat:

| Apa | File | Diubah oleh | Kapan berlaku |
|---|---|---|---|
| **Input EA** (semua angka yang bisa di-tuning: risiko, BE, partial, trailing, skor, filter) | `ea/src/Include/SDBot/Core/Inputs.mqh`: satu-satunya tempat deklarasi `input`, dengan default dari PRD | Developer (default); trader lewat tab Inputs MT5 atau file `.set` | Saat EA dipasang atau input diubah (EA re-init) |
| Batas aman input | `ea/src/Include/SDBot/Core/InputRules.mqh` | Developer | EA menolak jalan jika input di luar batas |
| **Preset per simbol** | `ea/src/Presets/SDBot_DAY_<SIMBOL>c.set`, 12 simbol bot Python (PC-10): forex major EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD; cross EURJPY, GBPJPY; komoditas XAUUSD, XAGUSD; crypto BTCUSD. Dibangkitkan `tools/gen_presets.py` (jangan diedit tangan); Fase 1 identik kecuali magic dan `InpPresetTag`, nilai per kategori bot Python dicatat sebagai komentar sampai inputnya ada (PC-12) | Hasil tuning, di-commit lewat generator | Dimuat di tab Inputs: Load |
| Preset pribadi (rahasia) | `*.local.set`, misalnya `SDBot_DAY_EURUSDc.local.set` | Trader, **tidak di-commit** | Berisi token dan chat ID Telegram (sama dengan `.env` bot Python) |
| Konstanta tetap dari PRD | `ea/src/Include/SDBot/Core/Constants.mqh` (retry 3x, cooldown 30 detik, DD info 5%, pulih 8% (atau `InpDDReducePct` × 0.8 bila lebih kecil), margin alert 300% / blok 200%, close all tiap 5 detik (pasar tutup 60 detik), Critical close all gagal setelah 3x lalu tiap 15 menit, posisi tanpa SL = 1% balance, scan operasi saldo tiap 10 detik, dll.) | Developer, lewat perubahan kode + compile | Versi EA berikutnya |
| Setting dari panel backoffice (Fase B5) | tabel `settings` di `sdbot_control.sqlite` | Admin lewat panel | Siklus timer berikutnya; **hanya boleh lebih ketat** dari input MT5 |
| File database EA | `sdbot.sqlite` (live), `sdbot_tester.sqlite` (Strategy Tester), `sdbot_unittest.sqlite` (unit test) di folder Common MT5 (`%APPDATA%\MetaQuotes\Terminal\Common\Files`). Optimasi tidak menulis DB. Konstanta `SDB_DB_*` di `Constants.mqh`: busy timeout 500 ms, antrean 2000 event, alert DB tidak bisa ditulis setelah 300 detik, buka ulang tiap 60 detik | EA sendiri; skema hanya lewat `tools/schema.py` | Migrasi diterapkan otomatis saat EA start |
| Skema dan enum DB | `shared/schema/` (`migrations/data/*.sql`, `enums.md`); file hasil generate `Storage/Migrations.mqh`, `Core/SchemaEnums.mqh`, `data_db.sql`, fixture | Developer lewat `schema.py new/build`, dicek pre-commit | Versi EA berikutnya |
| Status runtime (bukan konfigurasi) | Global Variables `SDB_<login>_*` di terminal: `PEAK_EQUITY`, `STOPPED`, `DAILY_PAUSE`, `LOT_REDUCED`, `DD_LEVEL`, `DAY_START_BAL`/`DAY_START_DATE`, `LAST_BAL_DEAL`/`LAST_BAL_TIME`, `MARGIN_LOW`, `CLOSE_ALL_ALERT_AT`, per instance `<magic>_RESET_SEEN`, `<magic>_REQ_COUNTER`, `<magic>_LAST_DEAL`/`<magic>_LAST_DEAL_TIME` (deal terakhir yang dicatat); di tester juga `RUN_KEY`. Satu set per akun, dibagi semua instance (compare-and-set) | EA sendiri | Jangan diedit; buka STOPPED hanya lewat `InpResetEmergencyStop` |
| Konstanta eksekusi dan posisi | `Constants.mqh`: ulang maksimal 3x dengan jeda 500 ms, deviasi 10 point, cari order ambigu 300 detik ke belakang, snapshot akun tiap 60 detik; posisi: geser SL minimal 5 point, retry modify tiap 30 detik maks 3 lalu alert, rekonsiliasi 30 hari tanpa GV, toleransi BE_STOP buffer + 2 point | Developer | Versi EA berikutnya |
| Skenario uji harness | `ea/tests/scenarios/SC-nn_<nama>.ini` (simbol, periode, model, tanggal) + `.set` bernama sama (input EA dan input harness) | Developer | Dibaca `run-ea-tests.ps1 -Scenario SC-nn` |
| Path mesin untuk alat build/uji | `tools/mt5-paths.local.json` (contoh: `tools/mt5-paths.example.json`) | Developer, **tidak di-commit** | Dibaca setiap kali skrip `tools/` jalan |

Kolom "Dibuat di" pada tabel input di bawah menunjukkan spec yang menambahkannya. Sebelum spec itu selesai, file dan input tersebut belum ada.

### Daftar input

| Grup | Input | Default | Batas | Dibuat di |
|---|---|---|---|---|
| Umum | `InpMagicNumber` | 2026091901 | 2026091901–2026091999, satu nomor per pair | spec 02 |
| Umum | `InpTradingStyle` | Day trading (H4/H1/M15) | — | spec 02 |
| Umum | `InpSymbolSuffix` | kosong (`c` di preset akun cent) | — | spec 02 |
| Umum | `InpAllowLiveTrading` | false | — | spec 02 |
| Umum | `InpLogLevel` | INFO | — | spec 02 |
| Umum | `InpPresetTag` | kosong (preset mengisi simbolnya, mis. `EURUSDc`) | WARN bila beda dengan simbol chart | spec 07 |
| Risiko | `InpRiskPerTradePct` | 0.5 | 0 < x ≤ 1.0 | spec 02 (dipakai spec 05) |
| Risiko | `InpMaxOpenRiskPct` | 3.0 | risk per trade ≤ x ≤ 10 | spec 02 (dipakai spec 05) |
| Risiko | `InpDailyLossPct` | 3.0 | 0 < x ≤ 10 | spec 02 (dipakai spec 05) |
| Risiko | `InpMaxPosForexMajor` / `InpMaxPosForexCross` / `InpMaxPosCommodity` / `InpMaxPosCrypto` | 5 / 3 / 1 / 1 (dari bot Python; batas akun, sama di semua preset) | 1–20 | spec 05 |
| Risiko | `InpMaxSameDirectionPerCurrency` | 2 posisi SDBot searah per mata uang di akun (dengan arah; XAU/XAG/BTC mata uang sendiri); 0 = mati | 0–10 | spec 15 |
| Risiko | `InpDDReducePct` / `InpDDStopPct` | 10 / 15 | 0 < reduce < stop ≤ 50 | spec 02 (dipakai spec 05) |
| Risiko | `InpResetEmergencyStop` | false | reset hanya saat berubah false → true | spec 02 (dipakai spec 05) |
| Posisi | `InpBreakevenR` / `InpBreakevenBufferPoints` | 1.0 / 2 | BE R < partial R | spec 02 (dipakai spec 06) |
| Posisi | `InpPartialR` / `InpPartialPct` | 1.5 / 50 | 0 < pct < 100 | spec 02 (dipakai spec 06) |
| Posisi | `InpTrailATRPeriod` / `InpTrailATRMult` | 14 / 2.0 (ATR di M15) | period 2–200, mult 0–10 | spec 02 (dipakai spec 06) |
| Analisis | `InpSwingStrength` | 2 (bar tiap sisi fractal; swing diakui setelah N bar kanan tutup) | 1–5 | spec 10 |
| Analisis | `InpStructureLookback` | 100 bar (jendela BOS / arah struktur) | 20–500 | spec 10 |
| Analisis | `InpEmaPeriod` / `InpEmaSlopeBars` | 50 / 3 (arah EMA: close vs EMA + kemiringan) | 10–400 / 1–20 | spec 10 |
| Entry | `InpEntryMode` | Market (opsi Limit) | — | Fase 5 (PC-19) |
| Zona | `InpZoneMinWidthAtr` / `InpZoneMaxWidthAtr` | 0.3 / 2.0 × ATR(14) H1 (lebar zona dari candle swing) | 0.05–1.0 / 0.5–5.0, min < max | spec 11 |
| Zona | `InpZoneMinLegAtr` / `InpZoneLegBars` | 1.5 × ATR dalam 10 bar (gerak keluar dari zona) | 0.5–5.0 / 3–50 | spec 11 |
| Zona | `InpMaxZoneAgeBars` | 100 bar H1 (PRD) | 20–500 | spec 11 |
| Entry | `InpMinConfluenceScore` | 65 (% dari skor maksimum komponen aktif; Fase 3: 55 → skor ≥ 36) | 0–100 | spec 13 |
| Entry | `InpMinRR` | 2.0 (TP ke zona lawan terdekat, atau 2R bila tidak ada) | 1.0–10.0 | spec 13 |
| Entry | `InpSlBufferAtr` | 0.1 × ATR(14) H1 di luar batas jauh zona (SELL + spread) | 0–1.0 | spec 13 |
| Entry | `InpMinSlAtr` / `InpMaxSlAtr` | 0.3 / 3.0 × ATR(14) H1 (jarak SL; minimal juga ≥ stops level + spread) | 0.05–2.0 / 0.5–10.0, min < max | spec 13 |
| Filter | `InpMaxSpreadPoints` | per simbol di preset = 3 × median spread live (EURUSD 24 … XAU 720, BTC 3000 point); 0 = mati | 0–100000 | spec 14 |
| Filter | `InpSessionTokyo` / `InpSessionLondon` / `InpSessionNewYork` | false / true / true (UTC: Tokyo 00–08, London 08–17, New York 13–22; semua false = mati) | — | spec 14 |
| Filter | `InpTesterUtcOffsetHours` | 0 (selisih server–UTC di Strategy Tester; Exness GMT+0) | −12..14 | spec 14 |
| Filter | `InpNewsFilter` / `InpNewsHighMinutes` / `InpNewsMediumMinutes` | true / 15 / 0 menit (± waktu rilis, mata uang simbol; XAU/XAG/BTC lewat USD; 0 = tidak diblokir) | — / 0–240 / 0–240 | spec 16 |
| Filter | `InpNewsCsvFile` | `sdbot_calendar.csv` di Common\Files (hanya tester; dibuat `ExportCalendar`) | — | spec 16 |
| Notifikasi | `InpTelegramToken` / `InpTelegramChatID` | kosong (isi di `*.local.set` lewat `tools/make_local_presets.py`); kosong = pesan hanya di log | — (tidak masuk `inputs_json`, hanya `InpTelegramConfigured`) | spec 09 |
| Notifikasi | `InpHeartbeatMinutes` | 60 | 0 (mati) atau 5–1440 | spec 09 |
| Backoffice | `InpEnableBackoffice` / `InpControlPollSeconds` | true / 2 | — | Fase B5 |

Parameter strategi lainnya (bias HTF, deteksi zona, buffer SL, nilai skor per komponen, Fibonacci, trendline, RSI) belum final. Draf katalognya ada di [specs/README.md](specs/README.md#katalog-parameter-strategi-draf-difinalkan-di-spec-fase-3-dan-5), dan akan dipindahkan ke tabel ini saat spec Fase 3 dan 5 disetujui.

### Alur tuning

1. Ubah nilai input di Strategy Tester (tab Inputs), atau jalankan **optimasi** dengan rentang nilai. Metrik optimasi SDBot adalah expectancy per trade dalam R ÷ max drawdown (`OnTester`).
2. Bandingkan hasil backtest di `sdbot_tester.sqlite` (query siap pakai di `tools/queries/`, misalnya `by_run.sql`, `by_session_inputs.sql`, `be_leak.sql`): setiap run tercatat di tabel `sessions` bersama `input_hash` dan nilai input lengkap (`inputs_json`), jadi hasil bisa dikelompokkan per setelan. Karena position ID dan deal ticket di tester mulai dari angka yang sama di setiap run, baris `trades`/`deals`/`closures`/`balance_ops`/`position_events` dibedakan per run lewat kolom `run_key` (ID sesi pertama run; di live selalu 0); gabungkan tabel dengan `login + run_key + position_id`. Query siap pakai ada di `tools/queries/` (spec 07).
3. Nilai yang terbukti lebih baik (backtest + forward test sesuai PRD) disimpan ke preset `ea/src/Presets/SDBot_DAY_<PAIR>c.set` dan di-commit.
4. Jika yang berubah adalah **default** di `Inputs.mqh` atau konstanta di `Constants.mqh`, perubahannya juga dicatat di `docs/PENDING-CHANGES.md` agar PRD ikut diperbarui (skill `sdbot-docs-sync`).
5. Di akun live, perubahan setting yang sifatnya mengetatkan (misalnya menurunkan risiko) bisa lewat panel backoffice tanpa membuka MT5 (Fase B5).

## Notifikasi Telegram

SDBot memakai bot dan chat Telegram yang sama dengan bot Python (PC-06). Setiap pesan diawali penanda `SDBot` · simbol (atau `AKUN <login>` untuk heartbeat dan laporan harian) · `CENT`/`REAL`/`DEMO`/`TESTER` · versi.

1. MT5: Tools > Options > Expert Advisors, centang Allow WebRequest dan tambahkan `https://api.telegram.org`. Tab Notifications: aktifkan push dan isi MetaQuotes ID (untuk Critical saat Telegram gagal).
2. `uv run python sdbot/tools/make_local_presets.py` membuat `SDBot_DAY_<SIMBOL>c.local.set` dari `.env` bot Python. Muat file `.local.set` (bukan preset repo) di tab Inputs.
3. Token kosong: EA jalan, pesan hanya di log Experts. URL belum diizinkan, token atau chat salah: Telegram nonaktif sampai EA di-init ulang, satu log CRITICAL dan satu push HP.

Aturan kirim: Critical lebih dulu tanpa batas; Medium/Info cooldown 5 menit per tipe; kuota non-Critical 20 pesan per jam server per akun; pesan basi 30 menit dibuang; jarak kirim 1 detik untuk semua instance; saat gagal sementara maks 1 kiriman per 10 detik. Heartbeat (tanpa bunyi, tiap `InpHeartbeatMinutes`) dan laporan harian dikirim satu instance pemimpin per akun; start/stop per instance tanpa bunyi. Status setiap pesan ada di tabel `alerts` (`status`, `status_reason`).

## Alat pengembangan

Semua skrip di `tools/`, dijalankan dari PowerShell (`powershell -ExecutionPolicy Bypass -File …`):

| Skrip | Fungsi |
|---|---|
| `link-mt5.ps1 -DataDir <folder data MT5>` | Hubungkan `ea/src` dan `ea/tests` ke MT5 lewat junction |
| `build-ea.ps1` | Compile EA dan entry point uji; gagal bila ada error atau warning |
| `run-ea-tests.ps1 [-Unit] [-Scenario SC-xx] [-All]` | Compile lalu jalankan unit test/skenario di Strategy Tester terminal uji; exit 0 = semua lulus |
| `run-ea-tests.ps1 -Baseline [-Symbols EURUSDc,...] [-CompareFrom N -CompareTo M]` | Backtest dasar: EA utama + preset per simbol, 12 bulan (`ea/tests/baseline/BL-*.ini`, sekitar 25 menit), lalu `baseline_report.py` menilai kriteria Fase 4 PC-22 (≥ 200 trade, ≥ 10 per simbol, `signal_id` + skor lengkap, tanpa log ERROR/CRITICAL); pembanding per simbol dari sesi DB (N, M] |
| `run-ea-tests.ps1 -ExportCalendar` | Jalankan script `SDBot\ExportCalendar` di terminal uji (harus login, sekitar 5 menit): kalender MT5 2025-01-01 s.d. +7 hari ke `Common\Files\sdbot_calendar.csv` untuk filter berita di tester. Ulangi sebelum backtest yang mencakup minggu baru |
| `run-ea-tests.ps1 -Baseline -Period IS\|OOS\|ALL` | Backtest dasar Fase 5 (spec 17): periode in-sample / out-of-sample dari `ea/tests/baseline/periods.ini` dengan real ticks; laporan per periode dengan PF, DD, dan status kriteria PRD tahap 2–3. Opsi `-FromDate`, `-ToDate`, `-Model` untuk periode bebas |
| `run-ea-tests.ps1 -ProbeHistory` | Rentang histori tester per simbol (tester dijalankan pada 2015 yang kosong, `tick_history.py` mengurai jurnal); dasar `periods.ini` |
| `baseline_report.py --db <sdbot_tester.sqlite> --after-session N [--periods periods.ini]` | Laporan per simbol dari DB tester: kandidat, tahap tolak, trade, win rate, R, PF, DD%; per periode bila `--periods`; dipanggil `-Baseline` |
| `component_report.py --db <sdbot_tester.sqlite> --sessions A-B [--periods periods.ini] [--candidates]` | Hasil trade per nilai komponen skor (aktif dan bayangan), IS vs OOS, dengan status aktivasi PC-25; `--candidates` = distribusi nilai per tahap tolak |
| `uv run python tools/make_local_presets.py [--force]` | Buat `SDBot_DAY_<SIMBOL>c.local.set` dari preset repo + `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` di `.env` bot Python; tidak menimpa yang sudah disunting tanpa `--force`; gagal bila hasilnya tidak diabaikan git |
| `uv run python tools/gen_presets.py` | Bangkitkan ulang 12 preset dari tabel di skrip (pytest memastikan file sama dengan hasil generator) |
| `tools/queries/*.sql` | Query analisis (ringkasan per simbol/versi, alasan tutup, kebocoran BE, loser yang tidak pernah profit, per input, per run, operasi saldo, alert); diuji terhadap fixture |
| `uv run python tools/schema.py new data "<deskripsi>"` | Buat file migrasi baru bernomor berikutnya |
| `uv run python tools/schema.py build` / `check` / `release` / `status <file>` | Bangun file hasil generate dari migrasi; cek konsistensi (juga dijalankan pre-commit); tandai migrasi sudah rilis; lihat versi skema sebuah file DB |

### Harness skenario

`tests/Experts/SDBotTests/SDBotHarness.mq5` memakai `CSdbApp` yang sama dengan EA utama, ditambah entry terjadwal, simulasi restart, dan pemeriksa skenario. Harness hanya jalan di Strategy Tester (di chart live gagal init dengan CRITICAL), dan wajib memakai magic cadangan `2026091900`. Input tambahannya (hanya ada di harness):

| Input | Isi |
|---|---|
| `InpTestRunId` | ID run, diisi runner |
| `HarnessScenario` | ID skenario yang diperiksa di akhir run (`SC-00`, `SC-01`, `SC-01b`, `SC-02`, `SC-03`, `SC-03r`, `SC-04`, `SC-04b`, `SC-05`, `SC-06`, `SC-07`, `SC-08`, `SC-10`, `SC-11`, `SC-12`, `SC-12x`, `SC-13`, `SC-13x`, `SC-14`, `SC-14x`, `SC-15`, `SC-15b`, `SC-16`; `SC-09` optimasi diperiksa runner); ID lain = FAIL |
| `HarnessEveryBars` | entry setiap N bar chart |
| `HarnessDirection` | 0 BUY, 1 SELL, 2 bergantian |
| `HarnessSlPoints` / `HarnessTpPoints` | jarak SL/TP dari harga (point) |
| `HarnessMaxOpen` | posisi sendiri maksimum |
| `HarnessFixedLot` | lot tetap; 0 = lot dari risiko (`CalcVolume`). Selalu lewat pre-trade check |
| `HarnessRestartAtBar` | bar tempat orkestrasi dibuat ulang (0 = tanpa restart) |
| `HarnessRestartBarsAfterStop` | restart N bar setelah STOPPED pertama terlihat (0 = tidak) |
| `HarnessRestartAfterPartial` | restart di bar ke-N setelah partial, hanya bila posisinya masih terbuka (0 = tidak) |
| `HarnessDetachBars` | saat restart, app dilepas N bar dulu (simulasi EA mati; posisi tetap di broker) |
| `HarnessWithdrawAtBar` / `HarnessWithdrawPct` | tarik saldo (`TesterWithdrawal`) di bar ini atau sesudahnya saat tanpa posisi; besar % balance |
| `HarnessTransportScript` | skrip transport palsu notifier (`OK,TEMP,LIMITED:60,PERM`, elemen terakhir berulang); kosong = transport log biasa |
| `HarnessTransportFailType` | tipe alert yang selalu gagal sementara di transport palsu |
| `HarnessRecordAnalysis` | rekam analisis HTF/MTF tiap bar baru untuk uji tanpa repaint (SC-12) |
| `HarnessRecordZones` / `HarnessMarkUsedAtBar` | rekam sidik peta zona tiap bar H1; tandai zona valid terbaru Used di bar ini (SC-13) |
| `HarnessPipeline` | pipeline sinyal membuka posisi seperti EA utama (SC-14); pakai `HarnessEveryBars=0` |
| `HarnessExposureSetup` | bar pertama: BUY GBPUSDc + BUY AUDUSDc dengan magic SDBot lain, SL/TP 5000 point (SC-16) |
| `HarnessAlertBurstAtBar` | kirim burst alert uji (2x `ORDER_FAILED`, tipe gagal, 25 Info) di bar ini (0 = tidak) |

Menjalankan: `powershell -ExecutionPolicy Bypass -File tools/run-ea-tests.ps1 -Scenario SC-00,SC-08` (atau `-All` untuk unit + semua skenario). Skenario baru = pasangan `.ini`/`.set` di `ea/tests/scenarios/` plus cabang `CheckScenario` di `ea/tests/Include/SDBotTests/Scenarios.mqh`. Skenario dengan `Optimization=1` di `.ini` diperiksa runner (file DB tester tidak berubah, laporan optimasi berisi hasil metrik custom). Uji manual: [ea/tests/manual-checklist.md](ea/tests/manual-checklist.md). Alur EA: [docs/flows/](docs/flows/README.md).

Terminal uji di mesin ini adalah instalasi "Broker A". Terminal "Broker B" dipakai bot Python dan tidak disentuh alat-alat ini.
