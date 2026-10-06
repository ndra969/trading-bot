//+------------------------------------------------------------------+
//| TestSignalRules.mqh — aturan sinyal sebagai fungsi murni: input,
//| tahap tolak, skor, SL/TP/R:R, ID sinyal, konteks (spec 13 design
//| §3.1, §6.1; TC-SG-01..23). Nilai dihitung tangan.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTSIGNALRULES_MQH
#define SDB_SUITES_TESTSIGNALRULES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/InputRules.mqh>
#include <SDBot/Signals/SignalRules.mqh>

void RunTestSignalInputs()
  {
   string err;
   InputValues v = DefaultInputValues();
   bool defaults = MathAbs(v.minConfluenceScore - 65.0) < 1e-9 && MathAbs(v.minRR - 2.0) < 1e-9 &&
                   MathAbs(v.slBufferAtr - 0.1) < 1e-9 && MathAbs(v.minSlAtr - 0.3) < 1e-9 &&
                   MathAbs(v.maxSlAtr - 3.0) < 1e-9 && ValidateInputValues(v, false, err);
   string names[] = {"InpMinRR", "InpMinConfluenceScore", "InpSlBufferAtr", "InpMinSlAtr", "InpMaxSlAtr", "InpMinConfluenceScore",
                     "InpSlBufferAtr", "InpMinSlAtr"};
   int bad = 0;
   for(int i = 0; i < ArraySize(names); i++)
     {
      v = DefaultInputValues();
      switch(i)
        {
         case 0: v.minRR = 0.9; break;
         case 1: v.minConfluenceScore = 101.0; break;
         case 2: v.slBufferAtr = -0.1; break;
         case 3: v.minSlAtr = 0.04; break;
         case 4: v.maxSlAtr = 10.1; break;
         case 5: v.minConfluenceScore = -1.0; break;
         case 6: v.slBufferAtr = 1.01; break;
         default: v.minSlAtr = 2.0; v.maxSlAtr = 2.0; break;
        }
      err = "";
      if(ValidateInputValues(v, false, err) || StringFind(err, names[i]) < 0)
         bad++;
     }
   v = DefaultInputValues();
   v.minConfluenceScore = 0.0;
   v.minRR = 10.0;
   v.slBufferAtr = 0.0;
   v.minSlAtr = 0.05;
   v.maxSlAtr = 10.0;
   bool edges = ValidateInputValues(v, false, err);
   AssertTrue("TC-SG-23", StringFormat("input sinyal: default 65/2.0/0.1/0.3/3.0 lolos, batas tepi lolos, salah ditolak dengan nama (gagal %d)", bad),
              defaults && edges && bad == 0);
  }

SdbSignalParams SgP0()
  {
   SdbSignalParams p;
   p.minScorePct = 65.0;
   p.minRR = 2.0;
   p.slBufferAtr = 0.1;
   p.minSlAtr = 0.3;
   p.maxSlAtr = 3.0;
   p.maxSpreadPoints = 0;
   return p;
  }

SdbPattern SgPat(const string code, const ENUM_SDB_DIR dir)
  {
   SdbPattern p;
   p.code = code;
   p.dir = dir;
   p.score = PaScore(code);
   p.barTime = D'2026.06.01 10:00';
   return p;
  }

