# Requirements — 13 Sinyal dan entry

Status: Done (2026-10-03)
Use case: UC-35, UC-36, UC-37, UC-38, UC-39 ([overview](../fase-3-overview.md))
Asal: PRD-EA §Pipeline analisis (tiga gerbang wajib, alur), §Skor konfluensi, §Eksekusi order, §Data dan database (`signals`, `signal_scores`, `trades.signal_id`), §Roadmap Fase 3; python-bot-lessons §1 (skor tidak prediktif → semua kandidat tercatat dengan skor per komponen; komponen wajib terbukti terpanggil), §2 (`entry_tags` kosong → `signal_id` wajib); PC-15 (ambang dinormalkan, TP cadangan 2R, parameter relatif ATR, kriteria backtest dasar); spec 10–12
Butuh: spec 10, 11, 12

## Pendahuluan

Spec ini menyambungkan analisis Fase 3 menjadi pipeline sinyal dan membuat EA **membuka posisi sendiri untuk pertama kali**. Pipeline berjalan setiap bar LTF (M15) tertutup dan menilai tiga gerbang wajib PRD: bias HTF, zona valid searah, dan trigger PA. Setelah itu skor konfluensi dari komponen yang ada (zona, tren, PA), lalu entry, SL, dan TP dari zona, R:R, lot, dan pre-trade check Fase 1. Order dikirim lewat `CExecutor` dengan `signal_id`. Setiap kandidat, lolos maupun ditolak, tercatat di `signals` + `signal_scores` dengan alasan. Spec ini juga menyediakan backtest dasar 12 simbol dan query kalibrasi.

Di luar lingkup: filter berita, sesi, spread, dan eksposur mata uang (Fase 4); komponen Fibonacci, trendline, breakout, RSI (Fase 5); tuning ambang (Fase 5–6); mode entry limit (keputusan 5).

Selesai jika:
- suite SignalRules ALL PASS;
- SC-14 membuktikan alur sinyal → posisi → closure dengan `signal_id` dan skor lengkap;
- backtest dasar 12 simbol memenuhi kriteria Requirement 8;
- regresi tetap PASS;
- EA naik ke `1.12` (Fase 3 selesai).

## Ukuran dari histori (dasar default)

Simulasi kasar pipeline di Python untuk 12 simbol, 2025-10-01 s.d. 2026-10-01. Aturannya sama dengan spec 10–12: bias H4, zona H1, pola M15, satu posisi per simbol, satu entry per zona. SL = batas jauh zona ± buffer × ATR(14) H1. TP = batas dekat zona lawan terdekat, atau 2R bila tidak ada. Simulasi tanpa BE/partial/trailing, tanpa spread, entry di close bar. Angka ini dasar untuk default, bukan hasil backtest.

| Ukuran per simbol per tahun | Rentang 12 simbol |
|---|---|
| Bar M15 dengan bias HTF | 67–80% |
| Bar M15 menyentuh zona valid searah bias (kandidat) | 980–1.560 (4–6 per hari) |
| Kandidat dengan pola PA terarah | 236–351 (sekitar 22%) |
| Skor ≥ 36 (65% dari 55) | 28–60 |
| Trade (lolos R:R ≥ 2, satu posisi, satu entry per zona), gerbang skor 36 | 19–37, total 312 |
| Trade tanpa gerbang skor | 68–105 |
| Jarak SL p10 / p50 / p90 (× ATR H1, buffer 0,1) | 0,45–0,95 / 1,0–1,6 / 1,6–3,9 |
| Kandidat yang punya zona lawan di depan harga | 70–84% |
| Kandidat dengan R:R ke zona lawan ≥ 2 | 44–72% |

Pengamatan:
- **Gerbang skor 36 menyisakan sekitar seperenam kandidat PA**, sehingga trade per simbol rata-rata 26 per tahun. Kriteria PC-15 "≥ 30 trade per simbol" hanya tercapai di 3 dari 12 simbol, sedangkan totalnya 312 ≥ 300 (keputusan 3).
- Dalam simulasi kasar ini, expectancy rata-rata 12 simbol dengan gerbang skor sekitar 0,0R, tanpa gerbang sekitar −0,16R. Sampelnya kecil dan simulasi tidak memakai manajemen posisi, jadi angka ini bukan dasar keputusan profit. Angka ini hanya alasan untuk tidak mematikan gerbang skor.
- Buffer SL 0,1 dan 0,2 ATR memberi hasil yang tidak berbeda konsisten. Dipilih 0,1, yang lebih dekat ke batas zona.

