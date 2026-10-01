-- Operasi saldo per bulan (UTC) dan run.
SELECT strftime('%Y-%m', time, 'unixepoch') AS month,
       run_key,
       op_type,
       COUNT(*)                             AS operations,
       ROUND(SUM(amount), 2)                AS amount
FROM balance_ops
GROUP BY month, run_key, op_type
ORDER BY month, run_key, op_type;
