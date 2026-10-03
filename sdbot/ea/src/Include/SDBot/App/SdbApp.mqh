//+------------------------------------------------------------------+
//| SdbApp.mqh — CSdbApp: orkestrasi event yang dipakai bersama EA
//| utama, harness, dan suite TestApp (spec 04 Req 6, design §4.4–4.5).
//| Konfigurasi masuk lewat SdbAppConfig, bukan input global. Semua
//| modul adalah member (tanpa new), jadi OnDeinit cukup menutup urutan.
//+------------------------------------------------------------------+
#ifndef SDB_APP_SDBAPP_MQH
#define SDB_APP_SDBAPP_MQH

#include <SDBot/Core/Inputs.mqh>
#include <SDBot/Core/State.mqh>
#include <SDBot/Account/Account.mqh>
#include <SDBot/Storage/Logger.mqh>
#include <SDBot/Execution/Executor.mqh>
#include <SDBot/Risk/RiskManager.mqh>
#include <SDBot/Risk/RiskMonitor.mqh>
#include <SDBot/Position/PositionManager.mqh>
#include <SDBot/Position/ClosureTracker.mqh>
#include <SDBot/Position/Reconciler.mqh>
#include <SDBot/Analysis/MarketStructure.mqh>
#include <SDBot/Analysis/ZoneBook.mqh>
#include <SDBot/Strategies/PaTrigger.mqh>
#include <SDBot/Signals/SignalEngine.mqh>
#include <SDBot/App/TeeSink.mqh>
#include <SDBot/Notify/Notifier.mqh>
#include <SDBot/Notify/TelegramTransport.mqh>
#include <SDBot/App/TesterMetric.mqh>

#define SDB_GV_PREFIX_UNITTEST "SDBTEST"