// F0 (design §6.1): EURUSDc, ATR MTF 0.0010, demand Fresh 1.10000-1.10060, bid/ask 1.10080/1.10090, PIN BULL, tren 7.
SdbSignalFacts SgF0()
  {
   SdbSignalFacts f;
   ZeroMemory(f);
   f.dir = SDB_DIR_BULL;
   f.zone.id = "H1-1780000000-D";
   f.zone.demand = true;
   f.zone.distal = 1.10000;
   f.zone.proximal = 1.10060;
   f.zone.atr = 0.0010;
   f.zone.status = SDB_ZONE_FRESH;
   f.zone.used = false;
   f.preStage = "";
   f.preDetail = "";
   f.positionOpen = false;
   f.pattern = SgPat(SDB_PA_PATTERN_PIN, SDB_DIR_BULL);
   f.trendScore = 7;
   f.bid = 1.10080;
   f.ask = 1.10090;
   f.point = 0.00001;
   f.digits = 5;
   f.stopsLevel = 0;
   f.atrMtf = 0.0010;
   f.haveOpposite = false;
   f.oppositeProximal = 0.0;
   f.session = "OVERLAP";
   f.sessionAllowed = true;
   f.spreadPoints = 10;
   f.newsBlocked = false;
   f.newsDetail = "";
   f.newsStatus = "ON";
   f.newsNext = "";
   f.fibMode = SDB_COMPONENT_OFF;
   ZeroMemory(f.fib);
   f.fib.ratio = -1.0;
   f.fib.reason = "";
   return f;
  }

SdbDecision SgEval(const SdbSignalFacts &f)
  {
   SdbDecision d;
   EvaluateSignal(f, SgP0(), d);
   return d;
  }

bool SgNear(const double a, const double b) { return MathAbs(a - b) < 1e-9; }

void RunTestSignalStops()
  {
   SdbSignalFacts f = SgF0();
   f.haveOpposite = true;
   f.oppositeProximal = 1.10350;
   SdbDecision d = SgEval(f);
   AssertTrue("TC-SG-01", StringFormat("F0 + zona lawan 1.10350: lolos, SL 1.09990, R 0.00100, TP 1.10350, R:R 2.60 ZONE (stage=%s sl=%.5f tp=%.5f rr=%.2f)",
                                        d.stage, d.stops.sl, d.stops.tp, d.stops.rr),
              d.stage == "" && d.stopsKnown && SgNear(d.stops.entry, 1.10090) && SgNear(d.stops.sl, 1.09990) &&
              SgNear(d.stops.risk, 0.00100) && SgNear(d.stops.tp, 1.10350) && MathAbs(d.stops.rr - 2.6) < 1e-6 &&
              d.stops.tpSource == SDB_TP_SOURCE_ZONE);

   f = SgF0();
   d = SgEval(f);
   AssertTrue("TC-SG-02", "tanpa zona lawan: TP 1.10290 = 2R, sumber RR",
              d.stage == "" && SgNear(d.stops.tp, 1.10290) && MathAbs(d.stops.rr - 2.0) < 1e-6 && d.stops.tpSource == SDB_TP_SOURCE_RR);

   f.haveOpposite = true;
   f.oppositeProximal = 1.10280;
   d = SgEval(f);
   AssertTrue("TC-SG-03", "zona lawan 1.10280 (R:R 1.90): RR_TOO_LOW | " + d.detail, d.stage == SDB_REJECT_STAGE_RR_TOO_LOW);

   f.oppositeProximal = 1.10290;
   d = SgEval(f);
   AssertTrue("TC-SG-04", "zona lawan tepat 1.10290 (R:R 2.00 inklusif): lolos | " + d.stage + " " + d.detail, d.stage == "");

   f = SgF0();
   f.dir = SDB_DIR_BEAR;
   f.zone.demand = false;
   f.zone.distal = 1.10200;
   f.zone.proximal = 1.10140;
   f.bid = 1.10120;
   f.ask = 1.10130;
   f.pattern = SgPat(SDB_PA_PATTERN_PIN, SDB_DIR_BEAR);
   d = SgEval(f);
   AssertTrue("TC-SG-05", StringFormat("SELL: SL 1.10220 (+ buffer + spread), R 0.00100, TP 2R 1.09920 (stage=%s sl=%.5f tp=%.5f)", d.stage, d.stops.sl, d.stops.tp),
              d.stage == "" && SgNear(d.stops.entry, 1.10120) && SgNear(d.stops.sl, 1.10220) && SgNear(d.stops.risk, 0.00100) &&
              SgNear(d.stops.tp, 1.09920));

   f = SgF0();
   f.zone.distal = 1.10070;
   d = SgEval(f);
   bool edge = d.stage == "" && SgNear(d.stops.risk, 0.00030);
   f.zone.distal = 1.10071;
   d = SgEval(f);
   AssertTrue("TC-SG-06", "R 0.3 ATR tepat lolos; R 0.00029: SL_TOO_CLOSE | " + d.detail, edge && d.stage == SDB_REJECT_STAGE_SL_TOO_CLOSE);

   f = SgF0();
   f.stopsLevel = 50;
   f.zone.distal = 1.10045;
   d = SgEval(f);
   AssertTrue("TC-SG-07", "stops level 50 pt + spread 10 pt > R 0.00055: SL_TOO_CLOSE | " + d.detail, d.stage == SDB_REJECT_STAGE_SL_TOO_CLOSE);

   f = SgF0();
   f.zone.distal = 1.09780;
   d = SgEval(f);
   AssertTrue("TC-SG-08", "R 0.00320 > 3 ATR: SL_TOO_FAR | " + d.detail, d.stage == SDB_REJECT_STAGE_SL_TOO_FAR);

   f = SgF0();
   f.bid = 1.09970;
   f.ask = 1.09980;
   d = SgEval(f);
   AssertTrue("TC-SG-09", "ask sudah di bawah SL: INVALID_STOPS | " + d.detail, d.stage == SDB_REJECT_STAGE_INVALID_STOPS);

   f = SgF0();
   f.zone.distal = 150.000;
   f.zone.proximal = 150.090;
   f.bid = 150.170;
   f.ask = 150.180;
   f.point = 0.001;
   f.digits = 3;
   f.atrMtf = 0.150;
   d = SgEval(f);
   AssertTrue("TC-SG-10", StringFormat("USDJPYc: SL 149.985, R 0.195, TP 150.570 (stage=%s sl=%.3f tp=%.3f)", d.stage, d.stops.sl, d.stops.tp),
              d.stage == "" && SgNear(d.stops.sl, 149.985) && MathAbs(d.stops.risk - 0.195) < 1e-9 && SgNear(d.stops.tp, 150.570));

   f = SgF0();
   f.zone.distal = 2350.00;
   f.zone.proximal = 2356.00;
   f.bid = 2362.30;
   f.ask = 2362.50;
   f.point = 0.01;
   f.digits = 2;
   f.atrMtf = 12.0;
   d = SgEval(f);
   AssertTrue("TC-SG-11", StringFormat("XAUUSDc: SL 2348.80, R 13.70, TP 2389.90 (stage=%s sl=%.2f tp=%.2f)", d.stage, d.stops.sl, d.stops.tp),
              d.stage == "" && MathAbs(d.stops.sl - 2348.80) < 1e-6 && MathAbs(d.stops.risk - 13.70) < 1e-6 && MathAbs(d.stops.tp - 2389.90) < 1e-6);
  }

