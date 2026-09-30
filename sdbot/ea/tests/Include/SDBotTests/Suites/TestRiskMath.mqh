//+------------------------------------------------------------------+
//| TestRiskMath.mqh — fungsi risiko murni (spec 05, TC-RM-xx): lot,
//| risiko order dan posisi, drawdown, rugi harian, pergantian hari,
//| reset emergency, operasi saldo, magic SDBot, sesi, jadwal close all.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTRISKMATH_MQH
#define SDB_SUITES_TESTRISKMATH_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Risk/RiskMath.mqh>

bool TrmNear(const double a, const double b)
  {
   return MathAbs(a - b) < 1e-9;
  }

void RunTestRiskMathLot()
  {
   AssertEq("TC-RM-01", "0.0379 dibulatkan ke bawah step 0.01 = 0.03", RoundLotDown(0.0379, 0.01), 0.03, 1e-12);
   AssertEq("TC-RM-02", "0.1 x 2.9 (0.28999...) tetap 0.29", RoundLotDown(0.1 * 2.9, 0.01), 0.29, 1e-12);
   AssertTrue("TC-RM-03", "1.0 step 0.1 = 1.0; 0.15 step 0.1 = 0.1",
              TrmNear(RoundLotDown(1.0, 0.1), 1.0) && TrmNear(RoundLotDown(0.15, 0.1), 0.1));

   ENUM_SDB_LOT_FLAG f;
   double lot = CalcLotSize(1000, 0.5, 20, 0.01, 0.01, 100, f);
   AssertTrue("TC-RM-04", "balance 1000, 0.5%, money/lot 20: 0.25 OK", TrmNear(lot, 0.25) && f == SDB_LOT_OK);
   lot = CalcLotSize(1000, 0.5, 30, 0.01, 0.01, 100, f);
   AssertTrue("TC-RM-05", "money/lot 30: 0.1666 -> 0.16 OK", TrmNear(lot, 0.16) && f == SDB_LOT_OK);
   lot = CalcLotSize(100, 0.5, 100, 0.01, 0.01, 100, f);
   AssertTrue("TC-RM-06", "balance 100, money/lot 100: 0 BELOW_MIN", lot == 0.0 && f == SDB_LOT_BELOW_MIN);
   lot = CalcLotSize(100000, 1.0, 10, 0.01, 0.01, 50, f);
   AssertTrue("TC-RM-07", "hasil 100 lot > max 50: 50 CAPPED_MAX", TrmNear(lot, 50) && f == SDB_LOT_CAPPED_MAX);
   ENUM_SDB_LOT_FLAG f2;
   double lot0 = CalcLotSize(1000, 0.5, 0, 0.01, 0.01, 100, f);
   double lotNeg = CalcLotSize(1000, 0.5, -5, 0.01, 0.01, 100, f2);
   AssertTrue("TC-RM-08", "money/lot 0 dan -5: 0 INVALID",
              lot0 == 0.0 && f == SDB_LOT_INVALID && lotNeg == 0.0 && f2 == SDB_LOT_INVALID);
   AssertTrue("TC-RM-09", "risiko efektif 0.5: flag aktif 0.25, tidak aktif 0.5",
              TrmNear(EffectiveRiskPct(0.5, true), 0.25) && TrmNear(EffectiveRiskPct(0.5, false), 0.5));
  }

void RunTestRiskMathRisk()
  {
   AssertTrue("TC-RM-10", "RiskPctOf 5 dari 1000 = 0.5; balance 0 = DBL_MAX",
              TrmNear(RiskPctOf(5, 1000), 0.5) && RiskPctOf(5, 0) == DBL_MAX);
   AssertEq("TC-RM-11", "buy open 1.10000 SL 1.09800, rugi di SL -2.0: risiko 2.0",
            PositionRiskMoney(true, 1.10000, 1.09800, -2.0, 1000, 1.0), 2.0, 1e-12);
   AssertTrue("TC-RM-12", "SL di harga buka (buy) dan SL lebih baik (sell): risiko 0",
              PositionRiskMoney(true, 1.10000, 1.10000, 0.0, 1000, 1.0) == 0.0 &&
              PositionRiskMoney(false, 1.10000, 1.09990, 0.1, 1000, 1.0) == 0.0);
   AssertEq("TC-RM-13", "tanpa SL, balance 1000, 1%: risiko 10",
            PositionRiskMoney(true, 1.10000, 0.0, 0.0, 1000, 1.0), 10.0, 1e-12);
  }

