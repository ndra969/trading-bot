//+------------------------------------------------------------------+
//| TestStructure.mqh — swing, BOS, EMA, bias, skor tren; fungsi murni
//| di atas array bar urut waktu naik (spec 10 design §3.1, §6.1;
//| TC-MS-01..21). Bar dibangun tangan agar hasil bisa dihitung manual.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTSTRUCTURE_MQH
#define SDB_SUITES_TESTSTRUCTURE_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Analysis/StructureRules.mqh>

#define TMS_T0 D'2026.06.01 00:00'

void MsAdd(MqlRates &r[], const double high, const double low, const double close)
  {
   int n = ArraySize(r);
   ArrayResize(r, n + 1);
   r[n].time = TMS_T0 + n * 3600;
   r[n].open = (n > 0) ? r[n - 1].close : close;
   r[n].high = high;
   r[n].low = low;
   r[n].close = close;
   r[n].tick_volume = 1;
   r[n].real_volume = 0;
   r[n].spread = 0;
  }

void MsHighs(MqlRates &r[], const double &highs[])
  {
   ArrayFree(r);
   for(int i = 0; i < ArraySize(highs); i++)
      MsAdd(r, highs[i], highs[i] - 1.0, highs[i] - 0.5);
  }

// Data dasar TC-MS-06..11 (n = 2): swing high 1.1050 di bar 2, swing low 1.0960 di bar 4, BOS bullish di bar 6.
void MsBase(MqlRates &r[], const double close6)
  {
   ArrayFree(r);
   MsAdd(r, 1.1000, 1.0990, 1.0995);
   MsAdd(r, 1.1020, 1.0995, 1.1015);
   MsAdd(r, 1.1050, 1.1010, 1.1030);
   MsAdd(r, 1.1030, 1.0980, 1.0990);
   MsAdd(r, 1.1010, 1.0960, 1.0970);
   MsAdd(r, 1.1040, 1.0970, 1.1035);
   MsAdd(r, 1.1060, 1.1030, close6);
  }

SdbStructure MsStructure(const MqlRates &r[], const int lookback)
  {
   SdbSwing sw[];
   FindSwings(r, 2, sw);
   SdbStructure st;
   StructureOf(r, sw, 2, lookback, st);
   return st;
  }

void RunTestStructureSwings()
  {
   MqlRates r[];
   double h1[] = {1, 2, 5, 2, 1};
   MsHighs(r, h1);
   AssertTrue("TC-MS-01", "high 1,2,5,2,1: swing high di indeks 2", IsSwingHigh(r, 2, 2) && !IsSwingHigh(r, 1, 2));
   double h2[] = {1, 2, 5, 5, 1, 0.5};
   MsHighs(r, h2);
   AssertTrue("TC-MS-02", "high sama persis: hanya bar lebih awal", IsSwingHigh(r, 2, 2) && !IsSwingHigh(r, 3, 2));
   double h3[] = {1, 2, 3, 4, 9, 5};
   MsHighs(r, h3);
   SdbSwing sw[];
   FindSwings(r, 2, sw);
   bool peak = false;
   for(int i = 0; i < ArraySize(sw); i++)
      if(sw[i].index == 4)
         peak = true;
   AssertTrue("TC-MS-03", "puncak dengan kanan belum lengkap belum diakui", !peak);

   SdbSwing before[], after[];
   MsBase(r, 1.1051);
   FindSwings(r, 2, before);
   MsAdd(r, 1.1045, 1.1035, 1.1040);
   MsAdd(r, 1.1045, 1.1035, 1.1040);
   MsAdd(r, 1.1045, 1.1035, 1.1040);
   FindSwings(r, 2, after);
   bool same = ArraySize(after) >= ArraySize(before);
   for(int i = 0; i < ArraySize(before) && same; i++)
      same = before[i].index == after[i].index && before[i].price == after[i].price && before[i].isHigh == after[i].isHigh;
   AssertTrue("TC-MS-04", StringFormat("swing lama tidak berubah setelah bar baru (%d -> %d swing)", ArraySize(before), ArraySize(after)),
              same && ArraySize(before) == 2);

   ArrayFree(r);
   double lows[] = {5, 4, 1, 4, 5};
   for(int i = 0; i < 5; i++)
      MsAdd(r, lows[i] + 1.0, lows[i], lows[i] + 0.5);
   AssertTrue("TC-MS-05", "low 5,4,1,4,5: swing low di indeks 2", IsSwingLow(r, 2, 2) && !IsSwingHigh(r, 2, 2));
  }

