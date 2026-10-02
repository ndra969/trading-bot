# Requirements — 11 Zona Supply & Demand

Status: Done (2026-10-02)
Use case: UC-32, UC-33 ([overview](../fase-3-overview.md))
Asal: PRD-EA §Aturan zona Supply & Demand, §Skor konfluensi (kualitas zona 30), §Eksekusi order (SL dari batas jauh zona, TP ke zona lawan), §Temuan review (zona Fresh tertinggi, zona valid gerbang wajib); python-bot-lessons §4 (zona tidak dimuat dari DB); PC-15 (ukuran relatif ATR); spec 10 (swing, bar tertutup)
Butuh: spec 10

## Pendahuluan

Spec ini membangun peta zona Supply & Demand di MTF (H1 untuk day trading): deteksi dari swing terkonfirmasi, filter ukuran dan kekuatan keluar relatif ATR, status Fresh / Tested / Lemah / Invalid / Kedaluwarsa / Used, ID deterministik, dan pembangunan ulang dari histori setiap bar MTF baru (sehingga restart memberi hasil sama). Spec ini juga menyediakan komponen skor kualitas zona dan pencarian zona untuk pipeline sinyal (zona yang disentuh harga, zona lawan untuk TP). Belum ada sinyal atau order (spec 13).

Selesai jika suite ZoneRules ALL PASS, SC-13 membuktikan peta zona selama run sama dengan peta yang dibangun ulang dari histori (termasuk setelah restart) dan status Used bertahan lintas restart, regresi tetap PASS, dan EA naik ke `1.10`.

## Ukuran dari histori (dasar default)

H1, 2025-10-01 s.d. 2026-10-01, 12 simbol, swing kekuatan 2, ATR(14) Wilder di bar swing. Hasilnya hampir sama untuk semua simbol (forex, logam, BTC), jadi satu set default berlaku untuk semua:

| Ukuran | Semua swing | Setelah filter usulan (keluar ≥ 1,5 ATR dalam 10 bar, lebar 0,3–2,0 ATR) |
|---|---|---|
| Zona per minggu per simbol (dua arah) | 31–34 | 10–12 |
| Lebar zona p10 / p50 / p90 (× ATR) | 0,41 / 0,85 / 1,70 | 0,44 / 0,81 / 1,40 |
| Kekuatan keluar p50 (× ATR) | 1,07 | 2,50 |
| Disentuh lagi dalam 100 bar | 84% | 78% |
| Ditembus close sebelum 100 bar | 79% | 63% |

## Glosarium

- **Zona demand / supply**: area di candle swing low / swing high H1. Batas jauh (*distal*) = low / high candle swing; batas dekat (*proximal*) = sisi badan candle yang menghadap harga (max(open, close) untuk demand, min(open, close) untuk supply).
- **ATR zona**: ATR(14) Wilder di MTF pada bar swing.
- **Kekuatan keluar**: jarak terjauh close dari batas dekat ke arah impuls dalam `InpZoneLegBars` bar setelah swing, dalam × ATR zona.
- **Aktif sejak**: bar MTF pertama di mana swing sudah terkonfirmasi (jeda `InpSwingStrength`) dan kekuatan keluar sudah tercapai.
- **Sentuhan**: bar MTF tertutup setelah zona aktif yang masuk ke zona (low ≤ batas dekat untuk demand, high ≥ batas dekat untuk supply) setelah bar sebelumnya di luar zona.
- **Status**: Fresh (0 sentuhan), Tested (1), Lemah (≥ 2, tidak dipakai), Invalid (close MTF melewati batas jauh), Kedaluwarsa (usia > `InpMaxZoneAgeBars` bar MTF sejak bar swing), Used (sudah menghasilkan entry).

## Requirements

### Requirement 1: Deteksi zona

**User story:** Sebagai trader, saya ingin zona hanya dari swing terkonfirmasi yang diikuti gerak keluar kuat, agar zona lemah tidak menjadi alasan entry.

