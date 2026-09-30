//+------------------------------------------------------------------+
//| TestPositionMath.mqh — keputusan posisi murni (spec 06, TC-PM-xx):
//| profit dalam R, BE, komisi, partial, trailing, pilihan SL terbaik,
//| pemasangan ulang SL, jadwal retry.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTPOSITIONMATH_MQH
#define SDB_SUITES_TESTPOSITIONMATH_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Position/PositionMath.mqh>

#define TPM_PT5 0.00001
#define TPM_PT3 0.001

bool TpmNear(const double a, const double b) { return MathAbs(a - b) < 1e-9; }

void RunTestPositionMathBe()
  {
   AssertEq("TC-PM-01", "buy 1.10000 SL 1.09800 harga 1.10200 = 1R", ProfitInR(true, 1.10000, 1.09800, 1.10200), 1.0, 1e-9);
   AssertEq("TC-PM-02", "sell 1.10000 SL 1.10200 harga 1.09700 = 1.5R", ProfitInR(false, 1.10000, 1.10200, 1.09700), 1.5, 1e-9);
   AssertTrue("TC-PM-03", "buy harga 1.09900 = -0.5R; R 0 = 0",
              TpmNear(ProfitInR(true, 1.10000, 1.09800, 1.09900), -0.5) && ProfitInR(true, 1.10000, 1.10000, 1.10500) == 0.0);
   AssertTrue("TC-PM-04", "buy: SL 1.10010 aktif, 1.09800 tidak, tepat 1.10000 aktif, SL 0 tidak",
              IsBreakevenActive(true, 1.10000, 1.10010) && !IsBreakevenActive(true, 1.10000, 1.09800) &&
              IsBreakevenActive(true, 1.10000, 1.10000) && !IsBreakevenActive(true, 1.10000, 0.0));
   AssertTrue("TC-PM-05", "sell SL 1.09990 aktif", IsBreakevenActive(false, 1.10000, 1.09990));
   AssertEq("TC-PM-06", "BE buy 1.10000 spread 8 buffer 2 = 1.10010", BreakevenSl(true, 1.10000, 8, 0, 2, TPM_PT5, 5), 1.10010, 1e-9);
   AssertEq("TC-PM-07", "BE sell = 1.09990", BreakevenSl(false, 1.10000, 8, 0, 2, TPM_PT5, 5), 1.09990, 1e-9);
   AssertEq("TC-PM-08", "BE JPY 161.500 spread 35 buffer 2 = 161.537", BreakevenSl(true, 161.500, 35, 0, 2, TPM_PT3, 3), 161.537, 1e-9);
   AssertEq("TC-PM-08b", "BE XAU 2000.00 spread 20 buffer 2 point 0.01 = 2000.22", BreakevenSl(true, 2000.00, 20, 0, 2, 0.01, 2), 2000.22, 1e-9);
   AssertTrue("TC-PM-08c", "komisi 0.14 / 0.1 per point = 2 point (ke atas); 0 = 0; negatif dihitung absolut",
              CommissionPoints(0.14, 0.1) == 2 && CommissionPoints(0.0, 0.1) == 0 && CommissionPoints(-0.14, 0.1) == 2 &&
              CommissionPoints(0.14, 0.0) == 0);
   AssertTrue("TC-PM-09", "BE: 1.0R dengan ambang 1.0 ya; 0.99R tidak",
              ShouldBreakeven(1.0, 1.0, false, true) && !ShouldBreakeven(0.99, 1.0, false, true));
   AssertTrue("TC-PM-10", "BE tidak jalan tanpa SL awal atau bila sudah aktif",
              !ShouldBreakeven(1.0, 1.0, false, false) && !ShouldBreakeven(2.0, 1.0, true, true));
  }

