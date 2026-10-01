//+------------------------------------------------------------------+
//| Transport.mqh — ISdbTransport: penerus pesan notifier yang sudah
//| diformat (spec 08 design §3.5). CLogTransport mencetak ke log Experts
//| atau log tester; Telegram ditambahkan di spec 09.
//+------------------------------------------------------------------+
#ifndef SDB_NOTIFY_TRANSPORT_MQH
#define SDB_NOTIFY_TRANSPORT_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Utils.mqh>

interface ISdbTransport
  {
   SdbSendResult Send(const SdbOutMessage &m);
   string        Name();
  };

// Live sebelum spec 09 dan Strategy Tester (Req 7.1, 7.3): selalu terkirim.
class CLogTransport : public ISdbTransport
  {
public:
   SdbSendResult Send(const SdbOutMessage &m)
     {
      LogInfo("Notify", "[" + m.key + "] " + m.text);
      SdbSendResult r;
      r.code = SDB_SEND_OK;
      r.retryAfterSec = 0;
      r.error = "";
      return r;
     }
   string Name() { return "LOG"; }
  };

#endif // SDB_NOTIFY_TRANSPORT_MQH
