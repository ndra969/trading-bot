-- 0004: signal score active
-- SQL maju saja. Dilarang: BEGIN/COMMIT/ROLLBACK/PRAGMA/ATTACH/VACUUM/CREATE TRIGGER.
-- Kolom NOT NULL baru di tabel berisi data wajib punya DEFAULT.


-- Spec 17 (PC-25): komponen skor Fase 5 dicatat dalam mode bayangan. active = 1 ikut skor gerbang
-- (signals.score_total), 0 = bayangan. Baris lama (ZONE/TREND/PA) semuanya ikut skor gerbang.
ALTER TABLE signal_scores ADD COLUMN active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1));
