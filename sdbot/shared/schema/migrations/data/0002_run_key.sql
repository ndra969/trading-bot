-- 0002: run_key memisahkan run backtest (spec 04 task 7, keputusan PC-08).
-- Di Strategy Tester, position ID dan deal ticket mulai dari angka kecil yang sama di setiap run,
-- dengan login yang sama, sehingga kunci (login, position_id) membuang baris run berikutnya.
-- run_key: 0 untuk live (posisi tetap unik per login lintas restart), ID sesi pertama run untuk
-- tester (restart harness di tengah run memakai run_key yang sama). Kunci unik menjadi
-- (login, run_key, <ID MT5>). SQLite tidak bisa mengubah UNIQUE, jadi tabel dibangun ulang.

DROP VIEW v_trade_results;

ALTER TABLE sessions ADD COLUMN run_key INTEGER NOT NULL DEFAULT 0;
UPDATE sessions SET run_key = id WHERE mode = 'TESTER';

ALTER TABLE position_events ADD COLUMN run_key INTEGER NOT NULL DEFAULT 0;
UPDATE position_events SET run_key = session_id WHERE session_id IN (SELECT id FROM sessions WHERE mode = 'TESTER');
CREATE INDEX ix_pos_events_run_position ON position_events (login, run_key, position_id);
DROP INDEX ix_pos_events_position;

-- trades
CREATE TABLE trades_v2 (
  id               INTEGER PRIMARY KEY,
  session_id       INTEGER NOT NULL,
  login            INTEGER NOT NULL,
  run_key          INTEGER NOT NULL DEFAULT 0,
  position_id      INTEGER NOT NULL,
  magic            INTEGER NOT NULL,
  symbol           TEXT    NOT NULL,
  direction        TEXT    NOT NULL CHECK (direction IN ('BUY','SELL')),
  source           TEXT    NOT NULL CHECK (source IN ('EA','RECONCILED')),
  volume_initial   REAL    NOT NULL,
  price_requested  REAL,
  price_open       REAL    NOT NULL,
  slippage_points  INTEGER,
  spread_points    INTEGER,
  sl_initial       REAL    NOT NULL,
  tp_initial       REAL    NOT NULL,
  risk_money       REAL,
  risk_pct         REAL,
  signal_id        INTEGER,
  ea_version       TEXT    NOT NULL,
  opened_at        INTEGER NOT NULL,
  UNIQUE (login, run_key, position_id)
);
INSERT INTO trades_v2 (id, session_id, login, run_key, position_id, magic, symbol, direction, source, volume_initial,
                       price_requested, price_open, slippage_points, spread_points, sl_initial, tp_initial, risk_money,
                       risk_pct, signal_id, ea_version, opened_at)
SELECT t.id, t.session_id, t.login, COALESCE(s.run_key, 0), t.position_id, t.magic, t.symbol, t.direction, t.source,
       t.volume_initial, t.price_requested, t.price_open, t.slippage_points, t.spread_points, t.sl_initial, t.tp_initial,
       t.risk_money, t.risk_pct, t.signal_id, t.ea_version, t.opened_at
FROM trades t LEFT JOIN sessions s ON s.id = t.session_id;
DROP TABLE trades;
ALTER TABLE trades_v2 RENAME TO trades;
CREATE INDEX ix_trades_login_opened ON trades (login, opened_at);

-- deals
CREATE TABLE deals_v2 (
  id           INTEGER PRIMARY KEY,
  session_id   INTEGER NOT NULL,
  login        INTEGER NOT NULL,
  run_key      INTEGER NOT NULL DEFAULT 0,
  deal_ticket  INTEGER NOT NULL,
  position_id  INTEGER NOT NULL,
  magic        INTEGER NOT NULL,
  symbol       TEXT    NOT NULL,
  time         INTEGER NOT NULL,
  entry        TEXT    NOT NULL CHECK (entry IN ('IN','OUT','INOUT','OUT_BY')),
  deal_type    TEXT    NOT NULL CHECK (deal_type IN ('BUY','SELL')),
  volume       REAL    NOT NULL,
  price        REAL    NOT NULL,
  reason       TEXT    NOT NULL,
  profit       REAL    NOT NULL,
  commission   REAL    NOT NULL,
  swap         REAL    NOT NULL,
  fee          REAL    NOT NULL,
  UNIQUE (login, run_key, deal_ticket)
);
INSERT INTO deals_v2 (id, session_id, login, run_key, deal_ticket, position_id, magic, symbol, time, entry, deal_type,
                      volume, price, reason, profit, commission, swap, fee)
