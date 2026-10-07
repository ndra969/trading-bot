# Changelog SDBot

Format: satu bagian per rilis EA dan backoffice (RULES §Git). Versi EA `MAJOR.MINOR`: MAJOR = memengaruhi posisi terbuka atau skema DB lintas fase; Fase 1 memakai `1.00`–`1.06`, `2.00` setelah validasi Fase 6 (PC-03).

## EA

### Fase 5 selesai — 2026-10-08 — spec 22 aktivasi komponen (tanpa perubahan EA, tetap 1.24)

- `component_report.py --rule v2` (default): kelompok > 0 vs 0 per periode IS / OOS / REAL; TERBUKTI bila lebih baik di IS (≥ 50 trade) dan OOS (≥ 10) dan tidak lebih buruk di real ticks. `--sessions` menerima beberapa rentang. `run-ea-tests.ps1 -SetInput 'Kunci=nilai',...` untuk backtest dasar. Uji TS-76..80.
- Data real ticks (REAL 2026-01..10, sesi 1260–1271): strategi dasar 167 trade, −0,045R per trade, PF 0,91.
- Keputusan aktivasi (aturan v2): hanya breakout & retest TERBUKTI (IS +0,097R vs −0,014R; OOS +0,356R vs −0,082R; REAL +0,151R vs −0,152R). Fibonacci dan trendline TIDAK, RSI sampel kurang.
- Sapuan ambang IS dengan breakout ACTIVE: 55% 610 trade +0,002R; **60%** 506 +0,001R (terpilih, aturan terkunci); 65% 431 −0,011R; 70% 317 +0,030R (jumlah trade kurang).
- Validasi akhir breakout ACTIVE + ambang 60%: IS +0,001R PF 1,01; OOS −0,016R PF 0,97 (< acuan 1,07); REAL −0,148R PF 0,74 (acuan 0,91). **Gagal**: aktivasi mengubah komposisi trade sehingga keunggulan breakout di mode bayangan tidak terbawa. Semua komponen tetap SHADOW, ambang tetap 65%; default EA dan preset tidak berubah. Keputusan PC-27.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-08): build 0 error / 0 warning (5 target); unit 661/661; 30 skenario PASS (SC-00..SC-21); durasi 21 menit 53 detik. pytest `sdbot/tools` 111/111, `schema.py check` OK (data versi 4).

### 1.24 — 2026-10-07 — perbaikan: spam log di Strategy Tester

- Bug: `LogThrottled` memakai `TimeLocal()`, yang di Strategy Tester mengikuti waktu simulasi. Pesan "sekali per menit" tercetak sekali per menit simulasi: backtest IS + OOS v1.23 menulis 676 ribu WARN "histori kurang ... analisis ditunda" selama pemanasan histori H4.
- Perbaikan: jam throttle `SdbThrottleNow()` = waktu nyata monoton (`GetTickCount64`). Berlaku untuk semua pemanggil `LogThrottled`; di live perilaku sama.
- Bukti: run EURUSDc 2024-04..2024-06 OHLC M1: WARN 42.151 → 4, baris jurnal 48.820 → 6.673. Uji TC-CU-17.
- `periods.ini`: catatan bahwa IS efektif mulai 2024-05-01..05-13 untuk sebagian besar simbol (pemanasan H4 sejak histori 2024-03-26; BTC dan XAU sejak April).

Regresi (`run-ea-tests.ps1 -All`, 2026-10-07): build 0 error / 0 warning; unit 661/661; 30 skenario PASS (SC-00..SC-21); durasi 30 menit 41 detik (dijalankan bersamaan dengan pengecekan lain).

### 1.23 — 2026-10-07 — spec 21 skor RSI divergence bayangan (Fase 5)

