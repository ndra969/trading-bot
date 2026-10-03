-- Pola PA pemicu vs R hasil (kekuatan PA 10/7/3 layak dipertahankan?). (spec 13 Req 8.3)
-- Trade dari sinyal ACCEPTED Fase 3 (punya context_json); posisi digabung dengan login + run_key + position_id (PC-08).
SELECT json_extract(s.context_json, '$.pa') AS pattern,
       COUNT(*)                                                      AS trades,
       ROUND(100.0 * SUM(CASE WHEN c.r_result > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_rate,
       ROUND(AVG(c.r_result), 3)                                     AS expectancy_r
FROM signals s
JOIN trades t   ON t.signal_id = s.id AND t.login = s.login
JOIN closures c ON c.login = t.login AND c.run_key = t.run_key AND c.position_id = t.position_id
WHERE s.status = 'ACCEPTED' AND s.context_json IS NOT NULL AND c.r_result IS NOT NULL
GROUP BY pattern
ORDER BY pattern;
