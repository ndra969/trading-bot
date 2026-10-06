# Requirements — Skor trendline (mode bayangan)

Status: Done (2026-10-06)
Use case: UC-54 ([fase-5-overview.md](../fase-5-overview.md))
Asal: PRD-EA §Skor konfluensi (trendline maks 15: 3+ sentuhan searah = 15, 2 sentuhan = 7), PC-25 (mode bayangan, aturan aktivasi); python-bot-lessons §1 (trendline bot Python ikut menghitung garis melawan tren, tanpa filter kemiringan, net −$102 per 30 hari)
Butuh: spec 18 (`ENUM_SDB_COMPONENT_MODE`, pola komponen bayangan, laporan komponen)

## Pendahuluan

Spec ini menambah komponen skor trendline: kandidat mendapat skor bila zonanya berada di trendline MTF searah sinyal. BUY memakai support naik dari swing low. SELL memakai resistance turun dari swing high.

- Seperti Fibonacci, komponen berjalan dalam mode bayangan secara default.
- Spec ini juga membuat kelas `CConfirmations` (rencana overview §5) yang menampung Fibonacci dan trendline, karena ini komponen kedua.

Di luar lingkup: trendline sebagai trigger entry atau sebagai SL/TP, dan trendline HTF.

Bukti selesai:
- suite `TrendlineRules` ALL PASS, termasuk kasus garis melawan tren (bug bot Python);
- SC-19 PASS;
- backtest IS + OOS dengan trade identik dengan acuan v1.20, plus laporan komponen TRENDLINE tercatat.

## Glosarium

- **Swing terkonfirmasi:** fractal MTF dengan kekuatan `SwingStrength` yang sudah diakui (jeda bar), sama dengan analisis struktur Fase 3.
- **Trendline searah:**
  - BUY: garis melalui dua swing low terkonfirmasi dengan kemiringan **naik**;
  - SELL: garis melalui dua swing high terkonfirmasi dengan kemiringan **turun**.
- **Sentuhan:** swing terkonfirmasi (low untuk BUY, high untuk SELL) yang berjarak ≤ toleransi dari garis. Dua titik pembentuk garis dihitung sebagai 2 sentuhan.
- **Garis patah:** sesudah sentuhan terakhir, ada bar MTF yang close-nya melewati garis lebih dari toleransi ke arah berlawanan (di bawah support, di atas resistance).

## Requirements

### Requirement 1: Garis dari swing terkonfirmasi, searah sinyal
**User story:** Sebagai trader, saya ingin hanya trendline yang searah sinyal yang dinilai, agar bug bot Python (support turun ikut memperkuat BUY) tidak terulang.

#### Acceptance criteria
1. EA WAJIB membentuk kandidat garis hanya dari swing terkonfirmasi MTF dalam jendela `StructureLookback` bar sebelum bar kandidat, hanya dari bar tertutup.
2. Untuk BUY, EA WAJIB hanya memakai garis swing low dengan kemiringan naik. Untuk SELL, hanya garis swing high dengan kemiringan turun.
3. Garis yang hampir datar (kemiringan di bawah batas minimum dalam ATR per bar) WAJIB tidak dihitung sebagai trendline.
4. Garis patah WAJIB tidak dipakai.
5. Untuk bar kandidat yang sama, nilai trendline WAJIB sama, baik dihitung bar per bar maupun setelah restart.

### Requirement 2: Skor dari sentuhan dan posisi zona
**User story:** Sebagai trader, saya ingin skor trendline hanya diberikan bila zona kandidat benar-benar berada di garis, agar skor mencerminkan konfluensi, bukan sekadar adanya garis di grafik.

#### Acceptance criteria
1. EA WAJIB memproyeksikan garis ke waktu bar kandidat. Garis hanya dihitung bila proyeksi itu berada di dalam zona kandidat, atau berjarak ≤ toleransi dari zona.
2. Nilai WAJIB mengikuti PRD: 3 sentuhan atau lebih = 15, 2 sentuhan = 7, tidak ada garis yang memenuhi syarat = 0.
3. Bila beberapa garis memenuhi syarat, EA WAJIB memilih garis dengan sentuhan terbanyak. Bila sama, dipilih garis dengan titik kedua terbaru.
4. EA WAJIB mencatat jumlah sentuhan, kemiringan (ATR per bar), dan jarak proyeksi ke zona di konteks sinyal.