#### Acceptance criteria

1.1. EA WAJIB membuat calon zona demand di setiap swing low dan zona supply di setiap swing high MTF yang terkonfirmasi (spec 10), dengan batas jauh dan batas dekat sesuai glosarium.
1.2. EA WAJIB menolak calon zona yang lebarnya di luar `InpZoneMinWidthAtr` (default 0,3) – `InpZoneMaxWidthAtr` (default 2,0) × ATR zona.
1.3. EA WAJIB menolak calon zona yang kekuatan keluarnya kurang dari `InpZoneMinLegAtr` (default 1,5) × ATR zona dalam `InpZoneLegBars` (default 10) bar setelah swing.
1.4. Zona WAJIB baru aktif (bisa disentuh, dipakai, dihitung statusnya) sejak bar aktif; sebelumnya zona tidak ada bagi pipeline.
1.5. Setiap zona WAJIB punya ID deterministik dari timeframe, waktu bar swing, dan jenis (demand/supply), sama antara jalan terus dan pembangunan ulang.

### Requirement 2: Status zona

**User story:** Sebagai trader, saya ingin status zona mengikuti aturan PRD, agar hanya zona Fresh dan Tested yang dipakai.

#### Acceptance criteria

2.1. Status WAJIB dihitung dari bar MTF tertutup sejak zona aktif: Fresh, Tested, Lemah, Invalid, Kedaluwarsa (glosarium); Invalid dan Kedaluwarsa bersifat final.
2.2. Bar yang menembus batas jauh dengan close WAJIB membuat zona Invalid walau bar itu juga menyentuh zona.
2.3. Zona WAJIB Kedaluwarsa setelah `InpMaxZoneAgeBars` (default 100, PRD) bar MTF sejak bar swing.
2.4. Zona berstatus Used WAJIB tidak bisa menghasilkan entry lagi (PRD: satu zona satu entry), apa pun status lainnya.
2.5. Hanya zona Fresh atau Tested yang tidak Used WAJIB dianggap valid untuk sinyal.

### Requirement 3: Pembangunan ulang dan Used

**User story:** Sebagai trader, saya ingin restart EA tidak mengubah peta zona dan tidak membuat zona yang sudah dipakai bisa dipakai lagi.

#### Acceptance criteria

3.1. KETIKA bar MTF baru tutup MAKA EA WAJIB membangun ulang peta zona sepenuhnya dari histori MTF (jumlah bar = usia maksimum + kebutuhan swing, kekuatan keluar, dan ATR), bukan memperbarui peta lama.
3.2. Peta zona WAJIB tidak dimuat dari DB (PRD), sehingga backtest tidak bocor data.
3.3. EA WAJIB menyediakan penanda Used per zona yang bertahan lintas restart (Global Variable per magic), dibaca saat membangun peta.
3.4. Penanda Used untuk zona yang sudah kedaluwarsa WAJIB dibersihkan agar Global Variable tidak menumpuk.
3.5. JIKA histori MTF kurang MAKA peta zona WAJIB kosong dengan alasan "data kurang" (sama dengan spec 10), bukan peta sebagian.

### Requirement 4: Akses untuk pipeline

**User story:** Sebagai developer pipeline sinyal, saya ingin menanyakan zona dengan jelas.

#### Acceptance criteria

4.1. EA WAJIB bisa menjawab zona valid searah arah tertentu yang disentuh rentang harga (high/low bar LTF), memilih Fresh lebih dulu, lalu yang paling baru.
4.2. EA WAJIB bisa menjawab zona lawan valid terdekat di depan harga (supply di atas untuk BUY, demand di bawah untuk SELL), untuk TP (spec 13).
4.3. Komponen skor kualitas zona WAJIB 30 untuk Fresh, 15 untuk Tested, 0 selain itu (PRD).
4.4. Jumlah zona per status WAJIB tersedia untuk log dan telemetri.

