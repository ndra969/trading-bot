//+------------------------------------------------------------------+
//| TestLogger.mqh — CLogger terhadap sdbot_unittest.sqlite (dihapus
//| sebelum dan sesudah suite, Req 1.4): target NONE, sesi, penulisan
//| idempoten, NULL, UTC, antrean, kunci, DB hilang (spec 03 task 7).
//| Isi DB diperiksa lewat koneksi kedua, seperti backoffice membacanya.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTLOGGER_MQH
#define SDB_SUITES_TESTLOGGER_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/TestDb.mqh>
#include <SDBotTests/FakeSink.mqh>
#include <SDBot/Storage/Logger.mqh>
#include <SDBot/App/TeeSink.mqh>

#define TL_LOGIN    1234567
#define TL_OFFSET   10800                        // server UTC+3
#define TL_SERVER_T D'2026.09.29 13:00:00'       // = 10:00 UTC
#define TL_BIG      1099511627776                // 2^40

void TlDeleteFiles()
  {
   TdbCloseAndDelete(INVALID_HANDLE, SDB_DB_FILE_UNITTEST);
  }

int TlPeek()
  {
   return DatabaseOpen(SDB_DB_FILE_UNITTEST, DATABASE_OPEN_READWRITE | DATABASE_OPEN_COMMON);
  }

long TlCount(const string table, const string where = "")
  {
   int db = TlPeek();
   long n = TdbScalarInt(db, "SELECT COUNT(*) FROM " + table + (where == "" ? "" : " WHERE " + where));
   DatabaseClose(db);
   return n;
  }

string TlText(const string sql)
  {
   int db = TlPeek();
   string v = TdbScalarText(db, sql);
   DatabaseClose(db);
   return v;
  }

long TlInt(const string sql)
  {
   int db = TlPeek();
   long v = TdbScalarInt(db, sql);
   DatabaseClose(db);
   return v;
  }

SessionInfo TlSession(const string inputsJson, const long runKey = SDB_RUN_KEY_LIVE)
  {
   SessionInfo s;
   s.runKey = runKey;
   s.login = TL_LOGIN;
   s.magic = SDB_MAGIC_HARNESS;
   s.symbol = "EURUSDc";
   s.mode = SDB_SESSION_MODE_TESTER;
   s.eaVersion = "1.02";
   s.inputsJson = inputsJson;
   s.startedAt = TL_SERVER_T;
   s.testerFrom = D'2026.01.01';
   s.testerTo = D'2026.06.30';
   s.testerModel = "EVERY_TICK_REAL";
   return s;
  }

TradeRecord TlTrade(const long positionId, const double sl)
  {
   TradeRecord t;
   t.positionId = positionId;
   t.magic = SDB_MAGIC_HARNESS;
   t.symbol = "EURUSDc";
   t.direction = SDB_DIRECTION_BUY;
   t.source = SDB_TRADE_SOURCE_RECONCILED;
   t.volumeInitial = 0.1;
   t.priceRequested = SDB_NULL_DOUBLE;
   t.priceOpen = 1.10000;
   t.slippagePoints = SDB_NULL_LONG;
   t.spreadPoints = SDB_NULL_LONG;
   t.slInitial = sl;
   t.tpInitial = 1.10500;
   t.riskMoney = SDB_NULL_DOUBLE;
   t.riskPct = 0.5;
   t.signalId = SDB_NULL_LONG;
   t.eaVersion = "1.02";
   t.openedAt = TL_SERVER_T;
   return t;
  }

DealRecord TlDeal(const long ticket, const long positionId)
  {
   DealRecord d;
   d.dealTicket = ticket;
   d.positionId = positionId;
   d.magic = SDB_MAGIC_HARNESS;
   d.symbol = "EURUSDc";
   d.time = TL_SERVER_T;
   d.entry = SDB_DEAL_ENTRY_IN;
   d.dealType = SDB_DEAL_TYPE_BUY;
   d.volume = 0.1;
   d.price = 1.1;
   d.reason = SDB_DEAL_REASON_EXPERT;
   d.profit = 0;
   d.commission = -0.7;
   d.swap = 0;
   d.fee = 0;
   return d;
  }

ClosureRecord TlClosure(const long positionId)
  {
   ClosureRecord c;
   c.positionId = positionId;
   c.magic = SDB_MAGIC_HARNESS;
   c.symbol = "EURUSDc";
   c.closedAt = TL_SERVER_T + 3600;
   c.reason = SDB_CLOSE_REASON_BE_STOP;
   c.levelPrice = 1.10002;
   c.priceClose = 1.10001;
   c.slippagePoints = -1;
   c.volumeTotal = 0.1;
   c.profit = 0.1;
   c.commission = -1.4;
   c.swap = 0;
   c.fee = 0;
   c.netProfit = -1.3;
   c.rResult = 0.0;
   c.mfeR = SDB_NULL_DOUBLE;
   c.maeR = SDB_NULL_DOUBLE;
   c.holdingSec = 3600;
   c.beActivated = true;
   c.partialDone = false;
   c.trailActivated = false;
   return c;
  }