void RunTestStructureBos()
  {
   MqlRates r[];
   MsBase(r, 1.1051);
   SdbStructure st = MsStructure(r, 100);
   AssertTrue("TC-MS-06", StringFormat("close 1.1051 > swing 1.1050: BOS bullish (dir=%d level=%.5f)", st.dir, st.bosLevel),
              st.dir == SDB_DIR_BULL && MathAbs(st.bosLevel - 1.1050) < 1e-9 && st.bosTime == r[6].time);
   MsBase(r, 1.1050);
   st = MsStructure(r, 100);
   AssertTrue("TC-MS-07", "close tepat di level: bukan BOS", st.dir == SDB_DIR_NONE && st.bosTime == 0);

   MsBase(r, 1.1051);
   MsAdd(r, 1.1040, 1.0950, 1.0955);
   st = MsStructure(r, 100);
   AssertTrue("TC-MS-08", "BOS bullish lalu close di bawah swing low 1.0960: BEAR",
              st.dir == SDB_DIR_BEAR && MathAbs(st.bosLevel - 1.0960) < 1e-9 && st.bosTime == r[7].time);

   MsBase(r, 1.1051);
   MsAdd(r, 1.1045, 1.1035, 1.1040);
   MsAdd(r, 1.1045, 1.1035, 1.1040);
   MsAdd(r, 1.1045, 1.1035, 1.1040);
   st = MsStructure(r, 2);
   AssertTrue("TC-MS-09", "BOS di luar jendela lookback: NONE", st.dir == SDB_DIR_NONE);

   MsBase(r, 1.1051);
   st = MsStructure(r, 100);
   AssertTrue("TC-MS-10", "swing terakhir: high 1.1050 di bar 2, low 1.0960 di bar 4, 2 swing",
              MathAbs(st.lastHigh - 1.1050) < 1e-9 && st.lastHighTime == r[2].time && MathAbs(st.lastLow - 1.0960) < 1e-9 &&
              st.lastLowTime == r[4].time && st.swings == 2);

   MsAdd(r, 1.1058, 1.1045, 1.1055);
   st = MsStructure(r, 100);
   AssertTrue("TC-MS-11", "close kedua di atas swing yang sama tidak membuat BOS baru", st.dir == SDB_DIR_BULL && st.bosTime == r[6].time);
  }

SdbStructureParams MsParams()
  {
   SdbStructureParams p;
   p.strength = 2;
   p.lookback = 100;
   p.emaPeriod = 50;
   p.slopeBars = 3;
   return p;
  }

SdbTfAnalysis MsTf(const ENUM_SDB_DIR st, const ENUM_SDB_DIR ema)
  {
   SdbTfAnalysis a;
   ZeroMemory(a);
   a.ready = true;
   a.st.dir = st;
   a.emaDir = ema;
   return a;
  }

