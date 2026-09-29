-- Data contoh per versi skema, dipakai schema.py:
--  - uji migrasi bertahap: DB versi N-1 diisi blok <= N-1, lalu migrasi N diterapkan;
--  - fixture data_latest_sample.sqlite untuk uji query (spec 07) dan API backoffice.
-- Tambahkan blok "-- @version N" baru bila migrasi N menambah tabel atau kolom.
-- Waktu UTC epoch detik. Login 12345 (akun cent USC), 4 pair dengan magic blok SDBot.

-- @version 1

INSERT INTO sessions (id, login, magic, symbol, mode, ea_version, input_hash, inputs_json, started_at, ended_at, end_reason)
VALUES (1, 12345, 2026091901, 'EURUSDc', 'LIVE', '1.06', 'hash-a', '{"InpRiskPerTradePct":0.5}', 1790640000, 1790726400, 'REMOVE'),
       (2, 12345, 2026091903, 'EURJPYc', 'LIVE', '1.06', 'hash-a', '{"InpRiskPerTradePct":0.5}', 1790640000, NULL, NULL);

INSERT INTO accounts (login, server, company, account_type, margin_mode, currency, leverage, balance, equity, peak_equity, server_utc_offset_sec, updated_at)
VALUES (12345, 'Exness-MT5Real20', 'Exness Technologies Ltd', 'CENT', 'HEDGING', 'USC', 500, 100500.0, 100350.0, 101000.0, 10800, 1790726400);

INSERT INTO signals (id, session_id, login, magic, symbol, time, direction, style, zone_ref, score_total, spread_points, status, reject_stage, reject_detail)
VALUES (1, 1, 12345, 2026091901, 'EURUSDc', 1790643600, 'BUY', 'DAY', 'H1-D-1790600000', 72, 8, 'ACCEPTED', NULL, NULL),
       (2, 1, 12345, 2026091901, 'EURUSDc', 1790650800, 'SELL', 'DAY', 'H1-S-1790610000', 58, 9, 'REJECTED', 'SCORE_TOO_LOW', 'score=58 min=65'),
       (3, 2, 12345, 2026091903, 'EURJPYc', 1790654400, 'BUY', 'DAY', NULL, NULL, 35, 'REJECTED', 'NO_PA_TRIGGER', NULL);

INSERT INTO signal_scores (signal_id, component, score, max_score)
VALUES (1, 'ZONE', 30, 30), (1, 'FIBONACCI', 15, 15), (1, 'TREND', 15, 15), (1, 'PRICE_ACTION', 7, 10), (1, 'RSI', 5, 5),
       (2, 'ZONE', 15, 30), (2, 'FIBONACCI', 8, 15), (2, 'TREND', 15, 15), (2, 'PRICE_ACTION', 10, 10), (2, 'RSI', 0, 5);

-- Posisi 1: TP; posisi 2: BE-stop padahal MFE 1.2R (kebocoran BE); posisi 3: loser yang tidak
-- pernah profit (entry salah arah); posisi 4: trailing-stop; posisi 5: hasil rekonsiliasi (NULL).
INSERT INTO trades (session_id, login, position_id, magic, symbol, direction, source, volume_initial, price_requested, price_open,
                    slippage_points, spread_points, sl_initial, tp_initial, risk_money, risk_pct, signal_id, ea_version, opened_at)
VALUES (1, 12345, 5000000001, 2026091901, 'EURUSDc', 'BUY', 'EA', 0.10, 1.10000, 1.10002, -2, 8, 1.09800, 1.10500, 500.0, 0.5, 1, '1.06', 1790643660),
       (1, 12345, 5000000002, 2026091901, 'EURUSDc', 'SELL', 'EA', 0.10, 1.10500, 1.10500, 0, 9, 1.10700, 1.10000, 500.0, 0.5, NULL, '1.06', 1790647200),
       (2, 12345, 5000000003, 2026091903, 'EURJPYc', 'BUY', 'EA', 0.05, 161.500, 161.503, -3, 35, 161.300, 162.000, 480.0, 0.48, NULL, '1.06', 1790650800),
       (2, 12345, 5000000004, 2026091903, 'EURJPYc', 'SELL', 'EA', 0.05, 162.000, 161.998, -2, 34, 162.200, 161.400, 500.0, 0.5, NULL, '1.06', 1790661600),
       (2, 12345, 5000000005, 2026091904, 'GBPJPYc', 'BUY', 'RECONCILED', 0.02, NULL, 190.000, NULL, NULL, 189.700, 191.000, NULL, NULL, NULL, '1.06', 1790665200);

