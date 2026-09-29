//+------------------------------------------------------------------+
//| TestFrameworkSelf.mqh — self-test framework uji (TC-TF-01..06):
//| membuktikan assert yang gagal benar-benar terhitung sebagai FAIL.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTFRAMEWORKSELF_MQH
#define SDB_SUITES_TESTFRAMEWORKSELF_MQH

#include <SDBotTests/TestFramework.mqh>

void RunTestFrameworkSelf()
  {
   TfBeginSuite("FrameworkSelf");

   // Assert di bawah sengaja dijalankan dalam mode mute: hasilnya hanya dihitung,
   // lalu hitungan dikembalikan agar ringkasan run tidak tercemar FAIL yang disengaja.
   int passBefore = TfPassCount();
   int failBefore = TfFailCount();
   TfMute(true);
   bool r01  = AssertEq("TC-TF-01", "1.0 == 1.0", 1.0, 1.0);
   bool r02  = AssertEq("TC-TF-02", "1.0 != 1.1", 1.0, 1.1);
   bool r03  = AssertEq("TC-TF-03", "0.1+0.2 ~ 0.3", 0.1 + 0.2, 0.3, 1e-9);
   bool r04a = AssertStrEq("TC-TF-04a", "SDB == SDB", "SDB", "SDB");
   bool r04b = AssertStrEq("TC-TF-04b", "a != b", "a", "b");
   bool r05a = AssertIntEq("TC-TF-05a", "3 == 3", 3, 3);
   bool r05b = AssertTrue("TC-TF-05b", "false", false);
   TfMute(false);
   int passDelta = TfPassCount() - passBefore;
   int failDelta = TfFailCount() - failBefore;
   TfSetCounts(passBefore, failBefore);

   // Assert sungguhan atas perilaku framework.
   AssertTrue("TC-TF-01", "AssertEq nilai sama mengembalikan true", r01);
   AssertTrue("TC-TF-02", "AssertEq nilai beda mengembalikan false", !r02);
   AssertTrue("TC-TF-03", "AssertEq memakai toleransi", r03);
   AssertTrue("TC-TF-04", "AssertStrEq sama true, beda false", r04a && !r04b);
   AssertTrue("TC-TF-05", "AssertIntEq sama true, AssertTrue(false) false", r05a && !r05b);
   AssertIntEq("TC-TF-06a", "assert mute yang lulus terhitung", passDelta, 4);
   AssertIntEq("TC-TF-06b", "assert mute yang gagal terhitung", failDelta, 3);

   TfEndSuite();
  }

#endif // SDB_SUITES_TESTFRAMEWORKSELF_MQH
