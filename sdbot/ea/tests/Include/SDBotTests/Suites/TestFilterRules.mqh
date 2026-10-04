//+------------------------------------------------------------------+
//| TestFilterRules.mqh — filter sesi (UTC) dan spread sebagai fungsi
//| murni (spec 14 design §3.1, §6.1; TC-FL-01..08).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTFILTERRULES_MQH
#define SDB_SUITES_TESTFILTERRULES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/InputRules.mqh>
#include <SDBot/Filters/FilterRules.mqh>

SdbSessionParams TflSessions(const bool tokyo, const bool london, const bool newYork)
  {
   SdbSessionParams p;
   p.tokyo = tokyo;
   p.london = london;
   p.newYork = newYork;
   return p;
  }

string TflAllowedText(const SdbSessionParams &p)
  {
   string s = "";
   for(int i = 0; i <= (int)SDB_SESSION_OFF; i++)
      s += SessionAllowed((ENUM_SDB_SESSION)i, p) ? "1" : "0";
   return s;
  }

void RunTestFilterRules()
  {
   TfBeginSuite("FilterRules");
   int secs[] = {0, 28799, 28800, 46799, 46800, 61199, 61200, 79199, 79200, 86399};
   string names = "";
   for(int i = 0; i < ArraySize(secs); i++)
      names += (i > 0 ? "," : "") + SessionText(SessionOfUtc(secs[i]));
   AssertStrEq("TC-FL-01", "nama sesi di batas jam UTC", names,
               "TOKYO,TOKYO,LONDON,LONDON,OVERLAP,OVERLAP,NEWYORK,NEWYORK,OFF,OFF");

   // Urutan: TOKYO, LONDON, OVERLAP, NEWYORK, OFF.
   AssertStrEq("TC-FL-02", "default London + NY", TflAllowedText(TflSessions(false, true, true)), "01110");
   AssertTrue("TC-FL-03", "hanya NY: overlap ya, London tidak; hanya Tokyo: Tokyo saja",
              TflAllowedText(TflSessions(false, false, true)) == "00110" && TflAllowedText(TflSessions(true, false, false)) == "10000");
   SdbSessionParams off = TflSessions(false, false, false);
   AssertTrue("TC-FL-04", "semua false: filter mati, semua sesi termasuk OFF diizinkan",
              !SessionFilterOn(off) && TflAllowedText(off) == "11111" && SessionFilterOn(TflSessions(true, false, false)));

   datetime d = D'2026.06.01 00:00';
   int a = UtcSecOfDay(d + 3 * 3600 + 1800, 3 * 3600);
   int b = UtcSecOfDay(d + 20 * 3600, -5 * 3600);
   int c = UtcSecOfDay(d + 900, 3 * 3600);
   AssertTrue("TC-FL-05", StringFormat("server ke UTC: 03:30+3 -> %d (1800), 20:00-5 -> %d (3600), 00:15+3 -> %d (76500)", a, b, c),
              a == 1800 && b == 3600 && c == 76500 && SessionOfUtc(c) == SDB_SESSION_NEWYORK);

   AssertTrue("TC-FL-06", "offset: tester 2 jam = 7200; live 10795 -> 10800; live -18010 -> -18000",
              ServerUtcOffsetSec(true, 2, d, d) == 7200 && ServerUtcOffsetSec(false, 9, d + 10795, d) == 10800 &&
              ServerUtcOffsetSec(false, 0, d, d + 18010) == -18000);

   AssertTrue("TC-FL-07", "spread 23/24 dan 24/24 lolos, 25/24 ditolak, maks 0 = mati",
              SpreadAllowed(23, 24) && SpreadAllowed(24, 24) && !SpreadAllowed(25, 24) && SpreadAllowed(500, 0));

   string err;
   InputValues v = DefaultInputValues();
   bool defaults = !v.sessionTokyo && v.sessionLondon && v.sessionNewYork && v.maxSpreadPoints == 0 && v.testerUtcOffsetHours == 0 &&
                   ValidateInputValues(v, false, err);
   string names2[] = {"InpMaxSpreadPoints", "InpMaxSpreadPoints", "InpTesterUtcOffsetHours", "InpTesterUtcOffsetHours"};
   int bad = 0;
   for(int i = 0; i < ArraySize(names2); i++)
     {
      v = DefaultInputValues();
      switch(i)
        {
         case 0: v.maxSpreadPoints = -1; break;
         case 1: v.maxSpreadPoints = 100001; break;
         case 2: v.testerUtcOffsetHours = -13; break;
         default: v.testerUtcOffsetHours = 15; break;
        }
      err = "";
      if(ValidateInputValues(v, false, err) || StringFind(err, names2[i]) < 0)
         bad++;
     }
   v = DefaultInputValues();
   v.maxSpreadPoints = 100000;
   v.testerUtcOffsetHours = -12;
   bool edges = ValidateInputValues(v, false, err);
   v.testerUtcOffsetHours = 14;
   edges = edges && ValidateInputValues(v, false, err);
   AssertTrue("TC-FL-08", StringFormat("input sesi/spread/offset: default lolos, batas tepi lolos, di luar ditolak (gagal %d)", bad),
              defaults && edges && bad == 0);
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTFILTERRULES_MQH
