-- Ringkasan hasil per simbol dan versi EA (spec 07 Req 3.1). Hanya posisi yang sudah tutup.
SELECT symbol,
       ea_version,
       COUNT(*)                                                         AS trades,
       ROUND(AVG(CASE WHEN net_profit > 0 THEN 1.0 ELSE 0.0 END), 3)   AS win_rate,
       ROUND(SUM(CASE WHEN net_profit > 0 THEN net_profit ELSE 0 END) /
             NULLIF(-SUM(CASE WHEN net_profit < 0 THEN net_profit ELSE 0 END), 0), 3) AS profit_factor,
       ROUND(AVG(r_result), 3)                                          AS expectancy_r
FROM v_trade_results
WHERE closed_at IS NOT NULL
GROUP BY symbol, ea_version
ORDER BY symbol, ea_version;