PositionEvent TlPosEvent(const long positionId, const double volume)
  {
   PositionEvent e;
   e.positionId = positionId;
   e.time = TL_SERVER_T;
   e.type = SDB_POSITION_EVENT_TRAILING;
   e.slOld = 1.099;
   e.slNew = 1.0995;
   e.volume = volume;
   e.price = 1.101;
   e.spreadPoints = 8;
   e.detail = "";
   return e;
  }

AlertEvent TlAlert(const ENUM_SDB_SEVERITY sev)
  {
   AlertEvent a;
   a.type = SDB_ALERT_TYPE_DD_INFO;
   a.severity = sev;
   a.message = "uji";
   a.symbol = "EURUSDc";
   a.magic = SDB_MAGIC_HARNESS;
   a.time = TL_SERVER_T;
   return a;
  }

AccountSnapshot TlAccount(const double equity)
  {
   AccountSnapshot a;
   a.login = TL_LOGIN;
   a.server = "Exness-MT5Trial";
   a.company = "Exness";
   a.type = SDB_ACC_CENT;
   a.marginMode = ACCOUNT_MARGIN_MODE_RETAIL_HEDGING;
   a.currency = "USC";
   a.leverage = 500;
   a.balance = 10000;
   a.equity = equity;
   a.peakEquity = 10500;
   a.time = TL_SERVER_T;
   return a;
  }

bool TlCapturedAtMostOnce(const string text)
  {
   int n = 0;
   for(int i = 0; i < SdbLogCapturedCount(); i++)
      if(StringFind(SdbLogCaptured(i), text) >= 0)
         n++;
   return n <= 1;
  }

// Satu "run" backtest: sesi dengan run_key tertentu, satu posisi, deal, dan operasi saldo bernomor sama.
long TlRun(const long runKey, const double sl, long &runKeyOut, double &slFound)
  {
   CLogger r;
   r.Init(NULL, "EURUSDc", SDB_MAGIC_HARNESS, "1.03");
   r.SetUtcOffsetForTest(TL_OFFSET);
   r.Open(SDB_DB_UNITTEST);
   long id = r.BeginSession(TlSession("{}", runKey));
   r.OnTradeOpened(TlTrade(600, sl));
   r.OnDeal(TlDeal(601, 600));
   BalanceOpRecord b;
   b.dealTicket = 602;
   b.time = TL_SERVER_T;
   b.opType = SDB_BALANCE_OP_TYPE_BALANCE;
   b.amount = 10000;
   b.comment = "";
   r.OnBalanceOp(b);
   r.Flush();
   runKeyOut = r.RunKey();
   if(!r.FindInitialSl(TL_LOGIN, 600, slFound))
      slFound = 0.0;
   r.EndSession(REASON_REMOVE);
   r.Close();
   return id;
  }

// TC-DB-23..25 (spec 04, PC-08): di tester ID MT5 berulang di setiap run; run_key memisahkannya.
void RunTestLoggerRunKey()
  {
   long key1, key2, key3;
   double sl1, sl2, sl3;
   long id1 = TlRun(SDB_RUN_KEY_NEW, 1.091, key1, sl1);
   long id2 = TlRun(SDB_RUN_KEY_NEW, 1.092, key2, sl2);
   long id3 = TlRun(key1, 1.093, key3, sl3);   // restart harness di tengah run pertama
   AssertTrue("TC-DB-23", "run baru: run_key = ID sesi sendiri; posisi, deal, saldo bernomor sama tersimpan per run",
              id1 > 0 && key1 == id1 && key2 == id2 && key1 != key2 &&
              TlInt("SELECT run_key FROM sessions WHERE id=" + IntegerToString(id2)) == id2 &&
              TlCount("trades", "position_id=600") == 2 && TlCount("deals", "deal_ticket=601") == 2 &&
              TlCount("balance_ops", "deal_ticket=602") == 2);
   AssertTrue("TC-DB-24", "run_key lama dipakai ulang: tetap idempoten, FindInitialSl membaca run sendiri",
              key3 == key1 && TlInt("SELECT run_key FROM sessions WHERE id=" + IntegerToString(id3)) == key1 &&
              TlCount("trades", "position_id=600 AND run_key=" + IntegerToString(key1)) == 1 &&
              MathAbs(sl1 - 1.091) < 1e-9 && MathAbs(sl2 - 1.092) < 1e-9 && MathAbs(sl3 - 1.091) < 1e-9);
   long keyL1, keyL2;
   double slL1, slL2;
   long idL1 = TlRun(SDB_RUN_KEY_LIVE, 1.094, keyL1, slL1);
   long idL2 = TlRun(SDB_RUN_KEY_LIVE, 1.095, keyL2, slL2);   // restart EA live: posisi yang sama
   AssertTrue("TC-DB-25", "live (run_key 0) lintas restart: 1 baris per posisi, SL awal dari sesi pertama",
              keyL1 == 0 && keyL2 == 0 && idL2 > idL1 &&
              TlCount("sessions", "run_key=0 AND id IN (" + IntegerToString(idL1) + "," + IntegerToString(idL2) + ")") == 2 &&
              TlCount("trades", "position_id=600 AND run_key=0") == 1 && MathAbs(slL2 - 1.094) < 1e-9);
  }

