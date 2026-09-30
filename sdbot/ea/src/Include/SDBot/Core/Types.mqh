//+------------------------------------------------------------------+
//| Types.mqh — enum dan struct yang dipakai antar-modul SDBot.
//| Modul berkomunikasi lewat struct ini, bukan variabel global (RULES).
//+------------------------------------------------------------------+
#ifndef SDB_CORE_TYPES_MQH
#define SDB_CORE_TYPES_MQH

enum ENUM_SDB_LOG_LEVEL
  {
   SDB_LOG_DEBUG = 0,
   SDB_LOG_INFO = 1,
   SDB_LOG_WARN = 2,
   SDB_LOG_ERROR = 3,
   SDB_LOG_CRITICAL = 4
  };

enum ENUM_SDB_SEVERITY
  {
   SDB_SEV_INFO = 0,
   SDB_SEV_MEDIUM = 1,
   SDB_SEV_HIGH = 2,
   SDB_SEV_CRITICAL = 3
  };

enum ENUM_SDB_TRADING_STYLE
  {
   SDB_STYLE_SCALPING = 0,
   SDB_STYLE_DAY = 1,
   SDB_STYLE_SWING = 2,
   SDB_STYLE_POSITION = 3
  };

enum ENUM_SDB_ACCOUNT_TYPE
  {
   SDB_ACC_DEMO = 0,
   SDB_ACC_REAL = 1,
   SDB_ACC_CENT = 2
  };

enum ENUM_SDB_VALIDATION
  {
   SDB_VAL_PASSED = 0,
   SDB_VAL_PENDING = 1,
   SDB_VAL_REJECTED = 2
  };

enum ENUM_SDB_CONN_ACTION
  {
   SDB_CONN_NONE = 0,
   SDB_CONN_LOG_DOWN = 1,
   SDB_CONN_ALERT_MEDIUM = 2,
   SDB_CONN_ALERT_RECOVERED = 3
  };

// File database yang dibuka CLogger (spec 03 Req 1).
enum ENUM_SDB_DB_TARGET
  {
   SDB_DB_NONE = 0,        // optimasi: tidak membuka file apa pun
   SDB_DB_LIVE = 1,        // sdbot.sqlite
   SDB_DB_TESTER = 2,      // sdbot_tester.sqlite
   SDB_DB_UNITTEST = 3     // sdbot_unittest.sqlite
  };

// Eksekusi (spec 04 design §4.1, §5).
enum ENUM_SDB_RETCODE_CLASS
  {
   SDB_RC_SUCCESS = 0,
   SDB_RC_NO_CHANGES = 1,
   SDB_RC_TRANSIENT = 2,       // requote, harga berubah: aman diulang
   SDB_RC_AMBIGUOUS = 3,       // tanpa jawaban pasti: cari dulu berdasarkan ID permintaan
   SDB_RC_POSITION_GONE = 4,
   SDB_RC_PERMANENT = 5
  };

enum ENUM_SDB_NEXT_STEP
  {
   SDB_STEP_SUCCEED = 0,
   SDB_STEP_RETRY = 1,
   SDB_STEP_GONE = 2,
   SDB_STEP_GIVE_UP = 3
  };

enum ENUM_SDB_EXEC
  {
   SDB_EXEC_OK = 0,
   SDB_EXEC_SKIPPED = 1,       // ditolak aturan sebelum ke broker (misalnya SL tidak lebih baik)
   SDB_EXEC_GONE = 2,          // posisi sudah tidak ada
   SDB_EXEC_FAILED = 3
  };

enum ENUM_SDB_APP_MODE
  {
   SDB_APP_LIVE = 0,           // SDBot.mq5 (live dan backtest)
   SDB_APP_HARNESS = 1,        // SDBotHarness.mq5
   SDB_APP_UNITTEST = 2        // suite TestApp
  };

// Risk management (spec 05 design §4.1, §5).
enum ENUM_SDB_DD_LEVEL
  {
   SDB_DD_NORMAL = 0,
   SDB_DD_INFO = 1,
   SDB_DD_REDUCE = 2,          // lot x 0.5
   SDB_DD_STOP = 3             // STOPPED; hanya reset manual yang mengembalikannya
  };

enum ENUM_SDB_LOT_FLAG
  {
   SDB_LOT_OK = 0,
   SDB_LOT_BELOW_MIN = 1,
   SDB_LOT_CAPPED_MAX = 2,
   SDB_LOT_INVALID = 3         // nilai uang per lot <= 0
  };

