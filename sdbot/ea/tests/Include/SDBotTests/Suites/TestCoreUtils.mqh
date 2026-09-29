//+------------------------------------------------------------------+
//| TestCoreUtils.mqh — input dan aturan validasinya (spec 02 Req 1).
//| Bagian util/log (TC-CU-09..15) ditambahkan di task 3.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTCOREUTILS_MQH
#define SDB_SUITES_TESTCOREUTILS_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/Inputs.mqh>

bool CuContains(const string text, const string part)
  {
   return StringFind(text, part) >= 0;
  }

// Validasi satu set input; kembalikan hasil dan pesan kesalahannya.
bool CuValidate(const InputValues &v, string &errors)
  {
   return ValidateInputValues(v, errors);
  }

void RunTestCoreUtilsInputs()
  {
   string err;
   InputValues v = DefaultInputValues();

   AssertTrue("TC-CU-01", "semua default lolos validasi", CuValidate(v, err));

   // Default di Inputs.mqh dan DefaultInputValues() berasal dari konstanta yang sama.
   InputValues cur = CurrentInputs();
   AssertTrue("TC-CU-01b", "CurrentInputs() dengan input default sama dengan DefaultInputValues()",
              cur.magic == v.magic && cur.riskPerTradePct == v.riskPerTradePct &&
              cur.maxOpenRiskPct == v.maxOpenRiskPct && cur.dailyLossPct == v.dailyLossPct &&
              cur.ddReducePct == v.ddReducePct && cur.ddStopPct == v.ddStopPct &&
              cur.breakevenR == v.breakevenR && cur.breakevenBufferPoints == v.breakevenBufferPoints &&
              cur.partialR == v.partialR && cur.partialPct == v.partialPct &&
              cur.trailAtrPeriod == v.trailAtrPeriod && cur.trailAtrMult == v.trailAtrMult);
   AssertIntEq("TC-CU-01c", "magic default di blok SDBot", v.magic, 2026091901);

   v = DefaultInputValues();
   v.riskPerTradePct = 1.5;
   bool ok = CuValidate(v, err);
   AssertTrue("TC-CU-02", "risk per trade 1.5 ditolak dan pesan menyebut input serta batas 1.0",
              !ok && CuContains(err, "InpRiskPerTradePct") && CuContains(err, "1.0"));

   v = DefaultInputValues();
   v.riskPerTradePct = 0.0;
   AssertTrue("TC-CU-03", "risk per trade 0 ditolak", !CuValidate(v, err) && CuContains(err, "InpRiskPerTradePct"));

   v = DefaultInputValues();
   v.maxOpenRiskPct = 0.3;
   ok = CuValidate(v, err);
   AssertTrue("TC-CU-04", "max open risk < risk per trade ditolak (hubungan antar-input)",
              !ok && CuContains(err, "InpMaxOpenRiskPct") && CuContains(err, "InpRiskPerTradePct"));

   v = DefaultInputValues();
   v.breakevenR = 1.5;
   v.partialR = 1.5;
   ok = CuValidate(v, err);
   AssertTrue("TC-CU-05", "BE R >= partial R ditolak", !ok && CuContains(err, "InpBreakevenR") && CuContains(err, "InpPartialR"));

   v = DefaultInputValues();
   v.ddReducePct = 15.0;
   v.ddStopPct = 10.0;
   ok = CuValidate(v, err);
   AssertTrue("TC-CU-06", "DD reduce >= DD stop ditolak", !ok && CuContains(err, "InpDDReducePct") && CuContains(err, "InpDDStopPct"));

   v = DefaultInputValues();
   v.partialPct = 100.0;
   AssertTrue("TC-CU-07", "partial pct 100 ditolak", !CuValidate(v, err) && CuContains(err, "InpPartialPct"));

   v = DefaultInputValues();
   v.magic = 0;
   v.riskPerTradePct = 2.0;
   ok = CuValidate(v, err);
   AssertTrue("TC-CU-08", "dua kesalahan sekaligus disebut dalam satu pesan",
              !ok && CuContains(err, "InpMagicNumber") && CuContains(err, "InpRiskPerTradePct"));

   v = DefaultInputValues();
   v.magic = 2026091904;
   bool okLow = CuValidate(v, err);
   v.magic = 2026091999;
   bool okHigh = CuValidate(v, err);
   AssertTrue("TC-CU-08b", "magic 2026091904 dan 2026091999 lolos", okLow && okHigh);

   long bad[] = {20260919, 2026092000, 2026091900};
   bool allRejected = true;
   bool allMention = true;
   for(int i = 0; i < ArraySize(bad); i++)
     {
      v = DefaultInputValues();
      v.magic = bad[i];
      if(CuValidate(v, err))
         allRejected = false;
      if(!CuContains(err, "2026091901") || !CuContains(err, "2026091999"))
         allMention = false;
     }
   AssertTrue("TC-CU-08c", "magic 20260919 / 2026092000 / 2026091900 ditolak dengan rentang yang benar",
              allRejected && allMention);

   v = DefaultInputValues();
   v.trailAtrPeriod = 1;
   v.trailAtrMult = 0.0;
   v.breakevenBufferPoints = -1;
   v.dailyLossPct = 11.0;
   ok = CuValidate(v, err);
   AssertTrue("TC-CU-08d", "batas ATR, buffer BE, dan rugi harian ditegakkan",
              !ok && CuContains(err, "InpTrailATRPeriod") && CuContains(err, "InpTrailATRMult") &&
              CuContains(err, "InpBreakevenBufferPoints") && CuContains(err, "InpDailyLossPct"));
  }

void RunTestCoreUtils()
  {
   TfBeginSuite("CoreUtils");
   RunTestCoreUtilsInputs();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTCOREUTILS_MQH
