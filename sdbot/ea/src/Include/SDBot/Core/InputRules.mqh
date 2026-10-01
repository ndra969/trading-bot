//+------------------------------------------------------------------+
//| InputRules.mqh — batas aman input SDBot (spec 02 Req 1). Fungsi murni:
//| menerima struct nilai, bukan membaca input global, agar bisa diuji.
//+------------------------------------------------------------------+
#ifndef SDB_CORE_INPUTRULES_MQH
#define SDB_CORE_INPUTRULES_MQH

#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/Types.mqh>

struct InputValues
  {
   long              magic;
   double            riskPerTradePct;
   double            maxOpenRiskPct;
   double            dailyLossPct;
   double            ddReducePct;
   double            ddStopPct;
   double            breakevenR;
   int               breakevenBufferPoints;
   double            partialR;
   double            partialPct;
   int               trailAtrPeriod;
   double            trailAtrMult;
   int               maxPosForexMajor;   // batas posisi SDBot per kategori aset di akun (spec 05 Req 2.8)
   int               maxPosForexCross;
   int               maxPosCommodity;
   int               maxPosCrypto;
  };

// Semua yang dibutuhkan CSdbApp dari input, agar orkestrasi bisa diuji tanpa input global
// (spec 04 design §4.4). Dibangun CurrentAppConfig() di Inputs.mqh.
struct SdbAppConfig
  {
   ENUM_SDB_APP_MODE      mode;
   InputValues            inputs;
   string                 symbolSuffix;
   bool                   allowLive;
   ENUM_SDB_LOG_LEVEL     logLevel;
   ENUM_SDB_TRADING_STYLE style;
   string                 inputsJson;
   string                 eaVersion;
   ENUM_SDB_DB_TARGET     dbTarget;
   bool                   resetEmergencyStop;   // InpResetEmergencyStop (spec 05 Req 5.5)
   string                 presetTag;            // InpPresetTag (spec 07 Req 2.6)
  };

InputValues DefaultInputValues()
  {
   InputValues v;
   v.magic = SDB_DEF_MAGIC;
   v.riskPerTradePct = SDB_DEF_RISK_PER_TRADE_PCT;
   v.maxOpenRiskPct = SDB_DEF_MAX_OPEN_RISK_PCT;
   v.dailyLossPct = SDB_DEF_DAILY_LOSS_PCT;
   v.ddReducePct = SDB_DEF_DD_REDUCE_PCT;
   v.ddStopPct = SDB_DEF_DD_STOP_PCT;
   v.breakevenR = SDB_DEF_BREAKEVEN_R;
   v.breakevenBufferPoints = SDB_DEF_BREAKEVEN_BUFFER_PTS;
   v.partialR = SDB_DEF_PARTIAL_R;
   v.partialPct = SDB_DEF_PARTIAL_PCT;
   v.trailAtrPeriod = SDB_DEF_TRAIL_ATR_PERIOD;
   v.trailAtrMult = SDB_DEF_TRAIL_ATR_MULT;
   v.maxPosForexMajor = SDB_DEF_MAX_POS_FOREX_MAJOR;
   v.maxPosForexCross = SDB_DEF_MAX_POS_FOREX_CROSS;
   v.maxPosCommodity = SDB_DEF_MAX_POS_COMMODITY;
   v.maxPosCrypto = SDB_DEF_MAX_POS_CRYPTO;
   return v;
  }

string IrNum(const double x) { return DoubleToString(x, 2); }

// Tambahkan satu kesalahan; semua kesalahan dilaporkan sekaligus (Req 1.3).
void IrAdd(string &errors, const string message)
  {
   if(errors != "")
      errors += "; ";
   errors += message;
  }

void IrCheckRisk(const InputValues &v, string &errors)
  {
   if(v.riskPerTradePct <= 0.0 || v.riskPerTradePct > SDB_MAX_RISK_PER_TRADE_PCT)
      IrAdd(errors, "InpRiskPerTradePct=" + IrNum(v.riskPerTradePct) + " harus 0 < x <= " + IrNum(SDB_MAX_RISK_PER_TRADE_PCT));
   if(v.maxOpenRiskPct < v.riskPerTradePct || v.maxOpenRiskPct > SDB_MAX_OPEN_RISK_PCT)
      IrAdd(errors, "InpMaxOpenRiskPct=" + IrNum(v.maxOpenRiskPct) + " harus InpRiskPerTradePct (" +
            IrNum(v.riskPerTradePct) + ") <= x <= " + IrNum(SDB_MAX_OPEN_RISK_PCT));
   if(v.dailyLossPct <= 0.0 || v.dailyLossPct > SDB_MAX_DAILY_LOSS_PCT)
      IrAdd(errors, "InpDailyLossPct=" + IrNum(v.dailyLossPct) + " harus 0 < x <= " + IrNum(SDB_MAX_DAILY_LOSS_PCT));
   if(v.ddReducePct <= 0.0 || v.ddReducePct >= v.ddStopPct)
      IrAdd(errors, "InpDDReducePct=" + IrNum(v.ddReducePct) + " harus 0 < x < InpDDStopPct (" + IrNum(v.ddStopPct) + ")");
   if(v.ddStopPct <= v.ddReducePct || v.ddStopPct > SDB_MAX_DD_STOP_PCT)
      IrAdd(errors, "InpDDStopPct=" + IrNum(v.ddStopPct) + " harus InpDDReducePct (" + IrNum(v.ddReducePct) +
            ") < x <= " + IrNum(SDB_MAX_DD_STOP_PCT));
  }