## Glosarium

- **Kandidat**: bar LTF tertutup yang menyentuh zona valid (Fresh/Tested, tidak Used) searah bias HTF. Hanya kandidat yang dicatat sebagai baris `signals`. Bar tanpa bias atau tanpa zona hanya dihitung (Requirement 6.4).
- **Menyentuh zona**: rentang bar (low–high) beririsan dengan zona (`TouchedZone` spec 11).
- **Skor aktif**: jumlah komponen yang sudah ada di Fase 3: zona (maks 30), keselarasan tren (maks 15), dan kekuatan PA (maks 10), total maksimum 55.
- **Persen skor**: skor ÷ maksimum aktif × 100, yang dibandingkan dengan `InpMinConfluenceScore` (PC-15).
- **ATR MTF**: ATR(14) Wilder H1 di bar H1 tertutup terakhir.
- **R**: jarak entry ke SL awal.

## Requirements

### Requirement 1: Pipeline per bar LTF

**User story:** Sebagai trader, saya ingin sinyal hanya dinilai sekali per bar LTF tertutup, dengan urutan pemeriksaan sesuai PRD, agar entry tidak lahir dari candle yang belum selesai.

#### Acceptance criteria

1.1. KETIKA bar LTF baru tutup dan akun PASSED serta status bersama siap MAKA EA WAJIB menilai bar itu tepat sekali, setelah analisis struktur, zona, dan pola untuk bar itu diperbarui.
1.2. EA WAJIB memakai hasil HTF dan MTF dari bar tertutup terakhir masing-masing pada saat bar LTF itu tutup, tanpa bar berjalan.
1.3. JIKA bar LTF tertutup terakhir sudah lebih tua dari 2 × durasi LTF saat dinilai (tick pertama setelah akhir pekan, terminal baru tersambung) MAKA EA WAJIB tidak menilainya dan mencatat log DEBUG.
1.4. Bar yang sudah dinilai WAJIB tidak dinilai ulang setelah restart di dalam bar yang sama (penanda bar terakhir di Global Variable per magic).
1.5. JIKA analisis HTF, MTF, atau LTF belum siap (histori kurang) MAKA EA WAJIB tidak membuat kandidat, dan mencatat WARN throttled.

### Requirement 2: Kandidat dan gerbang

**User story:** Sebagai trader, saya ingin sinyal hanya lahir bila tiga gerbang wajib lolos, dan skor hanya menilai kualitas.

#### Acceptance criteria

2.1. Bar WAJIB menjadi kandidat hanya bila bias HTF bullish/bearish dan bar menyentuh zona valid searah bias. Arah kandidat = arah bias, dan zona yang dipakai = pilihan `TouchedZone` (Fresh dulu, lalu terbaru).
2.2. Untuk kandidat, EA WAJIB memeriksa urutan berikut dan mencatat tahap pertama yang gagal sebagai `reject_stage`:
   1. pre-filter risiko: STOPPED, pause harian, tidak bisa trading (`STOPPED`, `DAILY_PAUSE`, `NOT_TRADABLE`);
   2. posisi instance masih terbuka (`POSITION_OPEN`, keputusan 4);
   3. trigger PA searah (`NO_PA_TRIGGER`);
   4. skor (`SCORE_TOO_LOW`);
   5. SL/TP dan R:R (Requirement 4);
   6. lot dan pre-trade check Fase 1;
   7. eksekusi.
2.3. Gerbang skor WAJIB lolos bila persen skor ≥ `InpMinConfluenceScore` (default 65, PC-15), sehingga default berarti skor ≥ 36 dari 55.
2.4. Skor WAJIB tidak bisa menggantikan gerbang: kandidat tanpa trigger PA ditolak walau skor zona dan tren penuh.

### Requirement 3: Skor konfluensi

**User story:** Sebagai developer, saya ingin skor per komponen tercatat untuk setiap kandidat, agar ambang dan bobot bisa dikalibrasi dari data.

#### Acceptance criteria

3.1. Skor kandidat WAJIB terdiri dari:
   - zona: `ZoneScore`, Fresh 30, Tested 15;
   - keselarasan tren: `TrendScore` MTF searah sinyal, 15/7/0;
   - kekuatan PA: `PaScore` pola searah, 10/7/3/0.
