# Requirements — 10 Market structure dan bias HTF

Status: Done (2026-10-02)
Use case: UC-31 ([overview](../fase-3-overview.md))
Asal: PRD-EA §Pipeline analisis (timeframe per gaya, alur, gerbang bias HTF), §Skor konfluensi (keselarasan tren: struktur + MA, 15), §Temuan review (HTF gerbang wajib, cache per bar baru, struktur dan MA digabung); RULES §Analysis (hanya baca harga dan indikator), aturan bar tertutup dan tanpa repaint; katalog parameter README (bias HTF); PC-15
Butuh: spec 01–09

## Pendahuluan

Spec ini membangun fondasi analisis: salinan bar tertutup per timeframe yang dihitung ulang hanya saat bar baru, swing dari Fractals berjeda, break of structure (BOS), EMA, bias HTF (gerbang wajib pertama), dan komponen skor keselarasan tren. Belum ada zona, pola candle, sinyal, atau order; EA utama belum memakai hasilnya untuk trading (spec 13).

Selesai jika suite StructureRules ALL PASS, skenario SC-12 membuktikan hasil analisis selama run sama dengan hasil yang dihitung ulang dari histori (tanpa repaint), regresi SC-00..SC-11 tetap PASS, dan EA naik ke `1.09`.

## Glosarium

- **HTF / MTF / LTF**: timeframe bias / zona dan struktur / trigger, dari input gaya trading (day trading = H4 / H1 / M15).
- **Bar tertutup**: bar dengan shift ≥ 1; bar berjalan (shift 0) tidak pernah dipakai.
- **Swing high (fractal)**: bar yang high-nya lebih tinggi dari high `N` bar di kiri dan `N` bar di kanan (`N` = kekuatan swing). Swing baru diketahui setelah `N` bar di kanannya tutup (jeda `N` bar). Swing low kebalikannya.
- **BOS bullish**: close bar tertutup di atas swing high terkonfirmasi terakhir; **BOS bearish**: close di bawah swing low terkonfirmasi terakhir.
- **Arah struktur**: arah BOS terakhir dalam jendela lookback; netral bila belum ada BOS.
- **Arah EMA**: bullish bila close bar tertutup terakhir di atas EMA dan EMA naik dibanding `k` bar sebelumnya; bearish kebalikannya; selain itu netral.
- **Bias HTF**: bullish atau bearish bila arah struktur dan arah EMA di HTF sama; selain itu netral.
- **Keselarasan tren**: arah struktur dan arah EMA di MTF dibanding arah sinyal.

## Requirements

### Requirement 1: Salinan bar per timeframe

**User story:** Sebagai trader, saya ingin analisis memakai bar yang sudah tutup dan dihitung ulang sekali per bar, agar hasilnya stabil dan hemat CPU.

#### Acceptance criteria

1.1. EA WAJIB menyalin bar tertutup HTF, MTF, dan LTF sejumlah yang dibutuhkan analisis (lookback + pemanasan EMA), tanpa bar berjalan.
1.2. KETIKA bar baru muncul di sebuah timeframe MAKA EA WAJIB menyalin ulang dan menghitung ulang analisis timeframe itu saja, sekali per bar.
1.3. JIKA salinan bar gagal atau jumlahnya kurang dari kebutuhan minimum (histori belum diunduh, simbol baru, awal backtest) MAKA EA WAJIB menandai analisis timeframe itu "data kurang", mencatat WARN sekali per timeframe, dan mencoba lagi di tick berikutnya.
1.4. Timeframe analisis WAJIB dari input gaya trading, tidak bergantung pada timeframe chart.

### Requirement 2: Swing terkonfirmasi

**User story:** Sebagai trader, saya ingin swing yang tidak berubah setelah muncul, agar backtest sama dengan live.

#### Acceptance criteria

2.1. EA WAJIB mendeteksi swing high dan swing low dari bar tertutup dengan kekuatan `InpSwingStrength` (default 2, 1–5); swing baru diakui setelah `InpSwingStrength` bar di kanannya tutup.
2.2. JIKA dua bar di jendela fractal punya high (atau low) sama persis MAKA EA WAJIB mengakui hanya bar yang lebih awal sebagai swing, agar hasil deterministik.
2.3. Swing yang sudah diakui WAJIB tidak pernah berubah atau hilang oleh bar berikutnya (tanpa repaint).

### Requirement 3: Break of structure dan arah struktur

**User story:** Sebagai trader, saya ingin arah struktur diukur dari tembusan swing yang jelas, bukan dari bentuk harga yang ditafsirkan bebas.

#### Acceptance criteria

3.1. EA WAJIB mendeteksi BOS dari close bar tertutup terhadap swing terkonfirmasi terakhir sebelum bar itu, dalam jendela `InpStructureLookback` bar (default 100, 20–500).
3.2. Arah struktur WAJIB sama dengan arah BOS terakhir dalam jendela; netral bila jendela tidak berisi BOS.
3.3. EA WAJIB menyimpan level dan waktu BOS terakhir serta swing high/low terakhir, untuk konteks sinyal dan zona (spec 11, 13).

### Requirement 4: EMA dan arahnya

**User story:** Sebagai trader, saya ingin filter tren EMA 50 sesuai PRD.

#### Acceptance criteria

4.1. EA WAJIB menghitung EMA close dengan periode `InpEmaPeriod` (default 50, 10–400) dari bar tertutup dengan pemanasan minimal 3 × periode bar.
4.2. Arah EMA WAJIB bullish bila close bar tertutup terakhir > EMA dan EMA naik dibanding `InpEmaSlopeBars` bar sebelumnya (default 3, 1–20); bearish kebalikannya; selain itu netral.
4.3. Hasil EMA WAJIB sama untuk histori yang sama, apa pun urutan pemanggilan (deterministik).

