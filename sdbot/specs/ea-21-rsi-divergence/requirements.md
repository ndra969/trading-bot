# Requirements — Skor RSI divergence (mode bayangan)

Status: Done (2026-10-07)
Use case: UC-56 ([fase-5-overview.md](../fase-5-overview.md))
Asal: PRD-EA §Skor konfluensi (RSI maks 5: divergence searah = 5), PC-25 (mode bayangan, aturan aktivasi); python-bot-lessons §1 (RSI bot Python berfungsi sebagai gerbang: 6.773 penolakan vs 6 kontribusi); sdbot-ea "handle indikator dibuat di OnInit, dicek, dilepas di OnDeinit"
Butuh: spec 20 (`CConfirmations`, `ActiveConfirmations`)

## Pendahuluan

Spec ini menambah komponen terakhir Fase 5: RSI divergence reguler searah sinyal di MTF.
- **BUY:** harga membuat low lebih rendah di dua swing low terakhir, tetapi RSI membuat low lebih tinggi (bullish divergence).
- **SELL:** cerminannya (bearish divergence).

RSI **hanya skor**, tidak pernah menjadi tahap tolak. Komponen berjalan dalam mode bayangan. Ini juga komponen pertama yang memakai indikator MT5 (`iRSI`), jadi siklus hidup handle-nya termasuk lingkup spec.

Di luar lingkup: hidden divergence, RSI sebagai filter overbought/oversold, dan RSI HTF.

Bukti selesai:
- suite `RsiRules` ALL PASS;
- SC-21 PASS (RSI tidak pernah muncul sebagai tahap tolak);
- backtest IS + OOS dengan trade identik dengan acuan v1.22, plus laporan komponen RSI tercatat.

## Glosarium

- **RSI:** RSI(14) dari close bar MTF tertutup, dari handle `iRSI` timeframe MTF.
- **Swing sinyal:** swing fractal terkonfirmasi MTF sisi sinyal (low untuk BUY, high untuk SELL), aturan yang sama dengan struktur Fase 3.
- **Divergence reguler BUY:** dua swing low terakhir di jendela, low kedua < low pertama, sedangkan RSI di bar low kedua > RSI di bar low pertama dengan selisih ≥ selisih RSI minimum. SELL cerminannya.

## Requirements

### Requirement 1: Data RSI tanpa repaint
**User story:** Sebagai developer, saya ingin RSI dibaca dari bar MTF tertutup dengan handle yang dikelola benar, agar skor sama di backtest dan live dan tidak membocorkan resource.

#### Acceptance criteria
1. BILA mode RSI bukan OFF, EA WAJIB membuat handle `iRSI` MTF periode 14 saat init, memeriksa `INVALID_HANDLE`, dan melepasnya saat deinit.
2. Nilai RSI WAJIB diambil hanya untuk bar MTF tertutup yang sama dengan cache zona (jumlah salinan diperiksa), sehingga indeks bar sejajar.
3. JIKA handle tidak valid atau salinan RSI kurang MAKA skor RSI WAJIB 0 dengan alasan "data kurang", satu WARN per sesi, dan entry tetap berjalan.
4. Untuk bar kandidat yang sama, nilai RSI WAJIB sama, baik dihitung bar per bar maupun setelah restart.

### Requirement 2: Divergence searah sinyal
**User story:** Sebagai trader, saya ingin skor RSI diberikan hanya untuk divergence reguler yang searah sinyal dan baru terbentuk, agar skor menandai melemahnya tekanan lawan tepat sebelum entry.

