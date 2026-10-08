# Requirements — Entry hanya dari zona Fresh (H1)

Status: Approved (2026-10-08)
Use case: UC-60, UC-63 ([fase-5b-overview.md](../fase-5b-overview.md))
Asal: PRD-EA §Aturan zona Supply & Demand (Fresh 30, Tested 15; ≥ 2 sentuhan tidak dipakai), §Skor konfluensi; PC-28 (aturan uji Fase 5b); diagnosis Fase 5 (Fresh +0,041 / +0,157 / +0,030R; Tested +0,001 / −0,264 / −0,216R di IS / OOS / REAL)
Butuh: spec 22 (alat IS/OOS/REAL, `-SetInput`), perbaikan 1.24

## Pendahuluan

Spec ini menguji hipotesis H1: entry hanya dari zona yang belum pernah disentuh (Fresh) memperbaiki hasil.

- Spec menambah input yang menolak kandidat dari zona Tested, mencatat penolakan itu di telemetri, lalu mengukur hasilnya di IS, OOS, dan REAL dengan aturan uji PC-28.
- Bila H1 diterima, default dan preset berubah (zona Tested tidak dipakai) dan PRD diperbarui. Bila ditolak, default tetap memakai zona Tested.

Di luar lingkup: perubahan definisi zona, umur zona, atau bobot skor zona.

Bukti selesai:
- suite unit ALL PASS;
- skenario SC-22 PASS;
- backtest IS, OOS, dan REAL dengan input baru tercatat;
- keputusan H1 diterima atau ditolak beserta datanya.

## Requirements

### Requirement 1: Input zona Tested
**User story:** Sebagai trader, saya ingin bisa menolak entry dari zona yang sudah pernah disentuh, agar hanya zona dengan reaksi pertama yang dipakai.

#### Acceptance criteria
1. Input `InpAllowTestedZones` (bool) WAJIB mengatur apakah zona Tested boleh menghasilkan entry. Default sementara `true` (perilaku sekarang); default akhir mengikuti keputusan Req 3.
2. SELAMA `InpAllowTestedZones = false`, kandidat yang zonanya berstatus Tested WAJIB ditolak dengan tahap `NO_VALID_ZONE` dan detail yang menyebut status zona.
3. Penolakan zona Tested WAJIB dinilai sesudah pre-filter risiko (STOPPED, pause harian, tidak bisa trading) dan sebelum filter berita, sesi, dan spread, agar urutan tahap tetap sesuai PRD (zona valid adalah gerbang).
4. Zona Fresh WAJIB tetap dipilih lebih dulu bila bar menyentuh zona Fresh dan Tested sekaligus (aturan Fase 3). Input ini tidak mengubah pemilihan zona.
5. Kandidat yang ditolak WAJIB tetap dicatat di `signals` dengan skor lengkap, termasuk komponen bayangan, agar analisis tidak kehilangan data.

### Requirement 2: Pengukuran IS/OOS/REAL
**User story:** Sebagai developer, saya ingin efek H1 diukur dengan aturan uji PC-28, agar keputusan berdasar data.

#### Acceptance criteria
1. Backtest `-Period IS` dengan `InpAllowTestedZones=false` WAJIB dibandingkan dengan acuan v1.24 (IS sesi 1157–1168): trade, R per trade, PF, DD.
2. Kriteria jumlah trade Fase 5b WAJIB diperiksa: IS ≥ 325 trade dan ≥ 13 per simbol.
3. Bila IS lebih baik dalam R per trade dan memenuhi jumlah trade, OOS dan REAL WAJIB dijalankan dan dibandingkan dengan acuan (OOS 1169–1180, REAL 1260–1271).
4. Semua hasil WAJIB dicatat di spec dan CHANGELOG, termasuk bila H1 ditolak.

### Requirement 3: Keputusan
**User story:** Sebagai trader, saya ingin aturan yang jelas kapan H1 diterapkan.

#### Acceptance criteria
1. H1 DITERIMA bila R per trade IS > acuan, jumlah trade memenuhi Req 2.2, dan R per trade OOS serta REAL ≥ acuan masing-masing.
2. Bila DITERIMA: default `InpAllowTestedZones = false`, preset 12 simbol diperbarui, dan PC baru untuk PRD §Aturan zona.
3. Bila DITOLAK: default tetap `true`, preset tidak berubah; input tetap ada untuk eksperimen.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Bar menyentuh zona Fresh dan Tested sekaligus | Zona Fresh dipilih, kandidat tidak ditolak | 1.4 |
| EC-02 | Zona Tested dengan skor tinggi | Tetap ditolak bila input false | 1.2 |
| EC-03 | STOPPED aktif dan zona Tested | Tahap `STOPPED` (pre-filter lebih dulu) | 1.3 |
| EC-04 | Zona Tested dan sedang news blackout | Tahap `NO_VALID_ZONE` (zona lebih dulu dari berita) | 1.3 |
| EC-05 | Input berubah antar sesi | `inputs_json` mencatat nilai, laporan bisa membedakan run | 1.1 |
| EC-06 | Jumlah trade IS turun di bawah 325 | H1 ditolak karena jumlah, dicatat | 2.2, 3.1 |

## Pertanyaan terbuka

- Tahap tolak `NO_VALID_ZONE` (usulan; enum sudah ada di skema, tanpa migrasi) atau tahap baru `ZONE_TESTED` (butuh skema v5)?
