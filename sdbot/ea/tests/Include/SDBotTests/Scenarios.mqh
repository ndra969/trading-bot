//+------------------------------------------------------------------+
//| Scenarios.mqh — pemeriksa harapan skenario harness SC-nn (spec 04
//| design §4.6, §7). Dipanggil di OnDeinit harness setelah CSdbApp
//| menutup DB; menulis satu TfRecord per harapan. ID yang tidak dikenal
//| selalu FAIL (Req 7.7), jadi salah ketik tidak pernah lulus.
//+------------------------------------------------------------------+
#ifndef SDB_SDBOTTESTS_SCENARIOS_MQH
#define SDB_SDBOTTESTS_SCENARIOS_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/TestDb.mqh>
#include <SDBotTests/ScenarioRecorder.mqh>
#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/SchemaEnums.mqh>
#include <SDBot/Execution/ExecutionRules.mqh>

// File tester dipakai semua run: hitung hanya baris sesi yang direkam run ini. -1 = DB tidak terbaca.
long ScDbCount(const string sql)
  {
   int db = DatabaseOpen(SDB_DB_FILE_TESTER, DATABASE_OPEN_READONLY | DATABASE_OPEN_COMMON);
   if(db == INVALID_HANDLE)
      return -1;
   long n = TdbScalarInt(db, sql);
   DatabaseClose(db);
   return n;
  }

// Sesi run ini tercatat di DB tester dengan mode TESTER; prasyarat pemeriksaan DB lain.
void ScCheckSessions(const string id, const CScenarioRecorder &rec, const int expected)
  {
   long n = ScDbCount("SELECT COUNT(*) FROM sessions WHERE mode='TESTER' AND id IN (" + rec.SessionIdList() + ")");
   AssertTrue(id + "-sessions", StringFormat("%d sesi TESTER tercatat (rekam=%d db=%I64d)", expected, rec.SessionCount(), n),
              rec.SessionCount() == expected && n == expected);
  }

// SC-06 (Req 1.4): SL 3 point selalu ditolak SL_TOO_CLOSE, tidak ada kiriman dan tidak ada trade.
void CheckSc06(const string id, const CScenarioRecorder &rec)
  {
   int n = rec.OpenCount();
   int tooClose = 0;
   string other = "";
   for(int i = 0; i < n; i++)
     {
      OrderResult r;
      rec.OpenAt(i, r);
      if(!r.ok && r.rejectStage == SDB_REJECT_STAGE_SL_TOO_CLOSE)
         tooClose++;
      else if(other == "")
         other = StringFormat("#%d ok=%s stage=%s %s", i, r.ok ? "true" : "false", r.rejectStage, r.detail);
     }
   AssertTrue(id + "-attempts", StringFormat("harness mencoba entry >= 3 kali (%d)", n), n >= 3);
   AssertTrue(id + "-rejected", StringFormat("semua percobaan ditolak SL_TOO_CLOSE (%d/%d) %s", tooClose, n, other),
              n > 0 && tooClose == n);
   AssertTrue(id + "-nosend", StringFormat("tidak ada OrderSend (%I64d)", rec.Sends()), rec.Sends() == 0);
   ScCheckSessions(id, rec, 1);
   long trades = ScDbCount("SELECT COUNT(*) FROM trades WHERE session_id IN (" + rec.SessionIdList() + ")");
   AssertTrue(id + "-notrades", StringFormat("0 baris trades untuk sesi ini (db=%I64d, sink=%d)", trades, rec.TradeCount()),
              trades == 0 && rec.TradeCount() == 0);
  }

// Setiap order berhasil punya ID permintaan; tidak boleh ada ID yang sama di seluruh run (Req 5.3).
void ScCheckUniqueRequestIds(const string id, const CScenarioRecorder &rec)
  {
   string seen = "|";
   string dup = "";
   int withId = 0;
   for(int i = 0; i < rec.OpenCount(); i++)
     {
      OrderResult r;
      rec.OpenAt(i, r);
      if(r.requestId == "")
         continue;
      withId++;
      if(StringFind(seen, "|" + r.requestId + "|") >= 0 && dup == "")
         dup = r.requestId;
      seen += r.requestId + "|";
     }
   AssertTrue(id + "-reqid", StringFormat("ID permintaan unik (%d ID, ganda=%s)", withId, dup),
              withId == rec.OpenCount() && dup == "");
  }

