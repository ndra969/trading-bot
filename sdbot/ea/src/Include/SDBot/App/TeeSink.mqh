//+------------------------------------------------------------------+
//| TeeSink.mqh — CTeeSink: meneruskan setiap event ke dua sink (Logger
//| dan perekam harness), tanpa mengubah penulisan ke DB (spec 04 Req 7.6).
//+------------------------------------------------------------------+
#ifndef SDB_APP_TEESINK_MQH
#define SDB_APP_TEESINK_MQH

#include <SDBot/Core/EventSink.mqh>

class CTeeSink : public ISdbEventSink
  {
private:
   ISdbEventSink    *m_primary;     // Logger: sumber FindInitialSl
   ISdbEventSink    *m_secondary;

public:
                     CTeeSink(void) : m_primary(NULL), m_secondary(NULL) {}

   void Init(ISdbEventSink *primary, ISdbEventSink *secondary)
     {
      m_primary = primary;
      m_secondary = secondary;
     }

   void OnAccount(const AccountSnapshot &a)
     {
      if(m_primary != NULL)   m_primary.OnAccount(a);
      if(m_secondary != NULL) m_secondary.OnAccount(a);
     }
   void OnTradeOpened(const TradeRecord &t)
     {
      if(m_primary != NULL)   m_primary.OnTradeOpened(t);
      if(m_secondary != NULL) m_secondary.OnTradeOpened(t);
     }
   void OnDeal(const DealRecord &d)
     {
      if(m_primary != NULL)   m_primary.OnDeal(d);
      if(m_secondary != NULL) m_secondary.OnDeal(d);
     }
   void OnPositionEvent(const PositionEvent &e)
     {
      if(m_primary != NULL)   m_primary.OnPositionEvent(e);
      if(m_secondary != NULL) m_secondary.OnPositionEvent(e);
     }
   void OnClosure(const ClosureRecord &c)
     {
      if(m_primary != NULL)   m_primary.OnClosure(c);
      if(m_secondary != NULL) m_secondary.OnClosure(c);
     }
   void OnBalanceOp(const BalanceOpRecord &b)
     {
      if(m_primary != NULL)   m_primary.OnBalanceOp(b);
      if(m_secondary != NULL) m_secondary.OnBalanceOp(b);
     }
   void OnAlert(const AlertEvent &a)
     {
      if(m_primary != NULL)   m_primary.OnAlert(a);
      if(m_secondary != NULL) m_secondary.OnAlert(a);
     }
   bool FindInitialSl(const long login, const ulong positionId, double &sl)
     {
      sl = 0.0;
      return m_primary != NULL && m_primary.FindInitialSl(login, positionId, sl);
     }
  };

#endif // SDB_APP_TEESINK_MQH
