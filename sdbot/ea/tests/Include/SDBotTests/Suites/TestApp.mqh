//+------------------------------------------------------------------+
//| TestApp.mqh — CSdbApp dengan SdbAppConfig buatan uji (spec 04
//| TC-APP-xx): urutan init, kode init, deinit, observer, dan jalur
//| broker CExecutor sungguhan. Hanya jalan di Strategy Tester: script
//| RunUnitTests di chart live tidak boleh memasang timer atau order.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTAPP_MQH
#define SDB_SUITES_TESTAPP_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/TestDb.mqh>
#include <SDBotTests/FakeSink.mqh>
#include <SDBot/App/SdbApp.mqh>

void TaDeleteDb()
  {
   TdbCloseAndDelete(INVALID_HANDLE, SDB_DB_FILE_UNITTEST);
  }

long TaCount(const string table, const string where = "")
  {
   int db = DatabaseOpen(SDB_DB_FILE_UNITTEST, DATABASE_OPEN_READONLY | DATABASE_OPEN_COMMON);
   if(db == INVALID_HANDLE)
      return -1;
   long n = TdbScalarInt(db, "SELECT COUNT(*) FROM " + table + (where == "" ? "" : " WHERE " + where));
   DatabaseClose(db);
   return n;
  }

SdbAppConfig TaConfig()
  {
   SdbAppConfig c = CurrentAppConfig(SDB_APP_UNITTEST, "test");
   c.inputs = DefaultInputValues();
   c.symbolSuffix = (StringLen(_Symbol) > 6) ? StringSubstr(_Symbol, 6) : "";
   c.allowLive = false;
   c.logLevel = SDB_LOG_INFO;
   c.dbTarget = SDB_DB_UNITTEST;
   c.resetEmergencyStop = false;
   return c;
  }

int TaInitDeinit(const SdbAppConfig &c, const int deinitReason)
  {
   CSdbApp *app = new CSdbApp;
   int r = app.OnInit(c);
   app.OnDeinit(deinitReason);
   delete app;
   return r;
  }

void RunTestAppInit()
  {
   SdbAppConfig live = CurrentAppConfig(SDB_APP_LIVE, "test");
   AssertTrue("TC-IR-02", "CurrentAppConfig membawa InpResetEmergencyStop (spec 05 Req 5.5)",
              live.resetEmergencyStop == InpResetEmergencyStop);

   SdbAppConfig c = TaConfig();
   c.inputs.riskPerTradePct = 2.0;
   int r = TaInitDeinit(c, REASON_INITFAILED);
   AssertTrue("TC-APP-01", "risk 2%: INIT_PARAMETERS_INCORRECT dan DB tidak dibuka",
              r == INIT_PARAMETERS_INCORRECT && !FileIsExist(SDB_DB_FILE_UNITTEST, FILE_COMMON));

   c = TaConfig();
   c.inputs.magic = SDB_MAGIC_HARNESS;
   int rLive = TaInitDeinit(c, REASON_INITFAILED);
   c.mode = SDB_APP_HARNESS;
   int rHarness = TaInitDeinit(c, REASON_REMOVE);
   AssertTrue("TC-APP-02", "magic 2026091900: ditolak di mode biasa, diterima di mode HARNESS",
              rLive == INIT_PARAMETERS_INCORRECT && rHarness == INIT_SUCCEEDED);
  }