AlertEvent TlAlert(const string type, const ENUM_SDB_SEVERITY sev, const string key)
  {
   AlertEvent a;
   a.type = type;
   a.severity = sev;
   a.message = "uji " + type;
   a.symbol = "EURUSDc";
   a.magic = SDB_MAGIC_HARNESS;
   a.time = TL_SERVER_T;
   a.key = key;
   return a;
  }

AlertStatus TlStatus(const string key, const string status, const int attempts, const datetime sentAt, const string reason)
  {
   AlertStatus s;
   s.key = key;
   s.status = status;
   s.attempts = attempts;
   s.sentAt = sentAt;
   s.reason = reason;
   return s;
  }

// Baris PENDING sesi lalu, ditulis langsung seperti sisa EA yang mati (TC-LG-32).
void TlPendingRow(const int db, const string key, const string severity, const long timeUtc, const long magic)
  {
   TdbExec(db, StringFormat("INSERT INTO alerts (session_id, login, magic, symbol, time, type, severity, message, status, attempts, "
                            "notify_key) VALUES (999, %d, %I64d, 'EURUSDc', %I64d, 'DD_STOP', '%s', 'sisa', 'PENDING', 0, '%s')",
                            TL_LOGIN, magic, timeUtc, severity, key));
  }

string TlAlertCol(const string key, const string col)
  {
   return TlText("SELECT COALESCE(" + col + ", '') FROM alerts WHERE notify_key='" + key + "'");
  }

// TC-LG-30..33 (spec 08): notify_key, status kirim, pesan tertunda saat restart, router alert.
void RunTestLoggerNotify()
  {
   TlDeleteFiles();
   CLogger lg;
   lg.Init(NULL, "EURUSDc", SDB_MAGIC_HARNESS, "1.07");
   lg.SetUtcOffsetForTest(TL_OFFSET);
   lg.Open(SDB_DB_UNITTEST);
   lg.BeginSession(TlSession("{}"));
   lg.OnAlert(TlAlert("CONN_DOWN", SDB_SEV_MEDIUM, "k-30"));
   lg.OnAlertStatus(TlStatus("k-30", "SENT", 1, TL_SERVER_T + 5, ""));
   lg.Flush();
   long utc = (long)TL_SERVER_T - TL_OFFSET;
   AssertTrue("TC-LG-30", "alert + status satu flush: SENT, attempts, sent_at UTC, notify_key",
              TlAlertCol("k-30", "status") == "SENT" && TlInt("SELECT attempts FROM alerts WHERE notify_key='k-30'") == 1 &&
              TlInt("SELECT sent_at FROM alerts WHERE notify_key='k-30'") == utc + 5 && TlAlertCol("k-30", "status_reason") == "");

   lg.OnAlert(TlAlert("MARGIN_OK", SDB_SEV_INFO, "k-31"));
   lg.Flush();
   lg.OnAlertStatus(TlStatus("k-31", "SKIPPED", 0, 0, "QUOTA"));
   lg.Flush();
   AssertTrue("TC-LG-31", "status di flush berikutnya: SKIPPED QUOTA, sent_at NULL",
              TlAlertCol("k-31", "status") == "SKIPPED" && TlAlertCol("k-31", "status_reason") == "QUOTA" &&
              TlCount("alerts", "notify_key='k-31' AND sent_at IS NULL") == 1);

   long now = 1790000000;
   int db = TlPeek();
   TlPendingRow(db, "r1", "INFO", now - 2400, SDB_MAGIC_HARNESS);
   TlPendingRow(db, "r2", "INFO", now - 300, SDB_MAGIC_HARNESS);
   TlPendingRow(db, "r3", "CRITICAL", now - 300, SDB_MAGIC_HARNESS);
   TlPendingRow(db, "r4", "CRITICAL", now - 2400, SDB_MAGIC_HARNESS);
   TlPendingRow(db, "r5", "INFO", now - 300, SDB_MAGIC_HARNESS + 1);
   DatabaseClose(db);
   AlertEvent back[];
   int n = lg.TakeRestartAlerts(now, back);
   AssertTrue("TC-LG-32", "restart: tua STALE, Info muda RESTART, Critical muda dikembalikan, instance lain utuh",
              n == 1 && ArraySize(back) == 1 && back[0].key == "r3" && back[0].severity == SDB_SEV_CRITICAL &&
              back[0].time == (datetime)(now - 300 + TL_OFFSET) && TlAlertCol("r1", "status_reason") == "STALE" &&
              TlAlertCol("r2", "status_reason") == "RESTART" && TlAlertCol("r3", "status") == "PENDING" &&
              TlAlertCol("r4", "status_reason") == "STALE" && TlAlertCol("r5", "status") == "PENDING");

   CFakeSink obs;
   CTeeSink tee;
   tee.Add(GetPointer(lg));
   tee.Add(GetPointer(obs));
   tee.SetKeyPrefix("LG");
   lg.SetRouter(GetPointer(tee));
   long before = TlCount("alerts");
   lg.RaiseAlert(SDB_ALERT_TYPE_DB_RECOVERED, SDB_SEV_INFO, "uji router");
   lg.Flush();
   AlertEvent got;
   AssertTrue("TC-LG-33", "router: alert Logger sampai sekali ke router dan satu baris DB dengan key",
              obs.CountAlert() == 1 && obs.LastAlert(got) && got.key == "LG-1" && TlCount("alerts") == before + 1 &&
              TlCount("alerts", "notify_key='LG-1'") == 1);
   lg.EndSession(REASON_PROGRAM);
   lg.Close();
  }

