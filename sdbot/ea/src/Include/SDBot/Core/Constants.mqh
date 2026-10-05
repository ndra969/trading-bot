//+------------------------------------------------------------------+
//| Constants.mqh — angka tetap dari PRD yang bukan input. Mengubahnya
//| berarti mengubah perilaku EA: catat di docs/PENDING-CHANGES.md.
//+------------------------------------------------------------------+
#ifndef SDB_CORE_CONSTANTS_MQH
#define SDB_CORE_CONSTANTS_MQH

#define SDB_TIMER_SEC                 1        // risk monitor dan koneksi dicek tiap detik (PRD)
#define SDB_DISCONNECT_ALERT_SEC      300      // putus > 5 menit memicu alert Medium (PRD)
#define SDB_CONN_ALERT_REPEAT_SEC     300      // alert putus diulang paling sering tiap 5 menit
#define SDB_LOG_THROTTLE_DEFAULT_SEC  60       // pesan berulang dicetak paling sering sekali per menit
#define SDB_LOG_THROTTLE_SLOTS        64       // batas kunci throttle agar tabel tidak tumbuh tanpa batas
#define SDB_CENT_CURRENCIES           "USC,EUC"
#define SDB_GV_PREFIX                 "SDB"
#define SDB_GV_TOUCH_SEC              86400    // MT5 menghapus GV yang tidak diakses 4 minggu
#define SDB_MAGIC_MIN                 2026091901  // blok magic SDBot (keputusan R2-1)
#define SDB_MAGIC_MAX                 2026091999
#define SDB_MAGIC_HARNESS             2026091900  // dicadangkan untuk harness uji

// Storage (spec 03 design §4). File di folder Common agar backoffice dan semua instance melihatnya.
#define SDB_DB_FILE_LIVE              "sdbot.sqlite"
#define SDB_DB_FILE_TESTER            "sdbot_tester.sqlite"
#define SDB_DB_FILE_UNITTEST          "sdbot_unittest.sqlite"
#define SDB_DB_BUSY_TIMEOUT_MS        500      // tunggu kunci maksimal ini per flush, lalu coba detik berikutnya
#define SDB_DB_QUEUE_MAX              2000     // kapasitas antrean tulis
#define SDB_DB_UNAVAILABLE_ALERT_SEC  300      // DB tidak bisa ditulis selama ini -> alert High sekali
#define SDB_DB_REOPEN_SEC             60       // buka ulang file yang gagal/hilang paling sering sekali per menit

// Eksekusi (spec 04 design §5).
#define SDB_MAX_RETRY                 3        // ulangan setelah kiriman pertama (retcode sementara/ambigu)
#define SDB_RETRY_DELAY_MS            500
#define SDB_MAX_DEVIATION_POINTS      10       // PRD tidak mengatur; kandidat input di Fase 3
#define SDB_COMMENT_PREFIX            "SDB|"
#define SDB_COMMENT_MAX_LEN           31       // batas komentar order MT5
#define SDB_REQUEST_ID_LEN            4
#define SDB_AMBIGUOUS_LOOKBACK_SEC    300      // cari posisi/deal dengan ID permintaan sejauh ini ke belakang
#define SDB_ACCOUNT_SNAPSHOT_SEC      60

//--- Risk management (spec 05 design §5; angka dari PRD §Risk management kecuali disebut)
#define SDB_DD_INFO_PCT                  5.0
#define SDB_DD_RECOVER_PCT               8.0     // flag lot x 0.5 dicabut di bawah ini
#define SDB_DD_RECOVER_RATIO             0.8     // = 8 / 10 PRD; ambang pulih bila InpDDReducePct < 10 (histeresis)
#define SDB_MARGIN_ALERT_PCT             300.0
#define SDB_MARGIN_BLOCK_PCT             200.0
#define SDB_NO_SL_RISK_PCT               1.0     // posisi SDBot tanpa SL (PC-09)
#define SDB_CLOSE_ALL_RETRY_SEC          5
#define SDB_CLOSE_ALL_CLOSED_MARKET_SEC  60      // PC-09
#define SDB_CLOSE_ALL_ALERT_FAILS        3
#define SDB_CLOSE_ALL_ALERT_REPEAT_SEC   900
#define SDB_BALANCE_SCAN_SEC             10
#define SDB_CAS_RETRY                    5
#define SDB_RISK_EPS                     1e-9    // toleransi perbandingan persen risiko
#define SDB_LOT_FIT_STEPS                5       // maks langkah turun lot agar rugi pembulatan broker <= risiko
#define SDB_MARKET_CLOSED_BACKOFF_SEC    60      // setelah retcode 10018, request simbol ditahan sekian detik
// Batas posisi per kategori aset (PC-10), default dari config/active_symbols.yaml bot Python.
#define SDB_DEF_MAX_POS_FOREX_MAJOR      5
#define SDB_DEF_MAX_POS_FOREX_CROSS      3
#define SDB_DEF_MAX_POS_COMMODITY        1
#define SDB_DEF_MAX_POS_CRYPTO           1
#define SDB_MAX_POS_PER_CLASS            20
#define SDB_MAX_POS_OTHER_CLASS          1       // simbol yang kategorinya tidak dikenali (EC-25)
#define SDB_COMMODITY_CURRENCIES         "XAU,XAG,XPT,XPD"
#define SDB_CRYPTO_CURRENCIES            "BTC,ETH,LTC,XRP,BCH,SOL,ADA,DOT,DOGE,BNB"

