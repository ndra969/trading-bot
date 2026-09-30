//+------------------------------------------------------------------+
//| ScenarioRecorder.mqh — CScenarioRecorder: sink pengamat harness
//| (spec 04 Req 7.6, design §4.6). Menyimpan event yang dikirim modul,
//| hasil setiap OpenMarket, ID sesi tiap init, dan posisi sebelum/
//| sesudah restart. Hidup di luar CSdbApp agar selamat dari restart.
//+------------------------------------------------------------------+
#ifndef SDB_SDBOTTESTS_SCENARIORECORDER_MQH
#define SDB_SDBOTTESTS_SCENARIORECORDER_MQH

#include <SDBot/Core/EventSink.mqh>

class CScenarioRecorder : public ISdbEventSink
  {
private:
   TradeRecord       m_trades[];
   AlertEvent        m_alerts[];
   datetime          m_snapshotTimes[];
   OrderResult       m_opens[];
   long              m_sessions[];
   long              m_posBeforeRestart[];
   long              m_posAfterRestart[];
   long              m_sends;           // jumlah OrderSend dari semua CExecutor (termasuk sebelum restart)
   int               m_deals;
   int               m_positionEvents;
   int               m_closures;
   int               m_balanceOps;

   static void PushLong(long &arr[], const long v)
     {
      int n = ArraySize(arr);
      ArrayResize(arr, n + 1);
      arr[n] = v;
     }

public:
                     CScenarioRecorder(void) : m_sends(0), m_deals(0), m_positionEvents(0), m_closures(0), m_balanceOps(0) {}

   //--- ISdbEventSink
   // Jam timer (TimeLocal), bukan a.time: a.time = waktu tick terakhir, yang tertinggal dari jadwal
   // snapshot saat tidak ada tick, sehingga jedanya tampak 59 atau 31 detik.
   void OnAccount(const AccountSnapshot &a)
     {
      int n = ArraySize(m_snapshotTimes);
      ArrayResize(m_snapshotTimes, n + 1);
      m_snapshotTimes[n] = TimeLocal();
     }
   void OnTradeOpened(const TradeRecord &t)
     {
      int n = ArraySize(m_trades);
      ArrayResize(m_trades, n + 1);
      m_trades[n] = t;
     }
   void OnAlert(const AlertEvent &a)
     {
      int n = ArraySize(m_alerts);
      ArrayResize(m_alerts, n + 1);
      m_alerts[n] = a;
     }
   void OnDeal(const DealRecord &d)             { m_deals++; }
   void OnPositionEvent(const PositionEvent &e) { m_positionEvents++; }
   void OnClosure(const ClosureRecord &c)       { m_closures++; }
   void OnBalanceOp(const BalanceOpRecord &b)   { m_balanceOps++; }
   bool FindInitialSl(const long login, const ulong positionId, double &sl) { sl = 0.0; return false; }

   //--- Catatan dari harness
   void AddOpenResult(const OrderResult &r)
     {
      int n = ArraySize(m_opens);
      ArrayResize(m_opens, n + 1);
      m_opens[n] = r;
     }
   void AddSession(const long sessionId)           { PushLong(m_sessions, sessionId); }
   void AddSends(const long n)                     { m_sends += n; }
   void AddPositionBeforeRestart(const long id)    { PushLong(m_posBeforeRestart, id); }
   void AddPositionAfterRestart(const long id)     { PushLong(m_posAfterRestart, id); }

   //--- Bacaan untuk pemeriksa skenario
   int  TradeCount() const                  { return ArraySize(m_trades); }
   bool TradeAt(const int i, TradeRecord &t) const
     {
      if(i < 0 || i >= ArraySize(m_trades))
         return false;
      t = m_trades[i];
      return true;
     }
   int  AlertCount() const                  { return ArraySize(m_alerts); }
   bool AlertAt(const int i, AlertEvent &a) const
     {
      if(i < 0 || i >= ArraySize(m_alerts))
         return false;
      a = m_alerts[i];
      return true;
     }
   int      SnapshotCount() const           { return ArraySize(m_snapshotTimes); }
   datetime SnapshotTime(const int i) const { return m_snapshotTimes[i]; }
   int  OpenCount() const                   { return ArraySize(m_opens); }
   bool OpenAt(const int i, OrderResult &r) const
     {
      if(i < 0 || i >= ArraySize(m_opens))
         return false;
      r = m_opens[i];
      return true;
     }
   int  OpenOkCount() const
     {
      int n = 0;
      for(int i = 0; i < ArraySize(m_opens); i++)
         if(m_opens[i].ok)
            n++;
      return n;
     }
   int  SessionCount() const                { return ArraySize(m_sessions); }
   long SessionAt(const int i) const        { return m_sessions[i]; }
   long Sends() const                       { return m_sends; }
   int  PositionsBeforeRestart() const      { return ArraySize(m_posBeforeRestart); }
   long PositionBeforeRestartAt(const int i) const { return m_posBeforeRestart[i]; }
   bool HasPositionAfterRestart(const long id) const
     {
      for(int i = 0; i < ArraySize(m_posAfterRestart); i++)
         if(m_posAfterRestart[i] == id)
            return true;
      return false;
     }

   // "1,2,3" untuk klausa SQL IN; "0" bila belum ada sesi (tidak cocok dengan id mana pun).
   string SessionIdList() const
     {
      string s = "";
      for(int i = 0; i < ArraySize(m_sessions); i++)
         s += (i > 0 ? "," : "") + IntegerToString(m_sessions[i]);
      return (s == "") ? "0" : s;
     }
  };

#endif // SDB_SDBOTTESTS_SCENARIORECORDER_MQH
