//+------------------------------------------------------------------+
//| TestIntegration.mqh — fungsi murni penutup Fase 1 (spec 07, TC-IN-xx):
//| metrik OnTester dan penanda preset.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTINTEGRATION_MQH
#define SDB_SUITES_TESTINTEGRATION_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/App/TesterMetric.mqh>
#include <SDBot/Core/Utils.mqh>

void RunTestIntegration()
  {
   TfBeginSuite("Integration");
   AssertEq("TC-IN-01", "30R dari 100 trade, DD 10% -> 0.03", TesterMetric(30, 100, 10, 30), 0.03, 1e-12);
   AssertEq("TC-IN-02", "10 trade < minimum 30 -> 0", TesterMetric(5, 10, 10, 30), 0.0, 1e-12);
   AssertTrue("TC-IN-03", "DD 0 -> 0; -20R dari 40 trade, DD 5% -> -0.1",
              TesterMetric(30, 100, 0, 30) == 0.0 && MathAbs(TesterMetric(-20, 40, 5, 30) + 0.1) < 1e-12);
   AssertTrue("TC-IN-05", "penanda preset: sama cocok; beda tidak; kosong tidak dicek",
              PresetMatchesSymbol("EURUSDc", "EURUSDc") && !PresetMatchesSymbol("EURUSDc", "GBPUSDc") &&
              PresetMatchesSymbol("", "GBPUSDc"));
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTINTEGRATION_MQH
