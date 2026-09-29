//+------------------------------------------------------------------+
//| TestState.mqh — status bersama di Global Variables (spec 02 Req 4).
//| Memakai prefix SDBTEST agar status akun sungguhan tidak tersentuh.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTSTATE_MQH
#define SDB_SUITES_TESTSTATE_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/State.mqh>

#define SDB_TEST_GV_PREFIX "SDBTEST"
#define SDB_TEST_GV_LOGIN  123

int StCountWithPrefix(const string prefix)
  {
   int n = 0;
   for(int i = GlobalVariablesTotal() - 1; i >= 0; i--)
      if(StringFind(GlobalVariableName(i), prefix) == 0)
         n++;
   return n;
  }

void RunTestState()
  {
   TfBeginSuite("State");
   string fullPrefix = SDB_TEST_GV_PREFIX + "_" + IntegerToString(SDB_TEST_GV_LOGIN) + "_";
   GlobalVariablesDeleteAll(fullPrefix);

   CState bad;
   AssertTrue("TC-ST-00", "Init dengan login 0 ditolak (terminal belum login)", !bad.Init(SDB_TEST_GV_PREFIX, 0));

   CState st;
   bool ok = st.Init(SDB_TEST_GV_PREFIX, SDB_TEST_GV_LOGIN);
   AssertTrue("TC-ST-00b", "Init dengan prefix uji dan login 123", ok);
   AssertStrEq("TC-ST-01", "nama kunci SDBTEST_123_STOPPED", st.Key("STOPPED"), "SDBTEST_123_STOPPED");

   bool missing = false;
   double v = st.GetOrInit("STOPPED", 0.0, missing);
   AssertTrue("TC-ST-02", "kunci baru: nilai awal 0, wasMissing true, GV langsung dibuat",
              v == 0.0 && missing && GlobalVariableCheck("SDBTEST_123_STOPPED"));

   GlobalVariableSet("SDBTEST_123_DAILY_PAUSE", 1.0);
   v = st.GetOrInit("DAILY_PAUSE", 0.0, missing);
   AssertTrue("TC-ST-03", "kunci yang sudah 1: nilai 1, wasMissing false", v == 1.0 && !missing);

   bool setOk = st.Set("PEAK_EQUITY", 1234.5, true);
   CState other;
   other.Init(SDB_TEST_GV_PREFIX, SDB_TEST_GV_LOGIN);
   AssertTrue("TC-ST-04", "Set lalu instance lain membaca nilai yang sama (simulasi instance EA lain)",
              setOk && other.Get("PEAK_EQUITY", -1.0) == 1234.5);
   AssertEq("TC-ST-04b", "Get kunci yang tidak ada mengembalikan fallback", other.Get("TIDAK_ADA", -7.0), -7.0);

   AssertIntEq("TC-ST-06", "TouchAll menyentuh semua kunci yang dipakai instance ini", st.TouchAll(), 3);

   int deleted = st.DeleteAll();
   AssertTrue("TC-ST-05", "DeleteAll menghapus semua GV berprefix SDBTEST_123_",
              deleted >= 3 && StCountWithPrefix(fullPrefix) == 0);

   TfEndSuite();
  }

#endif // SDB_SUITES_TESTSTATE_MQH