void RunTestAppBroker(CSdbApp *app)
  {
   CExecutor *ex = app.Executor();
   MqlTick tick;
   SymbolInfoTick(_Symbol, tick);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double vMin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);

   OrderRequest rq;
   rq.isBuy = true;
   rq.volume = vMin;
   rq.sl = tick.ask - 300 * point;
   rq.tp = tick.ask + 300 * point;
   rq.signalId = SDB_NULL_LONG;
   OrderResult res;
   bool ok = ex.OpenMarket(rq, res);
   AssertTrue("TC-APP-08a", "OpenMarket buy lot minimum: terisi, position ID, risiko > 0, ID 4 karakter | " + res.rejectStage + " " + res.detail,
              ok && res.positionId > 0 && MathAbs(res.volumeFilled - vMin) < 1e-8 && res.riskMoney > 0.0 &&
              res.riskMoney != SDB_NULL_DOUBLE && StringLen(res.requestId) == SDB_REQUEST_ID_LEN && ex.SendCount() == 1);

   double sl = 0;
   string id = "";
   bool parsed = ok && PositionSelectByTicket((ulong)res.positionId) &&
                 ParseOrderComment(PositionGetString(POSITION_COMMENT), sl, id);
   AssertTrue("TC-APP-08b", "komentar posisi SDB|SL|ID bisa di-parse, SL dan ID cocok",
              parsed && MathAbs(sl - NormalizeDouble(rq.sl, digits)) < point / 2 && id == res.requestId &&
              PositionGetInteger(POSITION_MAGIC) == TaConfig().inputs.magic);

   app.OnTimer();   // flush
   AssertTrue("TC-APP-08c", "trades tercatat: source EA, sl_initial, harga diminta, risk_pct",
              TaCount("trades", "position_id=" + IntegerToString(res.positionId) + " AND source='EA' AND " +
                      "ABS(sl_initial - " + DoubleToString(NormalizeDouble(rq.sl, digits), digits) + ") < 1e-9 AND " +
                      "price_requested IS NOT NULL AND risk_pct > 0 AND signal_id IS NULL") == 1);

   string why;
   ENUM_SDB_EXEC worse = ex.ModifySl((ulong)res.positionId, rq.sl - 50 * point, why);
   ENUM_SDB_EXEC better = ex.ModifySl((ulong)res.positionId, rq.sl + 100 * point, why);
   bool slMoved = PositionSelectByTicket((ulong)res.positionId) &&
                  MathAbs(PositionGetDouble(POSITION_SL) - NormalizeDouble(rq.sl + 100 * point, digits)) < point / 2;
   ENUM_SDB_EXEC gone = ex.ModifySl(123456789, rq.sl, why);
   AssertTrue("TC-APP-08d", "modify: SL lebih buruk SKIPPED, lebih baik OK dan terpasang, posisi tak dikenal GONE",
              worse == SDB_EXEC_SKIPPED && better == SDB_EXEC_OK && slMoved && gone == SDB_EXEC_GONE);

   ENUM_SDB_EXEC partial = ex.ClosePartial((ulong)res.positionId, vMin, why);
   ENUM_SDB_EXEC closed = ex.ClosePosition((ulong)res.positionId, why);
   ENUM_SDB_EXEC closedAgain = ex.ClosePosition((ulong)res.positionId, why);
   AssertTrue("TC-APP-08e", "tutup sebagian seluruh volume SKIPPED; tutup OK; tutup lagi GONE; posisi sendiri 0",
              partial == SDB_EXEC_SKIPPED && closed == SDB_EXEC_OK && closedAgain == SDB_EXEC_GONE && ex.CountOwnPositions() == 0);

   long sends = ex.SendCount();
   SymbolInfoTick(_Symbol, tick);
   rq.sl = tick.ask - 3 * point;
   rq.tp = tick.ask + 300 * point;
   OrderResult res2;
   bool ok2 = ex.OpenMarket(rq, res2);
   AssertTrue("TC-APP-08f", "SL 3 point: SL_TOO_CLOSE tanpa kiriman ke broker; ID permintaan baru",
              !ok2 && res2.rejectStage == SDB_REJECT_STAGE_SL_TOO_CLOSE && ex.SendCount() == sends &&
              res2.requestId != res.requestId && res2.requestId != "");
  }