void RunTestPositionMathPartial()
  {
   AssertTrue("TC-PM-11", "partial: 1.6R >= 1.5, volume = awal", ShouldPartial(1.6, 1.5, 0.10, 0.10, true));
   AssertTrue("TC-PM-12", "partial tidak diulang: volume 0.05 < awal 0.10; tanpa SL awal tidak jalan",
              !ShouldPartial(2.0, 1.5, 0.05, 0.10, true) && !ShouldPartial(2.0, 1.5, 0.10, 0.10, false));
   bool skip;
   double v = PartialVolume(0.10, 50, 0.01, 0.01, 0.10, skip);
   AssertTrue("TC-PM-13", "awal 0.10, 50% = 0.05", TpmNear(v, 0.05) && !skip);
   v = PartialVolume(0.03, 50, 0.01, 0.01, 0.03, skip);
   AssertTrue("TC-PM-14", "awal 0.03, 50% = 0.015 -> 0.01", TpmNear(v, 0.01) && !skip);
   v = PartialVolume(0.02, 50, 0.01, 0.01, 0.02, skip);
   AssertTrue("TC-PM-15", "awal 0.02 = 0.01, sisa 0.01 = minimum, boleh", TpmNear(v, 0.01) && !skip);
   v = PartialVolume(0.01, 50, 0.01, 0.01, 0.01, skip);
   AssertTrue("TC-PM-16", "awal 0.01: dilewati", skip && v == 0.0);
  }

void RunTestPositionMathTrail()
  {
   AssertEq("TC-PM-17", "trail buy bid 1.10500 ATR 0.00100 x2 = 1.10300", TrailingSl(true, 1.10500, 0.00100, 2.0, 5), 1.10300, 1e-9);
   AssertEq("TC-PM-18", "trail sell ask 1.10500 = 1.10700", TrailingSl(false, 1.10500, 0.00100, 2.0, 5), 1.10700, 1e-9);
   AssertTrue("TC-PM-19", "buy 1.10280 -> 1.10300 (20 point >= 5): lebih baik", IsSlImprovement(true, 1.10280, 1.10300, 5, TPM_PT5));
   AssertTrue("TC-PM-20", "buy 1.10298 -> 1.10300 (2 point): tidak; sell 1.10300 -> 1.10310 (lebih buruk): tidak",
              !IsSlImprovement(true, 1.10298, 1.10300, 5, TPM_PT5) && !IsSlImprovement(false, 1.10300, 1.10310, 5, TPM_PT5));
   AssertEq("TC-PM-21", "pilih terbaik: sekarang 1.10000, BE 1.10010, trail 1.10300 -> 1.10300",
            PickBestSl(true, 1.10000, 1.10010, 1.10300, 5, TPM_PT5), 1.10300, 1e-9);
   AssertEq("TC-PM-22", "sekarang 1.10300, BE 1.10010, trail 1.10200 -> 0 (tidak ada perbaikan)",
            PickBestSl(true, 1.10300, 1.10010, 1.10200, 5, TPM_PT5), 0.0, 1e-12);
   AssertEq("TC-PM-23", "restore: SL awal 1.09800 masih valid di harga 1.09900", RestoreSl(true, 1.09800, 1.09900, 0, 8, TPM_PT5, 5), 1.09800, 1e-9);
   AssertEq("TC-PM-24", "restore: harga 1.09790 sudah lewat SL awal -> harga - 9 point = 1.09781",
            RestoreSl(true, 1.09800, 1.09790, 0, 8, TPM_PT5, 5), 1.09781, 1e-9);
   AssertTrue("TC-PM-25", "trailing aktif: SL 1.10300 > titik BE 1.10010; SL = titik BE tidak",
              IsTrailingActive(true, 1.10010, 1.10300) && !IsTrailingActive(true, 1.10010, 1.10010));
   datetime t0 = D'2026.10.01 10:00:00';
   AssertTrue("TC-PM-26", "retry: gagal 0 ya; gagal 1 setelah 29 detik tidak, 30 detik ya; gagal 3 tidak",
              RetryDue(0, 0, t0) && !RetryDue(1, t0, t0 + 29) && RetryDue(1, t0, t0 + 30) && !RetryDue(3, t0, t0 + 999));
  }

void RunTestPositionMath()
  {
   TfBeginSuite("PositionMath");
   RunTestPositionMathBe();
   RunTestPositionMathPartial();
   RunTestPositionMathTrail();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTPOSITIONMATH_MQH
