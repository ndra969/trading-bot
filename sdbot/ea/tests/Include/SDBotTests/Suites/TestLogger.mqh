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

SessionInfo TlSession(const string inputsJson)
  {
   SessionInfo s;
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

   TlDeleteFiles();
   SdbLogCaptureStop();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTLOGGER_MQH