SELECT d.id, d.session_id, d.login, COALESCE(s.run_key, 0), d.deal_ticket, d.position_id, d.magic, d.symbol, d.time,
       d.entry, d.deal_type, d.volume, d.price, d.reason, d.profit, d.commission, d.swap, d.fee
FROM deals d LEFT JOIN sessions s ON s.id = d.session_id;
DROP TABLE deals;
ALTER TABLE deals_v2 RENAME TO deals;
CREATE INDEX ix_deals_position ON deals (login, run_key, position_id);

-- closures
CREATE TABLE closures_v2 (
  id               INTEGER PRIMARY KEY,
  session_id       INTEGER NOT NULL,
  login            INTEGER NOT NULL,
  run_key          INTEGER NOT NULL DEFAULT 0,
  position_id      INTEGER NOT NULL,
  magic            INTEGER NOT NULL,
  symbol           TEXT    NOT NULL,
  closed_at        INTEGER NOT NULL,
  reason           TEXT    NOT NULL,
  level_price      REAL,
  price_close      REAL    NOT NULL,
  slippage_points  INTEGER,
  volume_total     REAL    NOT NULL,
  profit           REAL    NOT NULL,
  commission       REAL    NOT NULL,
  swap             REAL    NOT NULL,
  fee              REAL    NOT NULL,
  net_profit       REAL    NOT NULL,
  r_result         REAL,
  mfe_r            REAL,
  mae_r            REAL,
  holding_sec      INTEGER NOT NULL,
  be_activated     INTEGER NOT NULL CHECK (be_activated IN (0,1)),
  partial_done     INTEGER NOT NULL CHECK (partial_done IN (0,1)),
  trail_activated  INTEGER NOT NULL CHECK (trail_activated IN (0,1)),
  UNIQUE (login, run_key, position_id)
);
INSERT INTO closures_v2 (id, session_id, login, run_key, position_id, magic, symbol, closed_at, reason, level_price,
                         price_close, slippage_points, volume_total, profit, commission, swap, fee, net_profit, r_result,
                         mfe_r, mae_r, holding_sec, be_activated, partial_done, trail_activated)
SELECT c.id, c.session_id, c.login, COALESCE(s.run_key, 0), c.position_id, c.magic, c.symbol, c.closed_at, c.reason,
       c.level_price, c.price_close, c.slippage_points, c.volume_total, c.profit, c.commission, c.swap, c.fee,
       c.net_profit, c.r_result, c.mfe_r, c.mae_r, c.holding_sec, c.be_activated, c.partial_done, c.trail_activated
FROM closures c LEFT JOIN sessions s ON s.id = c.session_id;
DROP TABLE closures;
ALTER TABLE closures_v2 RENAME TO closures;
CREATE INDEX ix_closures_login_closed ON closures (login, closed_at);

-- balance_ops (tanpa session_id: baris lama tetap run_key 0)
CREATE TABLE balance_ops_v2 (
  id           INTEGER PRIMARY KEY,
  login        INTEGER NOT NULL,
  run_key      INTEGER NOT NULL DEFAULT 0,
  deal_ticket  INTEGER NOT NULL,
  time         INTEGER NOT NULL,
  op_type      TEXT    NOT NULL CHECK (op_type IN ('BALANCE','CREDIT')),
  amount       REAL    NOT NULL,
  comment      TEXT,
  UNIQUE (login, run_key, deal_ticket)
);
INSERT INTO balance_ops_v2 (id, login, run_key, deal_ticket, time, op_type, amount, comment)
SELECT id, login, 0, deal_ticket, time, op_type, amount, comment FROM balance_ops;
DROP TABLE balance_ops;
ALTER TABLE balance_ops_v2 RENAME TO balance_ops;

CREATE VIEW v_trade_results AS
SELECT t.login, t.run_key, t.position_id, t.symbol, t.direction, t.magic, t.ea_version, t.session_id,
       t.opened_at, c.closed_at, c.reason, t.volume_initial, t.price_open, c.price_close,
       t.risk_money, c.net_profit, c.r_result, c.mfe_r, c.mae_r, c.holding_sec,
       c.be_activated, c.partial_done, c.trail_activated, t.signal_id
FROM trades t
LEFT JOIN closures c ON c.login = t.login AND c.run_key = t.run_key AND c.position_id = t.position_id;