// Tiap TradeRecord lengkap (Req 3.1) dan komentar deal masuknya ter-parse dengan SL = sl_initial (Req 5.1).
void ScCheckTradeRecords(const string id, const CScenarioRecorder &rec)
  {
   string bad = "";
   HistorySelect(0, TimeCurrent() + 60);
   for(int i = 0; i < rec.TradeCount() && bad == ""; i++)
     {
      TradeRecord t;
      rec.TradeAt(i, t);
      if(t.slInitial <= 0.0 || t.tpInitial <= 0.0 || t.priceOpen <= 0.0 || t.riskMoney == SDB_NULL_DOUBLE ||
         t.riskMoney <= 0.0 || t.source != SDB_TRADE_SOURCE_EA)
        {
         bad = StringFormat("pos %I64d: sl=%g tp=%g open=%g risk=%g source=%s", t.positionId, t.slInitial,
                            t.tpInitial, t.priceOpen, t.riskMoney, t.source);
         break;
        }
      string comment = "";
      for(int d = HistoryDealsTotal() - 1; d >= 0; d--)
        {
         ulong deal = HistoryDealGetTicket(d);
         if(HistoryDealGetInteger(deal, DEAL_POSITION_ID) == t.positionId && HistoryDealGetInteger(deal, DEAL_ENTRY) == DEAL_ENTRY_IN)
           {
            comment = HistoryDealGetString(deal, DEAL_COMMENT);
            break;
           }
        }
      double sl = 0.0;
      string reqId = "";
      double point = SymbolInfoDouble(t.symbol, SYMBOL_POINT);
      if(!ParseOrderComment(comment, sl, reqId) || MathAbs(sl - t.slInitial) > point / 2)
         bad = StringFormat("pos %I64d: komentar '%s' tidak cocok dengan sl_initial %g", t.positionId, comment, t.slInitial);
     }
   AssertTrue(id + "-records", "TradeRecord lengkap dan komentar SDB|SL|ID cocok dengan sl_initial " + bad,
              rec.TradeCount() > 0 && bad == "");
  }

// Snapshot akun tiap 60 detik simulasi (Req 6.5): tidak lebih sering, dan hampir semua jeda tepat 60 detik.
// Jeda panjang (akhir pekan, tanpa tick) tidak dihitung terlambat bila > 1 jam.
void ScCheckSnapshots(const string id, const CScenarioRecorder &rec)
  {
   int n = rec.SnapshotCount();
   int gaps = 0, onTime = 0, tooSoon = 0;
   for(int i = 1; i < n; i++)
     {
      long g = (long)(rec.SnapshotTime(i) - rec.SnapshotTime(i - 1));
      if(g > 3600)
         continue;
      gaps++;
      if(g < SDB_ACCOUNT_SNAPSHOT_SEC)
        {
         if(tooSoon < 5)
            TfInfo(StringFormat("jeda snapshot %I64d detik: %s -> %s", g, TimeToString(rec.SnapshotTime(i - 1), TIME_SECONDS),
                                TimeToString(rec.SnapshotTime(i), TIME_DATE | TIME_SECONDS)));
         tooSoon++;
        }
      else if(g <= SDB_ACCOUNT_SNAPSHOT_SEC + 2)
         onTime++;
     }
   AssertTrue(id + "-snapshots", StringFormat("snapshot akun tiap 60 detik (n=%d jeda=%d tepat=%d terlalu_cepat=%d)",
                                              n, gaps, onTime, tooSoon),
              n >= 100 && tooSoon == 0 && onTime >= gaps * 95 / 100);
  }

