//+------------------------------------------------------------------+
//| PatternRules.mqh — pola candle terarah LTF sebagai fungsi murni di
//| atas array MqlRates urut waktu naik (spec 12 Req 1–2; design §3.1).
//| Definisi untuk BULL; BEAR adalah cerminnya. Ukuran relatif ATR dan
//| rentang bar. Pola netral tidak diperiksa sama sekali (python-bot-
//| lessons §1: inside bar/doji dulu menang atas pola terarah).
//+------------------------------------------------------------------+
#ifndef SDB_STRATEGIES_PATTERNRULES_MQH
#define SDB_STRATEGIES_PATTERNRULES_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/SchemaEnums.mqh>

#define SDB_PA_EPS 1e-9   // x ATR: batas inklusif tetap lolos walau ada galat floating point

double PaBody(const MqlRates &b) { return MathAbs(b.close - b.open); }

// Arah badan: BULL bila close > open, BEAR bila close < open, NONE untuk doji.
ENUM_SDB_DIR PaBarDir(const MqlRates &b)
  {
   if(b.close > b.open)
      return SDB_DIR_BULL;
   if(b.close < b.open)
      return SDB_DIR_BEAR;
   return SDB_DIR_NONE;
  }

ENUM_SDB_DIR PaOpposite(const ENUM_SDB_DIR dir) { return dir == SDB_DIR_BULL ? SDB_DIR_BEAR : SDB_DIR_BULL; }

// a >= b dan a > b dengan toleransi (tol = SDB_PA_EPS x ATR).
bool PaGe(const double a, const double b, const double tol) { return a >= b - tol; }
bool PaGt(const double a, const double b, const double tol) { return a > b + tol; }

// Bintang pagi/sore: bar i-2 berlawanan besar, bar i-1 kecil, bar i searah melewati tengah badan i-2.
bool IsStar(const MqlRates &r[], const int i, const ENUM_SDB_DIR dir, const double atr)
  {
   if(i < 2 || i >= ArraySize(r))
      return false;
   double tol = SDB_PA_EPS * atr;
   double first = PaBody(r[i - 2]);
   if(PaBarDir(r[i - 2]) != PaOpposite(dir) || !PaGt(first, SDB_PA_STAR_FIRST_BODY_ATR * atr, tol))
      return false;
   if(PaBody(r[i - 1]) >= SDB_PA_STAR_MID_RATIO * first - tol || PaBarDir(r[i]) != dir)
      return false;
   double mid = (r[i - 2].open + r[i - 2].close) / 2.0;
   return dir == SDB_DIR_BULL ? PaGt(r[i].close, mid, tol) : PaGt(mid, r[i].close, tol);
  }

// Engulfing: i-1 berlawanan, i searah, badan i menelan (termasuk sama) dan lebih besar.
bool IsEngulf(const MqlRates &r[], const int i, const ENUM_SDB_DIR dir, const double atr)
  {
   if(i < 1 || i >= ArraySize(r))
      return false;
   double tol = SDB_PA_EPS * atr;
   if(PaBarDir(r[i - 1]) != PaOpposite(dir) || PaBarDir(r[i]) != dir)
      return false;
   if(!PaGt(PaBody(r[i]), PaBody(r[i - 1]), tol))
      return false;
   if(dir == SDB_DIR_BULL)
      return PaGe(r[i].close, r[i - 1].open, tol) && PaGe(r[i - 1].close, r[i].open, tol);
   return PaGe(r[i - 1].open, r[i].close, tol) && PaGe(r[i].open, r[i - 1].close, tol);
  }

// Engulfing kuat: engulfing + badan >= 60% rentang dan >= 0,8 ATR + close melewati high/low i-1.
bool IsEngulfStrong(const MqlRates &r[], const int i, const ENUM_SDB_DIR dir, const double atr)
  {
   if(!IsEngulf(r, i, dir, atr))
      return false;
   double tol = SDB_PA_EPS * atr;
   double body = PaBody(r[i]);
   if(!PaGe(body, SDB_PA_STRONG_BODY_RANGE * (r[i].high - r[i].low), tol) || !PaGe(body, SDB_PA_STRONG_BODY_ATR * atr, tol))
      return false;
   return dir == SDB_DIR_BULL ? PaGt(r[i].close, r[i - 1].high, tol) : PaGt(r[i - 1].low, r[i].close, tol);
  }

