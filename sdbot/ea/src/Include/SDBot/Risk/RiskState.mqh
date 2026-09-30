//+------------------------------------------------------------------+
//| RiskState.mqh — CRiskState: akses bertipe ke status risiko akun di
//| Global Variables "<prefix>_<login>_<NAMA>" (spec 05 design §4.2).
//| Getter membaca GV langsung tanpa cache agar instance lain langsung
//| terlihat (Req 6.2). Keputusan akun memakai compare-and-set
//| (GlobalVariableSetOnCondition): hanya satu instance yang menang (6.3).
//+------------------------------------------------------------------+
#ifndef SDB_RISK_RISKSTATE_MQH
#define SDB_RISK_RISKSTATE_MQH

#include <SDBot/Core/State.mqh>
#include <SDBot/Risk/RiskMath.mqh>

#define SDB_GV_PEAK_EQUITY        "PEAK_EQUITY"
#define SDB_GV_STOPPED            "STOPPED"
#define SDB_GV_DAILY_PAUSE        "DAILY_PAUSE"
#define SDB_GV_LOT_REDUCED        "LOT_REDUCED"
#define SDB_GV_DAY_START_BAL      "DAY_START_BAL"
#define SDB_GV_DAY_START_DATE     "DAY_START_DATE"
#define SDB_GV_LAST_BAL_DEAL      "LAST_BAL_DEAL"
#define SDB_GV_LAST_BAL_TIME      "LAST_BAL_TIME"
#define SDB_GV_DD_LEVEL           "DD_LEVEL"
#define SDB_GV_MARGIN_LOW         "MARGIN_LOW"
#define SDB_GV_CLOSE_ALL_ALERT_AT "CLOSE_ALL_ALERT_AT"
#define SDB_GV_RESET_SEEN         "RESET_SEEN"      // per magic: "<magic>_RESET_SEEN"