3.2. Setiap kandidat yang sampai di tahap trigger PA atau sesudahnya WAJIB punya tiga baris `signal_scores` (`ZONE`, `TREND`, `PA`) dengan skor dan maksimum, termasuk komponen bernilai 0. Kandidat yang ditolak sebelum tahap itu WAJIB tetap mencatat skor zona dan tren yang sudah diketahui.
3.3. `signals.score_total` WAJIB berisi jumlah skor mentah. Maksimum aktif dan persen skor WAJIB dicatat di konteks sinyal.

### Requirement 4: Entry, SL, TP, R:R

**User story:** Sebagai trader, saya ingin SL dan TP selalu dari zona, dan entry ditolak bila imbalannya tidak sepadan.

#### Acceptance criteria

4.1. Entry WAJIB market order: ask untuk BUY, bid untuk SELL, dibaca saat penilaian (keputusan 5).
4.2. SL WAJIB = batas jauh zona − `InpSlBufferAtr` (default 0,1) × ATR MTF untuk BUY. Untuk SELL: batas jauh + buffer + spread saat itu, karena SL SELL dipicu ask.
4.3. TP WAJIB = batas dekat zona lawan valid terdekat di depan entry (`OppositeZone` spec 11). JIKA tidak ada zona lawan MAKA TP = entry ± `InpMinRR` × R, dan sumber TP dicatat (`ZONE` / `RR`) (PC-15).
4.4. JIKA R:R = jarak TP ÷ R kurang dari `InpMinRR` (default 2,0) MAKA kandidat WAJIB ditolak `RR_TOO_LOW`.
4.5. JIKA R kurang dari max(stops level + spread, `InpMinSlAtr` (default 0,3) × ATR MTF) MAKA kandidat WAJIB ditolak `SL_TOO_CLOSE`. JIKA R lebih dari `InpMaxSlAtr` (default 3,0) × ATR MTF MAKA kandidat WAJIB ditolak `SL_TOO_FAR`.
4.6. JIKA entry sudah melewati SL (harga menembus batas jauh di dalam bar H1 berjalan) MAKA kandidat WAJIB ditolak `INVALID_STOPS`.
4.7. Lot WAJIB dihitung `CRiskManager` dari entry dan SL ini. Pre-trade check Fase 1 (risiko per trade, total risiko terbuka, batas posisi per kategori, margin) WAJIB lolos sebelum order. Penolakan memakai kode Fase 1.

### Requirement 5: Eksekusi dan zona Used

**User story:** Sebagai trader, saya ingin setiap posisi bisa ditelusuri ke sinyalnya, dan satu zona hanya menghasilkan satu entry.

#### Acceptance criteria

5.1. KETIKA kandidat lolos semua tahap MAKA EA WAJIB mengirim order lewat `CExecutor.OpenMarket` dengan SL, TP, volume, dan `signal_id` baris `signals` kandidat itu.
5.2. KETIKA order terisi MAKA EA WAJIB menandai zona Used (spec 11), dan `trades.signal_id` WAJIB terisi. Baris `signals` berstatus `ACCEPTED`.
5.3. JIKA order ditolak broker atau gagal setelah retry MAKA baris `signals` WAJIB berstatus `REJECTED` dengan tahap dari `CExecutor`, dan zona WAJIB tidak menjadi Used.
5.4. Satu instance WAJIB punya paling banyak satu posisi terbuka di simbolnya (keputusan 4).
5.5. Saat optimasi (tanpa DB) pipeline WAJIB tetap berjalan sama. Hanya pencatatan yang dilewati, dan `signal_id` kosong.

### Requirement 6: Telemetri sinyal

**User story:** Sebagai developer, saya ingin setiap kandidat dan alasan tolaknya tercatat, agar gerbang yang paling sering memblokir terukur.

#### Acceptance criteria

6.1. Setiap kandidat WAJIB menghasilkan tepat satu baris `signals` dengan:
   - waktu bar, arah, gaya, `zone_ref` (ID zona), spread (point), status, `reject_stage`, dan `reject_detail`;
   - `context_json` berisi: kode pola PA, status zona, alasan bias HTF, entry/SL/TP, sumber TP, R:R, ATR MTF, persen skor, dan maksimum aktif.
6.2. Kode komponen skor (`ZONE`, `TREND`, `PA`, dan cadangan Fase 5 `FIB`, `TRENDLINE`, `BREAKOUT`, `RSI`) dan tahap tolak baru (`POSITION_OPEN`, `SL_TOO_FAR`) WAJIB masuk `enums.md`.
6.3. Uji WAJIB membuktikan setiap komponen skor terpanggil di pipeline (pelajaran bot Python: layer breakout tidak pernah dipanggil).
6.4. Bar LTF yang dinilai tetapi bukan kandidat WAJIB dihitung per hari server menurut sebabnya (tanpa bias, tanpa zona). Ringkasannya dicatat di log INFO sekali per hari dan saat EA berhenti, tanpa baris `signals`.

