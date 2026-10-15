# Requirements — Lab strategi kedua untuk frekuensi (H11)

Status: Approved (2026-10-14)
Use case: UC-83, UC-84 (baru, [fase-5c-overview.md](../fase-5c-overview.md))
Asal: permintaan user 2026-10-13/14 (intraday, R:R minimal 1,5 sampai 2, lebih sering trade, tidak terlalu lama menunggu); PRD-EA §Gaya dan timeframe, §Position management, §Di luar lingkup; PC-28 (aturan uji); python-bot-lessons §1; temuan spec 31 (jam 13–17 UTC menguntungkan), spec 32 (setup trendline rugi), spec 34/36 (zona di bawah H1 rugi, spread ≈ 20% risiko di M15)
Butuh: spec 32 (lab dan port aturan), spec 37 (acuan 1.35). Acuan = EA 1.35 (DAY H4/H1/M15, zona lawan wajib, BE 1,5R tanpa partial)

## Pendahuluan

Semua cara menambah trade **di dalam** strategi S&D gagal: timeframe lebih kecil (spec 34, 36), R:R 1,5 (spec 34), simbol tambahan (spec 35), dan setup trendline (spec 32). Strategi S&D tetap positif (1.35: REAL +0,297R per trade), tetapi hanya sekitar 4,5 trade per bulan untuk 12 simbol.

Spec ini menguji hipotesis H11: ada setup intraday **yang berdiri sendiri** (tidak memakai zona S&D) yang positif dengan R:R tetap 1,5–2 dan bisa berjalan berdampingan dengan S&D untuk menambah frekuensi. Tiga setup diuji di lab Python (perluasan `trendline_lab.py`, port aturan yang sudah terverifikasi 99,7–100%), bukan di EA:

- **S1 London breakout:** range sesi Asia (00:00–07:00 UTC) ditembus close M15 di jam London (07:00–11:00 UTC).
- **S2 New York opening range:** range 30 menit pertama New York (13:30–14:00 UTC) ditembus close M15 sampai 17:00 UTC. Jam ini paling menguntungkan di temuan spec 31.
- **S3 Pullback EMA H1:** searah bias H4 EA, harga menyentuh EMA 21 H1, lalu ada pola PA M15 searah bias.

Di luar lingkup:
- perubahan EA: setup yang lolos menjadi spec EA tersendiri, dengan PC untuk PRD karena PRD v1 hanya punya satu strategi;
- optimasi parameter (jam, buffer, periode EMA tetap seperti ditulis di sini);
- filter berita (lab tidak memakai kalender; dampaknya dicatat, sama dengan spec 32);
- scalping M1–M5 (spread dan latensi mini PC, PRD §Infrastruktur).

Bukti selesai:
- pytest untuk deteksi range, breakout, pullback, dan simulasi;
- laporan IS/OOS/REAL per setup, varian R:R, dan simbol, ditambah gabungan dengan trade EA 1.35;
- keputusan H11 per setup.

## Glosarium

- **R**: jarak entry ke SL awal.
- **Range Asia / range NY**: high dan low semua bar M1 dalam jendela waktu UTC tersebut.
- **Tembus**: close bar M15 di luar range lebih dari 0,1 ATR(14) H1.
- **Bias H4**: bias EA (struktur + EMA 21 H4, mode AND_EMA), port `bias_at` spec 32.
- **Acuan 1.35**: trade EA hasil backtest 1.35 per periode (IS +0,205R, OOS +0,524R, REAL +0,297R per trade).

## Requirements

### Requirement 1: Data dan waktu
**User story:** Sebagai developer, saya ingin lab memakai bar dan jam yang sama dengan EA, agar hasilnya bisa dipindah ke EA tanpa selisih.

#### Acceptance criteria
1. Lab WAJIB memakai bar M1 ekspor spec 31 dan agregasi M15/H1/H4 dari spec 32.
2. Lab WAJIB mengubah waktu bar ke UTC dengan selisih server-GMT yang sama dengan EA, termasuk pergantian DST.
3. Lab WAJIB hanya memakai bar tertutup: keputusan di bar M15 t hanya memakai data sampai penutupan bar t.
4. Entry WAJIB di open bar M15 berikutnya dengan spread dari bar (BUY di ask, SELL di bid), sama dengan `outcome_sim`.

### Requirement 2: Setup S1 London breakout
#### Acceptance criteria
1. KETIKA close M15 antara 07:00 dan 11:00 UTC menembus high range Asia MAKA lab WAJIB membuat kandidat BUY; menembus low → SELL.
2. SL WAJIB di sisi lain range ± 0,1 ATR H1; JIKA lebar range < 0,5 ATR H1 atau > 2,5 ATR H1 MAKA hari itu dilewati.
3. Paling banyak satu entry S1 per simbol per hari.

### Requirement 3: Setup S2 New York opening range
#### Acceptance criteria
1. KETIKA close M15 antara 14:00 dan 17:00 UTC menembus high range NY MAKA lab WAJIB membuat kandidat BUY; menembus low → SELL.
2. SL WAJIB di sisi lain range ± 0,1 ATR H1; JIKA lebar range < 0,3 ATR H1 atau > 2 ATR H1 MAKA hari itu dilewati.
3. Paling banyak satu entry S2 per simbol per hari.

