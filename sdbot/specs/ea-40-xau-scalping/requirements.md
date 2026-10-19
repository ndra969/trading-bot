# Requirements — Riset scalping XAUUSD (H14)

Status: Done (2026-10-19)
Use case: UC-83, UC-84 ([fase-5c-overview.md](../fase-5c-overview.md))
Asal: permintaan user 2026-10-19 (trade lebih banyak, tidak banyak loss, profit per bulan; "scalping rugi juga?"); PRD-EA §Gaya dan timeframe (Scalping M15/M5/M1), §Infrastruktur (latensi mini PC kurang ideal untuk M1); PC-28 (aturan uji); temuan 2026-10-19 (spread ÷ range candle)
Butuh: spec 38 (lab, simulator dengan `close_after`). Acuan = EA 1.37 (DAY, XAUUSDc)

## Pendahuluan

Semua setup timeframe kecil yang sudah diuji rugi (spec 34, 36, 38). Uji entry acak 2026-10-19 menunjukkan penyebabnya biaya, bukan logika:
- entry acak: −0,109R per trade dengan spread ≈ 9% R, sesuai teori;
- setup breakout sedikit di atas acak, tetapi keunggulannya habis oleh spread.

Ukuran spread dibanding range candle (data 2026, jam 07–17 UTC):

| Simbol | M1 | M5 | M15 |
|---|---|---|---|
| EURUSD / GBPUSD / USDJPY | 48–53% | 20–22% | 11–13% |
| **XAUUSD** | **11%** | **5%** | **3%** |

XAUUSD adalah satu-satunya simbol aktif yang biayanya masuk akal untuk scalping. Spec ini menguji hipotesis H14: ada setup scalping XAUUSD yang memberi trade jauh lebih sering dari acuan dan tetap positif sesudah spread.

Dua setup, sengaja sedikit agar risiko lolos karena kebetulan kecil:
- **X1, S&D versi scalping (EA, Strategy Tester).** Gaya `SCALPING` yang sudah ada di EA (bias M15, zona M5, trigger PA M1), aturan lain sama dengan 1.37, hanya XAUUSDc. Tanpa perubahan kode.
- **X2, mean reversion M5 (lab Python).** Close M5 di luar Bollinger Band(20, 2) dengan RSI(14) ekstrem (≥ 75 untuk SELL, ≤ 25 untuk BUY), entry berlawanan arah, TP di garis tengah band. Hanya bila R:R ke TP ≥ 1,5.

Di luar lingkup:
- simbol selain XAUUSDc;
- M1 sebagai timeframe entry untuk X2 (latensi mini PC);
- optimasi parameter (periode, ambang, jam tetap seperti ditulis di sini);
- perubahan EA (setup yang lolos menjadi spec EA tersendiri, dengan PC karena PRD v1 hanya punya satu strategi).

Bukti selesai:
- backtest X1 IS/OOS/REAL;
- pytest untuk X2;
- laporan X2 IS/OOS/REAL;
- keputusan H14 per setup.

## Glosarium

- **R**: jarak entry ke SL awal.
- **Acuan**: trade XAUUSDc EA 1.35/1.37 per periode (sesi baseline yang sama dengan spec 37/39).
- **Biaya**: spread saat entry dalam R (`spread/R`).

## Requirements

### Requirement 1: X1 S&D scalping di EA
#### Acceptance criteria
1. Backtest `-Period` IS untuk XAUUSDc dengan `InpTradingStyle` = SCALPING, input lain dari preset XAUUSDc 1.37.
2. Laporan WAJIB memuat:
   - trade, trade per bulan, win rate, R per trade, total R, PF, DD;
   - alasan tutup dan lama posisi;
   - rata-rata spread/R (dari `signals.spread_points` dan SL).
3. Kandidat yang ditolak spread (`SPREAD_TOO_WIDE`) dan jarak SL WAJIB dihitung dan dilaporkan.

### Requirement 2: X2 mean reversion M5 di lab
#### Acceptance criteria
1. Lab WAJIB memakai bar M1 ekspor XAUUSDc (jam server = UTC, TS-137) yang diagregasi ke M5, hanya dengan bar tertutup (tanpa lookahead).
2. KETIKA close M5 > band atas BB(20, 2) dan RSI(14) M5 ≥ 75 MAKA lab WAJIB membuat kandidat SELL. KETIKA close M5 < band bawah dan RSI ≤ 25 MAKA kandidat BUY.
3. Entry di open bar M5 berikutnya. SL di luar ekstrem bar sinyal ± 0,1 ATR(14) M5 (SELL + spread). TP = garis tengah BB pada bar sinyal.
4. JIKA R:R ke TP < 1,5, ATAU jarak SL < 0,5 ATR / > 3 ATR M5, ATAU spread > 15% R, MAKA kandidat WAJIB dilewati dan dihitung per alasan.
5. Hanya jam 07:00–17:00 UTC (London dan overlap New York). Satu posisi sekaligus. Posisi terbuka ditutup Jumat 21:45 UTC.
6. Exit: SL/TP murni, tanpa BE dan trailing (simulator spec 31 dengan `be_r = partial_r = 99`).

### Requirement 3: Aturan lolos dan keputusan (ditulis sebelum hasil)
#### Acceptance criteria
1. Setiap setup dipilih hanya dari IS, dan lolos IS bila:
   - ≥ 20 trade per bulan (≈ 540 trade IS);
   - R per trade ≥ +0,10 sesudah spread;
   - PF ≥ 1,20;
   - DD ≤ 25R.
2. Setup yang lolos IS dikonfirmasi sekali di OOS dan REAL: R per trade ≥ +0,05 dan total R > 0 di keduanya.
3. Laporan WAJIB membandingkan dengan entry acak XAUUSDc pada jam dan R:R yang sama (pembanding tanpa keunggulan).
4. Setup yang lolos konfirmasi dicatat sebagai kandidat spec EA, dengan perkiraan trade dan R per bulan, plus catatan risiko eksekusi (latensi mini PC, slippage M5).
5. Semua hasil dicatat di spec ini dan `fase-5c-overview.md` §8.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Rilis berita HIGH USD (spike M5) | X1: filter berita EA ±15 menit tetap aktif. X2: tidak ada filter (dicatat); trade dalam ±15 menit rilis dilaporkan terpisah | 1.1, 2.2 |
| EC-02 | Spread melebar (pembukaan pasar, rollover 21–22 UTC) | Di luar jam X2; X1 ditolak `SPREAD_TOO_WIDE` | 1.3, 2.4, 2.5 |
| EC-03 | Real ticks XAUUSDc hanya sejak 2026-08-14 | REAL X1 sebagian memakai tick buatan (ShortHistory); dicatat di laporan | 1.1 |
| EC-04 | Gap akhir pekan | Posisi X2 ditutup Jumat 21:45; X1 mengikuti EA | 2.5 |
| EC-05 | TP garis tengah sudah tercapai di bar sinyal (band menyempit) | R:R < 1,5 → dilewati | 2.4 |
| EC-06 | Tren kuat: close terus di luar band beberapa bar | Satu posisi sekaligus; sinyal berikutnya hanya sesudah posisi tutup | 2.5 |

## Keputusan (2026-10-19)

1. Target ≥ 20 trade per bulan dari XAUUSD saja.
2. BB(20, 2) dan RSI(14) 75/25 apa adanya, tanpa optimasi.
