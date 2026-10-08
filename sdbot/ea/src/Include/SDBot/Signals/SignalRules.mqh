//+------------------------------------------------------------------+
//| SignalRules.mqh — aturan sinyal sebagai fungsi murni (spec 13
//| Req 1–6; design §3.1): skor per komponen, tahap tolak pertama
//| sesuai urutan PRD, entry/SL/TP/R:R dari zona, ID sinyal
//| deterministik, dan isi signals.context_json. Tanpa akses terminal.
//+------------------------------------------------------------------+
#ifndef SDB_SIGNALS_SIGNALRULES_MQH
#define SDB_SIGNALS_SIGNALRULES_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/SchemaEnums.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Analysis/MarketStructure.mqh>
#include <SDBot/Analysis/ZoneRules.mqh>
#include <SDBot/Strategies/PatternRules.mqh>
#include <SDBot/Filters/FilterRules.mqh>

// Bar LTF tertutup (barTime = waktu buka) yang sudah lebih tua dari 2 x LTF tidak dinilai (Req 1.3).
bool StaleLtfBar(const datetime barTime, const int ltfSec, const datetime now)
  {
   return (long)(now - barTime) > (long)SDB_SIGNAL_STALE_BARS * ltfSec;
  }

double ScorePct(const int total, const int maxActive)
  {
   return maxActive > 0 ? 100.0 * total / maxActive : 0.0;
  }

string ZoneStatusText(const ENUM_SDB_ZONE_STATUS s)
  {
   switch(s)
     {
      case SDB_ZONE_FRESH:   return "FRESH";
      case SDB_ZONE_TESTED:  return "TESTED";
      case SDB_ZONE_WEAK:    return "WEAK";
      case SDB_ZONE_INVALID: return "INVALID";
      default:               return "EXPIRED";
     }
  }

bool SgReject(string &stage, string &detail, const string s, const string d)
  {
   stage = s;
   detail = d;
   return false;
  }

// Entry market, SL dari batas jauh zona + buffer (SELL + spread), TP zona lawan atau minRR x R (Req 4.1–4.6).
bool BuildStops(const SdbSignalFacts &f, const SdbSignalParams &p, SdbStops &s, string &stage, string &detail)
  {
   ZeroMemory(s);
   bool buy = (f.dir == SDB_DIR_BULL);
   double spread = f.ask - f.bid;
   double eps = SDB_SIGNAL_EPS * f.atrMtf;
   s.entry = buy ? f.ask : f.bid;
   double sl = buy ? f.zone.distal - p.slBufferAtr * f.atrMtf : f.zone.distal + p.slBufferAtr * f.atrMtf + spread;
   s.sl = NormalizeDouble(sl, f.digits);
   s.risk = buy ? s.entry - s.sl : s.sl - s.entry;
   if(s.risk <= 0.0)
      return SgReject(stage, detail, SDB_REJECT_STAGE_INVALID_STOPS,
                      StringFormat("entry=%s sl=%s", DoubleToString(s.entry, f.digits), DoubleToString(s.sl, f.digits)));
   double minDist = MathMax(f.stopsLevel * f.point + spread, p.minSlAtr * f.atrMtf);
   if(s.risk < minDist - eps)
      return SgReject(stage, detail, SDB_REJECT_STAGE_SL_TOO_CLOSE,
                      StringFormat("r=%s min=%s", DoubleToString(s.risk, f.digits), DoubleToString(minDist, f.digits)));
   if(s.risk > p.maxSlAtr * f.atrMtf + eps)
      return SgReject(stage, detail, SDB_REJECT_STAGE_SL_TOO_FAR,
                      StringFormat("r=%s max=%s", DoubleToString(s.risk, f.digits), DoubleToString(p.maxSlAtr * f.atrMtf, f.digits)));
   if(f.haveOpposite)
     {
      s.tp = NormalizeDouble(f.oppositeProximal, f.digits);
      s.tpSource = SDB_TP_SOURCE_ZONE;
     }
   else
     {
      s.tp = NormalizeDouble(buy ? s.entry + p.minRR * s.risk : s.entry - p.minRR * s.risk, f.digits);
      s.tpSource = SDB_TP_SOURCE_RR;
     }
   double reward = buy ? s.tp - s.entry : s.entry - s.tp;
   s.rr = reward / s.risk;
   if(reward < p.minRR * s.risk - eps)
      return SgReject(stage, detail, SDB_REJECT_STAGE_RR_TOO_LOW, StringFormat("rr=%.2f min=%.2f", s.rr, p.minRR));
   return true;
  }