void RunTestSignalScores()
  {
   SdbSignalFacts f = SgF0();
   f.haveOpposite = true;
   f.oppositeProximal = 1.10350;
   SdbDecision d = SgEval(f);
   AssertTrue("TC-SG-12", StringFormat("Fresh 30 + tren 7 + PIN 7 = 44, 80%%, lolos (total=%d pct=%.2f)", d.total, d.pct),
              d.zoneScore == 30 && d.trendScore == 7 && d.paScore == 7 && d.total == 44 && d.maxActive == 55 &&
              MathAbs(d.pct - 80.0) < 1e-9 && d.stage == "");

   f.zone.status = SDB_ZONE_TESTED;
   f.pattern = SgPat(SDB_PA_PATTERN_ENGULF_STRONG, SDB_DIR_BULL);
   d = SgEval(f);
   AssertTrue("TC-SG-13", StringFormat("Tested 15 + tren 7 + ENGULF_STRONG 10 = 32 (%.2f%%): SCORE_TOO_LOW", d.pct),
              d.total == 32 && MathAbs(d.pct - 3200.0 / 55.0) < 1e-9 && d.stage == SDB_REJECT_STAGE_SCORE_TOO_LOW);

   SdbSignalParams p0 = SgP0();
   p0.minScorePct = 0.0;
   SdbDecision d0;
   f.trendScore = 0;
   f.pattern = SgPat(SDB_PA_PATTERN_TWEEZER, SDB_DIR_BULL);
   EvaluateSignal(f, p0, d0);
   AssertTrue("TC-SG-14", StringFormat("ScorePct(36,55)=%.2f >= 65, ScorePct(35,55)=%.2f < 65, ambang 0 meloloskan skor 18", ScorePct(36, 55), ScorePct(35, 55)),
              ScorePct(36, 55) >= 65.0 && ScorePct(35, 55) < 65.0 && ScorePct(10, 0) == 0.0 && d0.total == 18 && d0.stage == "");

   f = SgF0();
   f.trendScore = 15;
   f.pattern = SgPat(SDB_PA_PATTERN_NONE, SDB_DIR_NONE);
   d = SgEval(f);
   AssertTrue("TC-SG-15", "tanpa pola: NO_PA_TRIGGER walau zona dan tren penuh, skor tetap 30/15/0",
              d.stage == SDB_REJECT_STAGE_NO_PA_TRIGGER && d.zoneScore == 30 && d.trendScore == 15 && d.paScore == 0 && d.total == 45);

   f = SgF0();
   f.pattern = SgPat(SDB_PA_PATTERN_PIN, SDB_DIR_BEAR);
   d = SgEval(f);
   AssertTrue("TC-SG-16", "pola arah berlawanan: NO_PA_TRIGGER, skor PA 0", d.stage == SDB_REJECT_STAGE_NO_PA_TRIGGER && d.paScore == 0);

   f = SgF0();
   f.preStage = SDB_REJECT_STAGE_STOPPED;
   f.positionOpen = true;
   f.pattern = SgPat(SDB_PA_PATTERN_NONE, SDB_DIR_NONE);
   string s1 = SgEval(f).stage;
   f.preStage = "";
   string s2 = SgEval(f).stage;
   f.positionOpen = false;
   string s3 = SgEval(f).stage;
   AssertTrue("TC-SG-17", "urutan: " + s1 + " > " + s2 + " > " + s3,
              s1 == SDB_REJECT_STAGE_STOPPED && s2 == SDB_REJECT_STAGE_POSITION_OPEN && s3 == SDB_REJECT_STAGE_NO_PA_TRIGGER);

   f = SgF0();
   f.zone.status = SDB_ZONE_TESTED;
   f.zone.distal = 1.10071;
   d = SgEval(f);
   AssertTrue("TC-SG-18", "skor 29 + SL terlalu dekat: SCORE_TOO_LOW dulu, SL/TP belum dihitung",
              d.stage == SDB_REJECT_STAGE_SCORE_TOO_LOW && !d.stopsKnown);
  }

