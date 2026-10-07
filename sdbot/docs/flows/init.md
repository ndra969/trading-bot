# Init dan deinit

`SDBot.mq5` hanya meneruskan event ke `CSdbApp` (spec 04). Harness uji memakai `CSdbApp` yang sama. Tanpa DB (optimasi) notifier tidak dipasang (spec 08).

```mermaid
flowchart TB
    A([OnInit]) --> R[reset flag: init ulang pada objek yang sama saat ganti timeframe]
    R --> V{ValidateInputValues}
    V -->|gagal| P([INIT_PARAMETERS_INCORRECT])
    V -->|lolos| NT[tee: Logger + Notifier + observer; router alert Logger ke tee]
    NT --> S[CLogger: buka DB live/tester/none, migrasi, sesi baru + run_key]
    S --> RQ[TakeRestartAlerts: PENDING lama STALE/RESTART, Critical muda diantrekan ulang]
    RQ --> T
    T{InpPresetTag cocok dengan simbol chart?}
    T -->|tidak| W[WARN sekali]
    T -->|ya| AC
    W --> AC{CAccount::Validate}
    AC -->|REJECTED| F([INIT_FAILED; OnDeinit menutup sesi])
    AC -->|PASSED / PENDING| E[CExecutor, CRiskManager, CRiskMonitor]
    E --> H{handle ATR LTF}
    H -->|INVALID_HANDLE| F
    H -->|ok| PC[cache posisi, CPositionManager, CClosureTracker, CReconciler]
    PC --> ES[EnsureState: bila akun PASSED]
    ES --> TM{EventSetTimer 1 detik}
    TM -->|gagal| F
    TM -->|ok| ST[SendStart: pesan start + akhir sesi lalu]
    ST --> OK([INIT_SUCCEEDED])
```

Modul sinyal (bila sinyal aktif): struktur, zona, trigger PA, filter berita, lalu handle `iRSI(MTF, 14)` bila `InpScoreRsiMode` bukan OFF (spec 21). Handle RSI yang gagal dibuat hanya menghasilkan WARN; skor RSI menjadi 0 dan EA tetap jalan.

`EnsureState` (juga dicoba ulang dari timer selama akun PENDING): `CState` → `CRiskState` (nilai awal aman) → `CRiskMonitor.OnStateReady` (baseline operasi saldo, `STATE_RESET`, reset emergency, operasi saldo tertunda) → snapshot akun dengan puncak equity → `CReconciler.Run` (posisi terbuka `RECONCILED`, deal yang terlewat).

```mermaid
flowchart LR
    D([OnDeinit]) --> X{sudah deinit?}
    X -->|ya| Z([selesai])
    X -->|tidak| K[EventKillTimer] --> L[log alasan] --> I[IndicatorRelease ATR dan RSI] --> DR[SendStop, Drain: Critical lalu stop maks 2 detik, lepas lease pemimpin] --> ES[EndSession alasan] --> C[CLogger.Close: flush terakhir] --> Z
```
