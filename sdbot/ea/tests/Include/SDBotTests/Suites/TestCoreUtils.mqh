//+------------------------------------------------------------------+
//| TestCoreUtils.mqh — input dan aturan validasinya (spec 02 Req 1).
//| Bagian util/log (TC-CU-09..15) ditambahkan di task 3.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTCOREUTILS_MQH
#define SDB_SUITES_TESTCOREUTILS_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/Inputs.mqh>
#include <SDBot/Core/Utils.mqh>

bool CuContains(const string text, const string part)
  {
   return StringFind(text, part) >= 0;
  }

// Validasi satu set input; kembalikan hasil dan pesan kesalahannya.
bool CuValidate(const InputValues &v, string &errors)
  {
   return ValidateInputValues(v, false, errors);
  }

void RunTestCoreUtilsInputs()
  {
   string err;
   InputValues v = DefaultInputValues();

   AssertTrue("TC-CU-01", "semua default lolos validasi", CuValidate(v, err));

   // Default di Inputs.mqh dan DefaultInputValues() berasal dari konstanta yang sama.
   InputValues cur = CurrentInputs();
   AssertTrue("TC-CU-01b", "CurrentInputs() dengan input default sama dengan DefaultInputValues()",
              cur.magic == v.magic && cur.riskPerTradePct == v.riskPerTradePct &&
              cur.maxOpenRiskPct == v.maxOpenRiskPct && cur.dailyLossPct == v.dailyLossPct &&
              cur.ddReducePct == v.ddReducePct && cur.ddStopPct == v.ddStopPct &&
              cur.breakevenR == v.breakevenR && cur.breakevenBufferPoints == v.breakevenBufferPoints &&
              cur.partialR == v.partialR && cur.partialPct == v.partialPct &&
              cur.trailAtrPeriod == v.trailAtrPeriod && cur.trailAtrMult == v.trailAtrMult);
   AssertIntEq("TC-CU-01c", "magic default di blok SDBot", v.magic, 2026091901);

   v = DefaultInputValues();
   v.riskPerTradePct = 1.5;
   bool ok = CuValidate(v, err);
   AssertTrue("TC-CU-02", "risk per trade 1.5 ditolak dan pesan menyebut input serta batas 1.0",
              !ok && CuContains(err, "InpRiskPerTradePct") && CuContains(err, "1.0"));

   v = DefaultInputValues();
   v.riskPerTradePct = 0.0;
   AssertTrue("TC-CU-03", "risk per trade 0 ditolak", !CuValidate(v, err) && CuContains(err, "InpRiskPerTradePct"));

   v = DefaultInputValues();
   v.maxOpenRiskPct = 0.3;
   ok = CuValidate(v, err);
   AssertTrue("TC-CU-04", "max open risk < risk per trade ditolak (hubungan antar-input)",
              !ok && CuContains(err, "InpMaxOpenRiskPct") && CuContains(err, "InpRiskPerTradePct"));

   v = DefaultInputValues();
   v.breakevenR = 1.5;
   v.partialR = 1.5;
   ok = CuValidate(v, err);
   AssertTrue("TC-CU-05", "BE R >= partial R ditolak", !ok && CuContains(err, "InpBreakevenR") && CuContains(err, "InpPartialR"));

   v = DefaultInputValues();
   v.ddReducePct = 15.0;
   v.ddStopPct = 10.0;
   ok = CuValidate(v, err);
   AssertTrue("TC-CU-06", "DD reduce >= DD stop ditolak", !ok && CuContains(err, "InpDDReducePct") && CuContains(err, "InpDDStopPct"));

   v = DefaultInputValues();
   v.partialPct = 100.0;
   AssertTrue("TC-CU-07", "partial pct 100 ditolak", !CuValidate(v, err) && CuContains(err, "InpPartialPct"));

   v = DefaultInputValues();
   v.magic = 0;
   v.riskPerTradePct = 2.0;
   ok = CuValidate(v, err);
   AssertTrue("TC-CU-08", "dua kesalahan sekaligus disebut dalam satu pesan",
              !ok && CuContains(err, "InpMagicNumber") && CuContains(err, "InpRiskPerTradePct"));

   v = DefaultInputValues();
   v.magic = 2026091904;
   bool okLow = CuValidate(v, err);
   v.magic = 2026091999;
   bool okHigh = CuValidate(v, err);
   AssertTrue("TC-CU-08b", "magic 2026091904 dan 2026091999 lolos", okLow && okHigh);

   long bad[] = {20260919, 2026092000, 2026091900};
   bool allRejected = true;
   bool allMention = true;
   for(int i = 0; i < ArraySize(bad); i++)
     {
      v = DefaultInputValues();
      v.magic = bad[i];
      if(CuValidate(v, err))
         allRejected = false;
      if(!CuContains(err, "2026091901") || !CuContains(err, "2026091999"))
         allMention = false;
     }
   AssertTrue("TC-CU-08c", "magic 20260919 / 2026092000 / 2026091900 ditolak dengan rentang yang benar",
              allRejected && allMention);

   // Magic cadangan harness hanya diterima dalam mode harness (spec 04 Req 7.3, EC-19).
   v = DefaultInputValues();
   v.magic = SDB_MAGIC_HARNESS;
   bool harnessOk = ValidateInputValues(v, true, err);
   v.magic = SDB_MAGIC_HARNESS - 1;
   bool belowRejected = !ValidateInputValues(v, true, err);
   v.magic = 2026091901;
   bool normalOk = ValidateInputValues(v, true, err);
   AssertTrue("TC-IR-01", "mode harness: 2026091900 lolos, 2026091899 ditolak, 2026091901 tetap lolos",
              harnessOk && belowRejected && normalOk);

   // TC-SU-30 (spec 09 Req 1.1): heartbeat 0 = mati, selain itu 5-1440 menit.
   bool hbOk = true, hbBad = true;
   int okValues[] = {0, 5, 60, 1440};
   int badValues[] = {3, -1, 1441};
   for(int i = 0; i < ArraySize(okValues); i++)
     {
      v = DefaultInputValues();
      v.heartbeatMinutes = okValues[i];
      hbOk = hbOk && ValidateInputValues(v, false, err);
     }
   for(int i = 0; i < ArraySize(badValues); i++)
     {
      v = DefaultInputValues();
      v.heartbeatMinutes = badValues[i];
      hbBad = hbBad && !ValidateInputValues(v, false, err) && CuContains(err, "InpHeartbeatMinutes");
     }
   AssertTrue("TC-SU-30", "InpHeartbeatMinutes: 0, 5, 60, 1440 lolos; 3, -1, 1441 ditolak; default 60",
              hbOk && hbBad && DefaultInputValues().heartbeatMinutes == 60);

   // Batas posisi per kategori aset (spec 05 Req 2.8, PC-10): default dari bot Python, batas 1-20.
   v = DefaultInputValues();
   bool defaultsOk = v.maxPosForexMajor == 5 && v.maxPosForexCross == 3 && v.maxPosCommodity == 1 &&
                     v.maxPosCrypto == 1 && CuValidate(v, err);
   v.maxPosForexMajor = 0;
   v.maxPosForexCross = 21;
   v.maxPosCommodity = 0;
   v.maxPosCrypto = 21;
   ok = CuValidate(v, err);
   AssertTrue("TC-CU-08e", "batas posisi per kategori: default 5/3/1/1 lolos; 0 dan 21 ditolak dengan nama input",
              defaultsOk && !ok && CuContains(err, "InpMaxPosForexMajor") && CuContains(err, "InpMaxPosForexCross") &&
              CuContains(err, "InpMaxPosCommodity") && CuContains(err, "InpMaxPosCrypto"));

   v = DefaultInputValues();
   v.trailAtrPeriod = 1;
   v.trailAtrMult = 0.0;
   v.breakevenBufferPoints = -1;
   v.dailyLossPct = 11.0;
   ok = CuValidate(v, err);
   AssertTrue("TC-CU-08d", "batas ATR, buffer BE, dan rugi harian ditegakkan",
              !ok && CuContains(err, "InpTrailATRPeriod") && CuContains(err, "InpTrailATRMult") &&
              CuContains(err, "InpBreakevenBufferPoints") && CuContains(err, "InpDailyLossPct"));
  }

