//+------------------------------------------------------------------+
//| TelegramRules.mqh — fungsi murni untuk Telegram Bot API dan push HP:
//| body JSON sendMessage, URL dan samaran token, klasifikasi respons,
//| retry_after, teks polos, teks push, batas kirim push (spec 09 Req 1.3,
//| 2, 3; design §3.1, §4.3). Tidak memanggil WebRequest.
//+------------------------------------------------------------------+
#ifndef SDB_NOTIFY_TELEGRAMRULES_MQH
#define SDB_NOTIFY_TELEGRAMRULES_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>

#define SDB_TG_API_BASE "https://api.telegram.org/bot"

string TgJsonEscape(const string s)
  {
   string r = "";
   int n = StringLen(s);
   for(int i = 0; i < n; i++)
     {
      ushort c = StringGetCharacter(s, i);
      if(c == '"')
         r += "\\\"";
      else if(c == '\\')
         r += "\\\\";
      else if(c == '\n')
         r += "\\n";
      else if(c == '\r')
         r += "\\r";
      else if(c == '\t')
         r += "\\t";
      else if(c < 0x20)
         r += StringFormat("\\u%04x", c);
      else
         r += ShortToString(c);
     }
   return r;
  }

// html = false: teks polos tanpa parse_mode (kirim ulang setelah HTML ditolak, Req 2.4).
string TgBody(const string chatId, const string text, const bool silent, const bool html)
  {
   return "{\"chat_id\":\"" + TgJsonEscape(chatId) + "\",\"text\":\"" + TgJsonEscape(text) +
          "\",\"disable_notification\":" + (silent ? "true" : "false") + (html ? ",\"parse_mode\":\"HTML\"" : "") + "}";
  }

string TgUrl(const string token) { return SDB_TG_API_BASE + token + "/sendMessage"; }

// Token tidak pernah masuk log (Req 1.3).
string TgMask(const string s, const string token)
  {
   if(token == "")
      return s;
   string r = s;
   StringReplace(r, token, "***");
   return r;
  }

int TgRetryAfter(const string body)
  {
   string key = "\"retry_after\":";
   int p = StringFind(body, key);
   if(p < 0)
      return 0;
   return (int)StringToInteger(StringSubstr(body, p + StringLen(key), 10));
  }

bool TgIsParseError(const string body) { return StringFind(body, "can't parse entities") >= 0; }

// Error WebRequest (http -1) dan kode HTTP Telegram -> hasil (design §4.3).
ENUM_SDB_TG_OUTCOME TgClassify(const int http, const int wrError, const string body)
  {
   if(http < 0)
     {
      if(wrError == ERR_FUNCTION_NOT_ALLOWED || wrError == ERR_WEBREQUEST_INVALID_ADDRESS)
         return SDB_TG_CONFIG;
      return SDB_TG_TEMP;
     }
   if(http == 200)
      return StringFind(body, "\"ok\":true") >= 0 ? SDB_TG_OK : SDB_TG_TEMP;
   if(http == 429)
      return SDB_TG_LIMITED;
   if(http == 400)
     {
      if(TgIsParseError(body))
         return SDB_TG_PARSE_ERROR;
      return StringFind(body, "chat not found") >= 0 ? SDB_TG_CONFIG : SDB_TG_PERMANENT;
     }
   if(http == 401 || http == 403 || http == 404)
      return SDB_TG_CONFIG;
   return SDB_TG_TEMP;
  }

// Teks polos dari HTML Telegram: tag dibuang, entitas dikembalikan (&amp; terakhir).
string NtPlainText(const string html)
  {
   string r = "";
   int n = StringLen(html);
   for(int i = 0; i < n; i++)
     {
      ushort c = StringGetCharacter(html, i);
      if(c == '<')
        {
         int end = StringFind(html, ">", i);
         if(end > 0)
           {
            i = end;
            continue;
           }
        }
      r += ShortToString(c);
     }
   StringReplace(r, "&lt;", "<");
   StringReplace(r, "&gt;", ">");
   StringReplace(r, "&amp;", "&");
   return r;
  }

// Push HP: satu baris, maksimal maxLen karakter dengan elipsis (Req 3.1).
string NtPushText(const string plain, const int maxLen)
  {
   string r = plain;
   StringReplace(r, "\r", "");
   StringReplace(r, "\n", " ");
   StringTrimRight(r);
   if(StringLen(r) <= maxLen)
      return r;
   ushort ell[] = {0x2026};
   return StringSubstr(r, 0, maxLen - 1) + ShortArrayToString(ell);
  }

// Batas terminal untuk SendNotification: < 2 dalam 1 detik dan < 10 dalam 60 detik (Req 3.4).
bool PushAllowed(const ulong &sentMs[], const ulong nowMs)
  {
   int lastSec = 0, lastMin = 0;
   for(int i = 0; i < ArraySize(sentMs); i++)
     {
      if(nowMs - sentMs[i] < 1000)
         lastSec++;
      if(nowMs - sentMs[i] < 60000)
         lastMin++;
     }
   return lastSec < SDB_PUSH_PER_SEC && lastMin < SDB_PUSH_PER_MIN;
  }

#endif // SDB_NOTIFY_TELEGRAMRULES_MQH