// Kategori aset untuk batas posisi per kategori (spec 05 Req 2.8, PC-10).
enum ENUM_SDB_ASSET_CLASS
  {
   SDB_CLASS_FOREX_MAJOR = 0,  // pasangan dengan USD
   SDB_CLASS_FOREX_CROSS = 1,  // dua mata uang fiat tanpa USD
   SDB_CLASS_COMMODITY = 2,    // XAU, XAG, ...
   SDB_CLASS_CRYPTO = 3,
   SDB_CLASS_OTHER = 4         // tidak dikenali (indeks, dll.)
  };

// Manajemen posisi (spec 06 design §4.3, §5).
enum ENUM_SDB_SL_SOURCE
  {
   SDB_SL_SRC_NONE = 0,        // tidak diketahui: BE dan partial dilewati (Req 1.3)
   SDB_SL_SRC_COMMENT = 1,     // komentar SDB|<SL>|<ID>
   SDB_SL_SRC_ORDER = 2,       // ORDER_SL order pembuka di history
   SDB_SL_SRC_DB = 3           // tabel trades lewat event sink
  };

enum ENUM_SDB_POS_ACTION
  {
   SDB_ACT_BE = 0,
   SDB_ACT_TRAIL = 1,
   SDB_ACT_PARTIAL = 2,
   SDB_ACT_RESTORE = 3,
   SDB_ACT_COUNT = 4
  };

// Nilai mahal per posisi yang tidak berubah selama posisi terbuka, plus penghitung retry per aksi.
struct PositionCacheEntry
  {
   ulong             positionId;
   bool              owned;
   bool              isBuy;
   double            entry;
   datetime          entryTime;
   double            initialSl;
   ENUM_SDB_SL_SOURCE slSource;
   double            initialVolume;
   double            riskMoney;       // SDB_NULL_DOUBLE bila SL awal tidak diketahui
   double            commission;      // komisi pulang-pergi (uang, positif) untuk titik BE
   string            symbol;
   double            beSl;            // titik BE yang dipasang; 0 = belum
   bool              beDone;
   bool              partialDone;
   bool              trailDone;
   bool              slUnknownLogged;
   bool              partialSkippedLogged;
   datetime          lastTrailEventBar;
   int               fails[SDB_ACT_COUNT];
   datetime          lastFail[SDB_ACT_COUNT];
   double            failKeySl[SDB_ACT_COUNT];   // SL saat gagal; berubah -> penghitung di-reset (Req 5.3)
   double            failKeyVol[SDB_ACT_COUNT];
   bool              failAlerted[SDB_ACT_COUNT];
  };

// Hasil satu putaran close all (Req 5.8). closedMarket = dilewati karena pasar simbolnya tutup.
struct CloseAllResult
  {
   int               total;
   int               closed;
   int               failed;
   int               closedMarket;
  };

// Permintaan market order ke CExecutor. SL dan TP harga absolut.
struct OrderRequest
  {
   bool              isBuy;
   double            sl;
   double            tp;
   double            volume;
   long              signalId;        // SDB_NULL_LONG sebelum Fase 3
  };

// Hasil OpenMarket (Req 3.4). rejectStage "" = berhasil, selain itu kode reject_stage.
struct OrderResult
  {
   bool              ok;
   string            rejectStage;
   string            detail;
   uint              retcode;
   string            requestId;
   long              positionId;
   long              dealTicket;
   double            priceRequested;
   double            priceFilled;
   double            volumeFilled;
   long              slippagePts;     // SDB_NULL_LONG bila harga isi tidak diketahui
   long              spreadPts;
   double            riskMoney;       // SDB_NULL_DOUBLE bila tidak bisa dihitung
   int               attempts;
  };

// Nilai penanda NULL untuk kolom yang boleh kosong: DatabaseBind MQL5 tidak bisa mengikat NULL,
// jadi Logger mengubah penanda ini menjadi NULL (NULLIF) saat menulis.
#define SDB_NULL_DOUBLE DBL_MAX
#define SDB_NULL_LONG   LONG_MIN

// Semua waktu di struct event adalah waktu server MT5; Logger mengubahnya ke UTC saat menulis.