- `Strategies/RsiRules.mqh` (fungsi murni): divergence reguler di dua swing sinyal terakhir H1 (BUY lower low harga + higher low RSI, SELL cerminannya), selisih RSI ≥ 2, swing kedua ≤ 20 bar dari kandidat = 5. RSI **hanya skor**, tidak pernah tahap tolak; bot Python memakai RSI sebagai gerbang (6.773 penolakan vs 6 kontribusi).
- Handle `iRSI(MTF, 14)` milik `CSdbApp` (pola ATR trailing): dibuat bila sinyal aktif dan `InpScoreRsiMode` bukan OFF, dilepas di `OnDeinit`; gagal = WARN dan skor RSI 0, EA tetap jalan. `RsiCopyAligned` menyalin RSI berdasarkan waktu bar cache zona (wajib tepat n nilai); data tidak sejajar = skor 0 dengan WARN paling sering sekali sehari.
- Input `InpScoreRsiMode` (OFF / SHADOW / ACTIVE, default SHADOW); konteks `rsi_age`, `rsi_diff`, `rsi_pdiff`; `signal_scores` RSI (maks 5); maksimum 100 bila keempat komponen aktif (PRD).
- Uji: TC-RSI-01..11 (TC-RSI-11 memakai handle nyata di tester), TC-SG-22e, 24e, 33, 34 (RSI tidak mengubah tahap tolak), SC-21.

Backtest IS + OOS (sesi 1157–1180, 1 jam 13 menit): waktu entry, arah, SL/TP, dan harga close identik dengan v1.22. Tarif swap server berubah lagi, sehingga saldo bergeser beberapa sen dan sebagian lot berbeda satu step (misalnya 53,94 → 53,95); profit total berbeda sen. Laporan RSI bayangan:

| Periode | RSI 0 | RSI 5 |
|---|---|---|
| IS | 477 trade, +0,039R | 16 trade, −0,274R |
| OOS | 50 trade, −0,015R | 2 trade, +1,314R |

Divergence jarang (ACCEPTED bernilai 5 = 3,3%, kandidat 3,9%). Status PC-25 `SAMPEL KURANG`; di IS justru lebih buruk.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-07): build 0 error / 0 warning (5 target); unit 660/660; 30 skenario PASS (SC-00..SC-21); durasi 19 menit 58 detik. pytest `sdbot/tools` 106/106, `schema.py check` OK (data versi 4).

### 1.22 — 2026-10-07 — spec 20 skor breakout & retest bayangan (Fase 5)

- `Strategies/BreakoutRules.mqh` (fungsi murni): level = swing fractal H1 sisi sinyal (BUY swing high, SELL swing low) dalam 100 bar; breakout = close pertama sesudah bar konfirmasi swing yang menembus level searah ≥ 0,1 ATR (wick saja tidak dihitung); breakout gagal (close kembali melewati level > 0,2 ATR) membuang level; level di zona ± 0,2 ATR = 10; breakout terbaru dipilih. Bot Python punya layer breakout yang tidak pernah dipanggil; di sini keterhubungannya dibuktikan TC-SG-32 (ACTIVE mengubah `SCORE_TOO_LOW` menjadi lolos) dan SC-20 (nilai 10 dan 0 muncul di pipeline).
- `Strategies/StrategyMath.mqh`: `DistToZone` dipakai bersama trendline dan breakout.
- Input `InpScoreBreakoutMode` (OFF / SHADOW / ACTIVE, default SHADOW); konteks `bo_age`, `bo_dist`, `bo_level`; `signal_scores` BREAKOUT (maks 10); maksimum 95 bila Fibonacci, trendline, dan breakout aktif.
- Uji: TC-BO-01..11, TC-SG-22d, 24d, 31, 32, SC-20.

Backtest IS + OOS (sesi 1091–1114, 1 jam 1 menit): trade dan profit kotor **identik** dengan v1.21. Laporan BREAKOUT bayangan:

| Periode | BO 0 | BO 10 |
|---|---|---|
| IS | 304 trade, −0,014R | 189 trade, **+0,097R** |
| OOS | 38 trade, −0,083R | 14 trade, **+0,356R** |