void IrCheckClassLimit(const string name, const int value, string &errors)
  {
   if(value < 1 || value > SDB_MAX_POS_PER_CLASS)
      IrAdd(errors, name + "=" + IntegerToString(value) + " harus 1 <= x <= " + IntegerToString(SDB_MAX_POS_PER_CLASS));
  }

void IrCheckPosition(const InputValues &v, string &errors)
  {
   if(v.breakevenR <= 0.0 || v.breakevenR >= v.partialR)
      IrAdd(errors, "InpBreakevenR=" + IrNum(v.breakevenR) + " harus 0 < x < InpPartialR (" + IrNum(v.partialR) + ")");
   if(v.breakevenBufferPoints < 0 || v.breakevenBufferPoints > SDB_MAX_BREAKEVEN_BUFFER_PTS)
      IrAdd(errors, "InpBreakevenBufferPoints=" + IntegerToString(v.breakevenBufferPoints) + " harus 0 <= x <= " +
            IntegerToString(SDB_MAX_BREAKEVEN_BUFFER_PTS));
   if(v.partialR <= v.breakevenR || v.partialR > SDB_MAX_PARTIAL_R)
      IrAdd(errors, "InpPartialR=" + IrNum(v.partialR) + " harus InpBreakevenR (" + IrNum(v.breakevenR) +
            ") < x <= " + IrNum(SDB_MAX_PARTIAL_R));
   if(v.partialPct <= 0.0 || v.partialPct >= 100.0)
      IrAdd(errors, "InpPartialPct=" + IrNum(v.partialPct) + " harus 0 < x < 100");
   if(v.trailAtrPeriod < SDB_MIN_TRAIL_ATR_PERIOD || v.trailAtrPeriod > SDB_MAX_TRAIL_ATR_PERIOD)
      IrAdd(errors, "InpTrailATRPeriod=" + IntegerToString(v.trailAtrPeriod) + " harus " +
            IntegerToString(SDB_MIN_TRAIL_ATR_PERIOD) + " <= x <= " + IntegerToString(SDB_MAX_TRAIL_ATR_PERIOD));
   if(v.trailAtrMult <= 0.0 || v.trailAtrMult > SDB_MAX_TRAIL_ATR_MULT)
      IrAdd(errors, "InpTrailATRMult=" + IrNum(v.trailAtrMult) + " harus 0 < x <= " + IrNum(SDB_MAX_TRAIL_ATR_MULT));
  }

// true bila semua lolos; errors berisi semua kesalahan dipisah "; ".
// allowHarnessMagic: hanya harness uji yang boleh memakai SDB_MAGIC_HARNESS (spec 04 Req 7.3).
bool ValidateInputValues(const InputValues &v, const bool allowHarnessMagic, string &errors)
  {
   errors = "";
   bool harnessMagic = allowHarnessMagic && v.magic == SDB_MAGIC_HARNESS;
   if(!harnessMagic && (v.magic < SDB_MAGIC_MIN || v.magic > SDB_MAGIC_MAX))
      IrAdd(errors, "InpMagicNumber=" + IntegerToString(v.magic) + " harus di blok SDBot " +
            IntegerToString(SDB_MAGIC_MIN) + "-" + IntegerToString(SDB_MAGIC_MAX) + " (satu nomor per pair)");
   IrCheckRisk(v, errors);
   IrCheckClassLimit("InpMaxPosForexMajor", v.maxPosForexMajor, errors);
   IrCheckClassLimit("InpMaxPosForexCross", v.maxPosForexCross, errors);
   IrCheckClassLimit("InpMaxPosCommodity", v.maxPosCommodity, errors);
   IrCheckClassLimit("InpMaxPosCrypto", v.maxPosCrypto, errors);
   IrCheckPosition(v, errors);
   return errors == "";
  }

#endif // SDB_CORE_INPUTRULES_MQH
