//+------------------------------------------------------------------+
//| TestMarketStructure.mqh — CBarCache dan CMarketStructure dengan data
//| terminal (spec 10 Req 1, 5; design §3.2–3.3; TC-MSX-01..03).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTMARKETSTRUCTURE_MQH
#define SDB_SUITES_TESTMARKETSTRUCTURE_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Analysis/MarketStructure.mqh>

void RunTestMarketStructure()
  {
   TfBeginSuite("MarketStructure");

   CBarCache c;
   c.Init(_Symbol, PERIOD_H1, 20);
   bool first = c.Refresh();
   bool second = c.Refresh();
   MqlRates r[];
   int n = c.Copy(r);
   AssertTrue("TC-MSX-01", StringFormat("refresh pertama menyalin, kedua di bar yang sama tidak (n=%d)", n),
              first && !second && c.Ready() && n == 20 && r[19].time == iTime(_Symbol, PERIOD_H1, 1) && r[0].time < r[19].time);

   CBarCache big;
   big.Init(_Symbol, PERIOD_H4, 1000000);
   AssertTrue("TC-MSX-02", "histori kurang dari yang diminta: tidak siap", !big.Refresh() && !big.Ready());

   SdbStructureParams p;
   p.strength = 2;
   p.lookback = 100;
   p.emaPeriod = 50;
   p.slopeBars = 3;
   CMarketStructure ms;
   ms.Init(_Symbol, PERIOD_H4, PERIOD_H1, p);
   ms.OnTick();
   SdbTfAnalysis h, m;
   SdbBias b;
   ms.Htf(h);
   ms.Mtf(m);
   ms.Bias(b);
   int need = BarsNeeded(2, 100, 50, 3);
   bool enough = Bars(_Symbol, PERIOD_H4) - 1 >= need;
   bool consistent = enough ? (h.ready && h.barTime == iTime(_Symbol, PERIOD_H4, 1) && b.reason != "DATA")
                            : (!h.ready && h.reason == "data kurang" && b.dir == SDB_DIR_NONE && b.reason == "DATA");
   AssertTrue("TC-MSX-03", StringFormat("struktur H4/H1: siap sesuai histori (bar H4 %d, butuh %d, bias %d %s)",
                                        Bars(_Symbol, PERIOD_H4), need, b.dir, b.reason),
              ms.HtfTimeframe() == PERIOD_H4 && ms.MtfTimeframe() == PERIOD_H1 && consistent && !ms.OnTick());
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTMARKETSTRUCTURE_MQH
