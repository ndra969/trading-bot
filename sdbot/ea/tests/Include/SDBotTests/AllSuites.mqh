//+------------------------------------------------------------------+
//| AllSuites.mqh — daftar suite yang dijalankan script dan EA runner.
//| Tambahkan include dan panggilan Run<Suite>() setiap ada suite baru.
//+------------------------------------------------------------------+
#ifndef SDB_SDBOTTESTS_ALLSUITES_MQH
#define SDB_SDBOTTESTS_ALLSUITES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/Suites/TestFrameworkSelf.mqh>
#include <SDBotTests/Suites/TestEnvCheck.mqh>
#include <SDBotTests/Suites/TestEventSink.mqh>
#include <SDBotTests/Suites/TestCoreUtils.mqh>
#include <SDBotTests/Suites/TestState.mqh>
#include <SDBotTests/Suites/TestAccountRules.mqh>
#include <SDBotTests/Suites/TestAccount.mqh>
#include <SDBotTests/Suites/TestCodec.mqh>
#include <SDBotTests/Suites/TestMigrations.mqh>
#include <SDBotTests/Suites/TestLogger.mqh>
#include <SDBotTests/Suites/TestExecution.mqh>
#include <SDBotTests/Suites/TestApp.mqh>
#include <SDBotTests/Suites/TestRiskMath.mqh>
#include <SDBotTests/Suites/TestRiskState.mqh>
#include <SDBotTests/Suites/TestRisk.mqh>
#include <SDBotTests/Suites/TestPositionMath.mqh>
#include <SDBotTests/Suites/TestClosure.mqh>
#include <SDBotTests/Suites/TestPosition.mqh>
#include <SDBotTests/Suites/TestIntegration.mqh>
#include <SDBotTests/Suites/TestPresets.mqh>
#include <SDBotTests/Suites/TestNotifyRules.mqh>
#include <SDBotTests/Suites/TestNotifyFormat.mqh>
#include <SDBotTests/Suites/TestNotifier.mqh>
#include <SDBotTests/Suites/TestTelegramRules.mqh>
#include <SDBotTests/Suites/TestSchedule.mqh>
#include <SDBotTests/Suites/TestStructure.mqh>
#include <SDBotTests/Suites/TestMarketStructure.mqh>
#include <SDBotTests/Suites/TestZones.mqh>
#include <SDBotTests/Suites/TestZoneBook.mqh>
#include <SDBotTests/Suites/TestPatterns.mqh>
#include <SDBotTests/Suites/TestPaTrigger.mqh>

void RunAllSuites()
  {
   RunTestCodec();
   RunTestFrameworkSelf();
   RunTestEnvCheck();
   RunTestEventSink();
   RunTestCoreUtils();
   RunTestState();
   RunTestAccountRules();
   RunTestAccount();
   RunTestMigrations();
   RunTestLogger();
   RunTestExecution();
   RunTestApp();
   RunTestRiskMath();
   RunTestRiskState();
   RunTestRisk();
   RunTestPositionMath();
   RunTestClosure();
   RunTestPosition();
   RunTestIntegration();
   RunTestPresets();
   RunTestNotifyRules();
   RunTestNotifyFormat();
   RunTestNotifier();
   RunTestTelegramRules();
   RunTestSchedule();
   RunTestStructure();
   RunTestMarketStructure();
   RunTestZones();
   RunTestZoneBook();
   RunTestPatterns();
   RunTestPaTrigger();
  }

#endif // SDB_SDBOTTESTS_ALLSUITES_MQH