Komponen pertama Fase 5 yang membedakan hasil searah di IS dan OOS. Status PC-25 `SAMPEL KURANG` karena OOS bernilai 10 baru 14 trade (syarat 20). ACCEPTED bernilai 10 = 37,2% (dalam batas Req 5.3).

Regresi (`run-ea-tests.ps1 -All`, 2026-10-07): build 0 error / 0 warning (5 target); unit 645/645; 29 skenario PASS (SC-00..SC-20); durasi 19 menit 13 detik. pytest `sdbot/tools` 105/105, `schema.py check` OK (data versi 4).

### 1.21 — 2026-10-06 — spec 19 skor trendline bayangan (Fase 5)

- `Strategies/TrendlineRules.mqh` (fungsi murni): garis dari pasangan swing fractal H1 terkonfirmasi dalam 100 bar, **hanya searah sinyal** (BUY support naik, SELL resistance turun, kemiringan ≥ 0,02 ATR per bar). Bot Python tanpa filter kemiringan ikut menghitung support turun untuk BUY. Garis patah (close menembus > 0,2 ATR sejak sentuhan pertama) dibuang; proyeksi di bar kandidat wajib di zona ± 0,2 ATR; sentuhan = semua swing sesisi di garis; 3+ sentuhan 15, 2 sentuhan 7.
- `Strategies/Confirmations.mqh` (`CConfirmations`): komponen konfirmasi Fase 5 dalam satu kelas, satu salinan bar H1 untuk semua komponen. Fibonacci dipindah dari engine tanpa perubahan perilaku (distribusi FIB identik). `ActiveConfirmations` menjumlahkan komponen ACTIVE ke skor dan maksimum (55 / 70 / 85).
- Input `InpScoreTrendlineMode` (OFF / SHADOW / ACTIVE, default SHADOW); konteks `tl_dist`, `tl_slope`, `tl_touches`; `signal_scores` TRENDLINE.
- Uji: TC-TL-01..11 (termasuk support turun untuk BUY = 0), TC-SG-22c, 24c, 30, SC-19.

Backtest IS + OOS (sesi 1027–1051, 1 jam 35 menit, sebelumnya 1 jam 10 menit): trade dan profit kotor **identik** dengan v1.20. Laporan TRENDLINE bayangan:

| Periode | TL 0 | TL 7 | TL 15 |
|---|---|---|---|
| IS | 199 trade, +0,045R | 119, +0,020R | 175, +0,016R |
| OOS | 22, +0,476R | 12, −0,326R | 18, −0,261R |

Garis searah ditemukan pada 59% kandidat ACCEPTED (35% bernilai 15), dalam batas Req 4.3, tetapi trade dengan trendline **tidak lebih baik** di IS dan lebih buruk di OOS. Status PC-25: `SAMPEL KURANG`; arah data tidak mendukung aktivasi.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-06): build 0 error / 0 warning (5 target); unit 630/630; 28 skenario PASS (SC-00..SC-19); durasi 18 menit 13 detik. pytest `sdbot/tools` 104/104, `schema.py check` OK (data versi 4).

### 1.20 — 2026-10-06 — spec 18 skor Fibonacci bayangan (Fase 5)

