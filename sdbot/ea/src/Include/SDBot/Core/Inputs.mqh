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
#include <SDBot/Core/Utils.mqh>

input group "Umum"
input long                   InpMagicNumber           = SDB_DEF_MAGIC;              // Magic (2026091901-2026091999, satu per pair)
input ENUM_SDB_TRADING_STYLE InpTradingStyle          = SDB_STYLE_DAY;              // Gaya trading
input string                 InpSymbolSuffix          = "";                         // Akhiran simbol broker (akun cent Exness: c)
input bool                   InpAllowLiveTrading      = false;                      // Izinkan akun real/cent
input ENUM_SDB_LOG_LEVEL     InpLogLevel              = SDB_LOG_INFO;               // Level log terminal
input string                 InpPresetTag             = "";                         // Simbol preset (diisi file .set; kosong = tidak dicek)

input group "Risiko"
input double                 InpRiskPerTradePct       = SDB_DEF_RISK_PER_TRADE_PCT; // Risiko per trade (% balance, maks 1)
input double                 InpMaxOpenRiskPct        = SDB_DEF_MAX_OPEN_RISK_PCT;  // Total risiko posisi terbuka (%)
input double                 InpDailyLossPct          = SDB_DEF_DAILY_LOSS_PCT;     // Batas rugi harian (% balance awal hari)
input int                    InpMaxPosForexMajor      = SDB_DEF_MAX_POS_FOREX_MAJOR; // Maks posisi SDBot forex major di akun
input int                    InpMaxPosForexCross      = SDB_DEF_MAX_POS_FOREX_CROSS; // Maks posisi SDBot forex cross di akun
input int                    InpMaxPosCommodity       = SDB_DEF_MAX_POS_COMMODITY;   // Maks posisi SDBot komoditas di akun
input int                    InpMaxPosCrypto          = SDB_DEF_MAX_POS_CRYPTO;      // Maks posisi SDBot crypto di akun
input int                    InpMaxSameDirectionPerCurrency = SDB_DEF_MAX_SAME_DIR_CCY; // Maks posisi SDBot searah per mata uang (0 = mati)
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

input group "Analisis"
input int                    InpSwingStrength         = SDB_DEF_SWING_STRENGTH;     // Kekuatan swing fractal (bar tiap sisi, 1-5)
input int                    InpStructureLookback     = SDB_DEF_STRUCTURE_LOOKBACK; // Jendela struktur/BOS (bar, 20-500)
input int                    InpEmaPeriod             = SDB_DEF_EMA_PERIOD;         // Periode EMA tren (10-400)
input int                    InpEmaSlopeBars          = SDB_DEF_EMA_SLOPE_BARS;     // Kemiringan EMA dibanding N bar (1-20)
input double                 InpZoneMinWidthAtr       = SDB_DEF_ZONE_MIN_WIDTH_ATR; // Lebar zona minimum (x ATR MTF)
input double                 InpZoneMaxWidthAtr       = SDB_DEF_ZONE_MAX_WIDTH_ATR; // Lebar zona maksimum (x ATR MTF)
input double                 InpZoneMinLegAtr         = SDB_DEF_ZONE_MIN_LEG_ATR;   // Gerak keluar minimum (x ATR MTF)
input int                    InpZoneLegBars           = SDB_DEF_ZONE_LEG_BARS;      // Gerak keluar dalam N bar MTF (3-50)
input int                    InpMaxZoneAgeBars        = SDB_DEF_MAX_ZONE_AGE_BARS;  // Usia maksimum zona (bar MTF, PRD 100)

input group "Entry"
input double                 InpMinConfluenceScore    = SDB_DEF_MIN_CONFLUENCE_SCORE; // Skor minimum (% dari maksimum komponen aktif)
input double                 InpMinRR                 = SDB_DEF_MIN_RR;             // R:R minimum (TP ke zona lawan)
input double                 InpSlBufferAtr           = SDB_DEF_SL_BUFFER_ATR;      // Buffer SL di luar zona (x ATR MTF)
input double                 InpMinSlAtr              = SDB_DEF_MIN_SL_ATR;         // Jarak SL minimum (x ATR MTF)
input double                 InpMaxSlAtr              = SDB_DEF_MAX_SL_ATR;         // Jarak SL maksimum (x ATR MTF)

