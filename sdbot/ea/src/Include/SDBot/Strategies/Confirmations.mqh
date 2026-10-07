//+------------------------------------------------------------------+
//| Confirmations.mqh — CConfirmations: komponen skor konfirmasi Fase 5
//| (spec 19 Req 3.5; design §3.2). Memegang mode tiap komponen dan
//| mengisi SdbSignalFacts dari bar MTF tertutup cache zona (sekali
//| salin untuk semua komponen). Fibonacci (spec 18) dan trendline
//| (spec 19), breakout & retest (spec 20), RSI divergence (spec 21;
//| handle iRSI milik CSdbApp, dipinjam di sini).
//+------------------------------------------------------------------+
#ifndef SDB_STRATEGIES_CONFIRMATIONS_MQH
#define SDB_STRATEGIES_CONFIRMATIONS_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Analysis/MarketStructure.mqh>
#include <SDBot/Analysis/ZoneBook.mqh>
#include <SDBot/Strategies/FibRules.mqh>
#include <SDBot/Strategies/TrendlineRules.mqh>
#include <SDBot/Strategies/BreakoutRules.mqh>
#include <SDBot/Strategies/RsiRules.mqh>

#define SDB_RSI_WARN_SEC 86400   // WARN data RSI paling sering sekali sehari (spec 21 design keputusan 4)

// RSI sejajar dengan bar: salinan berdasarkan rentang waktu r[0]..r[n-1], wajib tepat n nilai (spec 21 Req 1.2).
bool RsiCopyAligned(const int handle, const MqlRates &r[], double &out[])
  {
   ArrayFree(out);
   int n = ArraySize(r);
   if(handle == INVALID_HANDLE || n == 0)
      return false;
   ArraySetAsSeries(out, false);
   if(CopyBuffer(handle, 0, r[0].time, r[n - 1].time, out) != n)
     {
      ArrayFree(out);
      return false;
     }
   return true;
  }

class CConfirmations
  {
private:
   ENUM_SDB_COMPONENT_MODE m_fibMode;
   ENUM_SDB_COMPONENT_MODE m_tlMode;
   ENUM_SDB_COMPONENT_MODE m_boMode;
   ENUM_SDB_COMPONENT_MODE m_rsiMode;
   int               m_rsiHandle;
   CZoneBook        *m_zb;
   CMarketStructure *m_ms;

public:
                     CConfirmations(void) : m_fibMode(SDB_COMPONENT_OFF), m_tlMode(SDB_COMPONENT_OFF), m_boMode(SDB_COMPONENT_OFF),
                     m_rsiMode(SDB_COMPONENT_OFF), m_rsiHandle(INVALID_HANDLE), m_zb(NULL), m_ms(NULL) {}

   void Init(const ENUM_SDB_COMPONENT_MODE fibMode, const ENUM_SDB_COMPONENT_MODE tlMode, const ENUM_SDB_COMPONENT_MODE boMode,
             const ENUM_SDB_COMPONENT_MODE rsiMode, const int rsiHandle, CZoneBook *zb, CMarketStructure *ms)
     {
      m_fibMode = fibMode;
      m_tlMode = tlMode;
      m_boMode = boMode;
      m_rsiMode = rsiMode;
      m_rsiHandle = rsiHandle;
      m_zb = zb;
      m_ms = ms;
     }

   bool AnyOn() const { return m_fibMode != SDB_COMPONENT_OFF || m_tlMode != SDB_COMPONENT_OFF || m_boMode != SDB_COMPONENT_OFF ||
                                m_rsiMode != SDB_COMPONENT_OFF; }

   void Evaluate(const SdbZone &zone, const ENUM_SDB_DIR dir, const double atrMtf, SdbSignalFacts &f)
     {
      f.fibMode = m_fibMode;
      f.tlMode = m_tlMode;
      f.boMode = m_boMode;
      f.rsiMode = m_rsiMode;
      f.fib.ratio = -1.0;
      f.fib.reason = "";
      f.tl.reason = "";
      f.bo.reason = "";
      f.rsi.reason = "";
      if(!AnyOn())
         return;
      MqlRates r[];
      if(m_zb == NULL || m_ms == NULL || m_zb.Rates(r) <= 0)
        {
         f.fib.reason = SDB_FIB_REASON_DATA;
         f.tl.reason = SDB_TL_REASON_DATA;
         f.bo.reason = SDB_BO_REASON_DATA;
         f.rsi.reason = SDB_RSI_REASON_DATA;
         return;
        }
      SdbZoneParams zp;
      m_zb.Params(zp);
      SdbStructureParams sp;
      m_ms.Params(sp);
      if(m_fibMode != SDB_COMPONENT_OFF)
         FibEvaluate(r, zone, zp.minLegAtr, sp.lookback, f.fib);
      if(m_tlMode != SDB_COMPONENT_OFF)
         TlEvaluate(r, zone, dir == SDB_DIR_BULL, sp.strength, sp.lookback, atrMtf, f.tl);
      if(m_boMode != SDB_COMPONENT_OFF)
         BoEvaluate(r, zone, dir == SDB_DIR_BULL, sp.strength, sp.lookback, atrMtf, f.bo);
      if(m_rsiMode != SDB_COMPONENT_OFF)
         EvaluateRsi(r, dir == SDB_DIR_BULL, sp, atrMtf, f.rsi);
     }

private:
   // Handle tidak valid atau buffer belum sejajar: skor 0 "data kurang", WARN tertahan, entry tetap jalan (Req 1.3).
   void EvaluateRsi(const MqlRates &r[], const bool buy, const SdbStructureParams &sp, const double atrMtf, SdbRsiResult &out)
     {
      double rsi[];
      if(!RsiCopyAligned(m_rsiHandle, r, rsi))
        {
         ZeroMemory(out);
         out.reason = SDB_RSI_REASON_DATA;
         LogThrottled(SDB_LOG_WARN, "rsi-data", SDB_RSI_WARN_SEC, "Signals",
                      m_rsiHandle == INVALID_HANDLE ? "handle iRSI tidak ada: skor RSI 0" : "data RSI belum sejajar dengan bar MTF: skor RSI 0");
         return;
        }
      RsiEvaluate(r, rsi, buy, sp.strength, sp.lookback, atrMtf, out);
     }
  };

#endif // SDB_STRATEGIES_CONFIRMATIONS_MQH