SignalRecord TlSignal(const long id, const string status, const string stage)
  {
   SignalRecord s;
   s.id = id;
   s.magic = SDB_MAGIC_HARNESS;
   s.symbol = "EURUSDc";
   s.time = TL_SERVER_T;
   s.direction = SDB_DIRECTION_BUY;
   s.style = SDB_TRADING_STYLE_DAY;
   s.zoneRef = "H1-1790000000-D";
   s.scoreTotal = 37;
   s.spreadPoints = 12;
   s.status = status;
   s.rejectStage = stage;
   s.rejectDetail = stage == "" ? "" : "pola=NONE";
   s.contextJson = "{\"pa\":\"NONE\"}";
   s.scoreZone = 30;
   s.scoreTrend = 7;
   s.scorePa = 0;
   s.scoreFib = 0;
   s.fibMode = SDB_COMPONENT_OFF;
   s.scoreTrendline = 0;
   s.trendlineMode = SDB_COMPONENT_OFF;
   return s;
  }

// TC-SG-24 (spec 13 Req 3.2, 6.1, EC-01): baris signals dengan id eksplisit + 3 skor, idempoten.
void RunTestLoggerSignal()
  {
   TlDeleteFiles();
   CLogger lg;
   lg.Init(NULL, "EURUSDc", SDB_MAGIC_HARNESS, "1.12");
   lg.SetUtcOffsetForTest(TL_OFFSET);
   lg.Open(SDB_DB_UNITTEST);
   lg.BeginSession(TlSession("{}"));
   lg.OnSignal(TlSignal(4242424242, SDB_SIGNAL_STATUS_REJECTED, SDB_REJECT_STAGE_NO_PA_TRIGGER));
   lg.OnSignal(TlSignal(4242424243, SDB_SIGNAL_STATUS_ACCEPTED, ""));
   lg.Flush();
   lg.OnSignal(TlSignal(4242424242, SDB_SIGNAL_STATUS_REJECTED, SDB_REJECT_STAGE_NO_PA_TRIGGER));
   bool again = lg.Flush();
   // TC-SG-24b (spec 18 Req 3.2, 3.4, 3.5): FIB dicatat dengan active sesuai mode; OFF tidak dicatat.
   SignalRecord sh = TlSignal(4242424244, SDB_SIGNAL_STATUS_REJECTED, SDB_REJECT_STAGE_SCORE_TOO_LOW);
   sh.fibMode = SDB_COMPONENT_SHADOW;
   sh.scoreFib = 11;
   SignalRecord ac = TlSignal(4242424245, SDB_SIGNAL_STATUS_REJECTED, SDB_REJECT_STAGE_SCORE_TOO_LOW);
   ac.fibMode = SDB_COMPONENT_ACTIVE;
   ac.scoreFib = 15;
   sh.trendlineMode = SDB_COMPONENT_SHADOW;
   sh.scoreTrendline = 7;
   ac.trendlineMode = SDB_COMPONENT_ACTIVE;
   ac.scoreTrendline = 15;
   lg.OnSignal(sh);
   lg.OnSignal(ac);
   lg.Flush();
   // TC-SG-24c (spec 19 Req 3.2, 3.4): TRENDLINE dengan active sesuai mode; OFF tanpa baris.
   AssertTrue("TC-SG-24c", "TRENDLINE bayangan active=0 skor 7, aktif active=1 skor 15, OFF tanpa baris",
              TlCount("signal_scores", "signal_id=4242424244 AND component='TRENDLINE' AND score=7 AND max_score=15 AND active=0") == 1 &&
              TlCount("signal_scores", "signal_id=4242424245 AND component='TRENDLINE' AND score=15 AND active=1") == 1 &&
              TlCount("signal_scores", "component='TRENDLINE' AND signal_id=4242424242") == 0);
   AssertTrue("TC-SG-24b", "FIB bayangan active=0 skor 11, aktif active=1 skor 15, mode OFF tanpa baris FIB",
              TlCount("signal_scores", "signal_id=4242424244 AND component='FIB' AND score=11 AND max_score=15 AND active=0") == 1 &&
              TlCount("signal_scores", "signal_id=4242424245 AND component='FIB' AND score=15 AND active=1") == 1 &&
              TlCount("signal_scores", "signal_id=4242424244") == 5 && TlCount("signal_scores", "component='FIB' AND signal_id=4242424242") == 0);
   long utc = (long)TL_SERVER_T - TL_OFFSET;
   AssertTrue("TC-SG-24", "signals id eksplisit + 3 skor aktif (spec 17: active=1); kirim ulang tidak menambah baris; reject_stage kosong = NULL",
              again && TlCount("signals") == 4 && TlCount("signal_scores", "signal_id IN (4242424242, 4242424243)") == 6 &&
              TlCount("signal_scores", "signal_id IN (4242424242, 4242424243) AND active=1") == 6 &&
              TlInt("SELECT time FROM signals WHERE id=4242424242") == utc &&
              TlText("SELECT reject_stage FROM signals WHERE id=4242424242") == SDB_REJECT_STAGE_NO_PA_TRIGGER &&
              TlCount("signals", "id=4242424243 AND reject_stage IS NULL AND reject_detail IS NULL AND status='ACCEPTED'") == 1 &&
              TlCount("signal_scores", "signal_id=4242424242 AND component='ZONE' AND score=30 AND max_score=30") == 1 &&
              TlCount("signal_scores", "signal_id=4242424242 AND component='TREND' AND score=7 AND max_score=15") == 1 &&
              TlCount("signal_scores", "signal_id=4242424242 AND component='PA' AND score=0 AND max_score=10") == 1 &&
              TlInt("SELECT session_id FROM signals WHERE id=4242424243") > 0 &&
              TlText("SELECT zone_ref || '|' || score_total || '|' || spread_points || '|' || context_json FROM signals WHERE id=4242424243") ==
              "H1-1790000000-D|37.0|12|{\"pa\":\"NONE\"}");
   lg.EndSession(REASON_PROGRAM);
   lg.Close();
  }

