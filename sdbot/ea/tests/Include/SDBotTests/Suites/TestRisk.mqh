//+------------------------------------------------------------------+
//| TestRisk.mqh — CRiskManager, CRiskMonitor, dan tambahan CExecutor
//| terhadap akun Strategy Tester sungguhan (spec 05, TC-RK-xx). Hanya
//| jalan di tester: membuka dan menutup posisi dengan magic harness.
//| Status risiko memakai prefix GV SDBTEST agar status akun aman.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTRISK_MQH
#define SDB_SUITES_TESTRISK_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/FakeSink.mqh>
#include <SDBot/Risk/RiskManager.mqh>
#include <SDBot/Risk/RiskMonitor.mqh>

#define TRK_PREFIX "SDBTEST"

// Satu set modul risiko untuk simbol tertentu, seperti yang dipasang CSdbApp.
class CTrkRig
  {
public:
   CFakeSink         sink;
   CAccount          acc;
   CState            st;
   CRiskState        rs;
   CExecutor         exe;
   CRiskManager      rm;
   InputValues       inputs;

   bool Setup(const string symbol)
     {
      inputs = DefaultInputValues();
      inputs.magic = SDB_MAGIC_HARNESS;
      string suffix = (StringLen(symbol) > 6) ? StringSubstr(symbol, 6) : "";
      acc.Init(GetPointer(sink), symbol, suffix, false, inputs.magic);
      if(acc.Validate() != SDB_VAL_PASSED || !st.Init(TRK_PREFIX, acc.Login()))
         return false;
      rs.Init(GetPointer(st), inputs.magic, AccountInfoDouble(ACCOUNT_EQUITY), AccountInfoDouble(ACCOUNT_BALANCE), TimeTradeServer());
      exe.Init(inputs.magic, symbol, GetPointer(acc), GetPointer(st), GetPointer(sink), "test");
      return rm.Init(symbol, GetPointer(rs), GetPointer(exe), GetPointer(acc), inputs);
     }
  };

OrderRequest TrkRequest(const string symbol, const bool isBuy, const int slPoints, const double volume)
  {
   MqlTick tick;
   SymbolInfoTick(symbol, tick);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double price = isBuy ? tick.ask : tick.bid;
   double dir = isBuy ? 1.0 : -1.0;
   OrderRequest rq;
   rq.isBuy = isBuy;
   rq.sl = price - dir * slPoints * point;
   rq.tp = price + dir * 2 * slPoints * point;
   rq.volume = volume;
   rq.signalId = SDB_NULL_LONG;
   return rq;
  }

bool TrkRiskOk(CTrkRig &r, const OrderRequest &rq, const double maxPct)
  {
   double p = 0.0;
   if(!OrderCalcProfit(rq.isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, _Symbol, rq.volume,
                       rq.isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID), rq.sl, p))
      return false;
   return -p / AccountInfoDouble(ACCOUNT_BALANCE) * 100.0 <= maxPct + 1e-9;
  }

