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
#include <SDBotTests/FakeTransport.mqh>
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

//--- Skenario posisi spec 06

bool ScTradeIsBuy(const CScenarioRecorder &rec, const long positionId, bool &isBuy)
  {
   for(int i = 0; i < rec.TradeCount(); i++)
     {
      TradeRecord t;
      rec.TradeAt(i, t);
      if(t.positionId == positionId)
        {
         isBuy = (t.direction == SDB_DIRECTION_BUY);
         return true;
        }
     }
   return false;
  }

int ScEventCount(const CScenarioRecorder &rec, const long positionId, const string type)
  {
   int n = 0;
   for(int i = 0; i < rec.EventCount(); i++)
     {
      PositionEvent e;
      rec.EventAt(i, e);
      if(e.positionId == positionId && e.type == type)
         n++;
     }
   return n;
  }

// Posisi mengalami BE, PARTIAL, dan TRAILING; TRAILING tidak pernah mendahului BE (PRD: trailing setelah BE).
// PARTIAL boleh sebelum BE (harga melompat 1R dan 1.5R dalam satu tick, EC-02) atau sesudah trailing.
bool ScHasBePartialTrail(const CScenarioRecorder &rec, const long positionId)
  {
   int be = -1, partial = -1, trail = -1;
   for(int i = 0; i < rec.EventCount(); i++)
     {
      PositionEvent e;
      rec.EventAt(i, e);
      if(e.positionId != positionId)
         continue;
      if(e.type == SDB_POSITION_EVENT_BE && be < 0)
         be = i;
      else if(e.type == SDB_POSITION_EVENT_PARTIAL && partial < 0)
         partial = i;
      else if(e.type == SDB_POSITION_EVENT_TRAILING && trail < 0)
         trail = i;
     }
   return be >= 0 && partial >= 0 && trail > be;
  }

// SL di event BE/TRAILING tidak pernah memburuk (Req 5.2).
bool ScSlNeverWorse(const CScenarioRecorder &rec, const long positionId, const bool isBuy)
  {
   double last = 0.0;
   for(int i = 0; i < rec.EventCount(); i++)
     {
      PositionEvent e;
      rec.EventAt(i, e);
      if(e.positionId != positionId || (e.type != SDB_POSITION_EVENT_BE && e.type != SDB_POSITION_EVENT_TRAILING))
         continue;
      if(last > 0.0 && (isBuy ? e.slNew < last : e.slNew > last))
         return false;
      last = e.slNew;
     }
   return true;
  }

int ScClosureCount(const CScenarioRecorder &rec, const long positionId, ClosureRecord &last)
  {
   int n = 0;
   for(int i = 0; i < rec.ClosureCount(); i++)
     {
      ClosureRecord c;
      rec.ClosureAt(i, c);
      if(c.positionId == positionId)
        {
         n++;
         last = c;
        }
     }
   return n;
  }

// Tester menutup posisi yang tersisa di akhir run setelah tick terakhir (alasan CLIENT) tanpa OnTradeTransaction;
// penutupan itu bukan perilaku EA dan tidak punya closure.
bool ScClosedByTesterEnd(const long positionId)
  {
   if(!HistorySelectByPosition((ulong)positionId))
      return false;
   for(int i = 0; i < HistoryDealsTotal(); i++)
     {
      ulong d = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(d, DEAL_ENTRY) != DEAL_ENTRY_IN && (datetime)HistoryDealGetInteger(d, DEAL_TIME) > TimeCurrent())
         return true;
     }
   return false;
  }

// Deal trading di history tester untuk posisi yang dibuka harness.
int ScHistoryDealsOfTrades(const CScenarioRecorder &rec)
  {
   if(!HistorySelect(0, TimeCurrent() + 60))
      return -1;
   int n = 0;
   for(int i = 0; i < HistoryDealsTotal(); i++)
     {
      ulong d = HistoryDealGetTicket(i);
      long type = HistoryDealGetInteger(d, DEAL_TYPE);
      bool isBuy;
      if((type == DEAL_TYPE_BUY || type == DEAL_TYPE_SELL) && ScTradeIsBuy(rec, HistoryDealGetInteger(d, DEAL_POSITION_ID), isBuy))
         n++;
     }
   return n;
  }