input group "Filter"
input bool                   InpSessionTokyo          = false;                      // Sesi Tokyo 00:00-08:00 UTC
input bool                   InpSessionLondon         = true;                       // Sesi London 08:00-17:00 UTC
input bool                   InpSessionNewYork        = true;                       // Sesi New York 13:00-22:00 UTC (semua false = filter mati)
input int                    InpMaxSpreadPoints       = 0;                          // Spread maksimum (point; 0 = mati, preset per simbol)
input int                    InpTesterUtcOffsetHours  = 0;                          // Selisih server-UTC di tester (jam)
input bool                   InpNewsFilter            = true;                       // Filter berita (kalender MT5; tester: CSV)
input int                    InpNewsHighMinutes       = SDB_DEF_NEWS_HIGH_MIN;      // Blackout berita high (+- menit, 0 = tidak)
input int                    InpNewsMediumMinutes     = SDB_DEF_NEWS_MEDIUM_MIN;    // Blackout berita medium (+- menit, 0 = tidak)
input string                 InpNewsCsvFile           = SDB_DEF_NEWS_CSV;           // CSV kalender di Common\Files (hanya tester)

input group "Notifikasi"
input string                 InpTelegramToken         = "";                         // Token bot Telegram (isi di *.local.set, jangan di-commit)
input string                 InpTelegramChatID        = "";                         // Chat ID Telegram (sama dengan bot Python)
input int                    InpHeartbeatMinutes      = SDB_DEF_HEARTBEAT_MIN;      // Heartbeat tiap N menit (0 = mati, 5-1440)

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
   v.maxPosForexMajor = InpMaxPosForexMajor;
   v.maxPosForexCross = InpMaxPosForexCross;
   v.maxPosCommodity = InpMaxPosCommodity;
   v.maxPosCrypto = InpMaxPosCrypto;
   v.heartbeatMinutes = InpHeartbeatMinutes;
   v.swingStrength = InpSwingStrength;
   v.structureLookback = InpStructureLookback;
   v.emaPeriod = InpEmaPeriod;
   v.emaSlopeBars = InpEmaSlopeBars;
   v.zoneMinWidthAtr = InpZoneMinWidthAtr;
   v.zoneMaxWidthAtr = InpZoneMaxWidthAtr;
   v.zoneMinLegAtr = InpZoneMinLegAtr;
   v.zoneLegBars = InpZoneLegBars;
   v.maxZoneAgeBars = InpMaxZoneAgeBars;
   v.minConfluenceScore = InpMinConfluenceScore;
   v.minRR = InpMinRR;
   v.slBufferAtr = InpSlBufferAtr;
   v.minSlAtr = InpMinSlAtr;
   v.maxSlAtr = InpMaxSlAtr;
   v.sessionTokyo = InpSessionTokyo;
   v.sessionLondon = InpSessionLondon;
   v.sessionNewYork = InpSessionNewYork;
   v.maxSpreadPoints = InpMaxSpreadPoints;
   v.testerUtcOffsetHours = InpTesterUtcOffsetHours;
   v.maxSameDirectionPerCurrency = InpMaxSameDirectionPerCurrency;
   v.newsFilter = InpNewsFilter;
   v.newsHighMinutes = InpNewsHighMinutes;
   v.newsMediumMinutes = InpNewsMediumMinutes;
   v.newsCsvFile = InpNewsCsvFile;
   return v;
  }