// TC-LG-34 (spec 09 Req 7.1): akhir sesi sebelumnya untuk pesan start.
void RunTestLoggerPreviousSession()
  {
   TlDeleteFiles();
   datetime endedAt;
   string reason;
   bool abnormal;
   CLogger first;
   first.Init(NULL, "EURUSDc", SDB_MAGIC_HARNESS, "1.08");
   first.SetUtcOffsetForTest(TL_OFFSET);
   first.Open(SDB_DB_UNITTEST);
   first.BeginSession(TlSession("{}"));
   bool none = !first.PreviousSessionEnd(endedAt, reason, abnormal);
   first.EndSession(REASON_REMOVE);
   first.Close();
   CLogger second;
   second.Init(NULL, "EURUSDc", SDB_MAGIC_HARNESS, "1.08");
   second.SetUtcOffsetForTest(TL_OFFSET);
   second.Open(SDB_DB_UNITTEST);
   second.BeginSession(TlSession("{}"));
   bool normal = second.PreviousSessionEnd(endedAt, reason, abnormal) && !abnormal && reason == "REMOVE" && endedAt > 0;
   second.Close();   // tanpa EndSession: seperti EA yang crash
   CLogger third;
   third.Init(NULL, "EURUSDc", SDB_MAGIC_HARNESS, "1.08");
   third.SetUtcOffsetForTest(TL_OFFSET);
   third.Open(SDB_DB_UNITTEST);
   third.BeginSession(TlSession("{}"));
   bool crashed = third.PreviousSessionEnd(endedAt, reason, abnormal) && abnormal;
   third.EndSession(REASON_REMOVE);
   third.Close();
   AssertTrue("TC-LG-34", "sesi lalu: tidak ada / berhenti normal dengan alasan / tidak ditutup normal", none && normal && crashed);
  }

