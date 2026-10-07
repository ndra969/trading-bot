//+------------------------------------------------------------------+
//| RsiRules.mqh — skor RSI divergence sebagai fungsi murni (spec 21
//| Req 1.2, 2; design §3.1; PRD skor konfluensi: divergence searah =
//| 5). Divergence reguler di dua swing sinyal terakhir MTF: BUY lower
//| low harga dengan higher low RSI, SELL cerminannya. RSI HANYA skor,
//| tidak pernah tahap tolak: di bot Python RSI menjadi gerbang (6.773
//| penolakan vs 6 kontribusi, python-bot-lessons §1).
//+------------------------------------------------------------------+
#ifndef SDB_STRATEGIES_RSIRULES_MQH
#define SDB_STRATEGIES_RSIRULES_MQH

#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/Types.mqh>
#include <SDBot/Analysis/StructureRules.mqh>

#define SDB_RSI_REASON_DATA  "data kurang"
#define SDB_RSI_REASON_SWING "swing kurang"

// Dua swing sinyal terakhir (low untuk BUY, high untuk SELL) dengan indeks >= n - lookback; false bila < 2.
bool RsiLastTwoSwings(const MqlRates &r[], const bool buy, const int strength, const int lookback, SdbSwing &s1, SdbSwing &s2)
  {
   SdbSwing sw[];
   FindSwings(r, strength, sw);
   int n = ArraySize(r), found = 0;
   for(int i = ArraySize(sw) - 1; i >= 0 && found < 2; i--)
     {
      if(sw[i].isHigh == buy || sw[i].index < n - lookback)
         continue;
      if(found == 0)
         s2 = sw[i];
      else
         s1 = sw[i];
      found++;
     }
   return found == 2;
  }

void RsiEvaluate(const MqlRates &r[], const double &rsi[], const bool buy, const int strength, const int lookback, const double atr,
                 SdbRsiResult &out)
  {
   ZeroMemory(out);
   out.reason = SDB_RSI_REASON_DATA;
   int n = ArraySize(r);
   if(n == 0 || ArraySize(rsi) != n || atr <= 0.0)
      return;
   SdbSwing s1, s2;
   if(!RsiLastTwoSwings(r, buy, strength, lookback, s1, s2))
     {
      out.reason = SDB_RSI_REASON_SWING;
      return;
     }
   out.have = true;
   out.reason = "";
   out.rsiDiff = buy ? rsi[s2.index] - rsi[s1.index] : rsi[s1.index] - rsi[s2.index];
   out.priceDiffAtr = MathAbs(s2.price - s1.price) / atr;
   out.ageBars = n - s2.index;
   bool newExtreme = buy ? s2.price < s1.price : s2.price > s1.price;
   if(newExtreme && out.rsiDiff >= SDB_RSI_MIN_DIFF - 1e-9 && out.ageBars <= SDB_RSI_MAX_AGE)
      out.score = SDB_RSI_SCORE;
  }

#endif // SDB_STRATEGIES_RSIRULES_MQH
