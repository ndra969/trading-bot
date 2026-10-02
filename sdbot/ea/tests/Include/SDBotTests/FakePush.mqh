//+------------------------------------------------------------------+
//| FakePush.mqh — push dan sumber status palsu untuk uji notifier
//| (spec 09 TC-NR-30..40). Hasil push diprogram "0,1,3" (elemen
//| terakhir berulang); teks yang diterima direkam.
//+------------------------------------------------------------------+
#ifndef SDB_SDBOTTESTS_FAKEPUSH_MQH
#define SDB_SDBOTTESTS_FAKEPUSH_MQH

#include <SDBot/Notify/Push.mqh>
#include <SDBot/Notify/StatusSource.mqh>

class CFakePush : public ISdbPush
  {
private:
   string            m_script[];
   int               m_calls;
   string            m_texts[];

public:
                     CFakePush(void) : m_calls(0) { Script("0"); }
   void Script(const string s) { ArrayFree(m_script); StringSplit(s, ',', m_script); m_calls = 0; }
   int Send(const string text)
     {
      int code = (int)StringToInteger(m_script[MathMin(m_calls, ArraySize(m_script) - 1)]);
      m_calls++;
      int n = ArraySize(m_texts);
      ArrayResize(m_texts, n + 1);
      m_texts[n] = text;
      return code;
     }
   int    Calls() const              { return m_calls; }
   string TextAt(const int i) const  { return (i >= 0 && i < ArraySize(m_texts)) ? m_texts[i] : ""; }
  };

class CFakeStatusSource : public ISdbStatusSource
  {
public:
   SdbHeartbeat      data;
                     CFakeStatusSource(void)
     {
      data.balance = 1000.0;
      data.equity = 990.0;
      data.ddPct = 1.0;
      data.riskStatus = "normal";
      data.sdbotPositions = 2;
      data.instancesAlive = 0;
      data.heldLastHour = 0;
     }
   bool HeartbeatData(SdbHeartbeat &h) { h = data; return true; }
  };

#endif // SDB_SDBOTTESTS_FAKEPUSH_MQH
