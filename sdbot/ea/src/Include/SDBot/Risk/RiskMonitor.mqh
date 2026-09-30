//+------------------------------------------------------------------+
//| RiskMonitor.mqh — CRiskMonitor: pemantauan risiko tiap detik dari
//| CSdbApp::OnTimer, terpisah dari entry (spec 05 Req 3–7, design §4.4):
//| operasi saldo, pergantian hari, puncak equity, drawdown, rugi harian,
//| margin, dan close all saat STOPPED. Keputusan tingkat akun diambil
//| pemenang compare-and-set di CRiskState, jadi alert tidak ganda antar-instance.
//+------------------------------------------------------------------+
#ifndef SDB_RISK_RISKMONITOR_MQH
#define SDB_RISK_RISKMONITOR_MQH

#include <SDBot/Core/InputRules.mqh>
#include <SDBot/Core/EventSink.mqh>
#include <SDBot/Execution/Executor.mqh>
#include <SDBot/Risk/RiskState.mqh>

class CRiskMonitor
  {
private:
   string            m_symbol;
   long              m_magic;
   CRiskState       *m_rs;
   CExecutor        *m_exe;
   ISdbEventSink    *m_sink;
   CNullSink         m_nullSink;
   InputValues       m_in;
   bool              m_live;          // bukan tester: STATE_RESET hanya relevan di akun sungguhan
   bool              m_ready;
   datetime          m_lastBalScan;
   datetime          m_lastCloseTry;
   bool              m_lastMarketOpen;
   int               m_closeFails;    // gagal berturut-turut instance ini saat pasar buka

   void Alert(const string type, const ENUM_SDB_SEVERITY sev, const string message)
     {
      AlertEvent a;
      a.type = type;
      a.severity = sev;
      a.message = message;
      a.symbol = m_symbol;
      a.magic = m_magic;
      a.time = TimeCurrent();
      m_sink.OnAlert(a);
      if(sev >= SDB_SEV_HIGH)
         LogWarn("Risk", type + " | " + message);
      else
         LogInfo("Risk", type + " | " + message);
     }

   bool HasSdbotHistory()
     {
      if(!HistorySelect(0, TimeCurrent() + 60))
         return false;
      for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
         if(IsSdbotMagic(HistoryDealGetInteger(HistoryDealGetTicket(i), DEAL_MAGIC)))
            return true;
      return false;
     }

   // Req 7.5: status baru -> operasi saldo yang sudah ada dianggap diproses.
   void BalanceBaseline()
     {
      ulong last = 0;
      datetime lastTime = 0;
      if(HistorySelect(0, TimeCurrent() + 60))
         for(int i = 0; i < HistoryDealsTotal(); i++)
           {
            ulong d = HistoryDealGetTicket(i);
            if(BalanceOpType(HistoryDealGetInteger(d, DEAL_TYPE)) != "" && d > last)
              {
               last = d;
               lastTime = (datetime)HistoryDealGetInteger(d, DEAL_TIME);
              }
           }
      m_rs.SetBalanceBaseline(last, lastTime);
     }

   // Req 5.5–5.7: reset hanya pada transisi input false -> true, hanya saat STOPPED.
   void ApplyResetInput(const bool resetInput)
     {
      bool lastSeen = m_rs.ResetInputLastSeen();
      if(ResetRequested(resetInput, lastSeen))
        {
         if(m_rs.IsStopped())
           {
            double eq = AccountInfoDouble(ACCOUNT_EQUITY);
            m_rs.ResetAfterEmergency(eq);
            Alert(SDB_ALERT_TYPE_EMERGENCY_RESET, SDB_SEV_INFO,
                  StringFormat("Emergency stop dibuka manual; puncak equity = %.2f", eq));
           }
         else
            LogInfo("Risk", "InpResetEmergencyStop = true tetapi STOPPED tidak aktif; tidak ada yang direset");
        }
      else if(resetInput && lastSeen)
         LogWarn("Risk", "InpResetEmergencyStop masih true dari init sebelumnya: tidak mereset lagi, kembalikan ke false");
      m_rs.SetResetInputLastSeen(resetInput);
     }

   // Req 7.1–7.4: operasi saldo baru, berurutan, tepat sekali per akun.
   void ScanBalanceOps(const bool force)
     {
      datetime now = TimeLocal();
      if(!force && now - m_lastBalScan < SDB_BALANCE_SCAN_SEC)
         return;
      m_lastBalScan = now;
      datetime from = m_rs.LastBalanceTime();
      if(!HistorySelect(from > 86400 ? from - 86400 : 0, TimeCurrent() + 60))
        {
         LogThrottled(SDB_LOG_ERROR, "risk_hist", SDB_LOG_THROTTLE_DEFAULT_SEC, "Risk", "HistorySelect gagal | " + ErrText(GetLastError()));
         return;
        }
      for(int i = 0; i < HistoryDealsTotal(); i++)
        {
         ulong d = HistoryDealGetTicket(i);
         string type = BalanceOpType(HistoryDealGetInteger(d, DEAL_TYPE));
         ulong lastSeen = m_rs.LastBalanceDeal();
         if(type == "" || d <= lastSeen || !m_rs.TryClaimBalanceDeal(lastSeen, d))
            continue;
         double amount = HistoryDealGetDouble(d, DEAL_PROFIT);
         datetime t = (datetime)HistoryDealGetInteger(d, DEAL_TIME);
         m_rs.AdjustPeakAndDayStart(amount);
         m_rs.SetLastBalanceTime(t);
         BalanceOpRecord b;
         b.dealTicket = (long)d;
         b.time = t;
         b.opType = type;
         b.amount = amount;
         b.comment = HistoryDealGetString(d, DEAL_COMMENT);
         m_sink.OnBalanceOp(b);
         Alert(SDB_ALERT_TYPE_BALANCE_OP, SDB_SEV_INFO,
               StringFormat("Operasi saldo %s %.2f; puncak %.2f, awal hari %.2f", type, amount, m_rs.PeakEquity(), m_rs.DayStartBalance()));
        }
     }

   void CheckNewDay()
     {
      datetime stored = m_rs.DayStartDate();
      datetime now = TimeTradeServer();
      if(IsNewServerDay(stored, now) && m_rs.TryClaimNewDay(stored, ServerDayStart(now), AccountInfoDouble(ACCOUNT_BALANCE)))
         LogInfo("Risk", StringFormat("hari server baru %s, balance awal hari %.2f, pause harian dicabut",
                                      TimeToString(ServerDayStart(now), TIME_DATE), m_rs.DayStartBalance()));
     }

   // Req 3.3–3.6, 3.9: transisi level lewat CAS; STOPPED disetel siapa pun yang melihat batas.
   void CheckDrawdown(const double equity)
     {
      double peak = m_rs.PeakEquity();
      double dd = DrawdownPct(peak, equity);
      ENUM_SDB_DD_LEVEL cur = m_rs.DdLevel();
      ENUM_SDB_DD_LEVEL next = DrawdownLevel(dd, cur, SDB_DD_INFO_PCT, m_in.ddReducePct, DdRecoverPct(m_in.ddReducePct), m_in.ddStopPct);
      if(next == SDB_DD_STOP && !m_rs.IsStopped())
         m_rs.SetStopped(true);
      if(next == cur || !m_rs.TryMoveDdLevel(cur, next))
         return;
      string d = StringFormat("drawdown %.2f%% (puncak %.2f, equity %.2f)", dd, peak, equity);
      if(next == SDB_DD_STOP)
        {
         m_lastCloseTry = 0;
         Alert(SDB_ALERT_TYPE_DD_STOP, SDB_SEV_CRITICAL, "EMERGENCY STOP: " + d + ", semua posisi SDBot ditutup");
        }
      else if(next == SDB_DD_REDUCE)
        {
         m_rs.SetLotReduced(true);
         Alert(SDB_ALERT_TYPE_DD_REDUCE, SDB_SEV_HIGH, "Lot x 0.5: " + d);
        }
      else if(cur == SDB_DD_REDUCE)
        {
         m_rs.SetLotReduced(false);
         Alert(SDB_ALERT_TYPE_DD_RECOVERED, SDB_SEV_INFO, "Lot normal kembali: " + d);
        }
      else if(next == SDB_DD_INFO && cur == SDB_DD_NORMAL)
         Alert(SDB_ALERT_TYPE_DD_INFO, SDB_SEV_INFO, d);
     }

   void CheckDailyLoss(const double equity)
     {
      double loss = DailyLossPct(m_rs.DayStartBalance(), equity);
      if(loss >= m_in.dailyLossPct - SDB_RISK_EPS && !m_rs.IsDailyPaused() && m_rs.TryPauseToday())
         Alert(SDB_ALERT_TYPE_DAILY_LOSS, SDB_SEV_HIGH,
               StringFormat("Rugi harian %.2f%% >= %.2f%%: entry dijeda sampai hari server berikutnya", loss, m_in.dailyLossPct));
     }

   void CheckMargin()
     {
      double ml = EffectiveMarginLevel(AccountInfoDouble(ACCOUNT_MARGIN_LEVEL), AccountInfoDouble(ACCOUNT_MARGIN));
      if(ml < SDB_MARGIN_ALERT_PCT)
        {
         if(m_rs.TryMarginAlert(true))
            Alert(SDB_ALERT_TYPE_MARGIN_LOW, SDB_SEV_HIGH, StringFormat("Margin level %.0f%% < %.0f%%", ml, SDB_MARGIN_ALERT_PCT));
        }
      else if(m_rs.TryMarginAlert(false))
         Alert(SDB_ALERT_TYPE_MARGIN_OK, SDB_SEV_INFO, StringFormat("Margin level pulih >= %.0f%%", SDB_MARGIN_ALERT_PCT));
     }

   // Req 5.1–5.3: jadwal 5 detik (pasar buka) / 60 detik (tutup); alert Critical dedupe lewat GV.
   void CloseAllIfStopped()
     {
      if(!m_rs.IsStopped())
        {
         m_closeFails = 0;
         return;
        }
      bool any = false, open = false;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         if(PositionGetTicket(i) == 0 || !IsSdbotMagic(PositionGetInteger(POSITION_MAGIC)))
            continue;
         any = true;
         if(m_exe.CloseAllowedNow(PositionGetString(POSITION_SYMBOL)))
            open = true;
        }
      if(!any)
        {
         m_closeFails = 0;
         return;
        }
      if(open && !m_lastMarketOpen)
         m_lastCloseTry = 0;   // pasar baru buka: coba di siklus ini (5.2)
      m_lastMarketOpen = open;
      datetime now = TimeLocal();
      if(!CloseAllDue(now, m_lastCloseTry, open))
         return;
      m_lastCloseTry = now;
      CloseAllResult r = m_exe.CloseAllSdbot();
      if(r.failed > 0)
         m_closeFails++;
      else if(r.closedMarket == 0)
         m_closeFails = 0;
      datetime lastAlert = m_rs.CloseAllAlertAt();
      if(CloseAllAlertDue(m_closeFails, now, lastAlert) && m_rs.TryClaimCloseAllAlert(lastAlert, now))
         Alert(SDB_ALERT_TYPE_CLOSE_ALL_FAILED, SDB_SEV_CRITICAL,
               StringFormat("Close all gagal %d kali berturut-turut; %d posisi SDBot masih terbuka", m_closeFails, r.failed));
     }

