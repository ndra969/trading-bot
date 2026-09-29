//+------------------------------------------------------------------+
//| TestExecution.mqh — aturan eksekusi murni (spec 04, TC-EX-xx):
//| sisi SL/TP, stops/freeze level, volume, retcode, retry, filling,
//| komentar, ID permintaan, slippage, modify SL, tutup sebagian.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTEXECUTION_MQH
#define SDB_SUITES_TESTEXECUTION_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Execution/ExecutionRules.mqh>

#define TE_PT5 0.00001
#define TE_PT3 0.001

void RunTestExecutionOrder()
  {
   AssertStrEq("TC-EX-01", "buy 1.10000 SL 1.09800 TP 1.10500 lolos",
               ValidateOrderSides(true, 1.10000, 1.09800, 1.10500), "");
   AssertStrEq("TC-EX-02", "buy dengan SL di atas harga ditolak INVALID_STOPS",
               ValidateOrderSides(true, 1.10000, 1.10100, 1.10500), SDB_REJECT_STAGE_INVALID_STOPS);
   AssertStrEq("TC-EX-03", "sell dengan TP di atas harga ditolak INVALID_STOPS",
               ValidateOrderSides(false, 1.10000, 1.10300, 1.10200), SDB_REJECT_STAGE_INVALID_STOPS);
   AssertTrue("TC-EX-04", "SL 0 atau TP 0 ditolak INVALID_STOPS (buy dan sell)",
              ValidateOrderSides(true, 1.10000, 0.0, 1.10500) == SDB_REJECT_STAGE_INVALID_STOPS &&
              ValidateOrderSides(true, 1.10000, 1.09800, 0.0) == SDB_REJECT_STAGE_INVALID_STOPS &&
              ValidateOrderSides(false, 1.10000, 0.0, 1.09500) == SDB_REJECT_STAGE_INVALID_STOPS);
   AssertStrEq("TC-EX-04b", "sell 1.10000 SL 1.10200 TP 1.09500 lolos",
               ValidateOrderSides(false, 1.10000, 1.10200, 1.09500), "");

   string why;
   AssertTrue("TC-EX-05", "SL 5 point, spread 8, stops 0: ditolak",
              !CheckStops(1.10000, 1.09995, 1.10500, 0, 0, 8, TE_PT5, why) && why != "");
   AssertTrue("TC-EX-06", "SL 100 point, spread 8, stops 0: lolos",
              CheckStops(1.10000, 1.09900, 1.10500, 0, 0, 8, TE_PT5, why));
   AssertTrue("TC-EX-07", "SL 20 point, stops 20 + spread 8 = 28: ditolak",
              !CheckStops(1.10000, 1.09980, 1.10500, 20, 0, 8, TE_PT5, why));
   AssertTrue("TC-EX-07b", "SL tepat 28 point, stops 20 + spread 8: lolos (batas)",
              CheckStops(1.10000, 1.09972, 1.10500, 20, 0, 8, TE_PT5, why));
   AssertTrue("TC-EX-08", "TP 3 point dengan freeze 5 (stops 0, spread 0): ditolak",
              !CheckStops(1.10000, 1.09800, 1.10003, 0, 5, 0, TE_PT5, why));
   AssertTrue("TC-EX-09", "JPY 161.500 SL 161.450 (50 point) spread 35: lolos",
              CheckStops(161.500, 161.450, 161.600, 0, 0, 35, TE_PT3, why));
   AssertTrue("TC-EX-09b", "JPY 161.500 SL 161.470 (30 point) spread 35: ditolak",
              !CheckStops(161.500, 161.470, 161.600, 0, 0, 35, TE_PT3, why));

   AssertTrue("TC-EX-10", "volume 0.015 dengan step 0.01 ditolak",
              !CheckVolume(0.015, 0.01, 100.0, 0.01, 0.0, 0.0, why) && why != "");
   AssertTrue("TC-EX-11", "volume 0.10 + posisi 0.15 melewati limit 0.20: ditolak",
              !CheckVolume(0.10, 0.01, 100.0, 0.01, 0.20, 0.15, why));
   AssertTrue("TC-EX-11b", "0.005 ditolak; 0.01 lolos; 200 (> max 100) ditolak; 0.07 lolos (floating point)",
              !CheckVolume(0.005, 0.01, 100.0, 0.01, 0.0, 0.0, why) &&
              CheckVolume(0.01, 0.01, 100.0, 0.01, 0.0, 0.0, why) &&
              !CheckVolume(200.0, 0.01, 100.0, 0.01, 0.0, 0.0, why) &&
              CheckVolume(0.07, 0.01, 100.0, 0.01, 0.0, 0.0, why));
   AssertTrue("TC-EX-11c", "limit 0 = tanpa batas; tepat di limit lolos",
              CheckVolume(5.0, 0.01, 100.0, 0.01, 0.0, 50.0, why) &&
              CheckVolume(0.05, 0.01, 100.0, 0.01, 0.20, 0.15, why));
  }

void RunTestExecution()
  {
   TfBeginSuite("Execution");
   RunTestExecutionOrder();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTEXECUTION_MQH
