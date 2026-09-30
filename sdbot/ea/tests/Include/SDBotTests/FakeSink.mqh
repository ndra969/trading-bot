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
   bool FindInitialSl(const long login, const ulong positionId, double &sl) { sl = 0.0; return false; }

   int  CountAccount() const { return ArraySize(m_accounts); }
   int  CountAlert() const   { return ArraySize(m_alerts); }
   int  CountDeal() const    { return ArraySize(m_deals); }
   int  CountClosure() const { return ArraySize(m_closures); }
   int  CountTrade() const   { return ArraySize(m_trades); }
   int  CountEvent() const   { return ArraySize(m_events); }
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
     }
  };

#endif // SDB_SDBOTTESTS_FAKESINK_MQH
