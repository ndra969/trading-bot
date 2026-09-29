//+------------------------------------------------------------------+
//| TestAccountRules.mqh — aturan akun, izin trading, dan koneksi
//| (spec 02 Req 2 dan 3), diuji dengan nilai buatan tanpa akun sungguhan.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTACCOUNTRULES_MQH
#define SDB_SUITES_TESTACCOUNTRULES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Account/AccountRules.mqh>

bool ArContains(const string text, const string part) { return StringFind(text, part) >= 0; }

void RunTestAccountEvaluate()
  {
   string r;
   AssertTrue("TC-AC-01", "demo + hedging + allowLive false: lolos",
              EvaluateAccount(ACCOUNT_TRADE_MODE_DEMO, ACCOUNT_MARGIN_MODE_RETAIL_HEDGING, false, r));
   bool ok = EvaluateAccount(ACCOUNT_TRADE_MODE_REAL, ACCOUNT_MARGIN_MODE_RETAIL_HEDGING, false, r);
   AssertTrue("TC-AC-02", "real + allowLive false: ditolak, menyebut InpAllowLiveTrading", !ok && ArContains(r, "InpAllowLiveTrading"));
   AssertTrue("TC-AC-03", "real + hedging + allowLive true: lolos",
              EvaluateAccount(ACCOUNT_TRADE_MODE_REAL, ACCOUNT_MARGIN_MODE_RETAIL_HEDGING, true, r));
   ok = EvaluateAccount(ACCOUNT_TRADE_MODE_REAL, ACCOUNT_MARGIN_MODE_RETAIL_NETTING, true, r);
   AssertTrue("TC-AC-04", "netting: ditolak, menyebut NETTING", !ok && ArContains(r, "NETTING"));
   ok = EvaluateAccount(ACCOUNT_TRADE_MODE_DEMO, ACCOUNT_MARGIN_MODE_EXCHANGE, false, r);
   AssertTrue("TC-AC-05", "exchange: ditolak, menyebut EXCHANGE", !ok && ArContains(r, "EXCHANGE"));
   ok = EvaluateAccount(ACCOUNT_TRADE_MODE_REAL, ACCOUNT_MARGIN_MODE_RETAIL_NETTING, false, r);
   AssertTrue("TC-AC-05b", "real + netting + allowLive false: kedua alasan disebut",
              !ok && ArContains(r, "InpAllowLiveTrading") && ArContains(r, "NETTING"));

   AssertIntEq("TC-AC-06", "real + USC = CENT", AccountTypeOf(ACCOUNT_TRADE_MODE_REAL, "USC"), SDB_ACC_CENT);
   AssertIntEq("TC-AC-07", "real + USD = REAL", AccountTypeOf(ACCOUNT_TRADE_MODE_REAL, "USD"), SDB_ACC_REAL);
   AssertIntEq("TC-AC-08", "demo + USC = DEMO", AccountTypeOf(ACCOUNT_TRADE_MODE_DEMO, "USC"), SDB_ACC_DEMO);
   AssertIntEq("TC-AC-08b", "real + EUC = CENT", AccountTypeOf(ACCOUNT_TRADE_MODE_REAL, "EUC"), SDB_ACC_CENT);
   AssertIntEq("TC-AC-08c", "real + US (bukan USC) = REAL", AccountTypeOf(ACCOUNT_TRADE_MODE_REAL, "US"), SDB_ACC_REAL);

   AssertTrue("TC-AC-09", "EURUSDc dengan suffix c", SymbolMatchesSuffix("EURUSDc", "c"));
   AssertTrue("TC-AC-10", "EURUSD dengan suffix c ditolak", !SymbolMatchesSuffix("EURUSD", "c"));
   AssertTrue("TC-AC-11", "suffix kosong selalu cocok", SymbolMatchesSuffix("EURUSDc", ""));
   AssertTrue("TC-AC-12", "EURUSD.pro dengan suffix .pro", SymbolMatchesSuffix("EURUSD.pro", ".pro"));
   AssertTrue("TC-AC-12b", "suffix lebih panjang dari simbol ditolak", !SymbolMatchesSuffix("c", "cc"));
  }

