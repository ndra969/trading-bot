-- Distribusi tahap tolak kandidat per simbol (spec 13 Req 8.3): gerbang mana yang paling sering memblokir.
-- ACCEPTED = kandidat yang menjadi posisi. share_pct = persen dari semua kandidat simbol itu.
SELECT symbol,
       COALESCE(reject_stage, 'ACCEPTED')                                              AS stage,
       COUNT(*)                                                                        AS signals,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY symbol), 1)           AS share_pct
FROM signals
GROUP BY symbol, stage
ORDER BY symbol, signals DESC, stage;
