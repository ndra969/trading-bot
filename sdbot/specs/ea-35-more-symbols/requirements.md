# Requirements — Simbol tambahan (H8)

Status: Done (2026-10-13)
Use case: UC-83 ([fase-5c-overview.md](../fase-5c-overview.md)); permintaan user 2026-10-13: lebih banyak trade tanpa mengorbankan kualitas, sesudah H7 (intraday) ditolak
Asal: PRD-EA §Simbol (PC-10: 12 simbol bot Python), §Parameter input (preset per simbol, magic), §Risk (batas posisi per kategori aset); PC-28 (aturan uji); spec 34 (frekuensi hanya naik tanpa merusak hasil bila jumlah simbol bertambah)
Butuh: spec 34 (selesai). Acuan = konfigurasi 1.31 (DAY, zona lawan wajib), EA 1.32 dengan default sama

## Pendahuluan

Spec ini menguji hipotesis H8: menambah simbol dengan aturan strategi yang sama menambah jumlah trade dan total profit tanpa menurunkan R per trade.

Spec 34 menunjukkan bahwa keunggulan strategi hanya ada di timeframe DAY. Menambah frekuensi lewat timeframe kecil atau R:R kecil merusak hasil. Jalan yang tersisa adalah lebih banyak pasar. Satu simbol di 1.31 menghasilkan sekitar 4–10 trade per tahun.

Kandidat dipilih dari simbol cent yang bisa diperdagangkan, dengan spread rata-rata ≤ 15% ATR H1 (12 simbol aktif berkisar 7–20%):

| Kelompok | Simbol | Spread / ATR H1 |
|---|---|---|
| Indeks | US30c, USTECc, US500c | 0,8–2,5% |
| Energi | USOILc, UKOILc | 2,0% |
| Kripto | ETHUSDc | 7,0% |
| Cross JPY | CADJPYc, AUDJPYc, CHFJPYc, NZDJPYc | 9,3–12,8% |
| Cross lain | EURCADc, EURAUDc, EURNZDc, GBPNZDc, AUDCHFc, GBPAUDc, GBPCADc | 12,4–14,9% |

Tidak diuji: EURGBP, AUDCAD, EURCHF, AUDNZD, GBPCHF (spread > 15% ATR), USDHKD (tidak bergerak), dan BTCUSDT (duplikat BTCUSD).

Risiko utama spec ini adalah **seleksi**. Memilih simbol dari hasilnya sendiri mudah menemukan kebetulan. Karena itu simbol dipilih hanya dari IS, lalu kelompok terpilih dikonfirmasi sekali di OOS dan REAL.

Di luar lingkup:
- penyetelan parameter per simbol (semua tetap preset baku, kecuali spread maksimum dan magic);
- menghapus simbol yang sudah aktif (ditinjau terpisah, misalnya EURJPY/GBPJPY);
- live: membuka chart baru adalah langkah manual sesudah keputusan.

Bukti selesai:
- semua kandidat punya histori tester yang cukup, atau dicatat tidak bisa diuji;
- preset dan klasifikasi aset kandidat lolos uji;
- backtest IS per kandidat, seleksi, lalu OOS + REAL kelompok terpilih;
- keputusan H8 beserta datanya.

## Glosarium

- **Kandidat**: simbol di tabel di atas.
- **Kelompok terpilih**: kandidat yang lolos seleksi IS.
- **Portofolio**: 12 simbol aktif + kelompok terpilih.
- **Acuan**: 1.31, 12 simbol. IS 1968–1979 (121 trade, +19,8R), OOS 1980–1991 (21, +8,84R), REAL 1992–2003 (55, +12,32R).

## Requirements

### Requirement 1: Kesiapan simbol kandidat
**User story:** Sebagai developer, saya ingin setiap kandidat bisa dijalankan EA dengan aman, agar backtestnya sah dan live tidak salah hitung risiko.

