# Requirements — Entry hanya dengan TP ke zona lawan (H6)

Status: Done (2026-10-12)
Use case: UC-83 ([fase-5c-overview.md](../fase-5c-overview.md) §7, perbaikan dari temuan spec 31)
Asal: PRD-EA §Aturan entry ("TP ke zona lawan lalu cek R:R ≥ 2"; tanpa zona lawan TP = 2R), §Parameter input; PC-28 (aturan uji Fase 5b); temuan spec 31 (`factor_report.py`, `outcome_sim.py`)
Butuh: spec 31 (selesai). Acuan = konfigurasi 1.28 (EMA bias 21), EA 1.29 dengan default yang sama

## Pendahuluan

Spec ini menguji hipotesis H6: entry yang targetnya zona lawan lebih baik daripada entry dengan TP 2R tetap, jadi entry tanpa zona lawan sebaiknya tidak diambil.

Sekarang EA mencari zona lawan searah TP. Kalau ada, TP = proximal zona itu dan R:R harus ≥ 2. Kalau tidak ada, TP = 2R.

Data acuan 1.28 (trade nyata, R per trade):

| Sumber TP | IS | OOS | REAL |
|---|---|---|---|
| Zona lawan | 121 trade, +0,161 | 21, +0,422 | 55, +0,224 |
| 2R tetap | 235, +0,036 | 20, −0,109 | 71, −0,031 |

Simulasi spec 31 menunjukkan bahwa menaikkan TP trade tanpa zona lawan ke 2,5R, 3R, atau 4R tidak memperbaiki hasil (IS −0,009 s/d +0,004; REAL −0,04 s/d −0,06). Jadi varian yang diuji adalah menolak trade tanpa zona lawan, bukan mengubah R:R.

Perkiraan dari data yang ada:

| | IS | OOS | REAL |
|---|---|---|---|
| R per trade | +0,079 → +0,161 | +0,163 → +0,422 | +0,080 → +0,224 |
| Total R | +28,0 → +19,5 | +6,7 → +8,9 | +10,1 → +12,3 |
| Jumlah trade | 356 → 121 | 41 → 21 | 126 → 55 |

Perkiraan ini belum memperhitungkan efek urutan. Trade yang tidak diambil membebaskan posisi dan zona untuk kandidat lain, jadi angka sebenarnya diukur dengan backtest EA.

Di luar lingkup:
- TP ke struktur HTF (swing H1/H4) sebagai pengganti 2R; butuh kode dan analisis sendiri;
- perubahan R:R minimum ke zona lawan (tetap 2,0);
- partial, BE, dan trailing.

Bukti selesai:
- suite unit dan regresi PASS, default identik dengan acuan;
- backtest IS/OOS/REAL tercatat;
- keputusan H6 diterima atau ditolak beserta datanya.

## Glosarium

- **Zona lawan**: zona Supply (untuk BUY) atau Demand (untuk SELL) terdekat di arah TP, sesuai aturan `OppositeZone` yang ada.
- **TP 2R**: TP = entry ± 2 × risiko, dipakai saat tidak ada zona lawan (`tp_source = RR`).
- **Acuan**: konfigurasi 1.28. Sesinya: IS 1848–1859, OOS 1860–1871, REAL 1872–1883 (EA 1.29, trade identik dengan 1.28).

## Requirements

### Requirement 1: Input syarat zona lawan
**User story:** Sebagai trader, saya ingin bisa mewajibkan zona lawan sebagai TP, agar EA hanya entry saat target jelas.

#### Acceptance criteria
1. Input `InpRequireOppositeZone` (bool) WAJIB tersedia. Default `false`, yaitu perilaku sekarang.
2. BILA `true` dan tidak ada zona lawan, MAKA kandidat WAJIB ditolak di tahap SL/TP dengan tahap tolak yang sudah ada `RR_TOO_LOW`. Detailnya menyebut "tanpa zona lawan". Skema dan enum tidak berubah.
3. BILA `true` dan zona lawan ada, MAKA perilaku WAJIB sama dengan sekarang (TP = proximal zona lawan, R:R ≥ `InpMinRR`).
4. BILA `false`, MAKA kandidat, trade, dan detail tolak WAJIB identik dengan acuan.
5. `inputs_json` WAJIB memuat input ini (57 kunci).
6. Posisi yang sudah terbuka WAJIB tidak terpengaruh.

### Requirement 2: Pengukuran IS
**User story:** Sebagai developer, saya ingin H6 diukur dengan aturan yang sama dengan spec sebelumnya.

#### Acceptance criteria
1. Backtest `-Period IS` WAJIB dijalankan dengan `InpRequireOppositeZone=true`, konfigurasi lain sama dengan acuan.
2. Laporan WAJIB memuat:
   - trade, R per trade, total R, PF, DD, dan jumlah per simbol;
   - alasan tutup (`exit_report.py`);
   - trade sama, baru, dan hilang (`trade_diff.py`).
3. Varian lolos IS bila R per trade > acuan (+0,079) **dan** memenuhi kriteria jumlah trade khusus H6: IS ≥ 100 trade dan ≥ 5 trade per simbol (keputusan 1).
4. JIKA tidak lolos, MAKA H6 WAJIB ditolak tanpa OOS dan REAL.

### Requirement 3: Konfirmasi dan keputusan
**User story:** Sebagai trader, saya ingin syarat ini dipakai hanya bila terbukti di data yang tidak dipakai menyetel.

#### Acceptance criteria
1. Bila lolos IS, varian WAJIB dijalankan sekali di OOS dan sekali di REAL.
2. H6 DITERIMA bila R per trade OOS dan REAL ≥ acuan **dan** total R REAL ≥ acuan (+10,1R). Syarat total R ditambahkan agar perbaikan tidak hanya berasal dari membuang trade.
3. Bila DITERIMA:
   - default `true` dan preset 12 simbol;
   - versi EA 1.31;
   - PC untuk PRD §Aturan entry dan §Parameter input.
4. Bila DITOLAK: default `false`, input tetap ada di 1.30 untuk eksperimen.
5. Semua hasil WAJIB dicatat di spec, CHANGELOG, dan `fase-5c-overview.md`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Zona lawan ada tetapi R:R ke zona < 2 | `RR_TOO_LOW` seperti sekarang (tidak berubah) | 1.3 |
| EC-02 | Tidak ada zona lawan, input `true` | `RR_TOO_LOW`, detail "tanpa zona lawan" | 1.2 |
| EC-03 | Tidak ada zona lawan, input `false` | TP 2R seperti sekarang | 1.4 |
| EC-04 | Zona lawan menjadi Used/Invalid sesudah entry | TP posisi tidak berubah (TP dipasang saat entry) | 1.6 |
| EC-05 | Trade lebih sedikit membebaskan slot posisi | Kandidat berikutnya bisa masuk; terlihat sebagai trade baru di `trade_diff` | 2.2 |
| EC-06 | Simbol dengan sedikit zona lawan (mis. tren kuat) | Trade simbol itu turun tajam; kriteria per simbol menentukan | 2.3 |

## Keputusan (2026-10-12)

1. Kriteria jumlah trade khusus H6 (opsi A): IS ≥ 100 trade dan ≥ 5 per simbol; keputusan tetap dari OOS dan REAL. Dicatat sebagai PC bersama hasil spec.
2. Frekuensi live sekitar 0,2 trade per hari diterima bila H6 lolos.
3. Tahap tolak memakai `RR_TOO_LOW` yang ada dengan detail "tanpa zona lawan"; skema dan enum tidak berubah.