// SC-01 (Req 2–6): BE -> PARTIAL -> TRAILING, sekali per posisi, SL tidak memburuk, closure lengkap.
void CheckSc01(const string id, const CScenarioRecorder &rec)
  {
   int ordered = 0, dupBe = 0, dupPartial = 0, worse = 0, closed = 0, badClosure = 0, beOrTrail = 0;
   string firstBad = "";
   for(int i = 0; i < rec.TradeCount(); i++)
     {
      TradeRecord t;
      rec.TradeAt(i, t);
      bool isBuy = (t.direction == SDB_DIRECTION_BUY);
      if(ScHasBePartialTrail(rec, t.positionId))
         ordered++;
      if(ScEventCount(rec, t.positionId, SDB_POSITION_EVENT_BE) > 1)
         dupBe++;
      if(ScEventCount(rec, t.positionId, SDB_POSITION_EVENT_PARTIAL) > 1)
         dupPartial++;
      if(!ScSlNeverWorse(rec, t.positionId, isBuy))
         worse++;
      if(PositionSelectByTicket((ulong)t.positionId) || ScClosedByTesterEnd(t.positionId))
         continue;
      closed++;
      ClosureRecord c;
      int nc = ScClosureCount(rec, t.positionId, c);
      bool ok = nc == 1 && c.reason != "" && c.rResult != SDB_NULL_DOUBLE &&
                (c.mfeR == SDB_NULL_DOUBLE || c.mfeR + 0.05 >= c.rResult);
      if(!ok)
        {
         badClosure++;
         if(firstBad == "")
            firstBad = StringFormat("pos %I64d closure=%d alasan=%s R=%.2f MFE=%.2f", t.positionId, nc, c.reason, c.rResult, c.mfeR);
        }
      if(nc == 1 && (c.reason == SDB_CLOSE_REASON_BE_STOP || c.reason == SDB_CLOSE_REASON_TRAIL_STOP))
         beOrTrail++;
     }
   AssertTrue(id + "-sequence", StringFormat("posisi dengan BE, PARTIAL, dan TRAILING (trailing sesudah BE): %d dari %d", ordered, rec.TradeCount()),
              ordered >= 1);
   AssertTrue(id + "-once", StringFormat("BE dan PARTIAL maksimal sekali per posisi (ganda BE %d, PARTIAL %d)", dupBe, dupPartial),
              dupBe == 0 && dupPartial == 0);
   AssertTrue(id + "-neverworse", StringFormat("SL di event BE/TRAILING tidak pernah memburuk (%d posisi melanggar)", worse), worse == 0);
   AssertTrue(id + "-closures", StringFormat("tiap posisi tutup punya tepat satu closure lengkap, MFE >= R hasil (%d tutup, salah %d) %s",
                                             closed, badClosure, firstBad), closed >= 3 && badClosure == 0);
   AssertTrue(id + "-leak", StringFormat("ada closure BE_STOP atau TRAIL_STOP (%d)", beOrTrail), beOrTrail >= 1);
   int hist = ScHistoryDealsOfTrades(rec);
   AssertTrue(id + "-deals", StringFormat("deal tercatat = deal posisi harness di history (%d vs %d)", rec.DealCount(), hist),
              hist > 0 && rec.DealCount() == hist);
   ScCheckSessions(id, rec, 1);
  }

// SC-01b (Req 3.2, EC-04): lot 0.01 -> PARTIAL_SKIPPED sekali per posisi, tidak pernah PARTIAL, BE tetap jalan.
void CheckSc01b(const string id, const CScenarioRecorder &rec)
  {
   int skippedPos = 0, dupSkip = 0, partials = 0, bes = 0;
   for(int i = 0; i < rec.TradeCount(); i++)
     {
      TradeRecord t;
      rec.TradeAt(i, t);
      int s = ScEventCount(rec, t.positionId, SDB_POSITION_EVENT_PARTIAL_SKIPPED);
      if(s >= 1)
         skippedPos++;
      if(s > 1)
         dupSkip++;
      partials += ScEventCount(rec, t.positionId, SDB_POSITION_EVENT_PARTIAL);
      bes += ScEventCount(rec, t.positionId, SDB_POSITION_EVENT_BE);
     }
   AssertTrue(id + "-skipped", StringFormat("PARTIAL_SKIPPED tepat sekali per posisi yang mencapai 1.5R (%d posisi, ganda %d)",
                                            skippedPos, dupSkip), skippedPos >= 1 && dupSkip == 0);
   AssertTrue(id + "-nopartial", StringFormat("tidak ada PARTIAL (%d)", partials), partials == 0);
   AssertTrue(id + "-be", StringFormat("BE tetap terjadi (%d)", bes), bes >= 1);
   ScCheckSessions(id, rec, 1);
  }

