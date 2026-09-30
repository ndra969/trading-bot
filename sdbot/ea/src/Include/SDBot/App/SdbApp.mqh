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
     }

public:
                     CSdbApp(void) : m_sink(NULL), m_storageOpened(false), m_stateReady(false), m_timerSet(false),
                     m_deinitDone(false), m_lastSnapshot(0), m_lastTouch(0) {}

   // Urutan init (Req 6.1). observer: perekam harness / sink uji, menerima event di samping Logger.
   int OnInit(const SdbAppConfig &cfg, ISdbEventSink *observer = NULL)
     {
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
      EnsureState();
      m_executor.Init(cfg.inputs.magic, _Symbol, GetPointer(m_account), GetPointer(m_state), m_sink, cfg.eaVersion);
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

   // Akun → state → risk monitor (spec 05) → snapshot → touch GV → flush (Req 6.3, 6.5).
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
      if(m_account.State() == SDB_VAL_PASSED && TimeLocal() - m_lastSnapshot >= SDB_ACCOUNT_SNAPSHOT_SEC)
        {
         m_sink.OnAccount(m_account.Snapshot());
         m_lastSnapshot = TimeLocal();
        }
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
  };

#endif // SDB_APP_SDBAPP_MQH
