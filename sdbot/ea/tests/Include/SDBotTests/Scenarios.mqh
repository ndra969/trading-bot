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
      // Init mengirim dua snapshot di detik yang sama: dari validasi akun lalu dengan puncak equity
      // setelah status risiko siap (spec 05 design §4.6). Jeda lebih dari 1 jam = pasar tutup.
      if(g > 3600 || (i == 1 && g == 0))
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

// SC-05 (spec 05 Req 1.3): lot hitungan < minimum selalu ditolak LOT_BELOW_MIN, tidak pernah dibulatkan ke atas.
void CheckSc05(const string id, const CScenarioRecorder &rec)
  {
   int n = rec.OpenCount();
   int belowMin = 0;
   string other = "";
   for(int i = 0; i < n; i++)
     {
      OrderResult r;
      rec.OpenAt(i, r);
      if(!r.ok && r.rejectStage == SDB_REJECT_STAGE_LOT_BELOW_MIN)
         belowMin++;
      else if(other == "")
         other = StringFormat("#%d ok=%s stage=%s %s", i, r.ok ? "true" : "false", r.rejectStage, r.detail);
     }
   AssertTrue(id + "-attempts", StringFormat("harness mencoba entry >= 3 kali (%d)", n), n >= 3);
   AssertTrue(id + "-rejected", StringFormat("semua ditolak LOT_BELOW_MIN (%d/%d) %s", belowMin, n, other), n > 0 && belowMin == n);
   AssertTrue(id + "-nosend", StringFormat("tidak ada OrderSend (%I64d)", rec.Sends()), rec.Sends() == 0);
   ScCheckSessions(id, rec, 1);
  }

//--- Skenario risiko spec 05

datetime ScFirstAlert(const CScenarioRecorder &rec, const string type)
  {
   for(int i = 0; i < rec.AlertCount(); i++)
     {
      AlertEvent a;
      rec.AlertAt(i, a);
      if(a.type == type)
         return a.time;
     }
   return 0;
  }

bool ScStoppedGv()
  {
   string key = SDB_GV_PREFIX + "_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "_STOPPED";
   return GlobalVariableCheck(key) && GlobalVariableGet(key) != 0.0;
  }

datetime ScDay(const datetime t) { return t - (datetime)((long)t % 86400); }

// Semua percobaan sejak `from` ditolak dengan `stage` (minimal satu percobaan).
bool ScAllRejectedSince(const CScenarioRecorder &rec, const datetime from, const string stage, int &count)
  {
   count = 0;
   for(int i = 0; i < rec.OpenCount(); i++)
     {
      if(rec.OpenTimeAt(i) < from)
         continue;
      OrderResult r;
      rec.OpenAt(i, r);
      if(r.ok || r.rejectStage != stage)
         return false;
      count++;
     }
   return count > 0;
  }

// SC-02 (Req 4.1–4.4): pause harian, sekali per hari, dicabut di hari server berikutnya.
void CheckSc02(const string id, const CScenarioRecorder &rec)
  {
   datetime lossDays[];
   bool dupDay = false;
   for(int i = 0; i < rec.AlertCount(); i++)
     {
      AlertEvent a;
      rec.AlertAt(i, a);
      if(a.type != SDB_ALERT_TYPE_DAILY_LOSS)
         continue;
      for(int k = 0; k < ArraySize(lossDays); k++)
         if(lossDays[k] == ScDay(a.time))
            dupDay = true;
      int n = ArraySize(lossDays);
      ArrayResize(lossDays, n + 1);
      lossDays[n] = ScDay(a.time);
     }
   int pauses = 0, pausesOnLossDay = 0;
   bool laterOk = false;
   for(int i = 0; i < rec.OpenCount(); i++)
     {
      OrderResult r;
      rec.OpenAt(i, r);
      datetime day = ScDay(rec.OpenTimeAt(i));
      if(r.ok && ArraySize(lossDays) > 0 && day > lossDays[0])
         laterOk = true;
      if(r.rejectStage != SDB_REJECT_STAGE_DAILY_PAUSE)
         continue;
      pauses++;
      for(int k = 0; k < ArraySize(lossDays); k++)
         if(lossDays[k] == day)
           {
            pausesOnLossDay++;
            break;
           }
     }
   AssertTrue(id + "-alert", StringFormat("DAILY_LOSS >= 1 dan maksimal sekali per hari server (%d hari, ganda=%s)",
                                          ArraySize(lossDays), dupDay ? "ya" : "tidak"), ArraySize(lossDays) >= 1 && !dupDay);
   AssertTrue(id + "-pause", StringFormat("setiap tolak DAILY_PAUSE jatuh di hari dengan DAILY_LOSS (%d/%d)", pausesOnLossDay, pauses),
              pauses >= 1 && pausesOnLossDay == pauses);
   AssertTrue(id + "-nextday", "ada entry berhasil di hari server sesudah pause pertama", laterOk);
   AssertTrue(id + "-notstopped", "emergency stop tidak aktif (skenario hanya menguji rugi harian)", !ScStoppedGv());
   ScCheckSessions(id, rec, 1);
  }