void RunTestRiskManagerFlags(CTrkRig &r)
  {
   OrderRequest rq = TrkRequest(_Symbol, true, 200, 0.0);
   string stage, detail;
   bool sized = r.rm.CalcVolume(rq, stage, detail);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   AssertTrue("TC-RK-01", "CalcVolume SL 200 point, risiko 0.5%: volume > 0, kelipatan step, risiko <= 0.5% | " + stage + " " + detail,
              sized && rq.volume > 0.0 && MathAbs(rq.volume / step - MathRound(rq.volume / step)) < 1e-6 && TrkRiskOk(r, rq, 0.5));

   r.rs.SetStopped(true);
   bool stopped = !r.rm.PreTradeCheck(rq, stage, detail) && stage == SDB_REJECT_STAGE_STOPPED;
   r.rs.SetStopped(false);
   AssertTrue("TC-RK-02", "STOPPED aktif: ditolak STOPPED", stopped);

   r.rs.TryPauseToday();
   bool paused = !r.rm.PreTradeCheck(rq, stage, detail) && stage == SDB_REJECT_STAGE_DAILY_PAUSE;
   r.st.Set("DAILY_PAUSE", 0.0, true);
   AssertTrue("TC-RK-03", "pause harian aktif: ditolak DAILY_PAUSE", paused);

   OrderRequest big = TrkRequest(_Symbol, true, 200, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX));
   AssertTrue("TC-RK-04", "lot tetap maksimum dengan risiko 0.5%: ditolak RISK_PER_TRADE | " + stage + " " + detail,
              !r.rm.PreTradeCheck(big, stage, detail) && stage == SDB_REJECT_STAGE_RISK_PER_TRADE);

   bool okNormal = r.rm.PreTradeCheck(rq, stage, detail);
   double ml = r.exe.MarginLevelAfter(rq);
   r.rm.SetMarginLevelForTest(150.0);
   bool marginLow = !r.rm.PreTradeCheck(rq, stage, detail) && stage == SDB_REJECT_STAGE_MARGIN_LOW;
   r.rm.SetMarginLevelForTest(-1.0);
   AssertTrue("TC-RK-06", StringFormat("order normal lolos (margin level sesudah %.0f%% > 200); margin 150%% ditolak MARGIN_LOW", ml),
              okNormal && ml > SDB_MARGIN_BLOCK_PCT && marginLow);
   OrderRequest tight = TrkRequest(_Symbol, true, 3, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   double mlTight = r.exe.MarginLevelAfter(tight);
   AssertTrue("TC-RK-06b", StringFormat("SL 3 point tidak membuat margin level 0 (%.0f%%): stop divalidasi executor, bukan cek margin", mlTight),
              mlTight > SDB_MARGIN_BLOCK_PCT);
  }

