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