### Requirement 7: EA utama membuka posisi

**User story:** Sebagai trader, saya ingin EA yang dipasang dengan preset mulai trading sendiri setelah Fase 3, dengan pengaman Fase 1 tetap berlaku.

#### Acceptance criteria

7.1. EA utama WAJIB menjalankan pipeline dan membuka posisi, dengan syarat validasi input dan akun Fase 1 tetap berlaku (termasuk `InpAllowLiveTrading` untuk akun real/cent).
7.2. Input baru `InpMinConfluenceScore` (65; 0–100), `InpMinRR` (2,0; 1,0–10,0), `InpSlBufferAtr` (0,1; 0–1,0), `InpMinSlAtr` (0,3; 0,05–2,0), `InpMaxSlAtr` (3,0; 0,5–10,0, > min) WAJIB divalidasi, masuk `inputs_json`, tabel input README, dan preset 12 simbol.
7.3. Harness uji WAJIB bisa menjalankan pipeline yang sama (bukan entry terjadwal) untuk skenario sinyal.

### Requirement 8: Backtest dasar dan kalibrasi

**User story:** Sebagai developer, saya ingin backtest dasar 12 simbol dan query kalibrasi, agar Fase 3 bisa dinyatakan selesai dan Fase 5 punya data.

#### Acceptance criteria

8.1. Alat uji WAJIB bisa menjalankan backtest dasar 12 simbol × 12 bulan terakhir dengan preset masing-masing dalam satu perintah, ke `sdbot_tester.sqlite`.
8.2. Backtest dasar WAJIB lolos bila:
   - tidak ada log CRITICAL/ERROR dari pipeline;
   - total trade ≥ 300 dan setiap simbol ≥ 15 trade (keputusan 3);
   - semua trade punya `signal_id` dan baris `signals` ACCEPTED dengan tiga komponen skor.
   Profit tidak menjadi syarat (PC-15).
8.3. Query kalibrasi WAJIB tersedia di `tools/queries/`:
   - distribusi `reject_stage` per simbol;
   - persen skor (bucket) vs R hasil;
   - pola PA vs R hasil;
   - zona Fresh vs Tested vs R hasil;
   - sumber TP (`ZONE`/`RR`) vs R hasil;
   - kandidat per hari per simbol.

### Requirement 9: Uji dan versi

9.1. Suite SignalRules WAJIB menguji fungsi murni: kandidat, urutan tahap, skor dan persen, SL/TP/R:R, batas SL, dan isi konteks. Setiap kasus dihitung tangan, termasuk JPY (3 digit) dan XAU.
9.2. SC-14 WAJIB menjalankan pipeline di tester (EURUSDc beberapa bulan) dan memeriksa:
   - minimal satu posisi terbuka dari sinyal;
   - setiap trade punya `signal_id` → baris `signals` ACCEPTED → tiga baris `signal_scores`;
   - closure lengkap;
   - zona Used tidak menghasilkan entry kedua;
   - tidak ada dua baris `signals` untuk bar yang sama.