### Requirement 5: Bias HTF

**User story:** Sebagai trader, saya ingin hanya trading searah tren besar, sesuai gerbang wajib PRD.

#### Acceptance criteria

5.1. Bias HTF WAJIB bullish bila arah struktur HTF dan arah EMA HTF sama-sama bullish, bearish bila sama-sama bearish, dan netral selain itu.
5.2. JIKA data HTF kurang (1.3) MAKA bias WAJIB netral dengan alasan "data kurang".
5.3. KETIKA bias berubah MAKA EA WAJIB mencatat log INFO berisi bias lama dan baru, arah struktur, arah EMA, dan level BOS.
5.4. Bias WAJIB tersedia untuk pipeline sinyal (spec 13) beserta alasannya (struktur, EMA, data kurang), agar penolakan `NO_HTF_BIAS` bisa dirinci.

### Requirement 6: Komponen skor keselarasan tren

**User story:** Sebagai developer, saya ingin komponen tren diberi nilai sesuai PRD dan terbukti terpakai.

#### Acceptance criteria

6.1. Skor keselarasan tren WAJIB 15 bila arah struktur MTF dan arah EMA MTF keduanya searah arah sinyal, 7 bila salah satu, 0 bila tidak ada (PRD §Skor).
6.2. Skor WAJIB dihitung sebagai fungsi murni dari arah sinyal dan analisis MTF, dan diuji dengan kasus dari setiap cabang.

### Requirement 7: Tanpa repaint dan uji

7.1. Hasil analisis untuk sebuah bar WAJIB hanya bergantung pada bar yang tutup sebelum atau pada bar itu.
7.2. Skenario SC-12 WAJIB membuktikan di Strategy Tester (EURUSDc dan XAUUSDc, beberapa bulan) bahwa bias HTF dan analisis MTF yang dihitung bar demi bar selama run sama persis dengan hasil yang dihitung ulang dari histori pada akhir run, termasuk setelah restart harness di tengah run.
7.3. EA dan harness WAJIB naik ke `1.09`; input baru masuk `Inputs.mqh`, JSON sesi, preset, dan README.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Terminal baru start, histori H4 belum lengkap | Data kurang, WARN sekali, dicoba lagi tiap tick; bias netral | 1.3, 5.2 |
| EC-02 | Awal backtest dengan histori sedikit | Sama dengan EC-01 sampai bar cukup | 1.3 |
| EC-03 | Gap akhir pekan (forex) atau bar hilang | Swing dan BOS memakai urutan bar apa adanya; tidak ada bar sintetis | 2.1, 3.1 |
| EC-04 | BTCUSDc diperdagangkan akhir pekan | Bar akhir pekan ikut dihitung seperti biasa | 1.2 |
| EC-05 | Dua high sama persis di jendela fractal | Hanya bar yang lebih awal diakui | 2.2 |
| EC-06 | Swing di N bar terakhir (kanannya belum lengkap) | Belum diakui | 2.1 |
| EC-07 | Close tepat sama dengan level swing | Bukan BOS (harus melewati) | 3.1 |
| EC-08 | BOS bullish lalu bearish di jendela yang sama | Arah = BOS terakhir (bearish) | 3.2 |
| EC-09 | Harga di atas EMA tetapi EMA turun | Arah EMA netral | 4.2 |
| EC-10 | Chart diganti timeframe / EA di-init ulang | Analisis dihitung ulang dari histori; hasil sama dengan sebelum | 1.4, 7.1 |
| EC-11 | Tick pertama bar baru datang terlambat (pasar sepi) | Hitung ulang tetap sekali untuk bar itu | 1.2 |
| EC-12 | Optimasi | Analisis berjalan sama, tanpa log DB | 1.2 |
| EC-13 | XAUUSDc (digit 2–3) dan USDJPYc (3 digit) | Perbandingan harga memakai nilai mentah, tidak dibulatkan ke pip | 2.1, 3.1 |

## Keputusan yang perlu disetujui

1. **Swing dari fungsi sendiri di atas `MqlRates`**, bukan indikator `iFractals`: hasil sama dengan definisi Bill Williams, tetapi bisa diuji dengan data tetap dan kekuatannya bisa diatur. Alternatif: `iFractals` (kekuatan tetap 2).
2. **EMA dari fungsi sendiri** dengan pemanasan 3 × periode, bukan handle `iMA`: deterministik terhadap jumlah bar yang disalin dan bisa diuji. Selisih terhadap `iMA` di luar pemanasan diabaikan (konvergen). Alternatif: handle `iMA` dibuat di `OnInit` (PRD mengizinkan).
3. **Arah EMA = posisi close terhadap EMA + kemiringan EMA** (`InpEmaSlopeBars`), agar harga yang baru melintas EMA datar tidak langsung dianggap tren.
4. **Keselarasan tren dinilai di MTF**, karena bias HTF sudah mensyaratkan struktur dan EMA HTF searah (kalau dinilai di HTF skornya selalu 15).
5. **Input baru**: `InpSwingStrength` (2), `InpStructureLookback` (100 bar), `InpEmaPeriod` (50), `InpEmaSlopeBars` (3). Default dari PRD dan katalog README (bot Python: lookback struktur 50 dengan kekuatan swing setara; saya pilih 100 karena di H4 50 bar hanya ~8 hari).
6. **Satu kekuatan swing untuk HTF dan MTF**; dipisah nanti bila data menunjukkan perlu.

## Pertanyaan terbuka

- Tidak ada selain keputusan di atas.
