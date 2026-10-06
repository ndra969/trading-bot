//+------------------------------------------------------------------+
//| TestPresets.mqh — setiap preset di ea/src/Presets lolos aturan input
//| EA yang sama dengan saat dipasang (spec 07 Req 2.5, TC-IN-04). Sandbox
//| MQL5 tidak bisa membaca folder Presets, jadi run-ea-tests.ps1 menyalin
//| preset ke Common\Files\sdbot_presets\ sebelum unit run.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTPRESETS_MQH
#define SDB_SUITES_TESTPRESETS_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/InputRules.mqh>

#define TPR_DIR      "sdbot_presets\\"
#define TPR_EXPECTED 12

// Nama input EA yang boleh ada di preset (Core/Inputs.mqh); kunci lain = salah ketik.
string TprKnownKeys()
  {
   return ",InpMagicNumber,InpTradingStyle,InpSymbolSuffix,InpAllowLiveTrading,InpLogLevel,InpPresetTag,"
          "InpRiskPerTradePct,InpMaxOpenRiskPct,InpMaxPosForexMajor,InpMaxPosForexCross,InpMaxPosCommodity,"
          "InpMaxPosCrypto,InpDailyLossPct,InpDDReducePct,InpDDStopPct,InpResetEmergencyStop,InpBreakevenR,"
          "InpBreakevenBufferPoints,InpPartialR,InpPartialPct,InpTrailATRPeriod,InpTrailATRMult,"
          "InpTelegramToken,InpTelegramChatID,InpHeartbeatMinutes,"
          "InpSwingStrength,InpStructureLookback,InpEmaPeriod,InpEmaSlopeBars,"
          "InpZoneMinWidthAtr,InpZoneMaxWidthAtr,InpZoneMinLegAtr,InpZoneLegBars,InpMaxZoneAgeBars,"
          "InpMinConfluenceScore,InpMinRR,InpSlBufferAtr,InpMinSlAtr,InpMaxSlAtr,"
          "InpSessionTokyo,InpSessionLondon,InpSessionNewYork,InpMaxSpreadPoints,InpTesterUtcOffsetHours,"
          "InpMaxSameDirectionPerCurrency,InpNewsFilter,InpNewsHighMinutes,InpNewsMediumMinutes,InpNewsCsvFile,InpScoreFibMode,";
  }

void TprApply(InputValues &v, const string key, const string value)
  {
   if(key == "InpMagicNumber")                v.magic = StringToInteger(value);
   else if(key == "InpRiskPerTradePct")       v.riskPerTradePct = StringToDouble(value);
   else if(key == "InpMaxOpenRiskPct")        v.maxOpenRiskPct = StringToDouble(value);
   else if(key == "InpDailyLossPct")          v.dailyLossPct = StringToDouble(value);
   else if(key == "InpDDReducePct")           v.ddReducePct = StringToDouble(value);
   else if(key == "InpDDStopPct")             v.ddStopPct = StringToDouble(value);
   else if(key == "InpBreakevenR")            v.breakevenR = StringToDouble(value);
   else if(key == "InpBreakevenBufferPoints") v.breakevenBufferPoints = (int)StringToInteger(value);
   else if(key == "InpPartialR")              v.partialR = StringToDouble(value);
   else if(key == "InpPartialPct")            v.partialPct = StringToDouble(value);
   else if(key == "InpTrailATRPeriod")        v.trailAtrPeriod = (int)StringToInteger(value);
   else if(key == "InpTrailATRMult")          v.trailAtrMult = StringToDouble(value);
   else if(key == "InpMaxPosForexMajor")      v.maxPosForexMajor = (int)StringToInteger(value);
   else if(key == "InpMaxPosForexCross")      v.maxPosForexCross = (int)StringToInteger(value);
   else if(key == "InpMaxPosCommodity")       v.maxPosCommodity = (int)StringToInteger(value);
   else if(key == "InpMaxPosCrypto")          v.maxPosCrypto = (int)StringToInteger(value);
   else if(key == "InpHeartbeatMinutes")      v.heartbeatMinutes = (int)StringToInteger(value);
   else if(key == "InpSwingStrength")         v.swingStrength = (int)StringToInteger(value);
   else if(key == "InpStructureLookback")     v.structureLookback = (int)StringToInteger(value);
   else if(key == "InpEmaPeriod")             v.emaPeriod = (int)StringToInteger(value);
   else if(key == "InpEmaSlopeBars")          v.emaSlopeBars = (int)StringToInteger(value);
   else if(key == "InpZoneMinWidthAtr")       v.zoneMinWidthAtr = StringToDouble(value);
   else if(key == "InpZoneMaxWidthAtr")       v.zoneMaxWidthAtr = StringToDouble(value);
   else if(key == "InpZoneMinLegAtr")         v.zoneMinLegAtr = StringToDouble(value);
   else if(key == "InpZoneLegBars")           v.zoneLegBars = (int)StringToInteger(value);
   else if(key == "InpMaxZoneAgeBars")        v.maxZoneAgeBars = (int)StringToInteger(value);
   else if(key == "InpMinConfluenceScore")    v.minConfluenceScore = StringToDouble(value);
   else if(key == "InpMinRR")                 v.minRR = StringToDouble(value);
   else if(key == "InpSlBufferAtr")           v.slBufferAtr = StringToDouble(value);
   else if(key == "InpMinSlAtr")              v.minSlAtr = StringToDouble(value);
   else if(key == "InpMaxSlAtr")              v.maxSlAtr = StringToDouble(value);
   else if(key == "InpSessionTokyo")          v.sessionTokyo = (value == "true");
   else if(key == "InpSessionLondon")         v.sessionLondon = (value == "true");
   else if(key == "InpSessionNewYork")        v.sessionNewYork = (value == "true");
   else if(key == "InpMaxSpreadPoints")       v.maxSpreadPoints = (int)StringToInteger(value);
   else if(key == "InpTesterUtcOffsetHours")  v.testerUtcOffsetHours = (int)StringToInteger(value);
   else if(key == "InpMaxSameDirectionPerCurrency") v.maxSameDirectionPerCurrency = (int)StringToInteger(value);
   else if(key == "InpNewsFilter")            v.newsFilter = (value == "true");
   else if(key == "InpNewsHighMinutes")       v.newsHighMinutes = (int)StringToInteger(value);
   else if(key == "InpNewsMediumMinutes")     v.newsMediumMinutes = (int)StringToInteger(value);
   else if(key == "InpNewsCsvFile")           v.newsCsvFile = value;
   else if(key == "InpScoreFibMode")          v.scoreFibMode = (ENUM_SDB_COMPONENT_MODE)StringToInteger(value);
  }

