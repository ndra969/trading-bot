//+------------------------------------------------------------------+
//| TestNewsRules.mqh — filter berita sebagai fungsi murni (spec 16
//| design §3.1, §6.1; TC-NW-01..11). Event dasar: USD HIGH NFP pukul
//| 12:30 server.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTNEWSRULES_MQH
#define SDB_SUITES_TESTNEWSRULES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/InputRules.mqh>
#include <SDBot/Filters/NewsRules.mqh>

#define TNW_DAY D'2026.06.05 00:00'

SdbNewsEvent TnwEv(const datetime t, const string ccy, const int impact, const string name)
  {
   SdbNewsEvent e;
   e.time = t;
   e.ccy = ccy;
   e.impact = impact;
   e.id = 1000 + impact;
   e.name = name;
   return e;
  }

SdbNewsParams TnwParams()
  {
   SdbNewsParams p;
   p.enabled = true;
   p.highMinutes = 30;
   p.mediumMinutes = 10;
   return p;
  }

void TnwPush(SdbNewsEvent &ev[], const SdbNewsEvent &e)
  {
   int n = ArraySize(ev);
   ArrayResize(ev, n + 1);
   ev[n] = e;
  }

bool TnwBlocked(const SdbNewsEvent &ev[], const datetime bar, const string base = "EUR", const string quote = "USD")
  {
   return FindBlackout(ev, bar, base, quote, TnwParams()) >= 0;
  }

