//+------------------------------------------------------------------+
//| TestRsiRules.mqh — skor RSI divergence sebagai fungsi murni (spec
//| 21 design §3.1, §5.1; TC-RSI-01..10). Bar sintetis 40 bar dengan
//| swing di bar tertentu dan array RSI sintetis sejajar.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTRSIRULES_MQH
#define SDB_SUITES_TESTRSIRULES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/InputRules.mqh>
#include <SDBot/Strategies/RsiRules.mqh>
#include <SDBot/Strategies/Confirmations.mqh>

#define TRS_N        40
#define TRS_STRENGTH 2
#define TRS_LOOKBACK 100
#define TRS_ATR      0.0010

// lows: swing low di bar a dan b (harga pa, pb), bar lain 1.1020. RSI 50 kecuali di bar swing.
void TrsLows(MqlRates &r[], double &rsi[], const int a, const double pa, const double ra, const int b, const double pb, const double rb)
  {
   ArrayResize(r, TRS_N);
   ArrayResize(rsi, TRS_N);
   for(int i = 0; i < TRS_N; i++)
     {
      ZeroMemory(r[i]);
      r[i].time = D'2026.06.01 00:00' + i * 3600;
      r[i].low = 1.1020;
      if(i == a)
         r[i].low = pa;
      if(i == b)
         r[i].low = pb;
      r[i].high = r[i].low + 0.0010;
      r[i].close = r[i].low + 0.0005;
      r[i].open = r[i].close;
      rsi[i] = (i == a) ? ra : ((i == b) ? rb : 50.0);
     }
  }

// highs: swing high di bar a dan b, bar lain 1.1080.
void TrsHighs(MqlRates &r[], double &rsi[], const int a, const double pa, const double ra, const int b, const double pb, const double rb)
  {
   ArrayResize(r, TRS_N);
   ArrayResize(rsi, TRS_N);
   for(int i = 0; i < TRS_N; i++)
     {
      ZeroMemory(r[i]);
      r[i].time = D'2026.06.01 00:00' + i * 3600;
      r[i].high = 1.1080;
      if(i == a)
         r[i].high = pa;
      if(i == b)
         r[i].high = pb;
      r[i].low = r[i].high - 0.0010;
      r[i].close = r[i].high - 0.0005;
      r[i].open = r[i].close;
      rsi[i] = (i == a) ? ra : ((i == b) ? rb : 50.0);
     }
  }

SdbRsiResult TrsEval(const MqlRates &r[], const double &rsi[], const bool buy)
  {
   SdbRsiResult res;
   RsiEvaluate(r, rsi, buy, TRS_STRENGTH, TRS_LOOKBACK, TRS_ATR, res);
   return res;
  }

