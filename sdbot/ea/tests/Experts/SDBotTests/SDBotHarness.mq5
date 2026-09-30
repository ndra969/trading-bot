//+------------------------------------------------------------------+
//| SDBotHarness.mq5 — harness skenario Strategy Tester (spec 04 Req 7,
//| design §4.6). Memakai CSdbApp dan modul yang sama dengan SDBot.mq5,
//| ditambah jadwal entry dari input, simulasi restart, dan pemeriksa
//| skenario SC-nn yang menulis hasil untuk run-ea-tests.ps1.
//| Hanya boleh jalan di Strategy Tester.
//+------------------------------------------------------------------+
#property copyright "SDBot"
#property version   "1.05"
#property description "Harness uji SDBot: entry terjadwal dan assert skenario. Hanya untuk Strategy Tester."

#define SDB_HARNESS_EA_VERSION "1.05"

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
input double                 HarnessFixedLot     = 0.0;        // lot tetap; 0 = CalcVolume (spec 05). Tetap lewat pre-trade check
input int                    HarnessRestartAtBar = 0;          // 0 = tanpa restart
input int                    HarnessRestartBarsAfterStop = 0;  // restart N bar setelah STOPPED pertama terlihat (0 = tidak)
input int                    HarnessRestartAfterPartial = 0;   // restart di bar ke-N setelah partial (1 = bar pertama sesudahnya; 0 = tidak, SC-04)
input int                    HarnessDetachBars    = 0;         // saat restart, app dilepas N bar dulu ("EA mati", SC-04b)
input int                    HarnessWithdrawAtBar = 0;         // tarik saldo di bar ini atau sesudahnya saat tanpa posisi (0 = tidak)
input double                 HarnessWithdrawPct   = 20.0;      // besar penarikan (% balance)

CSdbApp          *g_app = NULL;
CScenarioRecorder g_rec;
bool              g_runStarted = false;
datetime          g_lastBar = 0;
int               g_bar = 0;
int               g_entries = 0;
int               g_stopBar = 0;          // bar saat STOPPED pertama terlihat
bool              g_withdrawn = false;
int               g_partialBar = 0;       // bar saat PARTIAL terakhir tercatat
long              g_partialPos = 0;       // posisi PARTIAL terakhir; restart hanya bila masih terbuka
bool              g_partialRestartDone = false;
int               g_reattachBar = 0;      // > 0: app dilepas sampai bar ini

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
   g_rec.NoteRestart(TimeCurrent());
   RecordOwnPositions(true);
   StopApp(REASON_PROGRAM);
   if(HarnessDetachBars > 0)
     {
      g_reattachBar = g_bar + HarnessDetachBars;   // SC-04b: posisi tetap di broker, EA tidak ada
      return;
     }
   if(StartApp() != INIT_SUCCEEDED)
      LogError("Harness", "init ulang setelah restart gagal");
   RecordOwnPositions(false);
  }

void Reattach()
  {
   g_reattachBar = 0;
   g_rec.NoteReattach(TimeCurrent());
   if(StartApp() != INIT_SUCCEEDED)
      LogError("Harness", "init ulang setelah app dilepas gagal");
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
   g_entries++;
   // Jalur risiko sama dengan EA (spec 05 Req 8.1, 8.2): lot -> pre-trade check -> executor.
   string stage = "", detail = "";
   bool ok = (HarnessFixedLot > 0.0) || g_app.RiskManager().CalcVolume(rq, stage, detail);
   ok = ok && g_app.RiskManager().PreTradeCheck(rq, stage, detail);
   OrderResult res;
   if(!ok)
     {
      ZeroMemory(res);
      res.rejectStage = stage;
      res.detail = detail;
      g_rec.AddOpenResult(res, TimeCurrent());
      return;
     }
   g_app.Executor().OpenMarket(rq, res);
   g_rec.AddOpenResult(res, TimeCurrent());
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
   if(g_app != NULL)
      g_app.OnTick();
   datetime bar = iTime(_Symbol, _Period, 0);
   if(bar == 0 || bar == g_lastBar)
      return;
   g_lastBar = bar;
   g_bar++;
   if(g_app == NULL)
     {
      if(g_reattachBar > 0 && g_bar >= g_reattachBar)
         Reattach();
      return;
     }
   long lastPartial = g_rec.LastPartialPosition();
   if(lastPartial > 0 && lastPartial != g_partialPos)
     {
      g_partialPos = lastPartial;
      g_partialBar = g_bar;
     }
   bool restartAfterPartial = HarnessRestartAfterPartial > 0 && !g_partialRestartDone && g_partialBar > 0 &&
                              g_bar == g_partialBar + HarnessRestartAfterPartial - 1 && PositionSelectByTicket((ulong)g_partialPos);
   if(restartAfterPartial)
     {
      g_partialRestartDone = true;
      g_rec.NoteRestartPosition(g_partialPos);
     }
   if(g_stopBar == 0 && g_app.RiskState().IsReady() && g_app.RiskState().IsStopped())
      g_stopBar = g_bar;
   bool restartAfterStop = HarnessRestartBarsAfterStop > 0 && g_stopBar > 0 && g_bar == g_stopBar + HarnessRestartBarsAfterStop;
   if((HarnessRestartAtBar > 0 && g_bar == HarnessRestartAtBar) || restartAfterStop || restartAfterPartial)
      Restart();
   if(g_app != NULL && HarnessEveryBars > 0 && g_bar % HarnessEveryBars == 0)
      TryEntry();
   if(g_app != NULL)
      TryWithdraw();
  }

// Penarikan saldo terjadwal (spec 05 Req 8.3, SC-07): saat tanpa posisi, agar puncak tidak ikut
// berubah oleh floating antara penarikan dan pemrosesannya.
void TryWithdraw()
  {
   if(g_withdrawn || HarnessWithdrawAtBar <= 0 || g_bar < HarnessWithdrawAtBar || CountSdbotPositions() > 0 ||
      !g_app.RiskState().IsReady())
      return;
   double amount = NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE) * HarnessWithdrawPct / 100.0, 2);
   g_rec.NoteWithdraw(amount, g_app.RiskState().PeakEquity(), (int)g_app.RiskState().DdLevel());
   g_withdrawn = TesterWithdrawal(amount);
   if(!g_withdrawn)
      LogError("Harness", "TesterWithdrawal gagal | " + ErrText(GetLastError()));
  }

// Posisi SDBot di akun (semua simbol), untuk sampel emergency stop (SC-03).
int CountSdbotPositions()
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) != 0 && IsSdbotMagic(PositionGetInteger(POSITION_MAGIC)))
         n++;
   return n;
  }

void OnTimer()
  {
   if(g_app == NULL)
      return;
   g_app.OnTimer();
   if(!g_app.RiskState().IsReady())
      return;
   if(g_app.RiskState().IsStopped())
      g_rec.NoteStoppedSample(TimeCurrent(), CountSdbotPositions());
   if(g_withdrawn)
      g_rec.NoteAfterBalanceOp(g_app.RiskState().PeakEquity(), (int)g_app.RiskState().DdLevel());
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
