# SDBot specs

Spec-driven development dengan metode Kiro (skill `sdbot-spec`). Setiap spec punya `requirements.md` → `design.md` → `tasks.md`, masing-masing disetujui sebelum lanjut, lalu task dikerjakan satu per satu dengan TDD.

## Fase 1 — Fondasi EA

Ringkasan lingkup, use case, arsitektur bersama, dan strategi uji: [fase-1-overview.md](fase-1-overview.md).

Kerjakan **berurutan**. Spec berikutnya baru dimulai setelah semua task spec sebelumnya selesai dan terverifikasi.

| # | Spec | Isi | Butuh | Bukti selesai | Status |
|---|---|---|---|---|---|
| 1 | [ea-01-tooling](ea-01-tooling/) | Kerangka folder, junction MT5, compile otomatis, framework unit test, runner tester, cek SQLite MT5 | — | `build-ea` dan `run-ea-tests` jalan; self-test framework lulus | **Done** 2026-09-29 (2 cek manual tertunda) |
| 2 | [ea-02-core-account](ea-02-core-account/) | Core (tipe, konstanta, input, util, state GV, event sink), validasi akun, koneksi, log terminal | 1 | suite CoreUtils + AccountRules ALL PASS | **Done** 2026-09-29 (MC-01..06 manual tertunda) |
| 3 | [ea-03-storage-migrations](ea-03-storage-migrations/) | Skema SQLite baru, migrasi via skrip, file DB live vs tester terpisah, `CLogger` | 2 | pytest `schema.py` + suite Storage ALL PASS | **Done** 2026-09-29 (MC-DB-01..02 manual tertunda) |
| 4 | [ea-04-execution-harness](ea-04-execution-harness/) | `CExecutor`, orkestrasi `CSdbApp`, `SDBot.mq5`, harness uji dasar | 2, 3 | suite Execution ALL PASS, SC-06 PASS | **Done** 2026-09-30 (MC-EX-01..02 manual tertunda; skema v2 `run_key`, PC-08) |
| 5 | [ea-05-risk](ea-05-risk/) | Lot sizing, pre-trade check, drawdown, rugi harian, emergency stop, operasi saldo | 4 | suite RiskMath ALL PASS, SC-02/03/05/07 PASS | **Done** 2026-09-30 (MC-RK-01..02 manual tertunda; PC-09, PC-10) |
| 6 | [ea-06-position](ea-06-position/) | BE, partial, trailing, deteksi closure, restart aman | 4, 5 | suite PositionMath ALL PASS, SC-01/04 PASS | **Done** 2026-09-30 (MC-PS-01..04 manual di Fase 3; PC-11) |
| 7 | [ea-07-integration](ea-07-integration/) | Metrik OnTester, preset `.set`, checklist manual, regresi penuh, DoD Fase 1 | 1–6 | semua suite + SC-01..08 PASS, MC Fase 1 dicek | **Done** 2026-10-01 (Fase 1 selesai, v1.06; MC di `ea/tests/manual-checklist.md`; PC-12) |

```mermaid
flowchart LR
    S1[01 tooling] --> S2[02 core-account] --> S3[03 storage-migrations] --> S4[04 execution-harness]
    S4 --> S5[05 risk] --> S6[06 position] --> S7[07 integration]
    S4 --> S6
```

Versi EA naik 0.01 setiap spec selesai: 01 = `1.00`, 02 = `1.01`, … 06 = `1.05`, 07 = `1.06` (Fase 1 selesai). `2.00` setelah validasi Fase 6. MAJOR 0 tidak dipakai karena MetaEditor memberi warning 68 untuk versi `0.x` (temuan spike spec 01).

Urutan ini dipilih agar setiap spec bisa diuji penuh saat selesai: framework uji ada sebelum kode apa pun, event sink dan storage ada sebelum modul yang menulis log, dan harness ada sebelum modul yang butuh posisi sungguhan (risk, position).

Pelajaran dari bot Python yang memengaruhi spec ini: [python-bot-lessons.md](python-bot-lessons.md).