class CRiskState
  {
private:
   CState           *m_st;
   long              m_magic;
   bool              m_fresh;          // PEAK_EQUITY belum ada saat Init
   bool              m_balBaseline;    // LAST_BAL_DEAL belum ada saat Init: operasi lama tidak diproses (7.5)

   double Num(const string name, const double fallback) { return m_st.Get(name, fallback); }

   bool Cas(const string name, const double newValue, const double expected)
     {
      return GlobalVariableSetOnCondition(m_st.Key(name), newValue, expected);
     }

   // Tambah nilai GV secara atomik terhadap instance lain (dibaca ulang bila kalah).
   bool CasAdd(const string name, const double amount)
     {
      for(int i = 0; i < SDB_CAS_RETRY; i++)
        {
         double old = Num(name, 0.0);
         if(Cas(name, old + amount, old))
            return true;
        }
      LogThrottled(SDB_LOG_ERROR, "risk-cas-" + name, SDB_LOG_THROTTLE_DEFAULT_SEC, "Risk",
                   "compare-and-set gagal berulang | gv=" + m_st.Key(name));
      return false;
     }

   string ResetSeenName() const { return IntegerToString(m_magic) + "_" + SDB_GV_RESET_SEEN; }

public:
                     CRiskState(void) : m_st(NULL), m_magic(0), m_fresh(false), m_balBaseline(false) {}

   // Nilai awal aman spec 02 §4.5 + design §5. false bila status bersama belum siap (akun belum login).
   bool Init(CState *state, const long magic, const double equity, const double balance, const datetime serverNow)
     {
      m_st = state;
      m_magic = magic;
      if(m_st == NULL || !m_st.IsReady())
         return false;
      bool missing = false;
      m_st.GetOrInit(SDB_GV_PEAK_EQUITY, equity, m_fresh);
      m_st.GetOrInit(SDB_GV_STOPPED, 0.0, missing);
      m_st.GetOrInit(SDB_GV_DAILY_PAUSE, 0.0, missing);
      m_st.GetOrInit(SDB_GV_LOT_REDUCED, 0.0, missing);
      m_st.GetOrInit(SDB_GV_DAY_START_BAL, balance, missing);
      m_st.GetOrInit(SDB_GV_DAY_START_DATE, (double)ServerDayStart(serverNow), missing);
      m_st.GetOrInit(SDB_GV_LAST_BAL_DEAL, 0.0, m_balBaseline);
      m_st.GetOrInit(SDB_GV_LAST_BAL_TIME, 0.0, missing);
      m_st.GetOrInit(SDB_GV_DD_LEVEL, (double)SDB_DD_NORMAL, missing);
      m_st.GetOrInit(SDB_GV_MARGIN_LOW, 0.0, missing);
      m_st.GetOrInit(SDB_GV_CLOSE_ALL_ALERT_AT, 0.0, missing);
      m_st.GetOrInit(ResetSeenName(), 0.0, missing);
      return true;
     }

   bool IsReady() const               { return m_st != NULL && m_st.IsReady(); }
   bool WasFresh() const              { return m_fresh; }
   bool BalanceBaselineNeeded() const { return m_balBaseline; }
   void BalanceBaselineDone()         { m_balBaseline = false; }

   //--- Puncak equity (3.2) dan operasi saldo (7.1)
   double PeakEquity() { return Num(SDB_GV_PEAK_EQUITY, 0.0); }

   bool RaisePeak(const double equity)
     {
      for(int i = 0; i < SDB_CAS_RETRY; i++)
        {
         double old = PeakEquity();
         if(equity <= old)
            return false;
         if(Cas(SDB_GV_PEAK_EQUITY, equity, old))
            return true;
        }
      return false;
     }

   bool AdjustPeakAndDayStart(const double amount)
     {
      bool a = CasAdd(SDB_GV_PEAK_EQUITY, amount);
      bool b = CasAdd(SDB_GV_DAY_START_BAL, amount);
      GlobalVariablesFlush();
      return a && b;
     }

   //--- Flag (flush: tidak boleh hilang saat terminal crash)
   bool IsStopped()                 { return Num(SDB_GV_STOPPED, 0.0) != 0.0; }
   void SetStopped(const bool v)    { m_st.Set(SDB_GV_STOPPED, v ? 1.0 : 0.0, true); }
   bool IsDailyPaused()             { return Num(SDB_GV_DAILY_PAUSE, 0.0) != 0.0; }
   bool TryPauseToday()
     {
      bool won = Cas(SDB_GV_DAILY_PAUSE, 1.0, 0.0);
      if(won)
         GlobalVariablesFlush();
      return won;
     }
   bool IsLotReduced()              { return Num(SDB_GV_LOT_REDUCED, 0.0) != 0.0; }
   void SetLotReduced(const bool v) { m_st.Set(SDB_GV_LOT_REDUCED, v ? 1.0 : 0.0, true); }

   //--- Level drawdown dan alert margin (3.9)
   ENUM_SDB_DD_LEVEL DdLevel() { return (ENUM_SDB_DD_LEVEL)(int)Num(SDB_GV_DD_LEVEL, (double)SDB_DD_NORMAL); }
   bool TryMoveDdLevel(const ENUM_SDB_DD_LEVEL from, const ENUM_SDB_DD_LEVEL to)
     {
      bool won = Cas(SDB_GV_DD_LEVEL, (double)to, (double)from);
      if(won)
         GlobalVariablesFlush();
      return won;
     }
   // low = true: 0 -> 1 (alert margin rendah); low = false: 1 -> 0 (pulih).
   bool TryMarginAlert(const bool low) { return low ? Cas(SDB_GV_MARGIN_LOW, 1.0, 0.0) : Cas(SDB_GV_MARGIN_LOW, 0.0, 1.0); }

   //--- Hari server (4.3)
   double   DayStartBalance() { return Num(SDB_GV_DAY_START_BAL, 0.0); }
   datetime DayStartDate()    { return (datetime)(long)Num(SDB_GV_DAY_START_DATE, 0.0); }
   bool TryClaimNewDay(const datetime storedDay, const datetime newDay, const double balance)
     {
      if(!Cas(SDB_GV_DAY_START_DATE, (double)newDay, (double)storedDay))
         return false;
      m_st.Set(SDB_GV_DAY_START_BAL, balance, false);
      m_st.Set(SDB_GV_DAILY_PAUSE, 0.0, true);
      return true;
     }

   //--- Operasi saldo (7.2, 7.3). Tiket disimpan double: tepat sampai 2^53.
   ulong    LastBalanceDeal()                { return (ulong)Num(SDB_GV_LAST_BAL_DEAL, 0.0); }
   datetime LastBalanceTime()                { return (datetime)(long)Num(SDB_GV_LAST_BAL_TIME, 0.0); }
   void     SetLastBalanceTime(const datetime t) { m_st.Set(SDB_GV_LAST_BAL_TIME, (double)t, false); }
   void     SetBalanceBaseline(const ulong ticket, const datetime t)
     {
      m_st.Set(SDB_GV_LAST_BAL_DEAL, (double)ticket, false);
      m_st.Set(SDB_GV_LAST_BAL_TIME, (double)t, true);
      m_balBaseline = false;
     }
   bool TryClaimBalanceDeal(const ulong lastSeen, const ulong ticket)
     {
      bool won = Cas(SDB_GV_LAST_BAL_DEAL, (double)ticket, (double)lastSeen);
      if(won)
         GlobalVariablesFlush();
      return won;
     }

   //--- Alert close all, dedupe antar-instance (5.3)
   datetime CloseAllAlertAt() { return (datetime)(long)Num(SDB_GV_CLOSE_ALL_ALERT_AT, 0.0); }
   bool TryClaimCloseAllAlert(const datetime lastSeen, const datetime now)
     {
      return Cas(SDB_GV_CLOSE_ALL_ALERT_AT, (double)now, (double)lastSeen);
     }

   //--- Reset emergency (5.5, 5.6)
   bool ResetInputLastSeen()                 { return Num(ResetSeenName(), 0.0) != 0.0; }
   void SetResetInputLastSeen(const bool v)  { m_st.Set(ResetSeenName(), v ? 1.0 : 0.0, true); }

   void ResetAfterEmergency(const double equity)
     {
      m_st.Set(SDB_GV_PEAK_EQUITY, equity, false);
      m_st.Set(SDB_GV_DD_LEVEL, (double)SDB_DD_NORMAL, false);
      m_st.Set(SDB_GV_LOT_REDUCED, 0.0, false);
      m_st.Set(SDB_GV_STOPPED, 0.0, true);
     }
  };

#endif // SDB_RISK_RISKSTATE_MQH