//--- Manajemen posisi (spec 06 design §5; angka PRD kecuali disebut)
#define SDB_MIN_SL_STEP_POINTS           5       // geser SL minimal 5 point (PRD)
#define SDB_MODIFY_COOLDOWN_SEC          30      // retry modify tiap 30 detik (PRD)
#define SDB_MODIFY_MAX_ATTEMPTS          3       // lalu alert (PRD)
#define SDB_RECONCILE_LOOKBACK_DAYS      30      // scan history tanpa GV LAST_DEAL
#define SDB_CLOSE_REASON_TOLERANCE_PTS   2       // toleransi BE_STOP di atas InpBreakevenBufferPoints
#define SDB_TESTER_MIN_TRADES            30      // metrik OnTester 0 di bawah ini (spec 07)

//--- Notifier (spec 08 design §4.2; PRD §Notifikasi kecuali disebut)
#define SDB_NT_COOLDOWN_SEC           300      // Medium (PRD) dan Info (PC-13) per tipe
#define SDB_NT_QUOTA_PER_HOUR         20       // non-Critical per jam server, per akun (PC-13)
#define SDB_NT_STALE_SEC              1800     // non-Critical lebih tua dari ini dibuang
#define SDB_NT_QUEUE_MAX              100      // PC-13
#define SDB_NT_MAX_PER_TIMER          2        // WebRequest blocking: batasi kiriman per siklus (PC-13)
#define SDB_NT_MAX_ATTEMPTS           3
#define SDB_NT_MAX_LEN                4096     // batas pesan Telegram
#define SDB_NT_DRAIN_MS               2000     // kirim Critical + stop saat deinit; MT5 memotong OnDeinit di 2.5 detik (PC-14)
#define SDB_NT_QUOTA_HOUR_FACTOR      1000     // GV NT_QUOTA = jam x 1000 + jumlah
#define SDB_GV_NT_QUOTA               "NT_QUOTA"
#define SDB_GV_NT_CD_PREFIX           "NT_CD_"

//--- Telegram, push, pesan berjadwal (spec 09 design §4.5-4.6, PC-14)
#define SDB_TG_TIMEOUT_MS             3000     // PRD
#define SDB_TG_MIN_GAP_MS             1000     // jarak kiriman semua instance ke satu chat
#define SDB_TG_TEMP_BACKOFF_SEC       10       // selama gagal sementara: maks 1 kiriman per 10 detik
#define SDB_PUSH_MAX_LEN              255      // batas SendNotification
#define SDB_PUSH_PER_SEC              2
#define SDB_PUSH_PER_MIN              10
#define SDB_PUSH_QUEUE_MAX            20
#define SDB_NT_LEASE_TTL_SEC          120
#define SDB_NT_LEASE_RENEW_SEC        30
#define SDB_NT_REPORT_MAX_DAYS        7
#define SDB_DEF_HEARTBEAT_MIN         60       // PRD HeartbeatMinutes
#define SDB_MIN_HEARTBEAT_MIN         5
#define SDB_MAX_HEARTBEAT_MIN         1440
#define SDB_GV_NT_TG_NEXT             "NT_TG_NEXT"
#define SDB_GV_NT_LEADER              "NT_LEADER"
#define SDB_GV_NT_ALIVE_PREFIX        "NT_ALIVE_"
#define SDB_GV_NT_HB_AT               "NT_HB_AT"
#define SDB_GV_NT_REPORT_DAY          "NT_REPORT_DAY"
#define SDB_GV_NT_HELD                "NT_HELD"

