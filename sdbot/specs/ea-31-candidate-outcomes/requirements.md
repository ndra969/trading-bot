# Requirements — Hasil kandidat dan faktor profit

Status: Approved (2026-10-09)
Use case: UC-80, UC-81, UC-83 ([fase-5c-overview.md](../fase-5c-overview.md))
Asal: PRD-EA §Telemetri sinyal (`context_json`), §Aturan entry (SL di luar zona + buffer, TP ke zona lawan, R:R ≥ 2), §Position management (BE 1R, partial 1,5R 50%, trailing ATR(14) × 2), §Pengujian; `python-bot-lessons.md` (skor tidak prediktif); permintaan user 2026-10-09
Butuh: spec 27 (selesai; acuan konfigurasi tergantung keputusan H5)

## Pendahuluan

Spec ini membangun alat untuk menjawab dua pertanyaan dengan data:
- faktor apa yang konsisten membuat trade untung atau rugi;
- apakah gerbang EA membuang kandidat yang sebenarnya bagus.

Sekarang `context_json` baru berisi entry/SL/TP bila kandidat lolos sampai tahap SL/TP. Kandidat yang ditolak lebih awal (PA, skor, berita, sesi, spread, zona TESTED) tidak punya SL, jadi hasilnya tidak bisa dihitung. Spec ini menambah harga yang dibutuhkan ke `context_json`, lalu mensimulasikan setiap kandidat dengan aturan exit EA di atas bar M1.

Simulasi baru boleh dipakai bila hasilnya cocok dengan trade nyata backtest (kalibrasi).

Di luar lingkup:
- perubahan keputusan entry atau exit EA;
- simulasi interaksi antar posisi (batas 1 posisi per instance, eksposur mata uang, risiko terbuka). Setiap kandidat dihitung sendiri-sendiri;
- data live (Fase 6).

Bukti selesai:
- suite unit dan regresi `-All` PASS dengan keputusan entry identik;
- pytest PASS;
- kalibrasi simulator lolos di IS, OOS, dan REAL;
- laporan faktor dan laporan per tahap tolak untuk IS, OOS, dan REAL tercatat di spec.

## Glosarium

- **Kandidat**: baris `signals` (diterima maupun ditolak).
- **Hasil hipotetis**: R yang akan didapat kandidat bila dientry pada bar sesudahnya dengan aturan exit EA.
- **Kalibrasi**: membandingkan hasil hipotetis kandidat yang diterima dengan R nyata di `closures`.
- **Bucket faktor**: kelompok trade menurut satu faktor, misalnya status zona Fresh atau Tested.
- **Konsisten**: selisih R per trade bucket terhadap rata-rata periode searah di IS, OOS, dan REAL, masing-masing dengan ≥ 10 trade.

## Requirements

### Requirement 1: Telemetri harga kandidat
**User story:** Sebagai developer, saya ingin setiap kandidat membawa harga yang cukup untuk menghitung SL dan TP, agar kandidat yang ditolak bisa disimulasikan.

#### Acceptance criteria
1. EA WAJIB menambah ke `context_json` setiap kandidat:
   - `zone_prox` dan `zone_dist` (batas proximal dan distal zona);
   - `opp_prox` (proximal zona lawan, `null` bila tidak ada);
   - `bid` dan `ask` saat kandidat dinilai.
2. Nilai WAJIB dinormalisasi ke digit simbol, dengan format kanonik yang sama dengan kunci lain.
3. Keputusan, tahap tolak, skor, dan trade WAJIB identik dengan versi sebelumnya untuk data yang sama.
4. Skema DB WAJIB tidak berubah (kunci baru hanya di teks JSON).

### Requirement 2: Simulator hasil
**User story:** Sebagai developer, saya ingin hasil hipotetis setiap kandidat dihitung dengan aturan exit EA, agar kandidat yang ditolak bisa dibandingkan dengan trade nyata.

#### Acceptance criteria
1. Simulator WAJIB memakai aturan entry EA:
   - entry market pada harga ask (BUY) atau bid (SELL) kandidat;
   - SL = distal zona ∓ 0,1 × ATR MTF (SELL ditambah spread);
   - TP = proximal zona lawan, atau 2R bila tidak ada.
2. Simulator WAJIB memakai aturan exit EA dari input sesi:
   - SL dan TP;
   - BE di 1R dengan buffer 2 point;
   - partial 50% di 1,5R;
   - trailing ATR(14) M15 × 2 sesudah BE aktif;
   - SL hanya bergerak ke arah menguntungkan.
3. Harga keluar WAJIB memperhitungkan spread kandidat: BUY keluar di bid, SELL di ask.
4. JIKA SL dan TP (atau SL dan level BE/partial) tersentuh di bar M1 yang sama, MAKA simulator WAJIB menganggap kejadian yang merugikan lebih dulu.
5. Simulator WAJIB mencatat untuk setiap kandidat: R hipotetis, alasan tutup, MFE, dan apakah kandidat lolos aturan SL min/max dan R:R ≥ 2.
6. JIKA kandidat tidak punya `zone_prox`/`zone_dist` (data sebelum versi baru) atau bar tidak tersedia, MAKA kandidat WAJIB dilewati dan jumlahnya dicetak.
7. Posisi yang belum tutup sampai akhir periode WAJIB ditutup di close bar terakhir dan ditandai.

