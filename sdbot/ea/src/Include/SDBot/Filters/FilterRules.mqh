//+------------------------------------------------------------------+
//| FilterRules.mqh — filter sesi trading (UTC) dan spread sebagai
//| fungsi murni (spec 14 Req 1–2; design §3.1; PC-21, PC-22). Batas
//| sesi UTC dari bot Python (utils/market_session.py). Tanpa akses
//| terminal kecuali waktu yang diberikan pemanggil.
//+------------------------------------------------------------------+
#ifndef SDB_FILTERS_FILTERRULES_MQH
#define SDB_FILTERS_FILTERRULES_MQH

#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/Utils.mqh>

enum ENUM_SDB_SESSION
  {
   SDB_SESSION_TOKYO = 0,     // 00:00-08:00 UTC
   SDB_SESSION_LONDON = 1,    // 08:00-13:00
   SDB_SESSION_OVERLAP = 2,   // 13:00-17:00 (London dan New York)
   SDB_SESSION_NEWYORK = 3,   // 17:00-22:00
   SDB_SESSION_OFF = 4        // 22:00-24:00 rollover, bukan sesi mana pun
  };

struct SdbSessionParams
  {
   bool              tokyo;
   bool              london;
   bool              newYork;
   int               endHourUtc;   // spec 25: entry hanya bila jam UTC < nilai ini (22 = tanpa pemotongan)
  };

ENUM_SDB_SESSION SessionOfUtc(const int utcSecOfDay)
  {
   int h = utcSecOfDay / 3600;
   if(h < 8)
      return SDB_SESSION_TOKYO;
   if(h < 13)
      return SDB_SESSION_LONDON;
   if(h < 17)
      return SDB_SESSION_OVERLAP;
   if(h < 22)
      return SDB_SESSION_NEWYORK;
   return SDB_SESSION_OFF;
  }

string SessionText(const ENUM_SDB_SESSION s)
  {
   switch(s)
     {
      case SDB_SESSION_TOKYO:   return "TOKYO";
      case SDB_SESSION_LONDON:  return "LONDON";
      case SDB_SESSION_OVERLAP: return "OVERLAP";
      case SDB_SESSION_NEWYORK: return "NEWYORK";
      default:                  return "OFF";
     }
  }

// Ketiga input false = filter sesi mati (Req 1.3).
bool SessionFilterOn(const SdbSessionParams &p) { return p.tokyo || p.london || p.newYork; }

bool SessionAllowed(const ENUM_SDB_SESSION s, const SdbSessionParams &p)
  {
   if(!SessionFilterOn(p))
      return true;
   switch(s)
     {
      case SDB_SESSION_TOKYO:   return p.tokyo;
      case SDB_SESSION_LONDON:  return p.london;
      case SDB_SESSION_OVERLAP: return p.london || p.newYork;
      case SDB_SESSION_NEWYORK: return p.newYork;
      default:                  return false;
     }
  }

// Spec 25: aturan sesi ditambah jam akhir entry. Filter mati = semua jam diizinkan (Req 1.4).
bool SessionAllowedAt(const int utcSecOfDay, const SdbSessionParams &p)
  {
   if(!SessionAllowed(SessionOfUtc(utcSecOfDay), p))
      return false;
   return !SessionFilterOn(p) || utcSecOfDay < p.endHourUtc * 3600;
  }

// Detik sejak 00:00 UTC dari waktu server dan selisih server-UTC (Req 1.4).
int UtcSecOfDay(const datetime serverTime, const int offsetSec)
  {
   long t = (long)serverTime - offsetSec;
   return (int)(((t % 86400) + 86400) % 86400);
  }

// Tester: TimeGMT() sama dengan waktu server, jadi selisih dari input (Req 4.2). Live: dibulatkan 15 menit.
int ServerUtcOffsetSec(const bool tester, const int testerHours, const datetime serverNow, const datetime gmtNow)
  {
   if(tester)
      return testerHours * 3600;
   return RoundUtcOffset((long)serverNow - (long)gmtNow);
  }

// Batas 0 = filter mati; spread sama dengan batas lolos (Req 2.1–2.3).
bool SpreadAllowed(const long spreadPoints, const int maxSpreadPoints)
  {
   return maxSpreadPoints <= 0 || spreadPoints <= maxSpreadPoints;
  }

#endif // SDB_FILTERS_FILTERRULES_MQH
