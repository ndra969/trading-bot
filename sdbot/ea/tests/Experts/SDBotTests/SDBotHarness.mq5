//+------------------------------------------------------------------+
//| SDBotHarness.mq5 — harness skenario Strategy Tester (spec 04 Req 7,
//| design §4.6). Memakai CSdbApp dan modul yang sama dengan SDBot.mq5,
//| ditambah jadwal entry dari input, simulasi restart, dan pemeriksa
//| skenario SC-nn yang menulis hasil untuk run-ea-tests.ps1.
//| Hanya boleh jalan di Strategy Tester.
//+------------------------------------------------------------------+
#property copyright "SDBot"
#property version   "1.03"
#property description "Harness uji SDBot: entry terjadwal dan assert skenario. Hanya untuk Strategy Tester."

#define SDB_HARNESS_EA_VERSION "1.03"

#include <SDBot/Core/Inputs.mqh>
#include <SDBot/App/SdbApp.mqh>
#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/ScenarioRecorder.mqh>
#include <SDBotTests/Scenarios.mqh>

enum ENUM_HARNESS_DIRECTION
  {
   HARNESS_BUY = 0,
   HARNESS_SELL = 1,
   HARNESS_ALTERNATE = 2
  };

input group "Harness"
input string                 InpTestRunId        = "manual";   // ID run (diisi runner)
input string                 HarnessScenario     = "";         // ID skenario, mis. SC-06
input int                    HarnessEveryBars    = 20;         // entry setiap N bar chart
input ENUM_HARNESS_DIRECTION HarnessDirection    = HARNESS_ALTERNATE;
input int                    HarnessSlPoints     = 200;        // jarak SL dari harga (point)
input int                    HarnessTpPoints     = 200;        // jarak TP dari harga (point)
input int                    HarnessMaxOpen      = 1;          // posisi sendiri maksimum
input double                 HarnessFixedLot     = 0.01;       // lot tetap (lot sizing mulai spec 05)
input int                    HarnessRestartAtBar = 0;          // 0 = tanpa restart

CSdbApp          *g_app = NULL;
CScenarioRecorder g_rec;
bool              g_runStarted = false;
datetime          g_lastBar = 0;
int               g_bar = 0;
int               g_entries = 0;

// Posisi sendiri (magic + simbol) untuk pemeriksaan restart.
void RecordOwnPositions(const bool before)
  {
   long magic = CurrentInputs().magic;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || PositionGetInteger(POSITION_MAGIC) != magic || PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      long id = PositionGetInteger(POSITION_IDENTIFIER);
      if(before)
         g_rec.AddPositionBeforeRestart(id);
      else
         g_rec.AddPositionAfterRestart(id);
     }
  }

int StartApp()
  {
   g_app = new CSdbApp;
   int r = g_app.OnInit(CurrentAppConfig(SDB_APP_HARNESS, SDB_HARNESS_EA_VERSION), GetPointer(g_rec));
   if(g_app.Logger().SessionId() > 0)
      g_rec.AddSession(g_app.Logger().SessionId());
   return r;
  }

void StopApp(const int reason)
  {
   if(g_app == NULL)
      return;
   g_app.OnDeinit(reason);
   g_rec.AddSends(g_app.Executor().SendCount());
   delete g_app;
   g_app = NULL;
  }

// Restart simulasi (Req 7.5): GV dan posisi tetap, orkestrasi dibuat ulang, sesi baru.
void Restart()
  {
   RecordOwnPositions(true);
   StopApp(REASON_PROGRAM);
   if(StartApp() != INIT_SUCCEEDED)
      LogError("Harness", "init ulang setelah restart gagal");
   RecordOwnPositions(false);
  }

bool EntryIsBuy()
  {
   if(HarnessDirection == HARNESS_BUY)
      return true;
   if(HarnessDirection == HARNESS_SELL)
      return false;
   return (g_entries % 2) == 0;
  }

// Entry terjadwal lewat Executor (Req 7.4); hasil, termasuk tolak, dicatat perekam.
void TryEntry()
  {
   if(g_app.Executor().CountOwnPositions() >= HarnessMaxOpen)
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   OrderRequest rq;
   rq.isBuy = EntryIsBuy();
   rq.volume = HarnessFixedLot;
   rq.signalId = SDB_NULL_LONG;
   double price = rq.isBuy ? tick.ask : tick.bid;
   double dir = rq.isBuy ? 1.0 : -1.0;
   rq.sl = price - dir * HarnessSlPoints * point;
   rq.tp = price + dir * HarnessTpPoints * point;
   OrderResult res;
   g_app.Executor().OpenMarket(rq, res);
   g_rec.AddOpenResult(res);
   g_entries++;
  }

int OnInit()
  {
   if(!MQLInfoInteger(MQL_TESTER))
     {
      LogCritical("Harness", "harness hanya boleh jalan di Strategy Tester");
      return INIT_FAILED;
     }
   TfBeginRun(InpTestRunId);
   g_runStarted = true;
   return StartApp();
  }

void OnTick()
  {
   if(g_app == NULL)
      return;
   g_app.OnTick();
   datetime bar = iTime(_Symbol, _Period, 0);
   if(bar == 0 || bar == g_lastBar)
      return;
   g_lastBar = bar;
   g_bar++;
   if(HarnessRestartAtBar > 0 && g_bar == HarnessRestartAtBar)
      Restart();
   if(g_app != NULL && HarnessEveryBars > 0 && g_bar % HarnessEveryBars == 0)
      TryEntry();
  }

void OnTimer()
  {
   if(g_app != NULL)
      g_app.OnTimer();
  }

void OnTradeTransaction(const MqlTradeTransaction &t, const MqlTradeRequest &rq, const MqlTradeResult &rs)
  {
   if(g_app != NULL)
      g_app.OnTradeTransaction(t, rq, rs);
  }

double OnTester()
  {
   return (g_app != NULL) ? g_app.OnTester() : 0.0;
  }

// CSdbApp ditutup dulu (flush dan tutup DB), baru skenario diperiksa (design §4.6).
void OnDeinit(const int reason)
  {
   StopApp(reason);
   if(!g_runStarted)
      return;
   CheckScenario(HarnessScenario, g_rec);
   TfEndRun();
   g_runStarted = false;
  }
