//+------------------------------------------------------------------+
//| TestPatterns.mqh — pola candle terarah dan urutannya, fungsi murni
//| (spec 12 design §3.1, §6.1; TC-PA-01..22). Bar dibangun tangan,
//| ATR 0.0010 kecuali disebut; nilai dihitung manual.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTPATTERNS_MQH
#define SDB_SUITES_TESTPATTERNS_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Strategies/PatternRules.mqh>

#define TPA_ATR 0.0010

void PaR(MqlRates &r[], const double o, const double h, const double l, const double c)
  {
   int n = ArraySize(r);
   ArrayResize(r, n + 1);
   r[n].time = D'2026.06.01 00:00' + n * 900;
   r[n].open = o;
   r[n].high = h;
   r[n].low = l;
   r[n].close = c;
   r[n].tick_volume = 1;
   r[n].real_volume = 0;
   r[n].spread = 0;
  }

string PaCode(const MqlRates &r[], const ENUM_SDB_DIR dir, const double atr = TPA_ATR)
  {
   SdbPattern p;
   DetectPattern(r, atr, dir, p);
   return p.code;
  }

// Bar netral kecil sebagai pengisi i-2 / i-1 agar pola sebelumnya tidak ikut.
void PaFiller(MqlRates &r[])
  {
   PaR(r, 1.1005, 1.1008, 1.1004, 1.1006);
  }

void RunTestPatternsStarEngulf()
  {
   MqlRates r[];
   SdbPattern p;
   PaR(r, 1.1020, 1.1022, 1.1006, 1.1008);
   PaR(r, 1.1007, 1.1010, 1.1004, 1.1008);
   PaR(r, 1.1009, 1.1019, 1.1008, 1.1018);
   DetectPattern(r, TPA_ATR, SDB_DIR_BULL, p);
   AssertTrue("TC-PA-01", "bintang pagi: STAR BULL skor 3", p.code == SDB_PA_PATTERN_STAR && p.dir == SDB_DIR_BULL && p.score == 3 &&
              p.barTime == r[2].time);

   ArrayFree(r);
   PaR(r, 1.1013, 1.1015, 1.1006, 1.1008);
   PaR(r, 1.1007, 1.1010, 1.1004, 1.1008);
   PaR(r, 1.1009, 1.1019, 1.1008, 1.1018);
   AssertTrue("TC-PA-02", "badan pertama tepat 0,5 ATR (harus >): bukan STAR", PaCode(r, SDB_DIR_BULL) != SDB_PA_PATTERN_STAR);

   ArrayFree(r);
   PaR(r, 1.1008, 1.1022, 1.1006, 1.1020);
   PaR(r, 1.1021, 1.1024, 1.1018, 1.1020);
   PaR(r, 1.1019, 1.1020, 1.1009, 1.1010);
   AssertTrue("TC-PA-03", "bintang sore untuk SELL: STAR; diminta BUY: bukan STAR",
              PaCode(r, SDB_DIR_BEAR) == SDB_PA_PATTERN_STAR && PaCode(r, SDB_DIR_BULL) != SDB_PA_PATTERN_STAR);

   ArrayFree(r);
   PaFiller(r);
   PaR(r, 1.1010, 1.1012, 1.1002, 1.1004);
   PaR(r, 1.1003, 1.1014, 1.1003, 1.1013);
   DetectPattern(r, TPA_ATR, SDB_DIR_BULL, p);
   AssertTrue("TC-PA-04", "engulfing kuat: badan 0,0010 = 91% rentang, close > high sebelumnya: skor 10",
              p.code == SDB_PA_PATTERN_ENGULF_STRONG && p.score == 10);

   ArrayFree(r);
   PaFiller(r);
   PaR(r, 1.1010, 1.1011, 1.1003, 1.1004);
   PaR(r, 1.1003, 1.1017, 1.0997, 1.1015);
   AssertTrue("TC-PA-05", "badan tepat 60% rentang dan tepat 0,8 ATR (ATR 0.0015): ENGULF_STRONG",
              PaCode(r, SDB_DIR_BULL, 0.0015) == SDB_PA_PATTERN_ENGULF_STRONG);

   ArrayFree(r);
   PaFiller(r);
   PaR(r, 1.1008, 1.1009, 1.1003, 1.1004);
   PaR(r, 1.1004, 1.1012, 1.1003, 1.1011);
   DetectPattern(r, TPA_ATR, SDB_DIR_BULL, p);
   AssertTrue("TC-PA-06", "engulfing badan 0,7 ATR: ENGULF skor 3 (didahulukan atas tweezer)", p.code == SDB_PA_PATTERN_ENGULF && p.score == 3);

   ArrayFree(r);
   PaFiller(r);
   PaR(r, 1.1010, 1.1016, 1.1003, 1.1004);
   PaR(r, 1.1003, 1.1014, 1.1003, 1.1013);
   AssertTrue("TC-PA-07", "close tidak melewati high sebelumnya: ENGULF", PaCode(r, SDB_DIR_BULL) == SDB_PA_PATTERN_ENGULF);

   ArrayFree(r);
   PaFiller(r);
   PaR(r, 1.1010, 1.1012, 1.1002, 1.1004);
   PaR(r, 1.1003, 1.1014, 1.1001, 1.1013);
   AssertTrue("TC-PA-08", "engulfing kuat yang juga outside bar: ENGULF_STRONG", PaCode(r, SDB_DIR_BULL) == SDB_PA_PATTERN_ENGULF_STRONG);
  }

