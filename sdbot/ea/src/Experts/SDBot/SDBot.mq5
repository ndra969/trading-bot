//+------------------------------------------------------------------+
//| SDBot.mq5 — EA Supply & Demand + konfluensi (PRD-EA).
//| v1.01 (spec 02): validasi input dan akun, izin dan koneksi, status
//| bersama di Global Variables. Belum ada logika trading. Mulai spec 04,
//| file ini hanya meneruskan event ke CSdbApp.
//+------------------------------------------------------------------+
#property copyright "SDBot"
#property version   "1.01"
#property description "SDBot EA v1.01 (spec 02): validasi akun dan input. Tidak mengirim order apa pun."

#include <SDBot/Core/Inputs.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Core/State.mqh>
#include <SDBot/Account/Account.mqh>

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

int OnInit()
  {
   SdbSetLogLevel(InpLogLevel);
   string errors;
   if(!ValidateInputValues(CurrentInputs(), errors))
     {
      LogCritical("App", "input tidak valid | " + errors);
      return INIT_PARAMETERS_INCORRECT;
     }
   g_account.Init(NULL, _Symbol, InpSymbolSuffix, InpAllowLiveTrading, InpMagicNumber);
   if(g_account.Validate() == SDB_VAL_REJECTED)
      return INIT_FAILED;
   EnsureState();
   if(!EventSetTimer(SDB_TIMER_SEC))
     {
      LogCritical("App", "timer tidak bisa dipasang | " + ErrText(GetLastError()));
      return INIT_FAILED;
     }
   LogInfo("App", "SDBot v1.01 aktif | magic=" + IntegerToString(InpMagicNumber) +
           " style=" + EnumToString(InpTradingStyle) + " validasi=" + EnumToString(g_account.State()));
   return INIT_SUCCEEDED;
  }

void OnTimer()
  {
   g_account.OnTimer();
   if(g_account.RejectedFromTimer())
     {
      LogCritical("App", "validasi akun tertunda ditolak, EA dilepas dari chart | " + g_account.LastReason());
      ExpertRemove();
      return;
     }
   EnsureState();
   if(g_stateReady && TimeLocal() - g_lastTouch >= SDB_GV_TOUCH_SEC)
     {
      g_state.TouchAll();
      g_lastTouch = TimeLocal();
     }
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   LogInfo("App", "SDBot berhenti | reason=" + IntegerToString(reason));
  }

void OnTick()
  {
  }
