# Alur SDBot EA (v1.07)

Diagram Mermaid alur utama EA, mengikuti kode di `ea/src/Include/SDBot/App/SdbApp.mqh` dan modul yang dipanggilnya. Diperbarui setiap spec yang mengubah alur (RULES §Definition of done).

| File | Isi | Spec |
|---|---|---|
| [init.md](init.md) | `OnInit` / `OnDeinit` | 02–08 |
| [tick.md](tick.md) | `OnTick`: manajemen posisi | 06 |
| [timer.md](timer.md) | `OnTimer` tiap detik | 02–08 |
| [order-execution.md](order-execution.md) | lot, pre-trade check, `CExecutor::OpenMarket` | 04–05 |
| [risk-monitor.md](risk-monitor.md) | `CRiskMonitor::Run` | 05 |
| [closure.md](closure.md) | `OnTradeTransaction`, closure, rekonsiliasi | 06 |
| [notifier.md](notifier.md) | `CNotifier`: penilaian, antrean, kirim, status | 08 |
