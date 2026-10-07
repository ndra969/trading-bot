# Requirements — Aktivasi komponen dan kalibrasi ambang (Fase 5 selesai)

Status: Done (2026-10-08)
Use case: UC-57 ([fase-5-overview.md](../fase-5-overview.md))
Asal: PRD-EA §Skor konfluensi (komponen ditambah satu per satu, terbukti meningkatkan forward test; ambang 65 ditentukan ulang lewat backtest), §Pengujian (tahap 2–3), PC-25 (aturan aktivasi), PC-15 (filter candle klimaks), PRD §Temuan review (mode entry Adaptive); hasil spec 18–21
Butuh: spec 21, perbaikan 1.24

## Pendahuluan

Spec ini menutup Fase 5. Isinya:
- memutuskan komponen konfirmasi mana yang diaktifkan dengan data IS, OOS, dan real ticks;
- menyetel ulang ambang skor gerbang untuk maksimum skor yang baru;
- memperbarui preset;
- membuktikan bahwa konfigurasi akhir tidak lebih buruk dari acuan di OOS.

Komponen yang tidak terbukti tetap dicatat dalam mode bayangan untuk pengumpulan data live di Fase 6.

Data spec 18–21 (OHLC M1, sesi DB 964–1180):

| Komponen | IS, nilai > 0 vs 0 | OOS, nilai > 0 vs 0 | Kesan |
|---|---|---|---|
| Breakout & retest | 189 trade +0,097R vs 304 −0,014R | 14 +0,356R vs 38 −0,083R | konsisten |
| Fibonacci | 101 ~+0,015R vs 392 +0,032R | 15 ~+0,57R vs 37 −0,152R | tidak konsisten |
| Trendline | 294 ~+0,018R vs 199 +0,045R | 30 ~−0,29R vs 22 +0,476R | terbalik |
| RSI divergence | 16 −0,274R vs 477 +0,039R | 2 vs 50 | terlalu jarang |

Masalahnya: OOS 3 bulan hanya 52 trade, sehingga aturan PC-25 (≥ 20 trade per kelompok di IS **dan** OOS) tidak pernah terpenuhi.

Di luar lingkup: tuning exit (BE, partial, trailing), komponen baru, dan live akun cent (Fase 6).

Bukti selesai:
- backtest IS, OOS, dan REAL dengan konfigurasi akhir tercatat;
- OOS tidak lebih buruk dari acuan v1.24;
- preset diperbarui;
- PC baru untuk perubahan aturan aktivasi dan ambang;
- Fase 5 Done.

## Requirements

### Requirement 1: Aturan aktivasi yang bisa dipenuhi
**User story:** Sebagai developer, saya ingin aturan aktivasi yang memakai kelompok "bernilai > 0" vs "0" dan ambang sampel yang realistis untuk OOS 3 bulan, agar keputusan bisa diambil dari data, bukan selalu "sampel kurang".

#### Acceptance criteria
1. Laporan komponen WAJIB membandingkan kelompok nilai > 0 dengan kelompok nilai 0 (R per trade), di IS dan OOS.
2. Komponen WAJIB berstatus TERBUKTI hanya bila kelompok > 0 lebih baik dari kelompok 0 di IS **dan** OOS, dengan sampel minimum per kelompok IS ≥ 50 dan OOS ≥ 10 trade.
3. Komponen TERBUKTI WAJIB juga tidak memburuk di periode REAL (real ticks 2026-01..10): kelompok > 0 tidak lebih buruk dari kelompok 0.
4. Status aturan baru WAJIB tercetak di `component_report.py`; aturan lama tetap bisa dipilih lewat opsi.

### Requirement 2: Konfigurasi aktif
**User story:** Sebagai trader, saya ingin hanya komponen yang terbukti yang ikut skor gerbang, sedangkan sisanya tetap dicatat, agar entry membaik tanpa membuang data untuk evaluasi di live.

#### Acceptance criteria
1. Komponen berstatus TERBUKTI WAJIB diset ACTIVE di preset 12 simbol. Komponen lain tetap SHADOW.
2. Default input EA WAJIB mengikuti preset, sehingga EA tanpa preset berperilaku sama.
3. Bila tidak ada komponen yang TERBUKTI, semua tetap SHADOW, keputusan ini dicatat, dan Fase 5 tetap selesai (PC-25).

