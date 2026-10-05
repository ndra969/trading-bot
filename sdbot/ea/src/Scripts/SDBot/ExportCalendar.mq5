//+------------------------------------------------------------------+
//| ExportCalendar.mq5 — tulis kalender ekonomi MT5 ke CSV di
//| Common\Files untuk filter berita di Strategy Tester (spec 16
//| Req 5; design §3.3; PRD: kalender tidak tersedia di tester).
//| Format per baris: epoch_server,ccy,impact,event_id,nama (urut
//| waktu). Hanya jadwal event, tanpa nilai actual.
//+------------------------------------------------------------------+
#property copyright "SDBot"
#property version   "1.17"
#property description "Ekspor kalender ekonomi MT5 ke Common\\Files\\sdbot_calendar.csv untuk backtest SDBot."

#include <SDBot/Core/Utils.mqh>
#include <SDBot/Filters/NewsRules.mqh>

input datetime InpFrom          = D'2025.01.01';      // Mulai
input datetime InpTo            = 0;                  // Akhir (0 = sekarang + 7 hari)
input string   InpFile          = "sdbot_calendar.csv"; // File di Common\Files
input bool     InpCloseTerminal = false;              // Tutup terminal setelah selesai (dipakai runner)

#define EXP_STATUS_FILE "sdbot_calendar_status.txt"
#define EXP_SYNC_WAIT_MS 120000   // kalender baru tersinkron beberapa detik setelah terminal start (err 5401)
#define EXP_SYNC_STEP_MS 2000

void WriteStatus(const string text)
  {
   int h = FileOpen(EXP_STATUS_FILE, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h == INVALID_HANDLE)
      return;
   FileWriteString(h, text + "\n");
   FileClose(h);
  }

// Event satu mata uang, urut waktu (CalendarValueHistory mengembalikan urut waktu per mata uang).
int LoadCurrency(const string ccy, const datetime from, const datetime to, SdbNewsEvent &out[], int &counts[])
  {
   MqlCalendarValue vals[];
   int n = -1;
   for(int waited = 0; !IsStopped(); waited += EXP_SYNC_STEP_MS)
     {
      ResetLastError();
      n = CalendarValueHistory(vals, from, to, NULL, ccy);
      if(n > 0 || GetLastError() != ERR_CALENDAR_TIMEOUT || waited >= EXP_SYNC_WAIT_MS)
         break;
      Sleep(EXP_SYNC_STEP_MS);
     }
   if(n <= 0)
      return -1;
   for(int i = 0; i < n; i++)
     {
      MqlCalendarEvent ev;
      if(!CalendarEventById(vals[i].event_id, ev))
         continue;
      SdbNewsEvent e;
      e.time = vals[i].time;
      e.ccy = ccy;
      e.impact = (ev.importance == CALENDAR_IMPORTANCE_HIGH) ? SDB_NEWS_HIGH :
                 (ev.importance == CALENDAR_IMPORTANCE_MODERATE ? SDB_NEWS_MEDIUM : SDB_NEWS_LOW);
      e.id = (long)ev.id;
      e.name = ev.name;
      int m = ArraySize(out);
      ArrayResize(out, m + 1, 4096);
      out[m] = e;
      counts[e.impact]++;
     }
   return ArraySize(out);
  }

void OnStart()
  {
   string ccys[] = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"};
   datetime to = (InpTo > 0) ? InpTo : TimeTradeServer() + 7 * 86400;
   SdbNewsEvent all[];
   string summary = "";
   bool ok = true;
   for(int c = 0; c < ArraySize(ccys) && ok; c++)
     {
      SdbNewsEvent one[];
      int counts[3] = {0, 0, 0};
      if(LoadCurrency(ccys[c], InpFrom, to, one, counts) < 0)
        {
         ok = false;
         summary = "GAGAL kalender belum tersinkron / tidak tersedia untuk " + ccys[c] + " (" + ErrText(GetLastError()) + ")";
         break;
        }
      summary += StringFormat("%s high=%d medium=%d low=%d; ", ccys[c], counts[SDB_NEWS_HIGH], counts[SDB_NEWS_MEDIUM], counts[SDB_NEWS_LOW]);
      // Gabung terurut waktu (k-way merge sederhana: sisipkan blok terurut).
      SdbNewsEvent merged[];
      ArrayResize(merged, ArraySize(all) + ArraySize(one));
      int i = 0, j = 0, k = 0;
      while(i < ArraySize(all) || j < ArraySize(one))
        {
         if(j >= ArraySize(one) || (i < ArraySize(all) && all[i].time <= one[j].time))
            merged[k++] = all[i++];
         else
            merged[k++] = one[j++];
        }
      ArrayFree(all);
      ArrayResize(all, k);
      for(int m = 0; m < k; m++)
         all[m] = merged[m];
     }
   if(ok && ArraySize(all) == 0)
     {
      ok = false;
      summary = "GAGAL kalender kosong";
     }
   if(ok)
     {
      int h = FileOpen(InpFile, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
      if(h == INVALID_HANDLE)
        {
         ok = false;
         summary = "GAGAL tidak bisa menulis " + InpFile + " (" + ErrText(GetLastError()) + ")";
        }
      else
        {
         for(int i = 0; i < ArraySize(all); i++)
            FileWriteString(h, CalendarLine(all[i]) + "\n");
         FileClose(h);
         summary = StringFormat("OK %d event %s..%s | %s", ArraySize(all), TimeToString(all[0].time, TIME_DATE),
                                TimeToString(all[ArraySize(all) - 1].time, TIME_DATE), summary);
        }
     }
   WriteStatus(summary);
   if(ok)
      LogInfo("ExportCalendar", summary);
   else
      LogError("ExportCalendar", summary);
   if(InpCloseTerminal)
      TerminalClose(0);
  }