void RunTestPatternsPinOthers()
  {
   MqlRates r[];
   SdbPattern p;
   PaFiller(r);
   PaFiller(r);
   PaR(r, 1.1006, 1.1009, 1.0998, 1.1008);
   DetectPattern(r, TPA_ATR, SDB_DIR_BULL, p);
   AssertTrue("TC-PA-09", "hammer: badan 0,0002, sumbu bawah 0,0008, atas 0,0001: PIN skor 7", p.code == SDB_PA_PATTERN_PIN && p.score == 7);
   string bearOnHammer = PaCode(r, SDB_DIR_BEAR);

   ArrayFree(r);
   PaFiller(r);
   PaFiller(r);
   PaR(r, 1.1006, 1.1013, 1.0998, 1.1008);
   AssertTrue("TC-PA-10", "sumbu atas 0,0005 (sumbu bawah tidak > 2 x atas): bukan PIN", PaCode(r, SDB_DIR_BULL) != SDB_PA_PATTERN_PIN);

   ArrayFree(r);
   PaFiller(r);
   PaFiller(r);
   PaR(r, 1.1004, 1.1006, 1.0999, 1.1005);
   AssertTrue("TC-PA-11", "rentang 0,7 ATR: bukan PIN", PaCode(r, SDB_DIR_BULL) != SDB_PA_PATTERN_PIN);

   ArrayFree(r);
   PaFiller(r);
   PaFiller(r);
   PaR(r, 1.1002, 1.1010, 1.0999, 1.1000);
   AssertTrue("TC-PA-12", "shooting star untuk SELL: PIN; hammer diminta SELL: NONE",
              PaCode(r, SDB_DIR_BEAR) == SDB_PA_PATTERN_PIN && bearOnHammer == SDB_PA_PATTERN_NONE);

   ArrayFree(r);
   PaFiller(r);
   PaR(r, 1.1008, 1.1009, 1.0998, 1.1003);
   PaR(r, 1.1006, 1.1009, 1.0998, 1.1008);
   AssertTrue("TC-PA-13", "pin bar yang juga tweezer: PIN", PaCode(r, SDB_DIR_BULL) == SDB_PA_PATTERN_PIN);

   ArrayFree(r);
   PaFiller(r);
   PaR(r, 1.1008, 1.1009, 1.1003, 1.1004);
   PaR(r, 1.1004, 1.1010, 1.1003, 1.1009);
   AssertTrue("TC-PA-14", "open = close sebelumnya: ENGULF", PaCode(r, SDB_DIR_BULL) == SDB_PA_PATTERN_ENGULF);

   ArrayFree(r);
   PaFiller(r);
   PaR(r, 1.1008, 1.1009, 1.1002, 1.1004);
   PaR(r, 1.1005, 1.1008, 1.1003, 1.1007);
   string tw = PaCode(r, SDB_DIR_BULL);
   r[2].low = 1.10031;
   AssertTrue("TC-PA-15", "tweezer selisih low 0,1 ATR: TWEEZER; 0,11 ATR: NONE",
              tw == SDB_PA_PATTERN_TWEEZER && PaCode(r, SDB_DIR_BULL) == SDB_PA_PATTERN_NONE);

   ArrayFree(r);
   PaFiller(r);
   PaR(r, 1.1003, 1.1007, 1.1002, 1.1006);
   PaR(r, 1.1005, 1.1009, 1.1001, 1.1008);
   DetectPattern(r, TPA_ATR, SDB_DIR_BULL, p);
   AssertTrue("TC-PA-16", "outside bar bullish: OUTSIDE skor 3", p.code == SDB_PA_PATTERN_OUTSIDE && p.score == 3);

   ArrayFree(r);
   PaR(r, 1.1020, 1.1022, 1.1006, 1.1008);
   PaR(r, 1.1008, 1.1010, 1.1004, 1.1007);
   PaR(r, 1.1006, 1.1019, 1.1006, 1.1018);
   AssertTrue("TC-PA-17", "bar ketiga bintang yang juga engulfing: STAR", PaCode(r, SDB_DIR_BULL) == SDB_PA_PATTERN_STAR);

   ArrayFree(r);
   PaFiller(r);
   PaR(r, 1.1015, 1.1016, 1.1000, 1.1002);
   PaR(r, 1.1005, 1.1010, 1.1004, 1.1008);
   AssertTrue("TC-PA-18", "inside bar bullish kecil (kasus bot Python): NONE", PaCode(r, SDB_DIR_BULL) == SDB_PA_PATTERN_NONE);

   ArrayFree(r);
   PaFiller(r);
   PaR(r, 1.1000, 1.1016, 1.0999, 1.1015);
   PaR(r, 1.1008, 1.1010, 1.1006, 1.1008);
   bool harami = PaCode(r, SDB_DIR_BULL) == SDB_PA_PATTERN_NONE && PaCode(r, SDB_DIR_BEAR) == SDB_PA_PATTERN_NONE;
   ArrayFree(r);
   PaFiller(r);
   PaFiller(r);
   PaR(r, 1.1009, 1.1010, 1.1000, 1.1010);
   AssertTrue("TC-PA-19", "doji harami: NONE kedua arah; dragonfly badan 10% sumbu bawah 90%: PIN",
              harami && PaCode(r, SDB_DIR_BULL) == SDB_PA_PATTERN_PIN);
  }