### Requirement 3: Kalibrasi
**User story:** Sebagai trader, saya ingin tahu simulasi bisa dipercaya sebelum memakainya untuk keputusan.

#### Acceptance criteria
1. Kalibrasi WAJIB mensimulasikan semua trade nyata backtest acuan dan membandingkannya dengan `closures`.
2. Kalibrasi WAJIB melaporkan:
   - persen trade dengan alasan tutup sama;
   - selisih R rata-rata dan selisih R absolut rata-rata;
   - R per trade nyata vs simulasi per periode.
3. Simulator dianggap lolos bila di setiap periode (IS, OOS, REAL):
   - ≥ 85% alasan tutup sama;
   - selisih R absolut rata-rata ≤ 0,15R;
   - selisih R per trade agregat ≤ 0,03R.
4. JIKA kalibrasi tidak lolos, MAKA laporan faktor dan per tahap tolak WAJIB tidak dipakai untuk keputusan sampai sebabnya diperbaiki atau dijelaskan.

### Requirement 4: Laporan faktor profit
**User story:** Sebagai trader, saya ingin tahu mengapa trade untung atau rugi, agar perbaikan berikutnya didasarkan pada sebab.

#### Acceptance criteria
1. Laporan WAJIB memuat, untuk trade nyata dan untuk kandidat yang disimulasikan, R per trade dan jumlah per bucket faktor:
   - status zona;
   - trendline (tanpa garis, 2 sentuhan, 3+ sentuhan) dan jarak ke garis;
   - pola PA;
   - jam UTC dan sesi;
   - persen skor;
   - alasan bias;
   - arah;
   - R:R rencana dan sumber TP;
   - rezim ATR (tersier dari ATR MTF per simbol);
   - simbol.
2. Laporan WAJIB menandai setiap bucket KONSISTEN+ / KONSISTEN− / TIDAK KONSISTEN / SAMPEL KURANG menurut definisi glosarium.
3. Laporan WAJIB bisa dibuat untuk rentang sesi apa pun dan beberapa periode sekaligus.

### Requirement 5: Laporan per tahap tolak
**User story:** Sebagai trader, saya ingin tahu apakah gerbang membuang trade bagus, agar tahu apakah EA terlalu ketat.

#### Acceptance criteria
1. Laporan WAJIB menampilkan per tahap tolak: jumlah kandidat, jumlah tersimulasi, R per trade hipotetis, PF hipotetis, dan persen yang lolos aturan SL/R:R.
2. Laporan WAJIB menampilkan kandidat ACCEPTED (hipotetis dan nyata) sebagai pembanding.
3. Kandidat beruntun dari zona yang sama dalam satu episode WAJIB bisa dihitung sekali (opsi dedup: kandidat pertama per zona per hari), karena EA hanya mengambil satu entry per zona.

### Requirement 6: Backtest ulang dengan telemetri
**User story:** Sebagai developer, saya ingin data acuan memuat kunci baru, agar semua kandidat bisa disimulasikan.

#### Acceptance criteria
1. Backtest acuan WAJIB dijalankan ulang untuk IS, OOS, dan REAL dengan versi baru dan konfigurasi acuan.
2. Jumlah trade dan R per trade backtest ulang WAJIB identik dengan acuan sebelumnya (bukti Req 1.3).
3. Hasil kalibrasi dan kedua laporan WAJIB dicatat di spec dan ringkasan temuannya di `fase-5c-overview.md`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Kandidat SELL: SL di atas distal + buffer + spread | Sama dengan `BuildStops` | 2.1 |
| EC-02 | Harga JPY (3 digit) dan XAU (2 digit) | Normalisasi ke digit simbol; R dihitung dari jarak harga, tidak bergantung digit | 1.2, 2.1 |
| EC-03 | SL dan TP di bar M1 yang sama | Dihitung SL (konservatif) | 2.4 |
| EC-04 | Gap akhir pekan melewati SL | Keluar di harga open bar sesudah gap, R bisa < −1 | 2.2 |
| EC-05 | Kandidat ditolak di tahap sebelum zona lawan dicari | `opp_prox` tetap dicatat; bila tidak ada, TP 2R | 1.1, 2.1 |
| EC-06 | Kandidat tidak lolos SL min/max atau R:R | Tetap disimulasikan, ditandai tidak lolos aturan | 2.5 |
| EC-07 | Kandidat beruntun 15 menit sekali di zona yang sama | Dedup opsional per zona per hari | 5.3 |
| EC-08 | Data lama tanpa kunci baru | Dilewati dan dihitung | 2.6 |
| EC-09 | Periode REAL (real ticks) disimulasikan dengan bar M1 | Kalibrasi REAL menunjukkan besar selisihnya | 3.3 |
| EC-10 | Bucket dengan < 10 trade di salah satu periode | SAMPEL KURANG | 4.2 |
| EC-11 | Posisi masih terbuka di akhir periode | Ditutup di close terakhir, ditandai | 2.7 |

## Keputusan (2026-10-09)

1. Ambang kalibrasi: ≥ 85% alasan tutup sama, selisih R absolut rata-rata ≤ 0,15R, selisih R per trade agregat ≤ 0,03R, per periode.
2. Bar M1 diekspor script EA di terminal uji ke CSV Common/Files (data sama dengan tester).
3. Konfigurasi acuan mengikuti keputusan spec 27 (1.25 bila H5 ditolak).
