//+------------------------------------------------------------------+
//| BreakoutRules.mqh — skor breakout & retest sebagai fungsi murni
//| (spec 20 Req 1–2; design §3.1; PRD skor konfluensi: retest level
//| yang ditembus = 10). BUY: swing high (resistance) ditembus close
//| naik lalu zona menguji ulang level itu; SELL cerminannya. Hanya
//| close bar MTF tertutup sesudah swing terkonfirmasi; wick saja tidak
//| dihitung; breakout gagal membuang level. Bot Python punya layer
//| breakout yang tidak pernah dipanggil (python-bot-lessons §1), jadi
//| keterhubungannya dibuktikan di TC-SG-32 dan SC-20.
//+------------------------------------------------------------------+
#ifndef SDB_STRATEGIES_BREAKOUTRULES_MQH
#define SDB_STRATEGIES_BREAKOUTRULES_MQH

#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/Types.mqh>
#include <SDBot/Analysis/StructureRules.mqh>
#include <SDBot/Strategies/StrategyMath.mqh>

#define SDB_BO_REASON_DATA "data kurang"
#define SDB_BO_REASON_NONE "tidak ada breakout"

// Close pertama sesudah konfirmasi swing (index + strength) yang menembus level searah >= minBreak; -1 bila tidak ada.
int BoBreakIndex(const MqlRates &r[], const SdbSwing &s, const bool buy, const int strength, const double minBreak)
  {
   for(int k = s.index + strength + 1; k < ArraySize(r); k++)
      if(buy ? r[k].close >= s.price + minBreak - 1e-12 : r[k].close <= s.price - minBreak + 1e-12)
         return k;
   return -1;
  }

// Gagal: close di (k, n-1] kembali melewati level > tol ke arah berlawanan.
bool BoFailed(const MqlRates &r[], const int k, const double level, const bool buy, const double tol)
  {
   for(int j = k + 1; j < ArraySize(r); j++)
      if(buy ? r[j].close < level - tol - 1e-12 : r[j].close > level + tol + 1e-12)
         return true;
   return false;
  }

void BoEvaluate(const MqlRates &r[], const SdbZone &z, const bool buy, const int strength, const int lookback, const double atr,
                SdbBreakoutResult &out)
  {
   ZeroMemory(out);
   out.reason = SDB_BO_REASON_DATA;
   int n = ArraySize(r);
   if(n < 2 * strength + 2 || atr <= 0.0)
      return;
   SdbSwing sw[];
   FindSwings(r, strength, sw);
   out.reason = SDB_BO_REASON_NONE;
   double tol = SDB_BO_TOL_ATR * atr, minBreak = SDB_BO_MIN_BREAK_ATR * atr;
   int bestK = -1, bestSwing = -1;
   for(int i = 0; i < ArraySize(sw); i++)
     {
      if(sw[i].isHigh != buy || sw[i].index < n - lookback)
         continue;
      int k = BoBreakIndex(r, sw[i], buy, strength, minBreak);
      if(k < 0 || BoFailed(r, k, sw[i].price, buy, tol))
         continue;
      double dist = DistToZone(z, sw[i].price);
      if(dist > tol + 1e-12)
         continue;
      if(k < bestK || (k == bestK && sw[i].index <= bestSwing))
         continue;
      bestK = k;
      bestSwing = sw[i].index;
      out.score = SDB_BO_SCORE;
      out.level = sw[i].price;
      out.ageBars = n - k;
      out.distAtr = dist / atr;
      out.tBreak = r[k].time;
      out.reason = "";
     }
  }

#endif // SDB_STRATEGIES_BREAKOUTRULES_MQH
