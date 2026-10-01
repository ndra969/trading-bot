//+------------------------------------------------------------------+
//| NotifyRules.mqh — aturan kirim notifier sebagai fungsi murni: lingkup,
//| cooldown, kuota per jam, pesan basi, urutan antrean, langkah setelah
//| hasil kirim (spec 08 Req 2, 3; design §3.3). Waktu selalu parameter,
//| jadi cooldown dan kuota bisa diuji tanpa menunggu.
//+------------------------------------------------------------------+
#ifndef SDB_NOTIFY_NOTIFYRULES_MQH
#define SDB_NOTIFY_NOTIFYRULES_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/SchemaEnums.mqh>

// Tipe tentang akun dibagi semua instance: satu pesan per akun per cooldown (PC-13).
ENUM_SDB_NT_SCOPE NtScopeOf(const string type)
  {
   if(type == SDB_ALERT_TYPE_CONN_DOWN || type == SDB_ALERT_TYPE_CONN_UP || type == SDB_ALERT_TYPE_DAILY_LOSS ||
      type == SDB_ALERT_TYPE_MARGIN_LOW || type == SDB_ALERT_TYPE_MARGIN_OK || type == SDB_ALERT_TYPE_BALANCE_OP ||
      type == SDB_ALERT_TYPE_STATE_RESET || type == SDB_ALERT_TYPE_EMERGENCY_RESET || StringFind(type, "DD_") == 0)
      return SDB_NT_SCOPE_ACCOUNT;
   return SDB_NT_SCOPE_INSTANCE;
  }

// Event trade dikirim setiap kali (PRD "setiap event").
bool NtIsTradeType(const string type)
  {
   return type == SDB_ALERT_TYPE_TRADE_OPENED || type == SDB_ALERT_TYPE_TRADE_CLOSED ||
          type == SDB_ALERT_TYPE_BE_MOVED || type == SDB_ALERT_TYPE_PARTIAL_CLOSED;
  }

// Critical langsung; High sudah dikirim modul hanya saat status berubah (Req 2.2).
int NtCooldownSec(const ENUM_SDB_SEVERITY sev, const string type)
  {
   if(sev == SDB_SEV_CRITICAL || sev == SDB_SEV_HIGH || NtIsTradeType(type))
      return 0;
   return SDB_NT_COOLDOWN_SEC;
  }

bool NtCooldownOk(const long lastAt, const long now, const int cooldownSec)
  {
   return lastAt <= 0 || cooldownSec <= 0 || now - lastAt >= cooldownSec;
  }

long NtQuotaHour(const long now) { return now / 3600; }

// GV kuota = jam x 1000 + jumlah, satu nilai agar cukup satu compare-and-set (design §4.5).
bool NtQuotaTake(const double gvValue, const long now, const int limit, double &newValue)
  {
   long hour = NtQuotaHour(now);
   long stored = (long)MathRound(gvValue);
   long storedHour = stored / SDB_NT_QUOTA_HOUR_FACTOR;
   long count = (storedHour == hour) ? stored % SDB_NT_QUOTA_HOUR_FACTOR : 0;
   if(count >= limit)
     {
      newValue = gvValue;
      return false;
     }
   newValue = (double)(hour * SDB_NT_QUOTA_HOUR_FACTOR + count + 1);
   return true;
  }

bool NtIsStale(const ENUM_SDB_SEVERITY sev, const long queuedAt, const long now)
  {
   return sev != SDB_SEV_CRITICAL && now - queuedAt > SDB_NT_STALE_SEC;
  }

// Critical siap pertama, lalu non-Critical siap pertama (antrean berurutan masuk).
int NtPickNext(const SdbNtItem &q[], const long now)
  {
   int n = ArraySize(q);
   for(int pass = 0; pass < 2; pass++)
      for(int i = 0; i < n; i++)
        {
         bool critical = (q[i].msg.severity == SDB_SEV_CRITICAL);
         if(critical != (pass == 0) || q[i].notBefore > now)
            continue;
         return i;
        }
   return -1;
  }

int NtOverflowVictim(const SdbNtItem &q[])
  {
   int victim = -1;
   for(int i = 0; i < ArraySize(q); i++)
      if(q[i].msg.severity != SDB_SEV_CRITICAL && (victim < 0 || q[i].queuedAt < q[victim].queuedAt))
         victim = i;
   return victim;
  }

// attempts = jumlah percobaan yang sudah dilakukan termasuk yang baru saja.
ENUM_SDB_NT_NEXT NtAfterResult(const SdbSendResult &r, const int attempts)
  {
   switch(r.code)
     {
      case SDB_SEND_OK:      return SDB_NT_DONE_SENT;
      case SDB_SEND_LIMITED: return SDB_NT_WAIT;
      case SDB_SEND_TEMP:    return (attempts >= SDB_NT_MAX_ATTEMPTS) ? SDB_NT_DONE_FAILED : SDB_NT_RETRY;
      default:               return SDB_NT_DONE_FAILED;
     }
  }

#endif // SDB_NOTIFY_NOTIFYRULES_MQH
