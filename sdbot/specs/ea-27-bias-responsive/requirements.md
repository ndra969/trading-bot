# Requirements — Bias HTF lebih responsif (H5)

Status: Done (2026-10-10)
Use case: UC-63 ([fase-5b-overview.md](../fase-5b-overview.md), menilai perbaikan dengan IS/OOS/REAL); kandidat sesudah Fase 5b
Asal: PRD-EA §Struktur dan bias HTF ("bullish/bearish hanya bila arah struktur dan arah EMA HTF sama"), §Pipeline (gerbang bias, ringkasan log harian), §Parameter input; PC-28 (aturan uji); temuan live 2026-10-08/09
Butuh: spec 26 (selesai, H4 ditolak). Acuan tetap konfigurasi 1.25 (EA 1.26 dengan default yang sama)

## Pendahuluan

Spec ini menguji hipotesis H5: bias HTF yang lebih cepat mengikuti pembalikan tren menaikkan R per trade. Ada dua sebab:
- EA berhenti mengambil entry searah tren lama;
- EA lebih cepat masuk searah tren baru.

Dasarnya dari live akun cent 2026-10-08 18:00 sampai 2026-10-09 17:30 WIB (v1.24/1.25, 0 trade). Datanya dari log MT5 Broker B (ringkasan gerbang dan perubahan bias) dan DB live:

- **Bias tertinggal saat pembalikan.** EURUSD, NZDUSD dan AUDUSD masih BEAR (BOS 7 Okt) padahal harga sudah naik sejak 8 Okt sekitar 16:00 UTC. Semua 61 kandidat SELL di tiga pair itu bergerak melawan (MAE 20–56 pip, MFE umumnya < 15 pip). Bias baru lepas 20:00 UTC (EURUSD) dan 04:00 UTC (AUD/NZD). Sesudah lepas, bias menjadi NONE (CONFLICT: struktur BULL, EMA BEAR), bukan BULL.
- **Tren baru terblokir sampai EMA menyusul.** XAUUSD: struktur BULL sejak BOS 4143,4 (8 Okt 20:00 UTC), tetapi bias BULL baru muncul 9 Okt 08:00 UTC sesudah harga naik sekitar 2 ATR H4. Di antaranya alasannya CONFLICT, lalu EMA datar.
- **Banyak simbol tanpa bias seharian.** Pada 8 Okt (UTC): GBPUSD, EURJPY, USDCAD 100% bar tanpa bias, GBPJPY 52/53. Alasannya CONFLICT atau EMA datar. Harga di simbol ini memang choppy (efisiensi gerak 0,18–0,25), jadi sebagian blokir ini benar.

Aturan sekarang: struktur (BOS terakhir dalam `InpStructureLookback` bar H4) **dan** EMA H4 (close di sisi EMA, EMA miring `InpEmaSlopeBars` bar) harus searah. BOS berlawanan sudah membatalkan bias, karena struktur berbalik dan menjadi CONFLICT. Yang lambat adalah syarat EMA untuk arah baru. Karena itu varian (c) dari diskusi ("BOS berlawanan langsung membatalkan bias") dirumuskan ulang: struktur menentukan arah, dan EMA hanya memveto bila arahnya berlawanan (EMA datar tidak memblokir).

Varian yang diuji:
- **V-a `STRUCTURE_ONLY`**: bias = arah struktur HTF.
- **V-b EMA HTF lebih pendek**: aturan sekarang, periode EMA bias 21. EMA MTF untuk skor tren tetap 50.
- **V-c `STRUCTURE_NOT_OPPOSED`**: bias = arah struktur, kecuali EMA HTF berlawanan.

Di luar lingkup:
- definisi BOS dan swing (`InpSwingStrength`, `InpStructureLookback`);
- skor tren MTF;
- timeframe HTF;
- filter arah per rezim pasar.

