//+------------------------------------------------------------------+
//| Schedule.mqh — fungsi murni pesan berjadwal: lease pemimpin per akun,
//| jadwal heartbeat, hari yang perlu dilaporkan, agregasi laporan harian
//| (spec 09 Req 4–6; design §3.2, §4.2). Waktu = waktu server notifier.
//+------------------------------------------------------------------+
#ifndef SDB_NOTIFY_SCHEDULE_MQH
#define SDB_NOTIFY_SCHEDULE_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>

#define SDB_LEASE_IDX_FACTOR 10000000000   // GV lease = idx x 1e10 + waktu (waktu < 1e10)
#define SDB_DAY_SEC          86400

// idx = magic - SDB_MAGIC_HARNESS (0..99), satu GV agar cukup satu compare-and-set.
double LeaseEncode(const int idx, const long at) { return (double)((long)idx * SDB_LEASE_IDX_FACTOR + at); }

void LeaseDecode(const double v, int &idx, long &at)
  {
   long lv = (long)MathRound(v);
   idx = (int)(lv / SDB_LEASE_IDX_FACTOR);
   at = lv % SDB_LEASE_IDX_FACTOR;
  }

// Kosong, milik sendiri (perpanjang), atau milik instance lain yang tidak memperbarui selama ttl (Req 4.2).
bool LeaseCanTake(const double cur, const int myIdx, const long now, const int ttl)
  {
   if(cur <= 0.0)
      return true;
   int idx;
   long at;
   LeaseDecode(cur, idx, at);
   return idx == myIdx || now - at >= ttl;
  }

bool HeartbeatDue(const long lastAt, const long now, const int minutes)
  {
   return minutes > 0 && now - lastAt >= (long)minutes * 60;
  }

long ServerDayStart(const long t) { return t - t % SDB_DAY_SEC; }

// Hari setelah lastReportedDay sampai kemarin, maksimal SDB_NT_REPORT_MAX_DAYS terakhir (Req 6.1, 6.4).
int ReportDays(const long lastReportedDay, const long todayStart, long &days[])
  {
   ArrayFree(days);
   long first = MathMax(lastReportedDay + SDB_DAY_SEC, todayStart - (long)SDB_NT_REPORT_MAX_DAYS * SDB_DAY_SEC);
   for(long d = first; d < todayStart; d += SDB_DAY_SEC)
     {
      int n = ArraySize(days);
      ArrayResize(days, n + 1);
      days[n] = d;
     }
   return ArraySize(days);
  }

bool DsIsOpen(const long id, const long &openIds[])
  {
   for(int i = 0; i < ArraySize(openIds); i++)
      if(openIds[i] == id)
         return true;
   return false;
  }

void DsAddSymbol(SdbDayStats &out, const string symbol, const double net)
  {
   for(int i = 0; i < out.symbolCount; i++)
      if(out.symbols[i] == symbol)
        {
         out.symbolNet[i] += net;
         return;
        }
   if(out.symbolCount >= SDB_DS_MAX_SYMBOLS)
      return;
   out.symbols[out.symbolCount] = symbol;
   out.symbolNet[out.symbolCount] = net;
   out.symbolCount++;
  }

// Urut dari |net| terbesar (simbol paling berpengaruh di atas).
void DsSortSymbols(SdbDayStats &out)
  {
   for(int i = 1; i < out.symbolCount; i++)
      for(int j = i; j > 0 && MathAbs(out.symbolNet[j]) > MathAbs(out.symbolNet[j - 1]); j--)
        {
         string s = out.symbols[j];
         out.symbols[j] = out.symbols[j - 1];
         out.symbols[j - 1] = s;
         double v = out.symbolNet[j];
         out.symbolNet[j] = out.symbolNet[j - 1];
         out.symbolNet[j - 1] = v;
        }
  }

// Posisi tutup dengan deal keluar hari itu dan tidak lagi terbuka; win dari net seluruh deal posisi (design §4.2).
void DsCountClosed(const SdbDealRow &rows[], const long &openIds[], const long dayStart, SdbDayStats &out)
  {
   long seen[];
   for(int i = 0; i < ArraySize(rows); i++)
     {
      long id = rows[i].positionId;
      bool outToday = rows[i].kind == SDB_DS_KIND_OUT && rows[i].time >= dayStart && rows[i].time < dayStart + SDB_DAY_SEC;
      if(!outToday || DsIsOpen(id, openIds) || DsIsOpen(id, seen))
         continue;
      int n = ArraySize(seen);
      ArrayResize(seen, n + 1);
      seen[n] = id;
      double total = 0.0;
      for(int k = 0; k < ArraySize(rows); k++)
         if(rows[k].positionId == id && rows[k].kind != SDB_DS_KIND_BALANCE)
            total += rows[k].net;
      out.closed++;
      if(total > 0.0)
         out.wins++;
     }
  }

void DayStats(const SdbDealRow &rows[], const long &openIds[], const long dayStart, SdbDayStats &out)
  {
   ZeroMemory(out);
   out.dayStart = dayStart;
   for(int i = 0; i < ArraySize(rows); i++)
     {
      if(rows[i].time < dayStart || rows[i].time >= dayStart + SDB_DAY_SEC)
         continue;
      if(rows[i].kind == SDB_DS_KIND_BALANCE)
        {
         out.balanceOps += rows[i].amount;
         out.hasBalanceOps = true;
         continue;
        }
      out.net += rows[i].net;
      DsAddSymbol(out, rows[i].symbol, rows[i].net);
     }
   DsCountClosed(rows, openIds, dayStart, out);
   DsSortSymbols(out);
  }

// Laporan hanya untuk hari dengan posisi tutup atau operasi saldo (Req 6.3).
bool DayHasActivity(const SdbDayStats &s) { return s.closed > 0 || s.hasBalanceOps; }

#endif // SDB_NOTIFY_SCHEDULE_MQH
