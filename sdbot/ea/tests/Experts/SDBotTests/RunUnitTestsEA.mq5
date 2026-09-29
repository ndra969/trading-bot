//+------------------------------------------------------------------+
//| RunUnitTestsEA.mq5 — entry point runner otomatis (Strategy Tester):
//| menjalankan semua suite di OnInit, menulis hasil ke Common\Files,
//| lalu melepas diri agar tester langsung selesai.
//+------------------------------------------------------------------+
#property version "1.00"

#include <SDBotTests/AllSuites.mqh>

input string InpTestRunId = "manual";

int OnInit()
  {
   TfBeginRun(InpTestRunId);
   RunAllSuites();
   TfEndRun();
   ExpertRemove();
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
  }
