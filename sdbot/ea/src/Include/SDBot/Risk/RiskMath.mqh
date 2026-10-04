//+------------------------------------------------------------------+
//| RiskMath.mqh — fungsi risiko murni (spec 05 design §4.1): lot dari
//| risiko persen, risiko order dan posisi, drawdown, rugi harian,
//| pergantian hari, reset emergency, operasi saldo, magic SDBot, sesi,
//| jadwal close all. Tanpa akses pasar, diuji di suite TestRiskMath.
//+------------------------------------------------------------------+
#ifndef SDB_RISK_RISKMATH_MQH
#define SDB_RISK_RISKMATH_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/SchemaEnums.mqh>
#include <SDBot/Core/Utils.mqh>   // IsSdbotMagic (dipindah ke Core di spec 09)

// Digit desimal step volume (0.01 -> 2, 0.1 -> 1, 1 -> 0), untuk menormalkan hasil kali floating point.
int StepDigits(const double step)
  {
   int d = 0;
   double v = step;
   while(d < 8 && MathAbs(v - MathRound(v)) > 1e-9)
     {
      v *= 10.0;
      d++;
     }
   return d;
  }

// Req 1.2: bulatkan ke bawah ke kelipatan step; epsilon agar 0.28999999 tetap 0.29 (EC-01).
double RoundLotDown(const double lot, const double step)
  {
   if(step <= 0.0 || lot <= 0.0)
      return 0.0;
   double steps = MathFloor(lot / step + 1e-9);
   return NormalizeDouble(steps * step, StepDigits(step));
  }

// Req 1.1–1.4, 1.6: lot = balance x risiko% / nilai uang per lot, dibulatkan ke bawah, tidak pernah ke atas.
double CalcLotSize(const double balance, const double riskPct, const double moneyPerLot, const double step,
                   const double vMin, const double vMax, ENUM_SDB_LOT_FLAG &flag)
  {
   if(moneyPerLot <= 0.0 || balance <= 0.0 || riskPct <= 0.0 || step <= 0.0)
     {
      flag = SDB_LOT_INVALID;
      return 0.0;
     }
   double lot = RoundLotDown(balance * riskPct / 100.0 / moneyPerLot, step);
   if(lot < vMin - 1e-9)
     {
      flag = SDB_LOT_BELOW_MIN;
      return 0.0;
     }
   if(lot > vMax + 1e-9)
     {
      flag = SDB_LOT_CAPPED_MAX;
      return RoundLotDown(vMax, step);
     }
   flag = SDB_LOT_OK;
   return lot;
  }

// Req 1.5: flag lot x 0.5 dari drawdown REDUCE.
double EffectiveRiskPct(const double riskPct, const bool lotReduced)
  {
   return lotReduced ? riskPct * 0.5 : riskPct;
  }

// Persen balance; balance <= 0 dianggap tak terhingga agar setiap batas persen menolak.
double RiskPctOf(const double riskMoney, const double balance)
  {
   if(balance <= 0.0)
      return DBL_MAX;
   return riskMoney / balance * 100.0;
  }

// Req 2.5: lossMoneyAtSl = OrderCalcProfit dari harga buka ke SL (negatif bila rugi).
// SL di harga buka atau lebih baik -> 0; tanpa SL -> balance x noSlRiskPct%.
double PositionRiskMoney(const bool isBuy, const double openPrice, const double sl, const double lossMoneyAtSl,
                         const double balance, const double noSlRiskPct)
  {
   if(sl <= 0.0)
      return balance * noSlRiskPct / 100.0;
   bool protectedSl = isBuy ? (sl >= openPrice) : (sl <= openPrice);
   if(protectedSl)
      return 0.0;
   return MathMax(0.0, -lossMoneyAtSl);
  }

//--- Drawdown, rugi harian, margin (Req 2.6, 3, 4)

double DrawdownPct(const double peak, const double equity)
  {
   if(peak <= 0.0 || equity >= peak)
      return 0.0;
   return (peak - equity) / peak * 100.0;
  }

// Positif = rugi, negatif = untung, dari balance awal hari (termasuk floating lewat equity).
double DailyLossPct(const double dayStartBalance, const double equity)
  {
   if(dayStartBalance <= 0.0)
      return 0.0;
   return (dayStartBalance - equity) / dayStartBalance * 100.0;
  }

// Ambang pulih dari REDUCE: 8% PRD, tetapi selalu di bawah ambang REDUCE agar flag tidak berkedip
// saat InpDDReducePct disetel < 8 (ditemukan SC-03). Rasio 0.8 = 8/10 dari default PRD.
double DdRecoverPct(const double reducePct)
  {
   return MathMin(SDB_DD_RECOVER_PCT, reducePct * SDB_DD_RECOVER_RATIO);
  }

