//+------------------------------------------------------------------+
//| BarCache.mqh — CBarCache: salinan N bar tertutup satu timeframe, urut
//| waktu naik, disalin ulang hanya saat bar baru tutup (spec 10 Req 1;
//| design §3.2). Bar berjalan (shift 0) tidak pernah masuk.
//+------------------------------------------------------------------+
#ifndef SDB_ANALYSIS_BARCACHE_MQH
#define SDB_ANALYSIS_BARCACHE_MQH

class CBarCache
  {
private:
   string            m_symbol;
   ENUM_TIMEFRAMES   m_tf;
   int               m_count;
   MqlRates          m_rates[];
   datetime          m_last;         // bar tertutup terbaru di salinan
   bool              m_ready;

public:
                     CBarCache(void) : m_tf(PERIOD_CURRENT), m_count(0), m_last(0), m_ready(false) {}

   void Init(const string symbol, const ENUM_TIMEFRAMES tf, const int count)
     {
      m_symbol = symbol;
      m_tf = tf;
      m_count = count;
      m_last = 0;
      m_ready = false;
      ArrayFree(m_rates);
     }

   // true bila bar tertutup baru berhasil disalin. Gagal/kurang: tidak siap, waktu tidak dimajukan
   // sehingga dicoba lagi di tick berikutnya (Req 1.3).
   bool Refresh()
     {
      datetime closed = iTime(m_symbol, m_tf, 1);
      if(closed == 0)
        {
         m_ready = false;
         return false;
        }
      if(closed == m_last && m_ready)
         return false;
      MqlRates tmp[];
      ArraySetAsSeries(tmp, false);
      int got = CopyRates(m_symbol, m_tf, 1, m_count, tmp);
      if(got < m_count || tmp[got - 1].time != closed)
        {
         m_ready = false;
         return false;
        }
      ArrayFree(m_rates);
      ArrayCopy(m_rates, tmp);
      m_last = closed;
      m_ready = true;
      return true;
     }

   bool            Ready() const          { return m_ready; }
   datetime        LastClosedTime() const { return m_last; }
   ENUM_TIMEFRAMES Timeframe() const      { return m_tf; }

   int Copy(MqlRates &out[]) const
     {
      ArrayFree(out);
      if(!m_ready)
         return 0;
      ArrayCopy(out, m_rates);
      return ArraySize(out);
     }
  };

#endif // SDB_ANALYSIS_BARCACHE_MQH
