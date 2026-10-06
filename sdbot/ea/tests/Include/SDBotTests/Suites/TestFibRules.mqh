//+------------------------------------------------------------------+
//| TestFibRules.mqh — skor Fibonacci sebagai fungsi murni (spec 18
//| design §3.1, §6.1; TC-FIB-01..11). Leg dari batas jauh zona ke
//| ekstrem bar MTF sesudah candle swing; skor dari level terdekat.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTFIBRULES_MQH
#define SDB_SUITES_TESTFIBRULES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/InputRules.mqh>
#include <SDBot/Strategies/FibRules.mqh>

// Bar MTF: candle swing di indeks 1, high/low sesudahnya diatur per kasus.
void TfbRates(MqlRates &r[], const double &highs[], const double &lows[])
  {
   int n = ArraySize(highs);
   ArrayResize(r, n);
   for(int i = 0; i < n; i++)
     {
      ZeroMemory(r[i]);
      r[i].time = D'2026.06.01 00:00' + i * 3600;
      r[i].high = highs[i];
      r[i].low = lows[i];
      r[i].open = (highs[i] + lows[i]) / 2.0;
      r[i].close = r[i].open;
     }
  }

SdbZone TfbZone(const bool demand, const double distal, const double proximal, const double atr, const int swingIdx = 1)
  {
   SdbZone z;
   ZeroMemory(z);
   z.demand = demand;
   z.distal = distal;
   z.proximal = proximal;
   z.atr = atr;
   z.swingIdx = swingIdx;
   z.status = SDB_ZONE_FRESH;
   return z;
  }

int TfbScoreAt(const double ratio, double &level)
  {
   double dist;
   return FibScore(ratio, level, dist);
  }

