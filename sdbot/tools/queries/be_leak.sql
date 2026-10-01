-- Kebocoran breakeven (pelajaran bot Python): BE-stop padahal MFE sempat >= 1R.
SELECT c.run_key,
       c.position_id,
       c.symbol,
       c.r_result,
       c.mfe_r,
       ROUND(c.mfe_r - c.r_result, 3) AS leaked_r
FROM closures c
JOIN trades t ON t.login = c.login AND t.run_key = c.run_key AND t.position_id = c.position_id
WHERE c.reason = 'BE_STOP' AND c.mfe_r >= 1
ORDER BY leaked_r DESC;
