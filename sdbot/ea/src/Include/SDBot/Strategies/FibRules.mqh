//+------------------------------------------------------------------+
//| FibRules.mqh — skor Fibonacci sebagai fungsi murni (spec 18 Req
//| 1–2; design §3.1; PRD skor konfluensi). Leg = impuls penuh yang
//| memuat zona: ekstrem lookback bar MTF sebelum candle swing zona
//| sampai ekstrem bar sesudahnya (keputusan A 2026-10-06; leg dari
//| batas jauh zona sendiri hanya mengukur lebar zona). Tanpa
//| lookahead: cache zona hanya berisi bar tertutup. Skor dari level
//| TERDEKAT dengan rasio batas dekat zona, dikurangi linear sesuai
//| jarak; bot Python memilih level dengan skor tertinggi sehingga
//| 0.618 memberi skor penuh di ~83% setup (python-bot-lessons §1).
//+------------------------------------------------------------------+
#ifndef SDB_STRATEGIES_FIBRULES_MQH
#define SDB_STRATEGIES_FIBRULES_MQH

#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/Types.mqh>

#define SDB_FIB_REASON_SHORT "leg pendek"
#define SDB_FIB_REASON_DATA  "data kurang"
#define SDB_FIB_REASON_OUT   "di luar leg"

// Awal impuls: demand = low terendah r[swingIdx - lookback .. swingIdx], supply = high tertinggi.
bool FibLegStart(const MqlRates &r[], const SdbZone &z, const int lookback, double &legStart)
  {
   legStart = 0.0;
   if(z.swingIdx < 0 || z.swingIdx >= ArraySize(r))
      return false;
   legStart = z.demand ? r[z.swingIdx].low : r[z.swingIdx].high;
   for(int i = MathMax(0, z.swingIdx - MathMax(0, lookback)); i < z.swingIdx; i++)
      legStart = z.demand ? MathMin(legStart, r[i].low) : MathMax(legStart, r[i].high);
   return true;
  }

// Ujung impuls sejak candle swing zona: demand = high tertinggi, supply = low terendah.
bool FibLegEnd(const MqlRates &r[], const SdbZone &z, double &legEnd)
  {
   legEnd = 0.0;
   int n = ArraySize(r);
   if(z.swingIdx < 0 || z.swingIdx >= n)
      return false;
   legEnd = z.demand ? r[z.swingIdx].high : r[z.swingIdx].low;
   for(int i = z.swingIdx + 1; i < n; i++)
      legEnd = z.demand ? MathMax(legEnd, r[i].high) : MathMin(legEnd, r[i].low);
   return true;
  }

// 0 = ujung impuls, 1 = awal leg. Rumus sama untuk demand dan supply karena arah ada di tanda (end - start).
double RetraceRatio(const double start, const double end, const double price)
  {
   double leg = end - start;
   if(MathAbs(leg) < 1e-12)
      return -1.0;
   return (end - price) / leg;
  }

// Level terdekat (tie ke level lebih dalam); skor = dasar x (1 - jarak / toleransi), dibulatkan.
int FibScore(const double ratio, double &level, double &dist)
  {
   double levels[SDB_FIB_LEVELS] = {0.382, 0.5, 0.618, 0.786};
   int base[SDB_FIB_LEVELS] = {SDB_FIB_SCORE_LOW, SDB_FIB_SCORE_HIGH, SDB_FIB_SCORE_HIGH, SDB_FIB_SCORE_LOW};
   level = 0.0;
   dist = 0.0;
   if(ratio < SDB_FIB_MIN_RATIO || ratio > SDB_FIB_MAX_RATIO)
      return 0;
   int best = 0;
   for(int i = 1; i < SDB_FIB_LEVELS; i++)
      if(MathAbs(ratio - levels[i]) <= MathAbs(ratio - levels[best]) + 1e-12)
         best = i;
   level = levels[best];
   dist = MathAbs(ratio - level);
   return (int)MathRound(base[best] * MathMax(0.0, 1.0 - dist / SDB_FIB_TOLERANCE));
  }

void FibEvaluate(const MqlRates &r[], const SdbZone &z, const double minLegAtr, const int lookback, SdbFibResult &out)
  {
   ZeroMemory(out);
   out.ratio = -1.0;
   out.reason = "";
   if(!FibLegStart(r, z, lookback, out.legStart) || !FibLegEnd(r, z, out.legEnd))
     {
      out.reason = SDB_FIB_REASON_DATA;
      return;
     }
   if(MathAbs(out.legEnd - out.legStart) < minLegAtr * z.atr)
     {
      out.reason = SDB_FIB_REASON_SHORT;
      return;
     }
   out.ratio = RetraceRatio(out.legStart, out.legEnd, z.proximal);
   out.score = FibScore(out.ratio, out.level, out.dist);
   if(out.level == 0.0)
      out.reason = SDB_FIB_REASON_OUT;
  }

#endif // SDB_STRATEGIES_FIBRULES_MQH
