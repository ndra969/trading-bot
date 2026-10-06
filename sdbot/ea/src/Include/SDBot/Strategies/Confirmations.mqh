//+------------------------------------------------------------------+
//| Confirmations.mqh — CConfirmations: komponen skor konfirmasi Fase 5
//| (spec 19 Req 3.5; design §3.2). Memegang mode tiap komponen dan
//| mengisi SdbSignalFacts dari bar MTF tertutup cache zona (sekali
//| salin untuk semua komponen). Fibonacci (spec 18) dan trendline
//| (spec 19), breakout & retest (spec 20); RSI menyusul.
//+------------------------------------------------------------------+
#ifndef SDB_STRATEGIES_CONFIRMATIONS_MQH
#define SDB_STRATEGIES_CONFIRMATIONS_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Analysis/MarketStructure.mqh>
#include <SDBot/Analysis/ZoneBook.mqh>
#include <SDBot/Strategies/FibRules.mqh>
#include <SDBot/Strategies/TrendlineRules.mqh>
#include <SDBot/Strategies/BreakoutRules.mqh>

class CConfirmations
  {
private:
   ENUM_SDB_COMPONENT_MODE m_fibMode;
   ENUM_SDB_COMPONENT_MODE m_tlMode;
   ENUM_SDB_COMPONENT_MODE m_boMode;
   CZoneBook        *m_zb;
   CMarketStructure *m_ms;

public:
                     CConfirmations(void) : m_fibMode(SDB_COMPONENT_OFF), m_tlMode(SDB_COMPONENT_OFF), m_boMode(SDB_COMPONENT_OFF),
                     m_zb(NULL), m_ms(NULL) {}

   void Init(const ENUM_SDB_COMPONENT_MODE fibMode, const ENUM_SDB_COMPONENT_MODE tlMode, const ENUM_SDB_COMPONENT_MODE boMode, CZoneBook *zb,
             CMarketStructure *ms)
     {
      m_fibMode = fibMode;
      m_tlMode = tlMode;
      m_boMode = boMode;
      m_zb = zb;
      m_ms = ms;
     }

   bool AnyOn() const { return m_fibMode != SDB_COMPONENT_OFF || m_tlMode != SDB_COMPONENT_OFF || m_boMode != SDB_COMPONENT_OFF; }

   void Evaluate(const SdbZone &zone, const ENUM_SDB_DIR dir, const double atrMtf, SdbSignalFacts &f)
     {
      f.fibMode = m_fibMode;
      f.tlMode = m_tlMode;
      f.boMode = m_boMode;
      f.fib.ratio = -1.0;
      f.fib.reason = "";
      f.tl.reason = "";
      f.bo.reason = "";
      if(!AnyOn())
         return;
      MqlRates r[];
      if(m_zb == NULL || m_ms == NULL || m_zb.Rates(r) <= 0)
        {
         f.fib.reason = SDB_FIB_REASON_DATA;
         f.tl.reason = SDB_TL_REASON_DATA;
         f.bo.reason = SDB_BO_REASON_DATA;
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
     }
  };

#endif // SDB_STRATEGIES_CONFIRMATIONS_MQH