void RunTestRiskMathDrawdown()
  {
   AssertTrue("TC-RM-14", "drawdown 1000->900 = 10; 1000->1100 = 0; puncak 0 = 0",
              TrmNear(DrawdownPct(1000, 900), 10) && DrawdownPct(1000, 1100) == 0.0 && DrawdownPct(0, 50) == 0.0);
   AssertTrue("TC-RM-15", "rugi harian 1000->970 = 3; 1000->1010 = -1",
              TrmNear(DailyLossPct(1000, 970), 3) && TrmNear(DailyLossPct(1000, 1010), -1));
   AssertTrue("TC-RM-16", "4.9 dari NORMAL tetap NORMAL; 5.0 dari NORMAL -> INFO",
              DrawdownLevel(4.9, SDB_DD_NORMAL, 5, 10, 8, 15) == SDB_DD_NORMAL &&
              DrawdownLevel(5.0, SDB_DD_NORMAL, 5, 10, 8, 15) == SDB_DD_INFO);
   AssertTrue("TC-RM-17", "10 dari INFO dan dari NORMAL -> REDUCE",
              DrawdownLevel(10, SDB_DD_INFO, 5, 10, 8, 15) == SDB_DD_REDUCE &&
              DrawdownLevel(10, SDB_DD_NORMAL, 5, 10, 8, 15) == SDB_DD_REDUCE);
   AssertTrue("TC-RM-18", "9 dan 8.0 dari REDUCE tetap REDUCE (tidak berkedip)",
              DrawdownLevel(9, SDB_DD_REDUCE, 5, 10, 8, 15) == SDB_DD_REDUCE &&
              DrawdownLevel(8.0, SDB_DD_REDUCE, 5, 10, 8, 15) == SDB_DD_REDUCE);
   AssertTrue("TC-RM-19", "7.9 dari REDUCE -> INFO; 4.0 dari REDUCE -> NORMAL",
              DrawdownLevel(7.9, SDB_DD_REDUCE, 5, 10, 8, 15) == SDB_DD_INFO &&
              DrawdownLevel(4.0, SDB_DD_REDUCE, 5, 10, 8, 15) == SDB_DD_NORMAL);
   AssertTrue("TC-RM-19b", "ambang pulih = min(8, reduce x 0.8): 10->8, 20->8, 1->0.8; reduce 1: 0.9 tetap REDUCE, 0.7 NORMAL (tidak berkedip)",
              TrmNear(DdRecoverPct(10), 8) && TrmNear(DdRecoverPct(20), 8) && TrmNear(DdRecoverPct(1), 0.8) &&
              DrawdownLevel(0.9, SDB_DD_REDUCE, 5, 1, DdRecoverPct(1), 2) == SDB_DD_REDUCE &&
              DrawdownLevel(0.7, SDB_DD_REDUCE, 5, 1, DdRecoverPct(1), 2) == SDB_DD_NORMAL);
   AssertTrue("TC-RM-20", "15 dari NORMAL -> STOP (loncat); 14.99 dari REDUCE tetap REDUCE",
              DrawdownLevel(15, SDB_DD_NORMAL, 5, 10, 8, 15) == SDB_DD_STOP &&
              DrawdownLevel(14.99, SDB_DD_REDUCE, 5, 10, 8, 15) == SDB_DD_REDUCE);
   AssertTrue("TC-RM-21", "0 dari STOP tetap STOP (hanya reset manual)",
              DrawdownLevel(0, SDB_DD_STOP, 5, 10, 8, 15) == SDB_DD_STOP);
   AssertTrue("TC-RM-22", "margin 0 -> tak terbatas; margin level 250 dengan margin 10 -> 250",
              EffectiveMarginLevel(0, 0) == DBL_MAX && TrmNear(EffectiveMarginLevel(250, 10), 250));
  }

