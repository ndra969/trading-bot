-- 0005: style intraday
-- SQL maju saja. Dilarang: BEGIN/COMMIT/ROLLBACK/PRAGMA/ATTACH/VACUUM/CREATE TRIGGER.
-- Kolom NOT NULL baru di tabel berisi data wajib punya DEFAULT.

-- Spec 34 (gaya intraday H1/M15/M5): signals.style menerima INTRADAY. SQLite tidak bisa mengubah CHECK di tempat,
-- jadi tabel dibangun ulang dengan kolom dan urutan yang sama, data disalin, indeks dibuat ulang.
CREATE TABLE signals_v5 (
  id             INTEGER PRIMARY KEY,
  session_id     INTEGER NOT NULL,
  login          INTEGER NOT NULL,
  magic          INTEGER NOT NULL,
  symbol         TEXT    NOT NULL,
  time           INTEGER NOT NULL,
  direction      TEXT    NOT NULL CHECK (direction IN ('BUY','SELL')),
  style          TEXT    NOT NULL CHECK (style IN ('SCALPING','DAY','SWING','POSITION','INTRADAY')),
  zone_ref       TEXT,
  score_total    REAL,
  spread_points  INTEGER NOT NULL,
  status         TEXT    NOT NULL CHECK (status IN ('ACCEPTED','REJECTED')),
  reject_stage   TEXT,
  reject_detail  TEXT,
  context_json   TEXT
);
INSERT INTO signals_v5 (id, session_id, login, magic, symbol, time, direction, style, zone_ref, score_total, spread_points,
                        status, reject_stage, reject_detail, context_json)
  SELECT id, session_id, login, magic, symbol, time, direction, style, zone_ref, score_total, spread_points,
         status, reject_stage, reject_detail, context_json FROM signals;
DROP TABLE signals;
ALTER TABLE signals_v5 RENAME TO signals;
CREATE INDEX ix_signals_login_time ON signals (login, time);
CREATE INDEX ix_signals_stage ON signals (reject_stage, time);