// Snapshot akun untuk tabel accounts.
struct AccountSnapshot
  {
   long                     login;
   string                   server;
   string                   company;
   ENUM_SDB_ACCOUNT_TYPE    type;
   ENUM_ACCOUNT_MARGIN_MODE marginMode;
   string                   currency;
   long                     leverage;
   double                   balance;
   double                   equity;
   double                   peakEquity;   // puncak dari status risiko (spec 05); sebelum itu = equity
   datetime                 time;
  };

// Satu baris tabel sessions (spec 03 Req 8). inputsJson wajib kanonik (CurrentInputsJson),
// input_hash dihitung CLogger dari teks itu. testerFrom/testerTo 0 dan testerModel "" = NULL.
struct SessionInfo
  {
   long              login;
   long              runKey;          // SDB_RUN_KEY_LIVE, SDB_RUN_KEY_NEW, atau run_key run tester yang sedang jalan
   long              magic;
   string            symbol;
   string            mode;            // SDB_SESSION_MODE_*
   string            eaVersion;
   string            inputsJson;
   datetime          startedAt;
   datetime          testerFrom;
   datetime          testerTo;
   string            testerModel;
  };

// Alert untuk tabel alerts; dikirim Notifier di Fase 2. type = kode stabil dari enums.md.
struct AlertEvent
  {
   string            type;
   ENUM_SDB_SEVERITY severity;
   string            message;
   string            symbol;
   long              magic;
   datetime          time;
  };

// Struct event berikut mengikuti kolom tabel di shared/schema/data_db.sql. Kolom teks enum
// diisi dengan konstanta Core/SchemaEnums.mqh. Kolom yang boleh NULL memakai SDB_NULL_*.

struct TradeRecord          // tabel trades (spec 04 mengisi dari Executor, spec 06 dari rekonsiliasi)
  {
   long              positionId;
   long              magic;
   string            symbol;
   string            direction;       // SDB_DIRECTION_*
   string            source;          // SDB_TRADE_SOURCE_*
   double            volumeInitial;
   double            priceRequested;  // SDB_NULL_DOUBLE untuk RECONCILED
   double            priceOpen;
   long              slippagePoints;  // SDB_NULL_LONG untuk RECONCILED
   long              spreadPoints;    // SDB_NULL_LONG untuk RECONCILED
   double            slInitial;
   double            tpInitial;
   double            riskMoney;       // SDB_NULL_DOUBLE bila tidak diketahui
   double            riskPct;         // SDB_NULL_DOUBLE bila tidak diketahui
   long              signalId;        // SDB_NULL_LONG sebelum Fase 3
   string            eaVersion;
   datetime          openedAt;
  };

struct DealRecord           // tabel deals
  {
   long              dealTicket;
   long              positionId;
   long              magic;
   string            symbol;
   datetime          time;
   string            entry;           // SDB_DEAL_ENTRY_*
   string            dealType;        // SDB_DEAL_TYPE_*
   double            volume;
   double            price;
   string            reason;          // SDB_DEAL_REASON_*
   double            profit;
   double            commission;
   double            swap;
   double            fee;
  };

struct PositionEvent        // tabel position_events
  {
   long              positionId;
   datetime          time;
   string            type;            // SDB_POSITION_EVENT_*
   double            slOld;           // SDB_NULL_DOUBLE bila tidak relevan
   double            slNew;           // SDB_NULL_DOUBLE bila tidak relevan
   double            volume;
   double            price;
   long              spreadPoints;
   string            detail;          // "" = NULL
  };

struct ClosureRecord        // tabel closures
  {
   long              positionId;
   long              magic;
   string            symbol;
   datetime          closedAt;
   string            reason;          // SDB_CLOSE_REASON_*
   double            levelPrice;      // SDB_NULL_DOUBLE untuk close manual
   double            priceClose;
   long              slippagePoints;  // SDB_NULL_LONG bila tidak ada level
   double            volumeTotal;
   double            profit;
   double            commission;
   double            swap;
   double            fee;
   double            netProfit;
   double            rResult;         // SDB_NULL_DOUBLE bila risiko awal tidak diketahui
   double            mfeR;            // SDB_NULL_DOUBLE bila bar M1 tidak tersedia
   double            maeR;
   long              holdingSec;
   bool              beActivated;
   bool              partialDone;
   bool              trailActivated;
  };

struct BalanceOpRecord      // tabel balance_ops (spec 05)
  {
   long              dealTicket;
   datetime          time;
   string            opType;          // SDB_BALANCE_OP_TYPE_*
   double            amount;
   string            comment;
  };

#endif // SDB_CORE_TYPES_MQH