## Fase 2 — Notifikasi

Use case, pembagian spec, arsitektur bersama, dan strategi uji: [fase-2-overview.md](fase-2-overview.md).

| # | Spec | Isi | Butuh | Bukti selesai | Status |
|---|---|---|---|---|---|
| 8 | [ea-08-notifier-core](ea-08-notifier-core/) | `CNotifier` sebagai sink: aturan kirim, antrean prioritas, format pesan, event trade, status `alerts`, transport log di tester | 1–7 | suite NotifyRules ALL PASS, SC-10 PASS | **Done** 2026-10-01 (v1.07; MC-NT-01 manual tertunda; PC-13) |
| 9 | [ea-09-notifier-telegram](ea-09-notifier-telegram/) | Transport Telegram, rate limit bersama, push HP, heartbeat, laporan harian, start/stop, skrip `.local.set`, DoD Fase 2 | 8 | suite TelegramRules ALL PASS, SC-11 PASS, MC Telegram dicek | **Done** 2026-10-02 (Fase 2 selesai, v1.08; MC-TG-01..08 manual tertunda; PC-14) |

Versi EA: 08 = `1.07`, 09 = `1.08` (Fase 2 selesai 2026-10-02).

## Fase 3 — Strategi inti

Use case, pembagian spec, arsitektur bersama, strategi uji, dan keputusan terbuka: [fase-3-overview.md](fase-3-overview.md).

| # | Spec | Isi | Butuh | Bukti selesai | Status |
|---|---|---|---|---|---|
| 10 | [ea-10-market-structure](ea-10-market-structure/) | Cache bar per TF, swing Fractals berjeda, BOS, EMA, bias HTF, skor keselarasan tren | 1–9 | suite StructureRules ALL PASS, SC-12 PASS | **Done** 2026-10-02 (v1.09; MC-MS-01 manual tertunda; PC-15, PC-16) |
| 11 | [ea-11-zones](ea-11-zones/) | Zona S&D MTF, status Fresh/Tested/Invalid/Used/kedaluwarsa, rebuild saat init, skor kualitas zona | 10 | suite ZoneRules ALL PASS, SC-13 PASS | **Done** 2026-10-02 (v1.10; MC-ZN-01 manual tertunda; PC-17) |
| 12 | [ea-12-pa-trigger](ea-12-pa-trigger/) | Pola candle LTF terarah berurutan spesifik ke umum (netral bukan trigger), kekuatan pola, skor PA | 10 | suite PatternRules ALL PASS | **Done** 2026-10-03 (v1.11; MC-PA-01 manual tertunda; PC-18) |
| 13 | [ea-13-signal-entry](ea-13-signal-entry/) | Pipeline per bar LTF, gerbang, skor, telemetri sinyal, SL/TP dari zona, entry market/limit, EA membuka posisi, DoD Fase 3 | 10–12 | suite SignalRules ALL PASS, SC-14 PASS, backtest dasar 12 simbol | **Done** 2026-10-03 (Fase 3 selesai, v1.12; backtest dasar lolos 351 trade; MC-SG-01..02 manual tertunda; PC-19) |

Versi EA: 10 = `1.09`, 11 = `1.10`, 12 = `1.11`, 13 = `1.12` (Fase 3 selesai). Perbaikan bug sesudahnya: `1.13`, `1.14`.

## Fase 4 — Filter

Use case, pembagian spec, arsitektur, strategi uji, dan keputusan: [fase-4-overview.md](fase-4-overview.md) (Approved 2026-10-04, PC-21).

