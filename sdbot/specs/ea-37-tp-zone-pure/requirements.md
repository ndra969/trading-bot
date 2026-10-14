# Requirements — Manajemen posisi lebih ringan: TP ke zona lawan (H10)

Status: Done (2026-10-14)
Use case: UC-83 ([fase-5c-overview.md](../fase-5c-overview.md)); permintaan user 2026-10-13: cek apakah config yang membuat strategi hanya untung di R:R tertentu
Asal: PRD-EA §Position management (BE 1R, partial 50% di 1,5R, trailing ATR(14) × 2 sesudah BE), §Parameter input; PC-28 (aturan uji); spec 24 (BE lebih awal ditolak), spec 26 (trailing lebih longgar ditolak); simulasi 2026-10-13 (simulator spec 31)
Butuh: spec 33 (zona lawan wajib). Acuan = konfigurasi 1.31 (sesi IS 1968–1979, OOS 1980–1991, REAL 1992–2003)

## Pendahuluan

Spec ini menguji hipotesis H10: dengan TP selalu di zona lawan (1.31), breakeven dan partial memotong pemenang sebelum mencapai target, sehingga manajemen posisi yang lebih ringan menaikkan R per trade.

Simulasi trade acuan 1.31 (simulator terkalibrasi, alasan tutup cocok 98–99%):

| Periode | Config sekarang | Murni SL / TP ke zona lawan |
|---|---|---|
| IS (121 trade) | +0,151R, +18,2R | +0,298R, +36,1R |
| OOS (21) | +0,503R, +10,6R | +0,393R, +8,2R |
| REAL (55) | +0,292R, +16,1R | +0,382R, +21,0R |

Hasilnya membaik di IS dan REAL tetapi tidak di OOS (sampel kecil), jadi harus diuji di EA dengan aturan biasa.

Varian memakai input yang ada, tanpa perubahan kode (nilai yang tidak pernah tercapai mematikan fungsinya):

| Varian | `InpBreakevenR` | `InpPartialR` | Arti |
|---|---|---|---|
| V1 murni | 9,0 | 10,0 | tanpa BE, tanpa partial, tanpa trailing (trailing mulai sesudah BE) |
| V2 tanpa partial | 1,0 | 10,0 | BE 1R + trailing tetap, partial mati |
| V3 BE 1,5R tanpa partial | 1,5 | 10,0 | BE lebih jauh + trailing, partial mati |

R:R rencana rata-rata trade acuan sekitar 3,8, sehingga TP jarang melewati 9–10R. Trade yang targetnya lebih jauh dari 9R tetap memicu BE/partial, dan ini dicatat.

Di luar lingkup:
- R:R minimum (tetap 2; R:R 1,5 ditolak, lihat diagnosa 2026-10-13);
- jarak dan buffer SL (buffer besar diuji 2026-10-13, lebih buruk).

Bukti selesai:
- backtest IS tiga varian, lalu OOS + REAL varian terpilih;
- keputusan H10.

## Requirements

### Requirement 1: Pengukuran IS
#### Acceptance criteria
1. Backtest `-Period IS` untuk V1, V2, V3 dengan konfigurasi lain sama dengan acuan.
2. Laporan: trade, R per trade, total R, PF, DD, alasan tutup, lama posisi, trade per bulan, per simbol, dan `trade_diff` terhadap acuan.
3. Varian lolos IS bila:
   - R per trade > acuan (+0,164);
   - DD tidak lebih dari 1,5× acuan (≤ 9,8R);
   - trade ≥ 90% acuan (≥ 109), karena posisi yang lebih lama bisa menahan entry berikutnya di simbol yang sama.
4. Dari yang lolos pilih R per trade IS tertinggi; selisih < 0,02R → varian dengan perubahan paling kecil (V2, V3, lalu V1).
5. Tidak ada yang lolos → H10 ditolak.

### Requirement 2: Konfirmasi dan keputusan
#### Acceptance criteria
1. Varian terpilih dijalankan sekali di OOS dan REAL.
2. DITERIMA bila R per trade OOS dan REAL ≥ acuan (+0,421 dan +0,224; acuan 1.31 per periode).
3. Bila DITERIMA:
   - default `InpBreakevenR` / `InpPartialR` dan preset 12 simbol berubah;
   - versi naik;
   - PC untuk PRD §Position management;
   - spec lanjutan opsional untuk input "mati" eksplisit (misalnya 0 = tanpa BE) bila nilai besar dipakai sebagai default.
4. Bila DITOLAK: default tetap, hasil dicatat.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Tanpa BE, posisi terbuka dihitung risiko penuh (PRD: posisi BE = 0%) | Batas risiko terbuka 3% bisa lebih sering tercapai di live; di backtest per simbol tidak terlihat. Dicatat sebagai risiko | 1.2 |
| EC-02 | Posisi lebih lama menahan entry simbol yang sama (`POSITION_OPEN`) | Terlihat di trade hilang (`trade_diff`) dan syarat ≥ 90% trade | 1.3 |
| EC-03 | Target zona lawan > 9R | BE/partial tetap terpicu; dicatat jumlahnya | 1.2 |
| EC-04 | Gap akhir pekan saat posisi lama terbuka | Dihitung apa adanya | 1.2 |

## Keputusan (2026-10-13)

1. Tiga varian V1 murni, V2 tanpa partial, V3 BE 1,5R tanpa partial.
2. Batas DD IS ≤ 1,5× acuan (≤ 9,8R).
