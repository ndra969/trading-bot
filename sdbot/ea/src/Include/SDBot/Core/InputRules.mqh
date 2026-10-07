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
   int               heartbeatMinutes;   // InpHeartbeatMinutes: 0 = mati (spec 09 Req 1.1)
   int               swingStrength;      // analisis struktur (spec 10)
   int               structureLookback;
   int               emaPeriod;
   int               emaSlopeBars;
   double            zoneMinWidthAtr;    // zona S&D (spec 11)
   double            zoneMaxWidthAtr;
   double            zoneMinLegAtr;
   int               zoneLegBars;
   int               maxZoneAgeBars;
   double            minConfluenceScore; // sinyal dan entry (spec 13): persen dari maksimum aktif
   double            minRR;
   double            slBufferAtr;
   double            minSlAtr;
   double            maxSlAtr;
   bool              sessionTokyo;       // filter sesi dan spread (spec 14)
   bool              sessionLondon;
   bool              sessionNewYork;
   int               maxSpreadPoints;    // 0 = mati
   int               testerUtcOffsetHours;
   int               maxSameDirectionPerCurrency; // eksposur (spec 15), 0 = mati
   bool              newsFilter;         // filter berita (spec 16)
   int               newsHighMinutes;
   int               newsMediumMinutes;
   string            newsCsvFile;        // hanya tester
   ENUM_SDB_COMPONENT_MODE scoreFibMode;  // spec 18: skor Fibonacci OFF / SHADOW / ACTIVE
   ENUM_SDB_COMPONENT_MODE scoreTrendlineMode; // spec 19
   ENUM_SDB_COMPONENT_MODE scoreBreakoutMode;  // spec 20
   ENUM_SDB_COMPONENT_MODE scoreRsiMode;       // spec 21
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
   bool                   signalsOn;            // pipeline sinyal membuka posisi (spec 13 Req 7.1, 7.3)
   string                 telegramToken;        // rahasia: tidak masuk InputValues, JSON sesi, maupun log (spec 09 Req 1.3)
   string                 telegramChatId;
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
   v.heartbeatMinutes = SDB_DEF_HEARTBEAT_MIN;
   v.swingStrength = SDB_DEF_SWING_STRENGTH;
   v.structureLookback = SDB_DEF_STRUCTURE_LOOKBACK;
   v.emaPeriod = SDB_DEF_EMA_PERIOD;
   v.emaSlopeBars = SDB_DEF_EMA_SLOPE_BARS;
   v.zoneMinWidthAtr = SDB_DEF_ZONE_MIN_WIDTH_ATR;
   v.zoneMaxWidthAtr = SDB_DEF_ZONE_MAX_WIDTH_ATR;
   v.zoneMinLegAtr = SDB_DEF_ZONE_MIN_LEG_ATR;
   v.zoneLegBars = SDB_DEF_ZONE_LEG_BARS;
   v.maxZoneAgeBars = SDB_DEF_MAX_ZONE_AGE_BARS;
   v.minConfluenceScore = SDB_DEF_MIN_CONFLUENCE_SCORE;
   v.minRR = SDB_DEF_MIN_RR;
   v.slBufferAtr = SDB_DEF_SL_BUFFER_ATR;
   v.minSlAtr = SDB_DEF_MIN_SL_ATR;
   v.maxSlAtr = SDB_DEF_MAX_SL_ATR;
   v.sessionTokyo = false;
   v.sessionLondon = true;
   v.sessionNewYork = true;
   v.maxSpreadPoints = 0;
   v.testerUtcOffsetHours = 0;
   v.maxSameDirectionPerCurrency = SDB_DEF_MAX_SAME_DIR_CCY;
   v.newsFilter = true;
   v.newsHighMinutes = SDB_DEF_NEWS_HIGH_MIN;
   v.newsMediumMinutes = SDB_DEF_NEWS_MEDIUM_MIN;
   v.newsCsvFile = SDB_DEF_NEWS_CSV;
   v.scoreFibMode = SDB_COMPONENT_SHADOW;
   v.scoreTrendlineMode = SDB_COMPONENT_SHADOW;
   v.scoreBreakoutMode = SDB_COMPONENT_SHADOW;
   v.scoreRsiMode = SDB_COMPONENT_SHADOW;
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

void IrCheckRange(const string name, const int value, const int lo, const int hi, string &errors)
  {
   if(value < lo || value > hi)
      IrAdd(errors, name + "=" + IntegerToString(value) + " harus " + IntegerToString(lo) + " <= x <= " + IntegerToString(hi));
  }

void IrCheckAnalysis(const InputValues &v, string &errors)
  {
   IrCheckRange("InpSwingStrength", v.swingStrength, SDB_MIN_SWING_STRENGTH, SDB_MAX_SWING_STRENGTH, errors);
   IrCheckRange("InpStructureLookback", v.structureLookback, SDB_MIN_STRUCTURE_LOOKBACK, SDB_MAX_STRUCTURE_LOOKBACK, errors);
   IrCheckRange("InpEmaPeriod", v.emaPeriod, SDB_MIN_EMA_PERIOD, SDB_MAX_EMA_PERIOD, errors);
   IrCheckRange("InpEmaSlopeBars", v.emaSlopeBars, SDB_MIN_EMA_SLOPE_BARS, SDB_MAX_EMA_SLOPE_BARS, errors);
  }

