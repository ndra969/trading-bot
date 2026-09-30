-- GENERATED oleh sdbot/tools/schema.py — jangan diedit.
-- Snapshot skema data terbaru dari shared/schema/migrations/data/, untuk dibaca.
-- Tabel schema_migrations dibuat oleh runner migrasi (EA/API):

CREATE TABLE IF NOT EXISTS schema_migrations (
  version     INTEGER PRIMARY KEY,
  name        TEXT    NOT NULL,
  checksum    TEXT    NOT NULL,
  applied_at  INTEGER NOT NULL,
  applied_by  TEXT    NOT NULL
);

CREATE TABLE accounts (
  login                 INTEGER PRIMARY KEY,
  server                TEXT    NOT NULL,
  company               TEXT    NOT NULL,
  account_type          TEXT    NOT NULL CHECK (account_type IN ('DEMO','REAL','CENT')),
  margin_mode           TEXT    NOT NULL CHECK (margin_mode IN ('HEDGING','NETTING','EXCHANGE')),
  currency              TEXT    NOT NULL,
  leverage              INTEGER NOT NULL,
  balance               REAL    NOT NULL,
  equity                REAL    NOT NULL,
  peak_equity           REAL    NOT NULL,
  server_utc_offset_sec INTEGER NOT NULL,
  updated_at            INTEGER NOT NULL
);

CREATE TABLE alerts (
  id          INTEGER PRIMARY KEY,
  session_id  INTEGER NOT NULL,
  login       INTEGER NOT NULL,
  magic       INTEGER NOT NULL,
  symbol      TEXT    NOT NULL,
  time        INTEGER NOT NULL,
  type        TEXT    NOT NULL,
  severity    TEXT    NOT NULL CHECK (severity IN ('INFO','MEDIUM','HIGH','CRITICAL')),
  message     TEXT    NOT NULL,
  status      TEXT    NOT NULL CHECK (status IN ('PENDING','SENT','FAILED','SKIPPED')),
  attempts    INTEGER NOT NULL DEFAULT 0,
  sent_at     INTEGER
);

CREATE TABLE "balance_ops" (
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

CREATE TABLE "closures" (
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

CREATE TABLE "deals" (
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

CREATE TABLE position_events (
  id             INTEGER PRIMARY KEY,
  session_id     INTEGER NOT NULL,
  login          INTEGER NOT NULL,
  position_id    INTEGER NOT NULL,
  time           INTEGER NOT NULL,
  type           TEXT    NOT NULL,
  sl_old         REAL,
  sl_new         REAL,
  volume         REAL    NOT NULL,
  price          REAL    NOT NULL,
  spread_points  INTEGER NOT NULL,
  detail         TEXT
, run_key INTEGER NOT NULL DEFAULT 0);

CREATE TABLE sessions (
  id              INTEGER PRIMARY KEY,
  login           INTEGER NOT NULL,
  magic           INTEGER NOT NULL,
  symbol          TEXT    NOT NULL,
  mode            TEXT    NOT NULL CHECK (mode IN ('LIVE','TESTER')),
  ea_version      TEXT    NOT NULL,
  input_hash      TEXT    NOT NULL,
  inputs_json     TEXT    NOT NULL,
  started_at      INTEGER NOT NULL,
  ended_at        INTEGER,
  end_reason      TEXT,
  tester_from     INTEGER,
  tester_to       INTEGER,
  tester_model    TEXT
, run_key INTEGER NOT NULL DEFAULT 0);

CREATE TABLE signal_scores (
  signal_id  INTEGER NOT NULL,
  component  TEXT    NOT NULL,
  score      REAL    NOT NULL,
  max_score  REAL    NOT NULL,
  PRIMARY KEY (signal_id, component)
);

CREATE TABLE signals (
  id             INTEGER PRIMARY KEY,
  session_id     INTEGER NOT NULL,
  login          INTEGER NOT NULL,
  magic          INTEGER NOT NULL,
  symbol         TEXT    NOT NULL,
  time           INTEGER NOT NULL,
  direction      TEXT    NOT NULL CHECK (direction IN ('BUY','SELL')),
  style          TEXT    NOT NULL CHECK (style IN ('SCALPING','DAY','SWING','POSITION')),
  zone_ref       TEXT,
  score_total    REAL,
  spread_points  INTEGER NOT NULL,
  status         TEXT    NOT NULL CHECK (status IN ('ACCEPTED','REJECTED')),
  reject_stage   TEXT,
  reject_detail  TEXT,
  context_json   TEXT
);

CREATE TABLE "trades" (
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

CREATE INDEX ix_alerts_status_time ON alerts (status, time);

CREATE INDEX ix_closures_login_closed ON closures (login, closed_at);

CREATE INDEX ix_deals_position ON deals (login, run_key, position_id);

CREATE INDEX ix_pos_events_run_position ON position_events (login, run_key, position_id);

CREATE INDEX ix_sessions_login_started ON sessions (login, started_at);

CREATE INDEX ix_signals_login_time ON signals (login, time);

CREATE INDEX ix_signals_stage ON signals (reject_stage, time);

CREATE INDEX ix_trades_login_opened ON trades (login, opened_at);

CREATE VIEW v_trade_results AS
SELECT t.login, t.run_key, t.position_id, t.symbol, t.direction, t.magic, t.ea_version, t.session_id,
       t.opened_at, c.closed_at, c.reason, t.volume_initial, t.price_open, c.price_close,
       t.risk_money, c.net_profit, c.r_result, c.mfe_r, c.mae_r, c.holding_sec,
       c.be_activated, c.partial_done, c.trail_activated, t.signal_id
FROM trades t
LEFT JOIN closures c ON c.login = t.login AND c.run_key = t.run_key AND c.position_id = t.position_id;
