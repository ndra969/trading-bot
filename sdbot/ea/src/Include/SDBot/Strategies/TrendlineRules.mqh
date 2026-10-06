//+------------------------------------------------------------------+
//| TrendlineRules.mqh — skor trendline sebagai fungsi murni (spec 19
//| Req 1–2; design §3.1; PRD skor konfluensi: 3+ sentuhan searah =
//| 15, 2 = 7). Hanya garis SEARAH sinyal: support naik dari swing low
//| untuk BUY, resistance turun dari swing high untuk SELL. Bot Python
//| tanpa filter kemiringan ikut menghitung garis melawan tren (net
//| −$102 per 30 hari, python-bot-lessons §1). Swing dari FindSwings
//| (fractal berjeda, tanpa repaint), semua ukuran dalam ATR.
//+------------------------------------------------------------------+
#ifndef SDB_STRATEGIES_TRENDLINERULES_MQH
#define SDB_STRATEGIES_TRENDLINERULES_MQH

#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/Types.mqh>
#include <SDBot/Analysis/StructureRules.mqh>
#include <SDBot/Strategies/StrategyMath.mqh>

#define SDB_TL_REASON_DATA "data kurang"
#define SDB_TL_REASON_NONE "tidak ada garis"

double TlValueAt(const int i1, const double p1, const int i2, const double p2, const double x)
  {
   return p1 + (p2 - p1) / (double)(i2 - i1) * (x - i1);
  }

// Swing sesisi di jendela yang berjarak <= tol dari garis, termasuk yang sebelum i1 (garisnya sama secara geometri);
// first = indeks sentuhan paling awal, awal cek patah.
int TlTouches(const SdbSwing &sw[], const bool lows, const int i1, const double p1, const int i2, const double p2, const double tol,
              int &first)
  {
   int n = 0;
   first = i1;
   for(int k = 0; k < ArraySize(sw); k++)
      if(sw[k].isHigh != lows && MathAbs(sw[k].price - TlValueAt(i1, p1, i2, p2, sw[k].index)) <= tol + 1e-12)
        {
         n++;
         first = MathMin(first, sw[k].index);
        }
   return n;
  }

// Patah: close bar mana pun sejak sentuhan pertama melewati garis > tol ke arah berlawanan (design keputusan 1).
bool TlBroken(const MqlRates &r[], const bool support, const int from, const int i1, const double p1, const int i2, const double p2,
              const double tol)
  {
   for(int k = from; k < ArraySize(r); k++)
     {
      double line = TlValueAt(i1, p1, i2, p2, k);
      if(support ? r[k].close < line - tol - 1e-12 : r[k].close > line + tol + 1e-12)
         return true;
     }
   return false;
  }

void TlEvaluate(const MqlRates &r[], const SdbZone &z, const bool buy, const int strength, const int lookback, const double atr,
                SdbTrendlineResult &out)
  {
   ZeroMemory(out);
   out.reason = SDB_TL_REASON_DATA;
   int n = ArraySize(r);
   if(n < 2 * strength + 2 || atr <= 0.0)
      return;
   SdbSwing all[];
   FindSwings(r, strength, all);
   SdbSwing sw[];
   for(int k = 0; k < ArraySize(all); k++)
      if(all[k].isHigh != buy && all[k].index >= n - lookback)
        {
         int m = ArraySize(sw);
         ArrayResize(sw, m + 1, 32);
         sw[m] = all[k];
        }
   out.reason = SDB_TL_REASON_NONE;
   double tol = SDB_TL_TOL_ATR * atr;
   int best1 = -1, best2 = -1;
   for(int a = 0; a < ArraySize(sw); a++)
      for(int b = a + 1; b < ArraySize(sw); b++)
        {
         int i1 = sw[a].index, i2 = sw[b].index;
         double p1 = sw[a].price, p2 = sw[b].price;
         double slope = (p2 - p1) / (double)(i2 - i1) / atr;
         if(buy ? slope < SDB_TL_MIN_SLOPE_ATR : slope > -SDB_TL_MIN_SLOPE_ATR)
            continue;
         double dist = DistToZone(z, TlValueAt(i1, p1, i2, p2, n));
         if(dist > tol + 1e-12)
            continue;
         int first;
         int touches = TlTouches(sw, buy, i1, p1, i2, p2, tol, first);
         if(TlBroken(r, buy, first, i1, p1, i2, p2, tol))
            continue;
         bool better = touches > out.touches || (touches == out.touches && (i2 > best2 || (i2 == best2 && i1 > best1)));
         if(!better)
            continue;
         best1 = i1;
         best2 = i2;
         out.touches = touches;
         out.slopeAtr = slope;
         out.distAtr = dist / atr;
         out.t1 = sw[a].time;
         out.t2 = sw[b].time;
         out.reason = "";
        }
   out.score = out.touches >= 3 ? SDB_TL_SCORE_3 : (out.touches == 2 ? SDB_TL_SCORE_2 : 0);
  }

#endif // SDB_STRATEGIES_TRENDLINERULES_MQH
