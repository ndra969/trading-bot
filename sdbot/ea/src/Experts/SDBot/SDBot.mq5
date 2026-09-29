//+------------------------------------------------------------------+
//| SDBot.mq5 — EA Supply & Demand + konfluensi (PRD-EA).
//| v1.02 (spec 03): validasi input dan akun, izin dan koneksi, status
//| bersama di Global Variables, pencatatan ke SQLite (sesi, akun,
//| alert) lewat CLogger. Belum ada logika trading. Mulai spec 04, file
//| ini hanya meneruskan event ke CSdbApp.
//+------------------------------------------------------------------+
#property copyright "SDBot"
#property version   "1.02"
#property description "SDBot EA v1.02 (spec 03): validasi akun dan input, pencatatan SQLite. Tidak mengirim order apa pun."

#define SDB_EA_VERSION "1.02"   // sama dengan #property version

#include <SDBot/Core/Inputs.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Core/State.mqh>
#include <SDBot/Account/Account.mqh>
#include <SDBot/Storage/Logger.mqh>

CLogger  g_logger;
CAccount g_account;
CState   g_state;
bool     g_stateReady = false;
datetime g_lastTouch = 0;

// Status akun butuh login; saat terminal belum login, dipanggil ulang dari timer.
void EnsureState()
  {
   if(g_stateReady || g_account.State() != SDB_VAL_PASSED)
      return;
   g_stateReady = g_state.Init(SDB_GV_PREFIX, g_account.Login());
  }

// DB gagal dibuka tidak menggagalkan init: EA tetap jalan tanpa DB (spec 03 Req 2.2).
void OpenStorage()
  {
   ENUM_SDB_DB_TARGET target = SdbDbTargetForRuntime();
   g_logger.Init(NULL, _Symbol, InpMagicNumber, SDB_EA_VERSION);
   g_logger.Open(target);
   SessionInfo s;
   s.login = AccountInfoInteger(ACCOUNT_LOGIN);
   s.magic = InpMagicNumber;
   s.symbol = _Symbol;
   s.mode = (target == SDB_DB_TESTER) ? SDB_SESSION_MODE_TESTER : SDB_SESSION_MODE_LIVE;
   s.eaVersion = SDB_EA_VERSION;
   s.inputsJson = CurrentInputsJson();
   s.startedAt = TimeCurrent();
   s.testerFrom = (target == SDB_DB_TESTER) ? TimeCurrent() : 0;
   s.testerTo = 0;
   s.testerModel = "";
   g_logger.BeginSession(s);
  }

int OnInit()
  {
   SdbSetLogLevel(InpLogLevel);
   string errors;
   if(!ValidateInputValues(CurrentInputs(), errors))
     {
      LogCritical("App", "input tidak valid | " + errors);
      return INIT_PARAMETERS_INCORRECT;
     }
   OpenStorage();
   g_account.Init(GetPointer(g_logger), _Symbol, InpSymbolSuffix, InpAllowLiveTrading, InpMagicNumber);
   if(g_account.Validate() == SDB_VAL_REJECTED)
      return INIT_FAILED;   // OnDeinit(REASON_INITFAILED) menutup sesi dan menyimpan alert
   EnsureState();
   if(!EventSetTimer(SDB_TIMER_SEC))
     {
      LogCritical("App", "timer tidak bisa dipasang | " + ErrText(GetLastError()));
      return INIT_FAILED;
     }
   LogInfo("App", "SDBot v" + SDB_EA_VERSION + " aktif | magic=" + IntegerToString(InpMagicNumber) +
           " style=" + EnumToString(InpTradingStyle) + " validasi=" + EnumToString(g_account.State()) +
           " db=" + (g_logger.IsWritable() ? "ok" : "tidak ada"));
   return INIT_SUCCEEDED;
  }

void OnTimer()
  {
   g_account.OnTimer();
   if(g_account.RejectedFromTimer())
     {
      LogCritical("App", "validasi akun tertunda ditolak, EA dilepas dari chart | " + g_account.LastReason());
      g_logger.Flush();
      ExpertRemove();
      return;
     }
   EnsureState();
   if(g_stateReady && TimeLocal() - g_lastTouch >= SDB_GV_TOUCH_SEC)
     {
      g_state.TouchAll();
      g_lastTouch = TimeLocal();
     }
   g_logger.Flush();   // setelah semua pemeriksaan detik ini (design §4.2)
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   g_logger.EndSession(reason);
   g_logger.Close();
   LogInfo("App", "SDBot berhenti | reason=" + IntegerToString(reason));
  }

void OnTick()
  {
  }
