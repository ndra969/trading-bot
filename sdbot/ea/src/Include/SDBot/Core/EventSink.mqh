//+------------------------------------------------------------------+
//| EventSink.mqh — pintu pencatatan event. Modul mengirim event ke
//| interface ini dan tidak pernah memanggil Storage langsung (RULES:
//| hanya Storage yang menulis DB). CLogger (spec 03) dan CNotifier (spec 08)
//| mengimplementasikannya.
//+------------------------------------------------------------------+
#ifndef SDB_CORE_EVENTSINK_MQH
#define SDB_CORE_EVENTSINK_MQH

#include <SDBot/Core/Types.mqh>

interface ISdbEventSink
  {
   void OnAccount(const AccountSnapshot &a);
   void OnTradeOpened(const TradeRecord &t);
   void OnDeal(const DealRecord &d);
   void OnPositionEvent(const PositionEvent &e);
   void OnClosure(const ClosureRecord &c);
   void OnBalanceOp(const BalanceOpRecord &b);
   void OnAlert(const AlertEvent &a);
   void OnAlertStatus(const AlertStatus &s);   // hasil kirim notifikasi (spec 08)
   bool FindInitialSl(const long login, const ulong positionId, double &sl);
  };

// Dipakai saat storage tidak tersedia (optimasi, DB gagal dibuka) atau sink belum diset.
class CNullSink : public ISdbEventSink
  {
public:
   void OnAccount(const AccountSnapshot &a)     { }
   void OnTradeOpened(const TradeRecord &t)     { }
   void OnDeal(const DealRecord &d)             { }
   void OnPositionEvent(const PositionEvent &e) { }
   void OnClosure(const ClosureRecord &c)       { }
   void OnBalanceOp(const BalanceOpRecord &b)   { }
   void OnAlert(const AlertEvent &a)            { }
   void OnAlertStatus(const AlertStatus &s)     { }
   bool FindInitialSl(const long login, const ulong positionId, double &sl) { sl = 0.0; return false; }
  };

#endif // SDB_CORE_EVENTSINK_MQH
