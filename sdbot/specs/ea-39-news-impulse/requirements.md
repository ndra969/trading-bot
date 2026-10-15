# Requirements — Filter candle impuls sesudah berita (H13)

Status: Done (2026-10-15)
Use case: UC-83 ([fase-5c-overview.md](../fase-5c-overview.md)); permintaan user 2026-10-14 sesudah trade live pertama (USDCADc SELL kena SL sesudah CPI)
Asal: PRD-EA §Filter berita, §Parameter input EA, §Telemetri sinyal; temuan H12 (`fase-5c-overview.md` §8)
Butuh: spec 37 (acuan 1.35/1.36). Acuan = EA 1.36

## Pendahuluan

Trade live pertama SDBot (2026-10-14, USDCADc SELL) masuk 60 menit sesudah rilis CPI USD:
- candle M15 rilis bergerak 55 pip, sekitar 10× range M15 normal;
- SL berbasis zona hanya 16 pip;
- trade kena SL dalam 20 menit.

Filter berita sekarang hanya memblok ±15 menit dari rilis HIGH.

Hipotesis H13 adalah aturan **pengaman risiko**, bukan aturan profit. Sesudah berita HIGH yang memicu candle ekstrem, gejolak pasar jauh lebih besar dari SL zona, jadi entry ditunda sampai pasar tenang.

Data backtest tidak bisa membuktikan aturan ini menguntungkan (H12): candle ≥ 5× range normal hanya mendahului 4 dari 197 trade 1.35 (IS 0, OOS 2, REAL 2), dan keempatnya untung. Karena itu kriteria penerimaannya adalah **biaya kecil**, dan keputusan akhirnya diambil user dengan biaya itu terlihat.

Di luar lingkup:
- mengubah jendela ±15 menit yang sudah ada;
- filter impuls tanpa berita (gejolak tanpa rilis kalender);
- berita MEDIUM.

Bukti selesai:
- suite unit (fungsi murni deteksi impuls) PASS;
- skenario SC-39 PASS;
- regresi `-All` PASS;
- backtest IS/OOS/REAL dengan laporan trade yang hilang;
- keputusan user.

## Glosarium

- **Range bar**: high − low satu bar LTF (M15) tertutup.
- **Range normal**: rata-rata range 14 bar LTF tertutup terakhir, termasuk bar yang dinilai (bar sinyal).
- **Rasio impuls**: range bar terbesar dalam 8 bar LTF tertutup terakhir dibagi range normal. Definisinya sama dengan analisis H12, agar angka backtest di atas berlaku.
- **Berita HIGH relevan**: event kalender HIGH untuk mata uang simbol (XAU/XAG/BTC lewat USD), aturan yang sama dengan filter berita.

## Requirements

### Requirement 1: Penolakan sesudah berita dengan impuls ekstrem
**User story:** Sebagai trader, saya ingin EA tidak entry saat pasar masih bergejolak sesudah berita besar, agar SL zona yang kecil tidak tersapu gejolak.

#### Acceptance criteria
1. KETIKA kandidat dinilai dan ada berita HIGH relevan yang rilis dalam `NewsImpulseMinutes` menit terakhir (default 90) dan rasio impuls ≥ `NewsImpulseMult` (default 5,0) MAKA EA WAJIB menolak kandidat dengan tahap `NEWS_BLACKOUT`.
2. Detail penolakan WAJIB memuat nama event, mata uang, menit sejak rilis, dan rasio impuls (dua desimal).
3. JIKA hanya salah satu syarat terpenuhi (berita tanpa impuls ≥ ambang, atau impuls tanpa berita HIGH relevan) MAKA filter ini WAJIB tidak menolak.
4. Filter ini WAJIB dicek sesudah jendela berita ±15 menit yang sudah ada dan sebelum filter sesi, sehingga urutan tahap tolak PRD tetap.
5. Berita yang belum rilis tidak dihitung; hanya event dengan waktu rilis ≤ waktu bar yang dinilai.

### Requirement 2: Input dan telemetri
#### Acceptance criteria
1. Input `InpNewsImpulseMult` (default 5,0; 0 = filter mati; batas 0 atau 2–20) dan `InpNewsImpulseMinutes` (default 90; batas 15–240) WAJIB tersedia dan tercatat di `inputs_json`.
2. JIKA `InpNewsFilter` = false atau kalender tidak terbaca (`NEWS_FILTER_OFF`) MAKA filter impuls WAJIB tidak aktif, sama dengan filter berita.
3. Konteks sinyal (`context_json`) setiap kandidat WAJIB memuat rasio impuls (`impulse`, dua desimal), juga untuk kandidat yang lolos, agar ambang bisa dievaluasi dari data live.
4. Skema DB tidak berubah (tahap `NEWS_BLACKOUT` sudah ada).

### Requirement 3: Pengukuran dan keputusan
#### Acceptance criteria
1. Backtest `-Period` IS, OOS, dan REAL dengan default baru, dibandingkan dengan acuan 1.35 (sesi 2307–2318, 2376–2399) lewat `trade_diff`.
2. Laporan WAJIB memuat per periode:
   - trade yang hilang dan R masing-masing;
   - trade baru (efek posisi berikutnya);
   - R total dan R per trade sebelum/sesudah;
   - jumlah kandidat yang ditolak filter ini.
3. Syarat biaya, di setiap periode:
   - trade hilang ≤ 5% trade acuan;
   - total R tidak turun lebih dari 2R.
4. Bila syarat biaya terpenuhi, keputusan aktif atau tidak diambil user dengan laporan 3.2 terlihat. Bila tidak terpenuhi, default `InpNewsImpulseMult` = 0 (mati) dan input tetap ada.
5. Bila diaktifkan: versi naik, PC untuk PRD §Filter berita dan §Parameter input.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Rilis tepat di batas 90 menit | Inklusif: rilis ≤ 90 menit lalu dihitung | 1.1 |
| EC-02 | Rasio tepat 5,00 | Inklusif (≥) | 1.1 |
| EC-03 | Range normal 0 (data kosong, pasar tutup) | Rasio tidak dihitung, filter tidak menolak, dicatat `impulse` null | 1.3, 2.3 |
| EC-04 | Histori LTF kurang dari 14 bar tertutup (awal tester, simbol baru) | Sama dengan EC-03 | 1.3 |
| EC-05 | Dua berita HIGH dalam 90 menit | Yang paling baru masuk detail | 1.2 |
| EC-06 | Candle impuls terjadi sebelum rilis (kebocoran data) | Tetap dihitung bila dalam 8 bar terakhir; syarat berita tetap rilis ≤ 90 menit | 1.1 |
| EC-07 | XAU/BTC: berita USD | Dihitung lewat kaki USD | 1.1 |
| EC-08 | Restart EA dalam jendela 90 menit | Dihitung ulang dari kalender dan bar; tanpa state | 1.1 |
| EC-09 | Strategy Tester (kalender dari CSV) | Sama dengan live, memakai CSV | 2.2 |

## Keputusan (2026-10-14)

1. Filter hanya aktif bila ada berita HIGH relevan (tanpa filter gejolak tanpa berita).
2. Ambang rasio impuls 5,0 dan jendela 90 menit.
