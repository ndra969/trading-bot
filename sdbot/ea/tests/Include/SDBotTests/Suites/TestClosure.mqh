//+------------------------------------------------------------------+
//| TestClosure.mqh — aturan closure murni (spec 06, TC-CL-xx): alasan
//| tutup, R hasil, MFE/MAE, pemetaan enum deal MT5 ke teks DB.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTCLOSURE_MQH
#define SDB_SUITES_TESTCLOSURE_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Position/ClosureRules.mqh>

#define TCL_PT5 0.00001

string TclSlReason(const bool isBuy, const double entry, const double be, const double level)
  {
   return MapCloseReason(DEAL_REASON_SL, isBuy, entry, level, be, 4, TCL_PT5, true);
  }

void RunTestClosureReason()
  {
   AssertStrEq("TC-CL-01", "deal TP -> TP", MapCloseReason(DEAL_REASON_TP, true, 1.1, 1.105, 0, 4, TCL_PT5, true), SDB_CLOSE_REASON_TP);
   AssertStrEq("TC-CL-02", "SL buy, level 1.09800 di bawah harga buka -> SL", TclSlReason(true, 1.10000, 1.10010, 1.09800), SDB_CLOSE_REASON_SL);
   AssertStrEq("TC-CL-03", "SL buy, titik BE 1.10010, level 1.10011 (toleransi 4) -> BE_STOP",
               TclSlReason(true, 1.10000, 1.10010, 1.10011), SDB_CLOSE_REASON_BE_STOP);
   AssertStrEq("TC-CL-04", "SL buy, level 1.10300 -> TRAIL_STOP", TclSlReason(true, 1.10000, 1.10010, 1.10300), SDB_CLOSE_REASON_TRAIL_STOP);
   AssertStrEq("TC-CL-05", "SL sell, titik BE 1.09990, level 1.09700 -> TRAIL_STOP",
               TclSlReason(false, 1.10000, 1.09990, 1.09700), SDB_CLOSE_REASON_TRAIL_STOP);
   AssertTrue("TC-CL-06", "CLIENT, MOBILE, WEB -> MANUAL",
              MapCloseReason(DEAL_REASON_CLIENT, true, 1.1, 1.1, 0, 4, TCL_PT5, false) == SDB_CLOSE_REASON_MANUAL &&
              MapCloseReason(DEAL_REASON_MOBILE, true, 1.1, 1.1, 0, 4, TCL_PT5, false) == SDB_CLOSE_REASON_MANUAL &&
              MapCloseReason(DEAL_REASON_WEB, true, 1.1, 1.1, 0, 4, TCL_PT5, false) == SDB_CLOSE_REASON_MANUAL);
   AssertStrEq("TC-CL-07", "SO -> STOP_OUT", MapCloseReason(DEAL_REASON_SO, true, 1.1, 1.1, 0, 4, TCL_PT5, false), SDB_CLOSE_REASON_STOP_OUT);
   AssertTrue("TC-CL-08", "EXPERT ditutup SDBot -> EA_CLOSE; EXPERT magic lain -> OTHER",
              MapCloseReason(DEAL_REASON_EXPERT, true, 1.1, 1.1, 0, 4, TCL_PT5, true) == SDB_CLOSE_REASON_EA_CLOSE &&
              MapCloseReason(DEAL_REASON_EXPERT, true, 1.1, 1.1, 0, 4, TCL_PT5, false) == SDB_CLOSE_REASON_OTHER);
  }

void RunTestClosureNumbers()
  {
   AssertEq("TC-CL-09", "net 10, risiko 5 -> 2R", ResultInR(10, 5), 2.0, 1e-12);
   AssertTrue("TC-CL-10", "risiko 0 atau NULL -> NULL", ResultInR(10, 0) == SDB_NULL_DOUBLE && ResultInR(10, SDB_NULL_DOUBLE) == SDB_NULL_DOUBLE);
   double h1[] = {1.10100, 1.10240, 1.10050};
   double l1[] = {1.09950, 1.09900, 1.10000};
   double mfe, mae;
   MfeMaeInR(true, 1.10000, 0.00200, h1, l1, mfe, mae);
   AssertTrue("TC-CL-11", StringFormat("buy: MFE 1.2, MAE 0.5 (%.4f, %.4f)", mfe, mae), MathAbs(mfe - 1.2) < 1e-9 && MathAbs(mae - 0.5) < 1e-9);
   double h2[] = {1.10050, 1.10020};
   double l2[] = {1.09900, 1.09800};
   MfeMaeInR(false, 1.10000, 0.00200, h2, l2, mfe, mae);
   AssertTrue("TC-CL-12", StringFormat("sell: MFE 1.0, MAE 0.25 (%.4f, %.4f)", mfe, mae), MathAbs(mfe - 1.0) < 1e-9 && MathAbs(mae - 0.25) < 1e-9);
   double e1[], e2[];
   MfeMaeInR(true, 1.10000, 0.00200, e1, e2, mfe, mae);
   AssertTrue("TC-CL-13", "tanpa bar M1 -> MFE/MAE NULL", mfe == SDB_NULL_DOUBLE && mae == SDB_NULL_DOUBLE);
  }

void RunTestClosureTexts()
  {
   bool entries = DealEntryText(DEAL_ENTRY_IN) == SDB_DEAL_ENTRY_IN && DealEntryText(DEAL_ENTRY_OUT) == SDB_DEAL_ENTRY_OUT &&
                  DealEntryText(DEAL_ENTRY_INOUT) == SDB_DEAL_ENTRY_INOUT && DealEntryText(DEAL_ENTRY_OUT_BY) == SDB_DEAL_ENTRY_OUT_BY;
   bool types = DealTypeText(DEAL_TYPE_BUY) == SDB_DEAL_TYPE_BUY && DealTypeText(DEAL_TYPE_SELL) == SDB_DEAL_TYPE_SELL &&
                DealTypeText(DEAL_TYPE_BALANCE) == "" && DealTypeText(DEAL_TYPE_CREDIT) == "";
   bool reasons = DealReasonText(DEAL_REASON_CLIENT) == SDB_DEAL_REASON_CLIENT && DealReasonText(DEAL_REASON_MOBILE) == SDB_DEAL_REASON_MOBILE &&
                  DealReasonText(DEAL_REASON_WEB) == SDB_DEAL_REASON_WEB && DealReasonText(DEAL_REASON_EXPERT) == SDB_DEAL_REASON_EXPERT &&
                  DealReasonText(DEAL_REASON_SL) == SDB_DEAL_REASON_SL && DealReasonText(DEAL_REASON_TP) == SDB_DEAL_REASON_TP &&
                  DealReasonText(DEAL_REASON_SO) == SDB_DEAL_REASON_SO && DealReasonText(DEAL_REASON_ROLLOVER) == SDB_DEAL_REASON_ROLLOVER &&
                  DealReasonText(DEAL_REASON_VMARGIN) == SDB_DEAL_REASON_VMARGIN && DealReasonText(DEAL_REASON_SPLIT) == SDB_DEAL_REASON_SPLIT;
   AssertTrue("TC-CL-14", StringFormat("teks enum deal: entry=%s tipe=%s alasan=%s", entries ? "ok" : "salah", types ? "ok" : "salah",
                                       reasons ? "ok" : "salah"), entries && types && reasons);
  }

void RunTestClosure()
  {
   TfBeginSuite("Closure");
   RunTestClosureReason();
   RunTestClosureNumbers();
   RunTestClosureTexts();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTCLOSURE_MQH
