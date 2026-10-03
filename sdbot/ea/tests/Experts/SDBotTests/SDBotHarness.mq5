//+------------------------------------------------------------------+
//| SDBotHarness.mq5 — harness skenario Strategy Tester (spec 04 Req 7,
//| design §4.6). Memakai CSdbApp dan modul yang sama dengan SDBot.mq5,
//| ditambah jadwal entry dari input, simulasi restart, dan pemeriksa
//| skenario SC-nn yang menulis hasil untuk run-ea-tests.ps1.
//| Hanya boleh jalan di Strategy Tester.
//+------------------------------------------------------------------+
#property copyright "SDBot"
#property version   "1.12"
#property description "Harness uji SDBot: entry terjadwal dan assert skenario. Hanya untuk Strategy Tester."

#define SDB_HARNESS_EA_VERSION "1.12"

#include <SDBot/Core/Inputs.mqh>
#include <SDBot/App/SdbApp.mqh>
#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/ScenarioRecorder.mqh>
#include <SDBotTests/FakeTransport.mqh>
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
input string                 HarnessTransportScript   = "";    // skrip CFakeTransport ("" = transport log biasa), SC-10
input string                 HarnessTransportFailType = "";    // tipe yang selalu gagal sementara di transport palsu
input int                    HarnessAlertBurstAtBar   = 0;     // kirim burst alert uji di bar ini (0 = tidak)
input bool                   HarnessRecordAnalysis    = false; // rekam analisis HTF/MTF tiap bar baru (SC-12)
input bool                   HarnessRecordZones       = false; // rekam sidik peta zona tiap bar MTF baru (SC-13)
input bool                   HarnessPipeline          = false; // pipeline sinyal membuka posisi seperti EA utama (SC-14)
input int                    HarnessMarkUsedAtBar     = 0;     // tandai zona valid pertama Used di bar ini (0 = tidak, SC-13)

CSdbApp          *g_app = NULL;
CScenarioRecorder g_rec;
CFakeTransport    g_tr;
long              g_timerCycle = 0;
datetime          g_lastHtfSample = 0;
datetime          g_lastMtfSample = 0;
datetime          g_lastZoneSample = 0;
bool              g_zoneMarked = false;
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
   ISdbTransport *tr = (HarnessTransportScript != "") ? GetPointer(g_tr) : NULL;   // NULL = transport log (skenario lain)
   SdbAppConfig cfg = CurrentAppConfig(SDB_APP_HARNESS, SDB_HARNESS_EA_VERSION);
   cfg.signalsOn = HarnessPipeline;
   int r = g_app.OnInit(cfg, GetPointer(g_rec), tr);
   if(g_app.Logger().SessionId() > 0)
      g_rec.AddSession(g_app.Logger().SessionId());
   return r;
  }

void StopApp(const int reason)
  {
   if(g_app == NULL)
      return;
   g_tr.SetPhase("DEINIT");
   g_app.OnDeinit(reason);
   g_rec.SetNotifyQueueAtStop(g_app.Notifier().QueueSize());
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
   g_tr.Script(HarnessTransportScript);
   g_tr.FailType(HarnessTransportFailType);
   return StartApp();
  }

void OnTick()
  {
   g_tr.SetPhase("TICK");
   HarnessTick();
   g_tr.SetPhase("");
  }

// Burst alert uji (SC-10): 2x Medium untuk cooldown (sebelum kuota habis), satu tipe yang selalu gagal,
// lalu 25 Info berbeda tipe agar kuota 20 per jam terlampaui.
void AlertBurst()
  {
   AlertEvent a;
   a.symbol = _Symbol;
   a.magic = CurrentInputs().magic;
   a.time = TimeCurrent();
   a.type = SDB_ALERT_TYPE_ORDER_FAILED;
   a.severity = SDB_SEV_MEDIUM;
   a.message = "uji burst ORDER_FAILED pertama";
   g_app.Sink().OnAlert(a);
   a.message = "uji burst ORDER_FAILED kedua";
   g_app.Sink().OnAlert(a);
   a.severity = SDB_SEV_INFO;
   if(HarnessTransportFailType != "")
     {
      a.type = HarnessTransportFailType;
      a.message = "uji burst gagal sementara";
      g_app.Sink().OnAlert(a);
     }
   for(int i = 1; i <= 25; i++)
     {
      a.type = StringFormat("TEST_BURST_%02d", i);
      a.message = "uji burst kuota " + IntegerToString(i);
      g_app.Sink().OnAlert(a);
     }
  }

