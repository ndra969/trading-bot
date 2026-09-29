//+------------------------------------------------------------------+
//| Logger.mqh — CLogger: satu-satunya penulis database EA (spec 03
//| Req 1–3, 8, 9; design §4.2–4.3). Event dari modul masuk antrean di
//| memori lewat ISdbEventSink, lalu ditulis sekaligus dalam satu
//| transaksi oleh Flush() di OnTimer. Masalah DB tidak pernah
//| menghentikan trading: gagal = antrean ditahan dan dicoba lagi.
//+------------------------------------------------------------------+
#ifndef SDB_STORAGE_LOGGER_MQH
#define SDB_STORAGE_LOGGER_MQH

#include <SDBot/Core/EventSink.mqh>
#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Core/SchemaEnums.mqh>
#include <SDBot/Storage/MigrationRunner.mqh>
#include <SDBot/Storage/Migrations.mqh>

//--- Pemilihan file (Req 1).
ENUM_SDB_DB_TARGET SdbDbTargetForRuntime()
  {
   if(MQLInfoInteger(MQL_OPTIMIZATION))
      return SDB_DB_NONE;
   if(MQLInfoInteger(MQL_TESTER))
      return SDB_DB_TESTER;
   return SDB_DB_LIVE;
  }

string SdbDbFileFor(const ENUM_SDB_DB_TARGET target)
  {
   switch(target)
     {
      case SDB_DB_LIVE:     return SDB_DB_FILE_LIVE;
      case SDB_DB_TESTER:   return SDB_DB_FILE_TESTER;
      case SDB_DB_UNITTEST: return SDB_DB_FILE_UNITTEST;
      default:              return "";
     }
  }

//--- Teks enum untuk kolom DB (nilai dari SchemaEnums.mqh).
string SdbSeverityText(const ENUM_SDB_SEVERITY s)
  {
   switch(s)
     {
      case SDB_SEV_MEDIUM:   return SDB_SEVERITY_MEDIUM;
      case SDB_SEV_HIGH:     return SDB_SEVERITY_HIGH;
      case SDB_SEV_CRITICAL: return SDB_SEVERITY_CRITICAL;
      default:               return SDB_SEVERITY_INFO;
     }
  }

string SdbAccountTypeText(const ENUM_SDB_ACCOUNT_TYPE t)
  {
   switch(t)
     {
      case SDB_ACC_REAL: return SDB_ACCOUNT_TYPE_REAL;
      case SDB_ACC_CENT: return SDB_ACCOUNT_TYPE_CENT;
      default:           return SDB_ACCOUNT_TYPE_DEMO;
     }
  }

string SdbMarginModeText(const ENUM_ACCOUNT_MARGIN_MODE m)
  {
   switch(m)
     {
      case ACCOUNT_MARGIN_MODE_RETAIL_NETTING: return SDB_MARGIN_MODE_NETTING;
      case ACCOUNT_MARGIN_MODE_EXCHANGE:       return SDB_MARGIN_MODE_EXCHANGE;
      default:                                 return SDB_MARGIN_MODE_HEDGING;
     }
  }

string SdbDeinitReasonText(const int reason)
  {
   switch(reason)
     {
      case REASON_PROGRAM:     return SDB_DEINIT_REASON_PROGRAM;
      case REASON_REMOVE:      return SDB_DEINIT_REASON_REMOVE;
      case REASON_RECOMPILE:   return SDB_DEINIT_REASON_RECOMPILE;
      case REASON_CHARTCHANGE: return SDB_DEINIT_REASON_CHARTCHANGE;
      case REASON_CHARTCLOSE:  return SDB_DEINIT_REASON_CHARTCLOSE;
      case REASON_PARAMETERS:  return SDB_DEINIT_REASON_PARAMETERS;
      case REASON_ACCOUNT:     return SDB_DEINIT_REASON_ACCOUNT;
      case REASON_TEMPLATE:    return SDB_DEINIT_REASON_TEMPLATE;
      case REASON_INITFAILED:  return SDB_DEINIT_REASON_INITFAILED;
      case REASON_CLOSE:       return SDB_DEINIT_REASON_CLOSE;
      default:                 return SDB_DEINIT_REASON_OTHER;
     }
  }

//--- Antrean (design §4.3). Prioritas 0 tidak pernah dibuang; 2 dibuang lebih dulu dari 1.
enum ENUM_SDB_QUEUE_KIND
  {
   SDB_Q_ACCOUNT = 0,
   SDB_Q_TRADE = 1,
   SDB_Q_DEAL = 2,
   SDB_Q_POSITION = 3,
   SDB_Q_CLOSURE = 4,
   SDB_Q_BALANCE = 5,
   SDB_Q_ALERT = 6,
   SDB_Q_KINDS = 7
  };