#### Acceptance criteria
1. EA WAJIB memakai dua swing sinyal terkonfirmasi terakhir dalam jendela `StructureLookback`.
2. BUY: low kedua < low pertama dan RSI kedua − RSI pertama ≥ selisih RSI minimum → divergence. SELL: high kedua > high pertama dan RSI pertama − RSI kedua ≥ selisih minimum → divergence.
3. Swing kedua WAJIB berjarak ≤ jarak maksimum (bar MTF) dari bar kandidat. Kalau lebih jauh, divergence itu dianggap basi dan bernilai 0.
4. Nilai WAJIB mengikuti PRD: divergence searah = 5, selain itu 0.
5. EA WAJIB mencatat selisih RSI, selisih harga (ATR), dan jarak swing kedua ke kandidat (bar) di konteks sinyal.

### Requirement 3: RSI bukan gerbang
**User story:** Sebagai trader, saya ingin RSI tidak pernah memblokir kandidat, agar pola bot Python (RSI menolak ribuan setup) tidak terulang.

#### Acceptance criteria
1. EA WAJIB tidak memiliki tahap tolak berbasis RSI. Mode SHADOW dan ACTIVE hanya memengaruhi skor (ACTIVE: skor + maksimum).
2. Uji WAJIB membuktikan bahwa nilai RSI 0 tidak mengubah tahap tolak pada mode SHADOW, dan tidak pernah menghasilkan `reject_stage` baru di pipeline.

### Requirement 4: Mode komponen
**User story:** Sebagai developer, saya ingin RSI dicatat tanpa mengubah entry, sama dengan komponen lain.

#### Acceptance criteria
1. Input `InpScoreRsiMode` WAJIB menerima OFF, SHADOW, atau ACTIVE, dengan default SHADOW.
2. SHADOW WAJIB mencatat `signal_scores` RSI (`max_score` 5) dengan `active = 0`, tanpa mengubah skor gerbang, maksimum, entry, atau `score_total`.
3. ACTIVE WAJIB menambah skor ke gerbang dan maksimum +5. Bila keempat komponen aktif, maksimumnya 100 (PRD).
4. OFF WAJIB tidak membuat handle, tidak menghitung, dan tidak mencatat RSI.

### Requirement 5: Pengukuran IS/OOS
**User story:** Sebagai developer, saya ingin hasil RSI bayangan diukur di IS dan OOS, agar spec 22 punya data aktivasi untuk keempat komponen.

#### Acceptance criteria
1. Backtest `-Period ALL` WAJIB menghasilkan trade identik dengan acuan v1.22 (sesi 1091–1114). Selisih swap server tidak dihitung.
2. `component_report.py` WAJIB menampilkan RSI per nilai di IS dan OOS, dan hasilnya dicatat.
3. Bila > 60% atau < 2% kandidat ACCEPTED bernilai 5, temuan itu WAJIB dibahas.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Kurang dari dua swing sinyal di jendela | Skor 0 | 2.1 |
| EC-02 | Low kedua sama persis dengan low pertama | Bukan lower low, skor 0 | 2.2 |
| EC-03 | Harga lower low, RSI juga lower low | Bukan divergence, skor 0 | 2.2 |
| EC-04 | Selisih RSI di bawah minimum | Skor 0 | 2.2 |
| EC-05 | Divergence bearish saat kandidat BUY | Tidak dihitung (sisi swing berbeda) | 2.1, 2.2 |
| EC-06 | Swing kedua jauh sebelum kandidat | Basi, skor 0 | 2.3 |
| EC-07 | Handle `iRSI` gagal dibuat atau data belum siap | Skor 0, satu WARN, trading jalan | 1.3 |
| EC-08 | Restart di tengah bar | Nilai sama | 1.4 |
| EC-09 | Optimasi tester | Handle tetap dibuat bila mode bukan OFF; tanpa log DB (aturan optimasi) | 1.1 |

## Pertanyaan terbuka

- Selisih RSI minimum: 2,0 poin (usulan)?
- Jarak maksimum swing kedua ke kandidat: 20 bar H1, sekitar 1 hari trading (usulan)?
- Handle gagal saat mode ACTIVE: tetap degrade aman seperti SHADOW (usulan; RSI hanya bernilai 5 dari 100), atau INIT_FAILED?
