//+------------------------------------------------------------------+
//| TestNotifyRules.mqh — aturan kirim notifier, fungsi murni
//| (spec 08 Req 2, 3; design §3.3, katalog TC-NT-01..21).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTNOTIFYRULES_MQH
#define SDB_SUITES_TESTNOTIFYRULES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Notify/NotifyRules.mqh>

SdbNtItem NtTestItem(const ENUM_SDB_SEVERITY sev, const long queuedAt, const long notBefore = 0)
  {
   SdbNtItem it;
   it.msg.key = "k" + IntegerToString(queuedAt);
   it.msg.type = "T";
   it.msg.text = "";
   it.msg.silent = false;
   it.msg.severity = sev;
   it.queuedAt = queuedAt;
   it.attempts = 0;
   it.notBefore = notBefore;
   return it;
  }

SdbSendResult NtTestResult(const ENUM_SDB_SEND_CODE code, const int retryAfter = 0)
  {
   SdbSendResult r;
   r.code = code;
   r.retryAfterSec = retryAfter;
   r.error = "";
   return r;
  }

void RunTestNotifyRules()
  {
   TfBeginSuite("NotifyRules");

   // TC-NT-01..02: lingkup akun vs instance (Req 2.5, PC-13).
   AssertTrue("TC-NT-01", "DD_STOP, CONN_DOWN, BALANCE_OP lingkup akun",
              NtScopeOf("DD_STOP") == SDB_NT_SCOPE_ACCOUNT && NtScopeOf("CONN_DOWN") == SDB_NT_SCOPE_ACCOUNT &&
              NtScopeOf("BALANCE_OP") == SDB_NT_SCOPE_ACCOUNT && NtScopeOf("MARGIN_OK") == SDB_NT_SCOPE_ACCOUNT &&
              NtScopeOf("DAILY_LOSS") == SDB_NT_SCOPE_ACCOUNT && NtScopeOf("STATE_RESET") == SDB_NT_SCOPE_ACCOUNT &&
              NtScopeOf("EMERGENCY_RESET") == SDB_NT_SCOPE_ACCOUNT && NtScopeOf("CONN_UP") == SDB_NT_SCOPE_ACCOUNT);
   AssertTrue("TC-NT-02", "ORDER_FAILED, SL_RESTORED, TRADE_OPENED, tipe asing lingkup instance",
              NtScopeOf("ORDER_FAILED") == SDB_NT_SCOPE_INSTANCE && NtScopeOf("SL_RESTORED") == SDB_NT_SCOPE_INSTANCE &&
              NtScopeOf("TRADE_OPENED") == SDB_NT_SCOPE_INSTANCE && NtScopeOf("FOO") == SDB_NT_SCOPE_INSTANCE);

   // TC-NT-03..05: cooldown per severity dan tipe (Req 2.1–2.4).
   AssertTrue("TC-NT-03", "Critical dan High tanpa cooldown",
              NtCooldownSec(SDB_SEV_CRITICAL, "DD_STOP") == 0 && NtCooldownSec(SDB_SEV_HIGH, "DD_REDUCE") == 0);
   AssertTrue("TC-NT-04", "Medium dan Info alert 300 detik",
              NtCooldownSec(SDB_SEV_MEDIUM, "CONN_DOWN") == 300 && NtCooldownSec(SDB_SEV_INFO, "DD_INFO") == 300);
   AssertTrue("TC-NT-05", "event trade tanpa cooldown",
              NtCooldownSec(SDB_SEV_INFO, "BE_MOVED") == 0 && NtCooldownSec(SDB_SEV_INFO, "PARTIAL_CLOSED") == 0 &&
              NtCooldownSec(SDB_SEV_INFO, "TRADE_CLOSED") == 0 && NtCooldownSec(SDB_SEV_INFO, "TRADE_OPENED") == 0 &&
              NtIsTradeType("TRADE_OPENED") && !NtIsTradeType("DD_INFO"));

   // TC-NT-06: batas cooldown tepat 300 detik (Req 2.3).
   long now = 1790000000;
   AssertTrue("TC-NT-06", "last 0 lolos, 299 ditahan, 300 lolos",
              NtCooldownOk(0, now, 300) && !NtCooldownOk(now - 299, now, 300) && NtCooldownOk(now - 300, now, 300));

   // TC-NT-07..10: kuota per jam, GV = jam x 1000 + jumlah (Req 2.6).
   long h10 = 10 * 3600 + 5;
   double nv = -1;
   bool ok = NtQuotaTake(0, h10, 20, nv);
   AssertTrue("TC-NT-07", "GV kosong: lolos, jam 10 jumlah 1", ok && nv == 10 * 1000 + 1);
   ok = NtQuotaTake(10 * 1000 + 19, h10, 20, nv);
   AssertTrue("TC-NT-08", "jumlah 19: lolos jadi 20", ok && nv == 10 * 1000 + 20);
   nv = -1;
   ok = NtQuotaTake(10 * 1000 + 20, h10, 20, nv);
   AssertTrue("TC-NT-09", "jumlah 20: ditolak, nilai tetap", !ok && nv == 10 * 1000 + 20);
   ok = NtQuotaTake(9 * 1000 + 20, h10, 20, nv);
   AssertTrue("TC-NT-10", "jam lalu penuh: jam baru jumlah 1", ok && nv == 10 * 1000 + 1 && NtQuotaHour(h10) == 10);

   // TC-NT-11..12: pesan basi (Req 2.7).
   AssertTrue("TC-NT-11", "Info umur 1800 belum basi, 1801 basi",
              !NtIsStale(SDB_SEV_INFO, now - 1800, now) && NtIsStale(SDB_SEV_INFO, now - 1801, now));
   AssertTrue("TC-NT-12", "Critical tidak pernah basi", !NtIsStale(SDB_SEV_CRITICAL, now - 7200, now));

   // TC-NT-13..15: urutan ambil (Req 3.2, 3.5).
   SdbNtItem q[];
   ArrayResize(q, 3);
   q[0] = NtTestItem(SDB_SEV_INFO, 1);
   q[1] = NtTestItem(SDB_SEV_MEDIUM, 2);
   q[2] = NtTestItem(SDB_SEV_CRITICAL, 3);
   AssertIntEq("TC-NT-13", "Critical diambil dulu", NtPickNext(q, now), 2);
   SdbNtItem f[];
   ArrayResize(f, 2);
   f[0] = NtTestItem(SDB_SEV_INFO, 1);
   f[1] = NtTestItem(SDB_SEV_INFO, 2);
   AssertIntEq("TC-NT-14", "sesama prioritas FIFO", NtPickNext(f, now), 0);
   f[0].notBefore = now + 10;
   f[1].notBefore = now + 10;
   AssertIntEq("TC-NT-15", "semua menunggu: -1", NtPickNext(f, now), -1);

   // TC-NT-16..17: korban antrean penuh (Req 3.7).
   SdbNtItem o[];
   ArrayResize(o, 3);
   o[0] = NtTestItem(SDB_SEV_CRITICAL, 1);
   o[1] = NtTestItem(SDB_SEV_INFO, 5);
   o[2] = NtTestItem(SDB_SEV_MEDIUM, 3);
   AssertIntEq("TC-NT-16", "non-Critical tertua digeser", NtOverflowVictim(o), 2);
   SdbNtItem c[];
   ArrayResize(c, 2);
   c[0] = NtTestItem(SDB_SEV_CRITICAL, 1);
   c[1] = NtTestItem(SDB_SEV_CRITICAL, 2);
   AssertIntEq("TC-NT-17", "semua Critical: tidak ada korban", NtOverflowVictim(c), -1);

   // TC-NT-18..21: langkah setelah hasil kirim (Req 3.4–3.6). attempts = percobaan yang sudah dilakukan.
   AssertIntEq("TC-NT-18", "OK -> terkirim", NtAfterResult(NtTestResult(SDB_SEND_OK), 1), SDB_NT_DONE_SENT);
   AssertTrue("TC-NT-19", "TEMP: retry di 1 dan 2, gagal di 3",
              NtAfterResult(NtTestResult(SDB_SEND_TEMP), 1) == SDB_NT_RETRY &&
              NtAfterResult(NtTestResult(SDB_SEND_TEMP), 2) == SDB_NT_RETRY &&
              NtAfterResult(NtTestResult(SDB_SEND_TEMP), 3) == SDB_NT_DONE_FAILED);
   AssertIntEq("TC-NT-20", "LIMITED -> tunggu", NtAfterResult(NtTestResult(SDB_SEND_LIMITED, 60), 2), SDB_NT_WAIT);
   AssertIntEq("TC-NT-21", "PERMANENT -> gagal tanpa retry", NtAfterResult(NtTestResult(SDB_SEND_PERMANENT), 1), SDB_NT_DONE_FAILED);

   TfEndSuite();
  }

#endif // SDB_SUITES_TESTNOTIFYRULES_MQH