#### Acceptance criteria
1. Setiap kandidat WAJIB punya preset (`SDBot_DAY_<SIMBOL>.set`) dengan magic unik, spread maksimum sesuai aturan preset yang ada, dan input lain sama dengan preset aktif.
2. Setiap kandidat WAJIB diklasifikasikan ke kategori aset yang benar (forex mayor/cross, komoditas, kripto, atau kategori indeks bila belum ada) untuk batas posisi per kategori dan eksposur mata uang.
3. JIKA kategori indeks belum ada di EA, MAKA penambahannya WAJIB mengikuti aturan risk yang ada (batas posisi per kategori, input baru dengan default aman) dan diuji.
4. Histori tester setiap kandidat WAJIB diperiksa (`-ProbeHistory`). Kandidat yang historinya tidak menutup IS dicatat dan dikeluarkan.
5. Lot minimum WAJIB diperiksa untuk saldo live (1.801 USC, risk 0,5%) dengan backtest `-Deposit`. Kandidat yang sebagian besar sinyalnya tertolak lot minimum dicatat.

### Requirement 2: Seleksi IS
**User story:** Sebagai trader, saya ingin simbol ditambah hanya bila hasilnya baik di data pengembangan, dengan aturan yang ditulis sebelum melihat hasil.

#### Acceptance criteria
1. Backtest `-Period IS` WAJIB dijalankan untuk semua kandidat yang siap, dengan konfigurasi acuan.
2. Kandidat lolos IS bila ≥ 8 trade **dan** R per trade ≥ +0,05 **dan** PF ≥ 1,10.
3. Kelompok terpilih WAJIB ≥ 3 simbol. JIKA kurang dari 3, MAKA H8 ditolak.
4. Laporan WAJIB memuat per kandidat: trade, R per trade, total R, PF, trade per bulan, dan alasan tutup.

### Requirement 3: Konfirmasi dan keputusan
**User story:** Sebagai trader, saya ingin simbol baru dipakai hanya bila kelompoknya terbukti di data yang tidak dipakai memilih.

#### Acceptance criteria
1. Kelompok terpilih WAJIB dijalankan sekali di OOS dan sekali di REAL.
2. H8 DITERIMA bila, untuk kelompok terpilih di OOS dan REAL:
   - total R > 0;
   - R per trade ≥ +0,05;
   - portofolio tidak lebih buruk dari acuan dalam R per trade dikurangi 0,03.
3. Bila DITERIMA:
   - preset simbol baru masuk repo;
   - README dan PRD diperbarui;
   - langkah live (chart baru, preset lokal) dicatat.
4. Bila DITOLAK: preset kandidat tetap tersedia, tidak dipakai.
5. Semua hasil WAJIB dicatat di spec, CHANGELOG, dan `fase-5c-overview.md`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Indeks tidak punya mata uang base/profit forex (US30) | Klasifikasi kategori eksplisit; eksposur mata uang hanya dari mata uang profit | 1.2, 1.3 |
| EC-02 | Jam sesi indeks/minyak berbeda (tutup harian, akhir pekan) | Filter sesi dan pengecekan pasar buka yang ada berlaku | 1.1 |
| EC-03 | Tick value indeks besar sehingga lot minimum melebihi risiko di saldo kecil | Ditolak `LOT_BELOW_MIN`; terlihat di backtest `-Deposit` | 1.5 |
| EC-04 | Histori tester kandidat lebih pendek dari IS | Dikeluarkan atau diuji di periode yang ada dengan catatan | 1.4 |
| EC-05 | Kandidat berkorelasi tinggi dengan simbol aktif (EURAUD dengan AUDUSD) | Batas eksposur mata uang yang ada berlaku | 1.2 |
| EC-06 | Kandidat lolos IS hanya karena satu atau dua trade besar | Syarat ≥ 8 trade dan PF; OOS/REAL kelompok sebagai pengaman | 2.2, 3.2 |

## Keputusan (2026-10-13)

1. Kandidat: 17 simbol di tabel (semula tertulis 19, salah hitung), tanpa perubahan.
2. Tidak ada batas jumlah chart live.
3. Ambang seleksi IS: ≥ 8 trade, R per trade ≥ +0,05, PF ≥ 1,10; kelompok ≥ 3 simbol.
