//+------------------------------------------------------------------+
//| MarketStructure.mqh — CMarketStructure: analisis HTF dan MTF dari
//| salinan bar tertutup, dihitung ulang per bar baru, bias HTF sebagai
//| gerbang wajib pertama (spec 10 Req 1, 5; design §3.3). Hanya membaca
//| harga (lapisan Analysis): tidak menulis DB, tidak mengirim order.
//+------------------------------------------------------------------+
#ifndef SDB_ANALYSIS_MARKETSTRUCTURE_MQH
#define SDB_ANALYSIS_MARKETSTRUCTURE_MQH

#include <SDBot/Core/Utils.mqh>
#include <SDBot/Analysis/BarCache.mqh>
#include <SDBot/Analysis/StructureRules.mqh>

#define SDB_BIAS_OK        "OK"
#define SDB_BIAS_STRUCTURE "STRUCTURE"   // struktur HTF netral
#define SDB_BIAS_EMA       "EMA"         // arah EMA HTF netral
#define SDB_BIAS_CONFLICT  "CONFLICT"    // struktur dan EMA berlawanan
#define SDB_BIAS_DATA      "DATA"        // histori HTF kurang

string SdbDirText(const ENUM_SDB_DIR d) { return d == SDB_DIR_BULL ? "BULL" : (d == SDB_DIR_BEAR ? "BEAR" : "NONE"); }

// Alasan bias untuk telemetri penolakan NO_HTF_BIAS (Req 5.4).
string BiasReasonOf(const SdbTfAnalysis &htf)
  {
   if(!htf.ready)
      return SDB_BIAS_DATA;
   if(htf.st.dir == SDB_DIR_NONE)
      return SDB_BIAS_STRUCTURE;
   if(htf.emaDir == SDB_DIR_NONE)
      return SDB_BIAS_EMA;
   return (htf.st.dir == htf.emaDir) ? SDB_BIAS_OK : SDB_BIAS_CONFLICT;
  }

class CMarketStructure
  {
private:
   string            m_symbol;
   SdbStructureParams m_params;
   CBarCache         m_htfCache;
   CBarCache         m_mtfCache;
   SdbTfAnalysis     m_htf;
   SdbTfAnalysis     m_mtf;
   SdbBias           m_bias;

   void MarkNotReady(SdbTfAnalysis &a, const CBarCache &cache)
     {
      a.ready = false;
      a.reason = "data kurang";
      LogThrottled(SDB_LOG_WARN, "structure-data-" + EnumToString(cache.Timeframe()), SDB_LOG_THROTTLE_DEFAULT_SEC, "Structure",
                   "histori " + EnumToString(cache.Timeframe()) + " kurang dari " +
                   IntegerToString(BarsNeeded(m_params.strength, m_params.lookback, m_params.emaPeriod, m_params.slopeBars)) +
                   " bar tertutup, analisis ditunda");
     }

   // true bila timeframe dihitung ulang (bar baru).
   bool UpdateTf(CBarCache &cache, SdbTfAnalysis &a)
     {
      if(cache.Refresh())
        {
         MqlRates r[];
         cache.Copy(r);
         AnalyzeTf(r, m_params, a);
         return true;
        }
      if(!cache.Ready())
         MarkNotReady(a, cache);
      return false;
     }

   void UpdateBias()
     {
      ENUM_SDB_DIR dir = m_htf.ready ? BiasOf(m_htf.st.dir, m_htf.emaDir) : SDB_DIR_NONE;
      string reason = BiasReasonOf(m_htf);
      if(dir != m_bias.dir || reason != m_bias.reason)
         LogInfo("Structure", StringFormat("bias %s -> %s | alasan=%s struktur=%s ema=%s bos=%s @ %s", SdbDirText(m_bias.dir),
                                           SdbDirText(dir), reason, SdbDirText(m_htf.st.dir), SdbDirText(m_htf.emaDir),
                                           DoubleToString(m_htf.st.bosLevel, (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS)),
                                           TimeToString(m_htf.st.bosTime)));
      m_bias.dir = dir;
      m_bias.reason = reason;
      m_bias.htfBarTime = m_htf.barTime;
     }

public:
   void Init(const string symbol, const ENUM_TIMEFRAMES htf, const ENUM_TIMEFRAMES mtf, const SdbStructureParams &p)
     {
      m_symbol = symbol;
      m_params = p;
      int need = BarsNeeded(p.strength, p.lookback, p.emaPeriod, p.slopeBars);
      m_htfCache.Init(symbol, htf, need);
      m_mtfCache.Init(symbol, mtf, need);
      ZeroMemory(m_htf);
      ZeroMemory(m_mtf);
      m_htf.reason = "data kurang";
      m_mtf.reason = "data kurang";
      m_bias.dir = SDB_DIR_NONE;
      m_bias.reason = SDB_BIAS_DATA;
      m_bias.htfBarTime = 0;
     }

   // Murah bila tidak ada bar baru: hanya membandingkan waktu bar tertutup (Req 1.2).
   bool OnTick()
     {
      bool htfChanged = UpdateTf(m_htfCache, m_htf);
      bool mtfChanged = UpdateTf(m_mtfCache, m_mtf);
      if(htfChanged || !m_htf.ready)
         UpdateBias();
      return htfChanged || mtfChanged;
     }

   void Htf(SdbTfAnalysis &out) const       { out = m_htf; }
   void Mtf(SdbTfAnalysis &out) const       { out = m_mtf; }
   void Bias(SdbBias &out) const            { out = m_bias; }
   ENUM_TIMEFRAMES HtfTimeframe() const     { return m_htfCache.Timeframe(); }
   ENUM_TIMEFRAMES MtfTimeframe() const     { return m_mtfCache.Timeframe(); }
   int  BarsRequired() const                { return BarsNeeded(m_params.strength, m_params.lookback, m_params.emaPeriod, m_params.slopeBars); }
   void Params(SdbStructureParams &out) const { out = m_params; }
  };

#endif // SDB_ANALYSIS_MARKETSTRUCTURE_MQH
