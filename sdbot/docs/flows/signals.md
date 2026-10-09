# Pipeline sinyal dan entry (spec 13, filter Fase 4: spec 14–16)

```mermaid
flowchart TB
    T([CSignalEngine.OnTick: setelah struktur, zona, pola]) --> N{bar LTF tertutup baru?}
    N -->|tidak| Z([selesai])
    N -->|ya| GV{GV magic_SIGBAR >= bar? restart di bar yang sama}
    GV -->|ya| Z
    GV -->|tidak| CL[set GV SIGBAR = bar, flush]
    CL --> ST{bar lebih tua dari 2 x LTF / analisis belum siap?}
    ST -->|ya| Z
    ST -->|tidak| B{bias HTF?<br/>InpBiasMode: struktur+EMA / tanpa veto EMA datar / struktur saja}
    B -->|NONE| CB[hitung tanpa_bias] --> Z
    B -->|BUY/SELL| ZN{bar menyentuh zona valid searah? TouchedZone: Fresh lalu terbaru}
    ZN -->|tidak| CZ[hitung tanpa_zona] --> Z
    ZN -->|ya| F[fakta kandidat: STOPPED/pause/CanTrade, posisi instance, pola arah bias, TrendScore MTF, bid/ask, stops, ATR H1, zona lawan]
    F --> CF[CConfirmations.Evaluate: bar H1 tertutup cache zona]
    CF --> FB[FibEvaluate bila InpScoreFibMode != OFF: impuls H1 = ekstrem 100 bar sebelum swing zona -> ekstrem sesudahnya; rasio batas dekat; level terdekat 0.382/0.5/0.618/0.786 -> 8/15/15/8 dikurangi linear sampai jarak 0,05]
    CF --> TL[TlEvaluate bila InpScoreTrendlineMode != OFF: pasangan swing fractal 100 bar; BUY support naik / SELL resistance turun >= 0,02 ATR per bar; tidak patah; proyeksi di zona +- 0,2 ATR; 3+ sentuhan 15, 2 sentuhan 7]
    FB --> E[EvaluateSignal: skor ZONE 30/15 + TREND 15/7/0 + PA 10/7/3 dari 55; komponen ACTIVE menambah skor dan maksimum (FIB 15, TRENDLINE 15, BREAKOUT 10, RSI 5)]
    CF --> BO[BoEvaluate bila InpScoreBreakoutMode != OFF: swing fractal 100 bar sisi sinyal; close pertama sesudah konfirmasi menembus >= 0,1 ATR; tidak gagal (close balik > 0,2 ATR); level di zona +- 0,2 ATR = 10; breakout terbaru]
    TL --> E
    CF --> RS[RsiEvaluate bila InpScoreRsiMode != OFF: RSI 14 H1 disalin per waktu bar cache; dua swing sinyal terakhir; BUY lower low harga + higher low RSI >= 2, SELL cerminan; swing kedua <= 20 bar = 5; bukan tahap tolak]
    BO --> E
    RS --> E
    E --> S1{pre-filter risiko} -->|gagal| REJ
    S1 --> ZT{InpAllowTestedZones = false dan zona TESTED?} -->|ya: NO_VALID_ZONE| REJ
    ZT --> NW{status berita ON dan bar dalam jendela event mata uang simbol? HIGH ±30, MEDIUM ±10 menit} -->|ya: NEWS_BLACKOUT| REJ
    NW --> SS{sesi UTC bar diizinkan? Tokyo 00-08, London 08-17, NY 13-22; 22-24 tidak; jam bar < InpSessionEndHourUtc} -->|tidak: OUTSIDE_SESSION| REJ
    SS --> SPD{spread ask-bid <= InpMaxSpreadPoints? 0 = mati} -->|tidak: SPREAD_TOO_WIDE| REJ
    SPD --> S2{posisi instance terbuka?} -->|ya| REJ
    S2 --> S3{pola PA searah?} -->|tidak| REJ
    S3 --> S4{skor >= 65% dari 55?} -->|tidak| REJ
    S4 --> S5[SL = batas jauh -/+ 0,1 ATR, SELL + spread; TP = zona lawan atau 2R]
    S5 --> S6{R > 0, R >= max stops+spread, 0,3 ATR, R <= 3 ATR, R:R >= 2?} -->|tidak| REJ
    S6 --> L[CalcVolume + PreTradeCheck: lot turun per step bila rugi OrderCalcProfit > risiko]
    L -->|tolak| REJ
    L --> O[CExecutor.OpenMarket dengan signal_id]
    O -->|gagal| REJ
    O -->|terisi| U[zona MarkUsed GV] --> ACC[SignalRecord ACCEPTED]
    REJ[SignalRecord REJECTED + tahap pertama yang gagal] --> SK
    ACC --> SK[event sink: signals + 3 signal_scores, id = SHA-256 login/run_key/magic/bar]
```

Komponen Fibonacci (spec 18), trendline (spec 19), breakout & retest (spec 20), dan RSI divergence (spec 21) berjalan dalam mode bayangan secara default: skornya dicatat di `signal_scores` dengan `active = 0` dan di konteks (`fib_level`, `fib_ratio`, `tl_dist`, `tl_slope`, `tl_touches`, `bo_age`, `bo_dist`, `bo_level`, `rsi_age`, `rsi_diff`, `rsi_pdiff`), tetapi tidak mengubah skor gerbang atau entry. Aktivasi diputuskan dari data IS/OOS (PC-25, spec 22).

Gerbang zona Tested (spec 23): bila `InpAllowTestedZones = false`, kandidat dari zona TESTED ditolak `NO_VALID_ZONE` sesudah pre-filter risiko dan sebelum berita, dengan skor tetap dicatat. Default `false` sejak 1.25 (H1 diterima, PC-29); `true` mengembalikan perilaku 1.24.

Jam akhir entry (spec 25): bila filter sesi aktif, bar dengan jam UTC ≥ `InpSessionEndHourUtc` ditolak `OUTSIDE_SESSION` dengan detail `jam_akhir=H`; default 22 tidak memotong apa pun. Posisi terbuka tetap dikelola.

Filter berita (spec 16, [news.md](news.md)) berjalan sebelum sesi dan spread; status OFF atau DISABLED tidak memblokir. Konteks sinyal mencatat `news` (ON/OFF/DISABLED) dan `news_next` (event ≥ medium terdekat dalam 24 jam, atau null).

Satu baris `signals` per kandidat (bar yang menyentuh zona valid searah bias, 4–6 per hari per simbol). Bar tanpa bias atau tanpa zona hanya dihitung dan diringkas di log INFO saat hari server berganti dan saat EA berhenti. ID sinyal dihitung sebelum order sehingga `trades.signal_id` terisi, dan baris yang sama dari restart di bar yang sama ditolak `ON CONFLICT(id) DO NOTHING`. Query kalibrasi: `tools/queries/signal_rejects.sql`, `score_vs_r.sql`, `pattern_vs_r.sql`, `zone_status_vs_r.sql`, `tp_source_vs_r.sql`, `candidates_per_day.sql`.
