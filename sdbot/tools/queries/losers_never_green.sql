-- Loser yang tidak pernah profit (MFE < 0.2R): masalah arah/entry, bukan exit (pelajaran bot Python).
SELECT c.run_key,
       c.position_id,
       c.symbol,
       c.r_result,
       c.mfe_r,
       c.mae_r
FROM closures c
JOIN trades t ON t.login = c.login AND t.run_key = c.run_key AND t.position_id = c.position_id
WHERE c.r_result < 0 AND c.mfe_r < 0.2
ORDER BY c.r_result;
