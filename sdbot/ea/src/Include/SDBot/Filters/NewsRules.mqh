//+------------------------------------------------------------------+
//| NewsRules.mqh — filter berita sebagai fungsi murni (spec 16 Req
//| 1–2, 4–5; design §3.1; PC-24): model event kalender, baris CSV,
//| relevansi mata uang simbol, jendela blackout per dampak, pilihan
//| event saat tumpang tindih, event terdekat. Hanya jadwal event yang
//| dipakai, tidak pernah nilai actual (tanpa lookahead).
//+------------------------------------------------------------------+
#ifndef SDB_FILTERS_NEWSRULES_MQH
#define SDB_FILTERS_NEWSRULES_MQH

#define SDB_NEWS_LOW    0
#define SDB_NEWS_MEDIUM 1
#define SDB_NEWS_HIGH   2

struct SdbNewsEvent
  {
   datetime          time;            // waktu server
   string            ccy;
   int               impact;          // SDB_NEWS_*
   long              id;
   string            name;
  };

struct SdbNewsParams
  {
   bool              enabled;
   int               highMinutes;
   int               mediumMinutes;
  };

int ImpactFromText(const string s)
  {
   if(s == "HIGH")
      return SDB_NEWS_HIGH;
   if(s == "MEDIUM")
      return SDB_NEWS_MEDIUM;
   return SDB_NEWS_LOW;
  }

string ImpactText(const int i)
  {
   return i == SDB_NEWS_HIGH ? "HIGH" : (i == SDB_NEWS_MEDIUM ? "MEDIUM" : "LOW");
  }

bool NwIsDigits(const string s)
  {
   if(StringLen(s) == 0)
      return false;
   for(int i = 0; i < StringLen(s); i++)
     {
      ushort c = StringGetCharacter(s, i);
      if(c < '0' || c > '9')
         return false;
     }
   return true;
  }

// "epoch,ccy,impact,id,nama": hanya 4 koma pertama yang memisah, nama boleh berkoma (Req 2.2, EC-07).
bool ParseCalendarLine(const string line, SdbNewsEvent &e)
  {
   string s = line;
   StringTrimRight(s);
   StringTrimLeft(s);
   int p[4];
   int from = 0;
   for(int k = 0; k < 4; k++)
     {
      p[k] = StringFind(s, ",", from);
      if(p[k] < 0)
         return false;
      from = p[k] + 1;
     }
   string epoch = StringSubstr(s, 0, p[0]);
   string ccy = StringSubstr(s, p[0] + 1, p[1] - p[0] - 1);
   string imp = StringSubstr(s, p[1] + 1, p[2] - p[1] - 1);
   string id = StringSubstr(s, p[2] + 1, p[3] - p[2] - 1);
   if(!NwIsDigits(epoch) || StringToInteger(epoch) <= 0 || StringLen(ccy) != 3 || !NwIsDigits(id))
      return false;
   e.time = (datetime)StringToInteger(epoch);
   e.ccy = ccy;
   e.impact = ImpactFromText(imp);
   e.id = StringToInteger(id);
   e.name = StringSubstr(s, p[3] + 1);
   return true;
  }

// Kebalikan ParseCalendarLine; nama tanpa koma dan baris baru (Req 5.1).
string CalendarLine(const SdbNewsEvent &e)
  {
   string name = e.name;
   StringReplace(name, ",", " ");
   StringReplace(name, "\r", " ");
   StringReplace(name, "\n", " ");
   return StringFormat("%I64d,%s,%s,%I64d,%s", (long)e.time, e.ccy, ImpactText(e.impact), e.id, name);
  }

// Event untuk mata uang dasar atau kuotasi simbol; XAU/XAG/BTC tidak punya event, jadi hanya kaki USD (Req 1.1, EC-03).
bool EventForSymbol(const SdbNewsEvent &e, const string base, const string quote) { return e.ccy == base || e.ccy == quote; }

int WindowMinutes(const int impact, const SdbNewsParams &p)
  {
   if(impact == SDB_NEWS_HIGH)
      return p.highMinutes;
   if(impact == SDB_NEWS_MEDIUM)
      return p.mediumMinutes;
   return 0;
  }

// Negatif = bar sebelum rilis; dibulatkan menuju nol.
int MinutesToEvent(const datetime bar, const datetime ev) { return (int)(((long)bar - (long)ev) / 60); }

// Event relevan yang jendelanya (inklusif) mencakup bar: dampak tertinggi, lalu terdekat (Req 1.1–1.3).
int FindBlackout(const SdbNewsEvent &ev[], const datetime bar, const string base, const string quote, const SdbNewsParams &p)
  {
   if(!p.enabled)
      return -1;
   int best = -1;
   long bestDist = 0;
   for(int i = 0; i < ArraySize(ev); i++)
     {
      int w = WindowMinutes(ev[i].impact, p);
      if(w <= 0 || !EventForSymbol(ev[i], base, quote))
         continue;
      long dist = MathAbs((long)bar - (long)ev[i].time);
      if(dist > (long)w * 60)
         continue;
      if(best < 0 || ev[i].impact > ev[best].impact || (ev[i].impact == ev[best].impact && dist < bestDist))
        {
         best = i;
         bestDist = dist;
        }
     }
   return best;
  }

// Event relevan berdampak >= medium yang belum lewat, paling dekat dalam horizonSec (Req 4.1).
int NearestUpcoming(const SdbNewsEvent &ev[], const datetime bar, const string base, const string quote, const int horizonSec)
  {
   int best = -1;
   for(int i = 0; i < ArraySize(ev); i++)
     {
      if(ev[i].impact < SDB_NEWS_MEDIUM || !EventForSymbol(ev[i], base, quote))
         continue;
      if(ev[i].time < bar || (long)ev[i].time > (long)bar + horizonSec)
         continue;
      if(best < 0 || ev[i].time < ev[best].time)
         best = i;
     }
   return best;
  }

string BlackoutDetail(const SdbNewsEvent &e, const datetime bar)
  {
   return StringFormat("%s %s %s %dm", e.name, e.ccy, ImpactText(e.impact), MinutesToEvent(bar, e.time));
  }

#endif // SDB_FILTERS_NEWSRULES_MQH