void RunTestStructureEma()
  {
   MqlRates r[];
   for(int i = 0; i < 10; i++)
      MsAdd(r, 1.5, 0.5, 1.0);
   double ema[];
   bool ok = EmaSeries(r, 3, ema);
   bool flat = ok && ArraySize(ema) == 10;
   for(int i = 2; i < 10 && flat; i++)
      flat = MathAbs(ema[i] - 1.0) < 1e-12;
   AssertTrue("TC-MS-12", "close konstan 1.0: EMA 1.0", flat);

   ArrayFree(r);
   for(int i = 1; i <= 20; i++)
      MsAdd(r, i + 0.5, i - 0.5, (double)i);
   ok = EmaSeries(r, 5, ema);
   // Benih SMA(1..5) = 3 di indeks 4, alpha 1/3: deret naik 1 per bar tertinggal tepat 2 -> EMA terakhir 18.
   AssertTrue("TC-MS-13", StringFormat("deret 1..20 periode 5: EMA terakhir 18 (%.10f)", ok ? ema[19] : -1),
              ok && MathAbs(ema[19] - 18.0) < 1e-9 && MathAbs(ema[4] - 3.0) < 1e-12);

   ArrayResize(r, 14);
   AssertTrue("TC-MS-14", "bar < 3 x periode: gagal", !EmaSeries(r, 5, ema));

   double e[] = {1.0, 1.1, 1.2, 1.3};
   double d[] = {1.3, 1.2, 1.1, 1.0};
   AssertTrue("TC-MS-15", "arah EMA: close > EMA naik = BULL; close > EMA turun = NONE; close < EMA turun = BEAR",
              EmaDirectionOf(1.4, e, 3) == SDB_DIR_BULL && EmaDirectionOf(1.4, d, 3) == SDB_DIR_NONE &&
              EmaDirectionOf(0.9, d, 3) == SDB_DIR_BEAR && EmaDirectionOf(0.9, e, 3) == SDB_DIR_NONE);

   AssertTrue("TC-MS-16", "bias: sama = arah itu, beda / NONE = NONE",
              BiasOf(SDB_DIR_BULL, SDB_DIR_BULL) == SDB_DIR_BULL && BiasOf(SDB_DIR_BEAR, SDB_DIR_BEAR) == SDB_DIR_BEAR &&
              BiasOf(SDB_DIR_BULL, SDB_DIR_BEAR) == SDB_DIR_NONE && BiasOf(SDB_DIR_NONE, SDB_DIR_BULL) == SDB_DIR_NONE);

   AssertTrue("TC-MS-17", "skor tren MTF: 15 / 7 / 0, sinyal SELL dengan MTF BEAR = 15",
              TrendScore(SDB_DIR_BULL, MsTf(SDB_DIR_BULL, SDB_DIR_BULL)) == 15 && TrendScore(SDB_DIR_BULL, MsTf(SDB_DIR_BULL, SDB_DIR_NONE)) == 7 &&
              TrendScore(SDB_DIR_BULL, MsTf(SDB_DIR_BEAR, SDB_DIR_BEAR)) == 0 && TrendScore(SDB_DIR_BEAR, MsTf(SDB_DIR_BEAR, SDB_DIR_BEAR)) == 15 &&
              TrendScore(SDB_DIR_BEAR, MsTf(SDB_DIR_NONE, SDB_DIR_BEAR)) == 7);

   SdbTfAnalysis a;
   MsBase(r, 1.1051);
   AnalyzeTf(r, MsParams(), a);
   AssertTrue("TC-MS-18", "bar kurang dari BarsNeeded: tidak siap, alasan data kurang", !a.ready && a.reason == "data kurang");

   // TC-MS-19: data dasar dikali 100 (harga JPY) dan 2000 (XAU): BOS dari nilai mentah.
   MqlRates jpy[];
   MsBase(r, 1.1051);
   ArrayResize(jpy, ArraySize(r));
   for(int i = 0; i < ArraySize(r); i++)
     {
      jpy[i] = r[i];
      jpy[i].high = r[i].high * 100.0;
      jpy[i].low = r[i].low * 100.0;
      jpy[i].close = r[i].close * 100.0;
     }
   SdbSwing sw[];
   FindSwings(jpy, 2, sw);
   SdbStructure st;
   StructureOf(jpy, sw, 2, 100, st);
   AssertTrue("TC-MS-19", StringFormat("harga JPY: BOS di 110.50 (%.3f)", st.bosLevel), st.dir == SDB_DIR_BULL && MathAbs(st.bosLevel - 110.50) < 1e-9);

   AssertIntEq("TC-MS-20", "BarsNeeded default = 154", BarsNeeded(2, 100, 50, 3), 154);

   ArrayFree(r);
   for(int i = 0; i < 200; i++)
     {
      double base = 1.10 + 0.002 * MathSin(i / 7.0) + 0.0001 * i;
      MsAdd(r, base + 0.0008, base - 0.0008, base + 0.0002 * MathCos(i));
     }
   SdbTfAnalysis a1, a2;
   AnalyzeTf(r, MsParams(), a1);
   AnalyzeTf(r, MsParams(), a2);
   AssertTrue("TC-MS-21", StringFormat("data sama dua kali: hasil identik, siap (dir=%d ema=%d swings=%d)", a1.st.dir, a1.emaDir, a1.st.swings),
              a1.ready && a1.reason == "" && a1.barTime == r[199].time && a1.st.dir == a2.st.dir && a1.st.bosTime == a2.st.bosTime &&
              a1.ema == a2.ema && a1.emaDir == a2.emaDir && a1.st.swings > 0);
  }

void RunTestStructure()
  {
   TfBeginSuite("Structure");
   RunTestStructureSwings();
   RunTestStructureBos();
   RunTestStructureEma();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTSTRUCTURE_MQH
