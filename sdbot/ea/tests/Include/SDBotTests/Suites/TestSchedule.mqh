//+------------------------------------------------------------------+
//| TestSchedule.mqh — lease pemimpin, jadwal heartbeat, hari laporan,
//| agregasi laporan harian; fungsi murni (spec 09 Req 4–6; design §3.2,
//| §4.2; TC-SC-01..10).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTSCHEDULE_MQH
#define SDB_SUITES_TESTSCHEDULE_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Notify/Schedule.mqh>

#define TSC_DAY 1790812800   // 2026.10.01 00:00 (awal hari server)

SdbDealRow TscRow(const long pos, const string symbol, const int kind, const long time, const double net, const double amount = 0.0)
  {
   SdbDealRow r;
   r.ticket = pos * 10 + kind;
   r.positionId = pos;
   r.symbol = symbol;
   r.kind = kind;
   r.time = time;
   r.net = net;
   r.amount = amount;
   return r;
  }

void TscAdd(SdbDealRow &rows[], const SdbDealRow &r)
  {
   int n = ArraySize(rows);
   ArrayResize(rows, n + 1);
   rows[n] = r;
  }

void RunTestSchedule()
  {
   TfBeginSuite("Schedule");

   int idx;
   long at;
   LeaseDecode(LeaseEncode(12, 1790762405), idx, at);
   AssertTrue("TC-SC-01", "lease encode/decode bolak-balik", idx == 12 && at == 1790762405);

   long now = 1790762405;
   AssertTrue("TC-SC-02", "lease: kosong, milik sendiri, milik lain umur 119 / 120",
              LeaseCanTake(0, 5, now, 120) && LeaseCanTake(LeaseEncode(5, now - 10), 5, now, 120) &&
              !LeaseCanTake(LeaseEncode(7, now - 119), 5, now, 120) && LeaseCanTake(LeaseEncode(7, now - 120), 5, now, 120));

   AssertTrue("TC-SC-03", "heartbeat 60 menit: 3599 belum, 3600 jatuh tempo; 0 = mati",
              !HeartbeatDue(now - 3599, now, 60) && HeartbeatDue(now - 3600, now, 60) && !HeartbeatDue(now - 99999, now, 0));

   long days[];
   AssertTrue("TC-SC-04", "terakhir = kemarin: tidak ada hari", ReportDays(TSC_DAY - 86400, TSC_DAY, days) == 0 &&
              ServerDayStart(TSC_DAY + 3600) == TSC_DAY);
   int n = ReportDays(TSC_DAY - 3 * 86400, TSC_DAY, days);
   AssertTrue("TC-SC-05", "terakhir = 3 hari lalu: 2 hari urut",
              n == 2 && days[0] == TSC_DAY - 2 * 86400 && days[1] == TSC_DAY - 86400);
   n = ReportDays(TSC_DAY - 30 * 86400, TSC_DAY, days);
   AssertTrue("TC-SC-06", "terakhir = 30 hari lalu: 7 hari terakhir",
              n == SDB_NT_REPORT_MAX_DAYS && days[0] == TSC_DAY - 7 * 86400 && days[n - 1] == TSC_DAY - 86400);

   // Hari dilaporkan = TSC_DAY.
   long d = TSC_DAY;
   SdbDealRow rows[];
   TscAdd(rows, TscRow(1, "EURUSDc", SDB_DS_KIND_IN, d + 100, -1.0));    // komisi buka hari itu
   TscAdd(rows, TscRow(1, "EURUSDc", SDB_DS_KIND_OUT, d + 900, 31.0));
   TscAdd(rows, TscRow(2, "XAUUSDc", SDB_DS_KIND_IN, d + 200, 0.0));
   TscAdd(rows, TscRow(2, "XAUUSDc", SDB_DS_KIND_OUT, d + 800, -10.0));
   TscAdd(rows, TscRow(3, "EURUSDc", SDB_DS_KIND_IN, d + 300, 0.0));
   TscAdd(rows, TscRow(3, "EURUSDc", SDB_DS_KIND_OUT, d + 700, 5.0));    // partial, posisi masih terbuka
   long open[] = {3};
   SdbDayStats st;
   DayStats(rows, open, d, st);
   AssertTrue("TC-SC-07", StringFormat("net hari itu, posisi tutup, win, per simbol (net=%.2f closed=%d wins=%d sym0=%s %.2f)",
                                       st.net, st.closed, st.wins, st.symbols[0], st.symbolNet[0]),
              MathAbs(st.net - 25.0) < 1e-9 && st.closed == 2 && st.wins == 1 && st.symbolCount == 2 &&
              st.symbols[0] == "EURUSDc" && MathAbs(st.symbolNet[0] - 35.0) < 1e-9 && st.symbols[1] == "XAUUSDc" &&
              DayHasActivity(st));

   SdbDealRow rows2[];
   TscAdd(rows2, TscRow(4, "GBPJPYc", SDB_DS_KIND_IN, d - 86400 + 100, -2.0));
   TscAdd(rows2, TscRow(4, "GBPJPYc", SDB_DS_KIND_OUT, d - 86400 + 500, -50.0));   // partial kemarin
   TscAdd(rows2, TscRow(4, "GBPJPYc", SDB_DS_KIND_OUT, d + 500, 20.0));            // sisa tutup hari ini
   long none[];
   SdbDayStats st2;
   DayStats(rows2, none, d, st2);
   AssertTrue("TC-SC-08", "dibuka kemarin tutup hari ini: dihitung tutup hari ini, net hari ini +20, kalah secara posisi",
              st2.closed == 1 && st2.wins == 0 && MathAbs(st2.net - 20.0) < 1e-9);

   SdbDealRow rows3[];
   TscAdd(rows3, TscRow(0, "", SDB_DS_KIND_BALANCE, d + 60, 0.0, -200.0));
   SdbDayStats st3;
   DayStats(rows3, none, d, st3);
   AssertTrue("TC-SC-09", "hanya operasi saldo: tanpa posisi, operasi -200, ada aktivitas",
              st3.closed == 0 && st3.hasBalanceOps && MathAbs(st3.balanceOps + 200.0) < 1e-9 && DayHasActivity(st3));

   SdbDealRow empty[];
   SdbDayStats st4;
   DayStats(empty, none, d, st4);
   AssertTrue("TC-SC-10", "tanpa deal: tanpa aktivitas", !DayHasActivity(st4) && st4.closed == 0 && st4.net == 0.0);

   TfEndSuite();
  }

#endif // SDB_SUITES_TESTSCHEDULE_MQH
