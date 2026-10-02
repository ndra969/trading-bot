//+------------------------------------------------------------------+
//| TestPaTrigger.mqh — CPaTrigger dengan data terminal: hitung sekali
//| per bar LTF, hasil sama dengan DetectPattern atas salinan bar yang
//| sama (spec 12 Req 3; design §3.2; TC-PAX-01..02).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTPATRIGGER_MQH
#define SDB_SUITES_TESTPATRIGGER_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Strategies/PaTrigger.mqh>

void RunTestPaTrigger()
  {
   TfBeginSuite("PaTrigger");
   CPaTrigger trig;
   trig.Init(_Symbol, PERIOD_M15);
   bool first = trig.OnTick();
   bool second = trig.OnTick();
   AssertTrue("TC-PAX-01", "OnTick dua kali di bar M15 yang sama: true lalu false, Ready",
              first && !second && trig.Ready() && trig.LastBarTime() == iTime(_Symbol, PERIOD_M15, 1));

   MqlRates r[];
   ArraySetAsSeries(r, false);
   int got = CopyRates(_Symbol, PERIOD_M15, 1, SDB_PA_BARS, r);
   double atr[];
   bool atrOk = got == SDB_PA_BARS && AtrSeries(r, SDB_ZONE_ATR_PERIOD, atr);
   double a = atrOk ? atr[got - 1] : 0.0;
   SdbPattern expBull, expBear, gotBull, gotBear;
   DetectPattern(r, a, SDB_DIR_BULL, expBull);
   DetectPattern(r, a, SDB_DIR_BEAR, expBear);
   trig.Result(SDB_DIR_BULL, gotBull);
   trig.Result(SDB_DIR_BEAR, gotBear);
   MqlRates last;
   trig.LastBar(last);
   AssertTrue("TC-PAX-02", StringFormat("Result = DetectPattern atas CopyRates shift 1 (BULL %s, BEAR %s)", gotBull.code, gotBear.code),
              atrOk && a > 0.0 && gotBull.code == expBull.code && gotBull.score == expBull.score && gotBull.barTime == r[got - 1].time &&
              gotBear.code == expBear.code && gotBear.score == expBear.score && last.time == r[got - 1].time &&
              last.close == r[got - 1].close);
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTPATRIGGER_MQH