- `Strategies/FibRules.mqh` (fungsi murni): leg = impuls penuh yang memuat zona (ekstrem `StructureLookback` bar H1 sebelum candle swing zona sampai ekstrem sesudahnya, hanya bar tertutup); rasio retracement batas dekat zona; level **terdekat** dari 0.382 / 0.5 / 0.618 / 0.786 (tie ke level lebih dalam), nilai dasar 8 / 15 / 15 / 8, dikurangi linear sampai jarak 0,05; leg < 1,5 ATR atau rasio di luar 0,236–1,0 = 0. Bot Python memilih level dengan skor tertinggi sehingga 0.618 penuh di ~83% setup; di sini skor penuh hanya 0,6% dari ACCEPTED.
- Rencana awal (leg dari batas jauh zona sendiri) hanya mengukur lebar zona: di SC-18 rasio selalu 0,60–0,93. Diganti impuls penuh atas persetujuan user.
- Input `InpScoreFibMode` (OFF / SHADOW / ACTIVE, default SHADOW); enum `ENUM_SDB_COMPONENT_MODE` untuk komponen Fase 5 berikutnya. SHADOW mencatat `signal_scores` FIB dengan `active = 0` dan konteks `fib_level`, `fib_ratio`, tanpa mengubah skor gerbang; ACTIVE menaikkan maksimum ke 70.
- Runner: bug run "selesai" 1 detik tanpa backtest saat terminal uji dari run sebelumnya belum tertutup (Start-Process hanya meneruskan /config ke instance itu). Kini runner menunggu terminal uji mati sebelum setiap run (maks 120 detik, lalu ENV) dan menandai backtest GAGAL bila tidak ada sesi DB baru.
- Uji: TC-FIB-01..13, TC-SG-22b, 24b, 28, 29, SC-18, TS-72.

Backtest IS + OOS (sesi 964–987): trade **identik** dengan acuan v1.19 di semua simbol (IS 493, PF 1,06; OOS 52, PF 1,07); satu-satunya selisih adalah swap XAU (−21,69 vs −21,91 USC, tarif swap server berubah). Laporan FIB bayangan: IS FIB 0 = 392 trade +0,032R, FIB > 0 = 101 trade sekitar +0,015R; OOS FIB 0 = 37 trade −0,152R, FIB > 0 = 15 trade sekitar +0,57R. Status aktivasi PC-25: `SAMPEL KURANG` (nilai 15 hanya 3 trade). Usulan untuk spec 22: membandingkan FIB > 0 vs 0, bukan nilai tertinggi vs 0.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-06): build 0 error / 0 warning (5 target); unit 616/616; 27 skenario PASS (SC-00..SC-18); durasi 16 menit 35 detik. pytest `sdbot/tools` 103/103, `schema.py check` OK (data versi 4).

### 1.19 — 2026-10-06 — spec 17 alat ukur in-sample / out-of-sample (Fase 5)

- Skema data v4: `signal_scores.active` (1 = ikut skor gerbang, 0 = komponen bayangan Fase 5), default 1; Logger mengisinya. Strategi tidak berubah dari 1.18. Keputusan PC-26.
- `ea/tests/baseline/periods.ini`: IS 2024-04-01..2026-07-01 dan OOS 2026-07-01..2026-10-01 dengan OHLC M1, REAL 2026-01-05..2026-10-01 dengan real ticks. Diukur dengan `-ProbeHistory`: bar M1 tester ada sejak 2024-03-26, tetapi real ticks server cent hanya sejak 2026-01-05 (XAUUSDc sejak 2026-08-14). Sebelum itu tester diam-diam memakai tick buatan. Keputusan PC-25 opsi A.
- `run-ea-tests.ps1`: `-Period IS|OOS|ALL|REAL`, `-FromDate/-ToDate/-Model`, `-ProbeHistory`; pesan tester tentang tick buatan dan histori kosong dikumpulkan per simbol dan ditandai di laporan. Durasi total kini hh:mm:ss.
- `baseline_report.py`: tabel per periode, profit factor (uang) dan drawdown maks (% balance tertutup, R untuk total), pembanding per (periode, simbol), status kriteria PRD tahap 2–3 sebagai informasi; kriteria jumlah trade hanya untuk periode panjang (bukan OOS/REAL); kelengkapan skor hanya untuk komponen aktif.
- `component_report.py` (baru): hasil trade per nilai komponen, IS vs OOS, status aktivasi PC-25 (`TERBUKTI` / `TIDAK` / `SAMPEL KURANG`); `--candidates` untuk distribusi nilai per tahap tolak. `tick_history.py` (baru): parser jurnal probe histori.
- Uji: TS-60..71 (+ TS-65b), TC-DB-01e, TC-SG-24 (active).

