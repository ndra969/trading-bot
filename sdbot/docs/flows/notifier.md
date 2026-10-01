# Notifier

`CNotifier` (lapisan Notify) adalah sink di `CTeeSink` di samping `CLogger`. Event masuk dinilai saat itu juga; pengiriman hanya dari `OnTimer` dan `OnDeinit` (spec 08).

```mermaid
flowchart TB
    E([AlertEvent / TradeRecord / ClosureRecord lewat tee]) --> K[tee memberi notify_key bila kosong; Logger menyimpan baris PENDING]
    K --> TR{event trade?}
    TR -->|TradeRecord RECONCILED| Z([hanya catat arah posisi])
    TR -->|TradeRecord EA / ClosureRecord| TA[buat alert TRADE_OPENED / TRADE_CLOSED, simpan lewat Logger]
    TR -->|alert| C
    TA --> C{Critical?}
    C -->|ya| Q[antre]
    C -->|tidak| CD{cooldown tipe bebas? akun: GV NT_CD_tipe, instance: memori}
    CD -->|tidak| S1[SKIPPED COOLDOWN]
    CD -->|ya| QT{kuota jam server, GV NT_QUOTA < 20?}
    QT -->|tidak| S2[SKIPPED QUOTA, HeldInHour + 1]
    QT -->|ya| CT[pakai cooldown dengan compare-and-set] --> Q
    Q --> F{antrean 100?}
    F -->|ya| O[non-Critical tertua SKIPPED OVERFLOW]
```

```mermaid
flowchart TB
    T([OnTimer]) --> ST[non-Critical > 30 menit sejak masuk antrean: SKIPPED STALE]
    ST --> P{masih jeda LIMITED?}
    P -->|ya| Z([selesai])
    P -->|tidak| PK[ambil Critical siap, lalu non-Critical siap, FIFO]
    PK --> SD[transport.Send: log di spec 08, Telegram di spec 09]
    SD --> R{hasil}
    R -->|OK| SENT[SENT + attempts + sent_at]
    R -->|TEMP, attempts < 3| RT[coba siklus berikutnya]
    R -->|TEMP ke-3 / PERM| FL[FAILED + alasan]
    R -->|LIMITED| W[jeda seluruh antrean retry_after]
    SENT --> N{sudah 2 kiriman?}
    RT --> N
    FL --> N
    N -->|tidak| P
    N -->|ya| Z
```

Status (`SENT`, `FAILED`, `SKIPPED` + alasan) dikirim ke `CLogger.OnAlertStatus` dan ditulis di flush yang sama dengan baris alert-nya (UPDATE per `login + notify_key`). Umur pesan dihitung dari waktu masuk antrean menurut waktu notifier (`TimeTradeServer` di live, `TimeCurrent` di tester), karena `TimeCurrent` berhenti saat pasar tutup.

Restart: `CLogger.TakeRestartAlerts` menandai `PENDING` instance dari sesi lalu (> 30 menit `STALE`, non-Critical muda `RESTART`) dan mengembalikan Critical muda untuk `Requeue`. Deinit: `DrainCritical` mengirim Critical tersisa maksimal 3 detik.
