-- Kandidat sinyal per hari per simbol (spec 13 Req 8.3): frekuensi gerbang bias + zona dan jumlah entry.
-- Hari = tanggal UTC waktu bar LTF; hanya hari yang punya kandidat.
SELECT symbol,
       COUNT(DISTINCT date(time, 'unixepoch'))                                   AS days,
       COUNT(*)                                                                  AS candidates,
       ROUND(1.0 * COUNT(*) / COUNT(DISTINCT date(time, 'unixepoch')), 2)        AS per_day,
       SUM(CASE WHEN status = 'ACCEPTED' THEN 1 ELSE 0 END)                      AS accepted
FROM signals
GROUP BY symbol
ORDER BY symbol;