// Komponen konfirmasi Fase 5 yang ACTIVE: tambahan skor dan maksimum (PC-25; spec 18, 19). SHADOW hanya dicatat.
void ActiveConfirmations(const SdbSignalFacts &f, int &bonus, int &extraMax)
  {
   bonus = 0;
   extraMax = 0;
   if(f.fibMode == SDB_COMPONENT_ACTIVE)
     {
      bonus += f.fib.score;
      extraMax += SDB_SCORE_MAX_FIB;
     }
   if(f.tlMode == SDB_COMPONENT_ACTIVE)
     {
      bonus += f.tl.score;
      extraMax += SDB_SCORE_MAX_TRENDLINE;
     }
   if(f.boMode == SDB_COMPONENT_ACTIVE)
     {
      bonus += f.bo.score;
      extraMax += SDB_SCORE_MAX_BREAKOUT;
     }
   if(f.rsiMode == SDB_COMPONENT_ACTIVE)
     {
      bonus += f.rsi.score;
      extraMax += SDB_SCORE_MAX_RSI;
     }
  }

// Skor selalu dihitung; tahap tolak pertama dalam urutan PRD (Req 2.2–2.4, 3.1). Lot dan eksekusi di engine.
void EvaluateSignal(const SdbSignalFacts &f, const SdbSignalParams &p, SdbDecision &d)
  {
   ZeroMemory(d);
   d.stage = "";
   d.detail = "";
   bool patternOk = f.pattern.code != SDB_PA_PATTERN_NONE && f.pattern.dir == f.dir && f.dir != SDB_DIR_NONE;
   d.zoneScore = ZoneScore(f.zone);
   d.trendScore = f.trendScore;
   d.paScore = patternOk ? PaScore(f.pattern.code) : 0;
   d.total = d.zoneScore + d.trendScore + d.paScore;
   d.maxActive = SDB_SCORE_MAX_ACTIVE;
   // Spec 18-19: komponen konfirmasi dicatat di mode SHADOW, tetapi hanya ACTIVE yang mengubah skor gerbang dan maksimumnya.
   d.fibScore = (f.fibMode == SDB_COMPONENT_OFF) ? 0 : f.fib.score;
   d.tlScore = (f.tlMode == SDB_COMPONENT_OFF) ? 0 : f.tl.score;
   d.boScore = (f.boMode == SDB_COMPONENT_OFF) ? 0 : f.bo.score;
   d.rsiScore = (f.rsiMode == SDB_COMPONENT_OFF) ? 0 : f.rsi.score;   // RSI tidak punya tahap tolak (spec 21 Req 3)
   int bonus, extraMax;
   ActiveConfirmations(f, bonus, extraMax);
   d.total += bonus;
   d.maxActive += extraMax;
   d.pct = ScorePct(d.total, d.maxActive);
   if(f.preStage != "")
     {
      d.stage = f.preStage;
      d.detail = f.preDetail;
      return;
     }
   // Spec 23: zona valid adalah gerbang, jadi dinilai sebelum berita, sesi, dan spread; skor sudah terisi.
   if(!p.allowTestedZones && f.zone.status == SDB_ZONE_TESTED)
     {
      d.stage = SDB_REJECT_STAGE_NO_VALID_ZONE;
      d.detail = "zona TESTED (InpAllowTestedZones=false)";
      return;
     }
   if(f.newsBlocked)
     {
      d.stage = SDB_REJECT_STAGE_NEWS_BLACKOUT;
      d.detail = f.newsDetail;
      return;
     }
   if(!f.sessionAllowed)
     {
      d.stage = SDB_REJECT_STAGE_OUTSIDE_SESSION;
      d.detail = "sesi=" + f.session;
      return;
     }
   if(!SpreadAllowed(f.spreadPoints, p.maxSpreadPoints))
     {
      d.stage = SDB_REJECT_STAGE_SPREAD_TOO_WIDE;
      d.detail = StringFormat("spread=%I64d max=%d", f.spreadPoints, p.maxSpreadPoints);
      return;
     }
   if(f.positionOpen)
     {
      d.stage = SDB_REJECT_STAGE_POSITION_OPEN;
      return;
     }
   if(!patternOk)
     {
      d.stage = SDB_REJECT_STAGE_NO_PA_TRIGGER;
      d.detail = "pola=" + f.pattern.code;
      return;
     }
   if(d.pct < p.minScorePct - SDB_SIGNAL_EPS)
     {
      d.stage = SDB_REJECT_STAGE_SCORE_TOO_LOW;
      d.detail = StringFormat("skor=%d pct=%.1f min=%.1f", d.total, d.pct, p.minScorePct);
      return;
     }
   d.stopsKnown = true;
   BuildStops(f, p, d.stops, d.stage, d.detail);
  }

