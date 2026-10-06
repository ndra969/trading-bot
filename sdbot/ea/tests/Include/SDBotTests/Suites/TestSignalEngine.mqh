//+------------------------------------------------------------------+
//| TestSignalEngine.mqh — CSignalEngine dengan data terminal: menilai
//| bar LTF sekali, penanda bar di GV bertahan lintas objek (restart),
//| kandidat tercatat dengan skor atau bar dihitung sebagai bukan
//| kandidat (spec 13 Req 1, 6; design §3.2; TC-SGX-01..03). Risiko,
//| akun, dan eksekusi NULL: kandidat berhenti di NOT_TRADABLE, tanpa order.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTSIGNALENGINE_MQH
#define SDB_SUITES_TESTSIGNALENGINE_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/FakeSink.mqh>
#include <SDBot/Signals/SignalEngine.mqh>

#define TSE_LOGIN 990005
#define TSE_MAGIC 2026091951

SdbSignalParams TseParams()
  {
   InputValues v = DefaultInputValues();
   SdbSignalParams p;
   p.minScorePct = v.minConfluenceScore;
   p.minRR = v.minRR;
   p.slBufferAtr = v.slBufferAtr;
   p.minSlAtr = v.minSlAtr;
   p.maxSlAtr = v.maxSlAtr;
   p.maxSpreadPoints = v.maxSpreadPoints;
   return p;
  }

SdbSessionParams TseSessions()
  {
   SdbSessionParams s;
   s.tokyo = true;   // semua sesi: bar uji jatuh di jam berapa pun
   s.london = true;
   s.newYork = true;
   return s;
  }

void TseInit(CSignalEngine &eng, CMarketStructure &ms, CZoneBook &zb, CPaTrigger &pt, ISdbEventSink *sink, CState &st)
  {
   eng.Init(_Symbol, TSE_MAGIC, PERIOD_M15, TseParams(), GetPointer(ms), GetPointer(zb), GetPointer(pt), NULL, NULL, NULL, NULL,
            sink, SDB_STYLE_DAY, TseSessions(), 0, NULL, SDB_COMPONENT_SHADOW, SDB_COMPONENT_SHADOW);
   eng.SetState(GetPointer(st), TSE_LOGIN, 0);
  }

void RunTestSignalEngine()
  {
   TfBeginSuite("SignalEngine");
   CState st;
   st.Init("SDBTEST", TSE_LOGIN);
   st.DeleteAll();
   InputValues v = DefaultInputValues();
   SdbStructureParams sp;
   sp.strength = v.swingStrength;
   sp.lookback = v.structureLookback;
   sp.emaPeriod = v.emaPeriod;
   sp.slopeBars = v.emaSlopeBars;
   SdbZoneParams zp;
   zp.minWidthAtr = v.zoneMinWidthAtr;
   zp.maxWidthAtr = v.zoneMaxWidthAtr;
   zp.minLegAtr = v.zoneMinLegAtr;
   zp.legBars = v.zoneLegBars;
   zp.maxAge = v.maxZoneAgeBars;
   zp.strength = v.swingStrength;
   CMarketStructure ms;
   ms.Init(_Symbol, PERIOD_H4, PERIOD_H1, sp);
   CZoneBook zb;
   zb.Init(_Symbol, PERIOD_H1, zp, TSE_MAGIC);
   CPaTrigger pt;
   pt.Init(_Symbol, PERIOD_M15);
   ms.OnTick();
   zb.OnTick();
   pt.OnTick();

   CFakeSink sink;
   CSignalEngine eng;
   TseInit(eng, ms, zb, pt, GetPointer(sink), st);
   bool first = eng.OnTick();
   bool second = eng.OnTick();
   AssertTrue("TC-SGX-01", "OnTick dua kali di bar M15 yang sama: true lalu false", first && !second);

   CFakeSink sink2;
   CSignalEngine again;
   TseInit(again, ms, zb, pt, GetPointer(sink2), st);
   AssertTrue("TC-SGX-02", "engine baru, magic dan GV sama (restart): bar yang sama tidak dinilai ulang",
              !again.OnTick() && sink2.CountSignal() == 0);

   SdbSignalCounts c;
   eng.Counts(c);
   SignalRecord rec;
   bool candidate = c.candidates == 1 && sink.CountSignal() == 1 && sink.LastSignal(rec) && rec.id > 0 &&
                    rec.status == SDB_SIGNAL_STATUS_REJECTED && rec.rejectStage == SDB_REJECT_STAGE_NOT_TRADABLE &&
                    rec.scoreZone > 0 && rec.scoreTotal == rec.scoreZone + rec.scoreTrend + rec.scorePa &&
                    rec.time == pt.LastBarTime() && StringFind(rec.contextJson, "\"zone_status\"") > 0;
   bool notCandidate = c.candidates == 0 && c.noBias + c.noZone == 1 && sink.CountSignal() == 0;
   AssertTrue("TC-SGX-03", StringFormat("bar dinilai=%d: kandidat tercatat dengan skor (%d) atau dihitung bukan kandidat (bias %d, zona %d)",
                                        c.evaluated, c.candidates, c.noBias, c.noZone),
              c.evaluated == 1 && (candidate != notCandidate));
   st.DeleteAll();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTSIGNALENGINE_MQH