int ScEventCountSince(const CScenarioRecorder &rec, const long positionId, const string type, const datetime from)
  {
   int n = 0;
   for(int i = 0; i < rec.EventCount(); i++)
     {
      PositionEvent e;
      rec.EventAt(i, e);
      if(e.positionId == positionId && e.type == type && e.time >= from)
         n++;
     }
   return n;
  }

long ScFirstRunKeySql(const CScenarioRecorder &rec)
  {
   return (rec.SessionCount() > 0) ? rec.SessionAt(0) : 0;
  }

// SC-04 (Req 7.1, 7.3, EC-19): restart saat posisi sudah BE + PARTIAL.
void CheckSc04(const string id, const CScenarioRecorder &rec)
  {
   long p = rec.RestartPosition();
   datetime r = rec.RestartAt();
   AssertTrue(id + "-restart", StringFormat("restart (%s) saat pos %I64d sudah PARTIAL dan masih terbuka", TimeToString(r), p),
              p > 0 && r > 0 && rec.WasOpenBeforeRestart(p) && ScEventCount(rec, p, SDB_POSITION_EVENT_PARTIAL) >= 1);
   int be = ScEventCountSince(rec, p, SDB_POSITION_EVENT_BE, r);
   int partial = ScEventCountSince(rec, p, SDB_POSITION_EVENT_PARTIAL, r);
   AssertTrue(id + "-nodouble", StringFormat("sesudah restart tidak ada BE (%d) atau PARTIAL (%d) kedua untuk pos %I64d", be, partial, p),
              be == 0 && partial == 0);
   int reconciled = 0;
   for(int i = 0; i < rec.TradeCount(); i++)
     {
      TradeRecord t;
      rec.TradeAt(i, t);
      if(t.positionId == p && t.source == SDB_TRADE_SOURCE_RECONCILED)
         reconciled++;
     }
   long rows = ScDbCount("SELECT COUNT(*) FROM trades WHERE position_id=" + IntegerToString(p) +
                         " AND run_key=(SELECT run_key FROM sessions WHERE id=" + IntegerToString(ScFirstRunKeySql(rec)) + ")");
   AssertTrue(id + "-reconciled", StringFormat("TradeRecord RECONCILED dikirim (%d), baris trades tetap 1 (%I64d)", reconciled, rows),
              reconciled == 1 && rows == 1);
   ClosureRecord c;
   int closures = ScClosureCount(rec, p, c);
   bool managed = ScEventCountSince(rec, p, SDB_POSITION_EVENT_TRAILING, r) > 0 || closures == 1;
   AssertTrue(id + "-managed", StringFormat("pos %I64d tetap dikelola sesudah restart (trailing atau closure; closure %d, alasan %s)",
                                            p, closures, closures > 0 ? c.reason : "-"),
              managed && (closures == 1 || PositionSelectByTicket((ulong)p) || ScClosedByTesterEnd(p)));
   ScCheckSessions(id, rec, 2);
  }

