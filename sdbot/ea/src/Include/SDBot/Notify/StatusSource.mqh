//+------------------------------------------------------------------+
//| StatusSource.mqh — ISdbStatusSource: data akun dan risiko untuk
//| heartbeat, disediakan App (spec 09 design §3.6, §3.8). Notify tidak
//| meng-include Risk; arti status risiko tetap dari satu sumber.
//+------------------------------------------------------------------+
#ifndef SDB_NOTIFY_STATUSSOURCE_MQH
#define SDB_NOTIFY_STATUSSOURCE_MQH

#include <SDBot/Core/Types.mqh>

interface ISdbStatusSource
  {
   bool HeartbeatData(SdbHeartbeat &h);   // false = data belum siap (heartbeat ditunda)
  };

#endif // SDB_NOTIFY_STATUSSOURCE_MQH