| # | Spec | Isi | Butuh | Bukti selesai | Status |
|---|---|---|---|---|---|
| 14 | [ea-14-session-spread](ea-14-session-spread/) | Lapisan Filters, filter sesi (UTC) dan spread per simbol, tahap tolak di pipeline | 13 | suite FilterRules ALL PASS, SC-15 PASS | **Done** 2026-10-04 (v1.15; backtest dasar berfilter lolos 241 trade; MC-FL-01 manual tertunda; PC-21, PC-22) |
| 15 | [ea-15-currency-exposure](ea-15-currency-exposure/) | Eksposur per mata uang dengan arah, `CURRENCY_EXPOSURE` di pre-trade check | 13 | suite ExposureRules ALL PASS, SC-16 PASS | **Done** 2026-10-05 (v1.16; MC-EXP-01 manual tertunda; PC-23) |
| 16 | [ea-16-news](ea-16-news/) | Kalender live + CSV tester (`ExportCalendar`), blackout per dampak, degrade aman + alert, DoD Fase 4 | 14 | suite NewsRules ALL PASS, SC-17 PASS, backtest dasar dengan filter | **Done** 2026-10-05 (v1.17; MC-NW-01..02 manual tertunda; PC-24) |

Versi EA: 14 = `1.15`, 15 = `1.16`, 16 = `1.17` (Fase 4 selesai). Perbaikan bug sesudahnya: `1.18` (`LOT_BELOW_MIN` palsu pada pair kuotasi non-USD).

## Fase 5 — Konfirmasi

Use case, pembagian spec, arsitektur, strategi uji, dan keputusan: [fase-5-overview.md](fase-5-overview.md) (Done 2026-10-08, PC-25, PC-27).

| # | Spec | Isi | Butuh | Bukti selesai | Status |
|---|---|---|---|---|---|
| 17 | [ea-17-validation-harness](ea-17-validation-harness/) | Backtest in-sample / out-of-sample real ticks, laporan PF, DD, expectancy, dan per nilai komponen | 16 | pytest laporan; acuan IS + OOS v1.19 | **Done** 2026-10-06 (v1.19; acuan sesi DB 901–924: IS 901–912, OOS 913–924; PC-25, PC-26) |
| 18 | [ea-18-fibonacci](ea-18-fibonacci/) | Skor Fibonacci level terdekat, mode bayangan | 17 | suite FibRules ALL PASS; laporan IS/OOS | **Done** 2026-10-06 (v1.20; trade identik dengan acuan; FIB SAMPEL KURANG; sesi 964–987) |
| 19 | [ea-19-trendline](ea-19-trendline/) | Skor trendline dengan kemiringan searah sinyal, mode bayangan | 17 | suite TrendlineRules ALL PASS; laporan IS/OOS | **Done** 2026-10-06 (v1.21; trade identik; TRENDLINE tidak lebih baik, SAMPEL KURANG; sesi 1027–1051) |
| 20 | [ea-20-breakout-retest](ea-20-breakout-retest/) | Skor breakout & retest, mode bayangan | 17 | suite BreakoutRules ALL PASS; laporan IS/OOS | **Done** 2026-10-07 (v1.22; trade identik; BREAKOUT +0,097R vs −0,014R IS, +0,356R vs −0,083R OOS, SAMPEL KURANG; sesi 1091–1114) |
| 21 | [ea-21-rsi-divergence](ea-21-rsi-divergence/) | Skor RSI divergence, mode bayangan | 17 | suite RsiRules ALL PASS; laporan IS/OOS | **Done** 2026-10-07 (v1.23; entry identik, lot bergeser 1 step karena swap; RSI jarang, IS lebih buruk, SAMPEL KURANG; sesi 1157–1180) |
| 22 | [ea-22-score-calibration](ea-22-score-calibration/) | Aktivasi komponen terbukti, ambang baru, DoD Fase 5 | 18–21 | backtest IS + OOS ≥ acuan v1.18 di OOS | **Done** 2026-10-08 (tanpa perubahan EA, tetap 1.24; breakout lolos aturan v2 tetapi aktivasi memperburuk IS/OOS/REAL; semua SHADOW; PC-27) |

Versi EA: 17 = `1.19`, 18 = `1.20`, 19 = `1.21`, 20 = `1.22`, 21 = `1.23`, perbaikan throttle log `1.24`; spec 22 tanpa perubahan EA (Fase 5 selesai di 1.24, 2026-10-08).

## Fase 5b — Perbaikan strategi inti