// SC-04b (Req 7.2, EC-09, EC-16): posisi yang ditutup broker saat EA "mati" tercatat tepat sekali saat init ulang.
void CheckSc04b(const string id, const CScenarioRecorder &rec)
  {
   datetime from = rec.RestartAt(), to = rec.ReattachAt();
   AssertTrue(id + "-detach", StringFormat("app dilepas %s - %s", TimeToString(from), TimeToString(to)), from > 0 && to > from);
   int closedWhileAway = 0, bad = 0;
   string firstBad = "";
   for(int i = 0; i < rec.TradeCount(); i++)
     {
      TradeRecord t;
      rec.TradeAt(i, t);
      if(t.source != SDB_TRADE_SOURCE_EA || !HistorySelectByPosition((ulong)t.positionId))
         continue;
      datetime closeTime = 0;
      for(int k = 0; k < HistoryDealsTotal(); k++)
        {
         ulong d = HistoryDealGetTicket(k);
         if(HistoryDealGetInteger(d, DEAL_ENTRY) == DEAL_ENTRY_OUT)
            closeTime = (datetime)HistoryDealGetInteger(d, DEAL_TIME);
        }
      if(closeTime < from || closeTime > to)
         continue;
      closedWhileAway++;
      ClosureRecord c;
      int nc = ScClosureCount(rec, t.positionId, c);
      int deals = 0;
      for(int k = 0; k < rec.DealCount(); k++)
        {
         DealRecord d;
         rec.DealAt(k, d);
         if(d.positionId == t.positionId)
            deals++;
        }
      long rows = ScDbCount("SELECT COUNT(*) FROM closures WHERE position_id=" + IntegerToString(t.positionId) +
                            " AND run_key=(SELECT run_key FROM sessions WHERE id=" + IntegerToString(ScFirstRunKeySql(rec)) + ")");
      if(nc != 1 || deals != 2 || rows != 1)
        {
         bad++;
         if(firstBad == "")
            firstBad = StringFormat("pos %I64d closure=%d deal=%d db=%I64d", t.positionId, nc, deals, rows);
        }
     }
   AssertTrue(id + "-closed", StringFormat("ada posisi yang ditutup broker saat app dilepas (%d)", closedWhileAway), closedWhileAway >= 1);
   AssertTrue(id + "-once", StringFormat("tiap posisi itu: 1 closure, 2 deal, 1 baris closures (salah %d) %s", bad, firstBad), bad == 0);
   ScCheckSessions(id, rec, 2);
  }

// Baris alerts run ini (sesi yang direkam) dengan syarat tambahan.
long ScAlertCount(const CScenarioRecorder &rec, const string where)
  {
   return ScDbCount("SELECT COUNT(*) FROM alerts WHERE session_id IN (" + rec.SessionIdList() + ")" + (where == "" ? "" : " AND " + where));
  }

// Pesan event trade terkirim memuat posisi dan arah dari rekaman (Req 1.2, 1.3).
int ScBadTradeMessages(const CScenarioRecorder &rec, const CFakeTransport &tr, int &checked)
  {
   int bad = 0;
   checked = 0;
   for(int i = 0; i < tr.Count(); i++)
     {
      SdbOutMessage m;
      tr.At(i, m);
      if(tr.CodeAt(i) != SDB_SEND_OK || (m.type != SDB_ALERT_TYPE_TRADE_OPENED && m.type != SDB_ALERT_TYPE_TRADE_CLOSED))
         continue;
      checked++;
      bool found = false;
      for(int k = 0; k < rec.TradeCount() && !found; k++)
        {
         TradeRecord t;
         rec.TradeAt(k, t);
         found = StringFind(m.text, "<code>" + IntegerToString(t.positionId) + "</code>") > 0 &&
                 StringFind(m.text, " " + t.direction + " <code>") > 0 && StringFind(m.text, " TESTER ") > 0;
        }
      if(!found || (m.type == SDB_ALERT_TYPE_TRADE_CLOSED && StringFind(m.text, " R <code>") < 0))
         bad++;
     }
   return bad;
  }

