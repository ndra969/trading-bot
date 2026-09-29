//+------------------------------------------------------------------+
//| Account.mqh — CAccount: memutuskan apakah EA boleh jalan (validasi
//| akun) dan boleh trading (izin + koneksi), memakai aturan murni di
//| AccountRules.mqh. Validasi tertunda bila terminal belum login
//| (spec 02 Req 2–3, design §3.5).
//+------------------------------------------------------------------+
#ifndef SDB_ACCOUNT_ACCOUNT_MQH
#define SDB_ACCOUNT_ACCOUNT_MQH

#include <SDBot/Core/EventSink.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Account/AccountRules.mqh>

class CAccount
  {
private:
   ISdbEventSink    *m_sink;
   CNullSink         m_nullSink;
   string            m_symbol;
   string            m_suffix;
   bool              m_allowLive;
   long              m_magic;
   ENUM_SDB_VALIDATION m_state;
   string            m_reason;
   long              m_login;
   bool              m_rejectedFromTimer;
   bool              m_pendingLogged;
   bool              m_canTrade;
   string            m_canTradeWhy;
   bool              m_permKnown;
   datetime          m_downSince;
   datetime          m_lastConnAlert;
   bool              m_connAlerted;

   void SendAlert(const string type, const ENUM_SDB_SEVERITY severity, const string message)
     {
      AlertEvent a;
      a.type = type;
      a.severity = severity;
      a.message = message;
      a.symbol = m_symbol;
      a.magic = m_magic;
      a.time = TimeCurrent();
      m_sink.OnAlert(a);
     }

   // Semua syarat akun dan simbol; alasan penolakan digabung di m_reason.
   bool CheckRules()
     {
      string reason = "";
      EvaluateAccount((ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE),
                      (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE), m_allowLive, reason);
      if(!SymbolMatchesSuffix(m_symbol, m_suffix))
         reason = ArJoin(reason, "simbol " + m_symbol + " tidak berakhiran InpSymbolSuffix=\"" + m_suffix + "\"");
      if(!SymbolSelect(m_symbol, true))
         reason = ArJoin(reason, "simbol " + m_symbol + " tidak bisa ditambahkan ke Market Watch " + ErrText(GetLastError()));
      m_reason = reason;
      return reason == "";
     }

   void RefreshPermission()
     {
      string why;
      bool ok = TradePermission((bool)TerminalInfoInteger(TERMINAL_CONNECTED),
                                (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED),
                                (bool)MQLInfoInteger(MQL_TRADE_ALLOWED),
                                (bool)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED),
                                (bool)AccountInfoInteger(ACCOUNT_TRADE_EXPERT),
                                (ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(m_symbol, SYMBOL_TRADE_MODE), why);
      if(m_permKnown && ok != m_canTrade)
        {
         if(ok)
            LogInfo("Account", "izin trading kembali");
         else
            LogWarn("Account", "izin trading mati | " + why);
        }
      m_canTrade = ok;
      m_canTradeWhy = why;
      m_permKnown = true;
     }

   void CheckConnection()
     {
      ENUM_SDB_CONN_ACTION act = ConnectionStep((bool)TerminalInfoInteger(TERMINAL_CONNECTED), TimeLocal(),
                                                m_downSince, m_lastConnAlert, m_connAlerted);
      if(act == SDB_CONN_LOG_DOWN)
         LogWarn("Account", "terminal terputus, entry ditahan");
      else if(act == SDB_CONN_ALERT_MEDIUM)
        {
         LogWarn("Account", "terminal terputus lebih dari 5 menit");
         SendAlert(SDB_ALERT_CONN_DOWN, SDB_SEV_MEDIUM, "Terminal terputus lebih dari 5 menit, entry ditahan");
        }
      else if(act == SDB_CONN_ALERT_RECOVERED)
        {
         LogInfo("Account", "koneksi pulih");
         SendAlert(SDB_ALERT_CONN_UP, SDB_SEV_INFO, "Koneksi terminal pulih");
        }
     }

public:
                     CAccount(void) : m_sink(NULL), m_state(SDB_VAL_PENDING), m_login(0),
                     m_rejectedFromTimer(false), m_pendingLogged(false), m_canTrade(false),
                     m_permKnown(false), m_downSince(0), m_lastConnAlert(0), m_connAlerted(false) {}

   // Nilai input diberikan lewat parameter (bukan dibaca dari Inp*) agar kelas bisa diuji.
   bool Init(ISdbEventSink *sink, const string symbol, const string suffix, const bool allowLive, const long magic)
     {
      m_sink = (sink == NULL) ? GetPointer(m_nullSink) : sink;
      m_symbol = symbol;
      m_suffix = suffix;
      m_allowLive = allowLive;
      m_magic = magic;
      return true;
     }

   ENUM_SDB_VALIDATION Validate()
     {
      long login = AccountInfoInteger(ACCOUNT_LOGIN);
      if(!(bool)TerminalInfoInteger(TERMINAL_CONNECTED) || login == 0)
        {
         m_state = SDB_VAL_PENDING;
         if(!m_pendingLogged)
            LogInfo("Account", "validasi akun tertunda: terminal belum terkoneksi atau belum login");
         m_pendingLogged = true;
         return m_state;
        }
      if(!CheckRules())
        {
         m_state = SDB_VAL_REJECTED;
         LogCritical("Account", "EA tidak boleh jalan di akun ini | " + m_reason);
         SendAlert(SDB_ALERT_ACCOUNT_REJECTED, SDB_SEV_CRITICAL, "SDBot berhenti: " + m_reason);
         return m_state;
        }
      m_state = SDB_VAL_PASSED;
      m_login = login;
      m_sink.OnAccount(Snapshot());
      LogInfo("Account", "akun valid | login=" + IntegerToString(login) + " currency=" + AccountInfoString(ACCOUNT_CURRENCY));
      return m_state;
     }

   ENUM_SDB_VALIDATION State() const        { return m_state; }
   string              LastReason() const   { return m_reason; }
   bool                RejectedFromTimer() const { return m_rejectedFromTimer; }
   long                Login() const        { return m_login; }

   // Dipanggil tiap detik: validasi tertunda, ganti akun (Req 2.9), koneksi, izin.
   void OnTimer()
     {
      if(m_state == SDB_VAL_PENDING)
        {
         if(Validate() == SDB_VAL_REJECTED)
            m_rejectedFromTimer = true;
        }
      else if(m_state == SDB_VAL_PASSED)
        {
         long login = AccountInfoInteger(ACCOUNT_LOGIN);
         if(login != 0 && login != m_login)
           {
            LogWarn("Account", "login berubah " + IntegerToString(m_login) + " -> " + IntegerToString(login) + ", validasi ulang");
            if(Validate() == SDB_VAL_REJECTED)
               m_rejectedFromTimer = true;
           }
        }
      CheckConnection();
      RefreshPermission();
     }

   bool CanTrade(string &why)
     {
      if(m_state != SDB_VAL_PASSED)
        {
         why = "validasi akun belum lolos";
         return false;
        }
      if(!m_permKnown)
         RefreshPermission();
      why = m_canTradeWhy;
      return m_canTrade;
     }

   AccountSnapshot Snapshot()
     {
      AccountSnapshot s;
      s.login = AccountInfoInteger(ACCOUNT_LOGIN);
      s.server = AccountInfoString(ACCOUNT_SERVER);
      s.company = AccountInfoString(ACCOUNT_COMPANY);
      s.currency = AccountInfoString(ACCOUNT_CURRENCY);
      s.type = AccountTypeOf((ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE), s.currency);
      s.marginMode = (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
      s.leverage = AccountInfoInteger(ACCOUNT_LEVERAGE);
      s.balance = AccountInfoDouble(ACCOUNT_BALANCE);
      s.equity = AccountInfoDouble(ACCOUNT_EQUITY);
      s.time = TimeCurrent();
      return s;
     }
  };

#endif // SDB_ACCOUNT_ACCOUNT_MQH
