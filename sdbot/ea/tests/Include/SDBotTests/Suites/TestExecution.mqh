//+------------------------------------------------------------------+
//| TestExecution.mqh — aturan eksekusi murni (spec 04, TC-EX-xx):
//| sisi SL/TP, stops/freeze level, volume, retcode, retry, filling,
//| komentar, ID permintaan, slippage, modify SL, tutup sebagian.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTEXECUTION_MQH
#define SDB_SUITES_TESTEXECUTION_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Execution/ExecutionRules.mqh>
#include <SDBot/Execution/Executor.mqh>   // dikompilasi di sini; perilakunya diuji di TestApp dan skenario

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

void RunTestExecutionBroker()
  {
   AssertIntEq("TC-EX-12", "filling FOK+IOC -> FOK", PickFillingMode(SYMBOL_FILLING_FOK | SYMBOL_FILLING_IOC), ORDER_FILLING_FOK);
   AssertIntEq("TC-EX-13", "filling IOC saja -> IOC", PickFillingMode(SYMBOL_FILLING_IOC), ORDER_FILLING_IOC);
   AssertIntEq("TC-EX-14", "filling 0 -> RETURN", PickFillingMode(0), ORDER_FILLING_RETURN);

   uint rc[] = {TRADE_RETCODE_DONE, TRADE_RETCODE_PLACED, TRADE_RETCODE_DONE_PARTIAL, TRADE_RETCODE_NO_CHANGES,
                TRADE_RETCODE_REQUOTE, TRADE_RETCODE_PRICE_CHANGED, TRADE_RETCODE_PRICE_OFF,
                TRADE_RETCODE_TOO_MANY_REQUESTS, TRADE_RETCODE_LOCKED, TRADE_RETCODE_TIMEOUT,
                TRADE_RETCODE_CONNECTION, TRADE_RETCODE_ERROR, 0, TRADE_RETCODE_POSITION_CLOSED,
                TRADE_RETCODE_MARKET_CLOSED, TRADE_RETCODE_NO_MONEY, TRADE_RETCODE_INVALID_VOLUME,
                TRADE_RETCODE_INVALID_STOPS, TRADE_RETCODE_INVALID_FILL, TRADE_RETCODE_TRADE_DISABLED,
                TRADE_RETCODE_LIMIT_VOLUME, TRADE_RETCODE_REJECT};
   ENUM_SDB_RETCODE_CLASS cls[] = {SDB_RC_SUCCESS, SDB_RC_SUCCESS, SDB_RC_SUCCESS, SDB_RC_NO_CHANGES,
                                   SDB_RC_TRANSIENT, SDB_RC_TRANSIENT, SDB_RC_TRANSIENT, SDB_RC_TRANSIENT, SDB_RC_TRANSIENT,
                                   SDB_RC_AMBIGUOUS, SDB_RC_AMBIGUOUS, SDB_RC_AMBIGUOUS, SDB_RC_AMBIGUOUS,
                                   SDB_RC_POSITION_GONE, SDB_RC_MARKET_CLOSED, SDB_RC_PERMANENT, SDB_RC_PERMANENT,
                                   SDB_RC_PERMANENT, SDB_RC_PERMANENT, SDB_RC_PERMANENT, SDB_RC_PERMANENT, SDB_RC_PERMANENT};
   string wrong = "";
   for(int i = 0; i < ArraySize(rc); i++)
      if(ClassifyRetcode(rc[i]) != cls[i])
         wrong += IntegerToString(rc[i]) + " ";
   AssertStrEq("TC-EX-15", "22 retcode masuk kelas sesuai tabel design §4.1 (daftar yang salah)", wrong, "");

   AssertIntEq("TC-EX-28", "AMBIGUOUS, attempt 1, ID ditemukan -> SUCCEED", NextStep(SDB_RC_AMBIGUOUS, 1, true), SDB_STEP_SUCCEED);
   AssertIntEq("TC-EX-29", "AMBIGUOUS, attempt 1, tidak ditemukan -> RETRY", NextStep(SDB_RC_AMBIGUOUS, 1, false), SDB_STEP_RETRY);
   AssertTrue("TC-EX-30", "TRANSIENT: attempt 3 -> RETRY (ulangan ke-3), attempt 4 -> GIVE_UP",
              NextStep(SDB_RC_TRANSIENT, 3, false) == SDB_STEP_RETRY && NextStep(SDB_RC_TRANSIENT, 4, false) == SDB_STEP_GIVE_UP);
   AssertIntEq("TC-EX-31", "PERMANENT, attempt 1 -> GIVE_UP", NextStep(SDB_RC_PERMANENT, 1, false), SDB_STEP_GIVE_UP);
   AssertTrue("TC-EX-32", "NO_CHANGES -> SUCCEED; POSITION_GONE -> GONE; SUCCESS -> SUCCEED",
              NextStep(SDB_RC_NO_CHANGES, 1, false) == SDB_STEP_SUCCEED &&
              NextStep(SDB_RC_POSITION_GONE, 1, false) == SDB_STEP_GONE &&
              NextStep(SDB_RC_SUCCESS, 2, false) == SDB_STEP_SUCCEED);
   // TC-EX-33 (temuan backtest dasar spec 13): pasar tutup bukan kegagalan; ditunda ke tick berikutnya tanpa retry beruntun.
   AssertTrue("TC-EX-33", "MARKET_CLOSED attempt 1 dan 4 -> DEFER",
              NextStep(SDB_RC_MARKET_CLOSED, 1, false) == SDB_STEP_DEFER && NextStep(SDB_RC_MARKET_CLOSED, 4, false) == SDB_STEP_DEFER);
  }