void RunTestPatternsEdges()
  {
   MqlRates r[];
   PaFiller(r);
   PaFiller(r);
   PaR(r, 1.1000, 1.1000, 1.1000, 1.1000);
   bool flat = PaCode(r, SDB_DIR_BULL) == SDB_PA_PATTERN_NONE;
   ArrayFree(r);
   PaFiller(r);
   PaR(r, 1.1010, 1.1012, 1.1002, 1.1004);
   PaR(r, 1.1003, 1.1014, 1.1003, 1.1013);
   bool noAtr = PaCode(r, SDB_DIR_BULL, 0.0) == SDB_PA_PATTERN_NONE;
   bool noDir = PaCode(r, SDB_DIR_NONE) == SDB_PA_PATTERN_NONE;
   MqlRates two[];
   PaR(two, 1.1010, 1.1012, 1.1002, 1.1004);
   PaR(two, 1.1003, 1.1014, 1.1003, 1.1013);
   AssertTrue("TC-PA-20", "rentang 0, ATR 0, arah NONE, 2 bar: NONE tanpa error",
              flat && noAtr && noDir && PaCode(two, SDB_DIR_BULL) == SDB_PA_PATTERN_NONE);

   AssertTrue("TC-PA-21", "skor: STAR 3, ENGULF_STRONG 10, PIN 7, ENGULF 3, TWEEZER 3, OUTSIDE 3, NONE 0",
              PaScore(SDB_PA_PATTERN_STAR) == 3 && PaScore(SDB_PA_PATTERN_ENGULF_STRONG) == 10 && PaScore(SDB_PA_PATTERN_PIN) == 7 &&
              PaScore(SDB_PA_PATTERN_ENGULF) == 3 && PaScore(SDB_PA_PATTERN_TWEEZER) == 3 && PaScore(SDB_PA_PATTERN_OUTSIDE) == 3 &&
              PaScore(SDB_PA_PATTERN_NONE) == 0);

   // TC-PA-22: data TC-PA-04 dan TC-PA-09 diskalakan x1e6 (harga ~1.100.000, ATR 1000): hasil sama.
   MqlRates big[];
   for(int i = 0; i < ArraySize(r); i++)
     {
      PaR(big, r[i].open * 1e6, r[i].high * 1e6, r[i].low * 1e6, r[i].close * 1e6);
     }
   MqlRates pin[];
   PaFiller(pin);
   PaFiller(pin);
   PaR(pin, 1.1006, 1.1009, 1.0998, 1.1008);
   MqlRates bigPin[];
   for(int i = 0; i < ArraySize(pin); i++)
      PaR(bigPin, pin[i].open * 1e6, pin[i].high * 1e6, pin[i].low * 1e6, pin[i].close * 1e6);
   AssertTrue("TC-PA-22", "skala harga x1e6 dengan ATR 1000: ENGULF_STRONG dan PIN tetap",
              PaCode(big, SDB_DIR_BULL, 1000.0) == SDB_PA_PATTERN_ENGULF_STRONG && PaCode(bigPin, SDB_DIR_BULL, 1000.0) == SDB_PA_PATTERN_PIN);
  }

void RunTestPatterns()
  {
   TfBeginSuite("Patterns");
   RunTestPatternsStarEngulf();
   RunTestPatternsPinOthers();
   RunTestPatternsEdges();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTPATTERNS_MQH
