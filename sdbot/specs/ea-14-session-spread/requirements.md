# Requirements — 14 Filter sesi dan spread

Status: Done (2026-10-04)
Use case: UC-40, UC-41, UC-46 ([overview](../fase-4-overview.md))
Asal: PRD-EA §Pipeline analisis (pre-filter: sesi, spread), §Parameter input EA (`TradingSessions`, `MaxSpreadPoints`); PC-21 (sesi UTC, spread dari data live); PC-19 (urutan tahap kandidat); bot Python `utils/market_session.py` (batas sesi UTC) dan `config/active_symbols.yaml` (`max_spread_pips`)
Butuh: spec 13

## Pendahuluan

Spec ini menambahkan dua pre-filter PRD pertama di depan entry Fase 3, di lapisan baru `Filters/`:
- **sesi trading:** kandidat hanya dinilai lanjut bila bar-nya di sesi yang diizinkan, dalam UTC;
- **spread:** kandidat ditolak bila spread saat itu melebihi batas per simbol.

Penolakan tercatat di `signals` dengan alasan, sesi, dan spread, sehingga efeknya terukur di backtest dasar. Filter berita (spec 16) dan eksposur mata uang (spec 15) di luar lingkup.

Selesai jika:
- suite FilterRules ALL PASS;
- SC-15 membuktikan kandidat di luar sesi dan kandidat dengan spread lebar ditolak dengan alasan yang benar, tanpa order;
- backtest dasar 12 simbol dengan filter memenuhi kriteria Requirement 5;
- regresi tetap PASS;
- EA naik ke `1.15`.

## Ukuran (dasar default)