void RunTestSignalMisc()
  {
   datetime bar = D'2026.06.01 00:00';
   AssertTrue("TC-SG-19", "bar basi: 00:15:05 / 00:30:00 tidak, 00:30:01 basi (M15)",
              !StaleLtfBar(bar, 900, bar + 905) && !StaleLtfBar(bar, 900, bar + 1800) && StaleLtfBar(bar, 900, bar + 1801));

   long a = SignalIdOf(123456, 0, 2026091901, bar);
   long b = SignalIdOf(123456, 0, 2026091901, bar);
   long ids[4];
   ids[0] = SignalIdOf(123457, 0, 2026091901, bar);
   ids[1] = SignalIdOf(123456, 7, 2026091901, bar);
   ids[2] = SignalIdOf(123456, 0, 2026091902, bar);
   ids[3] = SignalIdOf(123456, 0, 2026091901, bar + 900);
   bool distinct = true;
   for(int i = 0; i < 4; i++)
     {
      if(ids[i] == a || ids[i] <= 0 || ids[i] >= 0x4000000000000000)
         distinct = false;
      for(int j = i + 1; j < 4; j++)
         if(ids[i] == ids[j])
            distinct = false;
     }
   AssertTrue("TC-SG-20", "SignalIdOf deterministik, beda tiap kunci, 0 < id < 2^62 (" + IntegerToString(a) + ")",
              a == b && a > 0 && a < 0x4000000000000000 && distinct);

   SdbSignalFacts f = SgF0();
   f.haveOpposite = true;
   f.oppositeProximal = 1.10350;
   SdbDecision d = SgEval(f);
   string json = SignalContextJson(f, d, SgP0(), SDB_BIAS_OK);
   string expect = "{\"atr_mtf\":0.00100,\"bias_reason\":\"OK\",\"entry\":1.10090,\"fib_level\":null,\"fib_ratio\":null,\"max_active\":55,\"max_spread\":0,\"news\":\"ON\",\"news_next\":null,\"pa\":\"PIN\",\"rr\":2.60,"
                   "\"score_pct\":80.0,\"session\":\"OVERLAP\",\"sl\":1.09990,\"tp\":1.10350,\"tp_source\":\"ZONE\",\"zone_status\":\"FRESH\"}";
   AssertStrEq("TC-SG-21", "konteks sinyal lolos", json, expect);

   f = SgF0();
   f.pattern = SgPat(SDB_PA_PATTERN_NONE, SDB_DIR_NONE);
   d = SgEval(f);
   json = SignalContextJson(f, d, SgP0(), SDB_BIAS_OK);
   expect = "{\"atr_mtf\":0.00100,\"bias_reason\":\"OK\",\"entry\":null,\"fib_level\":null,\"fib_ratio\":null,\"max_active\":55,\"max_spread\":0,\"news\":\"ON\",\"news_next\":null,\"pa\":\"NONE\",\"rr\":null,"
            "\"score_pct\":67.3,\"session\":\"OVERLAP\",\"sl\":null,\"tp\":null,\"tp_source\":null,\"zone_status\":\"FRESH\"}";
   AssertStrEq("TC-SG-22", "konteks NO_PA_TRIGGER: harga null", json, expect);

   f = SgF0();
   f.fibMode = SDB_COMPONENT_SHADOW;
   f.fib.score = 11;
   f.fib.ratio = 0.63;
   f.fib.level = 0.618;
   d = SgEval(f);
   json = SignalContextJson(f, d, SgP0(), SDB_BIAS_OK);
   AssertTrue("TC-SG-22b", "konteks Fibonacci bayangan: " + json,
              StringFind(json, "\"fib_level\":0.618,\"fib_ratio\":0.630,\"max_active\":55,") >= 0);
  }

