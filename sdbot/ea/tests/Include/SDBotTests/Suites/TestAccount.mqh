//+------------------------------------------------------------------+
//| TestAccount.mqh — CAccount di Strategy Tester (akun tester):
//| validasi, snapshot ke sink, izin trading, sink NULL (spec 02 task 6).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTACCOUNT_MQH
#define SDB_SUITES_TESTACCOUNT_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/FakeSink.mqh>
#include <SDBot/Account/Account.mqh>

// Suffix yang benar untuk simbol uji: bagian setelah nama pair 6 huruf (EURUSDc -> "c").
string TaSuffixOf(const string symbol)
  {
   return (StringLen(symbol) > 6) ? StringSubstr(symbol, 6) : "";
  }

void RunTestAccount()
  {
   TfBeginSuite("Account");
   SdbLogCaptureStart();   // log CAccount tidak perlu memenuhi output uji

   CFakeSink fake;
   CAccount acc;
   acc.Init(GetPointer(fake), _Symbol, TaSuffixOf(_Symbol), true, SDB_DEF_MAGIC);
   ENUM_SDB_VALIDATION v = acc.Validate();
   AccountSnapshot snap;
   bool hasSnap = fake.LastAccount(snap);
   AssertIntEq("TC-AC-22a", "Validate di tester: PASSED", v, SDB_VAL_PASSED);
   AssertIntEq("TC-AC-22b", "tepat satu AccountSnapshot dikirim ke sink", fake.CountAccount(), 1);
   AssertTrue("TC-AC-22c", "snapshot berisi login, mata uang, dan balance",
              hasSnap && snap.login > 0 && snap.currency != "" && snap.balance > 0 && snap.login == acc.Login());

   string why;
   acc.OnTimer();
   AssertTrue("TC-AC-23", "CanTrade di tester setelah validasi: true tanpa alasan", acc.CanTrade(why) && why == "");

   CFakeSink fake2;
   CAccount wrong;
   wrong.Init(GetPointer(fake2), _Symbol, "zz", true, SDB_DEF_MAGIC);
   ENUM_SDB_VALIDATION v2 = wrong.Validate();
   AlertEvent alert;
   bool hasAlert = fake2.LastAlert(alert);
   AssertTrue("TC-AC-25", "suffix salah: REJECTED, alert Critical ACCOUNT_REJECTED, alasan menyebut suffix",
              v2 == SDB_VAL_REJECTED && hasAlert && alert.severity == SDB_SEV_CRITICAL &&
              alert.type == SDB_ALERT_TYPE_ACCOUNT_REJECTED && StringFind(wrong.LastReason(), "zz") >= 0);
   AssertTrue("TC-AC-25b", "akun yang ditolak tidak boleh trading", !wrong.CanTrade(why));

   CAccount noSink;
   noSink.Init(NULL, _Symbol, TaSuffixOf(_Symbol), true, SDB_DEF_MAGIC);
   AssertIntEq("TC-AC-24", "Init(NULL) lalu Validate: tidak crash, tetap PASSED", noSink.Validate(), SDB_VAL_PASSED);

   SdbLogCaptureStop();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTACCOUNT_MQH
