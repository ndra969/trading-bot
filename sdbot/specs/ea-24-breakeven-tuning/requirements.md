# Requirements — Breakeven lebih awal (H2)

Status: Done (2026-10-08)
Use case: UC-61, UC-63 ([fase-5b-overview.md](../fase-5b-overview.md))
Asal: PRD-EA §Position management (breakeven saat profit ≥ 1R, trailing sesudah breakeven aktif), §Parameter input (`BreakevenR` 1.0); PC-28 (aturan uji Fase 5b); PC-29 (acuan v1.25 zona Fresh saja)
Butuh: spec 23 (v1.25, acuan baru), alat IS/OOS/REAL dan `-SetInput` (spec 22)

## Pendahuluan

Spec ini menguji hipotesis H2: breakeven yang aktif lebih awal memotong trade rugi yang sempat bergerak sesuai arah.

Data v1.25 (zona Fresh saja) mendukung hipotesis ini:
- **IS:** 53 dari 166 trade yang kena SL sempat mencapai MFE ≥ 0,5R.
- **REAL:** 21 dari 57 trade yang kena SL sempat mencapai MFE ≥ 0,5R.

Breakeven lebih awal juga punya biaya:
- winner yang sempat mundur ke titik entry ikut tertutup di BE;
- trailing ATR (aktif sesudah BE) mulai lebih cepat dan bisa memotong winner.

Input `InpBreakevenR` sudah ada, jadi spec ini hanya mengukur dan memutuskan. Kode EA tidak berubah kecuali default.

Di luar lingkup:
- perubahan aturan trailing (tetap aktif sesudah BE, ATR(14) × 2);
- perubahan partial close (1,5R, 50%);
- perubahan buffer BE.

Bukti selesai:
- backtest IS untuk tiap varian tercatat;
- varian terpilih diuji di OOS dan REAL;
- keputusan H2 diterima atau ditolak beserta datanya;
- bila diterima: default, preset, dan uji ikut berubah, regresi ALL PASS.

## Glosarium

- **Acuan**: konfigurasi v1.25 (`InpBreakevenR = 1.0`, zona Fresh saja). Sesinya: IS 1396–1407, OOS 1408–1419, REAL 1420–1431.
- **Varian**: nilai `InpBreakevenR` yang diuji, yaitu 0,5 dan 0,75.
- **MFE**: pergerakan terbaik posisi dalam R, dari bar M1. Untuk SELL nilainya sedikit lebih besar dari yang bisa dicapai karena dihitung dari harga bid.

## Requirements

### Requirement 1: Pengukuran varian di IS
**User story:** Sebagai developer, saya ingin setiap nilai breakeven diukur dengan data dan aturan yang sama, agar pilihan tidak bergantung pada OOS.

#### Acceptance criteria
1. Backtest `-Period IS` WAJIB dijalankan untuk `InpBreakevenR` 0,5 dan 0,75 dengan konfigurasi lain sama dengan acuan v1.25.
2. Setiap varian WAJIB dilaporkan dengan:
   - jumlah trade, R per trade, PF, dan DD;
   - sebaran alasan tutup (SL, BE_STOP, TRAIL_STOP, TP);
   - rata-rata R per alasan tutup.
3. Varian terpilih WAJIB ditentukan hanya dari hasil IS, dengan aturan yang ditulis di design sebelum OOS dijalankan.
4. Varian terpilih WAJIB memiliki R per trade IS lebih tinggi dari acuan dan memenuhi kriteria jumlah trade Fase 5b: IS ≥ 325 trade dan ≥ 13 trade per simbol.
5. JIKA tidak ada varian yang memenuhi kriteria 1.4, MAKA H2 WAJIB ditolak tanpa menjalankan OOS dan REAL.

### Requirement 2: Konfirmasi OOS dan REAL
**User story:** Sebagai developer, saya ingin varian terpilih dikonfirmasi sekali di data yang tidak dipakai menyetel, agar perbaikan tidak hanya kebetulan di IS.

#### Acceptance criteria
1. Varian terpilih WAJIB dijalankan sekali di `-Period OOS` dan sekali di `-Period REAL`, lalu dibandingkan dengan acuan OOS 1408–1419 dan REAL 1420–1431.
2. Laporan OOS dan REAL WAJIB memuat metrik yang sama dengan kriteria 1.2.
3. Semua hasil WAJIB dicatat di spec dan CHANGELOG, termasuk bila H2 ditolak.

### Requirement 3: Keputusan
**User story:** Sebagai trader, saya ingin aturan yang jelas kapan breakeven diubah.

#### Acceptance criteria
1. H2 DITERIMA bila varian terpilih:
   - lolos kriteria 1.4;
   - R per trade di OOS dan REAL ≥ acuan masing-masing.
2. Bila DITERIMA:
   - default `InpBreakevenR` berubah ke varian terpilih;
   - preset 12 simbol diperbarui;
   - uji yang memeriksa default ikut diperbarui;
   - versi EA naik ke 1.26;
   - PC baru mengubah PRD §Position management dan §Parameter input.
3. Bila DITOLAK: default tetap 1.0, preset dan versi tidak berubah, dan temuan dicatat.
4. Validasi input yang ada (`0 < InpBreakevenR < InpPartialR`) WAJIB tetap berlaku untuk default baru.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Titik BE (entry ± spread + komisi + buffer) terlalu dekat harga saat 0,5R, terutama simbol dengan spread lebar (XAUUSDc, BTCUSDc) | Aturan modifikasi yang ada berlaku: level di bawah stops/freeze level ditunda atau dicoba ulang; jumlah `MODIFY_FAILED` per varian dilaporkan | 1.2 |
| EC-02 | BE lebih awal membuat trailing ATR aktif lebih awal | Tetap sesuai PRD (trailing sesudah BE); efeknya terlihat di jumlah dan R TRAIL_STOP | 1.2 |
| EC-03 | MFE SELL dihitung dari bid, jadi sedikit lebih besar dari yang bisa dicapai | Hanya dipakai untuk diagnosis, bukan aturan keputusan; keputusan memakai R hasil | 1.3 |
| EC-04 | Gap akhir pekan melewati SL yang sudah di BE | Tutup di harga gap, R bisa negatif meski BE aktif; dihitung apa adanya | 1.2 |
| EC-05 | Kedua varian sama-sama lebih baik dari acuan | Aturan pilih di design menentukan satu varian; tidak ada uji OOS ganda | 1.3, 2.1 |
| EC-06 | Varian lolos IS tetapi lebih buruk di OOS atau REAL | H2 ditolak; varian lain tidak dicoba di OOS | 3.1, 3.3 |

## Pertanyaan terbuka

- Grid cukup 0,5 dan 0,75, atau tambah 0,6? Usulan saya dua nilai saja (sesuai overview) agar IS tidak disetel terlalu halus.
- Trailing tetap dimulai saat BE aktif (PRD). Memisahkan pemicu trailing dari BE butuh kode dan bisa jadi spec terpisah bila data menunjukkan trailing dini memotong winner.