Use case, hipotesis, aturan uji, dan keputusan: [fase-5b-overview.md](fase-5b-overview.md) (Approved 2026-10-08, PC-28).

| # | Spec | Isi | Butuh | Bukti selesai | Status |
|---|---|---|---|---|---|
| 23 | [ea-23-fresh-zones](ea-23-fresh-zones/) | H1: entry hanya dari zona Fresh | 22 | IS/OOS/REAL vs acuan v1.24 | Requirements + design Approved, tasks Draft |
| 24 | ea-24-breakeven-tuning | H2: breakeven lebih awal (0,5 / 0,75 / 1,0R) | 23 | IS/OOS/REAL vs acuan sesudah 23 | Belum mulai |
| 25 | ea-25-session-window | H3: jendela entry dipersempit | 24 | IS/OOS/REAL vs acuan sesudah 24 | Belum mulai |

## Fase berikutnya

Spec detail (requirements, design, tasks) dibuat saat fase sebelumnya selesai. Catatan awal di bawah memastikan hal penting dari PRD dan dari bot Python tidak hilang, dan Fase 1 sudah menyiapkan tempatnya.

### Fase 2 — Notifikasi (spec `ea-08-notifier-core`, `ea-09-notifier-telegram`)

Isi PRD: `CNotifier` satu pintu, Telegram lewat `WebRequest` dari antrean di `OnTimer` (tidak pernah di tengah proses order), push HP (`SendNotification`) bila Telegram gagal 3x untuk Critical, heartbeat tiap 60 menit, HTML mode, kuota non-Critical 20/jam, pesan non-Critical > 30 menit dibuang, Critical tanpa limit, cooldown per tipe, token dan chat ID hanya di input.

**Keputusan 2026-09-29: pakai bot dan chat Telegram yang sama dengan bot Python** (PC-06).
- Kredensial: nilai `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID` dari `.env` bot Python diisi ke input EA `InpTelegramToken` / `InpTelegramChatID` lewat preset pribadi `*.local.set` (tidak pernah di-commit). Spec 08 menimbang skrip kecil yang membuat `*.local.set` dari `.env` agar tidak disalin tangan.
- Format mengikuti `NotificationManager` bot Python: emoji per level (INFO ℹ️, SUCCESS ✅, WARNING ⚠️, ERROR ❌, CRITICAL 🚨), HTML mode dengan escape, pesan start (🚀) dan stop (🛑), heartbeat tanpa bunyi (💓 balance + posisi terbuka + status), laporan harian (📈/📉 P&L, jumlah trade, win rate, balance akhir), satuan mata uang dari akun (USC).
- Pemetaan severity PRD ke level bot Python: Critical → CRITICAL 🚨, High → ERROR ❌, Medium → WARNING ⚠️, Info → INFO ℹ️; open/close profit, BE, partial → SUCCESS ✅ atau INFO.
- Karena satu chat menerima pesan dari dua bot, setiap pesan SDBot diawali penanda `SDBot` + pair + tipe akun + versi EA, supaya tidak tertukar dengan pesan bot Python.
- Satu token dipakai dua proses: batas kirim Telegram per bot (sekitar 20 pesan/menit ke satu chat grup, 1 pesan/detik per chat) dibagi berdua. Kuota non-Critical SDBot (PRD: 20/jam) tetap, dan HTTP 429 dipatuhi lewat `retry_after`.
- Terminal yang menjalankan SDBot wajib mengizinkan `https://api.telegram.org` di pengaturan WebRequest.

Disiapkan di Fase 1: tabel `alerts` dengan status `PENDING`/`SENT`/`FAILED`/`SKIPPED`, `attempts`, `sent_at` (spec 03); semua modul sudah mengirim `AlertEvent` lewat event sink (spec 02).