### Requirement 5: Uji dan versi

5.1. Skenario SC-13 WAJIB membuktikan di Strategy Tester (EURUSDc dan XAUUSDc) bahwa peta zona setiap bar MTF selama run sama dengan peta yang dibangun dari histori (ID, batas, status), termasuk setelah restart, dan bahwa zona yang ditandai Used tetap Used setelah restart.
5.2. EA dan harness WAJIB naik ke `1.10`; input baru masuk `Inputs.mqh`, JSON sesi, preset, README.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Candle swing doji (badan sangat tipis) | Lebar < 0,3 ATR → ditolak | 1.2 |
| EC-02 | Candle swing sangat panjang (berita) | Lebar > 2 ATR → ditolak | 1.2 |
| EC-03 | Gerak keluar 1,4 ATR | Ditolak | 1.3 |
| EC-04 | Kekuatan keluar tercapai di bar ke-3 setelah swing (sebelum konfirmasi 2 bar) | Aktif sejak bar konfirmasi | 1.4 |
| EC-05 | Bar menyentuh lalu close di bawah batas jauh | Invalid, bukan Tested | 2.2 |
| EC-06 | Harga bertahan di dalam zona beberapa bar | Satu sentuhan | glosarium |
| EC-07 | Zona demand dan supply tumpang tindih | Keduanya disimpan; pipeline memilih searah bias | 4.1 |
| EC-08 | Dua zona demand bertumpuk | Keduanya disimpan; pipeline memilih Fresh lalu terbaru | 4.1 |
| EC-09 | Restart EA saat zona Used masih aktif | Tetap Used (GV) | 3.3 |
| EC-10 | Backtest baru dengan login sama | GV tester terpisah dari live dan dikosongkan per run | 3.3 |
| EC-11 | Gap akhir pekan melewati zona | Bar pertama setelah gap dinilai biasa (sentuhan/invalid dari bar itu) | 2.1 |
| EC-12 | BTCUSDc 24/7 | Sama dengan simbol lain, ATR dari bar yang ada | 1.2 |
| EC-13 | Histori kurang | Peta kosong, alasan data kurang | 3.5 |
| EC-14 | Tidak ada zona lawan di depan | Jawaban kosong; spec 13 memakai TP 2R (PC-15) | 4.2 |

## Keputusan yang perlu disetujui

1. **Batas zona dari satu candle swing** (low ke badan atas untuk demand), bukan dari rangkaian candle base. Sederhana, deterministik, dan lebarnya sudah wajar (median 0,8 ATR). Alternatif: base multi-candle (lebih banyak parameter).
2. **Default dari ukuran histori**: lebar 0,3–2,0 ATR, kekuatan keluar ≥ 1,5 ATR dalam 10 bar, usia 100 bar (PRD). ATR periode 14 sebagai konstanta (sama dengan ATR trailing).
3. **Peta dibangun ulang penuh tiap bar MTF** (fungsi murni atas ±130 bar), bukan diperbarui bertahap: lebih lambat sedikit, tetapi hasil jalan terus dan restart pasti sama.
4. **Penanda Used di Global Variable per magic** (`<magic>_ZU_<waktu swing>_<D|S>`), bukan disimpulkan dari history deal (ambigu bila zona bertumpuk) atau DB (PRD). Spec 13 yang menandai; spec 11 menyediakan baca, tulis, dan pembersihan.
5. **Zona bertumpuk tidak digabung**; pemilihan di pipeline (Fresh dulu, lalu terbaru).
6. **Input baru**: `InpZoneMinWidthAtr` 0,3, `InpZoneMaxWidthAtr` 2,0, `InpZoneMinLegAtr` 1,5, `InpZoneLegBars` 10, `InpMaxZoneAgeBars` 100 (sudah ada di PRD sebagai `MaxZoneAgeBars`).

## Pertanyaan terbuka

- Tidak ada selain keputusan di atas.
