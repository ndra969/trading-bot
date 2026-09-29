//+------------------------------------------------------------------+
//| RunUnitTests.mq5 — jalankan semua suite unit test SDBot secara manual:
//| seret ke chart mana pun, hasil tampil di tab Experts dan ditulis ke
//| Common\Files\sdbot_test_<InpTestRunId>.txt.
//+------------------------------------------------------------------+
#property version "1.00"
#property script_show_inputs

#include <SDBotTests/AllSuites.mqh>

input string InpTestRunId = "manual";

void OnStart()
  {
   TfBeginRun(InpTestRunId);
   RunAllSuites();
   int failed = TfEndRun();
   Print(failed == 0 ? "ALL PASS" : "FAILED: " + IntegerToString(failed));
  }