// Alert Medium ke atas selama run (ORDER_FAILED, DB_*, ACCOUNT_*) berarti ada yang salah.
void ScCheckNoErrorAlerts(const string id, const CScenarioRecorder &rec)
  {
   string first = "";
   int n = 0;
   for(int i = 0; i < rec.AlertCount(); i++)
     {
      AlertEvent a;
      rec.AlertAt(i, a);
      if(a.severity < SDB_SEV_MEDIUM)
         continue;
      n++;
      if(first == "")
         first = a.type + ": " + a.message;
     }
   AssertTrue(id + "-noalerts", StringFormat("tidak ada alert Medium ke atas (%d) %s", n, first), n == 0);
  }

// SC-00 smoke (Req 2.1, 3.1, 5.1, 6.1, 6.5).
void CheckSc00(const string id, const CScenarioRecorder &rec)
  {
   int ok = rec.OpenOkCount();
   AssertTrue(id + "-orders", StringFormat("order berhasil >= 3 (%d dari %d percobaan)", ok, rec.OpenCount()), ok >= 3);
   AssertTrue(id + "-sink", StringFormat("satu TradeRecord per order berhasil (%d/%d)", rec.TradeCount(), ok),
              rec.TradeCount() == ok);
   ScCheckTradeRecords(id, rec);
   ScCheckUniqueRequestIds(id, rec);
   ScCheckSessions(id, rec, 1);
   long trades = ScDbCount("SELECT COUNT(*) FROM trades WHERE source='EA' AND session_id IN (" + rec.SessionIdList() + ")");
   AssertTrue(id + "-dbtrades", StringFormat("baris trades sesi ini = order berhasil (db=%I64d, ok=%d)", trades, ok),
              trades == ok);
   ScCheckSnapshots(id, rec);
   ScCheckNoErrorAlerts(id, rec);
  }

// SC-08 restart (Req 5.3, 7.5, EC-14).
void CheckSc08(const string id, const CScenarioRecorder &rec)
  {
   AssertTrue(id + "-orders", StringFormat("order berhasil >= 3 (%d)", rec.OpenOkCount()), rec.OpenOkCount() >= 3);
   ScCheckSessions(id, rec, 2);
   long first = (rec.SessionCount() > 0) ? rec.SessionAt(0) : 0;
   long ended = ScDbCount("SELECT COUNT(*) FROM sessions WHERE id=" + IntegerToString(first) +
                          " AND end_reason='" + SDB_DEINIT_REASON_PROGRAM + "' AND ended_at IS NOT NULL");
   AssertTrue(id + "-firstended", "sesi pertama berakhir PROGRAM", ended == 1);
   long sameRun = ScDbCount("SELECT COUNT(*) FROM sessions WHERE run_key=" + IntegerToString(first) +
                            " AND id IN (" + rec.SessionIdList() + ")");
   AssertTrue(id + "-runkey", StringFormat("kedua sesi satu run: run_key = ID sesi pertama (%I64d/2)", sameRun), sameRun == 2);
   int before = rec.PositionsBeforeRestart();
   int kept = 0;
   for(int i = 0; i < before; i++)
      if(rec.HasPositionAfterRestart(rec.PositionBeforeRestartAt(i)))
         kept++;
   AssertTrue(id + "-positions", StringFormat("posisi sebelum restart masih ada sesudahnya (%d/%d)", kept, before),
              before >= 1 && kept == before);
   ScCheckUniqueRequestIds(id, rec);
   long trades = ScDbCount("SELECT COUNT(*) FROM trades WHERE session_id IN (" + rec.SessionIdList() + ")");
   AssertTrue(id + "-dbtrades", StringFormat("baris trades kedua sesi = order berhasil (db=%I64d, ok=%d)", trades, rec.OpenOkCount()),
              trades == rec.OpenOkCount());
   ScCheckNoErrorAlerts(id, rec);
  }

void CheckScenario(const string id, const CScenarioRecorder &rec)
  {
   TfBeginSuite(id == "" ? "(kosong)" : id);
   if(id == "SC-00")
      CheckSc00(id, rec);
   else if(id == "SC-06")
      CheckSc06(id, rec);
   else if(id == "SC-08")
      CheckSc08(id, rec);
   else
      AssertTrue(id, "skenario tidak dikenal harness: '" + id + "'", false);
   TfEndSuite();
  }

#endif // SDB_SDBOTTESTS_SCENARIOS_MQH
