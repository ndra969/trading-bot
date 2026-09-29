//+------------------------------------------------------------------+
//| ExecutionRules.mqh — aturan keputusan eksekusi sebagai fungsi murni
//| (spec 04 design §4.1): tidak membaca pasar, sehingga diuji penuh di
//| suite TestExecution. CExecutor hanya mengambil data simbol lalu
//| memanggil fungsi ini.
//+------------------------------------------------------------------+
#ifndef SDB_EXECUTION_EXECUTIONRULES_MQH
#define SDB_EXECUTION_EXECUTIONRULES_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/SchemaEnums.mqh>

#define SDB_VOLUME_EPS 1e-8   // toleransi floating point untuk perbandingan volume

// Jarak dua harga dalam point, dibulatkan agar 1.09972 vs 1.10000 = 28 tepat (bukan 27.9999).
int PriceDistancePoints(const double a, const double b, const double point)
  {
   return (int)MathRound(MathAbs(a - b) / point);
  }

// "" = lolos; selain itu kode reject_stage (Req 1.1, 1.2). price = ask untuk buy, bid untuk sell.
string ValidateOrderSides(const bool isBuy, const double price, const double sl, const double tp)
  {
   if(sl <= 0.0 || tp <= 0.0)
      return SDB_REJECT_STAGE_INVALID_STOPS;
   if(isBuy && (sl >= price || tp <= price))
      return SDB_REJECT_STAGE_INVALID_STOPS;
   if(!isBuy && (sl <= price || tp >= price))
      return SDB_REJECT_STAGE_INVALID_STOPS;
   return "";
  }

// Jarak SL dan TP minimal stops level + spread, dan tidak di dalam freeze level (Req 1.4).
bool CheckStops(const double price, const double sl, const double tp, const int stopsLevel, const int freezeLevel,
                const int spreadPts, const double point, string &why)
  {
   why = "";
   int minDist = stopsLevel + spreadPts;
   int slDist = PriceDistancePoints(price, sl, point);
   int tpDist = PriceDistancePoints(price, tp, point);
   if(slDist < minDist || tpDist < minDist)
     {
      why = StringFormat("jarak SL %d / TP %d point < stops %d + spread %d", slDist, tpDist, stopsLevel, spreadPts);
      return false;
     }
   if(slDist < freezeLevel || tpDist < freezeLevel)
     {
      why = StringFormat("jarak SL %d / TP %d point di dalam freeze level %d", slDist, tpDist, freezeLevel);
      return false;
     }
   return true;
  }

bool IsVolumeStepMultiple(const double vol, const double step)
  {
   if(step <= 0.0)
      return true;
   double steps = vol / step;
   return MathAbs(steps - MathRound(steps)) < 1e-6;
  }

// Volume dalam batas simbol, kelipatan step, dan tidak melewati limit bersama posisi yang ada (Req 1.5).
// limit 0 = broker tidak membatasi.
bool CheckVolume(const double vol, const double vMin, const double vMax, const double step, const double limit,
                 const double existingVol, string &why)
  {
   why = "";
   if(vol < vMin - SDB_VOLUME_EPS || vol > vMax + SDB_VOLUME_EPS)
      why = StringFormat("volume %.2f di luar %.2f-%.2f", vol, vMin, vMax);
   else if(!IsVolumeStepMultiple(vol, step))
      why = StringFormat("volume %.3f bukan kelipatan step %.2f", vol, step);
   else if(limit > 0.0 && existingVol + vol > limit + SDB_VOLUME_EPS)
      why = StringFormat("volume %.2f + posisi %.2f melewati limit %.2f", vol, existingVol, limit);
   return why == "";
  }

#endif // SDB_EXECUTION_EXECUTIONRULES_MQH