// SC-03 (Req 1.5, 3.4, 3.6, 5.1, 5.4): lot x 0.5 setelah DD_REDUCE, lalu STOPPED dan close all.
void CheckSc03(const string id, const CScenarioRecorder &rec)
  {
   datetime tReduce = ScFirstAlert(rec, SDB_ALERT_TYPE_DD_REDUCE);
   datetime tStop = ScFirstAlert(rec, SDB_ALERT_TYPE_DD_STOP);
   AssertTrue(id + "-order", StringFormat("DD_REDUCE (%s) sebelum DD_STOP (%s)", TimeToString(tReduce), TimeToString(tStop)),
              tReduce > 0 && tStop >= tReduce);
   // Risiko yang diharapkan per trade mengikuti alert REDUCE/RECOVERED terakhir sebelum trade dibuka.
   int full = 0, fullBad = 0, half = 0, halfBad = 0, flips = 0;
   for(int i = 0; i < rec.AlertCount(); i++)
     {
      AlertEvent a;
      rec.AlertAt(i, a);
      if(a.type == SDB_ALERT_TYPE_DD_REDUCE || a.type == SDB_ALERT_TYPE_DD_RECOVERED)
         flips++;
     }
   for(int i = 0; i < rec.TradeCount(); i++)
     {
      TradeRecord t;
      rec.TradeAt(i, t);
      if(tStop > 0 && t.openedAt >= tStop)
         continue;
      bool reduced = false;
      for(int k = 0; k < rec.AlertCount(); k++)
        {
         AlertEvent a;
         rec.AlertAt(k, a);
         if(a.time > t.openedAt)
            break;
         if(a.type == SDB_ALERT_TYPE_DD_REDUCE)
            reduced = true;
         else if(a.type == SDB_ALERT_TYPE_DD_RECOVERED)
            reduced = false;
        }
      if(reduced)
        {
         half++;
         if(t.riskPct > 0.5 + 1e-6 || t.riskPct < 0.4)
            halfBad++;
        }
      else
        {
         full++;
         if(t.riskPct > 1.0 + 1e-6 || t.riskPct < 0.8)
            fullBad++;
        }
     }
   AssertTrue(id + "-risk", StringFormat("risk_pct ~1%% tanpa flag (%d, salah %d), ~0.5%% dengan flag lot x 0.5 (%d, salah %d)",
                                         full, fullBad, half, halfBad), full >= 1 && fullBad == 0 && half >= 1 && halfBad == 0);
   // Histeresis (Req 3.5, EC-13): REDUCE hanya di dd >= InpDDReducePct, RECOVERED hanya di dd < ambang pulih.
   double reducePct = CurrentInputs().ddReducePct;
   double recoverPct = DdRecoverPct(reducePct);
   int badFlip = 0;
   for(int i = 0; i < rec.AlertCount(); i++)
     {
      AlertEvent a;
      rec.AlertAt(i, a);
      int p = StringFind(a.message, "drawdown ");
      if(p < 0 || (a.type != SDB_ALERT_TYPE_DD_REDUCE && a.type != SDB_ALERT_TYPE_DD_RECOVERED))
         continue;
      double dd = StringToDouble(StringSubstr(a.message, p + 9, 8));
      if((a.type == SDB_ALERT_TYPE_DD_REDUCE && dd < reducePct - 0.005) ||
         (a.type == SDB_ALERT_TYPE_DD_RECOVERED && dd >= recoverPct + 0.005))
         badFlip++;
     }
   AssertTrue(id + "-hysteresis", StringFormat("REDUCE di dd >= %.2f%%, RECOVERED di dd < %.2f%% (%d transisi, salah %d)",
                                               reducePct, recoverPct, flips, badFlip), badFlip == 0);
   AssertTrue(id + "-stopped", "STOPPED = 1 di akhir run", ScStoppedGv());
   long closeSec = (rec.LastOpenWhileStopped() == 0) ? 0 : (long)(rec.LastOpenWhileStopped() - rec.FirstStoppedAt());
   AssertTrue(id + "-closeall", StringFormat("posisi SDBot habis <= 10 detik simulasi setelah STOPPED (%I64d detik)", closeSec),
              rec.FirstStoppedAt() > 0 && closeSec <= 10);
   int after = 0;
   AssertTrue(id + "-noentry", "semua percobaan sesudah DD_STOP ditolak STOPPED",
              tStop > 0 && ScAllRejectedSince(rec, tStop + 1, SDB_REJECT_STAGE_STOPPED, after));
   ScCheckSessions(id, rec, 1);
  }

