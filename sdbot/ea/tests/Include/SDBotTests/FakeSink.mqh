//+------------------------------------------------------------------+
//| FakeSink.mqh — event sink palsu untuk unit test: menyimpan event
//| yang diterima agar suite bisa meng-assert apa yang dikirim modul.
//| Jenis event lain ditambahkan hitungannya oleh spec yang memakainya.
//+------------------------------------------------------------------+
#ifndef SDB_SDBOTTESTS_FAKESINK_MQH
#define SDB_SDBOTTESTS_FAKESINK_MQH

#include <SDBot/Core/EventSink.mqh>

class CFakeSink : public ISdbEventSink
  {
private:
   AccountSnapshot   m_accounts[];
   AlertEvent        m_alerts[];
   DealRecord        m_deals[];
   ClosureRecord     m_closures[];
   TradeRecord       m_trades[];
   PositionEvent     m_events[];
   AlertStatus       m_statuses[];

public:
   void OnAccount(const AccountSnapshot &a)
     {
      int n = ArraySize(m_accounts);
      ArrayResize(m_accounts, n + 1);
      m_accounts[n] = a;
     }
   void OnAlert(const AlertEvent &a)
     {
      int n = ArraySize(m_alerts);
      ArrayResize(m_alerts, n + 1);
      m_alerts[n] = a;
     }
   void OnTradeOpened(const TradeRecord &t)
     {
      int n = ArraySize(m_trades);
      ArrayResize(m_trades, n + 1);
      m_trades[n] = t;
     }
   void OnDeal(const DealRecord &d)
     {
      int n = ArraySize(m_deals);
      ArrayResize(m_deals, n + 1);
      m_deals[n] = d;
     }
   void OnPositionEvent(const PositionEvent &e)
     {
      int n = ArraySize(m_events);
      ArrayResize(m_events, n + 1);
      m_events[n] = e;
     }
   void OnClosure(const ClosureRecord &c)
     {
      int n = ArraySize(m_closures);
      ArrayResize(m_closures, n + 1);
      m_closures[n] = c;
     }
   void OnBalanceOp(const BalanceOpRecord &b)   { }
   void OnAlertStatus(const AlertStatus &s)
     {
      int n = ArraySize(m_statuses);
      ArrayResize(m_statuses, n + 1);
      m_statuses[n] = s;
     }
   bool FindInitialSl(const long login, const ulong positionId, double &sl) { sl = 0.0; return false; }

   int  CountAccount() const { return ArraySize(m_accounts); }
   int  CountAlert() const   { return ArraySize(m_alerts); }
   int  CountDeal() const    { return ArraySize(m_deals); }
   int  CountClosure() const { return ArraySize(m_closures); }
   int  CountTrade() const   { return ArraySize(m_trades); }
   int  CountEvent() const   { return ArraySize(m_events); }
   int  CountStatus() const  { return ArraySize(m_statuses); }
   bool LastStatus(AlertStatus &out) const
     {
      int n = ArraySize(m_statuses);
      if(n == 0)
         return false;
      out = m_statuses[n - 1];
      return true;
     }
   bool StatusAt(const int i, AlertStatus &out) const
     {
      if(i < 0 || i >= ArraySize(m_statuses))
         return false;
      out = m_statuses[i];
      return true;
     }
   // Status terakhir untuk key; false bila belum ada.
   bool StatusOf(const string key, AlertStatus &out) const
     {
      for(int i = ArraySize(m_statuses) - 1; i >= 0; i--)
         if(m_statuses[i].key == key)
           {
            out = m_statuses[i];
            return true;
           }
      return false;
     }
   bool AlertAt(const int i, AlertEvent &out) const
     {
      if(i < 0 || i >= ArraySize(m_alerts))
         return false;
      out = m_alerts[i];
      return true;
     }
   bool LastClosure(ClosureRecord &out) const
     {
      int n = ArraySize(m_closures);
      if(n == 0)
         return false;
      out = m_closures[n - 1];
      return true;
     }
   bool LastTrade(TradeRecord &out) const
     {
      int n = ArraySize(m_trades);
      if(n == 0)
         return false;
      out = m_trades[n - 1];
      return true;
     }
   int  CountAlertType(const string type) const
     {
      int n = 0;
      for(int i = 0; i < ArraySize(m_alerts); i++)
         if(m_alerts[i].type == type)
            n++;
      return n;
     }

   bool LastAlert(AlertEvent &out) const
     {
      int n = ArraySize(m_alerts);
      if(n == 0)
         return false;
      out = m_alerts[n - 1];
      return true;
     }

   bool LastAccount(AccountSnapshot &out) const
     {
      int n = ArraySize(m_accounts);
      if(n == 0)
         return false;
      out = m_accounts[n - 1];
      return true;
     }

   void Reset()
     {
      ArrayFree(m_accounts);
      ArrayFree(m_alerts);
      ArrayFree(m_deals);
      ArrayFree(m_closures);
      ArrayFree(m_trades);
      ArrayFree(m_events);
      ArrayFree(m_statuses);
     }
  };

#endif // SDB_SDBOTTESTS_FAKESINK_MQH