// SC-10 (spec 08 Req 1–3, 5, 7.4, 7.5): notifier dari event nyata di tester dengan transport palsu.
void CheckSc10(const string id, const CScenarioRecorder &rec, const CFakeTransport &tr)
  {
   int closures = rec.ClosureCount();
   long rowsOpen = ScAlertCount(rec, "type='TRADE_OPENED'");
   long rowsClose = ScAlertCount(rec, "type='TRADE_CLOSED'");
   int checked = 0;
   int badMsg = ScBadTradeMessages(rec, tr, checked);
   AssertTrue(id + "-trade", StringFormat("1 baris per trade (%d/%I64d) dan per closure (%d/%I64d); pesan terkirim memuat posisi dan arah (%d dicek, salah %d)",
                                          rec.TradeCount(), rowsOpen, closures, rowsClose, checked, badMsg),
              rec.TradeCount() >= 2 && rowsOpen == rec.TradeCount() && rowsClose == closures && closures >= 2 && checked >= 2 && badMsg == 0);

   int stopIdx = tr.FirstIndexOf(SDB_ALERT_TYPE_DD_STOP);
   datetime tStop = ScFirstAlert(rec, SDB_ALERT_TYPE_DD_STOP);
   int jumped = 0;
   for(int i = 0; i < stopIdx; i++)
     {
      SdbOutMessage m;
      tr.At(i, m);
      if(tr.TimeAt(i) >= tStop && m.severity != SDB_SEV_CRITICAL)
         jumped++;
     }
   AssertTrue(id + "-critical", StringFormat("DD_STOP terkirim <= 1 detik setelah dibuat (%s -> %s), tidak didahului non-Critical (%d)",
                                             TimeToString(tStop, TIME_SECONDS), TimeToString(tr.TimeAt(stopIdx), TIME_SECONDS), jumped),
              stopIdx >= 0 && tStop > 0 && tr.TimeAt(stopIdx) - tStop <= 1 && jumped == 0);

   AssertTrue(id + "-cooldown", StringFormat("ORDER_FAILED pertama SENT, kedua SKIPPED COOLDOWN (%I64d)", ScAlertCount(rec, "type='ORDER_FAILED' AND status_reason='COOLDOWN'")),
              ScAlertCount(rec, "type='ORDER_FAILED' AND message LIKE 'uji burst%'") == 2 &&
              ScAlertCount(rec, "type='ORDER_FAILED' AND message LIKE 'uji burst%' AND status='SKIPPED' AND status_reason='COOLDOWN'") == 1 &&
              ScAlertCount(rec, "type='ORDER_FAILED' AND message LIKE 'uji burst%' AND status='SENT'") == 1);

   int worstHour = 0;
   for(int i = 0; i < tr.Count(); i++)
     {
      SdbOutMessage m;
      tr.At(i, m);
      if(m.severity == SDB_SEV_CRITICAL || tr.CodeAt(i) != SDB_SEND_OK)
         continue;
      int inHour = 0;
      for(int k = 0; k < tr.Count(); k++)
        {
         SdbOutMessage o;
         tr.At(k, o);
         if(o.severity != SDB_SEV_CRITICAL && tr.CodeAt(k) == SDB_SEND_OK && (long)tr.TimeAt(k) / 3600 == (long)tr.TimeAt(i) / 3600)
            inHour++;
        }
      worstHour = MathMax(worstHour, inHour);
     }
   long quota = ScAlertCount(rec, "status_reason='QUOTA'");
   AssertTrue(id + "-quota", StringFormat("non-Critical terkirim per jam server maks %d (terbanyak %d), SKIPPED QUOTA %I64d", SDB_NT_QUOTA_PER_HOUR, worstHour, quota),
              worstHour <= SDB_NT_QUOTA_PER_HOUR && quota >= 1);

   AssertTrue(id + "-retry", StringFormat("TEST_FAIL: 3 percobaan lalu FAILED TRANSPORT_TEMP (kirim %d)", tr.CountType("TEST_FAIL")),
              tr.CountType("TEST_FAIL") == SDB_NT_MAX_ATTEMPTS &&
              ScAlertCount(rec, "type='TEST_FAIL' AND status='FAILED' AND attempts=3 AND status_reason='TRANSPORT_TEMP'") == 1);

   long sent = ScAlertCount(rec, "status='SENT'");
   long pending = ScAlertCount(rec, "status='PENDING'");
   AssertTrue(id + "-status", StringFormat("baris SENT = kiriman OK (%I64d/%d); PENDING = sisa antrean saat berhenti (%I64d/%d); semua baris punya notify_key",
                                           sent, tr.CountCode(SDB_SEND_OK), pending, rec.NotifyQueueAtStop()),
              sent == tr.CountCode(SDB_SEND_OK) && pending == rec.NotifyQueueAtStop() && ScAlertCount(rec, "notify_key IS NULL") == 0);

   AssertTrue(id + "-timer-only", StringFormat("tidak ada kiriman dari OnTick/OnTradeTransaction (%d)", tr.Violations()), tr.Violations() == 0);

   int worstCycle = 0;
   for(int i = 0; i < tr.Count(); i++)
     {
      if(tr.PhaseAt(i) != "TIMER")
         continue;
      int same = 0;
      for(int k = 0; k < tr.Count(); k++)
         if(tr.PhaseAt(k) == "TIMER" && tr.CycleAt(k) == tr.CycleAt(i))
            same++;
      worstCycle = MathMax(worstCycle, same);
     }
   AssertTrue(id + "-per-cycle", StringFormat("kiriman per siklus timer maks %d (terbanyak %d)", SDB_NT_MAX_PER_TIMER, worstCycle),
              worstCycle >= 1 && worstCycle <= SDB_NT_MAX_PER_TIMER);
   ScCheckSessions(id, rec, 1);
  }