### Requirement 3: Ambang skor gerbang
**User story:** Sebagai trader, saya ingin ambang `MinConfluenceScore` disetel ulang setelah maksimum skor berubah, agar jumlah trade dan kualitasnya tetap terkendali.

#### Acceptance criteria
1. Ambang WAJIB dipilih hanya dari data IS, dari kandidat ambang yang ditetapkan sebelum melihat OOS.
2. Ambang terpilih WAJIB memenuhi kriteria jumlah trade backtest dasar PC-22 di IS (≥ 200 trade, ≥ 10 per simbol, dihitung untuk 12 bulan setara).
3. Hasil ambang terpilih di OOS WAJIB dicatat apa adanya. Ambang tidak boleh diubah lagi setelah melihat OOS.

### Requirement 4: Validasi akhir
**User story:** Sebagai trader, saya ingin bukti bahwa konfigurasi akhir tidak lebih buruk dari acuan, sebelum Fase 6 di akun cent.

#### Acceptance criteria
1. Backtest `-Period ALL` dan `-Period REAL` WAJIB dijalankan dengan konfigurasi akhir.
2. PF OOS konfigurasi akhir WAJIB ≥ PF OOS acuan v1.24 (OHLC M1). JIKA tidak terpenuhi MAKA konfigurasi kembali ke semua SHADOW, dan temuan WAJIB dibahas.
3. Status kriteria PRD tahap 2 dan 3 WAJIB dicatat apa adanya, termasuk bila PF belum mencapai 1,3.

### Requirement 5: Keputusan tertunda Fase 5
**User story:** Sebagai trader, saya ingin keputusan tentang filter candle klimaks dan mode entry Adaptive/Limit dicatat jelas, agar tidak hilang.

#### Acceptance criteria
1. Spec WAJIB mencatat keputusan untuk filter candle klimaks (PC-15) dan mode entry Adaptive/Limit: diterapkan di spec ini, ditunda ke Fase 6 dengan data live, atau dibatalkan, beserta data yang mendasarinya.

### Requirement 6: Dokumen dan Fase 5 selesai
**User story:** Sebagai developer, saya ingin dokumen dan PRD mencerminkan keputusan akhir Fase 5.

#### Acceptance criteria
1. PC baru WAJIB mencatat aturan aktivasi baru, komponen aktif, dan ambang baru untuk PRD-EA §Skor konfluensi dan §Parameter input.
2. `fase-5-overview.md`, README spec, README EA, dan CHANGELOG WAJIB ditandai Fase 5 selesai.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Komponen lolos IS dan OOS tetapi memburuk di REAL | Tidak TERBUKTI | 1.3 |
| EC-02 | Tidak ada komponen TERBUKTI | Semua SHADOW, ambang tetap 65% dari 55 | 2.3 |
| EC-03 | Ambang terbaik IS memotong trade di bawah PC-22 | Ambang itu tidak dipakai | 3.2 |
| EC-04 | Konfigurasi akhir lebih buruk dari acuan di OOS | Kembali semua SHADOW, dibahas | 4.2 |
| EC-05 | XAU di periode REAL memakai tick buatan sebelum 2026-08-14 | Ditandai di laporan, tidak membatalkan keputusan | 1.3 |

## Pertanyaan terbuka

- Ambang sampel IS ≥ 50 dan OOS ≥ 10 per kelompok (usulan)? Alternatif: OOS diperpanjang ke belakang (misalnya 2026-04..2026-10, 6 bulan), dengan IS dipendekkan.
- Kandidat ambang `MinConfluenceScore` yang diuji di IS: 55 / 60 / 65 / 70% (usulan; 4 run IS, sekitar 4 jam)?
- Komponen yang tidak terbukti: tetap SHADOW di live untuk data (usulan), atau OFF agar backtest lebih cepat (trendline menambah sekitar 35% waktu backtest)?
- Filter candle klimaks dan mode entry Adaptive/Limit: tunda ke Fase 6 dengan data live (usulan; data Fase 3–5 belum menunjukkan masalah entry terlambat yang spesifik)?
