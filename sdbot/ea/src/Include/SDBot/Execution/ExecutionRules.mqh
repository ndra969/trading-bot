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

//--- Broker: filling, retcode, langkah retry

// FOK > IOC > RETURN, sesuai flag SYMBOL_FILLING_MODE simbol (Req 2.1, EC-05).
ENUM_ORDER_TYPE_FILLING PickFillingMode(const long symbolFillingFlags)
  {
   if((symbolFillingFlags & SYMBOL_FILLING_FOK) != 0)
      return ORDER_FILLING_FOK;
   if((symbolFillingFlags & SYMBOL_FILLING_IOC) != 0)
      return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
  }

ENUM_SDB_RETCODE_CLASS ClassifyRetcode(const uint retcode)
  {
   switch(retcode)
     {
      case TRADE_RETCODE_DONE:
      case TRADE_RETCODE_PLACED:
      case TRADE_RETCODE_DONE_PARTIAL:      return SDB_RC_SUCCESS;
      case TRADE_RETCODE_NO_CHANGES:        return SDB_RC_NO_CHANGES;
      case TRADE_RETCODE_REQUOTE:
      case TRADE_RETCODE_PRICE_CHANGED:
      case TRADE_RETCODE_PRICE_OFF:
      case TRADE_RETCODE_TOO_MANY_REQUESTS:
      case TRADE_RETCODE_LOCKED:            return SDB_RC_TRANSIENT;
      case 0:                               // tanpa jawaban server
      case TRADE_RETCODE_TIMEOUT:
      case TRADE_RETCODE_CONNECTION:
      case TRADE_RETCODE_ERROR:             return SDB_RC_AMBIGUOUS;
      case TRADE_RETCODE_POSITION_CLOSED:   return SDB_RC_POSITION_GONE;
      default:                              return SDB_RC_PERMANENT;
     }
  }

// attempt dihitung dari 1 (kiriman pertama): paling banyak 1 kirim + SDB_MAX_RETRY ulangan (Req 2.2–2.4, 4.6).
ENUM_SDB_NEXT_STEP NextStep(const ENUM_SDB_RETCODE_CLASS c, const int attempt, const bool foundByRequestId)
  {
   if(c == SDB_RC_SUCCESS || c == SDB_RC_NO_CHANGES)
      return SDB_STEP_SUCCEED;
   if(c == SDB_RC_AMBIGUOUS && foundByRequestId)
      return SDB_STEP_SUCCEED;
   if(c == SDB_RC_POSITION_GONE)
      return SDB_STEP_GONE;
   if((c == SDB_RC_TRANSIENT || c == SDB_RC_AMBIGUOUS) && attempt <= SDB_MAX_RETRY)
      return SDB_STEP_RETRY;
   return SDB_STEP_GIVE_UP;
  }

//--- Komentar order dan ID permintaan (Req 5)

string BuildOrderComment(const double initialSl, const int digits, const string requestId)
  {
   return SDB_COMMENT_PREFIX + DoubleToString(initialSl, digits) + "|" + requestId;
  }

bool IsRequestIdChar(const ushort c)
  {
   return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'z');
  }

// Angka positif desimal biasa: digit dengan paling banyak satu titik di tengah.
bool IsPlainPrice(const string s)
  {
   int n = StringLen(s);
   int dots = 0;
   if(n == 0)
      return false;
   for(int i = 0; i < n; i++)
     {
      ushort c = StringGetCharacter(s, i);
      if(c == '.')
        {
         if(i == 0 || i == n - 1 || ++dots > 1)
            return false;
        }
      else if(c < '0' || c > '9')
         return false;
     }
   return StringToDouble(s) > 0.0;
  }

