//+------------------------------------------------------------------+
//| StrategyMath.mqh — hitungan kecil bersama komponen konfirmasi Fase 5
//| (spec 20 design §3.4): jarak harga ke rentang zona.
//+------------------------------------------------------------------+
#ifndef SDB_STRATEGIES_STRATEGYMATH_MQH
#define SDB_STRATEGIES_STRATEGYMATH_MQH

#include <SDBot/Core/Types.mqh>

// Jarak (harga) dari nilai v ke rentang zona [distal, proximal]; 0 bila di dalam. Dipakai trendline dan breakout.
double DistToZone(const SdbZone &z, const double v)
  {
   double lo = MathMin(z.distal, z.proximal), hi = MathMax(z.distal, z.proximal);
   return v < lo ? lo - v : (v > hi ? v - hi : 0.0);
  }

#endif // SDB_STRATEGIES_STRATEGYMATH_MQH