#define SDB_Q_PRIO_KEEP     0   // trade, deal, closure, operasi saldo, alert Critical
#define SDB_Q_PRIO_NORMAL   1   // alert lain, event posisi, snapshot akun
#define SDB_Q_PRIO_LOW      2   // sinyal dan skor (Fase 3)

// Parameter penanda NULL di SQL: ?90 = SDB_NULL_DOUBLE, ?91 = SDB_NULL_LONG (dipakai lewat NULLIF).
#define SDB_BIND_NULL_DOUBLE 89
#define SDB_BIND_NULL_LONG   90

struct SdbQueuedEvent
  {
   ENUM_SDB_QUEUE_KIND kind;
   int               priority;
   long              login;
   AccountSnapshot   account;
   TradeRecord       trade;
   DealRecord        deal;
   PositionEvent     position;
   ClosureRecord     closure;
   BalanceOpRecord   balance;
   AlertEvent        alert;
  };

class CLogger : public ISdbEventSink
  {
private:
   ISdbEventSink    *m_alertSink;     // penerima alert milik Logger sendiri (FakeSink di uji, Notifier di Fase 2)
   string            m_symbol;
   long              m_magic;
   string            m_eaVersion;
   ENUM_SDB_DB_TARGET m_target;
   string            m_file;
   int               m_db;
   bool              m_disabled;      // NONE, DB lebih baru, migrasi gagal, atau sudah Close
   CSdbDataMigrations m_migrations;
   CSdbMigrationRunner m_runner;
   int               m_stmt[SDB_Q_KINDS];

   SdbQueuedEvent    m_queue[];
   int               m_capacity;
   int               m_dropped;

   long              m_login;
   long              m_sessionId;
   bool              m_haveSession;
   SessionInfo       m_session;
   bool              m_haveAccount;
   AccountSnapshot   m_account;

   long              m_failSince;     // detik pertama flush gagal berturut-turut; 0 = sehat
   bool              m_unavailAlerted;
   long              m_lastReopen;
   int               m_offset;        // offset server-UTC yang dipakai flush ini
   long              m_nowOverride;
   bool              m_offsetOverridden;
   int               m_offsetOverride;

   //--- Waktu
   long Now() const { return (m_nowOverride > 0) ? m_nowOverride : (long)(GetTickCount64() / 1000); }

   int UtcOffset() const
     {
      if(m_offsetOverridden)
         return m_offsetOverride;
      return RoundUtcOffset((long)(TimeTradeServer() - TimeGMT()));
     }

   long Utc(const datetime serverTime) const { return (long)ServerToUtc(serverTime, m_offset); }

   //--- Alert milik Logger: diteruskan ke penerima dan ikut disimpan di tabel alerts.
   void RaiseAlert(const string type, const ENUM_SDB_SEVERITY severity, const string message)
     {
      AlertEvent a;
      a.type = type;
      a.severity = severity;
      a.message = message;
      a.symbol = m_symbol;
      a.magic = m_magic;
      a.time = TimeCurrent();
      if(m_alertSink != NULL)
         m_alertSink.OnAlert(a);
      OnAlert(a);
     }

   //--- Antrean
   bool DropOne()
     {
      for(int p = SDB_Q_PRIO_LOW; p >= SDB_Q_PRIO_NORMAL; p--)
        {
         int n = ArraySize(m_queue);
         for(int i = 0; i < n; i++)
           {
            if(m_queue[i].priority != p)
               continue;
            for(int j = i; j < n - 1; j++)
               m_queue[j] = m_queue[j + 1];
            ArrayResize(m_queue, n - 1);
            m_dropped++;
            return true;
           }
        }
      return false;
     }

   void Enqueue(SdbQueuedEvent &e)
     {
      if(m_disabled)
         return;
      if(ArraySize(m_queue) >= m_capacity)
        {
         if(DropOne())
            LogThrottled(SDB_LOG_WARN, "sdb_db_queue_full", SDB_LOG_THROTTLE_DEFAULT_SEC, "Storage",
                         StringFormat("antrean DB penuh, %d event prioritas rendah dibuang sejak flush terakhir", m_dropped));
         else
            LogThrottled(SDB_LOG_WARN, "sdb_db_queue_keep", SDB_LOG_THROTTLE_DEFAULT_SEC, "Storage",
                         "antrean DB penuh berisi event wajib, kapasitas dilewati");
        }
      int n = ArraySize(m_queue);
      ArrayResize(m_queue, n + 1, 256);
      m_queue[n] = e;
     }

   //--- Koneksi
   void FinalizeStatements()
     {
      for(int k = 0; k < SDB_Q_KINDS; k++)
        {
         if(m_stmt[k] != INVALID_HANDLE)
            DatabaseFinalize(m_stmt[k]);
         m_stmt[k] = INVALID_HANDLE;
        }
     }

   void CloseDb()
     {
      FinalizeStatements();
      if(m_db != INVALID_HANDLE)
         DatabaseClose(m_db);
      m_db = INVALID_HANDLE;
     }

   bool Pragma(const string sql)
     {
      int st = DatabasePrepare(m_db, sql);
      if(st == INVALID_HANDLE)
         return false;
      DatabaseRead(st);
      DatabaseFinalize(st);
      return true;
     }

   // Buka file + pragma + migrasi. DB lebih baru atau migrasi gagal menonaktifkan Logger untuk sesi ini.
   bool OpenFile()
     {
      ResetLastError();
      m_db = DatabaseOpen(m_file, DATABASE_OPEN_READWRITE | DATABASE_OPEN_CREATE | DATABASE_OPEN_COMMON);
      if(m_db == INVALID_HANDLE)
        {
         LogError("Storage", "database tidak bisa dibuka, EA lanjut tanpa DB | file=" + m_file + " " + ErrText(GetLastError()));
         return false;
        }
      Pragma("PRAGMA journal_mode=WAL");
      Pragma("PRAGMA busy_timeout=" + IntegerToString(SDB_DB_BUSY_TIMEOUT_MS));
      Pragma("PRAGMA synchronous=NORMAL");
      m_runner.Init(m_alertSink, m_symbol, m_magic);
      string appliedBy = StringFormat("SDBot %s login=%I64d magic=%I64d", m_eaVersion, m_login, m_magic);
      if(m_runner.Run(m_db, GetPointer(m_migrations), appliedBy, (long)TimeGMT()) != SDB_MIGRATE_OK)
        {
         CloseDb();
         m_disabled = true;
         ArrayFree(m_queue);
         LogError("Storage", "penulisan DB dinonaktifkan untuk sesi ini | " + m_runner.LastError());
         return false;
        }
      LogInfo("Storage", "database siap | file=" + m_file + " versi=" + IntegerToString(SDB_SCHEMA_LATEST));
      return true;
     }

   void UnavailableNow(const long now, const string why)
     {
      if(m_failSince == 0)
         m_failSince = now;
      if(!m_unavailAlerted)
        {
         m_unavailAlerted = true;
         RaiseAlert(SDB_ALERT_TYPE_DB_UNAVAILABLE, SDB_SEV_HIGH, "Database tidak bisa dibuka, EA lanjut trading tanpa DB: " + why);
        }
     }

   // Setelah file dibuka ulang: sesi dan snapshot akun ditulis lagi, lalu kabar pulih.
   bool ReopenFile(const long now)
     {
      CloseDb();
      m_lastReopen = now;
      if(!OpenFile())
         return false;
      m_offset = UtcOffset();
      if(m_haveSession)
         m_sessionId = InsertSession(m_session);
      if(m_haveAccount)
         OnAccount(m_account);
      m_failSince = 0;
      m_unavailAlerted = false;
      RaiseAlert(SDB_ALERT_TYPE_DB_RECOVERED, SDB_SEV_INFO, "Database bisa ditulis lagi (file dibuka ulang)");
      return true;
     }

   bool SchemaMissing()
     {
      int st = DatabasePrepare(m_db, "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name IN ('schema_migrations', 'trades')");
      if(st == INVALID_HANDLE)
         return false;
      long n = 2;
      if(DatabaseRead(st))
         DatabaseColumnLong(st, 0, n);
      DatabaseFinalize(st);
      return n < 2;
     }

   void NoteFailure(const long now, const string why)
     {
      if(m_failSince == 0)
         m_failSince = now;
      LogThrottled(SDB_LOG_WARN, "sdb_db_flush", SDB_LOG_THROTTLE_DEFAULT_SEC, "Storage",
                   StringFormat("flush tertunda, dicoba lagi | %s antrean=%d", why, ArraySize(m_queue)));
      if(!m_unavailAlerted && now - m_failSince >= SDB_DB_UNAVAILABLE_ALERT_SEC)
        {
         m_unavailAlerted = true;
         RaiseAlert(SDB_ALERT_TYPE_DB_UNAVAILABLE, SDB_SEV_HIGH,
                    StringFormat("Database tidak bisa ditulis selama %d detik, event ditahan di memori: %s", (int)(now - m_failSince), why));
        }
     }

   void NoteSuccess()
     {
      m_failSince = 0;
      if(m_unavailAlerted)
        {
         m_unavailAlerted = false;
         RaiseAlert(SDB_ALERT_TYPE_DB_RECOVERED, SDB_SEV_INFO, "Database bisa ditulis lagi");
        }
     }

   //--- Penulisan
   bool Step(const int st, string &err)
     {
      ResetLastError();
      DatabaseRead(st);   // statement tanpa baris hasil: Read menjalankannya
      int code = GetLastError();
      if(code == 0 || code == ERR_DATABASE_NO_MORE_DATA)
         return true;
      err = ErrText(code);
      return false;
     }

   string SqlFor(const ENUM_SDB_QUEUE_KIND kind)
     {
      switch(kind)
        {
         case SDB_Q_ACCOUNT:
            return "INSERT INTO accounts (login, server, company, account_type, margin_mode, currency, leverage, balance, "
                   "equity, peak_equity, server_utc_offset_sec, updated_at) "
                   "VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12) "
                   "ON CONFLICT (login) DO UPDATE SET server = excluded.server, company = excluded.company, "
                   "account_type = excluded.account_type, margin_mode = excluded.margin_mode, currency = excluded.currency, "
                   "leverage = excluded.leverage, balance = excluded.balance, equity = excluded.equity, "
                   "peak_equity = excluded.peak_equity, server_utc_offset_sec = excluded.server_utc_offset_sec, "
                   "updated_at = excluded.updated_at";
         case SDB_Q_TRADE:
            return "INSERT INTO trades (session_id, login, position_id, magic, symbol, direction, source, volume_initial, "
                   "price_requested, price_open, slippage_points, spread_points, sl_initial, tp_initial, risk_money, risk_pct, "
                   "signal_id, ea_version, opened_at) "
                   "VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, NULLIF(?9, ?90), ?10, NULLIF(?11, ?91), NULLIF(?12, ?91), ?13, ?14, "
                   "NULLIF(?15, ?90), NULLIF(?16, ?90), NULLIF(?17, ?91), ?18, ?19) "
                   "ON CONFLICT (login, position_id) DO NOTHING";
         case SDB_Q_DEAL:
            return "INSERT INTO deals (session_id, login, deal_ticket, position_id, magic, symbol, time, entry, deal_type, "
                   "volume, price, reason, profit, commission, swap, fee) "
                   "VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16) "
                   "ON CONFLICT (login, deal_ticket) DO NOTHING";
         case SDB_Q_POSITION:
            return "INSERT INTO position_events (session_id, login, position_id, time, type, sl_old, sl_new, volume, price, "
                   "spread_points, detail) "
                   "VALUES (?1, ?2, ?3, ?4, ?5, NULLIF(?6, ?90), NULLIF(?7, ?90), ?8, ?9, ?10, NULLIF(?11, ''))";
         case SDB_Q_CLOSURE:
            return "INSERT INTO closures (session_id, login, position_id, magic, symbol, closed_at, reason, level_price, "
                   "price_close, slippage_points, volume_total, profit, commission, swap, fee, net_profit, r_result, mfe_r, "
                   "mae_r, holding_sec, be_activated, partial_done, trail_activated) "
                   "VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, NULLIF(?8, ?90), ?9, NULLIF(?10, ?91), ?11, ?12, ?13, ?14, ?15, ?16, "
                   "NULLIF(?17, ?90), NULLIF(?18, ?90), NULLIF(?19, ?90), ?20, ?21, ?22, ?23) "
                   "ON CONFLICT (login, position_id) DO NOTHING";
         case SDB_Q_BALANCE:
            return "INSERT INTO balance_ops (login, deal_ticket, time, op_type, amount, comment) "
                   "VALUES (?1, ?2, ?3, ?4, ?5, NULLIF(?6, '')) "
                   "ON CONFLICT (login, deal_ticket) DO NOTHING";
         case SDB_Q_ALERT:
            return "INSERT INTO alerts (session_id, login, magic, symbol, time, type, severity, message, status, attempts) "
                   "VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, 0)";
         default:
            return "";
        }
     }

   // Statement di-cache per jenis selama koneksi hidup; di-reset sebelum dipakai ulang.
   int Statement(const ENUM_SDB_QUEUE_KIND kind, string &err)
     {
      if(m_stmt[kind] != INVALID_HANDLE)
        {
         DatabaseReset(m_stmt[kind]);
         return m_stmt[kind];
        }
      ResetLastError();
      m_stmt[kind] = DatabasePrepare(m_db, SqlFor(kind));
      if(m_stmt[kind] == INVALID_HANDLE)
         err = "prepare " + EnumToString(kind) + " " + ErrText(GetLastError());
      return m_stmt[kind];
     }

   bool BindEvent(const int st, const SdbQueuedEvent &e)
     {
      bool ok = true;
      switch(e.kind)
        {
         case SDB_Q_ACCOUNT:
            ok = DatabaseBind(st, 0, e.account.login) && DatabaseBind(st, 1, e.account.server) &&
                 DatabaseBind(st, 2, e.account.company) && DatabaseBind(st, 3, SdbAccountTypeText(e.account.type)) &&
                 DatabaseBind(st, 4, SdbMarginModeText(e.account.marginMode)) && DatabaseBind(st, 5, e.account.currency) &&
                 DatabaseBind(st, 6, e.account.leverage) && DatabaseBind(st, 7, e.account.balance) &&
                 DatabaseBind(st, 8, e.account.equity) && DatabaseBind(st, 9, e.account.peakEquity) &&
                 DatabaseBind(st, 10, (long)m_offset) && DatabaseBind(st, 11, Utc(e.account.time));
            return ok;
         case SDB_Q_TRADE:
            ok = DatabaseBind(st, 0, m_sessionId) && DatabaseBind(st, 1, e.login) &&
                 DatabaseBind(st, 2, e.trade.positionId) && DatabaseBind(st, 3, e.trade.magic) &&
                 DatabaseBind(st, 4, e.trade.symbol) && DatabaseBind(st, 5, e.trade.direction) &&
                 DatabaseBind(st, 6, e.trade.source) && DatabaseBind(st, 7, e.trade.volumeInitial) &&
                 DatabaseBind(st, 8, e.trade.priceRequested) && DatabaseBind(st, 9, e.trade.priceOpen) &&
                 DatabaseBind(st, 10, e.trade.slippagePoints) && DatabaseBind(st, 11, e.trade.spreadPoints) &&
                 DatabaseBind(st, 12, e.trade.slInitial) && DatabaseBind(st, 13, e.trade.tpInitial) &&
                 DatabaseBind(st, 14, e.trade.riskMoney) && DatabaseBind(st, 15, e.trade.riskPct) &&
                 DatabaseBind(st, 16, e.trade.signalId) && DatabaseBind(st, 17, e.trade.eaVersion) &&
                 DatabaseBind(st, 18, Utc(e.trade.openedAt)) &&
                 DatabaseBind(st, SDB_BIND_NULL_DOUBLE, SDB_NULL_DOUBLE) && DatabaseBind(st, SDB_BIND_NULL_LONG, SDB_NULL_LONG);
            return ok;
         case SDB_Q_DEAL:
            ok = DatabaseBind(st, 0, m_sessionId) && DatabaseBind(st, 1, e.login) &&
                 DatabaseBind(st, 2, e.deal.dealTicket) && DatabaseBind(st, 3, e.deal.positionId) &&
                 DatabaseBind(st, 4, e.deal.magic) && DatabaseBind(st, 5, e.deal.symbol) &&
                 DatabaseBind(st, 6, Utc(e.deal.time)) && DatabaseBind(st, 7, e.deal.entry) &&
                 DatabaseBind(st, 8, e.deal.dealType) && DatabaseBind(st, 9, e.deal.volume) &&
                 DatabaseBind(st, 10, e.deal.price) && DatabaseBind(st, 11, e.deal.reason) &&
                 DatabaseBind(st, 12, e.deal.profit) && DatabaseBind(st, 13, e.deal.commission) &&
                 DatabaseBind(st, 14, e.deal.swap) && DatabaseBind(st, 15, e.deal.fee);
            return ok;
         case SDB_Q_POSITION:
            ok = DatabaseBind(st, 0, m_sessionId) && DatabaseBind(st, 1, e.login) &&
                 DatabaseBind(st, 2, e.position.positionId) && DatabaseBind(st, 3, Utc(e.position.time)) &&
                 DatabaseBind(st, 4, e.position.type) && DatabaseBind(st, 5, e.position.slOld) &&
                 DatabaseBind(st, 6, e.position.slNew) && DatabaseBind(st, 7, e.position.volume) &&
                 DatabaseBind(st, 8, e.position.price) && DatabaseBind(st, 9, e.position.spreadPoints) &&
                 DatabaseBind(st, 10, e.position.detail) && DatabaseBind(st, SDB_BIND_NULL_DOUBLE, SDB_NULL_DOUBLE);
            return ok;
         case SDB_Q_CLOSURE:
            ok = DatabaseBind(st, 0, m_sessionId) && DatabaseBind(st, 1, e.login) &&
                 DatabaseBind(st, 2, e.closure.positionId) && DatabaseBind(st, 3, e.closure.magic) &&
                 DatabaseBind(st, 4, e.closure.symbol) && DatabaseBind(st, 5, Utc(e.closure.closedAt)) &&
                 DatabaseBind(st, 6, e.closure.reason) && DatabaseBind(st, 7, e.closure.levelPrice) &&
                 DatabaseBind(st, 8, e.closure.priceClose) && DatabaseBind(st, 9, e.closure.slippagePoints) &&
                 DatabaseBind(st, 10, e.closure.volumeTotal) && DatabaseBind(st, 11, e.closure.profit) &&
                 DatabaseBind(st, 12, e.closure.commission) && DatabaseBind(st, 13, e.closure.swap) &&
                 DatabaseBind(st, 14, e.closure.fee) && DatabaseBind(st, 15, e.closure.netProfit) &&
                 DatabaseBind(st, 16, e.closure.rResult) && DatabaseBind(st, 17, e.closure.mfeR) &&
                 DatabaseBind(st, 18, e.closure.maeR) && DatabaseBind(st, 19, e.closure.holdingSec) &&
                 DatabaseBind(st, 20, (int)e.closure.beActivated) && DatabaseBind(st, 21, (int)e.closure.partialDone) &&
                 DatabaseBind(st, 22, (int)e.closure.trailActivated) &&
                 DatabaseBind(st, SDB_BIND_NULL_DOUBLE, SDB_NULL_DOUBLE) && DatabaseBind(st, SDB_BIND_NULL_LONG, SDB_NULL_LONG);
            return ok;
         case SDB_Q_BALANCE:
            ok = DatabaseBind(st, 0, e.login) && DatabaseBind(st, 1, e.balance.dealTicket) &&
                 DatabaseBind(st, 2, Utc(e.balance.time)) && DatabaseBind(st, 3, e.balance.opType) &&
                 DatabaseBind(st, 4, e.balance.amount) && DatabaseBind(st, 5, e.balance.comment);
            return ok;
         case SDB_Q_ALERT:
            ok = DatabaseBind(st, 0, m_sessionId) && DatabaseBind(st, 1, e.login) &&
                 DatabaseBind(st, 2, e.alert.magic) && DatabaseBind(st, 3, e.alert.symbol) &&
                 DatabaseBind(st, 4, Utc(e.alert.time)) && DatabaseBind(st, 5, e.alert.type) &&
                 DatabaseBind(st, 6, SdbSeverityText(e.alert.severity)) && DatabaseBind(st, 7, e.alert.message) &&
                 DatabaseBind(st, 8, SDB_ALERT_STATUS_PENDING);
            return ok;
        }
      return false;
     }

   // Satu transaksi untuk seluruh antrean; gagal di tengah = rollback dan antrean tetap utuh.
   bool WriteQueue(string &err)
     {
      m_offset = UtcOffset();
      ResetLastError();
      if(!DatabaseExecute(m_db, "BEGIN IMMEDIATE"))
        {
         err = "BEGIN IMMEDIATE " + ErrText(GetLastError());
         return false;
        }
      int n = ArraySize(m_queue);
      for(int i = 0; i < n; i++)
        {
         int st = Statement(m_queue[i].kind, err);
         bool ok = (st != INVALID_HANDLE);
         if(ok && !BindEvent(st, m_queue[i]))
           {
            ok = false;
            err = "bind " + EnumToString(m_queue[i].kind) + " " + ErrText(GetLastError());
           }
         if(ok && !Step(st, err))
           {
            ok = false;
            err = EnumToString(m_queue[i].kind) + " " + err;
           }
         if(!ok)
           {
            DatabaseExecute(m_db, "ROLLBACK");
            return false;
           }
        }
      ResetLastError();
      if(!DatabaseExecute(m_db, "COMMIT"))
        {
         err = "COMMIT " + ErrText(GetLastError());
         DatabaseExecute(m_db, "ROLLBACK");
         return false;
        }
      return true;
     }

   long InsertSession(const SessionInfo &s)
     {
      int st = DatabasePrepare(m_db, "INSERT INTO sessions (login, magic, symbol, mode, ea_version, input_hash, inputs_json, "
                                     "started_at, tester_from, tester_to, tester_model) "
                                     "VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, NULLIF(?9, 0), NULLIF(?10, 0), NULLIF(?11, '')) "
                                     "RETURNING id");
      if(st == INVALID_HANDLE)
        {
         LogError("Storage", "sesi tidak bisa dicatat | " + ErrText(GetLastError()));
         return 0;
        }
      long from = (s.testerFrom == 0) ? 0 : Utc(s.testerFrom);
      long to = (s.testerTo == 0) ? 0 : Utc(s.testerTo);
      long id = 0;
      if(DatabaseBind(st, 0, s.login) && DatabaseBind(st, 1, s.magic) && DatabaseBind(st, 2, s.symbol) &&
         DatabaseBind(st, 3, s.mode) && DatabaseBind(st, 4, s.eaVersion) && DatabaseBind(st, 5, Sha256Hex(s.inputsJson)) &&
         DatabaseBind(st, 6, s.inputsJson) && DatabaseBind(st, 7, Utc(s.startedAt)) && DatabaseBind(st, 8, from) &&
         DatabaseBind(st, 9, to) && DatabaseBind(st, 10, s.testerModel) && DatabaseRead(st))
         DatabaseColumnLong(st, 0, id);
      else
         LogError("Storage", "sesi tidak bisa dicatat | " + ErrText(GetLastError()));
      DatabaseFinalize(st);
      return id;
     }

public:
                     CLogger(void) : m_alertSink(NULL), m_magic(0), m_target(SDB_DB_NONE), m_db(INVALID_HANDLE),
                     m_disabled(true), m_capacity(SDB_DB_QUEUE_MAX), m_dropped(0), m_login(0), m_sessionId(0),
                     m_haveSession(false), m_haveAccount(false), m_failSince(0), m_unavailAlerted(false),
                     m_lastReopen(0), m_offset(0), m_nowOverride(0), m_offsetOverridden(false), m_offsetOverride(0)
     {
      for(int k = 0; k < SDB_Q_KINDS; k++)
         m_stmt[k] = INVALID_HANDLE;
     }

                    ~CLogger(void) { CloseDb(); }

   // alertSink menerima alert milik Logger (DB_*, MIGRATION_FAILED); NULL = hanya disimpan di DB.
   void Init(ISdbEventSink *alertSink, const string symbol, const long magic, const string eaVersion)
     {
      m_alertSink = alertSink;
      m_symbol = symbol;
      m_magic = magic;
      m_eaVersion = eaVersion;
      m_login = AccountInfoInteger(ACCOUNT_LOGIN);
     }

   // false = tanpa DB (NONE bukan kegagalan: mengembalikan true). EA tetap jalan apa pun hasilnya.
   bool Open(const ENUM_SDB_DB_TARGET target)
     {
      CloseDb();
      m_target = target;
      m_file = SdbDbFileFor(target);
      m_disabled = (target == SDB_DB_NONE);
      if(m_disabled)
         return true;
      if(OpenFile())
         return true;
      if(!m_disabled)   // file gagal dibuka: coba lagi dari Flush tiap SDB_DB_REOPEN_SEC
        {
         m_lastReopen = Now();
         UnavailableNow(Now(), "file " + m_file);
        }
      return false;
     }

   // Flush terakhir lalu tutup (Req 3.3). Setelah ini Logger tidak menerima event.
   void Close()
     {
      if(IsWritable())
         Flush();
      CloseDb();
      m_disabled = true;
      ArrayFree(m_queue);
     }

   bool IsWritable() const { return !m_disabled && m_db != INVALID_HANDLE; }

   // Dipanggil dari OnTimer. true = antrean kosong setelahnya.
   bool Flush()
     {
      if(m_disabled)
         return false;
      long now = Now();
      if(m_db == INVALID_HANDLE)
        {
         if(m_lastReopen == 0 || now - m_lastReopen >= SDB_DB_REOPEN_SEC)
            ReopenFile(now);
         if(m_db == INVALID_HANDLE)
           {
            if(!m_disabled)
               NoteFailure(now, "file " + m_file + " belum terbuka");
            return false;
           }
        }
      if(ArraySize(m_queue) == 0)
        {
         NoteSuccess();
         return true;
        }
      string err = "";
      bool ok = WriteQueue(err);
      if(!ok && SchemaMissing())   // file dihapus/diganti saat berjalan (EC-05)
        {
         LogWarn("Storage", "tabel DB hilang, file dibuka ulang dan dimigrasi | " + err);
         if((m_lastReopen == 0 || now - m_lastReopen >= SDB_DB_REOPEN_SEC) && ReopenFile(now))
            ok = WriteQueue(err);
        }
      if(!ok)
        {
         NoteFailure(now, err);
         return false;
        }
      ArrayResize(m_queue, 0);
      m_dropped = 0;
      NoteSuccess();
      return true;
     }

   // Ditulis langsung (bukan antrean) karena ID-nya dipakai event berikutnya (Req 8.1).
   long BeginSession(const SessionInfo &s)
     {
      if(m_disabled)
         return 0;
      m_session = s;
      m_haveSession = true;
      m_login = s.login;
      if(!IsWritable())
         return 0;   // dicatat saat file berhasil dibuka ulang
      m_offset = UtcOffset();
      m_sessionId = InsertSession(s);
      return m_sessionId;
     }

   // Sesi tanpa ended_at = berakhir tidak normal (Req 8.4). Sesi tester: tester_to = waktu simulasi terakhir,
   // karena MQL5 tidak menyediakan tanggal akhir dan model tester.
   void EndSession(const int reason)
     {
      m_haveSession = false;
      if(!IsWritable() || m_sessionId == 0)
         return;
      m_offset = UtcOffset();
      int st = DatabasePrepare(m_db, "UPDATE sessions SET ended_at = ?1, end_reason = ?2, "
                                     "tester_to = CASE WHEN mode = 'TESTER' THEN ?1 ELSE tester_to END WHERE id = ?3");
      if(st == INVALID_HANDLE)
         return;
      string err;
      if(!(DatabaseBind(st, 0, Utc(TimeCurrent())) && DatabaseBind(st, 1, SdbDeinitReasonText(reason)) &&
           DatabaseBind(st, 2, m_sessionId) && Step(st, err)))
         LogWarn("Storage", "akhir sesi tidak tercatat | " + err);
      DatabaseFinalize(st);
     }

   long SessionId() const    { return m_sessionId; }
   int  QueueSize() const    { return ArraySize(m_queue); }
   int  DroppedCount() const { return m_dropped; }

   //--- Hook uji
   void SetQueueCapacityForTest(const int n) { m_capacity = n; }
   void SetNowForTest(const long sec)        { m_nowOverride = sec; }
   void SetUtcOffsetForTest(const int sec)   { m_offsetOverridden = true; m_offsetOverride = sec; }

   //--- ISdbEventSink (Req 9)
   void OnAccount(const AccountSnapshot &a)
     {
      m_account = a;
      m_haveAccount = true;
      m_login = a.login;
      SdbQueuedEvent e;
      e.kind = SDB_Q_ACCOUNT;
      e.priority = SDB_Q_PRIO_NORMAL;
      e.login = a.login;
      e.account = a;
      Enqueue(e);
     }

   void OnTradeOpened(const TradeRecord &t)
     {
      SdbQueuedEvent e;
      e.kind = SDB_Q_TRADE;
      e.priority = SDB_Q_PRIO_KEEP;
      e.login = m_login;
      e.trade = t;
      Enqueue(e);
     }

   void OnDeal(const DealRecord &d)
     {
      SdbQueuedEvent e;
      e.kind = SDB_Q_DEAL;
      e.priority = SDB_Q_PRIO_KEEP;
      e.login = m_login;
      e.deal = d;
      Enqueue(e);
     }

   void OnPositionEvent(const PositionEvent &p)
     {
      SdbQueuedEvent e;
      e.kind = SDB_Q_POSITION;
      e.priority = SDB_Q_PRIO_NORMAL;
      e.login = m_login;
      e.position = p;
      Enqueue(e);
     }

   void OnClosure(const ClosureRecord &c)
     {
      SdbQueuedEvent e;
      e.kind = SDB_Q_CLOSURE;
      e.priority = SDB_Q_PRIO_KEEP;
      e.login = m_login;
      e.closure = c;
      Enqueue(e);
     }

   void OnBalanceOp(const BalanceOpRecord &b)
     {
      SdbQueuedEvent e;
      e.kind = SDB_Q_BALANCE;
      e.priority = SDB_Q_PRIO_KEEP;
      e.login = m_login;
      e.balance = b;
      Enqueue(e);
     }

   // Disimpan PENDING, attempts 0; dikirim Notifier di Fase 2 (Req 9.2).
   void OnAlert(const AlertEvent &a)
     {
      SdbQueuedEvent e;
      e.kind = SDB_Q_ALERT;
      e.priority = (a.severity == SDB_SEV_CRITICAL) ? SDB_Q_PRIO_KEEP : SDB_Q_PRIO_NORMAL;
      e.login = m_login;
      e.alert = a;
      Enqueue(e);
     }

   // Dibaca langsung dari DB, bukan antrean (Req 9.3).
   bool FindInitialSl(const long login, const ulong positionId, double &sl)
     {
      sl = 0.0;
      if(!IsWritable())
         return false;
      int st = DatabasePrepare(m_db, "SELECT sl_initial FROM trades WHERE login = ?1 AND position_id = ?2");
      if(st == INVALID_HANDLE)
         return false;
      bool found = DatabaseBind(st, 0, login) && DatabaseBind(st, 1, (long)positionId) && DatabaseRead(st) &&
                   DatabaseColumnDouble(st, 0, sl);
      DatabaseFinalize(st);
      return found;
     }
  };

#endif // SDB_STORAGE_LOGGER_MQH