// Mesin status design §4.1: STOP tidak pernah dilepas (5.7); REDUCE dilepas hanya di bawah recoverPct (3.5, EC-13).
ENUM_SDB_DD_LEVEL DrawdownLevel(const double dd, const ENUM_SDB_DD_LEVEL cur, const double infoPct, const double reducePct,
                                const double recoverPct, const double stopPct)
  {
   if(cur == SDB_DD_STOP || dd >= stopPct - SDB_RISK_EPS)
      return SDB_DD_STOP;
   if(dd >= reducePct - SDB_RISK_EPS)
      return SDB_DD_REDUCE;
   if(cur == SDB_DD_REDUCE && dd >= recoverPct - SDB_RISK_EPS)
      return SDB_DD_REDUCE;
   if(dd >= infoPct - SDB_RISK_EPS)
      return SDB_DD_INFO;
   return SDB_DD_NORMAL;
  }

// Akun tanpa margin terpakai: margin level MT5 = 0, padahal artinya tak terbatas (2.6).
double EffectiveMarginLevel(const double marginLevel, const double margin)
  {
   if(margin <= 0.0)
      return DBL_MAX;
   return marginLevel;
  }

//--- Hari server dan reset (Req 4.3, 4.4, 5.5–5.7)

datetime ServerDayStart(const datetime serverNow)
  {
   return serverNow - (datetime)((long)serverNow % 86400);
  }

bool IsNewServerDay(const datetime storedDay, const datetime serverNow)
  {
   return ServerDayStart(serverNow) > ServerDayStart(storedDay);
  }

// Hanya transisi false -> true; input yang lupa dikembalikan tidak mereset lagi (EC-07).
bool ResetRequested(const bool inputNow, const bool inputLastSeen)
  {
   return inputNow && !inputLastSeen;
  }

//--- Operasi saldo, magic, kategori aset (Req 2.8, 5.8, 7.1)

string BalanceOpType(const long dealType)
  {
   if(dealType == DEAL_TYPE_BALANCE)
      return SDB_BALANCE_OP_TYPE_BALANCE;
   if(dealType == DEAL_TYPE_CREDIT)
      return SDB_BALANCE_OP_TYPE_CREDIT;
   return "";
  }

bool CsvHas(const string csv, const string item)
  {
   return item != "" && StringFind("," + csv + ",", "," + item + ",") >= 0;
  }

// Kategori dari mata uang base/quote simbol (PC-10, design §9.9).
ENUM_SDB_ASSET_CLASS AssetClassOf(const string baseCcy, const string quoteCcy)
  {
   if(StringLen(baseCcy) != 3 || StringLen(quoteCcy) != 3 || baseCcy == quoteCcy)
      return SDB_CLASS_OTHER;
   if(CsvHas(SDB_COMMODITY_CURRENCIES, baseCcy))
      return SDB_CLASS_COMMODITY;
   if(CsvHas(SDB_CRYPTO_CURRENCIES, baseCcy))
      return SDB_CLASS_CRYPTO;
   if(CsvHas(SDB_COMMODITY_CURRENCIES, quoteCcy) || CsvHas(SDB_CRYPTO_CURRENCIES, quoteCcy))
      return SDB_CLASS_OTHER;
   if(baseCcy == "USD" || quoteCcy == "USD")
      return SDB_CLASS_FOREX_MAJOR;
   return SDB_CLASS_FOREX_CROSS;
  }

// limits[]: major, cross, komoditas, crypto (urutan ENUM_SDB_ASSET_CLASS).
int ClassPositionLimit(const ENUM_SDB_ASSET_CLASS c, const int &limits[])
  {
   int i = (int)c;
   if(c == SDB_CLASS_OTHER || i < 0 || i >= ArraySize(limits))
      return SDB_MAX_POS_OTHER_CLASS;
   return limits[i];
  }

//--- Close all (Req 5.1–5.3)

// Sesi trading satu hari, detik sejak 00:00 server, rentang [from, to).
bool InTradeSession(const int secOfDay, const int &from[], const int &to[])
  {
   int n = MathMin(ArraySize(from), ArraySize(to));
   for(int i = 0; i < n; i++)
     {
      bool inside = (from[i] < to[i]) ? (secOfDay >= from[i] && secOfDay < to[i])
                                      : (secOfDay >= from[i] || secOfDay < to[i]);   // to <= from: lewat tengah malam
      if(inside)
         return true;
     }
   return false;
  }

bool CloseAllDue(const datetime now, const datetime lastTry, const bool marketOpen)
  {
   int every = marketOpen ? SDB_CLOSE_ALL_RETRY_SEC : SDB_CLOSE_ALL_CLOSED_MARKET_SEC;
   return now - lastTry >= every;
  }

// Critical setelah 3 gagal berturut-turut saat pasar buka, lalu paling sering tiap 15 menit.
bool CloseAllAlertDue(const int consecutiveFails, const datetime now, const datetime lastAlert)
  {
   if(consecutiveFails < SDB_CLOSE_ALL_ALERT_FAILS)
      return false;
   return lastAlert == 0 || now - lastAlert >= SDB_CLOSE_ALL_ALERT_REPEAT_SEC;
  }

#endif // SDB_RISK_RISKMATH_MQH
