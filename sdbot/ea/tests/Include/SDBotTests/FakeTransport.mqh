//+------------------------------------------------------------------+
//| FakeTransport.mqh — transport palsu untuk unit test dan harness
//| (spec 08 Req 7.4, design §3.5). Hasil per kiriman diprogram lewat
//| skrip "OK,TEMP,LIMITED:60,PERM" (elemen terakhir berulang), dan satu
//| tipe bisa dibuat selalu gagal sementara (SC-10). Setiap kiriman
//| direkam beserta hasil, waktu, dan fase pemanggil yang diset harness
//| (TIMER, DEINIT, TICK, TRADE); kiriman di fase TICK/TRADE melanggar Req 3.1.
//+------------------------------------------------------------------+
#ifndef SDB_SDBOTTESTS_FAKETRANSPORT_MQH
#define SDB_SDBOTTESTS_FAKETRANSPORT_MQH

#include <SDBot/Notify/Transport.mqh>

class CFakeTransport : public ISdbTransport
  {
private:
   string            m_script[];
   int               m_calls;
   string            m_failType;
   string            m_phase;
   long              m_cycle;          // nomor siklus OnTimer dari harness
   SdbOutMessage     m_msgs[];
   datetime          m_times[];
   string            m_phases[];
   int               m_codes[];
   long              m_cycles[];

   bool              m_off;            // setelah CONFIG: seperti CTelegramTransport nonaktif

   // Langkah: OK[:NOTE], TEMP[:detik jeda], LIMITED:detik, PERM, CONFIG (nonaktif, berikutnya PERMANENT TELEGRAM_OFF).
   SdbSendResult Parse(const string step)
     {
      SdbSendResult r;
      r.retryAfterSec = 0;
      r.error = step;
      r.disable = false;
      r.note = "";
      string parts[];
      StringSplit(step, ':', parts);
      string code = ArraySize(parts) > 0 ? parts[0] : "OK";
      if(code == "TEMP")
        {
         r.code = SDB_SEND_TEMP;
         r.retryAfterSec = ArraySize(parts) > 1 ? (int)StringToInteger(parts[1]) : 0;
        }
      else if(code == "CONFIG")
        {
         r.code = SDB_SEND_PERMANENT;
         r.disable = true;
         r.note = "TELEGRAM_OFF";
         m_off = true;
        }
      else if(code == "LIMITED")
        {
         r.code = SDB_SEND_LIMITED;
         r.retryAfterSec = ArraySize(parts) > 1 ? (int)StringToInteger(parts[1]) : 1;
        }
      else if(code == "PERM")
         r.code = SDB_SEND_PERMANENT;
      else
        {
         r.code = SDB_SEND_OK;
         r.note = ArraySize(parts) > 1 ? parts[1] : "";
        }
      return r;
     }

public:
                     CFakeTransport(void) : m_calls(0), m_failType(""), m_phase(""), m_cycle(0), m_off(false) { Script("OK"); }

   void Script(const string script)
     {
      ArrayFree(m_script);
      StringSplit(script == "" ? "OK" : script, ',', m_script);
      m_calls = 0;
     }
   void FailType(const string type)  { m_failType = type; }
   void SetPhase(const string phase) { m_phase = phase; }
   void SetCycle(const long cycle)   { m_cycle = cycle; }

   SdbSendResult Send(const SdbOutMessage &m)
     {
      SdbSendResult r;
      if(m_off)
        {
         r = Parse("PERM");
         r.note = "TELEGRAM_OFF";
        }
      else if(m_failType != "" && m.type == m_failType)
         r = Parse("TEMP");
      else
         r = Parse(m_script[MathMin(m_calls, ArraySize(m_script) - 1)]);
      m_calls++;
      int k = ArraySize(m_msgs);
      ArrayResize(m_msgs, k + 1, 256);
      ArrayResize(m_times, k + 1, 256);
      ArrayResize(m_phases, k + 1, 256);
      ArrayResize(m_codes, k + 1, 256);
      ArrayResize(m_cycles, k + 1, 256);
      m_msgs[k] = m;
      m_times[k] = TimeCurrent();
      m_phases[k] = m_phase;
      m_codes[k] = (int)r.code;
      m_cycles[k] = m_cycle;
      return r;
     }
   string Name() { return "FAKE"; }

   int  Calls() const { return m_calls; }
   int  Count() const { return ArraySize(m_msgs); }
   bool At(const int i, SdbOutMessage &out) const
     {
      if(i < 0 || i >= ArraySize(m_msgs))
         return false;
      out = m_msgs[i];
      return true;
     }
   datetime TimeAt(const int i) const  { return (i >= 0 && i < ArraySize(m_times)) ? m_times[i] : 0; }
   string   PhaseAt(const int i) const { return (i >= 0 && i < ArraySize(m_phases)) ? m_phases[i] : ""; }
   int      CodeAt(const int i) const  { return (i >= 0 && i < ArraySize(m_codes)) ? m_codes[i] : -1; }
   long     CycleAt(const int i) const { return (i >= 0 && i < ArraySize(m_cycles)) ? m_cycles[i] : -1; }
   int  Violations() const
     {
      int n = 0;
      for(int i = 0; i < ArraySize(m_phases); i++)
         if(m_phases[i] == "TICK" || m_phases[i] == "TRADE")
            n++;
      return n;
     }
   int  CountCode(const ENUM_SDB_SEND_CODE code) const
     {
      int n = 0;
      for(int i = 0; i < ArraySize(m_codes); i++)
         if(m_codes[i] == (int)code)
            n++;
      return n;
     }
   int  CountType(const string type) const
     {
      int n = 0;
      for(int i = 0; i < ArraySize(m_msgs); i++)
         if(m_msgs[i].type == type)
            n++;
      return n;
     }
   int  FirstIndexOf(const string type) const
     {
      for(int i = 0; i < ArraySize(m_msgs); i++)
         if(m_msgs[i].type == type)
            return i;
      return -1;
     }
   void Reset()
     {
      ArrayFree(m_msgs);
      ArrayFree(m_times);
      ArrayFree(m_phases);
      ArrayFree(m_codes);
      ArrayFree(m_cycles);
      m_calls = 0;
     }
  };

#endif // SDB_SDBOTTESTS_FAKETRANSPORT_MQH
