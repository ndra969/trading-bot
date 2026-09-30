//+------------------------------------------------------------------+
//| TestRiskState.mqh — CRiskState di Global Variables (spec 05,
//| TC-RS-xx): nilai awal aman, compare-and-set antar-instance, puncak,
//| operasi saldo, reset. Dua objek dengan login sama = dua instance.
//| Prefix SDBTEST dan login palsu agar status akun sungguhan aman.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTRISKSTATE_MQH
#define SDB_SUITES_TESTRISKSTATE_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Risk/RiskState.mqh>

#define TRS_PREFIX "SDBTEST"
#define TRS_LOGIN  990001
#define TRS_DAY    D'2026.10.01 00:00:00'

string TrsFullPrefix() { return TRS_PREFIX + "_" + IntegerToString(TRS_LOGIN) + "_"; }

void RunTestRiskStateInit(CState &sa, CState &sb)
  {
   CRiskState a;
   bool ok = a.Init(GetPointer(sa), 2026091901, 1000.0, 990.0, TRS_DAY + 3600);
   bool fresh = a.WasFresh();
   CRiskState b;
   b.Init(GetPointer(sb), 2026091902, 5000.0, 5000.0, TRS_DAY + 7200);
   AssertTrue("TC-RS-01", "GV kosong: nilai awal aman (puncak = equity, awal hari = balance, level NORMAL); Init kedua tidak fresh",
              ok && fresh && !b.WasFresh() && a.PeakEquity() == 1000.0 && !a.IsStopped() && !a.IsDailyPaused() &&
              !a.IsLotReduced() && a.DdLevel() == SDB_DD_NORMAL && a.DayStartBalance() == 990.0 &&
              a.DayStartDate() == TRS_DAY && b.PeakEquity() == 1000.0 && a.BalanceBaselineNeeded());
  }

void RunTestRiskStateCas(CState &sa, CState &sb)
  {
   CRiskState a, b;
   a.Init(GetPointer(sa), 2026091901, 1000.0, 1000.0, TRS_DAY);
   b.Init(GetPointer(sb), 2026091902, 1000.0, 1000.0, TRS_DAY);
   datetime next = TRS_DAY + 86400;
   bool wa = a.TryClaimNewDay(TRS_DAY, next, 1111.0);
   bool wb = b.TryClaimNewDay(TRS_DAY, next, 2222.0);
   AssertTrue("TC-RS-02", "pergantian hari: tepat satu pemenang, awal hari = balance pemenang",
              wa != wb && a.DayStartDate() == next && b.DayStartBalance() == (wa ? 1111.0 : 2222.0));

   ulong last = a.LastBalanceDeal();
   bool da = a.TryClaimBalanceDeal(last, 500);
   bool db = b.TryClaimBalanceDeal(last, 500);
   AssertTrue("TC-RS-03", "deal saldo sama: tepat satu pemenang", da != db && b.LastBalanceDeal() == 500);

   bool la = a.TryMoveDdLevel(SDB_DD_NORMAL, SDB_DD_INFO);
   bool lb = b.TryMoveDdLevel(SDB_DD_NORMAL, SDB_DD_INFO);
   AssertTrue("TC-RS-04", "transisi level NORMAL->INFO: tepat satu pemenang", la != lb && b.DdLevel() == SDB_DD_INFO);

   a.SetStopped(true);
   bool seen = b.IsStopped();
   a.SetStopped(false);
   AssertTrue("TC-RS-05", "STOPPED disetel A langsung terbaca B tanpa Init ulang", seen && !b.IsStopped());
  }

void RunTestRiskStateValues(CState &sa, CState &sb)
  {
   CRiskState a, b;
   a.Init(GetPointer(sa), 2026091901, 1000.0, 1000.0, TRS_DAY);
   b.Init(GetPointer(sb), 2026091902, 1000.0, 1000.0, TRS_DAY);
   bool r900 = a.RaisePeak(900.0);
   double p1 = a.PeakEquity();
   bool r1100 = a.RaisePeak(1100.0);
   AssertTrue("TC-RS-06", "puncak hanya naik: 900 tidak mengubah 1000, 1100 menaikkan",
              !r900 && p1 == 1000.0 && r1100 && b.PeakEquity() == 1100.0);

   double day0 = a.DayStartBalance();
   bool adj = a.AdjustPeakAndDayStart(-200.0);
   AssertTrue("TC-RS-07", "operasi saldo -200: puncak dan awal hari turun 200",
              adj && a.PeakEquity() == 900.0 && a.DayStartBalance() == day0 - 200.0);

   a.SetStopped(true);
   a.SetLotReduced(true);
   a.TryMoveDdLevel(a.DdLevel(), SDB_DD_STOP);
   a.ResetAfterEmergency(950.0);
   AssertTrue("TC-RS-08", "reset emergency: STOPPED 0, LOT_REDUCED 0, level NORMAL, puncak 950",
              !b.IsStopped() && !b.IsLotReduced() && b.DdLevel() == SDB_DD_NORMAL && b.PeakEquity() == 950.0);

   a.SetResetInputLastSeen(true);
   b.SetResetInputLastSeen(false);
   AssertTrue("TC-RS-09", "RESET_SEEN per magic: A true, B false, tidak saling menimpa",
              a.ResetInputLastSeen() && !b.ResetInputLastSeen());
  }

void RunTestRiskState()
  {
   TfBeginSuite("RiskState");
   GlobalVariablesDeleteAll(TrsFullPrefix());
   CState sa, sb;
   sa.Init(TRS_PREFIX, TRS_LOGIN);
   sb.Init(TRS_PREFIX, TRS_LOGIN);
   RunTestRiskStateInit(sa, sb);
   GlobalVariablesDeleteAll(TrsFullPrefix());
   RunTestRiskStateCas(sa, sb);
   GlobalVariablesDeleteAll(TrsFullPrefix());
   RunTestRiskStateValues(sa, sb);
   GlobalVariablesDeleteAll(TrsFullPrefix());
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTRISKSTATE_MQH