Bukti selesai:
- suite unit ALL PASS dan regresi default identik dengan acuan;
- backtest IS tiap varian tercatat;
- varian terpilih diuji di OOS dan REAL;
- keputusan H5 diterima atau ditolak beserta datanya.

## Glosarium

- **Struktur HTF**: arah BOS terakhir di jendela `InpStructureLookback` bar H4 (BULL/BEAR/NONE).
- **Arah EMA HTF**: BULL bila close > EMA dan EMA naik dibanding `InpEmaSlopeBars` bar lalu; BEAR kebalikannya; selain itu NONE (datar).
- **Mode bias**: aturan yang menggabungkan struktur dan EMA HTF menjadi bias.
- **Acuan**: konfigurasi 1.25 (mode `STRUCTURE_AND_EMA`, EMA 50). Sesinya: IS 1396–1407, OOS 1408–1419, REAL 1420–1431.
- **Trade baru / hilang**: trade varian yang tidak ada di acuan (simbol + waktu bar sinyal sama), dan sebaliknya.

## Requirements

### Requirement 1: Input mode bias
**User story:** Sebagai trader, saya ingin memilih aturan bias HTF lewat input, agar varian bisa diuji tanpa build terpisah dan default tetap sesuai PRD.

#### Acceptance criteria
1. Input `InpBiasMode` WAJIB menyediakan tiga nilai: `STRUCTURE_AND_EMA` (default, perilaku sekarang), `STRUCTURE_NOT_OPPOSED`, dan `STRUCTURE_ONLY`.
2. BILA `STRUCTURE_AND_EMA`, EA WAJIB memberi bias = arah struktur hanya bila arah EMA HTF sama. Selain itu NONE.
3. BILA `STRUCTURE_NOT_OPPOSED`, EA WAJIB memberi bias = arah struktur, kecuali arah EMA HTF berlawanan. EMA datar tidak memblokir.
4. BILA `STRUCTURE_ONLY`, EA WAJIB memberi bias = arah struktur, tanpa melihat EMA.
5. Di semua mode, struktur NONE atau histori HTF kurang WAJIB menghasilkan bias NONE dengan alasan yang sama seperti sekarang (`STRUCTURE`, `DATA`).
6. Alasan bias di log perubahan bias dan di `context_json.bias_reason` WAJIB tetap dari himpunan yang ada (`OK`, `STRUCTURE`, `EMA`, `CONFLICT`, `DATA`). Skema DB tidak berubah.
7. JIKA nilai input tidak sah, MAKA EA WAJIB gagal init dengan pesan validasi, seperti input lain.

### Requirement 2: Periode EMA bias terpisah
**User story:** Sebagai developer, saya ingin periode EMA HTF untuk bias bisa diatur sendiri, agar varian V-b tidak ikut mengubah skor tren MTF.

#### Acceptance criteria
1. Input `InpBiasEmaPeriod` WAJIB mengatur periode EMA HTF untuk bias. Nilai 0 (default) berarti sama dengan `InpEmaPeriod`. Nilai lain sah 10–400.
2. EMA MTF dan skor tren WAJIB tetap memakai `InpEmaPeriod`.
3. Kebutuhan histori HTF WAJIB dihitung dari periode EMA bias yang berlaku. Bila histori kurang, bias NONE dengan alasan `DATA`.
4. `inputs_json` WAJIB memuat `InpBiasMode` dan `InpBiasEmaPeriod` (56 kunci).
5. Dengan default kedua input, sinyal dan trade WAJIB identik dengan acuan (regresi).

### Requirement 3: Pengukuran IS
**User story:** Sebagai developer, saya ingin varian bias diukur dengan aturan yang sama dengan spec sebelumnya, agar pilihan tidak bergantung pada OOS.

