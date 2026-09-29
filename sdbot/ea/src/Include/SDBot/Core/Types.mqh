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

// Snapshot akun untuk tabel accounts (spec 03).
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
   datetime                 time;
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

// Struct event berikut dilengkapi oleh spec pemakainya (04: trade, 05: operasi saldo,
// 06: deal, event posisi, closure). Satu field cukup agar interface sink bisa di-compile.
struct TradeRecord      { long positionId; };
struct DealRecord       { long dealTicket; };
struct PositionEvent    { long positionId; };
struct ClosureRecord    { long positionId; };
struct BalanceOpRecord  { long dealTicket; };

#endif // SDB_CORE_TYPES_MQH
