# Requirements — Lab setup trendline H1 + PA M15

Status: Done (2026-10-13)
Use case: UC-82, UC-83 ([fase-5c-overview.md](../fase-5c-overview.md))
Asal: permintaan user 2026-10-09 (setup trendline + price action, timeframe H1, tiga bentuk) dan 2026-10-13 (lebih banyak trade); PRD-EA §Struktur dan bias HTF, §Trigger PA, §Position management; `TrendlineRules.mqh` (spec 19), `PatternRules.mqh` (spec 12); simulator spec 31
Butuh: spec 31 (simulator terkalibrasi, bar M1 terekspor). Acuan = EA 1.31 (DAY, zona lawan wajib)

## Pendahuluan

Spec ini membangun alat riset `tools/trendline_lab.py` untuk mengukur tiga setup trendline yang diingat user sebagai setup yang berhasil:
- **(A) Pantulan trendline:** harga menyentuh trendline H1 searah tren lalu muncul pola PA M15. Tidak butuh zona S&D.
- **(B) Trendline + zona S&D:** sudah terukur di spec 31 dari kandidat EA. Dilaporkan ulang dari data itu, tanpa simulasi baru.
- **(C) Break + retest:** trendline ditembus, lalu harga kembali menyentuhnya dari sisi lain dengan pola PA searah tembusan.

Tujuannya dua:
- tahu apakah setup ini punya keunggulan;
- tahu apakah setup ini bisa menambah frekuensi trade tanpa merusak hasil, sesudah gaya intraday (spec 34) dan simbol tambahan (spec 35) ditolak.

Lab tidak mengubah EA. Setup yang lolos menjadi spec EA tersendiri.

Di luar lingkup:
- filter berita (lab tidak memakai kalender; dampaknya diperkirakan kecil dan dicatat);
- real ticks: periode REAL disimulasikan dengan bar M1 (simulator terkalibrasi, REAL sedikit optimis +0,036R);
- penyetelan parameter trendline atau PA.

Bukti selesai:
- pytest untuk deteksi trendline, pola PA, dan setup;
- laporan IS/OOS/REAL per setup dan per simbol;
- keputusan per setup: layak dibuat spec EA atau tidak.

## Glosarium

- **Trendline**: garis lewat dua swing H1 (fractal kekuatan 2, jendela 100 bar H1) searah sinyal, kemiringan ≥ 0,02 ATR H1 per bar, tidak patah (close tidak melewati garis > 0,2 ATR sejak sentuhan pertama). Aturannya sama dengan `TrendlineRules.mqh`.
- **Sentuhan**: swing atau harga dalam 0,2 ATR H1 dari garis.
- **Pola PA**: pola terarah M15 dengan aturan dan konstanta `PatternRules.mqh` (bintang, engulfing kuat, pin bar, engulfing, tweezer, outside). Pola netral tidak dipakai.
- **Bias**: bias H4 EA 1.31 (struktur dan EMA 21 searah).

## Requirements

### Requirement 1: Deteksi sama dengan EA
**User story:** Sebagai developer, saya ingin lab memakai aturan trendline dan PA yang sama dengan EA, agar setup yang lolos bisa dipindah ke EA tanpa perbedaan.

#### Acceptance criteria
1. Lab WAJIB mendeteksi swing, trendline (kemiringan, sentuhan, patah), dan pola PA dengan aturan dan konstanta EA.
2. Lab WAJIB hanya memakai bar tertutup (tanpa lookahead): keputusan di bar M15 t memakai H1/H4 yang sudah tutup sebelum t.
3. Kecocokan dengan EA WAJIB diuji:
   - pola PA pada fixture bar yang sama dengan uji MQL5 (`TestPatterns`);
   - trendline pada data kandidat spec 31 (`tl_touches`, `tl_dist`, `tl_slope` di `context_json`) untuk sampel kandidat.

### Requirement 2: Setup A dan C
**User story:** Sebagai trader, saya ingin setup pantulan dan break-retest diuji dengan aturan masuk dan keluar yang jelas.

