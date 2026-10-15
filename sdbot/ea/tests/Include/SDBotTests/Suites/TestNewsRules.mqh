//+------------------------------------------------------------------+
//| TestNewsRules.mqh — filter berita sebagai fungsi murni (spec 16
//| design §3.1, §6.1; TC-NW-01..11) dan filter impuls sesudah berita
//| (spec 39 design §3, §6; TC-NW-12..14). Event dasar: USD HIGH NFP pukul
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
   p.impulseMult = 0.0;
   p.impulseMinutes = 90;
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

// Range 13 bar = 10, satu bar = big di indeks bigAt (0 = bar tertutup terbaru), n bar.
void TnwBars(double &h[], double &l[], const int n, const int bigAt, const double big)
  {
   ArrayResize(h, n);
   ArrayResize(l, n);
   for(int i = 0; i < n; i++)
     {
      l[i] = 100.0;
      h[i] = 100.0 + (i == bigAt ? big : 10.0);
     }
  }

// TC-NW-12..14 (spec 39): rasio impuls, berita HIGH terbaru, keputusan.
void RunTestNewsImpulse()
  {
   double h[], l[];
   TnwBars(h, l, 14, 0, 60.0);
   double r0 = ImpulseRatio(h, l, 14);
   AssertTrue("TC-NW-12", StringFormat("rasio impuls 60 / rata-rata 13,571 = 4,421 (%.4f)", r0), MathAbs(r0 - 60.0 / (190.0 / 14.0)) < 1e-9);
   TnwBars(h, l, 14, 7, 60.0);
   double r7 = ImpulseRatio(h, l, 14);
   TnwBars(h, l, 14, 8, 60.0);
   double r8 = ImpulseRatio(h, l, 14);
   AssertTrue("TC-NW-12b", StringFormat("puncak di bar ke-8 dihitung (%.4f), ke-9 tidak (%.4f)", r7, r8),
              MathAbs(r7 - r0) < 1e-9 && MathAbs(r8 - 10.0 / (190.0 / 14.0)) < 1e-9);
   TnwBars(h, l, 13, 0, 60.0);
   bool shortNull = ImpulseRatio(h, l, 13) == SDB_NULL_DOUBLE;
   TnwBars(h, l, 14, 0, 0.0);
   for(int i = 0; i < 14; i++)
      h[i] = l[i];
   bool zeroNull = ImpulseRatio(h, l, 14) == SDB_NULL_DOUBLE;
   AssertTrue("TC-NW-12c", "kurang dari 14 bar atau range nol -> null", shortNull && zeroNull);

   datetime bar = TNW_DAY + 14 * 3600;
   SdbNewsEvent ev[];
   TnwPush(ev, TnwEv(bar - 90 * 60, "USD", SDB_NEWS_HIGH, "Batas90"));
   int at90 = FindRecentHigh(ev, bar, "USD", "CAD", 90);
   SdbNewsEvent ev2[];
   TnwPush(ev2, TnwEv(bar - 91 * 60, "USD", SDB_NEWS_HIGH, "Lewat91"));
   TnwPush(ev2, TnwEv(bar + 60, "USD", SDB_NEWS_HIGH, "BelumRilis"));
   TnwPush(ev2, TnwEv(bar - 10 * 60, "USD", SDB_NEWS_MEDIUM, "Medium"));
   TnwPush(ev2, TnwEv(bar - 10 * 60, "EUR", SDB_NEWS_HIGH, "EurUntukUsdJpy"));
   int none = FindRecentHigh(ev2, bar, "USD", "JPY", 90);
   SdbNewsEvent ev3[];
   TnwPush(ev3, TnwEv(bar - 80 * 60, "USD", SDB_NEWS_HIGH, "Lama"));
   TnwPush(ev3, TnwEv(bar - 20 * 60, "CAD", SDB_NEWS_HIGH, "Baru"));
   int recent = FindRecentHigh(ev3, bar, "USD", "CAD", 90);
   AssertTrue("TC-NW-13", StringFormat("berita HIGH terbaru: 90 menit inklusif (%d), 91 / belum rilis / medium / mata uang lain tidak (%d), terbaru dipilih (%s)",
                                       at90, none, recent >= 0 ? ev3[recent].name : "-"),
              at90 == 0 && none < 0 && recent == 1);

   SdbNewsParams p = TnwParams();
   p.impulseMult = 5.0;
   p.impulseMinutes = 90;
   SdbNewsEvent cpi[];
   TnwPush(cpi, TnwEv(bar - 60 * 60, "USD", SDB_NEWS_HIGH, "CPI m/m"));
   string d = "";
   bool at5 = ImpulseDecision(cpi, bar, "USD", "CAD", p, 5.0, d);
   string d2 = "";
   bool below = ImpulseDecision(cpi, bar, "USD", "CAD", p, 4.99, d2);
   SdbNewsEvent empty[];
   string d3 = "";
   bool noNews = ImpulseDecision(empty, bar, "USD", "CAD", p, 9.0, d3);
   SdbNewsParams off = p;
   off.impulseMult = 0.0;
   string d4 = "";
   bool multOff = ImpulseDecision(cpi, bar, "USD", "CAD", off, 9.0, d4);
   SdbNewsParams dis = p;
   dis.enabled = false;
   string d5 = "";
   bool disabled = ImpulseDecision(cpi, bar, "USD", "CAD", dis, 9.0, d5);
   string d6 = "";
   bool nullRatio = ImpulseDecision(cpi, bar, "USD", "CAD", p, SDB_NULL_DOUBLE, d6);
   string d7 = "";
   bool xau = ImpulseDecision(cpi, bar, "XAU", "USD", p, 9.0, d7);
   AssertTrue("TC-NW-14", "keputusan impuls: 5,00 + CPI 60m tolak (" + d + "); 4,99 / tanpa berita / mult 0 / filter mati / rasio null lolos; XAU lewat USD tolak",
              at5 && d == "impuls x5.00 sesudah CPI m/m USD HIGH 60m" && !below && !noNews && !multOff && !disabled && !nullRatio && xau);
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
   RunTestNewsImpulse();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTNEWSRULES_MQH