Edge case yang wajib masuk requirements:
- URL `https://api.telegram.org` belum diizinkan di MT5 (`WebRequest` error 4014): alert sekali lewat push HP + log CRITICAL, bukan diulang tiap detik.
- Token salah (HTTP 401) atau chat ID salah (400 "chat not found"): error permanen, jangan retry, beri tahu lewat push HP sekali.
- HTTP 429 dari Telegram: patuhi `retry_after` dari respons.
- Pesan > 4096 karakter: dipotong dengan penanda.
- Karakter `& < >` di pesan: di-escape (pelajaran bot Python).
- `WebRequest` blocking hingga timeout 3 detik: maksimal N pesan per siklus timer agar timer tidak tertahan.
- Empat instance di satu akun: heartbeat dan laporan harian cukup satu per akun (pemilihan instance via Global Variable), trade event tetap per instance.
- Strategy Tester: tidak ada `WebRequest`, pesan hanya dicetak ke log (PRD).
- Restart EA: pesan `PENDING` di DB yang lebih tua dari 30 menit ditandai `SKIPPED`, bukan dikirim terlambat.
- Mode ditandai di setiap pesan (akun cent/real, versi EA) agar pesan dari akun uji tidak tertukar.

### Fase 3 — Strategi inti (spec `ea-10`–`ea-13`: struktur, zona, trigger PA, sinyal + entry)

Isi PRD: bias HTF sebagai gerbang wajib, zona S&D dari Fractals berjeda di MTF (Fresh/Tested/Invalid/Used, maks 100 bar, satu zona satu entry), trigger PA di LTF, skor 100 poin, entry market (default) atau limit, TP ke zona lawan lalu cek R:R ≥ 2.

Pelajaran bot Python yang wajib jadi requirement: skor dan alasan tolak setiap kandidat tercatat (kalibrasi ambang 65 dari data, bukan asumsi); urutan detektor pola dari yang spesifik ke netral; setiap komponen skor punya uji yang membuktikan ia terpanggil di pipeline; `trades.signal_id` selalu terisi.

#### Katalog parameter strategi (draf, difinalkan di spec Fase 3 dan 5)

Aturan dari RULES dan pelajaran bot Python: tidak ada angka ajaib di kode. Setiap angka strategi menjadi **input** (bisa di-tuning dan dioptimasi di Strategy Tester) atau **konstanta** di `Core/Constants.mqh` (tetap sesuai PRD). Kolom "Bot Python" menunjuk padanan di `config/strategy_parameters.yaml` sebagai pembanding, bukan sebagai default.

| Area | Parameter | Default PRD | Bot Python | Usulan |
|---|---|---|---|---|
| Timeframe | HTF / MTF / LTF per gaya | day trading H4 / H1 / M15 | — | input `InpTradingStyle` (spec 02) |
| Bias HTF | Metode bias (struktur BOS + EMA) | EMA 50 searah + BOS | `ma.slow_period` 50, `structure.lookback` 50 | input periode EMA, lookback struktur |
| Zona S&D | Deteksi swing | Fractals dengan jeda bar | `zone_detection.*` (berbasis jam dan pip) | input jeda Fractals (bar) |
| Zona S&D | Usia maksimum zona | 100 bar MTF | `max_zone_age_hours` 72 | input `InpMaxZoneAgeBars` |
| Zona S&D | Status zona dan jumlah sentuhan | Fresh 0, Tested 1, ≥ 2 tidak dipakai | `min_touch_points` 2 (kebalikan PRD) | konstanta (aturan PRD) |
| Zona S&D | Ukuran zona minimum dan maksimum | tidak disebut | `min/max_zone_size_pips` 5 / 1000 | input dalam point; **perlu keputusan** |
| Entry | Mode entry | Market (opsi Limit) | — | input `InpEntryMode` |
| Entry | Buffer SL di luar zona | "batas jauh zona + buffer" | `zone_sl_buffer_multiplier` 1.2 | input (point atau × ATR); **perlu keputusan** |
| Entry | R:R minimum | 2.0 | `min_risk_reward_ratio` 2.0 | input `InpMinRR` |
| Entry | Jarak SL minimum dan maksimum | "SL ≥ stops level + spread" | `min/max_stop_loss_distance` per aset | input dalam point per pair (preset); **perlu keputusan** |
| Trigger PA | Pola dan urutan deteksi | engulfing kuat, pin bar, lainnya | 13 pola; bug urutan netral-dulu | konstanta daftar pola + urutan spesifik → netral (pelajaran bot Python) |
| Skor | Ambang skor minimum | 65 | quality_thresholds per aset | input `InpMinConfluenceScore` |
| Skor | Nilai maksimum per komponen | zona 30, Fibonacci 15, trendline 15, tren 15, breakout 10, PA 10, RSI 5 | `confluence_weights` (total 115%) | input per komponen dengan validasi total = 100, agar bisa dikalibrasi dari data (pelajaran: skor tidak prediktif) |
| Fibonacci | Level dan nilai | 0.5–0.618 = 15, 0.382/0.786 = 8 | `fibonacci.levels`, `tolerance` | konstanta level, input toleransi; skor turun sesuai jarak (bug bot Python) |
| Trendline | Sentuhan dan nilai | 3+ = 15, 2 = 7, searah | `trendline.min_touches` 3, `tolerance` | input minimal sentuhan dan toleransi; filter kemiringan wajib (bug bot Python) |
| RSI | Periode, divergence | divergence searah = 5 | `rsi.period` 14, 70/30 | input periode |
| Filter volatilitas | Candle klimaks | tidak disebut | `climax_multiplier` 2.0–2.5 × ATR | kandidat Fase 4/5; **perlu keputusan** |

