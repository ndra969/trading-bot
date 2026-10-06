//+------------------------------------------------------------------+
//| TestBreakoutRules.mqh — skor breakout & retest sebagai fungsi murni
//| (spec 20 design §3.1, §5.1; TC-BO-01..11). Bar sintetis dalam
//| satuan u (= ATR): level swing di base + 5u, harga lain diatur per
//| kasus. Swing strength 2.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTBREAKOUTRULES_MQH
#define SDB_SUITES_TESTBREAKOUTRULES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/InputRules.mqh>
#include <SDBot/Strategies/BreakoutRules.mqh>

#define TBO_N        40
#define TBO_STRENGTH 2
#define TBO_LOOKBACK 100

void TboSet(MqlRates &r[], const int i, const double high, const double low, const double close)
  {
   r[i].high = high;
   r[i].low = low;
   r[i].close = close;
   r[i].open = close;
  }

void TboInit(MqlRates &r[])
  {
   ArrayResize(r, TBO_N);
   for(int i = 0; i < TBO_N; i++)
     {
      ZeroMemory(r[i]);
      r[i].time = D'2026.06.01 00:00' + i * 3600;
     }
  }

// BUY: resistance base+5u (swing bar 10) ditembus close bar 20 (base+6u); breakFrac menggeser close tembus; sesudahnya di atas level.
void TboBuy(MqlRates &r[], const double base, const double u)
  {
   TboInit(r);
   for(int i = 0; i < 20; i++)
      TboSet(r, i, base + 4 * u, base + 3 * u, base + 3.5 * u);
   TboSet(r, 10, base + 5 * u, base + 4 * u, base + 4.5 * u);
   TboSet(r, 20, base + 6.5 * u, base + 5 * u, base + 6 * u);
   for(int i = 21; i < TBO_N; i++)
      TboSet(r, i, base + 8 * u, base + 6 * u, base + 7 * u);
  }

// SELL cerminan: support base+5u (swing low bar 10) ditembus turun close bar 20 (base+4u).
void TboSell(MqlRates &r[], const double base, const double u)
  {
   TboInit(r);
   for(int i = 0; i < 20; i++)
      TboSet(r, i, base + 7 * u, base + 6 * u, base + 6.5 * u);
   TboSet(r, 10, base + 6 * u, base + 5 * u, base + 5.5 * u);
   TboSet(r, 20, base + 5 * u, base + 3.5 * u, base + 4 * u);
   for(int i = 21; i < TBO_N; i++)
      TboSet(r, i, base + 4 * u, base + 2 * u, base + 3 * u);
  }

SdbZone TboZone(const bool demand, const double distal, const double proximal)
  {
   SdbZone z;
   ZeroMemory(z);
   z.demand = demand;
   z.distal = distal;
   z.proximal = proximal;
   z.status = SDB_ZONE_FRESH;
   return z;
  }

SdbBreakoutResult TboEval(const MqlRates &r[], const SdbZone &z, const bool buy, const double atr)
  {
   SdbBreakoutResult res;
   BoEvaluate(r, z, buy, TBO_STRENGTH, TBO_LOOKBACK, atr, res);
   return res;
  }

