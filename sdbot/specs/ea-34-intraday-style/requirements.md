# Requirements — Gaya intraday H1/M15/M5 (H7)

Status: Done (2026-10-13)
Use case: UC-83 ([fase-5c-overview.md](../fase-5c-overview.md)); permintaan user 2026-10-12: entry lebih sering seperti intraday, target 1:1,5 sampai 1:2, bukan scalping singkat
Asal: PRD-EA §Gaya dan timeframe (keputusan 2026-09-28: day trading H4/H1/M15), §Aturan entry (R:R ≥ 2), §Parameter input (`TradingStyle`, `MinRR`); PC-28 (aturan uji); PC-34 (zona lawan wajib)
Butuh: spec 33 (selesai). Acuan = konfigurasi 1.31 (gaya DAY, zona lawan wajib)

## Pendahuluan

Spec ini menguji hipotesis H7: gaya intraday (bias H1, zona M15, trigger M5) memberi trade lebih sering dengan hasil per trade yang masih positif.

Sekarang EA memakai gaya DAY (H4/H1/M15). Dengan zona lawan wajib (1.31), backtest 12 bulan terakhir menghasilkan sekitar 72 trade untuk 12 simbol (sekitar 6 per bulan, jeda terpanjang 21 hari). Penyebab utama jarangnya entry adalah timeframe: zona H1 baru terbentuk dan disentuh beberapa kali seminggu per simbol. R:R minimum (2,0) bukan pembatas utama, karena tahap `RR_TOO_LOW` hanya sekitar 1% kandidat.

Gaya yang ada:

| Gaya | HTF (bias) | MTF (zona) | LTF (trigger) |
|---|---|---|---|
| SCALPING | M15 | M5 | M1 |
| DAY (sekarang) | H4 | H1 | M15 |
| **INTRADAY (baru)** | **H1** | **M15** | **M5** |

Semua ukuran strategi berbasis ATR timeframe masing-masing (lebar zona, gerak keluar, buffer dan jarak SL, trailing ATR LTF). Karena itu gaya baru memakai parameter yang sama tanpa penyetelan ulang. Usia zona maksimum 100 bar MTF berarti sekitar 25 jam di M15.

Varian yang diuji:
- **V1:** INTRADAY, R:R minimum 2,0 (aturan sekarang);
- **V2:** INTRADAY, R:R minimum 1,5;
- **V3:** DAY, R:R minimum 1,5 (memisahkan efek R:R dari efek timeframe).

Di luar lingkup:
- penyetelan parameter per gaya (lookback, ATR, jarak SL) kecuali bila backtest menunjukkan kegagalan jelas;
- gaya SCALPING (M15/M5/M1), yang lebih pendek dari permintaan;
- jam sesi khusus intraday (tetap London + New York sampai 22 UTC).

Bukti selesai:
- suite unit dan regresi PASS, default identik dengan acuan;
- backtest IS/OOS/REAL tiap varian tercatat dengan frekuensi trade;
- keputusan H7 diterima atau ditolak beserta datanya.

## Glosarium

- **Gaya**: pasangan HTF/MTF/LTF dari input `InpTradingStyle`.
- **Frekuensi**: trade per bulan untuk 12 simbol.
- **Acuan**: konfigurasi 1.31 (DAY, R:R 2,0, zona lawan wajib). Sesi acuan IS/OOS/REAL: 1968–1979, 1980–1991, 1992–2003.

## Requirements

### Requirement 1: Gaya INTRADAY
**User story:** Sebagai trader, saya ingin memilih gaya intraday, agar EA mencari setup di timeframe lebih kecil dan entry lebih sering.