class CSdbApp : public ISdbStatusSource
  {
private:
   SdbAppConfig      m_cfg;
   CLogger           m_logger;
   CTeeSink          m_tee;
   ISdbEventSink    *m_sink;          // tee(Logger, Notifier, observer harness/uji)
   CNotifier         m_notifier;
   CLogTransport     m_logTransport;   // tester dan live tanpa token (spec 08 Req 7.1, spec 09 Req 1.2)
   CTelegramTransport m_telegram;      // live dengan token (spec 09)
   CPushSender       m_pushSender;     // live
   CLogPush          m_logPush;        // tester: tanpa SendNotification (spec 09 Req 2.7)
   bool              m_startSent;
   ISdbTransport    *m_transport;
   bool              m_notifyOn;       // false tanpa DB (optimasi, Req 7.2)
   CAccount          m_account;
   CState            m_state;
   CExecutor         m_executor;
   CRiskState        m_riskState;
   CRiskManager      m_riskManager;
   CRiskMonitor      m_riskMonitor;
   bool              m_riskReady;
   CPositionCache    m_posCache;
   CPositionManager  m_posManager;
   CMarketStructure  m_structure;      // bias HTF + struktur MTF (spec 10)
   CZoneBook         m_zones;          // zona S&D MTF (spec 11)
   CPaTrigger        m_trigger;        // pola candle LTF (spec 12)
   CSignalEngine     m_signals;        // pipeline sinyal dan entry (spec 13)
   CClosureTracker   m_closureTracker;
   CReconciler       m_reconciler;
   int               m_atrHandle;      // ATR trailing di LTF gaya trading (spec 06 Req 4.3)
   bool              m_storageOpened;
   bool              m_stateReady;
   bool              m_timerSet;
   bool              m_deinitDone;
   datetime          m_lastSnapshot;
   datetime          m_lastTouch;

   // CState butuh login; bila akun masih PENDING, dicoba lagi dari timer.
   void EnsureState()
     {
      if(m_stateReady || m_account.State() != SDB_VAL_PASSED)
         return;
      string prefix = (m_cfg.mode == SDB_APP_UNITTEST) ? SDB_GV_PREFIX_UNITTEST : SDB_GV_PREFIX;
      m_stateReady = m_state.Init(prefix, m_account.Login());
      m_lastSnapshot = TimeLocal();   // Validate() baru saja mengirim snapshot
      if(!m_stateReady)
         return;
      m_zones.SetState(GetPointer(m_state));   // penanda Used zona di GV per magic (spec 11 Req 3.3)
      m_signals.SetState(GetPointer(m_state), m_account.Login(), m_logger.RunKey());   // penanda bar + ID sinyal (spec 13)
      if(m_notifyOn)
        {
         m_notifier.SetState(GetPointer(m_state));   // cooldown, kuota, lease, jadwal di GV (spec 08 Req 2.5, spec 09 Req 4)
         m_notifier.SetContext(NotifyContext());
         m_telegram.SetState(GetPointer(m_state));   // jarak kirim Telegram bersama (spec 09 Req 2.5)
        }
      // Status risiko bersama (spec 05): baseline, reset input, operasi saldo tertunda, lalu snapshot
      // langsung dengan puncak yang benar (Req 3.8), karena snapshot Validate() dibuat sebelum puncak diketahui.
      m_riskReady = m_riskState.Init(GetPointer(m_state), m_cfg.inputs.magic, AccountInfoDouble(ACCOUNT_EQUITY),
                                     AccountInfoDouble(ACCOUNT_BALANCE), TimeTradeServer());
      if(m_riskReady)
        {
         m_riskMonitor.OnStateReady(m_cfg.resetEmergencyStop);
         SendSnapshot();
        }
      m_reconciler.Run();   // spec 06 Req 7.1, 7.2: butuh GV LAST_DEAL per magic dari status bersama
     }

   // Modul posisi (spec 06 design §4.8). Handle ATR dibuat sekali di init, dilepas di OnDeinit.
   bool InitPositions(const SdbAppConfig &cfg)
     {
      ENUM_TIMEFRAMES htf, mtf, ltf;
      StyleTimeframes(cfg.style, htf, mtf, ltf);
      m_atrHandle = iATR(_Symbol, ltf, cfg.inputs.trailAtrPeriod);
      if(m_atrHandle == INVALID_HANDLE)
        {
         LogCritical("App", "handle ATR trailing tidak bisa dibuat | " + ErrText(GetLastError()));
         return false;
        }
      m_posCache.Init(cfg.inputs.magic, _Symbol, m_sink);
      m_posManager.Init(_Symbol, cfg.inputs.magic, cfg.inputs, ltf, m_atrHandle, GetPointer(m_executor), GetPointer(m_account),
                        GetPointer(m_posCache), m_sink);
      m_closureTracker.Init(cfg.inputs.magic, _Symbol, GetPointer(m_posCache), GetPointer(m_state), m_sink,
                            cfg.inputs.breakevenBufferPoints);
      m_reconciler.Init(cfg.inputs.magic, _Symbol, GetPointer(m_posCache), GetPointer(m_closureTracker), m_sink, cfg.eaVersion);
      return true;
     }

   // Analisis struktur dari input gaya trading, bukan timeframe chart (spec 10 Req 1.4).
   void InitAnalysis(const SdbAppConfig &cfg)
     {
      ENUM_TIMEFRAMES htf, mtf, ltf;
      StyleTimeframes(cfg.style, htf, mtf, ltf);
      SdbStructureParams p;
      p.strength = cfg.inputs.swingStrength;
      p.lookback = cfg.inputs.structureLookback;
      p.emaPeriod = cfg.inputs.emaPeriod;
      p.slopeBars = cfg.inputs.emaSlopeBars;
      m_structure.Init(_Symbol, htf, mtf, p);
      SdbZoneParams zp;
      zp.minWidthAtr = cfg.inputs.zoneMinWidthAtr;
      zp.maxWidthAtr = cfg.inputs.zoneMaxWidthAtr;
      zp.minLegAtr = cfg.inputs.zoneMinLegAtr;
      zp.legBars = cfg.inputs.zoneLegBars;
      zp.maxAge = cfg.inputs.maxZoneAgeBars;
      zp.strength = cfg.inputs.swingStrength;
      m_zones.Init(_Symbol, mtf, zp, cfg.inputs.magic);
      m_trigger.Init(_Symbol, ltf);
      SdbSignalParams sp;
      sp.minScorePct = cfg.inputs.minConfluenceScore;
      sp.minRR = cfg.inputs.minRR;
      sp.slBufferAtr = cfg.inputs.slBufferAtr;
      sp.minSlAtr = cfg.inputs.minSlAtr;
      sp.maxSlAtr = cfg.inputs.maxSlAtr;
      m_signals.Init(_Symbol, cfg.inputs.magic, ltf, sp, GetPointer(m_structure), GetPointer(m_zones), GetPointer(m_trigger),
                     GetPointer(m_riskState), GetPointer(m_riskManager), GetPointer(m_executor), GetPointer(m_account), m_sink,
                     cfg.style);
     }

   void SendSnapshot()
     {
      AccountSnapshot s = m_account.Snapshot();
      if(m_riskReady)
         s.peakEquity = m_riskState.PeakEquity();
      m_sink.OnAccount(s);
      m_lastSnapshot = TimeLocal();
     }

   // Nama GV run_key tester: tester mengosongkan GV di setiap run, jadi GV ini menandai run yang
   // sedang jalan dan bertahan saat restart harness (spec 04, PC-08).
   string RunKeyGvName(const long login) const
     {
      string prefix = (m_cfg.mode == SDB_APP_UNITTEST) ? SDB_GV_PREFIX_UNITTEST : SDB_GV_PREFIX;
      return prefix + "_" + IntegerToString(login) + "_" + SDB_GV_RUN_KEY;
     }

   // Live: 0 (posisi unik per login lintas restart). Tester: run_key run ini, atau NEW di init pertama.
   long RunKeyFor(const long login) const
     {
      if(m_cfg.dbTarget == SDB_DB_LIVE)
         return SDB_RUN_KEY_LIVE;
      string gv = RunKeyGvName(login);
      return GlobalVariableCheck(gv) ? (long)GlobalVariableGet(gv) : SDB_RUN_KEY_NEW;
     }

   // Penanda pesan (spec 08 Req 4.1): TESTER di Strategy Tester agar tidak tertukar dengan akun sungguhan.
   SdbNtContext NotifyContext() const
     {
      SdbNtContext c;
      c.login = AccountInfoInteger(ACCOUNT_LOGIN);
      c.symbol = _Symbol;
      c.eaVersion = m_cfg.eaVersion;
      c.currency = AccountInfoString(ACCOUNT_CURRENCY);
      c.digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      c.accountTag = MQLInfoInteger(MQL_TESTER) ? "TESTER"
                     : SdbAccountTypeText(AccountTypeOf((ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE), c.currency));
      return c;
     }

   // Tee = Logger (+ Notifier) (+ observer). Notifier dipasang sebelum Logger.Open agar alert migrasi ikut
   // terkirim, dan Logger mengirim alertnya sendiri lewat tee (spec 08 design §3.8).
   void BuildSinks(ISdbEventSink *observer)
     {
      string keyPrefix = StringFormat("%I64d-%I64d-%u", m_cfg.inputs.magic, (long)TimeLocal(), GetTickCount() % 100000);
      m_tee.Clear();
      m_tee.Add(GetPointer(m_logger));
      m_notifyOn = (m_cfg.dbTarget != SDB_DB_NONE);
      if(m_notifyOn)
        {
         m_notifier.Init(GetPointer(m_logger), m_transport, NotifyContext());
         m_notifier.SetKeyPrefix(keyPrefix);
         m_notifier.SetPush(MQLInfoInteger(MQL_TESTER) ? (ISdbPush *)GetPointer(m_logPush) : (ISdbPush *)GetPointer(m_pushSender));
         m_notifier.SetStatusSource(GetPointer(this));
         m_notifier.SetSchedule(m_cfg.inputs.heartbeatMinutes, m_cfg.inputs.magic);
         m_tee.Add(GetPointer(m_notifier));
        }
      if(observer != NULL)
         m_tee.Add(observer);
      m_tee.SetKeyPrefix(keyPrefix);
      m_logger.SetRouter(GetPointer(m_tee));
      m_sink = GetPointer(m_tee);
     }

   void OpenStorage(ISdbEventSink *observer)
     {
      m_logger.Init(NULL, _Symbol, m_cfg.inputs.magic, m_cfg.eaVersion);
      BuildSinks(observer);
      m_logger.Open(m_cfg.dbTarget);   // gagal buka tidak menggagalkan init (spec 03 Req 2.2)
      m_storageOpened = true;
      bool tester = (bool)MQLInfoInteger(MQL_TESTER);
      SessionInfo s;
      s.login = AccountInfoInteger(ACCOUNT_LOGIN);
      s.runKey = RunKeyFor(s.login);
      s.magic = m_cfg.inputs.magic;
      s.symbol = _Symbol;
      s.mode = tester ? SDB_SESSION_MODE_TESTER : SDB_SESSION_MODE_LIVE;
      s.eaVersion = m_cfg.eaVersion;
      s.inputsJson = m_cfg.inputsJson;
      s.startedAt = TimeCurrent();
      s.testerFrom = tester ? TimeCurrent() : 0;
      s.testerTo = 0;
      s.testerModel = "";
      m_logger.BeginSession(s);
      if(s.runKey == SDB_RUN_KEY_NEW && m_logger.RunKey() > 0)
         GlobalVariableSet(RunKeyGvName(s.login), (double)m_logger.RunKey());
      RequeuePending();
     }

   // Uji > Strategy Tester / token kosong (log) > Telegram (spec 09 Req 1.2, 2.7).
   ISdbTransport *ChooseTransport(const SdbAppConfig &cfg, ISdbTransport *injected)
     {
      if(injected != NULL)
         return injected;
      if(MQLInfoInteger(MQL_TESTER))
         return GetPointer(m_logTransport);
      if(cfg.telegramToken == "" || cfg.telegramChatId == "")
        {
         LogWarn("App", "InpTelegramToken / InpTelegramChatID kosong: notifikasi hanya di log Experts (isi lewat *.local.set)");
         return GetPointer(m_logTransport);
        }
      m_telegram.Init(cfg.telegramToken, cfg.telegramChatId, NULL);
      return GetPointer(m_telegram);
     }

   string ValidationText() const
     {
      switch(m_account.State())
        {
         case SDB_VAL_PASSED:   return "PASSED";
         case SDB_VAL_REJECTED: return "REJECTED";
         default:               return "PENDING";
        }
     }

   // Pesan start dengan akhir sesi lalu (spec 09 Req 7.1).
   void SendStart(const SdbAppConfig &cfg)
     {
      if(!m_notifyOn)
         return;
      SdbStartInfo s;
      s.magic = cfg.inputs.magic;
      s.presetTag = cfg.presetTag;
      s.validation = ValidationText();
      s.hasPrevious = m_logger.PreviousSessionEnd(s.previousEndedAt, s.previousReason, s.previousAbnormal);
      m_notifier.SendStart(s);
      m_startSent = true;
     }

   // Pesan instance dari sesi lalu (spec 08 Req 6.1, 6.2): Critical muda dikirim ulang.
   void RequeuePending()
     {
      if(!m_notifyOn)
         return;
      AlertEvent back[];
      int n = m_logger.TakeRestartAlerts((long)TimeGMT(), back);
      for(int i = 0; i < n; i++)
         m_notifier.Requeue(back[i]);
      if(n > 0)
         LogInfo("App", IntegerToString(n) + " alert Critical dari sesi lalu diantrekan ulang");
     }

public:
                     CSdbApp(void) : m_sink(NULL), m_transport(NULL), m_notifyOn(false), m_startSent(false), m_riskReady(false), m_atrHandle(INVALID_HANDLE), m_storageOpened(false), m_stateReady(false), m_timerSet(false),
                     m_deinitDone(false), m_lastSnapshot(0), m_lastTouch(0) {}

   // Urutan init (Req 6.1). observer: perekam harness / sink uji, menerima event di samping Logger.
   // Ganti timeframe/simbol chart memanggil OnDeinit lalu OnInit pada objek global yang sama.
   int OnInit(const SdbAppConfig &cfg, ISdbEventSink *observer = NULL, ISdbTransport *transport = NULL)
     {
      m_sink = NULL;
      m_transport = ChooseTransport(cfg, transport);
      m_startSent = false;
      m_notifyOn = false;
      m_riskReady = false;
      m_storageOpened = false;
      m_stateReady = false;
      m_timerSet = false;
      m_deinitDone = false;
      m_lastSnapshot = 0;
      m_lastTouch = 0;
      m_cfg = cfg;
      SdbSetLogLevel(cfg.logLevel);
      string errors;
      if(!ValidateInputValues(cfg.inputs, cfg.mode == SDB_APP_HARNESS, errors))
        {
         LogCritical("App", "input tidak valid | " + errors);
         return INIT_PARAMETERS_INCORRECT;
        }
      OpenStorage(observer);
      if(!PresetMatchesSymbol(cfg.presetTag, _Symbol))
         LogWarn("App", "preset " + cfg.presetTag + " dimuat di chart " + _Symbol + ": magic dan setelan mungkin milik simbol lain");
      m_account.Init(m_sink, _Symbol, cfg.symbolSuffix, cfg.allowLive, cfg.inputs.magic);
      if(m_account.Validate() == SDB_VAL_REJECTED)
         return INIT_FAILED;   // OnDeinit(REASON_INITFAILED) menutup sesi dan menyimpan alert
      m_executor.Init(cfg.inputs.magic, _Symbol, GetPointer(m_account), GetPointer(m_state), m_sink, cfg.eaVersion);
      // Langkah 6 (spec 05): modul risiko dipasang sebelum status bersama agar OnStateReady bisa jalan.
      m_riskManager.Init(_Symbol, GetPointer(m_riskState), GetPointer(m_executor), GetPointer(m_account), cfg.inputs);
      m_riskMonitor.Init(_Symbol, cfg.inputs.magic, GetPointer(m_riskState), GetPointer(m_executor), m_sink, cfg);
      if(!InitPositions(cfg))
         return INIT_FAILED;
      InitAnalysis(cfg);
      EnsureState();
      if(!EventSetTimer(SDB_TIMER_SEC))
        {
         LogCritical("App", "timer tidak bisa dipasang | " + ErrText(GetLastError()));
         return INIT_FAILED;
        }
      m_timerSet = true;
      SendStart(cfg);
      LogInfo("App", "SDBot v" + cfg.eaVersion + " aktif | magic=" + IntegerToString(cfg.inputs.magic) +
              " mode=" + EnumToString(cfg.mode) + " style=" + EnumToString(cfg.style) +
              " validasi=" + EnumToString(m_account.State()) + " db=" + (m_logger.IsWritable() ? "ok" : "tidak ada"));
      return INIT_SUCCEEDED;
     }

   // Manajemen posisi per tick (spec 06); sampai akun lolos dan status siap, tick diabaikan.
   void OnTick()
     {
      if(m_deinitDone)
         return;
      m_structure.OnTick();   // hanya membaca harga: jalan walau akun belum PASSED (spec 10 design §8.3)
      m_zones.OnTick();       // penanda Used baru terbaca setelah status bersama siap (spec 11)
      m_trigger.OnTick();     // pola bar LTF tertutup untuk kedua arah (spec 12)
      if(m_account.State() != SDB_VAL_PASSED || !m_stateReady)
         return;
      if(m_cfg.signalsOn && m_riskReady)
         m_signals.OnTick();  // setelah analisis bar yang sama; sebelum manajemen posisi (spec 13 Req 1.1)
      m_posManager.OnTick();
     }

   // Akun → state → risk monitor (spec 05 Req 3.1) → snapshot → touch GV → flush (spec 04 Req 6.3, 6.5).
   void OnTimer()
     {
      if(!m_storageOpened || m_deinitDone)
         return;
      m_account.OnTimer();
      if(m_account.RejectedFromTimer())
        {
         LogCritical("App", "validasi akun tertunda ditolak, EA dilepas dari chart | " + m_account.LastReason());
         m_logger.Flush();
         if(m_cfg.mode != SDB_APP_UNITTEST)
            ExpertRemove();
         return;
        }
      EnsureState();
      if(m_riskReady)
         m_riskMonitor.Run();
      if(m_account.State() == SDB_VAL_PASSED && TimeLocal() - m_lastSnapshot >= SDB_ACCOUNT_SNAPSHOT_SEC)
         SendSnapshot();
      if(m_stateReady && TimeLocal() - m_lastTouch >= SDB_GV_TOUCH_SEC)
        {
         m_state.TouchAll();
         m_lastTouch = TimeLocal();
        }
      if(m_notifyOn)
         m_notifier.OnTimer();   // setelah risk monitor, sebelum flush agar status kirim ikut tersimpan (Req 3.3)
      m_logger.Flush();
     }

   // Deal dan closure posisi instance (spec 06 Req 6); sebelum status siap, rekonsiliasi yang menangkapnya.
   void OnTradeTransaction(const MqlTradeTransaction &t, const MqlTradeRequest &rq, const MqlTradeResult &rs)
     {
      if(m_stateReady && !m_deinitDone)
         m_closureTracker.OnTransaction(t);
     }

   // Metrik optimasi PRD (spec 07 Req 1): expectancy R per trade / max DD relatif equity.
   double OnTester()
     {
      return TesterMetric(m_closureTracker.TotalR(), m_closureTracker.TradesWithR(),
                          TesterStatistics(STAT_EQUITY_DDREL_PERCENT), SDB_TESTER_MIN_TRADES);
     }

   // Aman dipanggil dua kali dan setelah init gagal (Req 6.2, 6.4).
   void OnDeinit(const int reason)
     {
      if(m_deinitDone)
         return;
      m_deinitDone = true;
      if(m_timerSet)
         EventKillTimer();
      m_timerSet = false;
      LogInfo("App", "SDBot berhenti | reason=" + IntegerToString(reason) + " (" + SdbDeinitReasonText(reason) + ")");
      if(m_cfg.signalsOn)
         m_signals.LogDaySummary();
      if(m_atrHandle != INVALID_HANDLE)
         IndicatorRelease(m_atrHandle);
      m_atrHandle = INVALID_HANDLE;
      if(m_notifyOn)
        {
         if(m_startSent)
            m_notifier.SendStop(SdbDeinitReasonText(reason));   // spec 09 Req 7.2
         m_notifier.Drain(SDB_NT_DRAIN_MS);   // Critical lalu stop, termasuk init gagal (spec 08 Req 6.3, spec 09 Req 7.4)
         m_notifier.ReleaseLeader();           // spec 09 Req 4.3
        }
      if(m_storageOpened)
        {
         m_logger.EndSession(reason);
         m_logger.Close();
        }
     }

   CExecutor *Executor() { return GetPointer(m_executor); }
   CMarketStructure *Structure() { return GetPointer(m_structure); }
   CZoneBook *Zones() { return GetPointer(m_zones); }
   CPaTrigger *Trigger() { return GetPointer(m_trigger); }
   CSignalEngine *Signals() { return GetPointer(m_signals); }
   ISdbEventSink *Sink() { return m_sink; }
   bool NotifierActive() const { return m_notifyOn; }
   string TransportName() { return m_transport != NULL ? m_transport.Name() : ""; }

   // Data heartbeat (spec 09 Req 5.2); false sampai status risiko siap.
   bool HeartbeatData(SdbHeartbeat &h)
     {
      if(!m_riskReady)
         return false;
      h.balance = AccountInfoDouble(ACCOUNT_BALANCE);
      h.equity = AccountInfoDouble(ACCOUNT_EQUITY);
      double peak = m_riskState.PeakEquity();
      h.ddPct = (peak > 0.0 && h.equity < peak) ? (peak - h.equity) / peak * 100.0 : 0.0;
      h.riskStatus = m_riskState.IsStopped() ? "STOPPED" : m_riskState.IsDailyPaused() ? "pause harian"
                     : m_riskState.IsLotReduced() ? "lot x 0.5" : "normal";
      h.sdbotPositions = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
         if(PositionGetTicket(i) != 0 && IsSdbotMagic(PositionGetInteger(POSITION_MAGIC)))
            h.sdbotPositions++;
      h.instancesAlive = 0;
      h.heldLastHour = 0;
      return true;
     }
   CNotifier *Notifier() { return GetPointer(m_notifier); }
   CAccount  *Account()  { return GetPointer(m_account); }
   CLogger   *Logger()   { return GetPointer(m_logger); }
   CRiskManager *RiskManager() { return GetPointer(m_riskManager); }
   CRiskState   *RiskState()   { return GetPointer(m_riskState); }
  };

#endif // SDB_APP_SDBAPP_MQH