// TC-SG-28/29 (spec 18 Req 3.2-3.4): FIB hanya ikut skor gerbang dan maksimum pada mode ACTIVE.
void RunTestSignalFib()
  {
   SdbSignalFacts f = SgF0();
   f.trendScore = 15;
   f.fib.score = 15;
   f.fib.ratio = 0.5;
   f.fib.level = 0.5;
   f.fibMode = SDB_COMPONENT_OFF;
   SdbDecision off = SgEval(f);
   f.fibMode = SDB_COMPONENT_SHADOW;
   SdbDecision sh = SgEval(f);
   f.fibMode = SDB_COMPONENT_ACTIVE;
   SdbDecision ac = SgEval(f);
   AssertTrue("TC-SG-28", StringFormat("OFF %d/%d '%s', SHADOW %d/%d '%s', ACTIVE %d/%d (fib %d)", off.total, off.maxActive, off.stage,
                                       sh.total, sh.maxActive, sh.stage, ac.total, ac.maxActive, ac.fibScore),
              off.total == 52 && off.maxActive == 55 && sh.total == 52 && sh.maxActive == 55 && sh.stage == off.stage &&
              sh.fibScore == 15 && ac.total == 67 && ac.maxActive == 70);

   f = SgF0();
   f.trendScore = 0;                               // 30 + 0 + 7 = 37
   f.fibMode = SDB_COMPONENT_SHADOW;
   SdbDecision pass = SgEval(f);
   f.fibMode = SDB_COMPONENT_ACTIVE;               // fib 0: 37/70 = 52,9% < 65%
   SdbDecision fail = SgEval(f);
   AssertTrue("TC-SG-29", StringFormat("37/55 = %.1f%% '%s'; ACTIVE fib 0: %d/%d = %.1f%% '%s'", pass.pct, pass.stage, fail.total,
                                       fail.maxActive, fail.pct, fail.stage),
              pass.stage != SDB_REJECT_STAGE_SCORE_TOO_LOW && fail.stage == SDB_REJECT_STAGE_SCORE_TOO_LOW);
  }