// Kolom angka semua baris hasil query DB tester (urut sesuai query). -1 = DB tidak terbaca.
int ScDbLongs(const string sql, long &out[])
  {
   ArrayFree(out);
   int db = DatabaseOpen(SDB_DB_FILE_TESTER, DATABASE_OPEN_READONLY | DATABASE_OPEN_COMMON);
   if(db == INVALID_HANDLE)
      return -1;
   int st = DatabasePrepare(db, sql);
   if(st != INVALID_HANDLE)
     {
      long v;
      while(DatabaseRead(st))
        {
         DatabaseColumnLong(st, 0, v);
         int n = ArraySize(out);
         ArrayResize(out, n + 1);
         out[n] = v;
        }
      DatabaseFinalize(st);
     }
   DatabaseClose(db);
   return ArraySize(out);
  }

string ScDayText(const datetime t)
  {
   string d = TimeToString(t, TIME_DATE);
   StringReplace(d, ".", "-");
   return d;
  }

// Jumlah closure rekaman pada hari server itu (yyyy-mm-dd).
int ScClosuresOn(const CScenarioRecorder &rec, const string day)
  {
   int n = 0;
   for(int i = 0; i < rec.ClosureCount(); i++)
     {
      ClosureRecord c;
      rec.ClosureAt(i, c);
      if(ScDayText(c.closedAt) == day)
         n++;
     }
   return n;
  }

// Laporan harian per hari: cocok dengan closure rekaman, sekali per hari, hanya hari beraktivitas, bukan hari terakhir run.
void ScCheckReports(const string id, const CScenarioRecorder &rec, const CFakeTransport &tr, string &lastDay)
  {
   int bad = 0, reports = 0;
   string firstBad = "", seen = ",";
   lastDay = ScDayText(TimeCurrent());
   for(int i = 0; i < tr.Count(); i++)
     {
      SdbOutMessage m;
      tr.At(i, m);
      if(m.type != SDB_ALERT_TYPE_DAILY_REPORT)
         continue;
      reports++;
      int p = StringFind(m.text, "Laporan harian ");
      string day = (p >= 0) ? StringSubstr(m.text, p + 15, 10) : "?";
      int closed = ScClosuresOn(rec, day);
      bool ok = StringFind(seen, "," + day + ",") < 0 && closed > 0 &&
                StringFind(m.text, "Posisi tutup <code>" + IntegerToString(closed) + "</code>") > 0;
      seen += day + ",";
      if(!ok && bad++ == 0)
         firstBad = StringFormat("%s closure=%d", day, closed);
     }
   int missing = 0;
   for(int i = 0; i < rec.ClosureCount(); i++)
     {
      ClosureRecord c;
      rec.ClosureAt(i, c);
      string day = ScDayText(c.closedAt);
      if(day != lastDay && StringFind(seen, "," + day + ",") < 0 && missing++ == 0 && firstBad == "")
         firstBad = "tanpa laporan " + day;
     }
   AssertTrue(id + "-report", StringFormat("1 laporan per hari dengan closure, jumlah posisi cocok (%d laporan, salah %d, hilang %d) %s",
                                           reports, bad, missing, firstBad), reports >= 3 && bad == 0 && missing == 0);
   AssertTrue(id + "-weekend", "tidak ada laporan 2026-09-19 dan 2026-09-20 (tanpa aktivitas)",
              StringFind(seen, ",2026-09-19,") < 0 && StringFind(seen, ",2026-09-20,") < 0);
   AssertTrue(id + "-friday", StringFormat("laporan Jumat 2026-09-18 terkirim walau tick baru ada Senin (closure Jumat %d)", ScClosuresOn(rec, "2026-09-18")),
              ScClosuresOn(rec, "2026-09-18") > 0 && StringFind(seen, ",2026-09-18,") >= 0);
  }

