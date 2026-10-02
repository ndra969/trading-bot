# Analisis struktur (spec 10)

```mermaid
flowchart TB
    T([CMarketStructure.OnTick]) --> H{bar HTF tertutup baru? iTime shift 1}
    H -->|ya| CH[CopyRates shift 1, BarsNeeded bar, urut waktu naik]
    CH -->|kurang| DK[tidak siap: data kurang, WARN throttled, coba tick berikutnya]
    CH -->|cukup| AH[AnalyzeTf HTF]
    AH --> SW[FindSwings: fractal kekuatan SwingStrength, kanan lengkap]
    SW --> ST[StructureOf: BOS = close melewati swing aktif terkonfirmasi, ditembus sekali; arah = BOS terakhir di StructureLookback]
    ST --> EM[EmaSeries: benih SMA, >= 3 x periode; arah = close vs EMA + kemiringan EmaSlopeBars]
    EM --> BI[BiasOf: struktur dan EMA HTF sama = arah itu, lainnya NONE; alasan OK/STRUCTURE/EMA/CONFLICT/DATA]
    BI --> LG{bias berubah?}
    LG -->|ya| LI[log INFO bias lama -> baru]
    T --> M{bar MTF tertutup baru?}
    M -->|ya| AM[AnalyzeTf MTF: struktur + EMA untuk skor keselarasan tren 15/7/0]
```

Hanya bar tertutup yang dipakai; hasil sebuah bar hanya bergantung pada bar sampai bar itu. SC-12/SC-12x membuktikan hasil selama run sama dengan hasil dihitung ulang dari histori, termasuk setelah restart.
