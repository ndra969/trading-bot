//+------------------------------------------------------------------+
//| PaTrigger.mqh — CPaTrigger: pola candle bar LTF tertutup terakhir
//| untuk kedua arah, dihitung sekali per bar LTF baru dari SDB_PA_BARS
//| bar (pemanasan ATR + 3 bar pola) (spec 12 Req 3; design §3.2).
//| Hasil hanya bergantung pada bar sampai bar itu (tanpa repaint).
//+------------------------------------------------------------------+
#ifndef SDB_STRATEGIES_PATRIGGER_MQH
#define SDB_STRATEGIES_PATRIGGER_MQH

#include <SDBot/Core/Utils.mqh>
#include <SDBot/Analysis/BarCache.mqh>
#include <SDBot/Analysis/ZoneRules.mqh>
#include <SDBot/Strategies/PatternRules.mqh>

class CPaTrigger
  {
private:
   ENUM_TIMEFRAMES   m_tf;
   CBarCache         m_cache;
   SdbPattern        m_bull;
   SdbPattern        m_bear;
   MqlRates          m_last;
   bool              m_ready;

   void Clear()
     {
      SdbPattern none;
      none.code = SDB_PA_PATTERN_NONE;
      none.dir = SDB_DIR_NONE;
      none.score = 0;
      none.barTime = 0;
      m_bull = none;
      m_bear = none;
      ZeroMemory(m_last);
      m_ready = false;
     }

   bool Recompute()
     {
      MqlRates r[];
      double atr[];
      int n = m_cache.Copy(r);
      if(n == 0 || !AtrSeries(r, SDB_ZONE_ATR_PERIOD, atr))
        {
         Clear();
         return false;
        }
      DetectPattern(r, atr[n - 1], SDB_DIR_BULL, m_bull);
      DetectPattern(r, atr[n - 1], SDB_DIR_BEAR, m_bear);
      m_last = r[n - 1];
      m_ready = true;
      LogDebug("PaTrigger", StringFormat("pola %s | bar=%s buy=%s sell=%s", EnumToString(m_tf), TimeToString(m_last.time),
                                         m_bull.code, m_bear.code));
      return true;
     }

public:
                     CPaTrigger(void) : m_tf(PERIOD_CURRENT), m_ready(false) { Clear(); }

   void Init(const string symbol, const ENUM_TIMEFRAMES ltf)
     {
      m_tf = ltf;
      Clear();
      m_cache.Init(symbol, ltf, SDB_PA_BARS);
     }

   // true bila bar LTF baru dianalisis.
   bool OnTick()
     {
      bool fresh = m_cache.Refresh();
      if(!m_cache.Ready())
        {
         Clear();
         LogThrottled(SDB_LOG_WARN, "pa-data-" + EnumToString(m_tf), SDB_LOG_THROTTLE_DEFAULT_SEC, "PaTrigger",
                      "histori " + EnumToString(m_tf) + " kurang dari " + IntegerToString(SDB_PA_BARS) + " bar, tanpa pola");
         return false;
        }
      if(!fresh)
         return false;
      return Recompute();
     }

   bool Ready() const { return m_ready; }
   datetime LastBarTime() const { return m_cache.LastClosedTime(); }

   // Pola bar LTF tertutup terakhir untuk arah dir; NONE bila belum siap atau dir NONE.
   void Result(const ENUM_SDB_DIR dir, SdbPattern &out) const
     {
      if(dir == SDB_DIR_BULL)
         out = m_bull;
      else if(dir == SDB_DIR_BEAR)
         out = m_bear;
      else
        {
         out = m_bull;
         out.code = SDB_PA_PATTERN_NONE;
         out.dir = SDB_DIR_NONE;
         out.score = 0;
        }
     }

   void LastBar(MqlRates &out) const { out = m_last; }
  };

#endif // SDB_STRATEGIES_PATRIGGER_MQH
