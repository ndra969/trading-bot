//+------------------------------------------------------------------+
//| Inputs.mqh — satu-satunya tempat deklarasi input SDBot (RULES).
//| Default dari PRD lewat konstanta SDB_DEF_* di Constants.mqh; batas
//| aman divalidasi ValidateInputValues() di InputRules.mqh.
//| Setiap input baru juga dicatat di tabel input sdbot/README.md.
//+------------------------------------------------------------------+
#ifndef SDB_CORE_INPUTS_MQH
#define SDB_CORE_INPUTS_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/InputRules.mqh>

input group "Umum"
input long                   InpMagicNumber           = SDB_DEF_MAGIC;              // Magic (2026091901-2026091999, satu per pair)
input ENUM_SDB_TRADING_STYLE InpTradingStyle          = SDB_STYLE_DAY;              // Gaya trading
input string                 InpSymbolSuffix          = "";                         // Akhiran simbol broker (akun cent Exness: c)
input bool                   InpAllowLiveTrading      = false;                      // Izinkan akun real/cent
input ENUM_SDB_LOG_LEVEL     InpLogLevel              = SDB_LOG_INFO;               // Level log terminal

input group "Risiko"
input double                 InpRiskPerTradePct       = SDB_DEF_RISK_PER_TRADE_PCT; // Risiko per trade (% balance, maks 1)
input double                 InpMaxOpenRiskPct        = SDB_DEF_MAX_OPEN_RISK_PCT;  // Total risiko posisi terbuka (%)
input double                 InpDailyLossPct          = SDB_DEF_DAILY_LOSS_PCT;     // Batas rugi harian (% balance awal hari)
input double                 InpDDReducePct           = SDB_DEF_DD_REDUCE_PCT;      // Drawdown: lot x 0.5 (%)
input double                 InpDDStopPct             = SDB_DEF_DD_STOP_PCT;        // Drawdown: close all + STOPPED (%)
input bool                   InpResetEmergencyStop    = false;                      // Buka STOPPED (ubah false -> true sekali)

input group "Posisi"
input double                 InpBreakevenR            = SDB_DEF_BREAKEVEN_R;        // Breakeven saat profit >= R
input int                    InpBreakevenBufferPoints = SDB_DEF_BREAKEVEN_BUFFER_PTS; // Buffer BE di atas spread (point)
input double                 InpPartialR              = SDB_DEF_PARTIAL_R;          // Partial close saat profit >= R
input double                 InpPartialPct            = SDB_DEF_PARTIAL_PCT;        // Partial close (% volume awal)
input int                    InpTrailATRPeriod        = SDB_DEF_TRAIL_ATR_PERIOD;   // Periode ATR trailing (LTF)
input double                 InpTrailATRMult          = SDB_DEF_TRAIL_ATR_MULT;     // Pengali ATR trailing

// Salin nilai input ke struct agar aturan validasi bisa diuji tanpa bergantung pada input global.
InputValues CurrentInputs()
  {
   InputValues v;
   v.magic = InpMagicNumber;
   v.riskPerTradePct = InpRiskPerTradePct;
   v.maxOpenRiskPct = InpMaxOpenRiskPct;
   v.dailyLossPct = InpDailyLossPct;
   v.ddReducePct = InpDDReducePct;
   v.ddStopPct = InpDDStopPct;
   v.breakevenR = InpBreakevenR;
   v.breakevenBufferPoints = InpBreakevenBufferPoints;
   v.partialR = InpPartialR;
   v.partialPct = InpPartialPct;
   v.trailAtrPeriod = InpTrailATRPeriod;
   v.trailAtrMult = InpTrailATRMult;
   return v;
  }

#endif // SDB_CORE_INPUTS_MQH
