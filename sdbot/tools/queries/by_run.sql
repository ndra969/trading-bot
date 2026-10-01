-- Satu baris per run: live (run_key 0) dan setiap backtest (run_key = id sesi pertama run, PC-08).
SELECT v.run_key,
       COALESCE(s.mode, 'LIVE')     AS mode,
       MAX(v.ea_version)            AS ea_version,
       COUNT(*)                     AS trades,
       ROUND(SUM(v.net_profit), 2)  AS net_profit,
       ROUND(AVG(v.r_result), 3)    AS expectancy_r
FROM v_trade_results v
LEFT JOIN sessions s ON s.id = v.run_key
WHERE v.closed_at IS NOT NULL
GROUP BY v.run_key, s.mode
ORDER BY v.run_key;