void RunTestFibRules()
  {
   TfBeginSuite("FibRules");
   MqlRates r[];
   SdbFibResult res;

   // TC-FIB-01: demand 1.1000 -> high 1.1100, batas dekat 1.1050 = rasio 0.5
   double hiD[] = {1.1030, 1.1020, 1.1060, 1.1100, 1.1080, 1.1060};
   double loD[] = {1.1010, 1.1000, 1.1030, 1.1070, 1.1050, 1.1040};
   TfbRates(r, hiD, loD);
   SdbZone zd = TfbZone(true, 1.1000, 1.1050, 0.0040);
   FibEvaluate(r, zd, 1.5, 100, res);
   AssertTrue("TC-FIB-01", StringFormat("demand: legEnd %.4f rasio %.3f level %.3f skor %d '%s'", res.legEnd, res.ratio, res.level, res.score, res.reason),
              MathAbs(res.legEnd - 1.1100) < 1e-9 && MathAbs(res.ratio - 0.5) < 1e-9 && MathAbs(res.level - 0.5) < 1e-9 && res.score == 15 &&
              res.reason == "");

   // TC-FIB-02: supply cerminan (1.1100 -> low 1.1000, batas dekat 1.1050)
   double hiS[] = {1.1090, 1.1100, 1.1070, 1.1030, 1.1050, 1.1060};
   double loS[] = {1.1070, 1.1080, 1.1040, 1.1000, 1.1020, 1.1030};
   TfbRates(r, hiS, loS);
   SdbZone zs = TfbZone(false, 1.1100, 1.1050, 0.0040);
   FibEvaluate(r, zs, 1.5, 100, res);
   AssertTrue("TC-FIB-02", StringFormat("supply: legEnd %.4f rasio %.3f skor %d", res.legEnd, res.ratio, res.score),
              MathAbs(res.legEnd - 1.1000) < 1e-9 && MathAbs(res.ratio - 0.5) < 1e-9 && res.score == 15);

   double level = 0.0;
   int s055 = TfbScoreAt(0.55, level);
   AssertTrue("TC-FIB-03", StringFormat("bug bot Python: rasio 0.55 -> level %.3f skor %d (harus 0.5, 0)", level, s055),
              MathAbs(level - 0.5) < 1e-9 && s055 == 0);

   double l1, l2, l3;
   int a = TfbScoreAt(0.40, l1), b = TfbScoreAt(0.63, l2), c = TfbScoreAt(0.80, l3);
   AssertTrue("TC-FIB-04", StringFormat("linear: 0.40->%.3f %d, 0.63->%.3f %d, 0.80->%.3f %d (5, 11, 6)", l1, a, l2, b, l3, c),
              MathAbs(l1 - 0.382) < 1e-9 && a == 5 && MathAbs(l2 - 0.618) < 1e-9 && b == 11 && MathAbs(l3 - 0.786) < 1e-9 && c == 6);

   int t = TfbScoreAt(0.559, level);
   AssertTrue("TC-FIB-05", StringFormat("tie 0.559 -> level lebih dalam %.3f (skor %d)", level, t), MathAbs(level - 0.618) < 1e-9);

   double lx;
   AssertTrue("TC-FIB-06", "rasio 0.20 dan 1.05 (di luar leg) skor 0", TfbScoreAt(0.20, lx) == 0 && TfbScoreAt(1.05, lx) == 0);

   SdbZone zshort = TfbZone(true, 1.1000, 1.1050, 0.0080);   // leg 0.0100 = 1.25 ATR
   TfbRates(r, hiD, loD);
   FibEvaluate(r, zshort, 1.5, 100, res);
   AssertTrue("TC-FIB-07", StringFormat("leg 1.25 ATR: skor %d '%s'", res.score, res.reason), res.score == 0 && res.reason == "leg pendek");

   // EC-02: high baru 1.1150 sesudah zona, lalu kembali
   double hiN[] = {1.1030, 1.1020, 1.1100, 1.1150, 1.1090, 1.1070};
   TfbRates(r, hiN, loD);
   FibEvaluate(r, zd, 1.5, 100, res);
   AssertTrue("TC-FIB-08", StringFormat("high baru: legEnd %.4f rasio %.3f", res.legEnd, res.ratio),
              MathAbs(res.legEnd - 1.1150) < 1e-9 && MathAbs(res.ratio - 100.0 / 150.0) < 1e-9);

   // EC-05: USDJPY dan BTC dengan proporsi sama dengan TC-FIB-01
   double hiJ[] = {157.380, 157.320, 157.560, 157.800, 157.680, 157.560};
   double loJ[] = {157.260, 157.200, 157.380, 157.620, 157.500, 157.440};
   TfbRates(r, hiJ, loJ);
   SdbFibResult rj;
   FibEvaluate(r, TfbZone(true, 157.200, 157.500, 0.240), 1.5, 100, rj);
   double hiB[] = {60900.0, 60600.0, 61800.0, 63000.0, 62400.0, 61800.0};
   double loB[] = {60300.0, 60000.0, 60900.0, 62100.0, 61500.0, 61200.0};
   TfbRates(r, hiB, loB);
   SdbFibResult rb;
   FibEvaluate(r, TfbZone(true, 60000.0, 61500.0, 1200.0), 1.5, 100, rb);
   AssertTrue("TC-FIB-09", StringFormat("JPY rasio %.3f skor %d; BTC rasio %.3f skor %d", rj.ratio, rj.score, rb.ratio, rb.score),
              MathAbs(rj.ratio - 0.5) < 1e-9 && rj.score == 15 && MathAbs(rb.ratio - 0.5) < 1e-9 && rb.score == 15);

   TfbRates(r, hiD, loD);
   double end;
   bool okIdx = FibLegEnd(r, TfbZone(true, 1.1000, 1.1050, 0.0040, 99), end);
   FibEvaluate(r, TfbZone(true, 1.1000, 1.1050, 0.0040, 99), 1.5, 100, res);
   AssertTrue("TC-FIB-10", StringFormat("swingIdx di luar array: %s, skor %d '%s'", okIdx ? "true" : "false", res.score, res.reason),
              !okIdx && res.score == 0 && res.reason == "data kurang");

   // TC-FIB-12 (keputusan A, 2026-10-06): zona di tengah impuls. Leg dari low terendah sebelum swing zona (1.0900)
   // ke high sesudahnya (1.1100); batas dekat 1.1000 = rasio 0.5.
   double hiM[] = {1.0950, 1.1010, 1.1050, 1.1100, 1.1080};
   double loM[] = {1.0900, 1.0980, 1.1000, 1.1060, 1.1040};
   TfbRates(r, hiM, loM);
   FibEvaluate(r, TfbZone(true, 1.0980, 1.1000, 0.0040), 1.5, 100, res);
   AssertTrue("TC-FIB-12", StringFormat("zona tengah impuls: leg %.4f->%.4f rasio %.3f skor %d", res.legStart, res.legEnd, res.ratio, res.score),
              MathAbs(res.legStart - 1.0900) < 1e-9 && MathAbs(res.legEnd - 1.1100) < 1e-9 && MathAbs(res.ratio - 0.5) < 1e-9 && res.score == 15);

   // TC-FIB-13: zona di asal impuls (low zona = low terendah) -> rasio 0.9, skor 0; low di luar jendela lookback diabaikan.
   double hiO[] = {1.0950, 1.1020, 1.1060, 1.1100, 1.1080};
   double loO[] = {1.0800, 1.1000, 1.1030, 1.1060, 1.1040};
   TfbRates(r, hiO, loO);
   SdbFibResult ro;
   FibEvaluate(r, TfbZone(true, 1.1000, 1.1010, 0.0040), 1.5, 0, ro);   // lookback 0: hanya candle swing
   SdbFibResult rw;
   FibEvaluate(r, TfbZone(true, 1.1000, 1.1010, 0.0040), 1.5, 1, rw);   // lookback 1: low 1.0800 ikut
   AssertTrue("TC-FIB-13", StringFormat("asal impuls: rasio %.3f skor %d; lookback 1: awal %.4f rasio %.3f", ro.ratio, ro.score, rw.legStart, rw.ratio),
              MathAbs(ro.ratio - 0.9) < 1e-9 && ro.score == 0 && MathAbs(rw.legStart - 1.0800) < 1e-9);

   string err;
   InputValues v = DefaultInputValues();
   bool def = v.scoreFibMode == SDB_COMPONENT_SHADOW && ValidateInputValues(v, false, err);
   v.scoreFibMode = (ENUM_SDB_COMPONENT_MODE)3;
   err = "";
   bool bad = !ValidateInputValues(v, false, err) && StringFind(err, "InpScoreFibMode") >= 0;
   AssertTrue("TC-FIB-11", "input InpScoreFibMode: default SHADOW lolos; 3 ditolak dengan nama", def && bad);
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTFIBRULES_MQH
