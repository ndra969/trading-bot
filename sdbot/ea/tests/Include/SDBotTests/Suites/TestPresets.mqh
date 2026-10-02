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
          "InpTelegramToken,InpTelegramChatID,InpHeartbeatMinutes,";
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
  }

// "" = lolos; selain itu alasan gagal.
string TprCheckFile(const string name)
  {
   int h = FileOpen(TPR_DIR + name, FILE_READ | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h == INVALID_HANDLE)
      return "tidak bisa dibuka " + IntegerToString(GetLastError());
   InputValues v = DefaultInputValues();
   string unknown = "";
   int telegramKeys = 0;   // TC-PR-02 (spec 09 Req 1.8): token dan chat ID ada dan kosong, heartbeat ada
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
      TprApply(v, key, StringSubstr(line, eq + 1));
     }
   FileClose(h);
   if(unknown != "")
      return "kunci bukan input EA: " + unknown;
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
