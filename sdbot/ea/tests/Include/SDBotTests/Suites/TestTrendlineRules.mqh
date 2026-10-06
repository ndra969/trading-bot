//+------------------------------------------------------------------+
//| TestTrendlineRules.mqh — skor trendline sebagai fungsi murni (spec
//| 19 design §3.1, §5.1; TC-TL-01..11). Bar sintetis: garis lurus
//| base + step x; swing diletakkan tepat di garis, bar lain 0,5 ATR
//| di sisi luar sehingga hanya swing yang menyentuh garis.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTTRENDLINERULES_MQH
#define SDB_SUITES_TESTTRENDLINERULES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/InputRules.mqh>
#include <SDBot/Strategies/TrendlineRules.mqh>

#define TTL_N        40
#define TTL_STRENGTH 2
#define TTL_LOOKBACK 100

// support = garis di bawah harga (swing low di garis); selain itu resistance (swing high di garis).
void TtlBuild(MqlRates &r[], const double base, const double step, const double unit, const bool support, const int &swings[])
  {
   ArrayResize(r, TTL_N);
   for(int x = 0; x < TTL_N; x++)
     {
      ZeroMemory(r[x]);
      r[x].time = D'2026.06.01 00:00' + x * 3600;
      double line = base + step * x;
      bool onLine = false;
      for(int k = 0; k < ArraySize(swings); k++)
         if(swings[k] == x)
            onLine = true;
      if(support)
        {
         r[x].low = onLine ? line : line + 0.5 * unit;
         r[x].high = r[x].low + unit;
         r[x].close = r[x].low + 0.5 * unit;
        }
      else
        {
         r[x].high = onLine ? line : line - 0.5 * unit;
         r[x].low = r[x].high - unit;
         r[x].close = r[x].high - 0.5 * unit;
        }
      r[x].open = r[x].close;
     }
  }

SdbZone TtlZone(const bool demand, const double distal, const double proximal)
  {
   SdbZone z;
   ZeroMemory(z);
   z.demand = demand;
   z.distal = distal;
   z.proximal = proximal;
   z.status = SDB_ZONE_FRESH;
   return z;
  }

SdbTrendlineResult TtlEval(const MqlRates &r[], const SdbZone &z, const bool buy, const double atr)
  {
   SdbTrendlineResult res;
   TlEvaluate(r, z, buy, TTL_STRENGTH, TTL_LOOKBACK, atr, res);
   return res;
  }

