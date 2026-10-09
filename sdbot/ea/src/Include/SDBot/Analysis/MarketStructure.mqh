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

string SdbDirText(const ENUM_SDB_DIR d) { return d == SDB_DIR_BULL ? "BULL" : (d == SDB_DIR_BEAR ? "BEAR" : "NONE"); }

class CMarketStructure
  {
private:
   string            m_symbol;
   SdbStructureParams m_htfParams;      // EMA = periode EMA bias (spec 27)
   SdbStructureParams m_mtfParams;      // EMA = InpEmaPeriod, dipakai skor tren dan konfirmasi
   ENUM_SDB_BIAS_MODE m_mode;
   CBarCache         m_htfCache;
   CBarCache         m_mtfCache;
   SdbTfAnalysis     m_htf;
   SdbTfAnalysis     m_mtf;
   SdbBias           m_bias;

   static int Need(const SdbStructureParams &p) { return BarsNeeded(p.strength, p.lookback, p.emaPeriod, p.slopeBars); }

   void MarkNotReady(SdbTfAnalysis &a, const CBarCache &cache, const SdbStructureParams &p)
     {
      a.ready = false;
      a.reason = "data kurang";
      LogThrottled(SDB_LOG_WARN, "structure-data-" + EnumToString(cache.Timeframe()), SDB_LOG_THROTTLE_DEFAULT_SEC, "Structure",
                   "histori " + EnumToString(cache.Timeframe()) + " kurang dari " +
                   IntegerToString(Need(p)) +
                   " bar tertutup, analisis ditunda");
     }

   // true bila timeframe dihitung ulang (bar baru).
   bool UpdateTf(CBarCache &cache, SdbTfAnalysis &a, const SdbStructureParams &p)
     {
      if(cache.Refresh())
        {
         MqlRates r[];
         cache.Copy(r);
         AnalyzeTf(r, p, a);
         return true;
        }
      if(!cache.Ready())
         MarkNotReady(a, cache, p);
      return false;
     }

   void UpdateBias()
     {
      ENUM_SDB_DIR dir = m_htf.ready ? BiasOf(m_htf.st.dir, m_htf.emaDir, m_mode) : SDB_DIR_NONE;
      string reason = BiasReasonOf(m_htf, m_mode);
      if(dir != m_bias.dir || reason != m_bias.reason)
         LogInfo("Structure", StringFormat("bias %s -> %s | alasan=%s mode=%s struktur=%s ema=%s bos=%s @ %s", SdbDirText(m_bias.dir),
                                           SdbDirText(dir), reason, EnumToString(m_mode), SdbDirText(m_htf.st.dir), SdbDirText(m_htf.emaDir),
                                           DoubleToString(m_htf.st.bosLevel, (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS)),
                                           TimeToString(m_htf.st.bosTime)));
      m_bias.dir = dir;
      m_bias.reason = reason;
      m_bias.htfBarTime = m_htf.barTime;
     }

public:
   // htfP membawa periode EMA bias, mtfP periode EMA tren; histori per timeframe dari parameternya (spec 27 Req 2.2, 2.3).
   void Init(const string symbol, const ENUM_TIMEFRAMES htf, const ENUM_TIMEFRAMES mtf, const SdbStructureParams &htfP,
             const SdbStructureParams &mtfP, const ENUM_SDB_BIAS_MODE mode)
     {
      m_symbol = symbol;
      m_htfParams = htfP;
      m_mtfParams = mtfP;
      m_mode = mode;
      m_htfCache.Init(symbol, htf, Need(htfP));
      m_mtfCache.Init(symbol, mtf, Need(mtfP));
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
      bool htfChanged = UpdateTf(m_htfCache, m_htf, m_htfParams);
      bool mtfChanged = UpdateTf(m_mtfCache, m_mtf, m_mtfParams);
      if(htfChanged || !m_htf.ready)
         UpdateBias();
      return htfChanged || mtfChanged;
     }

   void Htf(SdbTfAnalysis &out) const       { out = m_htf; }
   void Mtf(SdbTfAnalysis &out) const       { out = m_mtf; }
   void Bias(SdbBias &out) const            { out = m_bias; }
   ENUM_TIMEFRAMES HtfTimeframe() const     { return m_htfCache.Timeframe(); }
   ENUM_TIMEFRAMES MtfTimeframe() const     { return m_mtfCache.Timeframe(); }
   int  BarsRequired() const                { return MathMax(Need(m_htfParams), Need(m_mtfParams)); }
   void Params(SdbStructureParams &out) const { out = m_mtfParams; }   // parameter MTF (konfirmasi)
   ENUM_SDB_BIAS_MODE BiasMode() const      { return m_mode; }
  };

#endif // SDB_ANALYSIS_MARKETSTRUCTURE_MQH
