//+------------------------------------------------------------------+
//| TestExposureRules.mqh — eksposur mata uang dengan arah sebagai
//| fungsi murni (spec 15 design §3.1, §6.1; TC-EXP-01..07). Mencegah
//| bug bot Python: arah SELL pernah dihitung terbalik.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTEXPOSURERULES_MQH
#define SDB_SUITES_TESTEXPOSURERULES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/InputRules.mqh>
#include <SDBot/Risk/ExposureRules.mqh>

// "EUR+ USD-" untuk kaki satu posisi.
string TexLegs(const string base, const string quote, const bool isBuy)
  {
   string ccy[];
   int dir[];
   int n = LegsOf(base, quote, isBuy, ccy, dir);
   string s = "";
   for(int i = 0; i < n; i++)
      s += (i > 0 ? " " : "") + ccy[i] + (dir[i] > 0 ? "+" : "-");
   return s;
  }

void RunTestExposureRules()
  {
   TfBeginSuite("ExposureRules");
   string got = TexLegs("EUR", "USD", true) + "|" + TexLegs("EUR", "USD", false) + "|" + TexLegs("USD", "JPY", true) + "|" +
                TexLegs("EUR", "JPY", false) + "|" + TexLegs("XAU", "USD", true) + "|" + TexLegs("BTC", "USD", false);
   AssertStrEq("TC-EXP-01", "kaki BUY/SELL EURUSD, BUY USDJPY, SELL EURJPY, BUY XAUUSD, SELL BTCUSD", got,
               "EUR+ USD-|EUR- USD+|USD+ JPY-|EUR- JPY+|XAU+ USD-|BTC- USD+");

   string ccy[];
   int dir[];
   AddLegs("EUR", "USD", true, ccy, dir);
   AddLegs("GBP", "USD", true, ccy, dir);
   AddLegs("USD", "JPY", false, ccy, dir);
   AssertTrue("TC-EXP-02", StringFormat("BUY EURUSD + BUY GBPUSD + SELL USDJPY: USD short %d (3), USD long %d (0), JPY long %d (1)",
                                        SameDirectionCount(ccy, dir, "USD", -1), SameDirectionCount(ccy, dir, "USD", 1),
                                        SameDirectionCount(ccy, dir, "JPY", 1)),
              SameDirectionCount(ccy, dir, "USD", -1) == 3 && SameDirectionCount(ccy, dir, "USD", 1) == 0 &&
              SameDirectionCount(ccy, dir, "JPY", 1) == 1);

   string c2[];
   int d2[];
   AddLegs("EUR", "USD", true, c2, d2);
   AddLegs("GBP", "USD", true, c2, d2);
   string det1 = "", det2 = "", det3 = "";
   bool buyAud = ExposureAllowed(c2, d2, "AUD", "USD", true, 2, det1);
   bool sellEur = ExposureAllowed(c2, d2, "EUR", "USD", false, 2, det2);
   bool off = ExposureAllowed(c2, d2, "AUD", "USD", true, 0, det3);
   AssertTrue("TC-EXP-03", "2 short USD: BUY AUDUSD ditolak '" + det1 + "', SELL EURUSD lolos, batas 0 lolos",
              !buyAud && det1 == "USD short 2/2" && sellEur && off);

   string c3[];
   int d3[];
   AddLegs("EUR", "JPY", true, c3, d3);
   AddLegs("USD", "JPY", true, c3, d3);
   string det4 = "";
   AssertTrue("TC-EXP-04", "BUY EURJPY + BUY USDJPY, lalu BUY GBPJPY: ditolak '" + det4 + "'",
              !ExposureAllowed(c3, d3, "GBP", "JPY", true, 2, det4) && det4 == "JPY short 2/2");

   string c4[];
   int d4[];
   AddLegs("XAU", "USD", true, c4, d4);
   AddLegs("EUR", "USD", true, c4, d4);
   string det5 = "";
   AssertTrue("TC-EXP-05", "BUY XAUUSD + BUY EURUSD, lalu BUY BTCUSD: ditolak USD short; XAU long 1",
              !ExposureAllowed(c4, d4, "BTC", "USD", true, 2, det5) && det5 == "USD short 2/2" &&
              SameDirectionCount(c4, d4, "XAU", 1) == 1);

   string c5[];
   int d5[];
   string det6 = "";
   AddLegs("EUR", "USD", true, c5, d5);
   AddLegs("EUR", "USD", true, c5, d5);
   AssertTrue("TC-EXP-06", "mata uang kosong / dasar = kuotasi: 0 kaki; order bermata uang kosong lolos",
              LegsOf("", "USD", true, ccy, dir) == 0 && LegsOf("USD", "USD", true, ccy, dir) == 0 &&
              ExposureAllowed(c5, d5, "", "USD", true, 2, det6));

   string err;
   InputValues v = DefaultInputValues();
   bool defaults = v.maxSameDirectionPerCurrency == 2 && ValidateInputValues(v, false, err);
   v.maxSameDirectionPerCurrency = 0;
   bool zero = ValidateInputValues(v, false, err);
   v.maxSameDirectionPerCurrency = 10;
   bool ten = ValidateInputValues(v, false, err);
   v.maxSameDirectionPerCurrency = -1;
   err = "";
   bool neg = !ValidateInputValues(v, false, err) && StringFind(err, "InpMaxSameDirectionPerCurrency") >= 0;
   v.maxSameDirectionPerCurrency = 11;
   err = "";
   bool big = !ValidateInputValues(v, false, err) && StringFind(err, "InpMaxSameDirectionPerCurrency") >= 0;
   AssertTrue("TC-EXP-07", "input: default 2, 0 dan 10 lolos, -1 dan 11 ditolak dengan nama", defaults && zero && ten && neg && big);
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTEXPOSURERULES_MQH