void RunTestLogger()
  {
   TfBeginSuite("Logger");
   SdbLogCaptureStart();
   TlDeleteFiles();
   CFakeSink fake;
   AlertEvent alert;
   double sl;

   // TC-DB-13: target NONE (optimasi) -> tidak ada file, semua method no-op
   CLogger none;
   none.Init(GetPointer(fake), "EURUSDc", SDB_MAGIC_HARNESS, "1.02");
   none.Open(SDB_DB_NONE);
   none.OnTradeOpened(TlTrade(1, 1.099));
   none.Flush();
   AssertTrue("TC-DB-13", "Open(NONE): tidak menulis, tanpa antrean, tanpa sesi, tanpa file",
              !none.IsWritable() && none.QueueSize() == 0 && none.BeginSession(TlSession("{}")) == 0 &&
              !none.FindInitialSl(TL_LOGIN, 1, sl) && !FileIsExist(SDB_DB_FILE_UNITTEST, FILE_COMMON));
   none.Close();
   ENUM_SDB_DB_TARGET expected = MQLInfoInteger(MQL_TESTER) ? SDB_DB_TESTER : SDB_DB_LIVE;   // suite juga bisa jalan sebagai script
   AssertTrue("TC-DB-13b", "target runtime: TESTER di tester (bukan optimasi), LIVE di chart; nama file sesuai target",
              SdbDbTargetForRuntime() == expected && SdbDbFileFor(SDB_DB_LIVE) == SDB_DB_FILE_LIVE &&
              SdbDbFileFor(SDB_DB_TESTER) == SDB_DB_FILE_TESTER && SdbDbFileFor(SDB_DB_NONE) == "");

   // Buka file kosong: migrasi diterapkan (TC-DB-01 lewat Open)
   CLogger lg;
   lg.Init(GetPointer(fake), "EURUSDc", SDB_MAGIC_HARNESS, "1.02");
   lg.SetUtcOffsetForTest(TL_OFFSET);
   bool opened = lg.Open(SDB_DB_UNITTEST);
   AssertTrue("TC-DB-01g", "Open(UNITTEST) pada file kosong: bisa menulis, skema versi terbaru, WAL",
              opened && lg.IsWritable() && TlInt("SELECT MAX(version) FROM schema_migrations") == SDB_SCHEMA_LATEST &&
              TlText("PRAGMA journal_mode") == "wal");

   // TC-DB-14 + Req 8: sesi, hash input tidak bergantung urutan
   string ka[] = {"InpA", "InpB"};
   string va[] = {"1", "\"x\""};
   string kb[] = {"InpB", "InpA"};
   string vb[] = {"\"x\"", "1"};
   long sid = lg.BeginSession(TlSession(CanonicalJson(ka, va)));
   CLogger lg2;
   lg2.Init(NULL, "GBPUSDc", SDB_MAGIC_HARNESS, "1.02");
   lg2.Open(SDB_DB_UNITTEST);
   long sid2 = lg2.BeginSession(TlSession(CanonicalJson(kb, vb)));
   lg2.EndSession(REASON_REMOVE);
   lg2.Close();
   AssertTrue("TC-DB-14", "dua sesi input sama urutan berbeda: input_hash sama = SHA-256 JSON kanonik",
              sid > 0 && sid2 > sid &&
              TlText("SELECT input_hash FROM sessions WHERE id=" + IntegerToString(sid)) ==
              TlText("SELECT input_hash FROM sessions WHERE id=" + IntegerToString(sid2)) &&
              TlText("SELECT input_hash FROM sessions WHERE id=" + IntegerToString(sid)) == Sha256Hex(CanonicalJson(ka, va)));
   AssertTrue("TC-DB-17", "sesi tester: mode, UTC, rentang tester; sesi yang diakhiri punya ended_at dan alasan",
              TlText("SELECT mode FROM sessions WHERE id=" + IntegerToString(sid)) == SDB_SESSION_MODE_TESTER &&
              TlInt("SELECT started_at FROM sessions WHERE id=" + IntegerToString(sid)) == (long)TL_SERVER_T - TL_OFFSET &&
              TlInt("SELECT tester_from FROM sessions WHERE id=" + IntegerToString(sid)) == (long)D'2026.01.01' - TL_OFFSET &&
              TlCount("sessions", "id=" + IntegerToString(sid) + " AND ended_at IS NULL") == 1 &&
              TlText("SELECT end_reason FROM sessions WHERE id=" + IntegerToString(sid2)) == SDB_DEINIT_REASON_REMOVE);

   // Akun: upsert per login
   lg.OnAccount(TlAccount(9900));
   lg.OnAccount(TlAccount(9800));
   // TC-DB-06/07/15: penulisan idempoten, NULL, ticket 64-bit
   lg.OnTradeOpened(TlTrade(TL_BIG, 1.09900));
   lg.OnTradeOpened(TlTrade(TL_BIG, 1.09900));
   lg.OnDeal(TlDeal(TL_BIG + 7, TL_BIG));
   lg.OnDeal(TlDeal(TL_BIG + 7, TL_BIG));
   lg.OnClosure(TlClosure(TL_BIG));
   lg.OnClosure(TlClosure(TL_BIG));
   BalanceOpRecord b;
   b.dealTicket = 555;
   b.time = TL_SERVER_T;
   b.opType = SDB_BALANCE_OP_TYPE_BALANCE;
   b.amount = 1000;
   b.comment = "";
   lg.OnBalanceOp(b);
   lg.OnBalanceOp(b);
   lg.OnAlert(TlAlert(SDB_SEV_CRITICAL));
   bool flushed = lg.Flush();
   AssertTrue("TC-DB-06", "OnTradeOpened dua kali posisi sama: 1 baris trades",
              flushed && lg.QueueSize() == 0 && TlCount("trades") == 1);
   AssertTrue("TC-DB-07", "OnDeal, OnClosure, OnBalanceOp ganda: 1 baris masing-masing",
              TlCount("deals") == 1 && TlCount("closures") == 1 && TlCount("balance_ops") == 1);
   AssertTrue("TC-DB-15", "position_id dan deal_ticket 2^40 terbaca utuh",
              TlInt("SELECT position_id FROM trades") == TL_BIG && TlInt("SELECT deal_ticket FROM deals") == TL_BIG + 7);
   AssertTrue("TC-DB-18", "nilai penanda jadi NULL; nilai biasa tetap",
              TlCount("trades", "price_requested IS NULL AND slippage_points IS NULL AND spread_points IS NULL AND "
                               "risk_money IS NULL AND signal_id IS NULL AND risk_pct = 0.5") == 1 &&
              TlCount("closures", "mfe_r IS NULL AND mae_r IS NULL AND r_result = 0 AND slippage_points = -1 AND be_activated = 1") == 1 &&
              TlCount("balance_ops", "comment IS NULL") == 1);
   AssertTrue("TC-DB-19", "waktu event disimpan UTC; event membawa session_id dan login",
              TlInt("SELECT opened_at FROM trades") == (long)TL_SERVER_T - TL_OFFSET &&
              TlInt("SELECT closed_at FROM closures") == (long)TL_SERVER_T + 3600 - TL_OFFSET &&
              TlCount("deals", "session_id=" + IntegerToString(sid) + " AND login=" + IntegerToString(TL_LOGIN)) == 1);
   AssertTrue("TC-DB-20", "akun di-upsert: 1 baris, equity terbaru, teks enum dan offset",
              TlCount("accounts") == 1 && TlInt("SELECT CAST(equity AS INTEGER) FROM accounts") == 9800 &&
              TlText("SELECT account_type || '/' || margin_mode FROM accounts") == "CENT/HEDGING" &&
              TlInt("SELECT server_utc_offset_sec FROM accounts") == TL_OFFSET);
   AssertTrue("TC-DB-21", "alert tersimpan PENDING, attempts 0, severity teks",
              TlCount("alerts", "status='PENDING' AND attempts=0 AND severity='CRITICAL' AND sent_at IS NULL") == 1);

   // TC-DB-12: FindInitialSl membaca DB langsung
   bool found = lg.FindInitialSl(TL_LOGIN, (ulong)TL_BIG, sl);
   double sl2;
   AssertTrue("TC-DB-12", "FindInitialSl: posisi tercatat -> sl_initial; posisi tak dikenal -> false",
              found && MathAbs(sl - 1.09900) < 1e-9 && !lg.FindInitialSl(TL_LOGIN, 42, sl2));

   // TC-DB-08: 100 event dalam satu flush
   for(int i = 0; i < 100; i++)
      lg.OnPositionEvent(TlPosEvent(TL_BIG, 0.1));
   AssertTrue("TC-DB-08", "100 event lalu satu Flush: semua tertulis, antrean kosong",
              lg.QueueSize() == 100 && lg.Flush() && lg.QueueSize() == 0 && TlCount("position_events") == 100 &&
              TlCount("position_events", "detail IS NULL") == 100);

   // TC-DB-09: koneksi lain memegang kunci tulis -> flush gagal diam-diam, antrean utuh, lalu sukses
   int locker = TlPeek();
   DatabaseExecute(locker, "BEGIN EXCLUSIVE");
   fake.Reset();
   lg.SetNowForTest(1000);
   lg.OnTradeOpened(TlTrade(2, 1.2));
   bool f1 = lg.Flush();
   lg.SetNowForTest(1100);
   bool f2 = lg.Flush();
   AssertTrue("TC-DB-09a", "DB terkunci: Flush gagal, antrean utuh, log paling banyak sekali",
              !f1 && !f2 && lg.QueueSize() == 1 && TlCapturedAtMostOnce("flush tertunda"));
   // Req 2.4: 5 menit tanpa bisa menulis -> alert High sekali, Info saat pulih
   lg.SetNowForTest(1301);
   lg.Flush();
   lg.SetNowForTest(1302);
   lg.Flush();
   bool hasAlert = fake.LastAlert(alert);
   AssertTrue("TC-DB-09b", "terkunci 300 detik: satu alert High DB_UNAVAILABLE",
              fake.CountAlert() == 1 && hasAlert && alert.type == SDB_ALERT_TYPE_DB_UNAVAILABLE && alert.severity == SDB_SEV_HIGH);
   DatabaseExecute(locker, "ROLLBACK");
   DatabaseClose(locker);
   lg.SetNowForTest(1303);
   bool f3 = lg.Flush();
   hasAlert = fake.LastAlert(alert);
   AssertTrue("TC-DB-09c", "kunci dilepas: Flush sukses, trade tersimpan, alert Info DB_RECOVERED",
              f3 && TlCount("trades", "position_id=2") == 1 && fake.CountAlert() == 2 && hasAlert &&
              alert.type == SDB_ALERT_TYPE_DB_RECOVERED && alert.severity == SDB_SEV_INFO);
   lg.Flush();
   AssertIntEq("TC-DB-09d", "kedua alert DB ikut tersimpan di tabel alerts",
               (int)TlCount("alerts", "type IN ('DB_UNAVAILABLE','DB_RECOVERED')"), 2);

   // TC-DB-10: antrean penuh -> buang prioritas terendah tertua; trade dan alert Critical utuh
   lg.SetQueueCapacityForTest(10);
   for(int i = 0; i < 4; i++)
      lg.OnTradeOpened(TlTrade(100 + i, 1.1));
   lg.OnAlert(TlAlert(SDB_SEV_CRITICAL));
   for(int i = 1; i <= 8; i++)
      lg.OnPositionEvent(TlPosEvent(200, i));   // volume = urutan
   lg.OnAlert(TlAlert(SDB_SEV_MEDIUM));
   lg.OnAlert(TlAlert(SDB_SEV_MEDIUM));
   int dropped = lg.DroppedCount();
   int queued = lg.QueueSize();
   lg.Flush();
   AssertTrue("TC-DB-10", "15 event kapasitas 10: 5 event posisi tertua dibuang, trade/Critical/Medium utuh",
              dropped == 5 && queued == 10 && lg.DroppedCount() == 0 &&
              TlCount("trades", "position_id BETWEEN 100 AND 103") == 4 &&
              TlCount("position_events", "position_id=200") == 3 &&
              TlCount("position_events", "position_id=200 AND volume >= 6") == 3 &&
              TlCount("alerts", "type='DD_INFO' AND severity='MEDIUM'") == 2 &&
              TlCount("alerts", "type='DD_INFO' AND severity='CRITICAL'") == 2);
   lg.SetQueueCapacityForTest(SDB_DB_QUEUE_MAX);

   // TC-DB-16: isi file hilang (semua tabel di-drop) -> flush membuka ulang, migrasi, event tersimpan
   int killer = TlPeek();
   TdbExec(killer, "DROP VIEW v_trade_results");
   string tables[] = {"sessions", "accounts", "signals", "signal_scores", "trades", "deals", "position_events",
                      "closures", "balance_ops", "alerts", "schema_migrations"};
   for(int i = 0; i < ArraySize(tables); i++)
      TdbExec(killer, "DROP TABLE " + tables[i]);
   DatabaseClose(killer);
   fake.Reset();
   lg.SetNowForTest(5000);
   lg.OnTradeOpened(TlTrade(300, 1.3));
   bool f16 = lg.Flush();
   hasAlert = fake.LastAlert(alert);
   AssertTrue("TC-DB-16", "skema hilang: Flush membuka ulang + migrasi, trade tersimpan, sesi dibuat ulang, alert DB_RECOVERED",
              f16 && TlCount("trades", "position_id=300") == 1 && TlInt("SELECT MAX(version) FROM schema_migrations") == SDB_SCHEMA_LATEST &&
              TlCount("sessions") == 1 && TlInt("SELECT session_id FROM trades WHERE position_id=300") == TlInt("SELECT id FROM sessions") &&
              hasAlert && alert.type == SDB_ALERT_TYPE_DB_RECOVERED);

   // Req 3.3: Close melakukan flush terakhir
   lg.OnTradeOpened(TlTrade(400, 1.4));
   lg.EndSession(REASON_PROGRAM);
   lg.Close();
   AssertTrue("TC-DB-22", "Close: flush terakhir dan sesi diakhiri; setelah Close tidak menulis",
              TlCount("trades", "position_id=400") == 1 && TlCount("sessions", "ended_at IS NOT NULL AND end_reason='PROGRAM'") == 1 &&
              !lg.IsWritable());

   RunTestLoggerRunKey();

   // TC-DB-02 / TC-DB-03 lewat Open: buka ulang tanpa migrasi ganda; DB lebih baru -> tidak menulis
   CLogger again;
   again.Init(GetPointer(fake), "EURUSDc", SDB_MAGIC_HARNESS, "1.02");
   AssertTrue("TC-DB-02b", "Open kedua pada DB yang sama: satu baris per versi",
              again.Open(SDB_DB_UNITTEST) && TlCount("schema_migrations") == SDB_SCHEMA_LATEST);
   again.Close();
   int future = TlPeek();
   TdbExec(future, "INSERT INTO schema_migrations VALUES (999, 'future', 'x', 0, 'future EA')");
   DatabaseClose(future);
   fake.Reset();
   CLogger old;
   old.Init(GetPointer(fake), "EURUSDc", SDB_MAGIC_HARNESS, "1.02");
   old.Open(SDB_DB_UNITTEST);
   old.OnTradeOpened(TlTrade(500, 1.5));
   old.Flush();
   hasAlert = fake.LastAlert(alert);
   AssertTrue("TC-DB-03c", "DB versi 999: tidak bisa menulis, antrean kosong, alert DB_NEWER_SCHEMA",
              !old.IsWritable() && old.QueueSize() == 0 && TlCount("trades", "position_id=500") == 0 &&
              hasAlert && alert.type == SDB_ALERT_TYPE_DB_NEWER_SCHEMA);
   old.Close();

   RunTestLoggerNotify();
   RunTestLoggerPreviousSession();
   RunTestLoggerSignal();
   TlDeleteFiles();
   SdbLogCaptureStop();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTLOGGER_MQH