// 62 bit pertama SHA-256 "login|runKey|magic|barTime": sama setelah restart, beda antar akun/run/instance/bar (Req 5.1).
long SignalIdOf(const long login, const long runKey, const long magic, const datetime barTime)
  {
   string hex = Sha256Hex(StringFormat("%I64d|%I64d|%I64d|%I64d", login, runKey, magic, (long)barTime));
   ulong v = 0;
   for(int i = 0; i < 16 && i < StringLen(hex); i++)
     {
      ushort c = StringGetCharacter(hex, i);
      int nib = (c >= '0' && c <= '9') ? c - '0' : c - 'a' + 10;
      v = (v << 4) | (ulong)nib;
     }
   long id = (long)(v & 0x3FFFFFFFFFFFFFFF);
   return id == 0 ? 1 : id;
  }

// signals.context_json: JSON kanonik; harga yang belum dihitung = null (Req 6.1).
string SignalContextJson(const SdbSignalFacts &f, const SdbDecision &d, const SdbSignalParams &p, const string biasReason)
  {
   string k[] = {"atr_mtf", "bias_reason", "entry", "max_active", "pa", "rr", "score_pct", "sl", "tp", "tp_source", "zone_status",
                 "max_spread", "session", "news", "news_next", "fib_level", "fib_ratio", "tl_dist", "tl_slope",
                 "tl_touches", "bo_age", "bo_dist", "bo_level", "rsi_age", "rsi_diff", "rsi_pdiff"};
   string v[];
   ArrayResize(v, ArraySize(k));
   bool known = d.stopsKnown && d.stops.risk > 0.0;
   v[0] = DoubleToString(f.atrMtf, f.digits);
   v[1] = JsonStr(biasReason);
   v[2] = known ? DoubleToString(d.stops.entry, f.digits) : "null";
   v[3] = IntegerToString(d.maxActive);
   v[4] = JsonStr(f.pattern.code);
   v[5] = known && d.stops.tpSource != "" ? DoubleToString(d.stops.rr, 2) : "null";
   v[6] = DoubleToString(d.pct, 1);
   v[7] = known ? DoubleToString(d.stops.sl, f.digits) : "null";
   v[8] = known && d.stops.tpSource != "" ? DoubleToString(d.stops.tp, f.digits) : "null";
   v[9] = known && d.stops.tpSource != "" ? JsonStr(d.stops.tpSource) : "null";
   v[10] = JsonStr(ZoneStatusText(f.zone.status));
   v[11] = IntegerToString(p.maxSpreadPoints);
   v[12] = JsonStr(f.session);
   v[13] = JsonStr(f.newsStatus);
   v[14] = f.newsNext == "" ? "null" : JsonStr(f.newsNext);
   bool fib = f.fibMode != SDB_COMPONENT_OFF && f.fib.ratio >= 0.0;
   v[15] = fib && f.fib.level > 0.0 ? DoubleToString(f.fib.level, 3) : "null";
   v[16] = fib ? DoubleToString(f.fib.ratio, 3) : "null";
   bool tl = f.tlMode != SDB_COMPONENT_OFF && f.tl.touches > 0;
   v[17] = tl ? DoubleToString(f.tl.distAtr, 2) : "null";
   v[18] = tl ? DoubleToString(f.tl.slopeAtr, 3) : "null";
   v[19] = tl ? IntegerToString(f.tl.touches) : "null";
   bool bo = f.boMode != SDB_COMPONENT_OFF && f.bo.level > 0.0;
   v[20] = bo ? IntegerToString(f.bo.ageBars) : "null";
   v[21] = bo ? DoubleToString(f.bo.distAtr, 2) : "null";
   v[22] = bo ? DoubleToString(f.bo.level, f.digits) : "null";
   bool rs = f.rsiMode != SDB_COMPONENT_OFF && f.rsi.have;
   v[23] = rs ? IntegerToString(f.rsi.ageBars) : "null";
   v[24] = rs ? DoubleToString(f.rsi.rsiDiff, 1) : "null";
   v[25] = rs ? DoubleToString(f.rsi.priceDiffAtr, 2) : "null";
   return CanonicalJson(k, v);
  }

#endif // SDB_SIGNALS_SIGNALRULES_MQH