#### Acceptance criteria
1. Backtest `-Period IS` WAJIB dijalankan untuk V-a, V-b (`InpBiasEmaPeriod=21`) dan V-c, dengan konfigurasi lain sama dengan acuan.
2. Setiap varian WAJIB dilaporkan dengan:
   - trade, R per trade, PF, DD, dan jumlah per simbol;
   - sebaran alasan tutup;
   - jumlah dan R per trade untuk trade sama, trade baru, dan trade hilang dibanding acuan.
3. Varian terpilih WAJIB ditentukan hanya dari IS, dengan aturan yang ditulis di design sebelum OOS dijalankan. Syaratnya R per trade IS lebih tinggi dari acuan dan memenuhi kriteria jumlah trade Fase 5b (IS ≥ 325 trade, ≥ 13 per simbol).
4. JIKA tidak ada varian yang lolos, MAKA H5 WAJIB ditolak tanpa OOS dan REAL.

### Requirement 4: Konfirmasi dan keputusan
**User story:** Sebagai trader, saya ingin aturan bias diubah hanya bila terbukti di data yang tidak dipakai menyetel.

#### Acceptance criteria
1. Varian terpilih WAJIB dijalankan sekali di OOS dan sekali di REAL, lalu dibandingkan dengan acuan.
2. H5 DITERIMA bila R per trade OOS dan REAL ≥ acuan masing-masing.
3. Bila DITERIMA:
   - default input dan preset 12 simbol berubah;
   - versi EA naik ke 1.28 (default berubah);
   - PC baru untuk PRD §Struktur dan bias HTF dan §Parameter input.
4. Bila DITOLAK: default tetap `STRUCTURE_AND_EMA` dan 0, preset tidak berubah. Input tetap ada di 1.27 untuk eksperimen, dengan PC untuk §Parameter input saja.
5. Semua hasil WAJIB dicatat di spec dan CHANGELOG.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Struktur BULL, EMA BEAR (pembalikan baru) | AND: NONE (CONFLICT); NOT_OPPOSED: NONE (CONFLICT); ONLY: BULL | 1.2–1.4 |
| EC-02 | Struktur BULL, EMA datar (XAU 9 Okt) | AND: NONE (EMA); NOT_OPPOSED: BULL (OK); ONLY: BULL | 1.2–1.4 |
| EC-03 | Struktur NONE (tidak ada BOS di jendela) | NONE (`STRUCTURE`) di semua mode | 1.5 |
| EC-04 | Histori HTF kurang untuk EMA bias 21 atau 50 | NONE (`DATA`), analisis ditunda seperti sekarang | 2.3 |
| EC-05 | Bias berbalik saat posisi terbuka | Posisi tetap dikelola (BE, partial, trailing). Bias hanya memengaruhi entry baru | 1.1 |
| EC-06 | Restart EA di tengah bar H4 | Bias dihitung ulang dari bar H4 tertutup, hasilnya sama dengan sebelum restart | 1.1 |
| EC-07 | `InpBiasEmaPeriod` 0 dan `InpEmaPeriod` 50 | Periode EMA bias 50, identik acuan | 2.1, 2.5 |
| EC-08 | `InpBiasEmaPeriod` di luar 0 atau 10–400 | Gagal init dengan pesan validasi | 1.7 |
| EC-09 | Mode longgar menambah kandidat di simbol choppy | Gerbang zona, PA, skor, dan R:R tetap berlaku. Efeknya terlihat di trade baru (3.2) | 3.2 |
| EC-10 | Selisih R per trade antar varian sangat kecil | Aturan pilih di design menentukan satu varian | 3.3 |
| EC-11 | Varian menambah trade tapi R per trade turun | Tidak lolos IS (syarat R per trade lebih tinggi) | 3.3 |

## Keputusan (2026-10-09)

1. Grid V-b: EMA bias 21 saja.
2. Dua input: `InpBiasMode` dan `InpBiasEmaPeriod` (terpisah dari `InpEmaPeriod`, agar skor tren MTF tidak ikut berubah).
3. Versi 1.27 untuk input baru, juga bila H5 ditolak (sama dengan spec 25).
