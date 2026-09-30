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
   void OnTradeOpened(const TradeRecord &t)     { }
   void OnDeal(const DealRecord &d)             { }
   void OnPositionEvent(const PositionEvent &e) { }
   void OnClosure(const ClosureRecord &c)       { }
   void OnBalanceOp(const BalanceOpRecord &b)   { }
   bool FindInitialSl(const long login, const ulong positionId, double &sl) { sl = 0.0; return false; }

   int  CountAccount() const { return ArraySize(m_accounts); }
   int  CountAlert() const   { return ArraySize(m_alerts); }
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
     }
  };

#endif // SDB_SDBOTTESTS_FAKESINK_MQH
