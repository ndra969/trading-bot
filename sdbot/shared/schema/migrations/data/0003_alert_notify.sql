-- 0003: kunci notifikasi dan alasan status di alerts (spec 08 task 1, keputusan PC-13).
-- Notifier melaporkan hasil kirim sebelum baris alert pasti sudah di-flush dan saat DB bisa saja tidak
-- tersedia, jadi Logger memperbarui baris lewat notify_key (dibuat CTeeSink), bukan ID baris.
-- status_reason: COOLDOWN, QUOTA, STALE, OVERFLOW, RESTART, kode transport (enums.md alert_status_reason).
-- Baris lama mendapat kunci 'row-<id>' agar restart bisa mengantrekan ulang Critical yang masih PENDING.

ALTER TABLE alerts ADD COLUMN notify_key TEXT;
ALTER TABLE alerts ADD COLUMN status_reason TEXT;
UPDATE alerts SET notify_key = 'row-' || id WHERE notify_key IS NULL;
CREATE INDEX ix_alerts_login_key ON alerts (login, notify_key);
