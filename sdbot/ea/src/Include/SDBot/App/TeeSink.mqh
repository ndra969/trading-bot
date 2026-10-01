//+------------------------------------------------------------------+
//| TeeSink.mqh — CTeeSink: meneruskan setiap event ke beberapa sink
//| (Logger, Notifier, perekam harness) tanpa mengubah penulisan ke DB
//| (spec 04 Req 7.6). Alert tanpa key diberi notify_key di sini agar
//| Logger dan Notifier merujuk baris alerts yang sama (spec 08 Req 5.1).
//+------------------------------------------------------------------+
#ifndef SDB_APP_TEESINK_MQH
#define SDB_APP_TEESINK_MQH

#include <SDBot/Core/EventSink.mqh>

#define SDB_TEE_MAX_SINKS 4

class CTeeSink : public ISdbEventSink
  {
private:
   ISdbEventSink    *m_sinks[SDB_TEE_MAX_SINKS];   // sink pertama = Logger: sumber FindInitialSl
   int               m_count;
   string            m_keyPrefix;
   long              m_seq;

public:
                     CTeeSink(void) : m_count(0), m_keyPrefix("0"), m_seq(0) {}

   void Clear() { m_count = 0; }

   bool Add(ISdbEventSink *sink)
     {
      if(sink == NULL || m_count >= SDB_TEE_MAX_SINKS)
         return false;
      m_sinks[m_count++] = sink;
      return true;
     }

   // "<magic>-<waktu init>-<tick>": unik per instance lintas restart (design §3.2).
   void   SetKeyPrefix(const string prefix) { m_keyPrefix = prefix; m_seq = 0; }
   string NextKey()                         { m_seq++; return m_keyPrefix + "-" + IntegerToString(m_seq); }

   void OnAccount(const AccountSnapshot &a)     { for(int i = 0; i < m_count; i++) m_sinks[i].OnAccount(a); }
   void OnTradeOpened(const TradeRecord &t)     { for(int i = 0; i < m_count; i++) m_sinks[i].OnTradeOpened(t); }
   void OnDeal(const DealRecord &d)             { for(int i = 0; i < m_count; i++) m_sinks[i].OnDeal(d); }
   void OnPositionEvent(const PositionEvent &e) { for(int i = 0; i < m_count; i++) m_sinks[i].OnPositionEvent(e); }
   void OnClosure(const ClosureRecord &c)       { for(int i = 0; i < m_count; i++) m_sinks[i].OnClosure(c); }
   void OnBalanceOp(const BalanceOpRecord &b)   { for(int i = 0; i < m_count; i++) m_sinks[i].OnBalanceOp(b); }
   void OnAlertStatus(const AlertStatus &s)     { for(int i = 0; i < m_count; i++) m_sinks[i].OnAlertStatus(s); }

   void OnAlert(const AlertEvent &a)
     {
      AlertEvent k = a;
      if(StringLen(k.key) == 0)   // modul tidak mengisi key: string NULL, bukan "" (NULL != "" di MQL5)
         k.key = NextKey();
      for(int i = 0; i < m_count; i++)
         m_sinks[i].OnAlert(k);
     }

   bool FindInitialSl(const long login, const ulong positionId, double &sl)
     {
      sl = 0.0;
      return m_count > 0 && m_sinks[0].FindInitialSl(login, positionId, sl);
     }
  };

#endif // SDB_APP_TEESINK_MQH