void RunTestRiskMathDay()
  {
   datetime stored = D'2026.10.01 00:00:00';
   AssertTrue("TC-RM-23", "hari tersimpan 1 Okt: 23:59:59 bukan hari baru; 2 Okt 00:00:00 hari baru",
              !IsNewServerDay(stored, D'2026.10.01 23:59:59') && IsNewServerDay(stored, D'2026.10.02 00:00:00') &&
              ServerDayStart(D'2026.10.02 13:45:10') == D'2026.10.02 00:00:00');
   AssertTrue("TC-RM-24", "tersimpan Jumat, sekarang Senin 00:00:05: hari baru",
              IsNewServerDay(D'2026.10.02 00:00:00', D'2026.10.05 00:00:05'));
   AssertTrue("TC-RM-25", "reset hanya pada transisi false -> true",
              ResetRequested(true, false) && !ResetRequested(true, true) && !ResetRequested(false, true) &&
              !ResetRequested(false, false));
   AssertTrue("TC-RM-26", "jenis deal saldo: BALANCE, CREDIT; BUY dan COMMISSION diabaikan",
              BalanceOpType(DEAL_TYPE_BALANCE) == SDB_BALANCE_OP_TYPE_BALANCE &&
              BalanceOpType(DEAL_TYPE_CREDIT) == SDB_BALANCE_OP_TYPE_CREDIT &&
              BalanceOpType(DEAL_TYPE_BUY) == "" && BalanceOpType(DEAL_TYPE_COMMISSION) == "");
   AssertTrue("TC-RM-27", "blok magic SDBot 2026091900-2026091999",
              !IsSdbotMagic(2026091899) && IsSdbotMagic(2026091900) && IsSdbotMagic(2026091999) &&
              !IsSdbotMagic(2026092000) && !IsSdbotMagic(0));
  }

void RunTestRiskMathClose()
  {
   int from[] = {300};
   int to[] = {86100};
   int none[];
   AssertTrue("TC-RM-28", "08:00 di sesi 00:05-23:55 buka; 23:58 tutup; tanpa sesi tutup",
              InTradeSession(8 * 3600, from, to) && !InTradeSession(23 * 3600 + 58 * 60, from, to) &&
              !InTradeSession(8 * 3600, none, none));
   datetime t0 = D'2026.10.01 10:00:00';
   AssertTrue("TC-RM-29", "close all: pasar buka tiap 5 detik, tutup tiap 60 detik",
              !CloseAllDue(t0 + 4, t0, true) && CloseAllDue(t0 + 5, t0, true) &&
              !CloseAllDue(t0 + 59, t0, false) && CloseAllDue(t0 + 60, t0, false));
   AssertTrue("TC-RM-30", "alert close all: 2 gagal belum; 3 gagal ya; ulang tiap 900 detik",
              !CloseAllAlertDue(2, t0, 0) && CloseAllAlertDue(3, t0, 0) &&
              !CloseAllAlertDue(5, t0 + 899, t0) && CloseAllAlertDue(5, t0 + 900, t0));
  }

void RunTestRiskMathClass()
  {
   AssertTrue("TC-RM-31", "kategori: EURUSD/USDJPY major, EURJPY/GBPJPY cross, XAU/XAG komoditas, BTC crypto, lainnya OTHER",
              AssetClassOf("EUR", "USD") == SDB_CLASS_FOREX_MAJOR && AssetClassOf("USD", "JPY") == SDB_CLASS_FOREX_MAJOR &&
              AssetClassOf("EUR", "JPY") == SDB_CLASS_FOREX_CROSS && AssetClassOf("GBP", "JPY") == SDB_CLASS_FOREX_CROSS &&
              AssetClassOf("XAU", "USD") == SDB_CLASS_COMMODITY && AssetClassOf("XAG", "USD") == SDB_CLASS_COMMODITY &&
              AssetClassOf("BTC", "USD") == SDB_CLASS_CRYPTO && AssetClassOf("USD", "USD") == SDB_CLASS_OTHER &&
              AssetClassOf("", "") == SDB_CLASS_OTHER);
   int limits[] = {5, 3, 1, 1};
   AssertTrue("TC-RM-32", "batas per kategori dari input {5,3,1,1}; OTHER = 1",
              ClassPositionLimit(SDB_CLASS_FOREX_MAJOR, limits) == 5 && ClassPositionLimit(SDB_CLASS_FOREX_CROSS, limits) == 3 &&
              ClassPositionLimit(SDB_CLASS_COMMODITY, limits) == 1 && ClassPositionLimit(SDB_CLASS_CRYPTO, limits) == 1 &&
              ClassPositionLimit(SDB_CLASS_OTHER, limits) == 1);
  }

void RunTestRiskMath()
  {
   TfBeginSuite("RiskMath");
   RunTestRiskMathLot();
   RunTestRiskMathRisk();
   RunTestRiskMathDrawdown();
   RunTestRiskMathDay();
   RunTestRiskMathClose();
   RunTestRiskMathClass();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTRISKMATH_MQH