void RunTestRsiRules()
  {
   TfBeginSuite("RsiRules");
   MqlRates r[];
   double rsi[];

   TrsLows(r, rsi, 15, 1.1000, 30.0, 30, 1.0990, 35.0);
   SdbRsiResult a = TrsEval(r, rsi, true);
   AssertTrue("TC-RSI-01", StringFormat("bullish divergence: skor %d diff %.1f harga %.2f ATR umur %d '%s'", a.score, a.rsiDiff, a.priceDiffAtr,
                                        a.ageBars, a.reason),
              a.score == 5 && a.have && MathAbs(a.rsiDiff - 5.0) < 1e-9 && MathAbs(a.priceDiffAtr - 1.0) < 1e-6 && a.ageBars == 10);

   TrsLows(r, rsi, 15, 1.1000, 30.0, 30, 1.0990, 25.0);
   SdbRsiResult b = TrsEval(r, rsi, true);
   AssertTrue("TC-RSI-02", StringFormat("lower low harga dan RSI: skor %d diff %.1f", b.score, b.rsiDiff), b.score == 0 && MathAbs(b.rsiDiff + 5.0) < 1e-9);

   TrsLows(r, rsi, 15, 1.1000, 30.0, 30, 1.1000, 35.0);
   SdbRsiResult c = TrsEval(r, rsi, true);
   AssertTrue("TC-RSI-03", StringFormat("low sama persis: skor %d", c.score), c.score == 0);

   TrsLows(r, rsi, 15, 1.1000, 30.0, 30, 1.0990, 31.5);
   SdbRsiResult d = TrsEval(r, rsi, true);
   AssertTrue("TC-RSI-04", StringFormat("selisih RSI 1,5 (< 2): skor %d", d.score), d.score == 0);

   TrsHighs(r, rsi, 15, 1.1100, 70.0, 30, 1.1110, 64.0);
   SdbRsiResult e = TrsEval(r, rsi, false);
   AssertTrue("TC-RSI-05", StringFormat("bearish divergence: skor %d diff %.1f", e.score, e.rsiDiff), e.score == 5 && MathAbs(e.rsiDiff - 6.0) < 1e-9);

   SdbRsiResult f = TrsEval(r, rsi, true);   // data bearish, kandidat BUY: swing low tidak ada
   AssertTrue("TC-RSI-06", StringFormat("divergence lawan arah: skor %d '%s'", f.score, f.reason), f.score == 0 && !f.have);

   TrsLows(r, rsi, 5, 1.1000, 30.0, 15, 1.0990, 35.0);
   SdbRsiResult g = TrsEval(r, rsi, true);
   AssertTrue("TC-RSI-07", StringFormat("swing kedua 25 bar dari kandidat: skor %d umur %d", g.score, g.ageBars), g.score == 0 && g.ageBars == 25);

   TrsLows(r, rsi, 30, 1.0990, 35.0, 30, 1.0990, 35.0);
   SdbRsiResult h = TrsEval(r, rsi, true);
   AssertTrue("TC-RSI-08", StringFormat("satu swing: skor %d have %s '%s'", h.score, h.have ? "true" : "false", h.reason), h.score == 0 && !h.have);

   TrsLows(r, rsi, 15, 1.1000, 30.0, 30, 1.0990, 35.0);
   ArrayResize(rsi, TRS_N - 1);
   SdbRsiResult k = TrsEval(r, rsi, true);
   AssertTrue("TC-RSI-09", StringFormat("RSI tidak sejajar (39 vs 40): skor %d '%s'", k.score, k.reason), k.score == 0 && k.reason == "data kurang");

   // TC-RSI-11 (Req 1.1, 1.2): handle iRSI H1 nyata di tester; salinan berdasarkan waktu bar sejajar n nilai; handle tidak valid = false.
   MqlRates h1[];
   int got = CopyRates(_Symbol, PERIOD_H1, 1, 50, h1);
   int hRsi = iRSI(_Symbol, PERIOD_H1, SDB_RSI_PERIOD, PRICE_CLOSE);
   double buf[];
   bool okCopy = got == 50 && hRsi != INVALID_HANDLE && RsiCopyAligned(hRsi, h1, buf);
   bool inRange = ArraySize(buf) == 50;
   for(int i = 0; i < ArraySize(buf) && inRange; i++)
      inRange = buf[i] > 0.0 && buf[i] < 100.0;
   double none[];
   bool invalid = !RsiCopyAligned(INVALID_HANDLE, h1, none) && ArraySize(none) == 0;
   bool released = hRsi != INVALID_HANDLE && IndicatorRelease(hRsi);
   AssertTrue("TC-RSI-11", StringFormat("iRSI H1: bar %d, salinan %d nilai dalam 0..100 %s, handle tidak valid ditolak %s, dilepas %s", got, ArraySize(buf),
                                        inRange ? "ya" : "tidak", invalid ? "ya" : "tidak", released ? "ya" : "tidak"),
              okCopy && inRange && invalid && released);

   string err;
   InputValues v = DefaultInputValues();
   bool def = v.scoreRsiMode == SDB_COMPONENT_SHADOW && ValidateInputValues(v, false, err);
   v.scoreRsiMode = (ENUM_SDB_COMPONENT_MODE)3;
   err = "";
   bool bad = !ValidateInputValues(v, false, err) && StringFind(err, "InpScoreRsiMode") >= 0;
   AssertTrue("TC-RSI-10", "input InpScoreRsiMode: default SHADOW lolos; 3 ditolak dengan nama", def && bad);
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTRSIRULES_MQH
