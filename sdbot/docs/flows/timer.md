# OnTimer (tiap 1 detik)

```mermaid
flowchart TB
    T([OnTimer]) --> A[CAccount.OnTimer: validasi tertunda, ganti login, koneksi, izin]
    A --> R{ditolak dari timer?}
    R -->|ya| X[CRITICAL, flush, ExpertRemove]
    R -->|tidak| E[EnsureState]
    E --> M[CRiskMonitor.Run]
    M --> S{60 detik sejak snapshot?}
    S -->|ya| SN[snapshot akun + puncak equity ke event sink]
    S -->|tidak| G
    SN --> G{24 jam sejak touch GV?}
    G -->|ya| TG[touch semua GV agar tidak dihapus MT5]
    G -->|tidak| F
    TG --> N[CNotifier.OnTimer: buang pesan basi, kirim maks 2]
    N --> F[CLogger.Flush: antrean ke SQLite dalam satu transaksi, termasuk status kirim]
```

Risk monitor jalan sebelum snapshot, notifier, dan flush, terpisah dari logika entry (PRD §Risk management). Notifier juga jalan saat akun belum PASSED, agar alert init terkirim (spec 08). Detail: [notifier.md](notifier.md).
