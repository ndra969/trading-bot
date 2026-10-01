-- Jumlah alert per severity dan status kirim.
SELECT severity,
       status,
       COUNT(*) AS alerts
FROM alerts
GROUP BY severity, status
ORDER BY CASE severity WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, status;