void RunTestNewsRules()
  {
   TfBeginSuite("NewsRules");
   datetime nfp = TNW_DAY + 12 * 3600 + 30 * 60;
   SdbNewsEvent ev[];
   TnwPush(ev, TnwEv(nfp, "USD", SDB_NEWS_HIGH, "Non-Farm Payrolls"));
   AssertTrue("TC-NW-01", StringFormat("NFP 12:30: bar 12:00 / 12:30 / 13:00 diblokir (menit %d / %d / %d)", MinutesToEvent(nfp - 1800, nfp),
                                       MinutesToEvent(nfp, nfp), MinutesToEvent(nfp + 1800, nfp)),
              TnwBlocked(ev, nfp - 1800) && TnwBlocked(ev, nfp) && TnwBlocked(ev, nfp + 1800) && MinutesToEvent(nfp - 1800, nfp) == -30 &&
              MinutesToEvent(nfp + 1800, nfp) == 30);
   AssertTrue("TC-NW-02", "bar 11:59 dan 13:01 tidak diblokir", !TnwBlocked(ev, nfp - 1860) && !TnwBlocked(ev, nfp + 1860));

   SdbNewsEvent em[];
   datetime cpi = TNW_DAY + 9 * 3600;
   TnwPush(em, TnwEv(cpi, "EUR", SDB_NEWS_MEDIUM, "CPI m/m"));
   TnwPush(em, TnwEv(TNW_DAY + 15 * 3600, "EUR", SDB_NEWS_LOW, "Bank Holiday"));
   AssertTrue("TC-NW-03", "EUR MEDIUM 09:00: 08:50 dan 09:10 diblokir, 09:11 tidak; LOW tidak pernah",
              TnwBlocked(em, cpi - 600) && TnwBlocked(em, cpi + 600) && !TnwBlocked(em, cpi + 660) && !TnwBlocked(em, TNW_DAY + 15 * 3600));

   SdbNewsEvent usd = ev[0];
   SdbNewsEvent jpy = TnwEv(nfp, "JPY", SDB_NEWS_HIGH, "BoJ");
   SdbNewsEvent gbp = TnwEv(nfp, "GBP", SDB_NEWS_HIGH, "BoE");
   AssertTrue("TC-NW-04", "relevansi: USD untuk EURUSD/USDJPY/XAUUSD/BTCUSD, JPY untuk EURJPY, GBP bukan untuk EURUSD",
              EventForSymbol(usd, "EUR", "USD") && EventForSymbol(usd, "USD", "JPY") && EventForSymbol(usd, "XAU", "USD") &&
              EventForSymbol(usd, "BTC", "USD") && EventForSymbol(jpy, "EUR", "JPY") && !EventForSymbol(gbp, "EUR", "USD"));

   SdbNewsEvent ov[];
   TnwPush(ov, TnwEv(nfp + 300, "USD", SDB_NEWS_MEDIUM, "ISM"));
   TnwPush(ov, TnwEv(nfp + 600, "EUR", SDB_NEWS_HIGH, "ECB Rate"));
   int idx = FindBlackout(ov, nfp + 300, "EUR", "USD", TnwParams());
   AssertTrue("TC-NW-05", "EUR HIGH + USD MEDIUM tumpang tindih: dipilih EUR HIGH", idx == 1);

   SdbNewsParams zero = TnwParams();
   zero.highMinutes = 0;
   zero.mediumMinutes = 0;
   SdbNewsParams off = TnwParams();
   off.enabled = false;
   AssertTrue("TC-NW-06", "jendela 0/0 dan filter mati: tidak ada blackout",
              FindBlackout(ev, nfp, "EUR", "USD", zero) < 0 && FindBlackout(ev, nfp, "EUR", "USD", off) < 0);

   SdbNewsEvent e;
   bool ok1 = ParseCalendarLine("1780648200,USD,HIGH,840030016,Non-Farm Payrolls", e) && e.time == 1780648200 && e.ccy == "USD" &&
              e.impact == SDB_NEWS_HIGH && e.id == 840030016 && e.name == "Non-Farm Payrolls";
   SdbNewsEvent e2;
   bool ok2 = ParseCalendarLine("1780648200,EUR,MEDIUM,1,ECB President Lagarde Speaks, Q&A", e2) && e2.name == "ECB President Lagarde Speaks, Q&A";
   bool bad = !ParseCalendarLine("1780648200,USD,HIGH", e) && !ParseCalendarLine("abc,USD,HIGH,1,X", e) && !ParseCalendarLine("1780648200,USDX,HIGH,1,X", e);
   AssertTrue("TC-NW-07", "parse: baris valid, nama berkoma utuh; kolom kurang / epoch bukan angka / ccy 4 huruf ditolak", ok1 && ok2 && bad);

   SdbNewsEvent src = TnwEv(nfp, "USD", SDB_NEWS_HIGH, "Fed, Chair\nSpeech");
   SdbNewsEvent back;
   string line = CalendarLine(src);
   AssertTrue("TC-NW-08", "round trip CalendarLine -> Parse: '" + line + "'",
              ParseCalendarLine(line, back) && back.time == src.time && back.ccy == "USD" && back.impact == SDB_NEWS_HIGH && back.id == src.id &&
              back.name == "Fed  Chair Speech");

   SdbNewsEvent up[];
   datetime now = TNW_DAY + 10 * 3600;
   TnwPush(up, TnwEv(now - 3600, "USD", SDB_NEWS_HIGH, "Lewat"));
   TnwPush(up, TnwEv(TNW_DAY + 86400 + 8 * 3600, "EUR", SDB_NEWS_MEDIUM, "Besok"));
   TnwPush(up, TnwEv(TNW_DAY + 2 * 86400 + 3600, "USD", SDB_NEWS_HIGH, "Lusa"));
   TnwPush(up, TnwEv(now + 3600, "EUR", SDB_NEWS_LOW, "Low"));
   int nx = NearestUpcoming(up, now, "EUR", "USD", 86400);
   AssertTrue("TC-NW-09", StringFormat("event terdekat 24 jam (>= medium, belum lewat): indeks %d (1)", nx), nx == 1);

   AssertStrEq("TC-NW-10", "detail blackout 12 menit sebelum rilis", BlackoutDetail(ev[0], nfp - 720), "Non-Farm Payrolls USD HIGH -12m");

   string err;
   InputValues v = DefaultInputValues();
   bool defaults = v.newsFilter && v.newsHighMinutes == 15 && v.newsMediumMinutes == 0 && v.newsCsvFile == "sdbot_calendar.csv" &&
                   ValidateInputValues(v, false, err);
   v.newsHighMinutes = 241;
   err = "";
   bool hi = !ValidateInputValues(v, false, err) && StringFind(err, "InpNewsHighMinutes") >= 0;
   v = DefaultInputValues();
   v.newsMediumMinutes = -1;
   err = "";
   bool md = !ValidateInputValues(v, false, err) && StringFind(err, "InpNewsMediumMinutes") >= 0;
   AssertTrue("TC-NW-11", "input berita: default lolos; 241 dan -1 ditolak dengan nama", defaults && hi && md);
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTNEWSRULES_MQH
