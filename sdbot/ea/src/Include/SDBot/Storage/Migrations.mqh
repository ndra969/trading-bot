// GENERATED oleh sdbot/tools/schema.py — jangan diedit. Sumber: shared/schema/migrations/data/
#ifndef SDB_STORAGE_MIGRATIONS_MQH
#define SDB_STORAGE_MIGRATIONS_MQH

#include <SDBot/Storage/MigrationSource.mqh>

#define SDB_SCHEMA_LATEST 1

class CSdbDataMigrations : public ISdbMigrationSource
  {
public:
   int    Count()              { return 1; }
   int    Version(const int i) { return i + 1; }
   string Name(const int i)
     {
      switch(i)
        {
         case 0: return "initial";
        }
      return "";
     }
   string Checksum(const int i)
     {
      switch(i)
        {
         case 0: return "77d01d0c2ffd5cff11891823fcdf5c730af39f460b67bc1242e47d9fa1a06fe8";
        }
      return "";
     }
   int    Statements(const int i, string &out[])
     {
      ArrayFree(out);
      switch(i)
        {
         case 0:
            ArrayResize(out, 19);
            out[0] = "CREATE TABLE sessions (\n" +
                     "  id              INTEGER PRIMARY KEY,\n" +
                     "  login           INTEGER NOT NULL,\n" +
                     "  magic           INTEGER NOT NULL,\n" +
                     "  symbol          TEXT    NOT NULL,\n" +
                     "  mode            TEXT    NOT NULL CHECK (mode IN ('LIVE','TESTER')),\n" +
                     "  ea_version      TEXT    NOT NULL,\n" +
                     "  input_hash      TEXT    NOT NULL,\n" +
                     "  inputs_json     TEXT    NOT NULL,\n" +
                     "  started_at      INTEGER NOT NULL,\n" +
                     "  ended_at        INTEGER,\n" +
                     "  end_reason      TEXT,\n" +
                     "  tester_from     INTEGER,\n" +
                     "  tester_to       INTEGER,\n" +
                     "  tester_model    TEXT\n" +
                     ")";
            out[1] = "CREATE INDEX ix_sessions_login_started ON sessions (login, started_at)";
            out[2] = "CREATE TABLE accounts (\n" +
                     "  login                 INTEGER PRIMARY KEY,\n" +
                     "  server                TEXT    NOT NULL,\n" +
                     "  company               TEXT    NOT NULL,\n" +
                     "  account_type          TEXT    NOT NULL CHECK (account_type IN ('DEMO','REAL','CENT')),\n" +
                     "  margin_mode           TEXT    NOT NULL CHECK (margin_mode IN ('HEDGING','NETTING','EXCHANGE')),\n" +
                     "  currency              TEXT    NOT NULL,\n" +
                     "  leverage              INTEGER NOT NULL,\n" +
                     "  balance               REAL    NOT NULL,\n" +
                     "  equity                REAL    NOT NULL,\n" +
                     "  peak_equity           REAL    NOT NULL,\n" +
                     "  server_utc_offset_sec INTEGER NOT NULL,\n" +
                     "  updated_at            INTEGER NOT NULL\n" +
                     ")";
            out[3] = "CREATE TABLE signals (\n" +
                     "  id             INTEGER PRIMARY KEY,\n" +
                     "  session_id     INTEGER NOT NULL,\n" +
                     "  login          INTEGER NOT NULL,\n" +
                     "  magic          INTEGER NOT NULL,\n" +
                     "  symbol         TEXT    NOT NULL,\n" +
                     "  time           INTEGER NOT NULL,\n" +
                     "  direction      TEXT    NOT NULL CHECK (direction IN ('BUY','SELL')),\n" +
                     "  style          TEXT    NOT NULL CHECK (style IN ('SCALPING','DAY','SWING','POSITION')),\n" +
                     "  zone_ref       TEXT,\n" +
                     "  score_total    REAL,\n" +
                     "  spread_points  INTEGER NOT NULL,\n" +
                     "  status         TEXT    NOT NULL CHECK (status IN ('ACCEPTED','REJECTED')),\n" +
                     "  reject_stage   TEXT,\n" +
                     "  reject_detail  TEXT,\n" +
                     "  context_json   TEXT\n" +
                     ")";
            out[4] = "CREATE INDEX ix_signals_login_time ON signals (login, time)";
            out[5] = "CREATE INDEX ix_signals_stage ON signals (reject_stage, time)";
            out[6] = "CREATE TABLE signal_scores (\n" +
                     "  signal_id  INTEGER NOT NULL,\n" +
                     "  component  TEXT    NOT NULL,\n" +
                     "  score      REAL    NOT NULL,\n" +
                     "  max_score  REAL    NOT NULL,\n" +
                     "  PRIMARY KEY (signal_id, component)\n" +
                     ")";
            out[7] = "CREATE TABLE trades (\n" +
                     "  id               INTEGER PRIMARY KEY,\n" +
                     "  session_id       INTEGER NOT NULL,\n" +
                     "  login            INTEGER NOT NULL,\n" +
                     "  position_id      INTEGER NOT NULL,\n" +
                     "  magic            INTEGER NOT NULL,\n" +
                     "  symbol           TEXT    NOT NULL,\n" +
                     "  direction        TEXT    NOT NULL CHECK (direction IN ('BUY','SELL')),\n" +
                     "  source           TEXT    NOT NULL CHECK (source IN ('EA','RECONCILED')),\n" +
                     "  volume_initial   REAL    NOT NULL,\n" +
                     "  price_requested  REAL,\n" +
                     "  price_open       REAL    NOT NULL,\n" +
                     "  slippage_points  INTEGER,\n" +
                     "  spread_points    INTEGER,\n" +
                     "  sl_initial       REAL    NOT NULL,\n" +
                     "  tp_initial       REAL    NOT NULL,\n" +
                     "  risk_money       REAL,\n" +
                     "  risk_pct         REAL,\n" +
                     "  signal_id        INTEGER,\n" +
                     "  ea_version       TEXT    NOT NULL,\n" +
                     "  opened_at        INTEGER NOT NULL,\n" +
                     "  UNIQUE (login, position_id)\n" +
                     ")";
            out[8] = "CREATE INDEX ix_trades_login_opened ON trades (login, opened_at)";
            out[9] = "CREATE TABLE deals (\n" +
                     "  id           INTEGER PRIMARY KEY,\n" +
                     "  session_id   INTEGER NOT NULL,\n" +
                     "  login        INTEGER NOT NULL,\n" +
                     "  deal_ticket  INTEGER NOT NULL,\n" +
                     "  position_id  INTEGER NOT NULL,\n" +
                     "  magic        INTEGER NOT NULL,\n" +
                     "  symbol       TEXT    NOT NULL,\n" +
                     "  time         INTEGER NOT NULL,\n" +
                     "  entry        TEXT    NOT NULL CHECK (entry IN ('IN','OUT','INOUT','OUT_BY')),\n" +
                     "  deal_type    TEXT    NOT NULL CHECK (deal_type IN ('BUY','SELL')),\n" +
                     "  volume       REAL    NOT NULL,\n" +
                     "  price        REAL    NOT NULL,\n" +
                     "  reason       TEXT    NOT NULL,\n" +
                     "  profit       REAL    NOT NULL,\n" +
                     "  commission   REAL    NOT NULL,\n" +
                     "  swap         REAL    NOT NULL,\n" +
                     "  fee          REAL    NOT NULL,\n" +
                     "  UNIQUE (login, deal_ticket)\n" +
                     ")";
            out[10] = "CREATE INDEX ix_deals_position ON deals (login, position_id)";
            out[11] = "CREATE TABLE position_events (\n" +
                      "  id             INTEGER PRIMARY KEY,\n" +
                      "  session_id     INTEGER NOT NULL,\n" +
                      "  login          INTEGER NOT NULL,\n" +
                      "  position_id    INTEGER NOT NULL,\n" +
                      "  time           INTEGER NOT NULL,\n" +
                      "  type           TEXT    NOT NULL,\n" +
                      "  sl_old         REAL,\n" +
                      "  sl_new         REAL,\n" +
                      "  volume         REAL    NOT NULL,\n" +
                      "  price          REAL    NOT NULL,\n" +
                      "  spread_points  INTEGER NOT NULL,\n" +
                      "  detail         TEXT\n" +
                      ")";
            out[12] = "CREATE INDEX ix_pos_events_position ON position_events (login, position_id)";
            out[13] = "CREATE TABLE closures (\n" +
                      "  id               INTEGER PRIMARY KEY,\n" +
                      "  session_id       INTEGER NOT NULL,\n" +
                      "  login            INTEGER NOT NULL,\n" +
                      "  position_id      INTEGER NOT NULL,\n" +
                      "  magic            INTEGER NOT NULL,\n" +
                      "  symbol           TEXT    NOT NULL,\n" +
                      "  closed_at        INTEGER NOT NULL,\n" +
                      "  reason           TEXT    NOT NULL,\n" +
                      "  level_price      REAL,\n" +
                      "  price_close      REAL    NOT NULL,\n" +
                      "  slippage_points  INTEGER,\n" +
                      "  volume_total     REAL    NOT NULL,\n" +
                      "  profit           REAL    NOT NULL,\n" +
                      "  commission       REAL    NOT NULL,\n" +
                      "  swap             REAL    NOT NULL,\n" +
                      "  fee              REAL    NOT NULL,\n" +
                      "  net_profit       REAL    NOT NULL,\n" +
                      "  r_result         REAL,\n" +
                      "  mfe_r            REAL,\n" +
                      "  mae_r            REAL,\n" +
                      "  holding_sec      INTEGER NOT NULL,\n" +
                      "  be_activated     INTEGER NOT NULL CHECK (be_activated IN (0,1)),\n" +
                      "  partial_done     INTEGER NOT NULL CHECK (partial_done IN (0,1)),\n" +
                      "  trail_activated  INTEGER NOT NULL CHECK (trail_activated IN (0,1)),\n" +
                      "  UNIQUE (login, position_id)\n" +
                      ")";
            out[14] = "CREATE INDEX ix_closures_login_closed ON closures (login, closed_at)";
            out[15] = "CREATE TABLE balance_ops (\n" +
                      "  id           INTEGER PRIMARY KEY,\n" +
                      "  login        INTEGER NOT NULL,\n" +
                      "  deal_ticket  INTEGER NOT NULL,\n" +
                      "  time         INTEGER NOT NULL,\n" +
                      "  op_type      TEXT    NOT NULL CHECK (op_type IN ('BALANCE','CREDIT')),\n" +
                      "  amount       REAL    NOT NULL,\n" +
                      "  comment      TEXT,\n" +
                      "  UNIQUE (login, deal_ticket)\n" +
                      ")";
            out[16] = "CREATE TABLE alerts (\n" +
                      "  id          INTEGER PRIMARY KEY,\n" +
                      "  session_id  INTEGER NOT NULL,\n" +
                      "  login       INTEGER NOT NULL,\n" +
                      "  magic       INTEGER NOT NULL,\n" +
                      "  symbol      TEXT    NOT NULL,\n" +
                      "  time        INTEGER NOT NULL,\n" +
                      "  type        TEXT    NOT NULL,\n" +
                      "  severity    TEXT    NOT NULL CHECK (severity IN ('INFO','MEDIUM','HIGH','CRITICAL')),\n" +
                      "  message     TEXT    NOT NULL,\n" +
                      "  status      TEXT    NOT NULL CHECK (status IN ('PENDING','SENT','FAILED','SKIPPED')),\n" +
                      "  attempts    INTEGER NOT NULL DEFAULT 0,\n" +
                      "  sent_at     INTEGER\n" +
                      ")";
            out[17] = "CREATE INDEX ix_alerts_status_time ON alerts (status, time)";
            out[18] = "CREATE VIEW v_trade_results AS\n" +
                      "SELECT t.login, t.position_id, t.symbol, t.direction, t.magic, t.ea_version, t.session_id,\n" +
                      "       t.opened_at, c.closed_at, c.reason, t.volume_initial, t.price_open, c.price_close,\n" +
                      "       t.risk_money, c.net_profit, c.r_result, c.mfe_r, c.mae_r, c.holding_sec,\n" +
                      "       c.be_activated, c.partial_done, c.trail_activated, t.signal_id\n" +
                      "FROM trades t\n" +
                      "LEFT JOIN closures c ON c.login = t.login AND c.position_id = t.position_id";
            return 19;
        }
      return 0;
     }
  };

#endif // SDB_STORAGE_MIGRATIONS_MQH