void RunTestAppLifecycle()
  {
   CSdbApp *app = new CSdbApp;
   int r = app.OnInit(TaConfig());
   app.OnTimer();
   AssertTrue("TC-APP-03", "konfigurasi valid: INIT_SUCCEEDED, satu sesi aktif, akun tercatat setelah flush",
              r == INIT_SUCCEEDED && TaCount("sessions", "ended_at IS NULL") == 1 && TaCount("accounts") == 1);
   if(r == INIT_SUCCEEDED)
      RunTestAppBroker(app);
   app.OnDeinit(REASON_REMOVE);
   app.OnDeinit(REASON_REMOVE);
   AssertTrue("TC-APP-04", "OnDeinit dua kali: tidak crash, semua sesi berakhir, Logger tertutup",
              TaCount("sessions", "ended_at IS NULL") == 0 && !app.Logger().IsWritable());

   // Ganti timeframe chart: MT5 memanggil OnDeinit lalu OnInit pada objek global yang sama.
   long sessionsBefore = TaCount("sessions");
   r = app.OnInit(TaConfig());
   app.OnTimer();
   bool reopened = app.Logger().IsWritable();
   app.OnDeinit(REASON_CHARTCHANGE);
   AssertTrue("TC-APP-04b", "OnInit ulang pada objek yang sama: sukses, DB terbuka lagi, sesi baru juga diakhiri",
              r == INIT_SUCCEEDED && reopened && TaCount("sessions") == sessionsBefore + 1 &&
              TaCount("sessions", "ended_at IS NULL") == 0);
   delete app;

   CFakeSink fake;
   SdbAppConfig c = TaConfig();
   c.symbolSuffix = "zz";
   app = new CSdbApp;
   r = app.OnInit(c, GetPointer(fake));
   OrderRequest rq;
   rq.isBuy = true;
   rq.volume = 0.01;
   rq.sl = 1.0;
   rq.tp = 2.0;
   rq.signalId = SDB_NULL_LONG;
   OrderResult res;
   bool ok = app.Executor().OpenMarket(rq, res);
   AssertTrue("TC-APP-06", "akun ditolak: OpenMarket NOT_TRADABLE tanpa kiriman",
              !ok && res.rejectStage == SDB_REJECT_STAGE_NOT_TRADABLE && app.Executor().SendCount() == 0);
   app.OnDeinit(REASON_INITFAILED);
   delete app;
   AlertEvent alert;
   bool hasAlert = fake.LastAlert(alert);
   AssertTrue("TC-APP-05", "suffix salah: INIT_FAILED, alert ACCOUNT_REJECTED tersimpan, sesi berakhir INITFAILED",
              r == INIT_FAILED && TaCount("alerts", "type='ACCOUNT_REJECTED'") == 1 &&
              TaCount("sessions", "end_reason='INITFAILED'") >= 1);
   AssertTrue("TC-APP-07", "observer menerima alert tepat sekali, DB juga sekali",
              hasAlert && alert.type == SDB_ALERT_TYPE_ACCOUNT_REJECTED && fake.CountAlert() == 1 &&
              TaCount("alerts") == 1);

   CFakeSink fake2;
   app = new CSdbApp;
   app.OnInit(TaConfig(), GetPointer(fake2));
   app.OnDeinit(REASON_REMOVE);
   delete app;
   // TC-RK-09: snapshot akun membawa puncak dari status bersama, bukan equity (spec 05 Req 3.8).
   string peakGv = SDB_GV_PREFIX_UNITTEST + "_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "_PEAK_EQUITY";
   double peak = AccountInfoDouble(ACCOUNT_EQUITY) + 500.0;
   GlobalVariableSet(peakGv, peak);
   CFakeSink fake3;
   app = new CSdbApp;
   app.OnInit(TaConfig(), GetPointer(fake3));
   AccountSnapshot snap;
   bool haveSnap = fake3.LastAccount(snap);
   app.OnDeinit(REASON_REMOVE);
   delete app;
   GlobalVariablesDeleteAll(SDB_GV_PREFIX_UNITTEST + "_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "_");
   AssertTrue("TC-RK-09", StringFormat("snapshot setelah status siap: peakEquity = GV puncak (%.2f vs %.2f)", haveSnap ? snap.peakEquity : -1.0, peak),
              haveSnap && MathAbs(snap.peakEquity - peak) < 1e-6);

   AssertTrue("TC-APP-07b", "observer menerima snapshot akun, DB juga", fake2.CountAccount() >= 1 && TaCount("accounts") == 1);
  }

void RunTestApp()
  {
   TfBeginSuite("App");
   if(!MQLInfoInteger(MQL_TESTER))
     {
      TfInfo("suite App dilewati: hanya di Strategy Tester (memasang timer dan mengirim order)");
      TfEndSuite();
      return;
     }
   SdbLogCaptureStart();
   TaDeleteDb();
   RunTestAppInit();
   RunTestAppLifecycle();
   TaDeleteDb();
   SdbLogCaptureStop();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTAPP_MQH
