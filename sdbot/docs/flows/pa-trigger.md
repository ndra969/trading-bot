# Trigger price action (spec 12)

```mermaid
flowchart TB
    T([CPaTrigger.OnTick]) --> N{bar LTF tertutup baru?}
    N -->|tidak| Z([selesai, hasil bar sebelumnya tetap])
    N -->|ya| C[CopyRates shift 1, 45 bar]
    C -->|kurang| DK[hasil NONE, WARN throttled]
    C --> A[ATR 14 Wilder di bar terakhir]
    A --> D[DetectPattern untuk BUY dan untuk SELL]
    D --> V{rentang 0, ATR 0, atau kurang dari 3 bar?}
    V -->|ya| NO[NONE]
    V -->|tidak| P1{bintang pagi/sore?}
    P1 -->|ya| R1[STAR 3]
    P1 -->|tidak| P2{engulfing kuat?}
    P2 -->|ya| R2[ENGULF_STRONG 10]
    P2 -->|tidak| P3{pin bar?}
    P3 -->|ya| R3[PIN 7]
    P3 -->|tidak| P4{engulfing?}
    P4 -->|ya| R4[ENGULF 3]
    P4 -->|tidak| P5{tweezer?}
    P5 -->|ya| R5[TWEEZER 3]
    P5 -->|tidak| P6{outside bar terarah?}
    P6 -->|ya| R6[OUTSIDE 3]
    P6 -->|tidak| NO
```

Ukuran pola relatif ATR dan rentang bar (konstanta `SDB_PA_*` di `Core/Constants.mqh`), sehingga satu definisi berlaku untuk forex, logam, dan crypto. Pola netral (inside bar, doji, harami) tidak diperiksa sama sekali, jadi tidak bisa mendahului pola terarah. Pipeline (spec 13) memanggil `Result(arah bias)` dan `LastBar` untuk cek sentuhan zona.