### Requirement 3: Mode komponen dan `CConfirmations`
**User story:** Sebagai developer, saya ingin trendline dicatat tanpa mengubah entry, dan komponen konfirmasi dikumpulkan di satu kelas, agar spec 20–21 tinggal menambah komponen.

#### Acceptance criteria
1. Input `InpScoreTrendlineMode` WAJIB menerima OFF, SHADOW, atau ACTIVE, dengan default SHADOW.
2. SHADOW WAJIB mencatat `signal_scores` TRENDLINE dengan `active = 0`, tanpa mengubah skor gerbang, maksimum, entry, atau `score_total`.
3. ACTIVE WAJIB menambah skor ke gerbang dan maksimum +15. Maksimum dihitung dari semua komponen aktif (misalnya Fibonacci dan trendline aktif = 85).
4. OFF WAJIB tidak menghitung dan tidak mencatat trendline.
5. Fibonacci dan trendline WAJIB dihitung lewat satu kelas `CConfirmations`. Perilaku Fibonacci spec 18 tidak berubah.

### Requirement 4: Pengukuran IS/OOS
**User story:** Sebagai developer, saya ingin hasil trendline bayangan diukur di IS dan OOS, agar spec 22 punya data aktivasi.

#### Acceptance criteria
1. Backtest `-Period ALL` versi spec ini WAJIB menghasilkan trade identik dengan acuan v1.20 (sesi 964–987). Selisih swap server tidak dihitung.
2. `component_report.py` WAJIB menampilkan TRENDLINE (bayangan) per nilai di IS dan OOS, dan hasilnya dicatat.
3. Distribusi nilai TRENDLINE atas semua kandidat WAJIB dicatat. Bila > 60% kandidat ACCEPTED bernilai 15, atau < 2% bernilai > 0, temuan itu WAJIB dibahas (deteksi terlalu longgar atau terlalu ketat).

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Support turun di bawah zona demand (garis melawan tren) | Tidak dihitung, skor 0 | 1.2 |
| EC-02 | Hanya satu swing terkonfirmasi di jendela | Skor 0 | 1.1 |
| EC-03 | Swing terbaru belum terkonfirmasi (jeda fractal) | Tidak dipakai | 1.1, 1.5 |
| EC-04 | Garis tembus close lalu kembali | Garis patah, tidak dipakai | 1.4 |
| EC-05 | Garis hampir datar (double bottom) | Bukan trendline (support horizontal bukan komponen ini) | 1.3 |
| EC-06 | Proyeksi garis jauh dari zona (garis di bawah zona) | Skor 0 | 2.1 |
| EC-07 | Dua garis sama-sama 3 sentuhan | Titik kedua terbaru dipilih, deterministik | 2.3 |
| EC-08 | JPY, XAU, BTC | Toleransi dan kemiringan dalam ATR, tidak bergantung skala harga | 1.3, 2.1 |
| EC-09 | Restart di tengah hari | Nilai sama untuk bar yang sama | 1.5 |
| EC-10 | Fibonacci ACTIVE dan trendline SHADOW | Maksimum 70; trendline tercatat `active = 0` | 3.3 |

## Pertanyaan terbuka

- Toleransi sentuhan dan jarak ke zona: 0,2 × ATR MTF (usulan; satu toleransi untuk keduanya)?
- Kemiringan minimum: 0,02 × ATR per bar MTF (usulan; di H1 kira-kira 0,5 ATR per hari)?
- Jumlah swing yang dipertimbangkan: semua pasangan swing terkonfirmasi di jendela 100 bar (usulan; paling banyak sekitar 20 swing per sisi, jadi ≤ 190 pasangan, ringan untuk 4–6 kandidat per hari)?