public:
                     CRiskMonitor(void) : m_magic(0), m_rs(NULL), m_exe(NULL), m_sink(NULL), m_live(false), m_ready(false),
                     m_lastBalScan(0), m_lastCloseTry(0), m_lastMarketOpen(false), m_closeFails(0) {}

   bool Init(const string symbol, const long magic, CRiskState *rs, CExecutor *exe, ISdbEventSink *sink, const SdbAppConfig &cfg)
     {
      m_symbol = symbol;
      m_magic = magic;
      m_rs = rs;
      m_exe = exe;
      m_sink = (sink == NULL) ? GetPointer(m_nullSink) : sink;
      m_in = cfg.inputs;
      m_live = !(bool)MQLInfoInteger(MQL_TESTER);
      m_ready = false;
      m_closeFails = 0;
      m_lastCloseTry = 0;
      return rs != NULL && exe != NULL;
     }

   // Sekali saat status bersama siap (design §4.4).
   void OnStateReady(const bool resetInput)
     {
      if(m_rs == NULL || !m_rs.IsReady())
         return;
      m_ready = true;
      if(m_rs.WasFresh() && m_live && HasSdbotHistory())
         Alert(SDB_ALERT_TYPE_STATE_RESET, SDB_SEV_HIGH,
               "Status risiko bersama (GV) hilang padahal akun punya riwayat SDBot: puncak equity, STOPPED, dan pause dimulai ulang");
      if(m_rs.BalanceBaselineNeeded())
         BalanceBaseline();
      ApplyResetInput(resetInput);
      ScanBalanceOps(true);
     }

   // Tiap detik dari CSdbApp::OnTimer, sebelum snapshot dan flush (Req 3.1).
   void Run()
     {
      if(!m_ready)
         return;
      ScanBalanceOps(false);
      CheckNewDay();
      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      m_rs.RaisePeak(equity);
      CheckDrawdown(equity);
      CheckDailyLoss(equity);
      CheckMargin();
      CloseAllIfStopped();
     }
  };

#endif // SDB_RISK_RISKMONITOR_MQH