#### Acceptance criteria
1. `InpTradingStyle` WAJIB menyediakan nilai `INTRADAY` dengan HTF H1, MTF M15, LTF M5.
2. Gaya yang sudah ada (SCALPING, DAY, SWING, POSITION) WAJIB tidak berubah.
3. BILA INTRADAY, EA WAJIB memakai aturan pipeline yang sama (bias, zona, PA, skor, filter, SL/TP, manajemen posisi) di timeframe gaya itu. Kebutuhan histori dihitung dari timeframe gaya.
4. `sessions` dan `signals.style` WAJIB mencatat gaya. JIKA nilai `INTRADAY` belum ada di enum skema `style`, MAKA perubahan skema mengikuti aturan kontrak `shared/schema` (versi skema naik, migrasi, fixture).
5. JIKA histori M5/M15/H1 kurang, MAKA perilaku WAJIB sama dengan sekarang (analisis ditunda, log WARN).

### Requirement 2: Pengukuran IS
**User story:** Sebagai developer, saya ingin gaya intraday dan R:R 1,5 diukur dengan aturan yang sama dengan spec sebelumnya.

#### Acceptance criteria
1. Backtest `-Period IS` WAJIB dijalankan untuk V1, V2, dan V3.
2. Laporan WAJIB memuat:
   - trade, frekuensi per bulan, R per trade, total R, PF, DD, jumlah per simbol;
   - lama posisi rata-rata (jam);
   - sebaran alasan tutup.
3. Varian lolos IS bila:
   - frekuensi ≥ 2× acuan (IS acuan 121 trade → ≥ 242);
   - R per trade ≥ +0,05 dan PF ≥ 1,10;
   - total R IS ≥ acuan (+19,8R);
   - ≥ 10 trade per simbol.
4. Dari yang lolos, varian terpilih = total R IS tertinggi (aturan rinci di design).
5. JIKA tidak ada yang lolos, MAKA H7 WAJIB ditolak tanpa OOS dan REAL.

### Requirement 3: Konfirmasi dan keputusan
**User story:** Sebagai trader, saya ingin gaya diganti hanya bila terbukti di data yang tidak dipakai menyetel.

#### Acceptance criteria
1. Varian terpilih WAJIB dijalankan sekali di OOS dan sekali di REAL.
2. H7 DITERIMA bila:
   - di OOS dan REAL, total R ≥ acuan;
   - R per trade ≥ +0,05;
   - frekuensi ≥ 2× acuan.
3. Bila DITERIMA:
   - default gaya dan R:R mengikuti varian, preset 12 simbol berubah;
   - versi EA naik;
   - PC untuk PRD §Gaya dan timeframe, §Aturan entry, §Parameter input.
4. Bila DITOLAK: default tetap DAY dan R:R 2,0. Gaya INTRADAY tetap tersedia untuk eksperimen.
5. Semua hasil WAJIB dicatat di spec, CHANGELOG, dan `fase-5c-overview.md`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Spread relatif besar terhadap ATR M15 (XAU, XAG) | Filter spread dan R:R yang ada berlaku; biaya terlihat di R per trade | 2.2 |
| EC-02 | Zona M15 sangat banyak | Gerbang zona, PA, skor tetap; batas 1 posisi per instance tetap | 1.3 |
| EC-03 | Berita high impact lebih sering memotong setup pendek | Blackout ±15/±10 menit tetap | 1.3 |
| EC-04 | Restart di tengah bar M5 | Bar dinilai sekali (penanda bar) seperti sekarang | 1.3 |
| EC-05 | Histori H1 cukup tetapi M5 kurang di awal backtest | Analisis ditunda sampai cukup | 1.5 |
| EC-06 | Live: lot minimum di saldo 1.801 USC dengan SL lebih pendek | SL lebih pendek berarti lot lebih besar; XAU/XAG lebih sering lolos lot minimum | 2.2 |

## Keputusan (2026-10-12)

1. Target frekuensi: minimal 2× acuan (IS ≥ 242 trade; OOS dan REAL ≥ 2× acuan masing-masing).
2. R:R yang diuji 1,5 dan 2,0; 1,0 tidak diuji.
3. Zona lawan wajib (H6, 1.31) berlaku di semua varian.