INSERT INTO deals (session_id, login, deal_ticket, position_id, magic, symbol, time, entry, deal_type, volume, price, reason, profit, commission, swap, fee)
VALUES (1, 12345, 7000000001, 5000000001, 2026091901, 'EURUSDc', 1790643660, 'IN',  'BUY',  0.10, 1.10002, 'EXPERT', 0, 0, 0, 0),
       (1, 12345, 7000000002, 5000000001, 2026091901, 'EURUSDc', 1790650000, 'OUT', 'SELL', 0.05, 1.10300, 'EXPERT', 1490, 0, 0, 0),
       (1, 12345, 7000000003, 5000000001, 2026091901, 'EURUSDc', 1790654000, 'OUT', 'SELL', 0.05, 1.10500, 'TP', 2490, 0, -12, 0),
       (1, 12345, 7000000004, 5000000002, 2026091901, 'EURUSDc', 1790647200, 'IN',  'SELL', 0.10, 1.10500, 'EXPERT', 0, 0, 0, 0),
       (1, 12345, 7000000005, 5000000002, 2026091901, 'EURUSDc', 1790652000, 'OUT', 'BUY',  0.10, 1.10490, 'SL', 100, 0, 0, 0),
       (2, 12345, 7000000006, 5000000003, 2026091903, 'EURJPYc', 1790650800, 'IN',  'BUY',  0.05, 161.503, 'EXPERT', 0, 0, 0, 0),
       (2, 12345, 7000000007, 5000000003, 2026091903, 'EURJPYc', 1790655000, 'OUT', 'SELL', 0.05, 161.298, 'SL', -490, 0, 0, 0),
       (2, 12345, 7000000008, 5000000004, 2026091903, 'EURJPYc', 1790661600, 'IN',  'SELL', 0.05, 161.998, 'EXPERT', 0, 0, 0, 0),
       (2, 12345, 7000000009, 5000000004, 2026091903, 'EURJPYc', 1790670000, 'OUT', 'BUY',  0.05, 161.720, 'SL', 700, 0, -8, 0);

INSERT INTO position_events (session_id, login, position_id, time, type, sl_old, sl_new, volume, price, spread_points, detail)
VALUES (1, 12345, 5000000001, 1790648000, 'BE', 1.09800, 1.10012, 0.10, 1.10210, 8, NULL),
       (1, 12345, 5000000001, 1790650000, 'PARTIAL', NULL, NULL, 0.05, 1.10300, 8, NULL),
       (1, 12345, 5000000002, 1790650000, 'BE', 1.10700, 1.10489, 0.10, 1.10290, 9, NULL),
       (2, 12345, 5000000004, 1790664000, 'BE', 162.200, 161.962, 0.05, 161.790, 34, NULL),
       (2, 12345, 5000000004, 1790666000, 'TRAILING', 161.962, 161.720, 0.05, 161.500, 33, NULL);

INSERT INTO closures (session_id, login, position_id, magic, symbol, closed_at, reason, level_price, price_close, slippage_points,
                      volume_total, profit, commission, swap, fee, net_profit, r_result, mfe_r, mae_r, holding_sec,
                      be_activated, partial_done, trail_activated)
VALUES (1, 12345, 5000000001, 2026091901, 'EURUSDc', 1790654000, 'TP', 1.10500, 1.10500, 0, 0.10, 3980, 0, -12, 0, 3968, 7.94, 2.5, 0.2, 10340, 1, 1, 0),
       (1, 12345, 5000000002, 2026091901, 'EURUSDc', 1790652000, 'BE_STOP', 1.10489, 1.10490, -1, 0.10, 100, 0, 0, 0, 100, 0.2, 1.2, 0.1, 4800, 1, 0, 0),
       (2, 12345, 5000000003, 2026091903, 'EURJPYc', 1790655000, 'SL', 161.300, 161.298, -2, 0.05, -490, 0, 0, 0, -490, -1.02, 0.1, 1.0, 4200, 0, 0, 0),
       (2, 12345, 5000000004, 2026091903, 'EURJPYc', 1790670000, 'TRAIL_STOP', 161.720, 161.720, 0, 0.05, 700, 0, -8, 0, 692, 1.38, 2.0, 0.3, 8400, 1, 0, 1);

-- Deal ticket di atas 2^32 memastikan kolom 64-bit terbaca utuh.
INSERT INTO balance_ops (login, deal_ticket, time, op_type, amount, comment)
VALUES (12345, 7000000010, 1790600000, 'BALANCE', 100000.0, 'deposit awal'),
       (12345, 7000000011, 1790700000, 'BALANCE', -20000.0, 'penarikan');

INSERT INTO alerts (session_id, login, magic, symbol, time, type, severity, message, status, attempts, sent_at)
VALUES (1, 12345, 2026091901, 'EURUSDc', 1790640005, 'CONN_UP', 'INFO', 'Koneksi terminal pulih', 'SENT', 1, 1790640006),
       (2, 12345, 2026091903, 'EURJPYc', 1790700000, 'BALANCE_OP', 'INFO', 'Penarikan -20000 USC', 'PENDING', 0, NULL),
       (2, 12345, 2026091903, 'EURJPYc', 1790701000, 'DD_REDUCE', 'HIGH', 'Drawdown 10%: lot x 0.5', 'FAILED', 3, NULL);