//--- Analisis struktur (spec 10 design §4.2, PC-16)
#define SDB_DEF_SWING_STRENGTH        2
#define SDB_MIN_SWING_STRENGTH        1
#define SDB_MAX_SWING_STRENGTH        5
#define SDB_DEF_STRUCTURE_LOOKBACK    100
#define SDB_MIN_STRUCTURE_LOOKBACK    20
#define SDB_MAX_STRUCTURE_LOOKBACK    500
#define SDB_DEF_EMA_PERIOD            50       // PRD: EMA 50
#define SDB_MIN_EMA_PERIOD            10
#define SDB_MAX_EMA_PERIOD            400
#define SDB_DEF_EMA_SLOPE_BARS        3
#define SDB_MIN_EMA_SLOPE_BARS        1
#define SDB_MAX_EMA_SLOPE_BARS        20
#define SDB_EMA_WARMUP_MULT           3        // EMA dihitung dari >= 3 x periode bar (konvergen, deterministik)

//--- Zona S&D (spec 11 design §4.2, PC-17); default dari ukuran histori H1 12 simbol 2025-10..2026-10
#define SDB_DEF_ZONE_MIN_WIDTH_ATR    0.3
#define SDB_MIN_ZONE_MIN_WIDTH_ATR    0.05
#define SDB_MAX_ZONE_MIN_WIDTH_ATR    1.0
#define SDB_DEF_ZONE_MAX_WIDTH_ATR    2.0
#define SDB_MIN_ZONE_MAX_WIDTH_ATR    0.5
#define SDB_MAX_ZONE_MAX_WIDTH_ATR    5.0
#define SDB_DEF_ZONE_MIN_LEG_ATR      1.5
#define SDB_MIN_ZONE_MIN_LEG_ATR      0.5
#define SDB_MAX_ZONE_MIN_LEG_ATR      5.0
#define SDB_DEF_ZONE_LEG_BARS         10
#define SDB_MIN_ZONE_LEG_BARS         3
#define SDB_MAX_ZONE_LEG_BARS         50
#define SDB_DEF_MAX_ZONE_AGE_BARS     100      // PRD MaxZoneAgeBars
#define SDB_MIN_MAX_ZONE_AGE_BARS     20
#define SDB_MAX_MAX_ZONE_AGE_BARS     500
#define SDB_ZONE_ATR_PERIOD           14
#define SDB_GV_ZONE_USED              "ZU"     // GV "<magic>_ZU_<epoch swing>_<D|S>"

//--- Sinyal dan entry (spec 13 design §3.3, PC-19); default SL dari simulasi pipeline 12 simbol 2025-10..2026-10
#define SDB_DEF_MIN_CONFLUENCE_SCORE  65.0     // persen dari skor maksimum komponen aktif (PC-15)
#define SDB_MIN_MIN_CONFLUENCE_SCORE  0.0
#define SDB_MAX_MIN_CONFLUENCE_SCORE  100.0
#define SDB_DEF_MIN_RR                2.0      // PRD MinRR
#define SDB_MIN_MIN_RR                1.0
#define SDB_MAX_MIN_RR                10.0
#define SDB_DEF_SL_BUFFER_ATR         0.1      // SL di luar batas jauh zona (x ATR MTF)
#define SDB_MIN_SL_BUFFER_ATR         0.0
#define SDB_MAX_SL_BUFFER_ATR         1.0
#define SDB_DEF_MIN_SL_ATR            0.3      // jarak SL minimum (x ATR MTF)
#define SDB_MIN_MIN_SL_ATR            0.05
#define SDB_MAX_MIN_SL_ATR            2.0
#define SDB_DEF_MAX_SL_ATR            3.0      // jarak SL maksimum (x ATR MTF)
#define SDB_MIN_MAX_SL_ATR            0.5
#define SDB_MAX_MAX_SL_ATR            10.0
#define SDB_SCORE_MAX_ACTIVE          55       // Fase 3: zona 30 + tren 15 + PA 10
#define SDB_SCORE_MAX_ZONE            30
#define SDB_SCORE_MAX_TREND           15
#define SDB_SCORE_MAX_PA              10
#define SDB_SIGNAL_STALE_BARS         2        // bar LTF lebih tua dari 2 x durasi LTF tidak dinilai
#define SDB_SIGNAL_EPS                1e-9     // x ATR: batas inklusif SL/TP
#define SDB_GV_SIGNAL_BAR             "SIGBAR" // GV "<magic>_SIGBAR": waktu bar LTF terakhir yang dinilai