// "" = lolos; selain itu alasan gagal.
string TprCheckFile(const string name)
  {
   int h = FileOpen(TPR_DIR + name, FILE_READ | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h == INVALID_HANDLE)
      return "tidak bisa dibuka " + IntegerToString(GetLastError());
   InputValues v = DefaultInputValues();
   string unknown = "";
   int telegramKeys = 0;
   int analysisKeys = 0;   // spec 10: 4 input analisis dengan default
   int zoneKeys = 0;       // spec 11: 5 input zona   // TC-PR-02 (spec 09 Req 1.8): token dan chat ID ada dan kosong, heartbeat ada
   while(!FileIsEnding(h))
     {
      string line = FileReadString(h);
      StringTrimLeft(line);
      StringTrimRight(line);
      int eq = StringFind(line, "=");
      if(line == "" || StringGetCharacter(line, 0) == ';' || eq <= 0)
         continue;
      string key = StringSubstr(line, 0, eq);
      if(StringFind(TprKnownKeys(), "," + key + ",") < 0 && unknown == "")
         unknown = key;
      string value = StringSubstr(line, eq + 1);
      if((key == "InpTelegramToken" || key == "InpTelegramChatID") && value == "")
         telegramKeys++;
      if(key == "InpHeartbeatMinutes" && value == "60")
         telegramKeys++;
      if((key == "InpSwingStrength" && value == "2") || (key == "InpStructureLookback" && value == "100") ||
         (key == "InpEmaPeriod" && value == "50") || (key == "InpEmaSlopeBars" && value == "3"))
         analysisKeys++;
      if(key == "InpZoneMinWidthAtr" || key == "InpZoneMaxWidthAtr" || key == "InpZoneMinLegAtr" || key == "InpZoneLegBars" ||
         key == "InpMaxZoneAgeBars")
         zoneKeys++;
      TprApply(v, key, StringSubstr(line, eq + 1));
     }
   FileClose(h);
   if(unknown != "")
      return "kunci bukan input EA: " + unknown;
   if(zoneKeys != 5)
      return "5 input zona wajib ada (spec 11)";
   if(analysisKeys != 4)
      return "InpSwingStrength=2, InpStructureLookback=100, InpEmaPeriod=50, InpEmaSlopeBars=3 wajib ada (spec 10)";
   if(telegramKeys != 3)
      return "InpTelegramToken/InpTelegramChatID kosong dan InpHeartbeatMinutes=60 wajib ada (TC-PR-02)";
   string errors;
   return ValidateInputValues(v, false, errors) ? "" : errors;
  }

void RunTestPresets()
  {
   TfBeginSuite("Presets");
   string name;
   long search = FileFindFirst(TPR_DIR + "*.set", name, FILE_COMMON);
   int files = 0, bad = 0;
   string firstBad = "";
   if(search != INVALID_HANDLE)
     {
      do
        {
         files++;
         string why = TprCheckFile(name);
         if(why != "")
           {
            bad++;
            if(firstBad == "")
               firstBad = name + ": " + why;
           }
        }
      while(FileFindNext(search, name));
      FileFindClose(search);
     }
   AssertTrue("TC-IN-04", StringFormat("preset tidak ditemukan / tidak lolos ValidateInputValues: %d file, gagal %d %s",
                                       files, bad, firstBad), files == TPR_EXPECTED && bad == 0);
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTPRESETS_MQH