**Sesi** (backtest dasar Fase 3, 351 trade, waktu bar M15 UTC): lihat [overview §2](../fase-4-overview.md#2-ukuran-dari-backtest-dasar-fase-3-tanpa-filter). Jam 22:00–24:00 −0,33R per trade; overlap London–NY +0,11R; London + New York (08:00–22:00) menyisakan sekitar 245 trade dengan expectancy sekitar +0,06R.

**Spread live** (tick 7 hari s.d. 2026-10-03, akun cent, point):

| Simbol | p50 | p99 | Maks | Bot Python (pip → point) | Usulan default (3 × p50) |
|---|---|---|---|---|---|
| EURUSDc | 8 | 23 | 131 | 30 | 24 |
| GBPUSDc | 10 | 40 | 271 | 40 | 30 |
| USDJPYc | 10 | 26 | 350 | 30 | 30 |
| USDCHFc | 13 | 27 | 300 | 40 | 39 |
| AUDUSDc | 9 | 41 | 232 | 40 | 27 |
| USDCADc | 16 | 45 | 159 | 40 | 48 |
| NZDUSDc | 14 | 72 | 108 | 40 | 42 |
| EURJPYc | 16 | 62 | 240 | 50 | 48 |
| GBPJPYc | 22 | 170 | 304 | 60 | 66 |
| XAUUSDc | 240 | 260 | 680 | 500 | 720 |
| XAGUSDc | 30 | 30 | 44 | 100 | 90 |
| BTCUSDc | 1000 | 1000 | 1000 | 1000 | 3000 |

Spread normal per simbol hampir tetap (p50 = p90); yang perlu disaring adalah lonjakan sesaat (sampai 10–30 × p50). Batas 3 × p50 memblokir lonjakan tanpa memblokir spread normal, termasuk untuk BTC, yang spread normalnya sudah sama dengan batas bot Python.

## Glosarium

- **Sesi (UTC, batas bot Python):** Tokyo 00:00–08:00, London 08:00–17:00, New York 13:00–22:00. Overlap 13:00–17:00 termasuk London dan New York. Jam 22:00–24:00 (rollover) tidak termasuk sesi mana pun.
- **Waktu UTC bar:** waktu buka bar LTF kandidat dikurangi selisih server–UTC.
- **Selisih server–UTC:** live = `TimeTradeServer() − TimeGMT()` dibulatkan 15 menit (`RoundUtcOffset`, Fase 1); tester = input `InpTesterUtcOffsetHours` (default 0), karena di tester `TimeGMT()` sama dengan waktu server.
- **Spread kandidat:** ask − bid saat kandidat dinilai, dalam point (sama dengan yang dipakai SL SELL).

## Requirements

### Requirement 1: Filter sesi

**User story:** Sebagai trader, saya ingin EA hanya entry di sesi likuid yang saya pilih, agar rollover dan sesi sepi tidak menghasilkan entry.

#### Acceptance criteria

1.1. EA WAJIB menyediakan input `InpSessionTokyo` (default false), `InpSessionLondon` (true), `InpSessionNewYork` (true).
1.2. JIKA waktu UTC bar kandidat tidak berada di salah satu sesi yang aktif (batas awal inklusif, batas akhir eksklusif) MAKA kandidat WAJIB ditolak `OUTSIDE_SESSION`, dengan nama sesi UTC bar (`TOKYO`, `LONDON`, `OVERLAP`, `NEWYORK`, `OFF`) di detail.
1.3. JIKA ketiga input sesi false MAKA filter sesi WAJIB mati (semua jam diizinkan, termasuk 22:00–24:00), dan EA mencatat INFO sekali saat init.
1.4. Selisih server–UTC WAJIB dihitung ulang setiap penilaian di live, sehingga pergantian DST broker tidak menggeser batas sesi UTC.

### Requirement 2: Filter spread

**User story:** Sebagai trader, saya ingin entry ditahan saat spread melonjak, agar biaya masuk tidak memakan sebagian besar R.

#### Acceptance criteria

2.1. EA WAJIB menyediakan input `InpMaxSpreadPoints` (0 = filter mati; 0–100000) dengan nilai per simbol di preset (tabel usulan default).
2.2. JIKA spread kandidat lebih besar dari `InpMaxSpreadPoints` (dan input > 0) MAKA kandidat WAJIB ditolak `SPREAD_TOO_WIDE`, dengan spread dan batasnya di detail.
2.3. Spread tepat sama dengan batas WAJIB lolos.

### Requirement 3: Posisi di pipeline dan telemetri

3.1. Untuk kandidat, urutan tahap WAJIB: STOPPED → pause harian → tidak bisa trading → `OUTSIDE_SESSION` → `SPREAD_TOO_WIDE` → `POSITION_OPEN` → trigger PA → skor → SL/TP → lot dan pre-trade → eksekusi. Spec 16 menyisipkan `NEWS_BLACKOUT` sebelum `OUTSIDE_SESSION`.
3.2. `context_json` setiap kandidat WAJIB memuat `session` (nama sesi UTC bar) dan `max_spread` (batas, 0 = mati), selain kolom `spread_points` yang sudah ada.
3.3. Filter sesi dan spread WAJIB hanya memengaruhi entry baru; manajemen posisi (BE, partial, trailing, close all) tetap berjalan di semua jam.

### Requirement 4: Input, preset, dokumen

4.1. Input baru WAJIB divalidasi, masuk `inputs_json`, tabel input README, dan 12 preset (spread per simbol sesuai tabel; sesi London + New York untuk semua simbol).
4.2. `InpTesterUtcOffsetHours` (−12..14, default 0) WAJIB hanya dipakai di Strategy Tester.

### Requirement 5: Uji, backtest dasar, versi

5.1. Suite FilterRules WAJIB menguji fungsi murni:
- nama sesi per jam UTC, termasuk batas 08:00, 13:00, 17:00, 22:00, 00:00;
- kombinasi input sesi, termasuk semua false;
- konversi waktu server ke UTC dengan selisih +3 jam dan −5 jam;
- spread di bawah, sama dengan, dan di atas batas, serta batas 0.
5.2. SC-15 WAJIB menjalankan pipeline di tester (EURUSDc beberapa bulan) dalam dua konfigurasi:
- hanya Tokyo aktif: tidak ada trade di luar 00:00–08:00 UTC, dan ada kandidat `OUTSIDE_SESSION`;
- `InpMaxSpreadPoints` di bawah spread normal: tidak ada trade, kandidat setelah pre-filter risiko dan sesi ditolak `SPREAD_TOO_WIDE`.
5.3. Backtest dasar 12 simbol dengan filter WAJIB berjalan tanpa log ERROR/CRITICAL, semua trade punya `signal_id` dan skor lengkap, total ≥ 200 trade dan setiap simbol ≥ 10 trade (keputusan 4). Laporan WAJIB menunjukkan perubahan trade dan expectancy dibanding backtest dasar Fase 3.
5.4. EA dan harness WAJIB naik ke `1.15`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Bar tepat 22:00 UTC (London + NY aktif) | `OUTSIDE_SESSION` (akhir eksklusif) | 1.2 |
| EC-02 | Bar 13:00–17:00 UTC dengan hanya New York aktif | Lolos (overlap termasuk NY) | 1.2 |
| EC-03 | Broker berganti DST, selisih server–UTC berubah 1 jam | Batas sesi tetap dalam UTC | 1.4 |
| EC-04 | Broker GMT+2/+3 di tester | Hasil benar bila `InpTesterUtcOffsetHours` diisi; default 0 cocok untuk Exness | 4.2 |
| EC-05 | Lonjakan spread tepat di bar kandidat (berita, rollover) | `SPREAD_TOO_WIDE`, kandidat bar berikutnya dinilai normal | 2.2 |
| EC-06 | Preset lama tanpa `InpMaxSpreadPoints` | Default 0 = mati, WARN sekali saat init | 2.1 |
| EC-07 | Posisi terbuka melewati 22:00 UTC | BE/partial/trailing tetap berjalan | 3.3 |
| EC-08 | Semua input sesi false | Filter mati, 24 jam diizinkan | 1.3 |
| EC-09 | Kandidat STOPPED sekaligus di luar sesi | `STOPPED` (urutan) | 3.1 |

## Keputusan yang perlu disetujui

1. **Tiga input bool sesi** (Tokyo, London, New York), bukan satu input teks, dengan batas UTC tetap dari bot Python. 22:00–24:00 hanya terbuka bila filter dimatikan. Alternatif: input jam mulai/akhir bebas (lebih fleksibel, lebih mudah salah isi).
2. **Default spread = 3 × median spread live** per simbol (tabel), bukan nilai bot Python. Alasannya: nilai bot Python sama dengan spread normal untuk BTC (memblokir lonjakan sekecil apa pun) dan terlalu longgar untuk XAG. Alternatif: memakai nilai bot Python apa adanya.
3. **Selisih UTC di tester dari input** (default 0, cocok untuk server Exness GMT+0), karena tester tidak memberi waktu GMT yang benar.
4. **Kriteria backtest dasar Fase 4: total ≥ 200 trade dan ≥ 10 per simbol**, menggantikan ≥ 300 / ≥ 15 dari PC-19. Filter sesi London + New York saja diperkirakan menyisakan sekitar 245 trade per tahun. Alternatif: tetap ≥ 300 dengan menambah Tokyo ke default.

## Pertanyaan terbuka

- Tidak ada selain keputusan di atas.
