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
  }

#endif // SDB_SDBOTTESTS_ALLSUITES_MQH
