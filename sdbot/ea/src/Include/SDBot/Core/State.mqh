//+------------------------------------------------------------------+
//| State.mqh — status akun yang dibagi semua instance SDBot di akun yang
//| sama, disimpan di Global Variables terminal "<prefix>_<login>_<NAMA>"
//| (spec 02 Req 4). Akses bertipe (IsStopped, PeakEquity, ...) ada di
//| Risk/RiskState.mqh (spec 05).
//+------------------------------------------------------------------+
#ifndef SDB_CORE_STATE_MQH
#define SDB_CORE_STATE_MQH

#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/Utils.mqh>

class CState
  {
private:
   string            m_prefix;   // "<prefix>_<login>_"
   string            m_names[];  // kunci yang dipakai instance ini, untuk TouchAll

   void Remember(const string name)
     {
      for(int i = 0; i < ArraySize(m_names); i++)
         if(m_names[i] == name)
            return;
      int n = ArraySize(m_names);
      ArrayResize(m_names, n + 1);
      m_names[n] = name;
     }

public:
   // prefix "SDB" untuk live, "SDBTEST" untuk unit test. Login 0 = terminal belum login.
   bool Init(const string prefix, const long login)
     {
      if(prefix == "" || login <= 0)
         return false;
      m_prefix = prefix + "_" + IntegerToString(login) + "_";
      ArrayFree(m_names);
      return true;
     }

   string Key(const string name) const { return m_prefix + name; }

   // Nilai GV, atau safeDefault yang langsung disimpan bila GV belum ada (Req 4.2).
   double GetOrInit(const string name, const double safeDefault, bool &wasMissing)
     {
      Remember(name);
      string key = Key(name);
      wasMissing = !GlobalVariableCheck(key);
      if(!wasMissing)
         return GlobalVariableGet(key);
      Set(name, safeDefault, true);
      return safeDefault;
     }

   double Get(const string name, const double fallback)
     {
      string key = Key(name);
      if(!GlobalVariableCheck(key))
         return fallback;
      Remember(name);
      return GlobalVariableGet(key);
     }

   // flush = true untuk status yang tidak boleh hilang saat terminal crash (STOPPED, pause, flag lot).
   bool Set(const string name, const double value, const bool flush)
     {
      Remember(name);
      ResetLastError();
      if(GlobalVariableSet(Key(name), value) == 0)
        {
         LogThrottled(SDB_LOG_ERROR, "gv-set-" + name, SDB_LOG_THROTTLE_DEFAULT_SEC, "State",
                      "GlobalVariableSet gagal | key=" + Key(name) + " " + ErrText(GetLastError()));
         return false;
        }
      if(flush)
         GlobalVariablesFlush();
      return true;
     }

   // Membaca GV memperbarui waktu aksesnya, sehingga MT5 tidak menghapusnya setelah 4 minggu (Req 4.4).
   int TouchAll()
     {
      int touched = 0;
      for(int i = 0; i < ArraySize(m_names); i++)
        {
         string key = Key(m_names[i]);
         if(GlobalVariableCheck(key))
           {
            GlobalVariableGet(key);
            touched++;
           }
        }
      return touched;
     }

   // Hanya untuk unit test dan skrip reset: hapus semua GV berprefix instance ini.
   int DeleteAll()
     {
      int deleted = GlobalVariablesDeleteAll(m_prefix);
      GlobalVariablesFlush();
      ArrayFree(m_names);
      return deleted;
     }
  };

#endif // SDB_CORE_STATE_MQH