void RunTestAccountPermission()
  {
   string why;
   AssertTrue("TC-AC-13", "semua izin ada, simbol FULL: boleh trading",
              TradePermission(true, true, true, true, true, SYMBOL_TRADE_MODE_FULL, why) && why == "");
   bool ok = TradePermission(true, true, false, true, true, SYMBOL_TRADE_MODE_FULL, why);
   AssertTrue("TC-AC-14", "izin EA mati: tidak boleh, alasan menyebut izin EA", !ok && ArContains(why, "MQL_TRADE_ALLOWED"));
   ok = TradePermission(true, true, true, true, true, SYMBOL_TRADE_MODE_CLOSEONLY, why);
   AssertTrue("TC-AC-15", "simbol close-only: tidak boleh, alasan menyebut simbol", !ok && ArContains(why, "SYMBOL_TRADE_MODE"));
   ok = TradePermission(false, true, true, true, true, SYMBOL_TRADE_MODE_FULL, why);
   AssertTrue("TC-AC-15b", "terputus: tidak boleh, alasan menyebut koneksi", !ok && ArContains(why, "TERMINAL_CONNECTED"));
   ok = TradePermission(true, false, true, false, false, SYMBOL_TRADE_MODE_FULL, why);
   AssertTrue("TC-AC-15c", "beberapa izin mati: semua disebut",
              !ok && ArContains(why, "TERMINAL_TRADE_ALLOWED") && ArContains(why, "ACCOUNT_TRADE_ALLOWED") &&
              ArContains(why, "ACCOUNT_TRADE_EXPERT"));
  }

void RunTestAccountConnection()
  {
   datetime t0 = D'2026.09.29 10:00:00';
   datetime down = 0, last = 0;
   bool alerted = false;
   ENUM_SDB_CONN_ACTION a1 = ConnectionStep(false, t0, down, last, alerted);
   ENUM_SDB_CONN_ACTION a2 = ConnectionStep(false, t0 + 299, down, last, alerted);
   AssertTrue("TC-AC-16", "putus: LOG_DOWN sekali, lalu tanpa alert sampai 299 detik",
              a1 == SDB_CONN_LOG_DOWN && a2 == SDB_CONN_NONE);
   AssertIntEq("TC-AC-17", "putus 300 detik: alert Medium", ConnectionStep(false, t0 + 300, down, last, alerted), SDB_CONN_ALERT_MEDIUM);
   AssertIntEq("TC-AC-18", "masih putus 450 detik: belum diulang", ConnectionStep(false, t0 + 450, down, last, alerted), SDB_CONN_NONE);
   AssertIntEq("TC-AC-19", "masih putus 600 detik: alert diulang", ConnectionStep(false, t0 + 600, down, last, alerted), SDB_CONN_ALERT_MEDIUM);
   ENUM_SDB_CONN_ACTION up1 = ConnectionStep(true, t0 + 610, down, last, alerted);
   ENUM_SDB_CONN_ACTION up2 = ConnectionStep(true, t0 + 611, down, last, alerted);
   AssertTrue("TC-AC-20", "pulih setelah alert: ALERT_RECOVERED sekali lalu NONE",
              up1 == SDB_CONN_ALERT_RECOVERED && up2 == SDB_CONN_NONE);

   // Putus-sambung tiap 2 menit selama 20 menit: tidak pernah 5 menit berturut-turut.
   datetime d2 = 0, l2 = 0;
   bool al2 = false;
   bool anyAlert = false;
   int logDowns = 0;
   for(int c = 0; c < 10; c++)
     {
      datetime start = t0 + c * 240;
      for(int s = 0; s <= 120; s += 30)
        {
         ENUM_SDB_CONN_ACTION a = ConnectionStep(false, start + s, d2, l2, al2);
         if(a == SDB_CONN_ALERT_MEDIUM)
            anyAlert = true;
         if(a == SDB_CONN_LOG_DOWN)
            logDowns++;
        }
      if(ConnectionStep(true, start + 150, d2, l2, al2) == SDB_CONN_ALERT_RECOVERED)
         anyAlert = true;
     }
   AssertTrue("TC-AC-21", "putus-sambung 10x @ 2 menit: tanpa alert, 10 WARN putus", !anyAlert && logDowns == 10);
  }

void RunTestAccountRules()
  {
   TfBeginSuite("AccountRules");
   RunTestAccountEvaluate();
   RunTestAccountPermission();
   RunTestAccountConnection();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTACCOUNTRULES_MQH
