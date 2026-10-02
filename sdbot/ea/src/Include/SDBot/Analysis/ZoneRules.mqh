//+------------------------------------------------------------------+
//| ZoneRules.mqh — zona Supply & Demand sebagai fungsi murni di atas
//| array MqlRates MTF urut waktu naik (spec 11 Req 1–4; design §3.1):
//| ATR Wilder, calon zona dari candle swing (lebar dan gerak keluar
//| relatif ATR, bar aktif), status, peta, pemilihan zona, skor.
//+------------------------------------------------------------------+
#ifndef SDB_ANALYSIS_ZONERULES_MQH
#define SDB_ANALYSIS_ZONERULES_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>
#include <SDBot/Analysis/StructureRules.mqh>

#define SDB_ZONE_EPS 1e-9   // batas inklusif input (0.30 dan 2.0 diterima) walau ada galat floating point

// TR Wilder; benih rata-rata TR `period` bar pertama di indeks period-1 (indeks sebelumnya 0).
bool AtrSeries(const MqlRates &r[], const int period, double &atr[])
  {
   int n = ArraySize(r);
   ArrayResize(atr, n);
   ArrayInitialize(atr, 0.0);
   if(period < 1 || n < SDB_EMA_WARMUP_MULT * period)
      return false;
   double sum = 0.0;
   for(int i = 0; i < n; i++)
     {
      double tr = r[i].high - r[i].low;
      if(i > 0)
         tr = MathMax(tr, MathMax(MathAbs(r[i].high - r[i - 1].close), MathAbs(r[i].low - r[i - 1].close)));
      if(i < period)
        {
         sum += tr;
         if(i == period - 1)
            atr[i] = sum / period;
         continue;
        }
      atr[i] = (atr[i - 1] * (period - 1) + tr) / period;
     }
   return true;
  }

string ZoneTfText(const ENUM_TIMEFRAMES tf)
  {
   string s = EnumToString(tf);   // PERIOD_H1
   StringReplace(s, "PERIOD_", "");
   return s;
  }

string ZoneId(const ENUM_TIMEFRAMES tf, const datetime swingTime, const bool demand)
  {
   return ZoneTfText(tf) + "-" + IntegerToString((long)swingTime) + (demand ? "-D" : "-S");
  }

// Gerak keluar di bar j (× ATR): close menjauh dari batas dekat ke arah impuls.
double ZoneMove(const MqlRates &r[], const int j, const bool demand, const double proximal, const double atr)
  {
   return (demand ? r[j].close - proximal : proximal - r[j].close) / atr;
  }

// Calon zona dari candle swing (Req 1.1–1.4). Bar aktif = max(konfirmasi swing, bar gerak keluar tercapai).
bool ZoneCandidate(const MqlRates &r[], const double &atr[], const SdbSwing &sw, const SdbZoneParams &p, SdbZone &z)
  {
   ZeroMemory(z);
   int s = sw.index;
   int last = ArraySize(r) - 1;
   if(s < 0 || s > last || s >= ArraySize(atr) || atr[s] <= 0.0)
      return false;
   z.demand = !sw.isHigh;
   z.swingIdx = s;
   z.swingTime = r[s].time;
   z.atr = atr[s];
   z.distal = z.demand ? r[s].low : r[s].high;
   z.proximal = z.demand ? MathMax(r[s].open, r[s].close) : MathMin(r[s].open, r[s].close);
   z.widthAtr = MathAbs(z.proximal - z.distal) / z.atr;
   if(z.widthAtr < p.minWidthAtr - SDB_ZONE_EPS || z.widthAtr > p.maxWidthAtr + SDB_ZONE_EPS)
      return false;
   int reach = -1;
   for(int j = s + 1; j <= MathMin(s + p.legBars, last) && reach < 0; j++)
      if(ZoneMove(r, j, z.demand, z.proximal, z.atr) >= p.minLegAtr - SDB_ZONE_EPS)
         reach = j;
   if(reach < 0)
      return false;
   z.legAtr = ZoneMove(r, reach, z.demand, z.proximal, z.atr);
   z.activeIdx = MathMax(s + p.strength, reach);
   z.activeTime = (z.activeIdx <= last) ? r[z.activeIdx].time : 0;
   z.status = SDB_ZONE_FRESH;
   return true;
  }

bool ZoneEntered(const MqlRates &bar, const SdbZone &z) { return z.demand ? bar.low <= z.proximal : bar.high >= z.proximal; }
bool ZoneBroken(const MqlRates &bar, const SdbZone &z)  { return z.demand ? bar.close < z.distal : bar.close > z.distal; }

// Status dari bar sesudah bar aktif (Req 2.1–2.3). Invalid diperiksa lebih dulu dan final; sentuhan = masuk
// setelah bar sebelumnya di luar, dengan keadaan awal dari bar aktif (design §8.2).
void ZoneStatus(const MqlRates &r[], const SdbZoneParams &p, SdbZone &z)
  {
   int last = ArraySize(r) - 1;
   z.touches = 0;
   if(z.activeIdx > last)
     {
      z.status = SDB_ZONE_FRESH;
      return;
     }
   bool inside = ZoneEntered(r[z.activeIdx], z);
   int end = MathMin(last, z.swingIdx + p.maxAge);
   for(int j = z.activeIdx + 1; j <= end; j++)
     {
      if(ZoneBroken(r[j], z))
        {
         z.status = SDB_ZONE_INVALID;
         return;
        }
      bool entered = ZoneEntered(r[j], z);
      if(entered && !inside)
         z.touches++;
      inside = entered;
     }
   if(last - z.swingIdx > p.maxAge)
      z.status = SDB_ZONE_EXPIRED;
   else
      z.status = (z.touches == 0) ? SDB_ZONE_FRESH : (z.touches == 1 ? SDB_ZONE_TESTED : SDB_ZONE_WEAK);
  }

