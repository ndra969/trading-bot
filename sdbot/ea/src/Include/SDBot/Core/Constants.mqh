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

#endif // SDB_CORE_CONSTANTS_MQH