// SC-11 (spec 09 Req 4–7, 8.1): heartbeat, laporan harian, start/stop, pemimpin setelah restart.
void CheckSc11(const string id, const CScenarioRecorder &rec, const CFakeTransport &tr)
  {
   long times[];
   int hb = ScDbLongs("SELECT time FROM alerts WHERE type='HEARTBEAT' AND session_id IN (" + rec.SessionIdList() + ") ORDER BY time", times);
   long minGap = LONG_MAX;
   for(int i = 1; i < hb; i++)
      minGap = MathMin(minGap, times[i] - times[i - 1]);
   int loud = 0;
   for(int i = 0; i < tr.Count(); i++)
     {
      SdbOutMessage m;
      tr.At(i, m);
      if((m.type == SDB_ALERT_TYPE_HEARTBEAT || m.type == SDB_ALERT_TYPE_EA_START || m.type == SDB_ALERT_TYPE_EA_STOP) && !m.silent)
         loud++;
     }
   AssertTrue(id + "-heartbeat", StringFormat("heartbeat >= 3, jarak minimal 3600 detik lintas restart (%d, jarak terkecil %I64d), tanpa bunyi (berbunyi %d)",
                                              hb, minGap, loud), hb >= 3 && minGap >= 3600 && loud == 0 && tr.CountType(SDB_ALERT_TYPE_HEARTBEAT) == hb);
   string lastDay;
   ScCheckReports(id, rec, tr, lastDay);
   int secondStart = -1, starts = 0;
   for(int i = 0; i < tr.Count(); i++)
     {
      SdbOutMessage m;
      tr.At(i, m);
      if(m.type == SDB_ALERT_TYPE_EA_START && ++starts == 2)
         secondStart = i;
     }
   SdbOutMessage s2;
   bool mentions = secondStart >= 0 && tr.At(secondStart, s2) && StringFind(s2.text, "Sesi lalu berhenti") > 0;
   AssertTrue(id + "-startstop", StringFormat("2 start (yang kedua menyebut sesi lalu) dan 2 stop (start %d, stop %d)", starts, tr.CountType(SDB_ALERT_TYPE_EA_STOP)),
              starts == 2 && tr.CountType(SDB_ALERT_TYPE_EA_STOP) == 2 && mentions);
   long skipped = ScDbCount("SELECT COUNT(*) FROM alerts WHERE session_id IN (" + rec.SessionIdList() +
                            ") AND type IN ('HEARTBEAT','DAILY_REPORT','EA_START','EA_STOP') AND status <> 'SENT'");
   AssertTrue(id + "-never-skipped", StringFormat("heartbeat, laporan, start, stop semuanya SENT (bukan SENT: %I64d)", skipped), skipped == 0);
   ScCheckSessions(id, rec, 2);
  }

void CheckScenario(const string id, const CScenarioRecorder &rec, const CFakeTransport &tr)
  {
   TfBeginSuite(id == "" ? "(kosong)" : id);
   if(id == "SC-00")
      CheckSc00(id, rec);
   else if(id == "SC-01")
      CheckSc01(id, rec);
   else if(id == "SC-01b")
      CheckSc01b(id, rec);
   else if(id == "SC-04")
      CheckSc04(id, rec);
   else if(id == "SC-04b")
      CheckSc04b(id, rec);
   else if(id == "SC-02")
      CheckSc02(id, rec);
   else if(id == "SC-03")
      CheckSc03(id, rec);
   else if(id == "SC-03r")
      CheckSc03r(id, rec);
   else if(id == "SC-09")
      TfInfo("SC-09 (optimasi) diperiksa runner lewat laporan optimasi dan file DB, bukan oleh harness");
   else if(id == "SC-05")
      CheckSc05(id, rec);
   else if(id == "SC-07")
      CheckSc07(id, rec);
   else if(id == "SC-06")
      CheckSc06(id, rec);
   else if(id == "SC-08")
      CheckSc08(id, rec);
   else if(id == "SC-10")
      CheckSc10(id, rec, tr);
   else if(id == "SC-11")
      CheckSc11(id, rec, tr);
   else
      AssertTrue(id, "skenario tidak dikenal harness: '" + id + "'", false);
   TfEndSuite();
  }

#endif // SDB_SDBOTTESTS_SCENARIOS_MQH