void IrCheckRangeD(const string name, const double value, const double lo, const double hi, string &errors)
  {
   if(value < lo || value > hi)
      IrAdd(errors, name + "=" + IrNum(value) + " harus " + IrNum(lo) + " <= x <= " + IrNum(hi));
  }

void IrCheckZones(const InputValues &v, string &errors)
  {
   IrCheckRangeD("InpZoneMinWidthAtr", v.zoneMinWidthAtr, SDB_MIN_ZONE_MIN_WIDTH_ATR, SDB_MAX_ZONE_MIN_WIDTH_ATR, errors);
   IrCheckRangeD("InpZoneMaxWidthAtr", v.zoneMaxWidthAtr, SDB_MIN_ZONE_MAX_WIDTH_ATR, SDB_MAX_ZONE_MAX_WIDTH_ATR, errors);
   if(v.zoneMinWidthAtr >= v.zoneMaxWidthAtr)
      IrAdd(errors, "InpZoneMinWidthAtr (" + IrNum(v.zoneMinWidthAtr) + ") harus < InpZoneMaxWidthAtr (" + IrNum(v.zoneMaxWidthAtr) + ")");
   IrCheckRangeD("InpZoneMinLegAtr", v.zoneMinLegAtr, SDB_MIN_ZONE_MIN_LEG_ATR, SDB_MAX_ZONE_MIN_LEG_ATR, errors);
   IrCheckRange("InpZoneLegBars", v.zoneLegBars, SDB_MIN_ZONE_LEG_BARS, SDB_MAX_ZONE_LEG_BARS, errors);
   IrCheckRange("InpMaxZoneAgeBars", v.maxZoneAgeBars, SDB_MIN_MAX_ZONE_AGE_BARS, SDB_MAX_MAX_ZONE_AGE_BARS, errors);
  }

void IrCheckSignals(const InputValues &v, string &errors)
  {
   IrCheckRangeD("InpMinConfluenceScore", v.minConfluenceScore, SDB_MIN_MIN_CONFLUENCE_SCORE, SDB_MAX_MIN_CONFLUENCE_SCORE, errors);
   IrCheckRangeD("InpMinRR", v.minRR, SDB_MIN_MIN_RR, SDB_MAX_MIN_RR, errors);
   IrCheckRangeD("InpSlBufferAtr", v.slBufferAtr, SDB_MIN_SL_BUFFER_ATR, SDB_MAX_SL_BUFFER_ATR, errors);
   IrCheckRangeD("InpMinSlAtr", v.minSlAtr, SDB_MIN_MIN_SL_ATR, SDB_MAX_MIN_SL_ATR, errors);
   IrCheckRangeD("InpMaxSlAtr", v.maxSlAtr, SDB_MIN_MAX_SL_ATR, SDB_MAX_MAX_SL_ATR, errors);
   if(v.minSlAtr >= v.maxSlAtr)
      IrAdd(errors, "InpMinSlAtr (" + IrNum(v.minSlAtr) + ") harus < InpMaxSlAtr (" + IrNum(v.maxSlAtr) + ")");
   IrCheckRange("InpMaxSpreadPoints", v.maxSpreadPoints, 0, SDB_MAX_MAX_SPREAD_POINTS, errors);
   IrCheckRange("InpTesterUtcOffsetHours", v.testerUtcOffsetHours, SDB_MIN_TESTER_UTC_OFFSET_H, SDB_MAX_TESTER_UTC_OFFSET_H, errors);
   IrCheckRange("InpMaxSameDirectionPerCurrency", v.maxSameDirectionPerCurrency, 0, SDB_MAX_MAX_SAME_DIR_CCY, errors);
   IrCheckRange("InpNewsHighMinutes", v.newsHighMinutes, 0, SDB_MAX_NEWS_MIN, errors);
   IrCheckRange("InpNewsMediumMinutes", v.newsMediumMinutes, 0, SDB_MAX_NEWS_MIN, errors);
   IrCheckRange("InpScoreFibMode", (int)v.scoreFibMode, SDB_COMPONENT_OFF, SDB_COMPONENT_ACTIVE, errors);
   IrCheckRange("InpScoreTrendlineMode", (int)v.scoreTrendlineMode, SDB_COMPONENT_OFF, SDB_COMPONENT_ACTIVE, errors);
   IrCheckRange("InpScoreBreakoutMode", (int)v.scoreBreakoutMode, SDB_COMPONENT_OFF, SDB_COMPONENT_ACTIVE, errors);
   IrCheckRange("InpScoreRsiMode", (int)v.scoreRsiMode, SDB_COMPONENT_OFF, SDB_COMPONENT_ACTIVE, errors);
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
   IrCheckAnalysis(v, errors);
   IrCheckZones(v, errors);
   IrCheckSignals(v, errors);
   if(v.heartbeatMinutes != 0 && (v.heartbeatMinutes < SDB_MIN_HEARTBEAT_MIN || v.heartbeatMinutes > SDB_MAX_HEARTBEAT_MIN))
      IrAdd(errors, "InpHeartbeatMinutes=" + IntegerToString(v.heartbeatMinutes) + " harus 0 (mati) atau " +
            IntegerToString(SDB_MIN_HEARTBEAT_MIN) + " <= x <= " + IntegerToString(SDB_MAX_HEARTBEAT_MIN));
   return errors == "";
  }

#endif // SDB_CORE_INPUTRULES_MQH