bool ZoneInList(const string id, const string &ids[])
  {
   for(int i = 0; i < ArraySize(ids); i++)
      if(ids[i] == id)
         return true;
   return false;
  }

// Peta lengkap dari bar MTF (Req 3.1): swing -> calon -> hanya yang sudah aktif -> status -> Used.
int BuildZones(const MqlRates &r[], const SdbZoneParams &p, const ENUM_TIMEFRAMES tf, const string &usedIds[], SdbZone &out[])
  {
   ArrayFree(out);
   double atr[];
   if(!AtrSeries(r, SDB_ZONE_ATR_PERIOD, atr))
      return 0;
   SdbSwing sw[];
   FindSwings(r, p.strength, sw);
   int last = ArraySize(r) - 1;
   for(int k = 0; k < ArraySize(sw); k++)
     {
      SdbZone z;
      if(!ZoneCandidate(r, atr, sw[k], p, z) || z.activeIdx > last)
         continue;
      z.id = ZoneId(tf, z.swingTime, z.demand);
      ZoneStatus(r, p, z);
      z.used = ZoneInList(z.id, usedIds);
      int n = ArraySize(out);
      ArrayResize(out, n + 1, 32);
      out[n] = z;
     }
   return ArraySize(out);
  }

int ZonesNeeded(const SdbZoneParams &p)
  {
   return p.maxAge + p.legBars + 2 * p.strength + SDB_EMA_WARMUP_MULT * SDB_ZONE_ATR_PERIOD;
  }

bool ZoneValid(const SdbZone &z)
  {
   return !z.used && (z.status == SDB_ZONE_FRESH || z.status == SDB_ZONE_TESTED);
  }

// Zona valid searah yang dipotong rentang bar; Fresh dulu, lalu swing terbaru (Req 4.1).
int TouchedZone(const SdbZone &z[], const ENUM_SDB_DIR dir, const double low, const double high)
  {
   int best = -1;
   for(int i = 0; i < ArraySize(z); i++)
     {
      if(!ZoneValid(z[i]) || z[i].demand != (dir == SDB_DIR_BULL) || dir == SDB_DIR_NONE)
         continue;
      double lo = MathMin(z[i].distal, z[i].proximal), hi = MathMax(z[i].distal, z[i].proximal);
      if(low > hi || high < lo)
         continue;
      if(best < 0)
        {
         best = i;
         continue;
        }
      bool fresh = z[i].status == SDB_ZONE_FRESH, bestFresh = z[best].status == SDB_ZONE_FRESH;
      if((fresh && !bestFresh) || (fresh == bestFresh && z[i].swingTime > z[best].swingTime))
         best = i;
     }
   return best;
  }

// Zona lawan valid terdekat di depan harga, diukur dari batas dekatnya (Req 4.2, design §8.1).
int OppositeZone(const SdbZone &z[], const ENUM_SDB_DIR dir, const double price)
  {
   int best = -1;
   for(int i = 0; i < ArraySize(z); i++)
     {
      if(!ZoneValid(z[i]) || dir == SDB_DIR_NONE)
         continue;
      bool buy = (dir == SDB_DIR_BULL);
      if(buy && (z[i].demand || z[i].proximal <= price))
         continue;
      if(!buy && (!z[i].demand || z[i].proximal >= price))
         continue;
      if(best < 0 || (buy ? z[i].proximal < z[best].proximal : z[i].proximal > z[best].proximal))
         best = i;
     }
   return best;
  }

int ZoneScore(const SdbZone &z)
  {
   if(z.used)
      return 0;
   return z.status == SDB_ZONE_FRESH ? 30 : (z.status == SDB_ZONE_TESTED ? 15 : 0);
  }

// Zona dengan waktu swing sebelum batas ini sudah Kedaluwarsa (last - swingIdx > maxAge), dihitung dalam
// bar, bukan jam kalender: gap akhir pekan tidak membuat penanda Used zona yang masih aktif terhapus (temuan SC-13).
datetime ZoneUsedCutoff(const MqlRates &r[], const int maxAge)
  {
   int last = ArraySize(r) - 1;
   return (last - maxAge >= 0) ? r[last - maxAge].time : 0;
  }

// Sidik peta urut ID untuk uji tanpa repaint (design §8.5).
string ZoneMapText(const SdbZone &z[], const int digits)
  {
   string items[];
   int n = ArraySize(z);
   ArrayResize(items, n);
   for(int i = 0; i < n; i++)
      items[i] = StringFormat("%s:%d:%d:%d:%s:%s", z[i].id, (int)z[i].status, z[i].touches, (int)z[i].used,
                              DoubleToString(z[i].distal, digits), DoubleToString(z[i].proximal, digits));
   for(int i = 1; i < n; i++)
      for(int j = i; j > 0 && items[j] < items[j - 1]; j--)
        {
         string t = items[j];
         items[j] = items[j - 1];
         items[j - 1] = t;
        }
   string out = "";
   for(int i = 0; i < n; i++)
      out += items[i] + ";";
   return out;
  }

#endif // SDB_ANALYSIS_ZONERULES_MQH
