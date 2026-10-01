# Init dan deinit

`SDBot.mq5` hanya meneruskan event ke `CSdbApp` (spec 04). Harness uji memakai `CSdbApp` yang sama.

```mermaid
flowchart TB
    A([OnInit]) --> R[reset flag: init ulang pada objek yang sama saat ganti timeframe]
    R --> V{ValidateInputValues}
    V -->|gagal| P([INIT_PARAMETERS_INCORRECT])
    V -->|lolos| S[CLogger: buka DB live/tester/none, migrasi, sesi baru + run_key]
    S --> T{InpPresetTag cocok dengan simbol chart?}
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
    TM -->|ok| OK([INIT_SUCCEEDED])
```

`EnsureState` (juga dicoba ulang dari timer selama akun PENDING): `CState` → `CRiskState` (nilai awal aman) → `CRiskMonitor.OnStateReady` (baseline operasi saldo, `STATE_RESET`, reset emergency, operasi saldo tertunda) → snapshot akun dengan puncak equity → `CReconciler.Run` (posisi terbuka `RECONCILED`, deal yang terlewat).

```mermaid
flowchart LR
    D([OnDeinit]) --> X{sudah deinit?}
    X -->|ya| Z([selesai])
    X -->|tidak| K[EventKillTimer] --> L[log alasan] --> I[IndicatorRelease ATR] --> ES[EndSession alasan] --> C[CLogger.Close: flush terakhir] --> Z
```
