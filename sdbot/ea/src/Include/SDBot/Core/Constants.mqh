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
#define SDB_NT_DRAIN_MS               3000     // kirim Critical tersisa saat deinit
#define SDB_NT_QUOTA_HOUR_FACTOR      1000     // GV NT_QUOTA = jam x 1000 + jumlah
#define SDB_GV_NT_QUOTA               "NT_QUOTA"
#define SDB_GV_NT_CD_PREFIX           "NT_CD_"

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
