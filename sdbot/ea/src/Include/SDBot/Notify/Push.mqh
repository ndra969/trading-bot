//+------------------------------------------------------------------+
//| Push.mqh — ISdbPush: push HP untuk Critical saat Telegram gagal
//| (spec 09 Req 3; design §3.5). Hanya Notify memanggil
//| SendNotification (RULES). Tester memakai CLogPush (Req 2.7).
//+------------------------------------------------------------------+
#ifndef SDB_NOTIFY_PUSH_MQH
#define SDB_NOTIFY_PUSH_MQH

#include <SDBot/Core/Utils.mqh>
#include <SDBot/Notify/TelegramRules.mqh>

#define SDB_PUSH_OK          0
#define SDB_PUSH_DEFERRED    1   // batas kirim terminal: coba lagi nanti
#define SDB_PUSH_FAILED      2
#define SDB_PUSH_NOT_SETUP   3   // MetaQuotes ID / push belum diaktifkan

interface ISdbPush
  {
   int Send(const string text);   // SDB_PUSH_*
  };

class CPushSender : public ISdbPush
  {
private:
   ulong             m_sentMs[];

   void Remember(const ulong now)
     {
      int n = ArraySize(m_sentMs);
      ArrayResize(m_sentMs, n + 1);
      m_sentMs[n] = now;
      while(ArraySize(m_sentMs) > SDB_PUSH_PER_MIN)   // cukup simpan jendela 60 detik terakhir
         ArrayRemove(m_sentMs, 0, 1);
     }

public:
   int Send(const string text)
     {
      ulong now = GetTickCount64();
      if(!PushAllowed(m_sentMs, now))
         return SDB_PUSH_DEFERRED;
      ResetLastError();
      if(SendNotification(text))
        {
         Remember(now);
         return SDB_PUSH_OK;
        }
      int err = GetLastError();
      if(err == ERR_NOTIFICATION_TOO_FREQUENT)
         return SDB_PUSH_DEFERRED;
      if(err == ERR_NOTIFICATION_WRONG_SETTINGS || err == ERR_NOTIFICATION_WRONG_PARAMETER)
         return SDB_PUSH_NOT_SETUP;
      LogWarn("Notify", "push HP gagal | " + ErrText(err));
      return SDB_PUSH_FAILED;
     }
  };

// Strategy Tester: tidak ada SendNotification, teks dicetak ke log.
class CLogPush : public ISdbPush
  {
public:
   int Send(const string text)
     {
      LogInfo("Notify", "push (tester): " + text);
      return SDB_PUSH_OK;
     }
  };

#endif // SDB_NOTIFY_PUSH_MQH