"Perlu keputusan" berarti PRD belum menentukan angkanya. Nilainya diputuskan bersama Anda di requirements spec Fase 3, lalu dicatat di `docs/PENDING-CHANGES.md`.

### Fase 4 — Filter (spec `ea-14`..`ea-16`, lihat [fase-4-overview.md](fase-4-overview.md))

Isi PRD: filter berita memakai kalender bawaan MT5 (`CalendarValueHistory`) ±30 menit berita high impact; di Strategy Tester memakai CSV kalender historis di Common/Files (dibuat script `ExportCalendar`); filter sesi London + New York; filter spread per simbol; eksposur maks 2 posisi searah per mata uang.

Pelajaran dari spec news bot Python yang wajib masuk:
- Blackout per tingkat dampak (high ±30 menit, medium ±10 menit, low tidak diblokir), dapat diatur lewat input.
- Pemetaan mata uang ke pair: EURUSD → EUR, USD; EURJPY → EUR, JPY; event salah satu mata uang memblokir pair itu.
- **Degrade aman tetapi terlihat**: jika kalender tidak bisa dibaca (terminal belum sinkron, CSV tidak ada di tester), entry tidak diblokir **dan** alert "proteksi berita OFF" dikirim sekali, bukan diam-diam.
- Waktu event dikonversi dengan benar: kalender MT5 memakai waktu server; CSV tester harus memakai zona waktu yang sama dengan data tester.
- **Tanpa lookahead**: di backtest hanya event dengan waktu ≤ waktu bar yang boleh dipakai, dan nilai `actual` baru ada setelah rilis.
- Telemetri: sinyal yang ditolak dicatat `NEWS_BLACKOUT` dengan nama event dan menit ke/dari rilis; trade yang lolos menyimpan event terdekat.
- Eksposur mata uang dihitung **dengan arah** (BUY EURUSD = long EUR + short USD, SELL kebalikannya), dengan test case pair JPY (bug bot Python).
- Modifier kepercayaan dari hasil rilis (surprise) di luar lingkup sampai blackout terbukti (sama dengan urutan bot Python).

### Fase 5–7 dan backoffice

Fase 5 konfirmasi (Fibonacci, trendline, breakout-retest, RSI, satu per satu dengan pelajaran bug di `python-bot-lessons.md`), Fase 6 validasi (forward test + akun cent 1–3 bulan), backoffice B1–B6 mengikuti PRD Backoffice. Spec dibuat saat gilirannya.

## Status gate

`Draft` → `Approved (tanggal)` per dokumen. `tasks.md` baru dibuat setelah requirements dan design spec itu disetujui. Spec dianggap `Done` setelah semua task dicentang dan bukti selesai di tabel terpenuhi.
