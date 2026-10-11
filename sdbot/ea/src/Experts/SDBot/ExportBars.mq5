//+------------------------------------------------------------------+
//| ExportBars.mq5 — alat riset (spec 31 Req 2.1): dijalankan di
//| Strategy Tester per simbol, menulis setiap bar M1 tertutup (bid)
//| dan spreadnya ke Common\Files\sdbot_bars\<SIMBOL>_M1.csv untuk
//| tools/outcome_sim.py. Tester dipakai, bukan script, karena
//| CopyRates di terminal dibatasi "Max bars in chart"; di tester
//| datanya sama persis dengan data backtest. Tidak trading, tidak DB.
//+------------------------------------------------------------------+
#property copyright "SDBot"
#property version   "1.29"
#property description "Alat riset: ekspor bar M1 dari Strategy Tester ke Common\\Files\\sdbot_bars (spec 31)."

#include <SDBot/Core/Utils.mqh>

#define EXB_DIR "sdbot_bars\\"

int      g_file = INVALID_HANDLE;
datetime g_last = 0;
long     g_count = 0;
datetime g_first = 0;
string   g_error = "";

string ExbPath(const string suffix) { return EXB_DIR + _Symbol + suffix; }

int OnInit()
  {
   if(!MQLInfoInteger(MQL_TESTER))
     {
      LogError("ExportBars", "hanya untuk Strategy Tester");
      return INIT_FAILED;
     }
   g_file = FileOpen(ExbPath("_M1.csv"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(g_file == INVALID_HANDLE)
     {
      LogError("ExportBars", "tidak bisa menulis " + ExbPath("_M1.csv") + " | " + ErrText(GetLastError()));
      return INIT_FAILED;
     }
   FileWriteString(g_file, StringFormat("# symbol=%s point=%s digits=%d\n", _Symbol,
                                        DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_POINT), 10),
                                        (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS)));
   FileWriteString(g_file, "time,open,high,low,close,spread\n");
   return INIT_SUCCEEDED;
  }

// Semua bar M1 tertutup sesudah g_last (bisa lebih dari satu bila tick melompati menit).
void OnTick()
  {
   datetime closed = iTime(_Symbol, PERIOD_M1, 1);
   if(closed <= 0 || closed <= g_last || g_file == INVALID_HANDLE)
      return;
   MqlRates r[];
   int n = (g_last == 0) ? CopyRates(_Symbol, PERIOD_M1, 1, 1, r) : CopyRates(_Symbol, PERIOD_M1, g_last + 1, closed, r);
   if(n <= 0)
     {
      g_error = "CopyRates " + TimeToString(closed) + " | " + ErrText(GetLastError());
      return;
     }
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   for(int i = 0; i < n; i++)
     {
      if(r[i].time <= g_last)
         continue;
      FileWriteString(g_file, StringFormat("%I64d,%s,%s,%s,%s,%d\n", (long)r[i].time, DoubleToString(r[i].open, digits),
                                           DoubleToString(r[i].high, digits), DoubleToString(r[i].low, digits),
                                           DoubleToString(r[i].close, digits), r[i].spread));
      if(g_first == 0)
         g_first = r[i].time;
      g_last = r[i].time;
      g_count++;
     }
  }

void OnDeinit(const int reason)
  {
   if(g_file != INVALID_HANDLE)
      FileClose(g_file);
   string status = (g_count > 0 && g_error == "")
                   ? StringFormat("OK %I64d bar %s..%s", g_count, TimeToString(g_first), TimeToString(g_last))
                   : StringFormat("PARTIAL %I64d bar %s", g_count, g_error == "" ? "tanpa bar" : g_error);
   int h = FileOpen(ExbPath("_status.txt"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h != INVALID_HANDLE)
     {
      FileWriteString(h, status + "\n");
      FileClose(h);
     }
   if(g_count > 0 && g_error == "")
      LogInfo("ExportBars", status);
   else
      LogWarn("ExportBars", status);
  }