// Semua input dalam JSON kanonik untuk sessions.inputs_json; hash-nya mengelompokkan hasil
// per setelan (spec 03 Req 8). Setiap input baru wajib ditambahkan di sini.
string CurrentInputsJson()
  {
   string k[] = {"InpMagicNumber", "InpTradingStyle", "InpSymbolSuffix", "InpAllowLiveTrading", "InpLogLevel",
                 "InpRiskPerTradePct", "InpMaxOpenRiskPct", "InpDailyLossPct", "InpDDReducePct", "InpDDStopPct",
                 "InpResetEmergencyStop", "InpBreakevenR", "InpBreakevenBufferPoints", "InpPartialR",
                 "InpPartialPct", "InpTrailATRPeriod", "InpTrailATRMult", "InpMaxPosForexMajor",
                 "InpMaxPosForexCross", "InpMaxPosCommodity", "InpMaxPosCrypto", "InpPresetTag",
                 "InpHeartbeatMinutes", "InpTelegramConfigured", "InpSwingStrength", "InpStructureLookback",
                 "InpEmaPeriod", "InpEmaSlopeBars", "InpZoneMinWidthAtr", "InpZoneMaxWidthAtr", "InpZoneMinLegAtr",
                 "InpZoneLegBars", "InpMaxZoneAgeBars", "InpMinConfluenceScore", "InpMinRR", "InpSlBufferAtr",
                 "InpMinSlAtr", "InpMaxSlAtr", "InpSessionTokyo", "InpSessionLondon", "InpSessionNewYork",
                 "InpMaxSpreadPoints", "InpTesterUtcOffsetHours", "InpMaxSameDirectionPerCurrency",
                 "InpNewsFilter", "InpNewsHighMinutes", "InpNewsMediumMinutes", "InpNewsCsvFile"};
   string v[];
   ArrayResize(v, ArraySize(k));
   v[0] = JsonNum((double)InpMagicNumber);
   v[1] = JsonStr(EnumToString(InpTradingStyle));
   v[2] = JsonStr(InpSymbolSuffix);
   v[3] = JsonBool(InpAllowLiveTrading);
   v[4] = JsonStr(EnumToString(InpLogLevel));
   v[5] = JsonNum(InpRiskPerTradePct);
   v[6] = JsonNum(InpMaxOpenRiskPct);
   v[7] = JsonNum(InpDailyLossPct);
   v[8] = JsonNum(InpDDReducePct);
   v[9] = JsonNum(InpDDStopPct);
   v[10] = JsonBool(InpResetEmergencyStop);
   v[11] = JsonNum(InpBreakevenR);
   v[12] = JsonNum(InpBreakevenBufferPoints);
   v[13] = JsonNum(InpPartialR);
   v[14] = JsonNum(InpPartialPct);
   v[15] = JsonNum(InpTrailATRPeriod);
   v[16] = JsonNum(InpTrailATRMult);
   v[17] = JsonNum(InpMaxPosForexMajor);
   v[18] = JsonNum(InpMaxPosForexCross);
   v[19] = JsonNum(InpMaxPosCommodity);
   v[20] = JsonNum(InpMaxPosCrypto);
   v[21] = JsonStr(InpPresetTag);
   v[22] = JsonNum(InpHeartbeatMinutes);
   // Token dan chat ID rahasia: hanya tanda terisi, agar input_hash tidak membocorkan dan tidak berubah karenanya.
   v[23] = JsonBool(InpTelegramToken != "" && InpTelegramChatID != "");
   v[24] = JsonNum(InpSwingStrength);
   v[25] = JsonNum(InpStructureLookback);
   v[26] = JsonNum(InpEmaPeriod);
   v[27] = JsonNum(InpEmaSlopeBars);
   v[28] = JsonNum(InpZoneMinWidthAtr);
   v[29] = JsonNum(InpZoneMaxWidthAtr);
   v[30] = JsonNum(InpZoneMinLegAtr);
   v[31] = JsonNum(InpZoneLegBars);
   v[32] = JsonNum(InpMaxZoneAgeBars);
   v[33] = JsonNum(InpMinConfluenceScore);
   v[34] = JsonNum(InpMinRR);
   v[35] = JsonNum(InpSlBufferAtr);
   v[36] = JsonNum(InpMinSlAtr);
   v[37] = JsonNum(InpMaxSlAtr);
   v[38] = JsonBool(InpSessionTokyo);
   v[39] = JsonBool(InpSessionLondon);
   v[40] = JsonBool(InpSessionNewYork);
   v[41] = JsonNum(InpMaxSpreadPoints);
   v[42] = JsonNum(InpTesterUtcOffsetHours);
   v[43] = JsonNum(InpMaxSameDirectionPerCurrency);
   v[44] = JsonBool(InpNewsFilter);
   v[45] = JsonNum(InpNewsHighMinutes);
   v[46] = JsonNum(InpNewsMediumMinutes);
   v[47] = JsonStr(InpNewsCsvFile);
   return CanonicalJson(k, v);
  }

// Konfigurasi CSdbApp dari input (spec 04 design §4.4). Uji membangun SdbAppConfig sendiri.
SdbAppConfig CurrentAppConfig(const ENUM_SDB_APP_MODE mode, const string eaVersion)
  {
   SdbAppConfig c;
   c.mode = mode;
   c.inputs = CurrentInputs();
   c.signalsOn = (mode == SDB_APP_LIVE);   // EA utama; harness menyetel dari HarnessPipeline
   c.symbolSuffix = InpSymbolSuffix;
   c.allowLive = InpAllowLiveTrading;
   c.logLevel = InpLogLevel;
   c.style = InpTradingStyle;
   c.inputsJson = CurrentInputsJson();
   c.eaVersion = eaVersion;
   c.dbTarget = SdbDbTargetForRuntime();
   c.resetEmergencyStop = InpResetEmergencyStop;
   c.presetTag = InpPresetTag;
   c.telegramToken = InpTelegramToken;
   c.telegramChatId = InpTelegramChatID;
   return c;
  }

#endif // SDB_CORE_INPUTS_MQH
