//+------------------------------------------------------------------+
//| TelegramTransport.mqh — CTelegramTransport: kirim notifikasi ke
//| sendMessage Telegram Bot API lewat WebRequest (spec 09 Req 1.3, 2;
//| design §3.4). Jarak kirim 1 detik dan jeda 429 dibagi semua instance
//| lewat GV NT_TG_NEXT (ms GetTickCount64, satu jam untuk semua EA di
//| terminal). Error konfigurasi menonaktifkan transport sampai init
//| ulang. Token tidak pernah ditulis ke log. Tidak dipakai di tester.
//+------------------------------------------------------------------+
#ifndef SDB_NOTIFY_TELEGRAMTRANSPORT_MQH
#define SDB_NOTIFY_TELEGRAMTRANSPORT_MQH

#include <SDBot/Core/State.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Core/SchemaEnums.mqh>
#include <SDBot/Notify/Transport.mqh>
#include <SDBot/Notify/TelegramRules.mqh>

#define SDB_TG_RESPONSE_LOG_LEN 160   // potongan respons di log/alasan

class CTelegramTransport : public ISdbTransport
  {
private:
   string            m_token;
   string            m_chatId;
   CState           *m_state;
   bool              m_disabled;
   string            m_disabledReason;
   ulong             m_nextLocal;      // jarak kirim bila GV belum siap (akun PENDING)
   int               m_webCalls;
   int               m_lastError;

   SdbSendResult Result(const ENUM_SDB_SEND_CODE code, const int retryAfter, const string error, const bool disable, const string note)
     {
      SdbSendResult r;
      r.code = code;
      r.retryAfterSec = retryAfter;
      r.error = TgMask(error, m_token);
      r.disable = disable;
      r.note = note;
      return r;
     }

   SdbSendResult Off(const bool justDisabled)
     {
      return Result(SDB_SEND_PERMANENT, 0, m_disabledReason, justDisabled, SDB_ALERT_STATUS_REASON_TELEGRAM_OFF);
     }

   bool GapReady() const { return m_state != NULL && m_state.IsReady(); }

   // Klaim slot kirim: 0 = boleh sekarang, > 0 = tunggu sekian detik (Req 2.5).
   int ClaimSlot()
     {
      ulong now = GetTickCount64();
      if(!GapReady())
        {
         if(now < m_nextLocal)
            return (int)((m_nextLocal - now + 999) / 1000);
         m_nextLocal = now + SDB_TG_MIN_GAP_MS;
         return 0;
        }
      string key = m_state.Key(SDB_GV_NT_TG_NEXT);
      if(!GlobalVariableCheck(key))
         m_state.Set(SDB_GV_NT_TG_NEXT, 0.0, false);
      double next = m_state.Get(SDB_GV_NT_TG_NEXT, 0.0);
      if((double)now < next)
         return (int)(((ulong)next - now + 999) / 1000);
      return GlobalVariableSetOnCondition(key, (double)(now + SDB_TG_MIN_GAP_MS), next) ? 0 : 1;
     }

   // 429: jeda berlaku untuk semua instance.
   void PushBackAll(const int seconds)
     {
      ulong until = GetTickCount64() + (ulong)seconds * 1000;
      if(GapReady())
         m_state.Set(SDB_GV_NT_TG_NEXT, (double)until, false);
      m_nextLocal = until;
     }

   int Post(const string body, string &response)
     {
      char data[], result[];
      string headers;
      int n = StringToCharArray(body, data, 0, WHOLE_ARRAY, CP_UTF8);
      ArrayResize(data, MathMax(n - 1, 0));   // tanpa terminator nol
      m_webCalls++;
      ResetLastError();
      int code = WebRequest("POST", TgUrl(m_token), "Content-Type: application/json\r\n", SDB_TG_TIMEOUT_MS, data, result, headers);
      m_lastError = (code < 0) ? GetLastError() : 0;
      response = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
      return code;
     }

   string Describe(const int http, const string response) const
     {
      if(http < 0)
         return StringFormat("WebRequest error %d", m_lastError) +
                (m_lastError == ERR_FUNCTION_NOT_ALLOWED ? " (URL https://api.telegram.org belum diizinkan)" : "");
      return StringFormat("HTTP %d %s", http, StringSubstr(response, 0, SDB_TG_RESPONSE_LOG_LEN));
     }

   SdbSendResult Map(const ENUM_SDB_TG_OUTCOME outcome, const int http, const string response, const string note)
     {
      string why = Describe(http, response);
      switch(outcome)
        {
         case SDB_TG_OK:
            return Result(SDB_SEND_OK, 0, "", false, note);
         case SDB_TG_LIMITED:
           {
            int wait = MathMax(TgRetryAfter(response), 1);
            PushBackAll(wait);
            return Result(SDB_SEND_LIMITED, wait, why, false, "");
           }
         case SDB_TG_CONFIG:
            Disable(why);
            return Off(true);
         case SDB_TG_PERMANENT:
         case SDB_TG_PARSE_ERROR:
            return Result(SDB_SEND_PERMANENT, 0, why, false, "");
         default:
            return Result(SDB_SEND_TEMP, SDB_TG_TEMP_BACKOFF_SEC, why, false, "");
        }
     }

public:
                     CTelegramTransport(void) : m_state(NULL), m_disabled(false), m_nextLocal(0), m_webCalls(0), m_lastError(0) {}

   void Init(const string token, const string chatId, CState *state)
     {
      m_token = token;
      m_chatId = chatId;
      m_state = state;
      m_disabled = false;
      m_disabledReason = "";
      m_nextLocal = 0;
     }

   void   SetState(CState *state)       { m_state = state; }
   void   Disable(const string reason)  { m_disabled = true; m_disabledReason = TgMask(reason, m_token); }
   bool   IsDisabled() const            { return m_disabled; }
   string DisabledReason() const        { return m_disabledReason; }
   int    WebRequestCount() const       { return m_webCalls; }
   string Name()                        { return "TELEGRAM"; }

   SdbSendResult Send(const SdbOutMessage &m)
     {
      if(m_disabled)
         return Off(false);
      if(m_token == "" || m_chatId == "")
        {
         Disable("InpTelegramToken / InpTelegramChatID kosong");
         return Off(true);
        }
      int wait = ClaimSlot();
      if(wait > 0)
         return Result(SDB_SEND_LIMITED, wait, "jarak kirim Telegram", false, "");
      if(MQLInfoInteger(MQL_TESTER))
        {
         Disable("Strategy Tester tidak mengizinkan WebRequest");   // Req 2.7: penjaga terakhir sebelum jaringan
         return Off(true);
        }
      string response;
      int http = Post(TgBody(m_chatId, m.text, m.silent, true), response);
      ENUM_SDB_TG_OUTCOME outcome = TgClassify(http, m_lastError, response);
      if(outcome != SDB_TG_PARSE_ERROR)
         return Map(outcome, http, response, "");
      // HTML ditolak parser Telegram: kirim ulang sekali sebagai teks polos (Req 2.4).
      LogError("Notify", "HTML ditolak Telegram, dikirim ulang sebagai teks polos | type=" + m.type + " " + TgMask(Describe(http, response), m_token));
      http = Post(TgBody(m_chatId, NtPlainText(m.text), m.silent, false), response);
      return Map(TgClassify(http, m_lastError, response), http, response, SDB_ALERT_STATUS_REASON_PLAIN_TEXT);
     }
  };

#endif // SDB_NOTIFY_TELEGRAMTRANSPORT_MQH
