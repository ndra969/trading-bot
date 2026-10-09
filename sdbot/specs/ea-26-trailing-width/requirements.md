# Requirements — Trailing lebih longgar (H4)

Status: Done (2026-10-09)
Use case: UC-61, UC-63 ([fase-5b-overview.md](../fase-5b-overview.md) §7, kandidat sesudah Fase 5b)
Asal: PRD-EA §Position management (trailing ATR(14) × 2 sesudah breakeven aktif), §Parameter input (`TrailATRPeriod` / `TrailATRMult`); PC-28 (aturan uji); temuan spec 24
Butuh: spec 23 (acuan v1.25); spec 24 dan 25 ditolak, jadi acuan tetap konfigurasi 1.25 (EA 1.26 dengan default yang sama)

## Pendahuluan

Spec ini menguji hipotesis H4: trailing yang lebih longgar membiarkan winner berjalan lebih jauh dan menaikkan R per trade.

Dasarnya dari data v1.25 (IS, sesi 1396–1407) dan kode:
- **Trailing memakai ATR(14) M15 × 2.** Jarak SL awal rata-rata (median) 1,13 × ATR H1. ATR M15 kira-kira setengah ATR H1, jadi jarak trailing sekitar 0,9R dari harga. Koreksi normal M15 sudah cukup untuk menyentuh SL trailing.
- **Trade TRAIL_STOP (97)** sempat mencapai MFE rata-rata +1,62R, tapi hanya terealisasi +0,90R (sudah termasuk partial 1,5R). Hanya 12 yang mencapai 2R. Pola yang sama muncul di OOS (MFE +1,69, realisasi +1,13) dan REAL (+1,57 → +0,87).
- **Trade TP (45)** rata-rata +1,93R. Trade yang dibiarkan berjalan sampai zona lawan hasilnya jauh lebih baik.
- **Spec 24 menunjukkan efek sebaliknya.** Pada 67 trade yang sama-sama ditutup trailing, BE 0,5R membuat trailing aktif lebih awal dan hasilnya 15,5R lebih buruk. Contoh: XAUUSDc 2026-06-04, acuan +1,42R, BE 0,5 +0,09R.

Input `InpTrailATRMult` sudah ada (PRD: 2.0). Spec ini mengukur nilai yang lebih longgar tanpa mengubah kode, sama seperti spec 24.

Di luar lingkup:
- timeframe ATR trailing (tetap M15);
- pemicu trailing terpisah dari BE (butuh kode; bisa menjadi spec lanjutan bila H4 ditolak);
- perubahan partial, BE, dan TP.

Bukti selesai:
- backtest IS untuk tiap varian tercatat;
- varian terpilih diuji di OOS dan REAL;
- keputusan H4 diterima atau ditolak beserta datanya.

## Glosarium

- **Acuan**: konfigurasi 1.25 (`InpTrailATRMult` 2,0). Sesinya: IS 1396–1407, OOS 1408–1419, REAL 1420–1431.
- **Varian**: nilai `InpTrailATRMult` yang diuji, yaitu 3,0 dan 4,0.
- **Give-back**: MFE dikurangi R hasil pada trade yang ditutup trailing.

## Requirements

### Requirement 1: Pengukuran IS
**User story:** Sebagai developer, saya ingin lebar trailing diukur dengan aturan yang sama dengan spec sebelumnya, agar pilihan tidak bergantung pada OOS.

#### Acceptance criteria
1. Backtest `-Period IS` WAJIB dijalankan untuk `InpTrailATRMult` 3,0 dan 4,0, dengan konfigurasi lain sama dengan acuan.
2. Setiap varian WAJIB dilaporkan dengan:
   - trade, R per trade, PF, DD, dan jumlah per simbol (`baseline_report.py`);
   - sebaran alasan tutup dengan R rata-rata (`exit_report.py`);
   - MFE rata-rata dan give-back rata-rata trade TRAIL_STOP.
3. Varian terpilih WAJIB ditentukan hanya dari IS, dengan aturan yang ditulis di design sebelum OOS dijalankan.
4. Varian terpilih WAJIB memiliki R per trade IS lebih tinggi dari acuan dan memenuhi kriteria jumlah trade Fase 5b (IS ≥ 325 trade, ≥ 13 per simbol). Trailing tidak mengubah entry, jadi jumlah trade seharusnya hampir sama.
5. JIKA tidak ada varian yang lolos, MAKA H4 WAJIB ditolak tanpa OOS dan REAL.

### Requirement 2: Konfirmasi dan keputusan
**User story:** Sebagai trader, saya ingin trailing diubah hanya bila terbukti di data yang tidak dipakai menyetel.

#### Acceptance criteria
1. Varian terpilih WAJIB dijalankan sekali di OOS dan sekali di REAL, lalu dibandingkan dengan acuan.
2. H4 DITERIMA bila R per trade OOS dan REAL ≥ acuan masing-masing.
3. Bila DITERIMA:
   - default `InpTrailATRMult` dan preset 12 simbol berubah;
   - uji yang memeriksa default diperbarui;
   - versi EA naik ke 1.27;
   - PC baru untuk PRD §Position management dan §Parameter input.
4. Bila DITOLAK: default tetap 2,0, preset dan versi tidak berubah.
5. Semua hasil WAJIB dicatat di spec dan CHANGELOG.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Trailing lebih longgar membuat kandidat trailing lebih jarang melewati titik BE | SL tetap di BE sampai trailing lebih baik (aturan `PickBestSl` yang ada); terlihat sebagai pergeseran TRAIL_STOP ke BE_STOP atau TP | 1.2 |
| EC-02 | Winner yang sebelumnya keluar lewat trailing berbalik sampai BE | Ditutup di BE (sekitar +0,25R termasuk partial); dihitung apa adanya | 1.2 |
| EC-03 | Total risiko terbuka: posisi yang sudah BE dihitung 0% (PRD) | Tidak berubah; trailing longgar tidak menambah risiko di atas BE | 1.1 |
| EC-04 | Posisi bertahan lebih lama dan melewati akhir pekan | Gap tetap mungkin; dihitung apa adanya | 1.2 |
| EC-05 | Selisih R per trade dua varian sangat kecil | Aturan pilih di design menentukan satu varian | 1.3 |

## Pertanyaan terbuka

- Grid 3,0 dan 4,0 cukup? Usulan saya cukup. 3,0 kira-kira 1,3R dari harga, 4,0 kira-kira 1,8R, keduanya masih di bawah TP rata-rata (≈ 2R).
- Bila H4 ditolak, apakah pemicu trailing terpisah (misalnya trailing baru mulai sesudah partial 1,5R) dijadikan spec 27? Usulan saya diputuskan sesudah melihat hasil H4.
