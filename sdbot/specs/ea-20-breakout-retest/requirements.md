# Requirements — Skor breakout & retest (mode bayangan)

Status: Done (2026-10-07)
Use case: UC-55 ([fase-5-overview.md](../fase-5-overview.md))
Asal: PRD-EA §Skor konfluensi (breakout & retest maks 10: retest level yang ditembus = 10), PC-25 (mode bayangan, aturan aktivasi); python-bot-lessons §1 (layer breakout bot Python berbobot 0.12 tetapi fungsinya tidak pernah terhubung ke pipeline)
Butuh: spec 19 (`CConfirmations`, `ActiveConfirmations`)

## Pendahuluan

Spec ini menambah komponen skor breakout & retest. Kandidat mendapat skor bila zonanya berada di level swing MTF yang sudah ditembus searah sinyal dan sekarang diuji ulang: resistance yang ditembus naik menjadi support untuk BUY, dan support yang ditembus turun menjadi resistance untuk SELL.

- Komponen ditambahkan ke `CConfirmations` dalam mode bayangan.
- Karena bot Python pernah punya layer breakout yang tidak pernah terpanggil, spec ini wajib membuktikan komponen benar-benar menyumbang nilai di pipeline nyata, bukan hanya di unit test.

Di luar lingkup: breakout sebagai trigger entry, dan level dari HTF atau angka bulat.

Bukti selesai:
- suite `BreakoutRules` ALL PASS;
- SC-20 PASS, dengan BREAKOUT > 0 muncul di pipeline;
- backtest IS + OOS dengan trade identik dengan acuan v1.21, plus laporan komponen BREAKOUT tercatat.

## Glosarium

- **Level:** harga swing terkonfirmasi MTF. BUY memakai swing high (resistance), SELL memakai swing low (support).
- **Breakout:** close bar MTF pertama sesudah swing itu yang melewati level searah sinyal dengan jarak ≥ jarak tembus minimum. Tembusan wick saja tidak dihitung.
- **Retest:** level berada di dalam zona kandidat, atau berjarak ≤ toleransi dari zona, pada saat kandidat.
- **Breakout gagal:** sesudah breakout dan sebelum bar kandidat, ada close MTF yang kembali melewati level ke arah berlawanan lebih dari toleransi.

## Requirements

### Requirement 1: Level dan breakout tanpa lookahead
**User story:** Sebagai developer, saya ingin level dan breakout hanya dibentuk dari swing terkonfirmasi dan bar MTF tertutup, agar skor di backtest sama dengan di live.

#### Acceptance criteria
1. EA WAJIB memakai swing terkonfirmasi MTF dalam jendela `StructureLookback` bar sebelum bar kandidat. Swing harus sisi yang sesuai: high untuk BUY, low untuk SELL.
2. Breakout WAJIB berupa close bar MTF tertutup sesudah swing (sesudah konfirmasinya) yang melewati level searah sinyal dengan jarak ≥ jarak tembus minimum. Tembusan wick saja WAJIB tidak dihitung.
3. Breakout gagal WAJIB membuat level itu tidak dipakai.
4. Untuk bar kandidat yang sama, nilai breakout WAJIB sama, baik dihitung bar per bar maupun setelah restart.

### Requirement 2: Skor retest
**User story:** Sebagai trader, saya ingin skor diberikan hanya bila zona kandidat benar-benar menguji ulang level yang ditembus, agar skor mencerminkan pola polarity flip.

#### Acceptance criteria
1. KETIKA ada level dengan breakout valid yang berada di zona kandidat atau berjarak ≤ toleransi dari zona MAKA skor WAJIB 10 (PRD). Selain itu skor WAJIB 0.
2. Bila beberapa level memenuhi syarat, EA WAJIB memilih level dengan breakout terbaru.
3. EA WAJIB mencatat harga level, umur breakout dalam bar MTF, dan jarak level ke zona (ATR) di konteks sinyal.

### Requirement 3: Mode komponen
**User story:** Sebagai developer, saya ingin breakout dicatat tanpa mengubah entry, sama dengan Fibonacci dan trendline.

#### Acceptance criteria
1. Input `InpScoreBreakoutMode` WAJIB menerima OFF, SHADOW, atau ACTIVE, dengan default SHADOW.
2. SHADOW WAJIB mencatat `signal_scores` BREAKOUT (`max_score` 10) dengan `active = 0`, tanpa mengubah skor gerbang, maksimum, entry, atau `score_total`.
3. ACTIVE WAJIB menambah skor ke gerbang dan maksimum +10. Bila Fibonacci, trendline, dan breakout aktif, maksimumnya 95.
4. OFF WAJIB tidak menghitung dan tidak mencatat breakout.

### Requirement 4: Bukti komponen terhubung
**User story:** Sebagai developer, saya ingin bukti bahwa breakout benar-benar menyumbang nilai di pipeline, agar bug bot Python (layer berbobot tetapi tidak pernah dipanggil) tidak terulang.

#### Acceptance criteria
1. Skenario pipeline WAJIB menunjukkan ada kandidat dengan BREAKOUT = 10 dan ada yang = 0.
2. Unit test WAJIB membuktikan bahwa BREAKOUT pada mode ACTIVE mengubah skor gerbang dan dapat mengubah tahap tolak (`SCORE_TOO_LOW` menjadi lolos).

### Requirement 5: Pengukuran IS/OOS
**User story:** Sebagai developer, saya ingin hasil breakout bayangan diukur di IS dan OOS, agar spec 22 punya data aktivasi.

#### Acceptance criteria
1. Backtest `-Period ALL` WAJIB menghasilkan trade identik dengan acuan v1.21 (sesi 1027–1051). Selisih swap server tidak dihitung.
2. `component_report.py` WAJIB menampilkan BREAKOUT per nilai di IS dan OOS, dan hasilnya dicatat.
3. Bila > 60% atau < 2% kandidat ACCEPTED bernilai 10, temuan itu WAJIB dibahas.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Level hanya ditembus wick | Bukan breakout, skor 0 | 1.2 |
| EC-02 | Breakout lalu close kembali di bawah level (BUY) | Breakout gagal, level tidak dipakai | 1.3 |
| EC-03 | Breakout melawan arah sinyal (support ditembus turun, kandidat BUY) | Tidak dihitung | 1.1, 1.2 |
| EC-04 | Swing belum terkonfirmasi | Tidak dipakai | 1.1, 1.4 |
| EC-05 | Breakout terjadi di bar MTF yang memuat kandidat (belum tertutup) | Tidak dipakai | 1.2 |
| EC-06 | Dua level ditembus, keduanya dekat zona | Breakout terbaru dipilih | 2.2 |
| EC-07 | Level jauh dari zona (> toleransi) | Skor 0 | 2.1 |
| EC-08 | JPY, XAU, BTC | Jarak tembus dan toleransi dalam ATR | 1.2, 2.1 |
| EC-09 | Swing sudah keluar jendela 100 bar | Tidak dipakai | 1.1 |

## Pertanyaan terbuka

- Jarak tembus minimum: 0,1 × ATR MTF dari level ke close (usulan)?
- Toleransi retest dan breakout gagal: 0,2 × ATR, sama dengan trendline (usulan)?
- Batas umur breakout: tidak ada selain jendela `StructureLookback` 100 bar (usulan), atau dibatasi misalnya 30 bar?