void RunTestRiskManagerPositions(CTrkRig &r)
  {
   string stage, detail;
   // Posisi A berisiko ~2.8% dan posisi B kecil: risiko terbuka + order 0.5% melewati 3%.
   OrderRequest a = TrkRequest(_Symbol, true, 300, 0.0);
   r.rs.SetLotReduced(false);
   r.rm.CalcVolume(a, stage, detail);
   a.volume = RoundLotDown(a.volume * 2.8 / 0.5, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP));
   OrderResult ra, rb;
   bool openedA = r.exe.OpenMarket(a, ra);
   OrderRequest b = TrkRequest(_Symbol, false, 300, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   bool openedB = r.exe.OpenMarket(b, rb);
   OrderRequest rq = TrkRequest(_Symbol, true, 200, 0.0);
   r.rm.CalcVolume(rq, stage, detail);
   double openPct = r.rm.OpenRiskMoney() / AccountInfoDouble(ACCOUNT_BALANCE) * 100.0;
   AssertTrue("TC-RK-05", StringFormat("risiko terbuka %.2f%% + order 0.5%% > 3%%: ditolak MAX_OPEN_RISK | %s %s", openPct, stage, detail),
              openedA && openedB && !r.rm.PreTradeCheck(rq, stage, detail) && stage == SDB_REJECT_STAGE_MAX_OPEN_RISK);

   CloseAllResult c = r.exe.CloseAllSdbot();
   AssertTrue("TC-RK-08", StringFormat("CloseAllSdbot: total=%d closed=%d failed=%d, posisi SDBot 0", c.total, c.closed, c.failed),
              c.total == 2 && c.closed == 2 && c.failed == 0 && r.rm.CountSdbotPositionsInClass(SDB_CLASS_FOREX_MAJOR) == 0);

   OrderRequest one = TrkRequest(_Symbol, true, 300, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   OrderResult ro;
   r.exe.OpenMarket(one, ro);
   r.inputs.maxPosForexMajor = 1;
   r.rm.Init(_Symbol, GetPointer(r.rs), GetPointer(r.exe), GetPointer(r.acc), r.inputs);
   bool limited = !r.rm.PreTradeCheck(one, stage, detail) && stage == SDB_REJECT_STAGE_CLASS_POSITION_LIMIT;
   r.exe.CloseAllSdbot();
   AssertTrue("TC-RK-10", "1 posisi forex major terbuka, batas major 1: ditolak CLASS_POSITION_LIMIT | " + detail, limited);
  }

void RunTestRiskManagerOtherSymbols()
  {
   string syms[] = {"XAUUSDc", "BTCUSDc"};
   for(int i = 0; i < ArraySize(syms); i++)
     {
      MqlTick t;
      if(!SymbolSelect(syms[i], true) || !SymbolInfoTick(syms[i], t) || t.ask <= 0.0)
        {
         TfInfo("TC-RK-11 dilewati untuk " + syms[i] + ": simbol/harga tidak tersedia di tester");
         continue;
        }
      CTrkRig r;
      bool ready = r.Setup(syms[i]);
      OrderRequest rq = TrkRequest(syms[i], true, 1000, 0.0);
      string stage, detail;
      bool ok = ready && r.rm.CalcVolume(rq, stage, detail);
      double step = SymbolInfoDouble(syms[i], SYMBOL_VOLUME_STEP);
      double p = 0.0;
      bool calc = OrderCalcProfit(ORDER_TYPE_BUY, syms[i], rq.volume, t.ask, rq.sl, p);
      AssertTrue("TC-RK-11", StringFormat("%s CalcVolume SL 1000 point: volume %.2f kelipatan step %.2f, risiko %.3f%% <= 0.5%% | %s %s",
                                          syms[i], rq.volume, step, calc ? -p / AccountInfoDouble(ACCOUNT_BALANCE) * 100.0 : -1.0, stage, detail),
                 (ok && calc && MathAbs(rq.volume / step - MathRound(rq.volume / step)) < 1e-6 &&
                  -p / AccountInfoDouble(ACCOUNT_BALANCE) * 100.0 <= 0.5 + 1e-9) ||
                 (!ok && stage == SDB_REJECT_STAGE_LOT_BELOW_MIN));
     }
  }

bool TrkLogHas(const string text)
  {
   for(int i = 0; i < SdbLogCapturedCount(); i++)
      if(StringFind(SdbLogCaptured(i), text) >= 0)
         return true;
   return false;
  }

SdbAppConfig TrkConfig(CTrkRig &r)
  {
   SdbAppConfig c;
   c.mode = SDB_APP_UNITTEST;
   c.inputs = r.inputs;
   c.dbTarget = SDB_DB_NONE;
   c.resetEmergencyStop = false;
   c.signalsOn = false;
   return c;
  }

void RunTestRiskMonitor(CTrkRig &r)
  {
   // TC-RK-07: reset hanya pada transisi input false -> true (Req 5.5, 5.6).
   r.rs.SetStopped(true);
   r.rs.SetResetInputLastSeen(false);
   r.sink.Reset();
   CRiskMonitor m1;
   m1.Init(_Symbol, r.inputs.magic, GetPointer(r.rs), GetPointer(r.exe), GetPointer(r.sink), TrkConfig(r));
   m1.OnStateReady(true);
   bool reset1 = !r.rs.IsStopped() && r.sink.CountAlertType(SDB_ALERT_TYPE_EMERGENCY_RESET) == 1 &&
                 MathAbs(r.rs.PeakEquity() - AccountInfoDouble(ACCOUNT_EQUITY)) < 1e-6;
   r.rs.SetStopped(true);
   CRiskMonitor m2;
   m2.Init(_Symbol, r.inputs.magic, GetPointer(r.rs), GetPointer(r.exe), GetPointer(r.sink), TrkConfig(r));
   m2.OnStateReady(true);
   bool noReset2 = r.rs.IsStopped() && r.sink.CountAlertType(SDB_ALERT_TYPE_EMERGENCY_RESET) == 1 &&
                   TrkLogHas("InpResetEmergencyStop");
   r.rs.ResetAfterEmergency(AccountInfoDouble(ACCOUNT_EQUITY));
   AssertTrue("TC-RK-07", "reset input false->true saat STOPPED: reset + EMERGENCY_RESET; init berikutnya tetap true: WARN tanpa reset",
              reset1 && noReset2);

   // TC-RK-12: drawdown >= batas stop -> STOPPED, DD_STOP sekali, posisi SDBot ditutup (Req 3.6, 5.1, 5.8).
   OrderRequest rq = TrkRequest(_Symbol, true, 300, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   OrderResult ro;
   r.exe.OpenMarket(rq, ro);
   r.sink.Reset();
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   r.st.Set("PEAK_EQUITY", eq / (1.0 - (r.inputs.ddStopPct + 1.0) / 100.0), true);
   m2.Run();
   m2.Run();
   AssertTrue("TC-RK-12", StringFormat("drawdown %.1f%% >= %.1f%%: STOPPED, DD_STOP sekali, level STOP, posisi SDBot 0",
                                       DrawdownPct(r.rs.PeakEquity(), eq), r.inputs.ddStopPct),
              r.rs.IsStopped() && r.rs.DdLevel() == SDB_DD_STOP && r.sink.CountAlertType(SDB_ALERT_TYPE_DD_STOP) == 1 &&
              r.rm.CountSdbotPositionsInClass(SDB_CLASS_FOREX_MAJOR) == 0);
   r.rs.ResetAfterEmergency(AccountInfoDouble(ACCOUNT_EQUITY));

   // TC-RK-13: rugi harian >= batas -> pause + DAILY_LOSS sekali (Req 4.1).
   r.sink.Reset();
   r.st.Set("DAILY_PAUSE", 0.0, true);
   r.st.Set("DAY_START_BAL", AccountInfoDouble(ACCOUNT_EQUITY) / (1.0 - (r.inputs.dailyLossPct + 0.5) / 100.0), true);
   m2.Run();
   m2.Run();
   bool paused = r.rs.IsDailyPaused() && r.sink.CountAlertType(SDB_ALERT_TYPE_DAILY_LOSS) == 1;
   r.st.Set("DAILY_PAUSE", 0.0, true);
   r.st.Set("DAY_START_BAL", AccountInfoDouble(ACCOUNT_BALANCE), true);
   AssertTrue("TC-RK-13", "rugi harian > batas: pause harian aktif, DAILY_LOSS tepat sekali", paused);
  }

// TC-RK-14 (temuan SC-14 spec 13): lot dari CalcVolume selalu lolos cek risiko per trade PreTradeCheck.
// OrderCalcProfit membulatkan uang ke sen, jadi uang/lot x lot bisa sedikit di bawah rugi volume itu sebenarnya.
void RunTestRiskLotFits(CTrkRig &r)
  {
   int tried = 0, over = 0;
   string first = "";
   for(int b = 0; b < 25; b++)
   for(int sl = 41; sl <= 401; sl += 9)
      for(int dir = 0; dir < 2; dir++)
        {
         r.rm.SetBalanceForTest(9900.0 + b * 7.31);   // SC-14: balance 9973.92, SELL SL 166 pt, 30.04 lot
         OrderRequest rq = TrkRequest(_Symbol, dir == 0, sl, 0.0);
         string stage = "", detail = "";
         if(!r.rm.CalcVolume(rq, stage, detail))
            continue;
         tried++;
         if(!r.rm.PreTradeCheck(rq, stage, detail) && stage == SDB_REJECT_STAGE_RISK_PER_TRADE && over++ == 0)
            first = StringFormat("sl=%d %s %s", sl, dir == 0 ? "BUY" : "SELL", detail);
        }
   r.rm.SetBalanceForTest(0.0);
   AssertTrue("TC-RK-14", StringFormat("%d lot dari CalcVolume, ditolak RISK_PER_TRADE %d %s", tried, over, first), tried > 1000 && over == 0);
  }

// TC-RK-15 (bug: close all saat broker menjawab 10018 dihitung gagal -> Critical CLOSE_ALL_FAILED palsu):
// penolakan pasar tutup dan jeda sesudahnya dihitung closedMarket, bukan failed.
void RunTestRiskCloseAllMarketClosed(CTrkRig &r)
  {
   OrderRequest rq = TrkRequest(_Symbol, true, 300, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   OrderResult ro;
   if(!r.exe.OpenMarket(rq, ro))
     {
      AssertTrue("TC-RK-15", "posisi uji terbuka | " + ro.rejectStage + " " + ro.detail, false);
      return;
     }
   long s0 = r.exe.SendCount();
   r.exe.SetForceRetcodeForTest(TRADE_RETCODE_MARKET_CLOSED);
   CloseAllResult a = r.exe.CloseAllSdbot();
   long sendA = r.exe.SendCount() - s0;
   r.exe.SetForceRetcodeForTest(0);
   long s1 = r.exe.SendCount();
   CloseAllResult b = r.exe.CloseAllSdbot();   // masih dalam jeda 60 detik: tidak dikirim
   long sendB = r.exe.SendCount() - s1;
   r.exe.SetMarketClosedUntilForTest(0);
   CloseAllResult c = r.exe.CloseAllSdbot();
   AssertTrue("TC-RK-15", StringFormat("10018: gagal %d pasar_tutup %d kirim %I64d; jeda: gagal %d pasar_tutup %d kirim %I64d; normal: tutup %d",
                                       a.failed, a.closedMarket, sendA, b.failed, b.closedMarket, sendB, c.closed),
              a.failed == 0 && a.closedMarket == 1 && sendA == 1 && b.failed == 0 && b.closedMarket == 1 && sendB == 0 &&
              c.closed == 1 && c.failed == 0);
  }

// Posisi pembantu di simbol lain (tester mendukung order multi-simbol): magic SDBot lain atau 0 (manual).
bool TrkOpenOther(const string symbol, const long magic, const bool isBuy)
  {
   if(!SymbolSelect(symbol, true))
      return false;
   CTrade t;
   t.SetExpertMagicNumber(magic);
   double vol = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   return isBuy ? t.Buy(vol, symbol) : t.Sell(vol, symbol);
  }

void TrkCloseOther(const long magic)
  {
   CTrade t;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket != 0 && PositionGetInteger(POSITION_MAGIC) == magic)
         t.PositionClose(ticket);
     }
  }

// TC-RK-16..18 (spec 15 Req 1.2, 2.1, 2.2): eksposur dengan posisi nyata di simbol lain.
void RunTestRiskExposure(CTrkRig &r)
  {
   bool opened = TrkOpenOther("GBPUSDc", 2026091902, true) && TrkOpenOther("AUDUSDc", 2026091907, true);
   string stage = "", detail = "";
   OrderRequest buy = TrkRequest(_Symbol, true, 300, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   bool buyOk = r.rm.PreTradeCheck(buy, stage, detail);
   string buyStage = stage, buyDetail = detail;
   OrderRequest sell = TrkRequest(_Symbol, false, 300, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   stage = "";
   r.rm.PreTradeCheck(sell, stage, detail);
   AssertTrue("TC-RK-16", StringFormat("BUY GBPUSD + BUY AUDUSD (SDBot lain): BUY %s %s '%s'; SELL tahap '%s'", _Symbol,
                                       buyStage, buyDetail, stage),
              opened && !buyOk && buyStage == SDB_REJECT_STAGE_CURRENCY_EXPOSURE && buyDetail == "USD short 2/2" &&
              stage != SDB_REJECT_STAGE_CURRENCY_EXPOSURE);

   InputValues tight = r.inputs;
   tight.maxPosForexMajor = 2;
   CRiskManager rm2;
   rm2.Init(_Symbol, GetPointer(r.rs), GetPointer(r.exe), GetPointer(r.acc), tight);
   stage = "";
   rm2.PreTradeCheck(buy, stage, detail);
   AssertTrue("TC-RK-17", "batas forex major 2 dan eksposur penuh: CLASS_POSITION_LIMIT lebih dulu | " + stage + " " + detail,
              stage == SDB_REJECT_STAGE_CLASS_POSITION_LIMIT);
   TrkCloseOther(2026091902);
   TrkCloseOther(2026091907);

   bool manual = TrkOpenOther("GBPUSDc", 0, true) && TrkOpenOther("AUDUSDc", 0, true);
   stage = "";
   r.rm.PreTradeCheck(buy, stage, detail);
   TrkCloseOther(0);
   AssertTrue("TC-RK-18", "posisi manual (magic 0) tidak dihitung eksposur | tahap '" + stage + "'",
              manual && stage != SDB_REJECT_STAGE_CURRENCY_EXPOSURE);
  }

void RunTestRisk()
  {
   TfBeginSuite("Risk");
   if(!MQLInfoInteger(MQL_TESTER))
     {
      TfInfo("suite Risk dilewati: hanya di Strategy Tester (membuka posisi)");
      TfEndSuite();
      return;
     }
   string prefix = TRK_PREFIX + "_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "_";
   GlobalVariablesDeleteAll(prefix);
   SdbLogCaptureStart();
   CTrkRig r;
   if(!r.Setup(_Symbol))
      AssertTrue("TC-RK-00", "rig risiko siap (akun tester lolos validasi)", false);
   else
     {
      RunTestRiskManagerFlags(r);
      RunTestRiskLotFits(r);
      RunTestRiskCloseAllMarketClosed(r);
      RunTestRiskExposure(r);
      RunTestRiskManagerPositions(r);
      RunTestRiskMonitor(r);
      RunTestRiskManagerOtherSymbols();
     }
   SdbLogCaptureStop();
   GlobalVariablesDeleteAll(prefix);
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTRISK_MQH
