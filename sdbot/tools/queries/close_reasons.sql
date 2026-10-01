-- Distribusi alasan tutup dan rata-rata R (spec 07 Req 3.1): kebocoran SL/BE_STOP/TRAIL_STOP terlihat di sini.
SELECT reason,
       COUNT(*)                 AS closures,
       ROUND(AVG(r_result), 3)  AS avg_r
FROM closures
GROUP BY reason
ORDER BY closures DESC, reason;
