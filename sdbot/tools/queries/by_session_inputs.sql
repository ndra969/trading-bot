-- Performa per setelan input (sessions.input_hash), untuk membandingkan backtest/optimasi.
SELECT s.input_hash,
       COUNT(DISTINCT s.id)       AS sessions,
       COUNT(v.position_id)       AS trades,
       ROUND(SUM(v.net_profit), 2) AS net_profit,
       ROUND(AVG(v.r_result), 3)  AS expectancy_r
FROM sessions s
JOIN v_trade_results v ON v.session_id = s.id AND v.closed_at IS NOT NULL
GROUP BY s.input_hash
ORDER BY expectancy_r DESC;