#### Acceptance criteria
1. **Setup A:**
   - BUY bila low bar M15 dalam 0,2 ATR H1 dari support naik dan bar itu membentuk pola PA bullish;
   - SELL kebalikannya (resistance turun);
   - entry di open bar berikutnya;
   - SL di luar ekstrem bar pola atau garis (yang lebih jauh) ± 0,1 ATR H1;
   - TP 2R.
2. **Setup C:**
   - tembusan = close M15 melewati garis > 0,2 ATR H1;
   - dalam 20 bar M15 sesudahnya harga kembali dalam 0,2 ATR dari garis dan bar itu membentuk pola PA searah tembusan;
   - entry di open bar berikutnya;
   - SL di luar ekstrem bar retest ± 0,1 ATR H1;
   - TP 2R.
3. Kedua setup WAJIB memakai filter sesi EA (London + New York, sampai 22 UTC) dan jarak SL min/max EA (0,3–3 ATR H1).
4. Setiap setup diukur dalam dua varian: dengan bias H4 searah (gerbang EA) dan tanpa bias.
5. Exit WAJIB memakai simulator spec 31 (BE 1R, partial 50% di 1,5R, trailing ATR M15 × 2, spread dari bar).
6. Satu posisi per simbol: setup baru selama posisi simbol itu masih terbuka WAJIB dilewati.

### Requirement 3: Setup B dari data spec 31
**User story:** Sebagai trader, saya ingin hasil trendline + zona terlihat berdampingan dengan setup lain.

#### Acceptance criteria
1. Laporan WAJIB memuat setup B dari kandidat EA acuan yang trendline-nya dalam 0,2 ATR dari zona (`tl_touches` ≥ 2), memakai hasil simulasi spec 31 (trade nyata dan semua kandidat).

### Requirement 4: Laporan dan keputusan
**User story:** Sebagai trader, saya ingin tahu setup mana yang layak dibangun di EA, dengan aturan yang ditulis sebelum melihat hasil.

#### Acceptance criteria
1. Laporan per setup dan varian, untuk IS, OOS, dan REAL: trade, trade per bulan, R per trade, total R, PF, DD dalam R, sebaran alasan tutup, dan per simbol.
2. Varian dipilih hanya dari IS, lolos bila:
   - ≥ 100 trade (12 simbol, 27 bulan);
   - R per trade ≥ +0,10;
   - PF ≥ 1,20.
3. Varian yang lolos IS dikonfirmasi sekali di OOS dan REAL: R per trade ≥ +0,05 dan total R > 0 di keduanya.
4. Varian yang lolos konfirmasi WAJIB dicatat sebagai kandidat spec EA, dengan perkiraan tambahan trade per bulan terhadap acuan 1.31 (~4,5 per bulan).
5. Semua hasil WAJIB dicatat di spec dan `fase-5c-overview.md`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Beberapa trendline memenuhi | Pilih seperti EA: sentuhan terbanyak, lalu swing terbaru | 1.1 |
| EC-02 | Garis patah sesudah sentuhan | Tidak dipakai untuk A; untuk C patahnya adalah tembusan | 2.1, 2.2 |
| EC-03 | SL < 0,3 ATR atau > 3 ATR | Setup dilewati | 2.3 |
| EC-04 | Setup saat posisi simbol masih terbuka | Dilewati | 2.6 |
| EC-05 | Gap akhir pekan | Simulator: keluar di open | 2.5 |
| EC-06 | Histori H4/H1 kurang di awal data | Bar dilewati sampai cukup | 1.2 |
| EC-07 | XAU/BTC dengan digit dan ATR besar | Semua ukuran dalam ATR, digit dari bar | 1.1 |

## Keputusan (2026-10-13)

1. TP 2R untuk setup A dan C.
2. Retest setup C dalam 20 bar M15.
3. Ambang lolos IS: ≥ 100 trade, R per trade ≥ +0,10, PF ≥ 1,20; konfirmasi OOS dan REAL R per trade ≥ +0,05 dan total R > 0.