// Satu sampel per bar baru HTF/MTF (bertahan lintas restart karena variabel global harness).
void RecordAnalysis()
  {
   if(!HarnessRecordAnalysis || g_app == NULL)
      return;
   SdbTfAnalysis h, m;
   SdbBias b;
   g_app.Structure().Htf(h);
   g_app.Structure().Mtf(m);
   g_app.Structure().Bias(b);
   if(h.barTime != 0 && h.barTime != g_lastHtfSample)
     {
      g_lastHtfSample = h.barTime;
      g_rec.AddAnalysisSample(SampleOf(g_app.Structure().HtfTimeframe(), h, (int)b.dir));
     }
   if(m.barTime != 0 && m.barTime != g_lastMtfSample)
     {
      g_lastMtfSample = m.barTime;
      g_rec.AddAnalysisSample(SampleOf(g_app.Structure().MtfTimeframe(), m, 0));
     }
  }

SdbAnalysisSample SampleOf(const ENUM_TIMEFRAMES tf, const SdbTfAnalysis &a, const int bias)
  {
   SdbAnalysisSample s;
   s.tf = tf;
   s.barTime = a.barTime;
   s.ready = a.ready;
   s.structDir = (int)a.st.dir;
   s.bosLevel = a.st.bosLevel;
   s.bosTime = a.st.bosTime;
   s.emaDir = (int)a.emaDir;
   s.ema = a.ema;
   s.bias = bias;
   s.recordedAt = TimeCurrent();
   return s;
  }

void RecordZones()
  {
   if(!HarnessRecordZones || g_app == NULL || !g_app.Zones().Ready())
      return;
   datetime t = g_app.Zones().LastBarTime();
   if(t == 0 || t == g_lastZoneSample)
      return;
   g_lastZoneSample = t;
   SdbZone z[];
   SdbZoneSample s;
   s.zones = g_app.Zones().Zones(z);
   s.barTime = t;
   s.map = ZoneMapText(z, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
   s.recordedAt = TimeCurrent();
   g_rec.AddZoneSample(s);
  }

// SC-13: zona valid terbaru ditandai Used (seperti entry spec 13); terbaru agar belum kedaluwarsa saat restart.
void MarkFirstValidZone()
  {
   if(g_zoneMarked || HarnessMarkUsedAtBar <= 0 || g_bar < HarnessMarkUsedAtBar || g_app == NULL)
      return;
   SdbZone z[];
   int n = g_app.Zones().Zones(z), pick = -1;
   for(int i = 0; i < n; i++)
      if(ZoneValid(z[i]) && (pick < 0 || z[i].swingTime > z[pick].swingTime))
         pick = i;
   if(pick >= 0 && g_app.Zones().MarkUsed(z[pick].id))
     {
      g_zoneMarked = true;
      g_rec.NoteMarkedZone(z[pick].id, TimeCurrent());
     }
  }

void HarnessTick()
  {
   if(g_app != NULL)
      g_app.OnTick();
   RecordAnalysis();
   RecordZones();
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
   if(g_app != NULL && HarnessAlertBurstAtBar > 0 && g_bar == HarnessAlertBurstAtBar)
      AlertBurst();
   MarkFirstValidZone();
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
   g_tr.SetPhase("TIMER");
   g_tr.SetCycle(++g_timerCycle);
   g_app.OnTimer();
   g_tr.SetPhase("");
   if(!g_app.RiskState().IsReady())
      return;
   if(g_app.RiskState().IsStopped())
      g_rec.NoteStoppedSample(TimeCurrent(), CountSdbotPositions());
   if(g_withdrawn)
      g_rec.NoteAfterBalanceOp(g_app.RiskState().PeakEquity(), (int)g_app.RiskState().DdLevel());
  }

void OnTradeTransaction(const MqlTradeTransaction &t, const MqlTradeRequest &rq, const MqlTradeResult &rs)
  {
   g_tr.SetPhase("TRADE");
   if(g_app != NULL)
      g_app.OnTradeTransaction(t, rq, rs);
   g_tr.SetPhase("");
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
   CheckScenario(HarnessScenario, g_rec, g_tr);
   TfEndRun();
   g_runStarted = false;
  }
