//+------------------------------------------------------------------+
//| AllSuites.mqh — daftar suite yang dijalankan script dan EA runner.
//| Tambahkan include dan panggilan Run<Suite>() setiap ada suite baru.
//+------------------------------------------------------------------+
#ifndef SDB_SDBOTTESTS_ALLSUITES_MQH
#define SDB_SDBOTTESTS_ALLSUITES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/Suites/TestFrameworkSelf.mqh>

void RunAllSuites()
  {
   RunTestFrameworkSelf();
  }

#endif // SDB_SDBOTTESTS_ALLSUITES_MQH