void RunTestExecutionComment()
  {
   AssertStrEq("TC-EX-16", "komentar 5 digit", BuildOrderComment(1.08234, 5, "k3f9"), "SDB|1.08234|k3f9");
   string jpy = BuildOrderComment(161.234, 3, "zz00");
   AssertTrue("TC-EX-17", "komentar JPY 3 digit, panjang <= 31", jpy == "SDB|161.234|zz00" && StringLen(jpy) <= SDB_COMMENT_MAX_LEN);

   double sl = 0;
   string id = "";
   bool ok = ParseOrderComment("SDB|1.08234|k3f9", sl, id);
   AssertTrue("TC-EX-18", "parse komentar valid: SL dan ID benar", ok && MathAbs(sl - 1.08234) < 1e-9 && id == "k3f9");

   string bad[] = {"", "SDB|", "SDB|abc|k3f9", "[sl 1.08234]", "SDB|1.08234", "SDB|1.08234|k3", "SDB|1.08234|k3f9x",
                   "SDB|1.08234|K3F9", "SDB|0|k3f9", "SDB|1.08.234|k3f9", "XDB|1.08234|k3f9"};
   string accepted = "";
   for(int i = 0; i < ArraySize(bad); i++)
      if(ParseOrderComment(bad[i], sl, id))
         accepted += "[" + bad[i] + "] ";
   AssertStrEq("TC-EX-19", "komentar tidak valid/diubah broker ditolak (daftar yang lolos)", accepted, "");

   string a = MakeRequestId(2026091900, 5);
   string b = MakeRequestId(2026091901, 5);
   AssertTrue("TC-EX-20", "magic berbeda, counter sama: ID berbeda, panjang 4", a != b && StringLen(a) == 4 && StringLen(b) == 4);
   AssertTrue("TC-EX-20b", "counter 1 vs 2 berbeda; counter 1 vs 1297 sama (siklus 1.296)",
              MakeRequestId(2026091901, 1) != MakeRequestId(2026091901, 2) &&
              MakeRequestId(2026091901, 1) == MakeRequestId(2026091901, 1297));
   ok = ParseOrderComment(BuildOrderComment(1.1, 5, MakeRequestId(2026091999, 1295)), sl, id);
   AssertTrue("TC-EX-20c", "ID buatan MakeRequestId selalu lolos parser", ok && id == MakeRequestId(2026091999, 1295));

   AssertIntEq("TC-EX-21", "buy diminta 1.10000 isi 1.10003 -> -3", SlippagePoints(true, 1.10000, 1.10003, TE_PT5), -3);
   AssertIntEq("TC-EX-22", "sell diminta 1.10000 isi 1.10003 -> +3", SlippagePoints(false, 1.10000, 1.10003, TE_PT5), 3);
  }

void RunTestExecutionPosition()
  {
   string why;
   AssertTrue("TC-EX-23", "buy: SL 1.09900 -> 1.09850 (lebih buruk) ditolak",
              !IsModifySlAllowed(true, 1.09900, 1.09850, 1.10000, 1.10008, 0, 0, TE_PT5, why) && why != "");
   AssertTrue("TC-EX-24", "buy: SL baru di atas bid ditolak",
              !IsModifySlAllowed(true, 1.09900, 1.10010, 1.10000, 1.10008, 0, 0, TE_PT5, why));
   AssertTrue("TC-EX-24b", "sell: SL 1.10100 -> 1.10050, ask 1.10000: lolos",
              IsModifySlAllowed(false, 1.10100, 1.10050, 1.09992, 1.10000, 0, 0, TE_PT5, why));
   AssertTrue("TC-EX-24c", "buy: SL sama dengan SL lama ditolak",
              !IsModifySlAllowed(true, 1.09900, 1.09900, 1.10000, 1.10008, 0, 0, TE_PT5, why));
   AssertTrue("TC-EX-24d", "buy: SL baru 5 point dari bid dengan stops 10 ditolak; 20 point lolos",
              !IsModifySlAllowed(true, 1.09900, 1.09995, 1.10000, 1.10008, 10, 0, TE_PT5, why) &&
              IsModifySlAllowed(true, 1.09900, 1.09980, 1.10000, 1.10008, 10, 0, TE_PT5, why));
   AssertTrue("TC-EX-24e", "buy: SL lama 3 point dari bid, freeze 5 -> ditolak (beku)",
              !IsModifySlAllowed(true, 1.09997, 1.09998, 1.10000, 1.10008, 0, 5, TE_PT5, why));

   AssertTrue("TC-EX-25", "tutup 0.10 dari 0.10 ditolak", !IsPartialVolumeValid(0.10, 0.10, 0.01, 0.01, why) && why != "");
   AssertTrue("TC-EX-26", "tutup 0.02 dari 0.03 (min 0.01) lolos", IsPartialVolumeValid(0.02, 0.03, 0.01, 0.01, why));
   AssertTrue("TC-EX-27", "tutup 0.025 dari 0.05 (step 0.01) ditolak", !IsPartialVolumeValid(0.025, 0.05, 0.01, 0.01, why));
   AssertTrue("TC-EX-27b", "tutup 0.045 dari 0.05 (sisa 0.005 < min) ditolak", !IsPartialVolumeValid(0.045, 0.05, 0.01, 0.001, why));
   AssertTrue("TC-EX-27c", "volume 0 dan negatif ditolak", !IsPartialVolumeValid(0.0, 0.05, 0.01, 0.01, why) &&
              !IsPartialVolumeValid(-0.01, 0.05, 0.01, 0.01, why));
  }

void RunTestExecution()
  {
   TfBeginSuite("Execution");
   RunTestExecutionOrder();
   RunTestExecutionBroker();
   RunTestExecutionComment();
   RunTestExecutionPosition();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTEXECUTION_MQH
