//+------------------------------------------------------------------+
//| Utils.mqh — log terminal SDBot (format RULES, level, throttle) dan
//| fungsi util murni. Modul menulis log hanya lewat fungsi di sini.
//| Log terminal tidak menulis DB; baris SQLite adalah event lewat sink.
//+------------------------------------------------------------------+
#ifndef SDB_CORE_UTILS_MQH
#define SDB_CORE_UTILS_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>

//--- Throttle: pesan berkunci sama dicetak paling sering sekali per interval.
class CLogThrottle
  {
private:
   string            m_keys[SDB_LOG_THROTTLE_SLOTS];
   datetime          m_last[SDB_LOG_THROTTLE_SLOTS];
   int               m_suppressed[SDB_LOG_THROTTLE_SLOTS];
   int               m_used;

   int FindSlot(const string key) const
     {
      for(int i = 0; i < m_used; i++)
         if(m_keys[i] == key)
            return i;
      return -1;
     }

   // Tabel penuh: pakai slot yang paling lama tidak mencetak (LRU), agar tabel tidak tumbuh.
   int FreeSlot()
     {
      if(m_used < SDB_LOG_THROTTLE_SLOTS)
         return m_used++;
      int oldest = 0;
      for(int i = 1; i < m_used; i++)
         if(m_last[i] < m_last[oldest])
            oldest = i;
      return oldest;
     }

public:
                     CLogThrottle(void) : m_used(0) {}

   // true = boleh cetak sekarang; suppressed = jumlah pesan yang ditahan sejak cetakan terakhir.
   bool Allow(const string key, const datetime now, const int intervalSec, int &suppressed)
     {
      suppressed = 0;
      int i = FindSlot(key);
      if(i < 0)
        {
         i = FreeSlot();
         m_keys[i] = key;
         m_last[i] = now;
         m_suppressed[i] = 0;
         return true;
        }
      if(now - m_last[i] < intervalSec)
        {
         m_suppressed[i]++;
         return false;
        }
      suppressed = m_suppressed[i];
      m_suppressed[i] = 0;
      m_last[i] = now;
      return true;
     }
  };

//--- State modul log (internal Utils, bukan komunikasi antar-modul).
ENUM_SDB_LOG_LEVEL g_sdbLogLevel = SDB_LOG_INFO;
bool               g_sdbLogCapture = false;
string             g_sdbLogCaptured[];
CLogThrottle       g_sdbLogThrottle;

void SdbSetLogLevel(const ENUM_SDB_LOG_LEVEL level) { g_sdbLogLevel = level; }

string LevelName(const ENUM_SDB_LOG_LEVEL level)
  {
   switch(level)
     {
      case SDB_LOG_DEBUG:    return "DEBUG";
      case SDB_LOG_INFO:     return "INFO";
      case SDB_LOG_WARN:     return "WARN";
      case SDB_LOG_ERROR:    return "ERROR";
      case SDB_LOG_CRITICAL: return "CRITICAL";
     }
   return "INFO";
  }

string FormatLogLine(const ENUM_SDB_LOG_LEVEL level, const string module, const string symbol, const string msg)
  {
   return "[SDB][" + LevelName(level) + "][" + module + "][" + symbol + "] " + msg;
  }

string FormatSuppressed(const string msg, const int suppressed)
  {
   if(suppressed <= 0)
      return msg;
   return msg + " (+" + IntegerToString(suppressed) + " ditahan)";
  }

//--- Hook uji: tangkap baris log alih-alih mencetaknya.
void   SdbLogCaptureStart()           { ArrayFree(g_sdbLogCaptured); g_sdbLogCapture = true; }
void   SdbLogCaptureStop()            { g_sdbLogCapture = false; }
int    SdbLogCapturedCount()          { return ArraySize(g_sdbLogCaptured); }
string SdbLogCaptured(const int i)    { return (i >= 0 && i < ArraySize(g_sdbLogCaptured)) ? g_sdbLogCaptured[i] : ""; }

void SdbLog(const ENUM_SDB_LOG_LEVEL level, const string module, const string msg)
  {
   if(level < g_sdbLogLevel)
      return;
   string line = FormatLogLine(level, module, _Symbol, msg);
   if(g_sdbLogCapture)
     {
      int n = ArraySize(g_sdbLogCaptured);
      ArrayResize(g_sdbLogCaptured, n + 1);
      g_sdbLogCaptured[n] = line;
      return;
     }
   Print(line);
  }

void LogDebug(const string module, const string msg)    { SdbLog(SDB_LOG_DEBUG, module, msg); }
void LogInfo(const string module, const string msg)     { SdbLog(SDB_LOG_INFO, module, msg); }
void LogWarn(const string module, const string msg)     { SdbLog(SDB_LOG_WARN, module, msg); }
void LogError(const string module, const string msg)    { SdbLog(SDB_LOG_ERROR, module, msg); }
void LogCritical(const string module, const string msg) { SdbLog(SDB_LOG_CRITICAL, module, msg); }

// Untuk pesan yang bisa berulang tiap tick/detik (misalnya "trading tidak diizinkan").
void LogThrottled(const ENUM_SDB_LOG_LEVEL level, const string key, const int intervalSec,
                  const string module, const string msg)
  {
   if(level < g_sdbLogLevel)
      return;
   int suppressed = 0;
   if(g_sdbLogThrottle.Allow(key, TimeLocal(), intervalSec, suppressed))
      SdbLog(level, module, FormatSuppressed(msg, suppressed));
  }

//--- Util murni.
double NormalizePriceTo(const double price, const int digits)
  {
   return NormalizeDouble(price, digits);
  }

// Tabel timeframe PRD: HTF bias, MTF zona & struktur, LTF trigger.
void StyleTimeframes(const ENUM_SDB_TRADING_STYLE style, ENUM_TIMEFRAMES &htf, ENUM_TIMEFRAMES &mtf, ENUM_TIMEFRAMES &ltf)
  {
   switch(style)
     {
      case SDB_STYLE_SCALPING: htf = PERIOD_M15; mtf = PERIOD_M5;  ltf = PERIOD_M1;  return;
      case SDB_STYLE_SWING:    htf = PERIOD_W1;  mtf = PERIOD_D1;  ltf = PERIOD_H4;  return;
      case SDB_STYLE_POSITION: htf = PERIOD_MN1; mtf = PERIOD_W1;  ltf = PERIOD_D1;  return;
      default:                 htf = PERIOD_H4;  mtf = PERIOD_H1;  ltf = PERIOD_M15; return;
     }
  }

string ErrText(const int code)
  {
   return "err=" + IntegerToString(code);
  }

#endif // SDB_CORE_UTILS_MQH
