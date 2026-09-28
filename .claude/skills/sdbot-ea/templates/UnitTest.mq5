//+------------------------------------------------------------------+
//| SDBotTests/Test<Area>.mq5 — unit tests for pure functions in <Area>
//| Run: drag onto any chart; Experts tab must print "ALL PASS".
//+------------------------------------------------------------------+
#property script_show_inputs false

#include <SDBot/Core/Utils.mqh>

int g_fail = 0;

void AssertEq(const double actual, const double expected, const string name)
  {
   if(MathAbs(actual - expected) > 1e-8)
     {
      g_fail++;
      PrintFormat("FAIL %s: %.10f != %.10f", name, actual, expected);
     }
  }

void AssertTrue(const bool cond, const string name)
  {
   if(!cond)
     {
      g_fail++;
      PrintFormat("FAIL %s", name);
     }
  }

void OnStart()
  {
   // One assert per behaviour; name states the rule from the PRD.
   AssertEq(RoundLotDown(0.0379, 0.01), 0.03, "lot dibulatkan ke bawah");
   AssertEq(ProfitInR(1.1050, 1.1000, 1.0950), 1.0, "profit 1R");

   Print(g_fail == 0 ? "ALL PASS" : "FAILED: " + IntegerToString(g_fail));
  }