Acuan Fase 5 (12 simbol, OHLC M1, sesi DB 901–924):

| Periode | Trade | Win | R/trade | R total | PF | DD maks simbol | DD total |
|---|---|---|---|---|---|---|---|
| IS 2024-04..2026-06 | 493 | 50% | +0,029 | +14,12 | 1,06 | 6,9% | 17,0R |
| OOS 2026-07..2026-10 | 52 | 50% | +0,036 | +1,85 | 1,07 | 1,5% | 8,1R |

Kriteria PRD tahap 2 (PF ≥ 1,3) belum terpenuhi; DD aman. Laporan komponen: ZONE Fresh +0,041R vs Tested +0,001R di IS; tren MTF 0 di IS sekitar impas (+0,001R, 50 trade), jadi angka +0,396R di v1.18 adalah sampel kecil. OOS 3 bulan hanya 52 trade, sehingga hampir semua kelompok nilai "sampel kecil" dan status aktivasi `SAMPEL KURANG`.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-06): build 0 error / 0 warning (5 target); unit 599/599; 26 skenario PASS (SC-00..SC-17b); durasi 15 menit 19 detik. pytest `sdbot/tools` 102/102, `schema.py check` OK (data versi 4).

### 1.18 — 2026-10-05 — perbaikan: LOT_BELOW_MIN palsu pada pair kuotasi non-USD

- Bug: di akun cent, uang/lot dari `OrderCalcProfit` 1 lot (sekitar $0,3–2) dibulatkan ke sen, galat sampai 0,26%. Untuk lot puluhan, rugi lot akhir bisa di atas batas risiko lebih dari 5 step (`SDB_LOT_FIT_STEPS`), lalu kandidat ditolak `LOT_BELOW_MIN` "lot minimum melebihi risiko" padahal lot minimum jauh di bawah risiko. Terjadi di USDCAD, USDCHF, USDJPY, EURJPY, GBPJPY: 38 kandidat di backtest dasar v1.17.
- Perbaikan: `CalcVolume` menurunkan lot proporsional (lot × batas ÷ rugi) sebelum turun per step.
- Uji: TC-RK-19 (USDCHFc/USDCADc/USDJPYc, 1.728 permintaan: sebelum perbaikan 214 tolak palsu).
- Runner: skenario tanpa input berita sendiri dijalankan dengan `InpNewsFilter=false`, agar hasil tidak bergantung pada `sdbot_calendar.csv` di Common\Files.

Backtest dasar (semua filter Fase 4): **LOLOS**, `LOT_BELOW_MIN` 38 → 0, trade 215 → 248 (11 → 18 USDCHF, 16 → 30 USDCAD, 11 → 16 EURJPY, 16 → 21 GBPJPY, 16 → 18 USDJPY). Total R +12,55 → +3,86 (+0,058R → +0,016R per trade): trade yang sebelumnya tertolak salah justru bersih rugi, jadi angka v1.17 terlalu optimis karena bug ini, bukan karena strategi.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-05): build 0 error / 0 warning (5 target); unit 598/598; 26 skenario PASS (SC-00..SC-17b); durasi 14 menit 57 detik.

### 1.17 — 2026-10-05 — spec 16 filter berita, Fase 4 selesai