void RunTestTrendlineRules()
  {
   TfBeginSuite("TrendlineRules");
   MqlRates r[];
   const double atr = 0.0010;
   // Support naik 0,1 ATR per bar: garis di bar 40 = 1.1040; zona demand 1.1035..1.1045 memuat proyeksi.
   SdbZone zd = TtlZone(true, 1.1035, 1.1045);
   int s3[] = {10, 20, 30};
   TtlBuild(r, 1.1000, 0.0001, atr, true, s3);
   SdbTrendlineResult a = TtlEval(r, zd, true, atr);
   AssertTrue("TC-TL-01", StringFormat("BUY support naik 3 sentuhan: skor %d sentuhan %d kemiringan %.3f jarak %.2f '%s'", a.score, a.touches, a.slopeAtr,
                                       a.distAtr, a.reason),
              a.score == 15 && a.touches == 3 && MathAbs(a.slopeAtr - 0.1) < 1e-6 && a.distAtr == 0.0);

   int s2[] = {10, 20};
   TtlBuild(r, 1.1000, 0.0001, atr, true, s2);
   SdbTrendlineResult b = TtlEval(r, zd, true, atr);
   AssertTrue("TC-TL-02", StringFormat("BUY 2 sentuhan: skor %d sentuhan %d", b.score, b.touches), b.score == 7 && b.touches == 2);

   // Bug bot Python: support TURUN melewati zona demand ikut memperkuat BUY.
   TtlBuild(r, 1.1040, -0.0001, atr, true, s3);
   SdbTrendlineResult c = TtlEval(r, TtlZone(true, 1.0995, 1.1005), true, atr);
   AssertTrue("TC-TL-03", StringFormat("BUY dengan support turun: skor %d '%s'", c.score, c.reason), c.score == 0);

   // SELL: resistance turun 0,1 ATR per bar, garis di bar 40 = 1.1060; zona supply 1.1065..1.1055.
   TtlBuild(r, 1.1100, -0.0001, atr, false, s3);
   SdbTrendlineResult d = TtlEval(r, TtlZone(false, 1.1065, 1.1055), false, atr);
   AssertTrue("TC-TL-04", StringFormat("SELL resistance turun 3 sentuhan: skor %d sentuhan %d kemiringan %.3f", d.score, d.touches, d.slopeAtr),
              d.score == 15 && d.touches == 3 && MathAbs(d.slopeAtr + 0.1) < 1e-6);

   // Kemiringan 0,01 ATR per bar (< 0,02): bukan trendline.
   TtlBuild(r, 1.1000, 0.00001, atr, true, s3);
   SdbTrendlineResult e = TtlEval(r, TtlZone(true, 1.0999, 1.1009), true, atr);
   AssertTrue("TC-TL-05", StringFormat("garis datar: skor %d", e.score), e.score == 0);

   // Close bar 15 menembus support 0,5 ATR: garis lewat 10 tidak berlaku; tersisa garis 20-30 (2 sentuhan).
   TtlBuild(r, 1.1000, 0.0001, atr, true, s3);
   r[15].close = 1.1000 + 0.0001 * 15 - 0.0005;
   r[15].low = r[15].close - 0.0001;
   SdbTrendlineResult f = TtlEval(r, zd, true, atr);
   AssertTrue("TC-TL-06", StringFormat("garis patah oleh close: skor %d sentuhan %d", f.score, f.touches), f.score == 7 && f.touches == 2);

   TtlBuild(r, 1.1000, 0.0001, atr, true, s3);
   SdbTrendlineResult far = TtlEval(r, TtlZone(true, 1.1045, 1.1055), true, atr);       // 0,5 ATR di atas proyeksi
   SdbTrendlineResult near = TtlEval(r, TtlZone(true, 1.10415, 1.10515), true, atr);    // 0,15 ATR
   AssertTrue("TC-TL-07", StringFormat("proyeksi 0,5 ATR dari zona: skor %d; 0,15 ATR: skor %d jarak %.2f", far.score, near.score, near.distAtr),
              far.score == 0 && near.score == 15 && MathAbs(near.distAtr - 0.15) < 1e-6);

   int s4[] = {5, 10, 20, 30};
   TtlBuild(r, 1.1000, 0.0001, atr, true, s4);
   SdbTrendlineResult g = TtlEval(r, zd, true, atr);
   AssertTrue("TC-TL-08", StringFormat("4 swing segaris: sentuhan %d, titik %s / %s", g.touches, TimeToString(g.t1), TimeToString(g.t2)),
              g.score == 15 && g.touches == 4 && g.t1 == r[20].time && g.t2 == r[30].time);

   // Swing di bar 38 belum terkonfirmasi (perlu 2 bar kanan tutup): sentuhan tetap 3.
   int s5[] = {10, 20, 30, 38};
   TtlBuild(r, 1.1000, 0.0001, atr, true, s5);
   SdbTrendlineResult h = TtlEval(r, zd, true, atr);
   AssertTrue("TC-TL-09", StringFormat("swing belum terkonfirmasi: sentuhan %d", h.touches), h.touches == 3 && h.score == 15);

   // Skala USDJPY (x143) dan BTC (x50000) dengan proporsi sama.
   TtlBuild(r, 157.300, 0.0143, 0.143, true, s3);
   SdbTrendlineResult j = TtlEval(r, TtlZone(true, 157.300 + 0.0143 * 40 - 0.0715, 157.300 + 0.0143 * 40 + 0.0715), true, 0.143);
   TtlBuild(r, 60000.0, 5.0, 50.0, true, s3);
   SdbTrendlineResult k = TtlEval(r, TtlZone(true, 60175.0, 60225.0), true, 50.0);
   AssertTrue("TC-TL-10", StringFormat("JPY skor %d sentuhan %d; BTC skor %d sentuhan %d", j.score, j.touches, k.score, k.touches),
              j.score == 15 && j.touches == 3 && k.score == 15 && k.touches == 3);

   string err;
   InputValues v = DefaultInputValues();
   bool def = v.scoreTrendlineMode == SDB_COMPONENT_SHADOW && ValidateInputValues(v, false, err);
   v.scoreTrendlineMode = (ENUM_SDB_COMPONENT_MODE)3;
   err = "";
   bool bad = !ValidateInputValues(v, false, err) && StringFind(err, "InpScoreTrendlineMode") >= 0;
   AssertTrue("TC-TL-11", "input InpScoreTrendlineMode: default SHADOW lolos; 3 ditolak dengan nama", def && bad);
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTTRENDLINERULES_MQH
