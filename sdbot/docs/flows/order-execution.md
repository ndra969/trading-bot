# Eksekusi order

Fase 1 hanya membuka posisi lewat harness uji; entry dari sinyal masuk di Fase 3 dengan jalur yang sama.

```mermaid
flowchart TB
    S([permintaan entry: arah, SL, TP]) --> MC{pasar tutup? di luar jadwal sesi simbol atau < 60 detik sejak retcode 10018}
    MC -->|ya| RX[tolak NOT_TRADABLE tanpa kiriman; modify/partial: SKIPPED]
    MC -->|tidak| L[CRiskManager.CalcVolume: balance x risiko% / OrderCalcProfit, bulat ke bawah; turun proporsional lalu per step bila rugi lot akhir (dibulatkan broker) > risiko, spec 13, v1.18]
    L -->|lot < minimum| R1[tolak LOT_BELOW_MIN]
    L --> P[PreTradeCheck berurutan]
    P --> P1{boleh trading?} -->|tidak| X1[NOT_TRADABLE]
    P1 --> P2{STOPPED?} -->|ya| X2[STOPPED]
    P2 --> P3{pause harian?} -->|ya| X3[DAILY_PAUSE]
    P3 --> P4{risiko order <= risiko efektif?} -->|tidak| X4[RISK_PER_TRADE]
    P4 --> P5{risiko terbuka + order <= 3%?} -->|tidak| X5[MAX_OPEN_RISK]
    P5 --> P6{posisi sekategori < batas?} -->|tidak| X6[CLASS_POSITION_LIMIT]
    P6 --> PE{kaki mata uang order: posisi SDBot searah di akun < 2? BUY = dasar long + kuotasi short} -->|tidak| XE[CURRENCY_EXPOSURE, contoh USD short 2/2]
    PE --> P7{margin level sesudah order >= 200%?} -->|tidak| X7[MARGIN_LOW]
    P7 --> O[CExecutor.OpenMarket]
    O --> V[ID permintaan dari GV, SL/TP dinormalkan, sisi, stops/freeze, volume, OrderCheck]
    V -->|gagal| X8[INVALID_STOPS / SL_TOO_CLOSE / INVALID_VOLUME / MARGIN_LOW / BROKER_REJECTED]
    V --> K[OrderSend, komentar SDB|SL|ID, deviasi 10 point]
    K --> N{NextStep}
    N -->|sementara| W[jeda 500 ms, validasi ulang, maks 3 ulangan] --> V
    N -->|ambigu| Q[cari posisi/deal dengan ID permintaan] --> N
    N -->|sukses| T[TradeRecord: harga isi, slippage, risiko aktual]
    N -->|permanen / habis| F[ERROR + alert ORDER_FAILED sekali]
```