// Gagal untuk apa pun selain SDB|<harga>|<id 4 karakter [0-9a-z]> (komentar dipotong/diubah broker).
bool ParseOrderComment(const string comment, double &initialSl, string &requestId)
  {
   initialSl = 0.0;
   requestId = "";
   if(StringFind(comment, SDB_COMMENT_PREFIX) != 0)
      return false;
   string parts[];
   if(StringSplit(comment, '|', parts) != 3 || !IsPlainPrice(parts[1]) || StringLen(parts[2]) != SDB_REQUEST_ID_LEN)
      return false;
   for(int i = 0; i < SDB_REQUEST_ID_LEN; i++)
      if(!IsRequestIdChar(StringGetCharacter(parts[2], i)))
         return false;
   initialSl = StringToDouble(parts[1]);
   requestId = parts[2];
   return true;
  }

// base36 4 karakter dari (magic % 1296) × 1296 + counter % 1296: beda antar-instance di blok magic,
// berulang baru setelah 1.296 order per instance.
string MakeRequestId(const long magic, const long counter)
  {
   const string digits = "0123456789abcdefghijklmnopqrstuvwxyz";
   long n = (magic % 1296) * 1296 + counter % 1296;
   string id = "";
   for(int i = 0; i < SDB_REQUEST_ID_LEN; i++)
     {
      id = StringSubstr(digits, (int)(n % 36), 1) + id;
      n /= 36;
     }
   return id;
  }

// Negatif = merugikan trader (buy terisi lebih mahal, sell terisi lebih murah).
int SlippagePoints(const bool isBuy, const double requested, const double filled, const double point)
  {
   double diff = isBuy ? requested - filled : filled - requested;
   return (int)MathRound(diff / point);
  }

//--- Posisi: ubah SL dan tutup sebagian (Req 4.2, 4.5)

// SL hanya boleh bergerak ke arah menguntungkan, di sisi harga yang benar, di luar stops level,
// dan tidak saat SL lama berada di dalam freeze level.
bool IsModifySlAllowed(const bool isBuy, const double oldSl, const double newSl, const double bid, const double ask,
                       const int stopsLevel, const int freezeLevel, const double point, string &why)
  {
   why = "";
   double price = isBuy ? bid : ask;
   bool better = (oldSl <= 0.0) || (isBuy ? newSl > oldSl : newSl < oldSl);
   bool rightSide = isBuy ? newSl < price : newSl > price;
   if(!better)
      why = StringFormat("SL baru %s tidak lebih baik dari %s", DoubleToString(newSl, 8), DoubleToString(oldSl, 8));
   else if(!rightSide)
      why = "SL baru di sisi harga yang salah";
   else if(PriceDistancePoints(price, newSl, point) < stopsLevel)
      why = StringFormat("SL baru %d point dari harga < stops %d", PriceDistancePoints(price, newSl, point), stopsLevel);
   else if(oldSl > 0.0 && freezeLevel > 0 && PriceDistancePoints(price, oldSl, point) <= freezeLevel)
      why = StringFormat("SL lama di dalam freeze level %d", freezeLevel);
   return why == "";
  }

bool IsPartialVolumeValid(const double closeVol, const double posVol, const double vMin, const double step, string &why)
  {
   why = "";
   if(closeVol <= 0.0)
      why = "volume tutup <= 0";
   else if(closeVol >= posVol - SDB_VOLUME_EPS)
      why = StringFormat("volume tutup %.3f >= volume posisi %.3f", closeVol, posVol);
   else if(closeVol < vMin - SDB_VOLUME_EPS)
      why = StringFormat("volume tutup %.3f < lot minimum %.3f", closeVol, vMin);
   else if(!IsVolumeStepMultiple(closeVol, step))
      why = StringFormat("volume tutup %.3f bukan kelipatan step %.3f", closeVol, step);
   else if(posVol - closeVol < vMin - SDB_VOLUME_EPS)
      why = StringFormat("sisa %.3f < lot minimum %.3f", posVol - closeVol, vMin);
   return why == "";
  }

#endif // SDB_EXECUTION_EXECUTIONRULES_MQH