bool CuTfEq(const ENUM_SDB_TRADING_STYLE style, const ENUM_TIMEFRAMES h, const ENUM_TIMEFRAMES m, const ENUM_TIMEFRAMES l)
  {
   ENUM_TIMEFRAMES htf, mtf, ltf;
   StyleTimeframes(style, htf, mtf, ltf);
   return htf == h && mtf == m && ltf == l;
  }

void RunTestCoreUtilsLogAndUtil()
  {
   AssertStrEq("TC-CU-09", "format baris log RULES",
               FormatLogLine(SDB_LOG_WARN, "Filters", "EURUSDc", "sinyal ditolak | alasan=spread"),
               "[SDB][WARN][Filters][EURUSDc] sinyal ditolak | alasan=spread");

   CLogThrottle th;
   datetime t0 = D'2026.09.29 10:00:00';
   int sup = -1;
   bool first = th.Allow("k", t0, 60, sup);
   bool anyAllowed = false;
   for(int i = 1; i <= 4; i++)
      if(th.Allow("k", t0 + i * 2, 60, sup))
         anyAllowed = true;
   AssertTrue("TC-CU-10", "kunci sama 5x dalam 10 detik: pertama lolos, 4 berikutnya ditahan", first && !anyAllowed);
   bool again = th.Allow("k", t0 + 61, 60, sup);
   AssertTrue("TC-CU-11", "setelah 61 detik lolos lagi dengan 4 pesan ditahan", again && sup == 4);
   AssertStrEq("TC-CU-11b", "jumlah yang ditahan disebut di cetakan berikutnya",
               FormatSuppressed("koneksi putus", 4), "koneksi putus (+4 ditahan)");
   AssertStrEq("TC-CU-11c", "tanpa pesan ditahan, teks tidak berubah", FormatSuppressed("koneksi putus", 0), "koneksi putus");

   CLogThrottle lru;
   datetime t1 = D'2026.09.29 11:00:00';
   for(int k = 0; k < SDB_LOG_THROTTLE_SLOTS + 1; k++)
      lru.Allow("key" + IntegerToString(k), t1 + k, 3600, sup);
   AssertTrue("TC-CU-12", "65 kunci: kunci tertua tergusur sehingga lolos lagi walau masih dalam interval",
              lru.Allow("key0", t1 + 100, 3600, sup));

   AssertEq("TC-CU-13", "NormalizePriceTo 1.082346 ke 5 digit", NormalizePriceTo(1.082346, 5), 1.08235, 1e-10);
   AssertEq("TC-CU-13b", "NormalizePriceTo 1.082344 ke 5 digit", NormalizePriceTo(1.082344, 5), 1.08234, 1e-10);
   AssertEq("TC-CU-13c", "NormalizePriceTo JPY 161.2346 ke 3 digit", NormalizePriceTo(161.2346, 3), 161.235, 1e-10);

   AssertTrue("TC-CU-14", "day trading: H4 / H1 / M15", CuTfEq(SDB_STYLE_DAY, PERIOD_H4, PERIOD_H1, PERIOD_M15));
   AssertTrue("TC-CU-15a", "scalping: M15 / M5 / M1", CuTfEq(SDB_STYLE_SCALPING, PERIOD_M15, PERIOD_M5, PERIOD_M1));
   AssertTrue("TC-CU-15b", "swing: W1 / D1 / H4", CuTfEq(SDB_STYLE_SWING, PERIOD_W1, PERIOD_D1, PERIOD_H4));
   AssertTrue("TC-CU-15c", "position: MN1 / W1 / D1", CuTfEq(SDB_STYLE_POSITION, PERIOD_MN1, PERIOD_W1, PERIOD_D1));

   AssertStrEq("TC-CU-16", "ErrText memberi kode error", ErrText(4756), "err=4756");

   // TC-LG-01: level INFO tidak mencetak DEBUG; baris yang dicetak mengikuti format.
   SdbSetLogLevel(SDB_LOG_INFO);
   SdbLogCaptureStart();
   LogDebug("Test", "tidak boleh muncul");
   LogInfo("Test", "muncul");
   LogThrottled(SDB_LOG_WARN, "tc-lg-01", 3600, "Test", "sekali saja");
   LogThrottled(SDB_LOG_WARN, "tc-lg-01", 3600, "Test", "sekali saja");
   SdbLogCaptureStop();
   AssertIntEq("TC-LG-01a", "DEBUG disaring, INFO dan WARN pertama tercetak", SdbLogCapturedCount(), 2);
   AssertStrEq("TC-LG-01b", "baris INFO sesuai format", SdbLogCaptured(0),
               FormatLogLine(SDB_LOG_INFO, "Test", _Symbol, "muncul"));
   SdbSetLogLevel(SDB_LOG_DEBUG);
   SdbLogCaptureStart();
   LogDebug("Test", "sekarang muncul");
   SdbLogCaptureStop();
   AssertIntEq("TC-LG-01c", "level DEBUG mencetak DEBUG", SdbLogCapturedCount(), 1);
   SdbSetLogLevel(SDB_LOG_INFO);
  }

void RunTestCoreUtils()
  {
   TfBeginSuite("CoreUtils");
   RunTestCoreUtilsInputs();
   RunTestCoreUtilsLogAndUtil();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTCOREUTILS_MQH