// TC-SG-25/26 (spec 14 Req 2.2, 3.1): sesi dan spread setelah pre-filter risiko, sebelum POSITION_OPEN.
void RunTestSignalFilters()
  {
   SdbSignalFacts f = SgF0();
   f.sessionAllowed = false;
   f.session = "OFF";
   string s1 = SgEval(f).stage;
   string d1 = SgEval(f).detail;
   f.preStage = SDB_REJECT_STAGE_STOPPED;
   string s2 = SgEval(f).stage;
   f.preStage = "";
   f.positionOpen = true;
   string s3 = SgEval(f).stage;
   AssertTrue("TC-SG-25", "di luar sesi: " + s1 + " (" + d1 + "); + STOPPED: " + s2 + "; + posisi terbuka: " + s3,
              s1 == SDB_REJECT_STAGE_OUTSIDE_SESSION && StringFind(d1, "OFF") >= 0 && s2 == SDB_REJECT_STAGE_STOPPED &&
              s3 == SDB_REJECT_STAGE_OUTSIDE_SESSION);

   SdbSignalParams p = SgP0();
   p.maxSpreadPoints = 24;
   f = SgF0();
   f.spreadPoints = 25;
   SdbDecision a;
   EvaluateSignal(f, p, a);
   f.spreadPoints = 24;
   SdbDecision b;
   EvaluateSignal(f, p, b);
   f.spreadPoints = 25;
   f.sessionAllowed = false;
   SdbDecision c;
   EvaluateSignal(f, p, c);
   AssertTrue("TC-SG-26", "spread 25/24: " + a.stage + " (" + a.detail + "); 24/24: '" + b.stage + "'; luar sesi + spread lebar: " + c.stage,
              a.stage == SDB_REJECT_STAGE_SPREAD_TOO_WIDE && StringFind(a.detail, "spread=25") >= 0 && b.stage == "" &&
              c.stage == SDB_REJECT_STAGE_OUTSIDE_SESSION);
  }

// TC-SG-27 (spec 16 Req 1.4, EC-10): NEWS_BLACKOUT setelah pre-filter risiko, sebelum sesi.
void RunTestSignalNews()
  {
   SdbSignalFacts f = SgF0();
   f.newsBlocked = true;
   f.newsDetail = "Non-Farm Payrolls USD HIGH -12m";
   SdbDecision a = SgEval(f);
   f.preStage = SDB_REJECT_STAGE_STOPPED;
   string s2 = SgEval(f).stage;
   f.preStage = "";
   f.sessionAllowed = false;
   string s3 = SgEval(f).stage;
   AssertTrue("TC-SG-27", "berita: " + a.stage + " (" + a.detail + "); + STOPPED: " + s2 + "; + luar sesi: " + s3,
              a.stage == SDB_REJECT_STAGE_NEWS_BLACKOUT && a.detail == "Non-Farm Payrolls USD HIGH -12m" &&
              s2 == SDB_REJECT_STAGE_STOPPED && s3 == SDB_REJECT_STAGE_NEWS_BLACKOUT);
  }

void RunTestSignalRules()
  {
   TfBeginSuite("SignalRules");
   RunTestSignalInputs();
   RunTestSignalStops();
   RunTestSignalScores();
   RunTestSignalMisc();
   RunTestSignalFilters();
   RunTestSignalNews();
   RunTestSignalFib();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTSIGNALRULES_MQH