// SC-03r (Req 5.4, 5.7): restart saat STOPPED tidak membuka STOPPED.
void CheckSc03r(const string id, const CScenarioRecorder &rec)
  {
   datetime tStop = ScFirstAlert(rec, SDB_ALERT_TYPE_DD_STOP);
   AssertTrue(id + "-restart", StringFormat("restart (%s) sesudah DD_STOP (%s)", TimeToString(rec.RestartAt()), TimeToString(tStop)),
              tStop > 0 && rec.RestartAt() > tStop);
   AssertTrue(id + "-stopped", "STOPPED tetap 1 setelah restart", ScStoppedGv());
   int after = 0;
   bool rejected = ScAllRejectedSince(rec, rec.RestartAt(), SDB_REJECT_STAGE_STOPPED, after);
   AssertTrue(id + "-noentry", StringFormat("semua percobaan sesudah restart ditolak STOPPED (%d)", after), rejected);
   ScCheckSessions(id, rec, 2);
   long first = (rec.SessionCount() > 0) ? rec.SessionAt(0) : 0;
   long sameRun = ScDbCount("SELECT COUNT(*) FROM sessions WHERE run_key=" + IntegerToString(first) +
                            " AND id IN (" + rec.SessionIdList() + ")");
   AssertTrue(id + "-runkey", StringFormat("kedua sesi satu run (%I64d/2)", sameRun), sameRun == 2);
  }

// SC-07 (Req 7.1–7.5, 8.3): penarikan tercatat tepat sekali dan menggeser puncak tanpa mengubah level DD.
void CheckSc07(const string id, const CScenarioRecorder &rec)
  {
   double w = rec.WithdrawAmount();
   AssertTrue(id + "-withdraw", StringFormat("harness menarik saldo (%.2f)", w), w > 0.0);
   BalanceOpRecord b;
   bool have = rec.BalanceOpAt(0, b);
   AssertTrue(id + "-once", StringFormat("tepat 1 operasi saldo (deposit awal tidak dihitung): %d, amount %.2f, jenis %s",
                                         rec.BalanceOpCount(), have ? b.amount : 0.0, have ? b.opType : ""),
              rec.BalanceOpCount() == 1 && have && MathAbs(b.amount + w) < 0.01 && b.opType == SDB_BALANCE_OP_TYPE_BALANCE);
   AssertTrue(id + "-peak", StringFormat("puncak sesudah = sebelum - penarikan (%.2f -> %.2f, selisih %.2f)",
                                         rec.PeakBefore(), rec.PeakAfter(), rec.PeakBefore() - rec.PeakAfter()),
              MathAbs(rec.PeakBefore() - rec.PeakAfter() - w) < 0.01);
   AssertTrue(id + "-level", StringFormat("level DD tidak berubah (%d -> %d)", rec.LevelBefore(), rec.LevelAfter()),
              rec.LevelBefore() >= 0 && rec.LevelBefore() == rec.LevelAfter());
   int alerts = 0;
   for(int i = 0; i < rec.AlertCount(); i++)
     {
      AlertEvent a;
      rec.AlertAt(i, a);
      if(a.type == SDB_ALERT_TYPE_BALANCE_OP)
         alerts++;
     }
   AssertTrue(id + "-alert", StringFormat("alert BALANCE_OP tepat sekali (%d)", alerts), alerts == 1);
   ScCheckSessions(id, rec, 1);
   long first = (rec.SessionCount() > 0) ? rec.SessionAt(0) : 0;
   long rows = ScDbCount("SELECT COUNT(*) FROM balance_ops WHERE run_key = (SELECT run_key FROM sessions WHERE id=" +
                         IntegerToString(first) + ")");
   AssertTrue(id + "-db", StringFormat("1 baris balance_ops untuk run_key run ini (%I64d)", rows), rows == 1);
  }

void CheckScenario(const string id, const CScenarioRecorder &rec)
  {
   TfBeginSuite(id == "" ? "(kosong)" : id);
   if(id == "SC-00")
      CheckSc00(id, rec);
   else if(id == "SC-02")
      CheckSc02(id, rec);
   else if(id == "SC-03")
      CheckSc03(id, rec);
   else if(id == "SC-03r")
      CheckSc03r(id, rec);
   else if(id == "SC-05")
      CheckSc05(id, rec);
   else if(id == "SC-07")
      CheckSc07(id, rec);
   else if(id == "SC-06")
      CheckSc06(id, rec);
   else if(id == "SC-08")
      CheckSc08(id, rec);
   else
      AssertTrue(id, "skenario tidak dikenal harness: '" + id + "'", false);
   TfEndSuite();
  }

#endif // SDB_SDBOTTESTS_SCENARIOS_MQH
