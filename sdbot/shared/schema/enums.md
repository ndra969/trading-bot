# Enum SDBot

Satu-satunya sumber nilai teks enum di database SDBot (spec 03 Req 6). `sdbot/tools/schema.py build` membaca tabel di bawah untuk:

- menghasilkan konstanta MQL5 di `ea/src/Include/SDBot/Core/SchemaEnums.mqh` (`SDB_<ENUM>_<NILAI>`, misalnya `SDB_CLOSE_REASON_TP`), dipakai kode EA alih-alih literal;
- mencocokkan `CHECK (kolom IN (...))` di skema dengan kolom "CHECK" = `ya`. Enum `tidak` sengaja tanpa `CHECK` karena nilainya akan bertambah (mengubah `CHECK` di SQLite berarti membangun ulang tabel).

Aturan penulisan: nilai huruf besar dengan `_`, dalam backtick, dipisah koma. Kolom ditulis `tabel.kolom`. Menambah nilai: edit tabel ini, lalu `schema.py build`; untuk enum `ya`, juga buat migrasi yang membangun ulang tabelnya.

| Enum | Nilai | CHECK | Kolom |
|---|---|---|---|
| `direction` | `BUY`, `SELL` | ya | `signals.direction`, `trades.direction` |
| `deal_type` | `BUY`, `SELL` | ya | `deals.deal_type` |
| `session_mode` | `LIVE`, `TESTER` | ya | `sessions.mode` |
| `account_type` | `DEMO`, `REAL`, `CENT` | ya | `accounts.account_type` |
| `margin_mode` | `HEDGING`, `NETTING`, `EXCHANGE` | ya | `accounts.margin_mode` |
| `trading_style` | `SCALPING`, `DAY`, `SWING`, `POSITION` | ya | `signals.style` |
| `signal_status` | `ACCEPTED`, `REJECTED` | ya | `signals.status` |
| `trade_source` | `EA`, `RECONCILED` | ya | `trades.source` |
| `deal_entry` | `IN`, `OUT`, `INOUT`, `OUT_BY` | ya | `deals.entry` |
| `balance_op_type` | `BALANCE`, `CREDIT` | ya | `balance_ops.op_type` |
| `severity` | `INFO`, `MEDIUM`, `HIGH`, `CRITICAL` | ya | `alerts.severity` |
| `alert_status` | `PENDING`, `SENT`, `FAILED`, `SKIPPED` | ya | `alerts.status` |
| `close_reason` | `TP`, `SL`, `BE_STOP`, `TRAIL_STOP`, `MANUAL`, `STOP_OUT`, `EA_CLOSE`, `ROLLOVER`, `OTHER` | tidak | `closures.reason` |
| `deal_reason` | `CLIENT`, `MOBILE`, `WEB`, `EXPERT`, `SL`, `TP`, `SO`, `ROLLOVER`, `VMARGIN`, `SPLIT`, `OTHER` | tidak | `deals.reason` |
| `position_event` | `BE`, `PARTIAL`, `PARTIAL_SKIPPED`, `TRAILING`, `MODIFY_FAILED`, `SL_RESTORED` | tidak | `position_events.type` |
| `reject_stage` | `STOPPED`, `DAILY_PAUSE`, `NOT_TRADABLE`, `MAX_OPEN_RISK`, `MARGIN_LOW`, `CURRENCY_EXPOSURE`, `NEWS_BLACKOUT`, `OUTSIDE_SESSION`, `SPREAD_TOO_WIDE`, `NO_HTF_BIAS`, `NO_VALID_ZONE`, `ZONE_USED`, `NO_PA_TRIGGER`, `SCORE_TOO_LOW`, `RR_TOO_LOW`, `SL_TOO_CLOSE`, `INVALID_STOPS`, `INVALID_VOLUME`, `LOT_BELOW_MIN`, `BROKER_REJECTED`, `OTHER` | tidak | `signals.reject_stage` |
| `alert_type` | `ACCOUNT_REJECTED`, `CONN_DOWN`, `CONN_UP`, `DB_UNAVAILABLE`, `DB_RECOVERED`, `DB_NEWER_SCHEMA`, `MIGRATION_FAILED`, `ORDER_FAILED`, `MODIFY_FAILED`, `DD_INFO`, `DD_REDUCE`, `DD_RECOVERED`, `DD_STOP`, `DAILY_LOSS`, `MARGIN_LOW`, `MARGIN_OK`, `CLOSE_ALL_FAILED`, `EMERGENCY_RESET`, `BALANCE_OP`, `STATE_RESET`, `SL_RESTORED` | tidak | `alerts.type` |
| `deinit_reason` | `PROGRAM`, `REMOVE`, `RECOMPILE`, `CHARTCHANGE`, `CHARTCLOSE`, `PARAMETERS`, `ACCOUNT`, `TEMPLATE`, `INITFAILED`, `CLOSE`, `OTHER` | tidak | `sessions.end_reason` |