void RunTestBreakoutRules()
  {
   TfBeginSuite("BreakoutRules");
   MqlRates r[];
   const double b = 1.1000, u = 0.0010;
   SdbZone zd = TboZone(true, b + 4.5 * u, b + 5.5 * u);

   TboBuy(r, b, u);
   SdbBreakoutResult a = TboEval(r, zd, true, u);
   AssertTrue("TC-BO-01", StringFormat("BUY tembus + retest: skor %d level %.5f umur %d jarak %.2f '%s'", a.score, a.level, a.ageBars, a.distAtr,
                                       a.reason),
              a.score == 10 && MathAbs(a.level - (b + 5 * u)) < 1e-9 && a.ageBars == 20 && a.distAtr == 0.0 && a.tBreak == r[20].time);

   TboBuy(r, b, u);
   TboSet(r, 20, b + 6.5 * u, b + 4 * u, b + 4.8 * u);   // wick di atas level, close di bawah
   for(int i = 21; i < TBO_N; i++)
      TboSet(r, i, b + 4.5 * u, b + 3.5 * u, b + 4 * u);
   SdbBreakoutResult w = TboEval(r, zd, true, u);
   AssertTrue("TC-BO-02", StringFormat("hanya wick: skor %d", w.score), w.score == 0);

   TboBuy(r, b, u);
   TboSet(r, 25, b + 6 * u, b + 2 * u, b + 2.5 * u);      // close kembali 2,5u di bawah level (> 0,2 ATR)
   SdbBreakoutResult fl = TboEval(r, zd, true, u);
   AssertTrue("TC-BO-03", StringFormat("breakout gagal: skor %d", fl.score), fl.score == 0);

   TboSell(r, b, u);                                      // support ditembus turun; kandidat BUY tidak memakainya
   SdbBreakoutResult opp = TboEval(r, zd, true, u);
   AssertTrue("TC-BO-04", StringFormat("tembus melawan arah sinyal: skor %d", opp.score), opp.score == 0);

   TboInit(r);
   for(int i = 0; i < TBO_N; i++)
      TboSet(r, i, b + 4 * u, b + 3 * u, b + 3.5 * u);
   TboSet(r, 38, b + 5 * u, b + 4 * u, b + 4.5 * u);     // calon swing bar 38 belum punya 2 bar kanan
   TboSet(r, 39, b + 6.5 * u, b + 5 * u, b + 6 * u);
   SdbBreakoutResult un = TboEval(r, zd, true, u);
   AssertTrue("TC-BO-05", StringFormat("swing belum terkonfirmasi: skor %d", un.score), un.score == 0);

   // Dua level: 5u (tembus bar 15) dan 5,3u (swing bar 22, tembus bar 30); keduanya di zona -> terbaru (bar 30).
   TboInit(r);
   for(int i = 0; i < 15; i++)
      TboSet(r, i, b + 4 * u, b + 3 * u, b + 3.5 * u);
   TboSet(r, 10, b + 5 * u, b + 4 * u, b + 4.5 * u);
   TboSet(r, 15, b + 6 * u, b + 5 * u, b + 5.8 * u);
   for(int i = 16; i < 30; i++)
      TboSet(r, i, b + 5.1 * u, b + 4.6 * u, b + 4.9 * u);
   TboSet(r, 22, b + 5.3 * u, b + 4.8 * u, b + 4.9 * u);
   TboSet(r, 30, b + 6.5 * u, b + 5.5 * u, b + 6.2 * u);
   for(int i = 31; i < TBO_N; i++)
      TboSet(r, i, b + 7.5 * u, b + 6 * u, b + 7 * u);
   SdbBreakoutResult two = TboEval(r, zd, true, u);
   AssertTrue("TC-BO-06", StringFormat("dua level: level %.5f tembus %s", two.level, TimeToString(two.tBreak)),
              two.score == 10 && MathAbs(two.level - (b + 5.3 * u)) < 1e-9 && two.tBreak == r[30].time);

   TboBuy(r, b, u);
   SdbBreakoutResult far = TboEval(r, TboZone(true, b + 5.5 * u, b + 6.5 * u), true, u);      // level 0,5 ATR di bawah zona
   SdbBreakoutResult near = TboEval(r, TboZone(true, b + 5.15 * u, b + 6.15 * u), true, u);   // 0,15 ATR
   AssertTrue("TC-BO-07", StringFormat("level 0,5 ATR dari zona: %d; 0,15 ATR: %d jarak %.2f", far.score, near.score, near.distAtr),
              far.score == 0 && near.score == 10 && MathAbs(near.distAtr - 0.15) < 1e-6);

   TboSell(r, b, u);
   SdbBreakoutResult s = TboEval(r, TboZone(false, b + 5.5 * u, b + 4.5 * u), false, u);
   AssertTrue("TC-BO-08", StringFormat("SELL tembus + retest: skor %d level %.5f", s.score, s.level),
              s.score == 10 && MathAbs(s.level - (b + 5 * u)) < 1e-9);

   TboBuy(r, 157.000, 0.143);
   SdbBreakoutResult j = TboEval(r, TboZone(true, 157.000 + 4.5 * 0.143, 157.000 + 5.5 * 0.143), true, 0.143);
   TboBuy(r, 60000.0, 50.0);
   SdbBreakoutResult k = TboEval(r, TboZone(true, 60225.0, 60275.0), true, 50.0);
   AssertTrue("TC-BO-09", StringFormat("JPY skor %d; BTC skor %d", j.score, k.score), j.score == 10 && k.score == 10);

   TboBuy(r, b, u);
   TboSet(r, 20, b + 5.5 * u, b + 4.9 * u, b + 5.05 * u);   // tembus 0,05 ATR
   for(int i = 21; i < TBO_N; i++)
      TboSet(r, i, b + 5.3 * u, b + 4.9 * u, b + 5.05 * u);
   SdbBreakoutResult small = TboEval(r, zd, true, u);
   AssertTrue("TC-BO-10", StringFormat("tembus 0,05 ATR: skor %d", small.score), small.score == 0);

   string err;
   InputValues v = DefaultInputValues();
   bool def = v.scoreBreakoutMode == SDB_COMPONENT_SHADOW && ValidateInputValues(v, false, err);
   v.scoreBreakoutMode = (ENUM_SDB_COMPONENT_MODE)3;
   err = "";
   bool bad = !ValidateInputValues(v, false, err) && StringFind(err, "InpScoreBreakoutMode") >= 0;
   AssertTrue("TC-BO-11", "input InpScoreBreakoutMode: default SHADOW lolos; 3 ditolak dengan nama", def && bad);
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTBREAKOUTRULES_MQH
