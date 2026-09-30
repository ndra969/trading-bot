//+------------------------------------------------------------------+
//| PositionMath.mqh — keputusan manajemen posisi murni (spec 06 design
//| §4.1). Tanpa akses pasar; diuji di suite TestPositionMath.
//+------------------------------------------------------------------+
#ifndef SDB_POSITION_POSITIONMATH_MQH
#define SDB_POSITION_POSITIONMATH_MQH

#include <SDBot/Core/Constants.mqh>
#include <SDBot/Risk/RiskMath.mqh>

//--- R, breakeven, partial (Req 1–3)

// Profit dalam R dari harga penutupan saat ini (bid buy, ask sell). R <= 0 -> 0.
double ProfitInR(const bool isBuy, const double entry, const double initialSl, const double closePrice)
  {
   double r = MathAbs(entry - initialSl);
   if(r <= 0.0 || initialSl <= 0.0)
      return 0.0;
   return (isBuy ? closePrice - entry : entry - closePrice) / r;
  }

// Req 1.4: SL di harga buka atau lebih baik.
bool IsBreakevenActive(const bool isBuy, const double entry, const double sl)
  {
   if(sl <= 0.0)
      return false;
   return isBuy ? sl >= entry - 1e-10 : sl <= entry + 1e-10;
  }

// Komisi pulang-pergi (uang) menjadi point untuk volume posisi, dibulatkan ke atas agar BE tidak rugi.
int CommissionPoints(const double roundTripCommissionMoney, const double moneyPerPoint)
  {
   double c = MathAbs(roundTripCommissionMoney);
   if(c <= 0.0 || moneyPerPoint <= 0.0)
      return 0;
   return (int)MathCeil(c / moneyPerPoint - 1e-9);
  }

// Req 2.1: titik BE = harga buka +/- (spread + komisi + buffer) point.
double BreakevenSl(const bool isBuy, const double entry, const int spreadPts, const int commissionPts, const int bufferPts,
                   const double point, const int digits)
  {
   double off = (spreadPts + commissionPts + bufferPts) * point;
   return NormalizeDouble(isBuy ? entry + off : entry - off, digits);
  }

bool ShouldBreakeven(const double profitR, const double beR, const bool beActive, const bool initialSlKnown)
  {
   return initialSlKnown && !beActive && profitR >= beR - 1e-9;
  }

// Req 3.1, 3.4: partial sudah dilakukan bila volume sekarang < volume awal (termasuk tutup sebagian manual).
bool ShouldPartial(const double profitR, const double partialR, const double curVol, const double initVol, const bool initialSlKnown)
  {
   bool done = curVol < initVol - 1e-9;
   return initialSlKnown && !done && profitR >= partialR - 1e-9;
  }

// Req 3.1, 3.2: persen dari volume awal, dibulatkan ke bawah; volume tutup atau sisa < minimum -> skip.
double PartialVolume(const double initVol, const double pct, const double step, const double vMin, const double curVol, bool &skip)
  {
   double v = RoundLotDown(initVol * pct / 100.0, step);
   skip = (v < vMin - 1e-9) || (curVol - v < vMin - 1e-9);
   return skip ? 0.0 : v;
  }

//--- Trailing, pilihan SL, restore, retry (Req 4, 5)

// Req 4.1: buy = bid - ATR x mult, sell = ask + ATR x mult.
double TrailingSl(const bool isBuy, const double closePrice, const double atr, const double mult, const int digits)
  {
   double off = atr * mult;
   return NormalizeDouble(isBuy ? closePrice - off : closePrice + off, digits);
  }

// Req 4.2, 5.2: SL baru lebih baik minimal minStepPts; SL lama 0 (tanpa SL) selalu lebih baik.
bool IsSlImprovement(const bool isBuy, const double oldSl, const double newSl, const int minStepPts, const double point)
  {
   if(newSl <= 0.0)
      return false;
   if(oldSl <= 0.0)
      return true;
   double gainPts = MathRound((isBuy ? newSl - oldSl : oldSl - newSl) / point);
   return gainPts >= minStepPts;
  }

// Req 5.2: kandidat terbaik antara BE dan trailing (0 = tidak ada kandidat); 0 bila bukan perbaikan.
double PickBestSl(const bool isBuy, const double currentSl, const double beCandidate, const double trailCandidate,
                  const int minStepPts, const double point)
  {
   double best = 0.0;
   if(beCandidate > 0.0)
      best = beCandidate;
   if(trailCandidate > 0.0 && (best == 0.0 || (isBuy ? trailCandidate > best : trailCandidate < best)))
      best = trailCandidate;
   return IsSlImprovement(isBuy, currentSl, best, minStepPts, point) ? best : 0.0;
  }

// Req 5.5: SL awal bila masih di sisi rugi dan cukup jauh (stops + spread); kalau tidak, SL valid terdekat.
double RestoreSl(const bool isBuy, const double initialSl, const double closePrice, const int stopsLevel, const int spreadPts,
                 const double point, const int digits)
  {
   double minDist = (stopsLevel + spreadPts) * point;
   if(initialSl > 0.0 && (isBuy ? initialSl <= closePrice - minDist + 1e-10 : initialSl >= closePrice + minDist - 1e-10))
      return NormalizeDouble(initialSl, digits);
   double off = (stopsLevel + spreadPts + 1) * point;
   return NormalizeDouble(isBuy ? closePrice - off : closePrice + off, digits);
  }

// Req 6.6: SL sudah lebih baik dari titik BE yang dipasang.
bool IsTrailingActive(const bool isBuy, const double beSl, const double sl)
  {
   if(beSl <= 0.0 || sl <= 0.0)
      return false;
   return isBuy ? sl > beSl + 1e-10 : sl < beSl - 1e-10;
  }

// Req 5.3: maksimal 3 percobaan per aksi, berjarak 30 detik.
bool RetryDue(const int fails, const datetime lastFail, const datetime now)
  {
   if(fails >= SDB_MODIFY_MAX_ATTEMPTS)
      return false;
   return fails == 0 || now - lastFail >= SDB_MODIFY_COOLDOWN_SEC;
  }

#endif // SDB_POSITION_POSITIONMATH_MQH