//--- Filter sesi dan spread (spec 14 design §3.2, PC-22)
#define SDB_MAX_MAX_SPREAD_POINTS     100000   // 0 = filter spread mati
#define SDB_MIN_TESTER_UTC_OFFSET_H   -12
#define SDB_MAX_TESTER_UTC_OFFSET_H   14

//--- Eksposur mata uang (spec 15, PC-23)
#define SDB_DEF_MAX_SAME_DIR_CCY      2        // PRD: maks 2 posisi searah per mata uang; 0 = mati
#define SDB_MAX_MAX_SAME_DIR_CCY      10

//--- Filter berita (spec 16, PC-24)
#define SDB_DEF_NEWS_HIGH_MIN         15       // PC-24: +-15 menit (PRD +-30 memblokir ~22% trade backtest, PC-22 gagal)
#define SDB_DEF_NEWS_MEDIUM_MIN       0        // PC-24: medium tidak diblokir secara default
#define SDB_MAX_NEWS_MIN              240
#define SDB_DEF_NEWS_CSV              "sdbot_calendar.csv"
#define SDB_NEWS_REFRESH_SEC          900      // kalender live dimuat ulang tiap 15 menit

//--- Trigger price action (spec 12 design §3.3, PC-18): ambang relatif ATR(14) LTF dari ukuran M15 12 simbol
#define SDB_PA_STAR_FIRST_BODY_ATR    0.5      // badan bar pertama bintang > 0,5 ATR
#define SDB_PA_STAR_MID_RATIO         0.3      // badan bar tengah < 0,3 x badan pertama
#define SDB_PA_STRONG_BODY_RANGE      0.6      // engulfing kuat: badan >= 60% rentang
#define SDB_PA_STRONG_BODY_ATR        0.8      // engulfing kuat: badan >= 0,8 ATR
#define SDB_PA_PIN_BODY_RANGE         0.35     // pin bar: badan <= 35% rentang
#define SDB_PA_PIN_WICK_BODY          2.0      // sumbu >= 2 x badan
#define SDB_PA_PIN_WICK_RANGE         0.6      // sumbu >= 60% rentang
#define SDB_PA_PIN_WICK_OTHER         2.0      // sumbu > 2 x sumbu sisi lain
#define SDB_PA_PIN_RANGE_ATR          0.8      // rentang pin bar >= 0,8 ATR
#define SDB_PA_TWEEZER_ATR            0.1      // selisih low/high tweezer <= 0,1 ATR
#define SDB_PA_BARS                   45       // 3 x ATR 14 + 3 bar pola

//--- run_key (spec 04, PC-08): ID MT5 berulang di setiap run tester, jadi baris dipisah per run.
#define SDB_RUN_KEY_LIVE              0        // live: posisi unik per login lintas restart
#define SDB_RUN_KEY_NEW               -1       // run tester baru: run_key = ID sesi pertama
#define SDB_GV_RUN_KEY                "RUN_KEY"

// Default input dari PRD. Satu sumber untuk Inputs.mqh dan DefaultInputValues().
#define SDB_DEF_MAGIC                 2026091901
#define SDB_DEF_RISK_PER_TRADE_PCT    0.5
#define SDB_DEF_MAX_OPEN_RISK_PCT     3.0
#define SDB_DEF_DAILY_LOSS_PCT        3.0
#define SDB_DEF_DD_REDUCE_PCT         10.0
#define SDB_DEF_DD_STOP_PCT           15.0
#define SDB_DEF_BREAKEVEN_R           1.0
#define SDB_DEF_BREAKEVEN_BUFFER_PTS  2
#define SDB_DEF_PARTIAL_R             1.5
#define SDB_DEF_PARTIAL_PCT           50.0
#define SDB_DEF_TRAIL_ATR_PERIOD      14
#define SDB_DEF_TRAIL_ATR_MULT        2.0

// Batas validasi input (spec 02 design §4.3). Batas antar-input dicek di InputRules.mqh.
#define SDB_MAX_RISK_PER_TRADE_PCT    1.0
#define SDB_MAX_OPEN_RISK_PCT         10.0
#define SDB_MAX_DAILY_LOSS_PCT        10.0
#define SDB_MAX_DD_STOP_PCT           50.0
#define SDB_MAX_BREAKEVEN_BUFFER_PTS  1000
#define SDB_MAX_PARTIAL_R             10.0
#define SDB_MIN_TRAIL_ATR_PERIOD      2
#define SDB_MAX_TRAIL_ATR_PERIOD      200
#define SDB_MAX_TRAIL_ATR_MULT        10.0

#endif // SDB_CORE_CONSTANTS_MQH