9.3. EA dan harness WAJIB naik ke `1.12`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Restart EA di dalam bar M15 yang sudah dinilai | Bar tidak dinilai ulang, tanpa baris atau order kedua | 1.4 |
| EC-02 | Tick pertama Senin setelah akhir pekan (bar terakhir Jumat) | Bar basi tidak dinilai | 1.3 |
| EC-03 | Bias HTF berubah tepat saat bar H4 tutup bersamaan dengan bar M15 | Pakai bar H4 yang baru tutup (bar tertutup terakhir) | 1.2 |
| EC-04 | Bar menyentuh zona demand dan supply sekaligus (bar lebar) | Hanya zona searah bias yang dipakai | 2.1 |
| EC-05 | Zona sudah disentuh bar M15 tetapi status H1-nya baru berubah di bar H1 berikutnya | Status dari bar H1 tertutup terakhir; zona tetap valid sampai H1 tutup | 1.2 |
| EC-06 | Posisi instance masih terbuka saat zona lain disentuh | Ditolak `POSITION_OPEN`, tercatat | 2.2, 5.4 |
| EC-07 | Harga menembus batas jauh zona di dalam jam berjalan (entry di bawah SL BUY) | `INVALID_STOPS` | 4.6 |
| EC-08 | Tidak ada zona lawan valid | TP 2R, sumber `RR` | 4.3 |
| EC-09 | Zona lawan sangat dekat (entry hampir di zona lawan) | `RR_TOO_LOW` | 4.4 |
| EC-10 | Spread melebar saat kandidat (SL SELL ikut melebar) | SL dihitung dengan spread saat itu; jarak SL tetap dicek | 4.2, 4.5 |
| EC-11 | Lot hitungan di bawah lot minimum akun cent | `LOT_BELOW_MIN`, zona tidak Used | 4.7, 5.3 |
| EC-12 | Retcode ambigu (timeout) saat order | Alur Fase 1 mencari ID permintaan; bila ternyata terisi, sinyal ACCEPTED dan zona Used, tanpa order kedua | 5.2 |
| EC-13 | Optimasi di tester | Pipeline sama, tanpa baris DB | 5.5 |
| EC-14 | Emergency stop atau pause harian aktif saat kandidat | `STOPPED` / `DAILY_PAUSE`, tetap tercatat | 2.2 |
| EC-15 | USDJPYc (3 digit) dan XAUUSDc | Semua jarak relatif ATR dan point, hasil sama bentuknya | 9.1 |
| EC-16 | Posisi ditutup manual | Zona tetap Used, closure `MANUAL` dengan `signal_id` di trade | 5.2 |
| EC-17 | Disconnect saat kandidat | `NOT_TRADABLE` | 2.2 |
| EC-18 | DB terkunci atau gagal tulis baris `signals` | Order tetap boleh dikirim dengan `signal_id` kosong, log ERROR (Storage tidak menghentikan trading) | 5.1 |

## Keputusan yang perlu disetujui

1. **Satu baris per kandidat** (bar yang menyentuh zona valid searah bias), sekitar 4–6 baris per hari per simbol. Bar tanpa bias atau tanpa zona hanya dihitung di ringkasan log harian. Alternatif: satu baris per bar M15 (96/hari/simbol), yang lebih lengkap untuk frekuensi gerbang tetapi tabel jauh lebih besar.
2. **Urutan tahap untuk kandidat**: pre-filter risiko, posisi terbuka, PA, skor, SL/TP/R:R, lot dan pre-trade, eksekusi. Pre-filter tetap pertama sesuai PRD, tetapi hanya tercatat untuk kandidat.
3. **Gerbang skor 65% dari 55 dipertahankan**, dan kriteria backtest dasar PC-15 diubah dari "≥ 30 trade per simbol" menjadi "**total ≥ 300 trade dan setiap simbol ≥ 15 trade**". Dengan gerbang ini, simulasi memberi 19–37 trade per simbol dan total 312. Alternatif: turunkan ambang ke sekitar 55% (≥ 30 dari 55; simulasi 26–39 trade per simbol), atau matikan gerbang skor di Fase 3 (68–105 trade, tetapi expectancy kasar lebih buruk). Perubahan ini masuk PENDING-CHANGES sebagai koreksi PC-15.
4. **Maksimal satu posisi per instance** (seperti aturan bot Python "max 1 trade per symbol"), dengan tahap tolak baru `POSITION_OPEN`. Alternatif: tanpa batas per simbol, hanya batas kategori Fase 1.
5. **Hanya market order di Fase 3.** Input `InpEntryMode` (limit di batas dekat zona) ditunda ke Fase 5. Limit butuh pengelolaan order tertunda (kedaluwarsa, batal saat zona invalid, rekonsiliasi), sementara data Fase 3 belum menunjukkan manfaatnya. Alternatif: bangun limit sekarang (menambah sekitar satu spec).
6. **Parameter SL baru sebagai input relatif ATR MTF**: buffer 0,1, minimal 0,3, maksimal 3,0 (dari simulasi: p10 jarak SL sekitar 0,45, p90 sampai 3,9 untuk USDJPY). SL SELL ditambah spread. Tahap tolak baru `SL_TOO_FAR`.
7. **Skor mentah di `score_total`**, persen dan maksimum aktif di konteks, agar tetap bisa dibandingkan setelah komponen Fase 5 aktif.
8. **Penanda bar terakhir yang dinilai di Global Variable per magic**, agar restart di dalam bar tidak membuat kandidat atau order ganda.
9. **Backtest dasar lewat runner yang sama** (`run-ea-tests.ps1 -Baseline`) dengan 12 file `.ini` yang memakai preset per simbol, ditambah laporan ringkas per simbol dari DB tester.

## Pertanyaan terbuka

- Tidak ada selain keputusan di atas.