- `Filters/NewsRules.mqh` (fungsi murni): event kalender, baris CSV `epoch,ccy,impact,id,nama`, relevansi mata uang simbol (XAU/XAG/BTC lewat USD), jendela inklusif per dampak, pilihan event saat tumpang tindih (dampak tertinggi lalu terdekat), event terdekat. Hanya jadwal event, tanpa nilai actual.
- `Filters/NewsFilter.mqh` (`CNewsFilter`): live dari kalender MT5 (−1..+2 hari, muat ulang tiap 15 menit, 60 detik setelah gagal); tester dari `Common\Files\<InpNewsCsvFile>`. Kalender tak terbaca = status OFF, entry tidak diblokir berita, satu alert High `NEWS_FILTER_OFF` per sesi.
- Pipeline: tahap `NEWS_BLACKOUT` sesudah pre-filter risiko, sebelum sesi dan spread; detail `nama CCY DAMPAK menit`. Konteks sinyal mendapat `news` (ON/OFF/DISABLED) dan `news_next`.
- Input `InpNewsFilter` (true), `InpNewsHighMinutes` (15), `InpNewsMediumMinutes` (0), `InpNewsCsvFile` (`sdbot_calendar.csv`). PRD semula ±30 menit; dengan ±30/±10 backtest dasar hanya 187 trade (< 200) dan trade yang terblokir bersih +1,24R karena kalender MT5 menandai HIGH juga untuk rilis kecil. Keputusan PC-24.
- Alat: script `Scripts/SDBot/ExportCalendar.mq5` dan `run-ea-tests.ps1 -ExportCalendar` (18.787 event 2025-01..2026-10); runner menyalin fixture `ea/tests/fixtures/common/` ke Common\Files sebelum skenario. Enum `alert_type` + `NEWS_FILTER_OFF` (data skema tetap v3).
- Uji: TC-NW-01..11, TC-SG-27, TS-57..59, SC-17 (kalender fixture, jendela 30/10 eksplisit) dan SC-17b (CSV tidak ada: tetap trading, satu alert).

Backtest dasar dengan semua filter Fase 4 (12 simbol, 2025.10.01–2026.10.01, OHLC M1): **LOLOS**, 215 trade (11–31 per simbol), tanpa log ERROR/CRITICAL. Dibanding v1.15: trade 241 → 215, expectancy +0,035R → +0,058R, total R +8,42 → +12,55.

Regresi (`run-ea-tests.ps1 -All`, 2026-10-05): build 0 error / 0 warning (5 target, termasuk `ExportCalendar`); unit 597/597; 26 skenario PASS (SC-00..SC-17b); durasi 14 menit 54 detik. pytest `sdbot/tools` 88/88, `schema.py check` OK (data versi 3).

### 1.16 — 2026-10-05 — spec 15 eksposur mata uang (Fase 4)

- `Risk/ExposureRules.mqh` (fungsi murni): kaki mata uang berarah per posisi (BUY = dasar long + kuotasi short; XAU, XAG, BTC mata uang sendiri), hitungan posisi searah, penilaian batas. Long dan short dihitung terpisah, sehingga bug bot Python yang mengabaikan arah SELL tidak terulang.
- Pre-trade check: langkah `CURRENCY_EXPOSURE` (kosong sejak Fase 1) kini aktif, setelah batas kategori dan sebelum margin. Dihitung atas semua posisi SDBot di akun; posisi manual tidak dihitung. Detail tolak misalnya `USD short 2/2`.
- Input `InpMaxSameDirectionPerCurrency` (2; 0 = mati), preset diperbarui. Keputusan PC-23.
- Replay 241 trade backtest berfilter v1.15: batas 2 memblokir 8 trade (5 rugi, 3 untung, bersih −0,85R); expectancy +0,035R → +0,040R.
- Uji: TC-EXP-01..07, TC-RK-16..18 (posisi nyata di GBPUSDc/AUDUSDc, urutan vs batas kategori, posisi manual), SC-16 (harness `HarnessExposureSetup`: BUY EURUSD ditolak sepanjang run, SELL tetap dibuka).

Regresi (`run-ea-tests.ps1 -All`, 2026-10-05): build 0 error / 0 warning (4 target); unit 585/585; 24 skenario PASS (SC-00..SC-16); durasi 13 menit. pytest `sdbot/tools` 85/85, `schema.py check` OK (data versi 3).

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
