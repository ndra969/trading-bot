# Alur SDBot EA (v1.12)

Diagram Mermaid alur utama EA, mengikuti kode di `ea/src/Include/SDBot/App/SdbApp.mqh` dan modul yang dipanggilnya. Diperbarui setiap spec yang mengubah alur (RULES §Definition of done).

| File | Isi | Spec |
|---|---|---|
| [init.md](init.md) | `OnInit` / `OnDeinit` | 02–09 |
| [tick.md](tick.md) | `OnTick`: analisis struktur, zona, dan pola PA, sinyal, manajemen posisi | 06, 10–13 |
| [structure.md](structure.md) | `CMarketStructure`: bar per TF, swing, BOS, EMA, bias HTF | 10 |
| [zones.md](zones.md) | `CZoneBook`: zona S&D H1, status, penanda Used | 11 |
| [pa-trigger.md](pa-trigger.md) | `CPaTrigger`: pola candle terarah M15, urutan, skor | 12 |
| [signals.md](signals.md) | `CSignalEngine`: kandidat, tahap tolak, skor, SL/TP, entry, telemetri | 13 |
| [timer.md](timer.md) | `OnTimer` tiap detik | 02–09 |
| [order-execution.md](order-execution.md) | lot, pre-trade check, `CExecutor::OpenMarket` | 04–05, 13 |
| [risk-monitor.md](risk-monitor.md) | `CRiskMonitor::Run` | 05 |
| [closure.md](closure.md) | `OnTradeTransaction`, closure, rekonsiliasi | 06 |
| [notifier.md](notifier.md) | `CNotifier`: penilaian, antrean, kirim, status, Telegram, push, pesan berjadwal | 08–09 |