### Requirement 4: Setup S3 pullback EMA H1
#### Acceptance criteria
1. SELAMA bias H4 BULL, KETIKA low bar M15 dalam 0,2 ATR H1 dari EMA 21 H1 dan bar itu membentuk pola PA bullish (`detect_pattern`, pola netral tidak dipakai) MAKA lab WAJIB membuat kandidat BUY; kebalikannya untuk BEAR → SELL.
2. SL WAJIB di luar ekstrem bar pola ± 0,1 ATR H1.
3. S3 WAJIB memakai filter sesi EA (London + New York sampai 22:00 UTC).

### Requirement 5: Exit, biaya, dan satu posisi
#### Acceptance criteria
1. Setiap setup WAJIB diukur dengan dua varian TP tetap: 1,5R dan 2R, tanpa BE/partial/trailing (target R:R yang diminta user).
2. JIKA jarak SL < 0,3 ATR H1 atau > 3 ATR H1 MAKA kandidat dilewati (batas SL EA).
3. JIKA spread saat entry > 15% R MAKA kandidat dilewati dan jumlahnya dilaporkan.
4. Posisi yang belum tutup di 21:45 UTC Jumat WAJIB ditutup di harga bar itu (tanpa menahan posisi lewat akhir pekan).
5. Satu posisi per simbol per setup; setup baru selama posisi setup itu masih terbuka WAJIB dilewati.

### Requirement 6: Laporan dan keputusan
**User story:** Sebagai trader, saya ingin tahu setup mana yang layak dibangun di EA, dengan aturan yang ditulis sebelum melihat hasil.

#### Acceptance criteria
1. Laporan per setup × varian TP × periode WAJIB memuat: trade, trade per bulan, win rate, R per trade, total R, PF, DD dalam R, rata-rata spread/R, lama posisi, dan per simbol.
2. Varian dipilih **hanya dari IS** dan lolos bila:
   - ≥ 120 trade (≈ 4,5 per bulan, sama dengan frekuensi acuan);
   - R per trade ≥ +0,10 dan PF ≥ 1,20;
   - ≥ 7 dari 12 simbol dengan total R > 0.
3. Per setup dipilih satu varian TP (R per trade IS tertinggi yang lolos); varian terpilih dikonfirmasi sekali di OOS dan REAL: R per trade ≥ +0,05 dan total R > 0 di keduanya.
4. Untuk setup yang lolos konfirmasi, laporan WAJIB menambah simulasi **gabungan** dengan trade EA 1.35 per periode, dengan aturan satu posisi per simbol lintas strategi (trade EA lebih dulu): trade per bulan, R per trade, total R, DD.
5. Setup yang lolos 6.3 dan gabungannya (6.4) memberi total R ≥ acuan 1.35 di OOS dan REAL WAJIB dicatat sebagai kandidat spec EA, dengan perkiraan tambahan trade per bulan.
6. Semua hasil WAJIB dicatat di spec ini dan `fase-5c-overview.md` §8.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Pergantian DST (Maret/Oktober–November) menggeser jam server | Jendela tetap dalam UTC, bukan jam server | 1.2 |
| EC-02 | Range Asia tidak lengkap (Senin pagi, hari libur, data bolong > 30 menit di jendela) | Hari itu dilewati dan dihitung | 2.2 |
| EC-03 | Close menembus dua sisi range di hari yang sama | Hanya tembusan pertama; satu entry per hari | 2.3, 3.3 |
| EC-04 | Gap akhir pekan atau gap berita melewati SL/TP | Simulator keluar di open bar | 5.1 |
| EC-05 | BTC buka akhir pekan dan tidak punya sesi | Jendela UTC sama setiap hari, termasuk Sabtu/Minggu; aturan Jumat 5.4 tidak berlaku untuk crypto | 2.1, 5.4 |
| EC-06 | XAU/XAG/BTC dengan digit dan ATR besar | Semua ukuran dalam ATR, digit dari bar | 2.2, 5.2 |
| EC-07 | Spread melebar saat pembukaan London/NY | Kandidat dilewati bila > 15% R (5.3) dan jumlahnya dilaporkan | 5.3 |
| EC-08 | Setup lain dan EA ingin masuk di simbol yang sama | Di laporan per setup: setup independen. Di simulasi gabungan: EA lebih dulu, setup dilewati | 5.5, 6.4 |
| EC-09 | Histori H4 kurang di awal periode (bias S3) | Pemanasan 60 hari seperti spec 32; bar dilewati sampai cukup | 4.1 |

## Keputusan (2026-10-14)

1. Tiga setup S1, S2, S3 (user menyetujui draft tanpa setup tambahan).
2. Ambang IS ≥ 120 trade, R per trade ≥ +0,10, PF ≥ 1,20, ≥ 7 dari 12 simbol positif.
3. Varian exit hanya TP tetap 1,5R dan 2R tanpa BE/trailing (tidak ada varian BE 1,5R).
