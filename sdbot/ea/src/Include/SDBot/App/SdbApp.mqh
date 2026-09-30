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
#include <SDBot/App/TeeSink.mqh>

#define SDB_GV_PREFIX_UNITTEST "SDBTEST"

class CSdbApp
  {
private:
   SdbAppConfig      m_cfg;
   CLogger           m_logger;
   CTeeSink          m_tee;
   ISdbEventSink    *m_sink;          // Logger, atau tee(Logger, observer) di harness/uji
   CAccount          m_account;
   CState            m_state;
   CExecutor         m_executor;
   CRiskState        m_riskState;
   CRiskManager      m_riskManager;
   CRiskMonitor      m_riskMonitor;
   bool              m_riskReady;
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
      // Status risiko bersama (spec 05): baseline, reset input, operasi saldo tertunda, lalu snapshot
      // langsung dengan puncak yang benar (Req 3.8), karena snapshot Validate() dibuat sebelum puncak diketahui.
      m_riskReady = m_riskState.Init(GetPointer(m_state), m_cfg.inputs.magic, AccountInfoDouble(ACCOUNT_EQUITY),
                                     AccountInfoDouble(ACCOUNT_BALANCE), TimeTradeServer());
      if(m_riskReady)
        {
         m_riskMonitor.OnStateReady(m_cfg.resetEmergencyStop);
         SendSnapshot();
        }
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

   void OpenStorage(ISdbEventSink *observer)
     {
      m_logger.Init(observer, _Symbol, m_cfg.inputs.magic, m_cfg.eaVersion);
      m_logger.Open(m_cfg.dbTarget);   // gagal buka tidak menggagalkan init (spec 03 Req 2.2)
      m_storageOpened = true;
      if(observer == NULL)
         m_sink = GetPointer(m_logger);
      else
        {
         m_tee.Init(GetPointer(m_logger), observer);
         m_sink = GetPointer(m_tee);
        }
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
     }

public:
                     CSdbApp(void) : m_sink(NULL), m_riskReady(false), m_storageOpened(false), m_stateReady(false), m_timerSet(false),
                     m_deinitDone(false), m_lastSnapshot(0), m_lastTouch(0) {}

   // Urutan init (Req 6.1). observer: perekam harness / sink uji, menerima event di samping Logger.
   // Ganti timeframe/simbol chart memanggil OnDeinit lalu OnInit pada objek global yang sama.
   int OnInit(const SdbAppConfig &cfg, ISdbEventSink *observer = NULL)
     {
      m_sink = NULL;
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
      m_account.Init(m_sink, _Symbol, cfg.symbolSuffix, cfg.allowLive, cfg.inputs.magic);
      if(m_account.Validate() == SDB_VAL_REJECTED)
         return INIT_FAILED;   // OnDeinit(REASON_INITFAILED) menutup sesi dan menyimpan alert
      m_executor.Init(cfg.inputs.magic, _Symbol, GetPointer(m_account), GetPointer(m_state), m_sink, cfg.eaVersion);
      // Langkah 6 (spec 05): modul risiko dipasang sebelum status bersama agar OnStateReady bisa jalan.
      m_riskManager.Init(_Symbol, GetPointer(m_riskState), GetPointer(m_executor), GetPointer(m_account), cfg.inputs);
      m_riskMonitor.Init(_Symbol, cfg.inputs.magic, GetPointer(m_riskState), GetPointer(m_executor), m_sink, cfg);
      EnsureState();
      if(!EventSetTimer(SDB_TIMER_SEC))
        {
         LogCritical("App", "timer tidak bisa dipasang | " + ErrText(GetLastError()));
         return INIT_FAILED;
        }
      m_timerSet = true;
      LogInfo("App", "SDBot v" + cfg.eaVersion + " aktif | magic=" + IntegerToString(cfg.inputs.magic) +
              " mode=" + EnumToString(cfg.mode) + " style=" + EnumToString(cfg.style) +
              " validasi=" + EnumToString(m_account.State()) + " db=" + (m_logger.IsWritable() ? "ok" : "tidak ada"));
      return INIT_SUCCEEDED;
     }

   // Posisi dikelola mulai spec 06; sampai akun lolos, tick diabaikan.
   void OnTick()
     {
      if(m_account.State() != SDB_VAL_PASSED)
         return;
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
      m_logger.Flush();
     }

   // Pencatatan deal dan closure mulai spec 06.
   void OnTradeTransaction(const MqlTradeTransaction &t, const MqlTradeRequest &rq, const MqlTradeResult &rs)
     {
     }

   // Metrik optimasi mulai spec 07.
   double OnTester() { return 0.0; }

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
      if(m_storageOpened)
        {
         m_logger.EndSession(reason);
         m_logger.Close();
        }
     }

   CExecutor *Executor() { return GetPointer(m_executor); }
   CAccount  *Account()  { return GetPointer(m_account); }
   CLogger   *Logger()   { return GetPointer(m_logger); }
   CRiskManager *RiskManager() { return GetPointer(m_riskManager); }
   CRiskState   *RiskState()   { return GetPointer(m_riskState); }
  };

#endif // SDB_APP_SDBAPP_MQH