// Pin bar: badan kecil, sumbu sisi berlawanan arah panjang dan dominan, rentang cukup.
bool IsPin(const MqlRates &r[], const int i, const ENUM_SDB_DIR dir, const double atr)
  {
   if(i < 0 || i >= ArraySize(r))
      return false;
   double tol = SDB_PA_EPS * atr;
   double range = r[i].high - r[i].low;
   double body = PaBody(r[i]);
   double lower = MathMin(r[i].open, r[i].close) - r[i].low;
   double upper = r[i].high - MathMax(r[i].open, r[i].close);
   double wick = dir == SDB_DIR_BULL ? lower : upper;
   double other = dir == SDB_DIR_BULL ? upper : lower;
   return PaGe(SDB_PA_PIN_BODY_RANGE * range, body, tol) && PaGe(wick, SDB_PA_PIN_WICK_BODY * body, tol) &&
          PaGe(wick, SDB_PA_PIN_WICK_RANGE * range, tol) && PaGt(wick, SDB_PA_PIN_WICK_OTHER * other, tol) &&
          PaGe(range, SDB_PA_PIN_RANGE_ATR * atr, tol);
  }

// Tweezer: i-1 berlawanan, i searah, low (BEAR: high) keduanya berselisih <= 0,1 ATR.
bool IsTweezer(const MqlRates &r[], const int i, const ENUM_SDB_DIR dir, const double atr)
  {
   if(i < 1 || i >= ArraySize(r))
      return false;
   if(PaBarDir(r[i - 1]) != PaOpposite(dir) || PaBarDir(r[i]) != dir)
      return false;
   double diff = dir == SDB_DIR_BULL ? MathAbs(r[i].low - r[i - 1].low) : MathAbs(r[i].high - r[i - 1].high);
   return PaGe(SDB_PA_TWEEZER_ATR * atr, diff, SDB_PA_EPS * atr);
  }

// Outside bar terarah: high dan low melewati bar i-1, bar i searah, close melewati close i-1.
bool IsOutside(const MqlRates &r[], const int i, const ENUM_SDB_DIR dir, const double atr)
  {
   if(i < 1 || i >= ArraySize(r))
      return false;
   double tol = SDB_PA_EPS * atr;
   if(!PaGt(r[i].high, r[i - 1].high, tol) || !PaGt(r[i - 1].low, r[i].low, tol) || PaBarDir(r[i]) != dir)
      return false;
   return dir == SDB_DIR_BULL ? PaGt(r[i].close, r[i - 1].close, tol) : PaGt(r[i - 1].close, r[i].close, tol);
  }

int PaScore(const string code)
  {
   if(code == SDB_PA_PATTERN_ENGULF_STRONG)
      return 10;
   if(code == SDB_PA_PATTERN_PIN)
      return 7;
   if(code == SDB_PA_PATTERN_STAR || code == SDB_PA_PATTERN_ENGULF || code == SDB_PA_PATTERN_TWEEZER ||
      code == SDB_PA_PATTERN_OUTSIDE)
      return 3;
   return 0;
  }

// Pola bar terakhir untuk arah `dir`; urutan dari yang paling spesifik, pola pertama yang cocok menang.
void DetectPattern(const MqlRates &r[], const double atr, const ENUM_SDB_DIR dir, SdbPattern &out)
  {
   int n = ArraySize(r);
   out.code = SDB_PA_PATTERN_NONE;
   out.dir = SDB_DIR_NONE;
   out.score = 0;
   out.barTime = n > 0 ? r[n - 1].time : 0;
   if(n < 3 || atr <= 0.0 || dir == SDB_DIR_NONE || r[n - 1].high - r[n - 1].low <= 0.0)
      return;
   int i = n - 1;
   string code = SDB_PA_PATTERN_NONE;
   if(IsStar(r, i, dir, atr))
      code = SDB_PA_PATTERN_STAR;
   else if(IsEngulfStrong(r, i, dir, atr))
      code = SDB_PA_PATTERN_ENGULF_STRONG;
   else if(IsPin(r, i, dir, atr))
      code = SDB_PA_PATTERN_PIN;
   else if(IsEngulf(r, i, dir, atr))
      code = SDB_PA_PATTERN_ENGULF;
   else if(IsTweezer(r, i, dir, atr))
      code = SDB_PA_PATTERN_TWEEZER;
   else if(IsOutside(r, i, dir, atr))
      code = SDB_PA_PATTERN_OUTSIDE;
   if(code == SDB_PA_PATTERN_NONE)
      return;
   out.code = code;
   out.dir = dir;
   out.score = PaScore(code);
  }

#endif // SDB_STRATEGIES_PATTERNRULES_MQH
