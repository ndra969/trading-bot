//+------------------------------------------------------------------+
//| SignalEngine.mqh — CSignalEngine: pipeline sinyal per bar LTF
//| tertutup (spec 13 Req 1–6; design §3.2). Mengumpulkan fakta dari
//| analysis, risiko, akun, posisi, dan harga; keputusan di
//| SignalRules; bila lolos: lot -> pre-trade check -> order -> zona
//| Used. Setiap kandidat menjadi satu SignalRecord di event sink.
//+------------------------------------------------------------------+
#ifndef SDB_SIGNALS_SIGNALENGINE_MQH
#define SDB_SIGNALS_SIGNALENGINE_MQH

#include <SDBot/Core/State.mqh>
#include <SDBot/Core/EventSink.mqh>
#include <SDBot/Core/InputRules.mqh>
#include <SDBot/Account/Account.mqh>
#include <SDBot/Risk/RiskState.mqh>
#include <SDBot/Risk/RiskManager.mqh>
#include <SDBot/Execution/Executor.mqh>
#include <SDBot/Analysis/MarketStructure.mqh>
#include <SDBot/Analysis/ZoneBook.mqh>
#include <SDBot/Strategies/PaTrigger.mqh>
#include <SDBot/Signals/SignalRules.mqh>
#include <SDBot/Filters/NewsFilter.mqh>

// Hitungan per hari server (Req 6.4): bar yang bukan kandidat tidak punya baris signals.
struct SdbSignalCounts
  {
   int               evaluated;
   int               noBias;
   int               noZone;
   int               candidates;
   int               accepted;
  };

string SdbStyleText(const ENUM_SDB_TRADING_STYLE s)
  {
   switch(s)
     {
      case SDB_STYLE_SCALPING: return SDB_TRADING_STYLE_SCALPING;
      case SDB_STYLE_SWING:    return SDB_TRADING_STYLE_SWING;
      case SDB_STYLE_POSITION: return SDB_TRADING_STYLE_POSITION;
      default:                 return SDB_TRADING_STYLE_DAY;
     }
  }

class CSignalEngine
  {
private:
   string            m_symbol;
   long              m_magic;
   ENUM_TIMEFRAMES   m_ltf;
   SdbSignalParams   m_params;
   string            m_style;
   SdbSessionParams  m_sessions;      // filter sesi UTC (spec 14)
   CNewsFilter      *m_news;          // filter berita (spec 16); NULL = DISABLED
   int               m_testerUtcOffsetH;
   CMarketStructure *m_ms;
   CZoneBook        *m_zb;
   CPaTrigger       *m_pt;
   CRiskState       *m_rs;            // NULL di uji: tanpa cek STOPPED/pause
   CRiskManager     *m_rm;
   CExecutor        *m_exe;
   CAccount         *m_acc;           // NULL = tidak bisa trading
   ISdbEventSink    *m_sink;
   CState           *m_state;
   long              m_login;
   long              m_runKey;
   datetime          m_lastBar;
   long              m_day;           // hari server hitungan berjalan
   SdbSignalCounts   m_counts;

   bool   StateReady() const { return m_state != NULL && m_state.IsReady(); }

   // Selisih server-UTC: tester dari input, live dari TimeTradeServer - TimeGMT (spec 14 Req 1.4, 4.2).
   int UtcOffsetNow() const
     {
      bool tester = MQLInfoInteger(MQL_TESTER) != 0;
      datetime gmt = TimeGMT();
      if(!tester && gmt == 0)
        {
         LogThrottled(SDB_LOG_WARN, "signals-gmt", SDB_LOG_THROTTLE_DEFAULT_SEC, "Signals", "TimeGMT tidak tersedia, selisih UTC dianggap 0");
         return 0;
        }
      return ServerUtcOffsetSec(tester, m_testerUtcOffsetH, TimeTradeServer(), gmt);
     }
   string BarKey() const     { return IntegerToString(m_magic) + "_" + SDB_GV_SIGNAL_BAR; }

   // Penanda bar di GV sebelum penilaian, agar restart atau crash di tengah order tidak menilai bar yang sama lagi (Req 1.4).
   bool ClaimBar(const datetime t)
     {
      if(!StateReady())
         return true;
      if((datetime)(long)m_state.Get(BarKey(), 0.0) >= t)
         return false;
      if(!m_state.Set(BarKey(), (double)(long)t, true))
         LogError("Signals", "penanda bar sinyal tidak tersimpan | " + BarKey());
      return true;
     }

   void RollDay(const datetime t)
     {
      long day = (long)t / 86400;
      if(m_day != 0 && day != m_day)
        {
         LogDaySummary();
         ZeroMemory(m_counts);
        }
      m_day = day;
     }

   bool HasOwnPosition() const
     {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         if(PositionGetSymbol(i) != m_symbol)
            continue;
         if(PositionGetInteger(POSITION_MAGIC) == m_magic)
            return true;
        }
      return false;
     }

   void PreFilter(SdbSignalFacts &f)
     {
      f.preStage = "";
      f.preDetail = "";
      string why = "";
      if(m_rs != NULL && m_rs.IsStopped())
         f.preStage = SDB_REJECT_STAGE_STOPPED;
      else if(m_rs != NULL && m_rs.IsDailyPaused())
         f.preStage = SDB_REJECT_STAGE_DAILY_PAUSE;
      else if(m_acc == NULL || !m_acc.CanTrade(why))
        {
         f.preStage = SDB_REJECT_STAGE_NOT_TRADABLE;
         f.preDetail = (m_acc == NULL) ? "akun tidak tersedia" : why;
        }
     }

   void CollectFacts(const SdbBias &bias, const SdbZone &zone, SdbSignalFacts &f)
     {
      ZeroMemory(f);
      f.dir = bias.dir;
      f.zone = zone;
      PreFilter(f);
      f.positionOpen = HasOwnPosition();
      m_pt.Result(bias.dir, f.pattern);
      SdbTfAnalysis mtf;
      m_ms.Mtf(mtf);
      f.trendScore = TrendScore(bias.dir, mtf);
      f.bid = SymbolInfoDouble(m_symbol, SYMBOL_BID);
      f.ask = SymbolInfoDouble(m_symbol, SYMBOL_ASK);
      f.point = SymbolInfoDouble(m_symbol, SYMBOL_POINT);
      f.digits = (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS);
      f.stopsLevel = (int)SymbolInfoInteger(m_symbol, SYMBOL_TRADE_STOPS_LEVEL);
      f.atrMtf = m_zb.LastAtr();
      SdbZone opp;
      f.haveOpposite = m_zb.OppositeZone(bias.dir, bias.dir == SDB_DIR_BULL ? f.ask : f.bid, opp);
      f.oppositeProximal = f.haveOpposite ? opp.proximal : 0.0;
      ENUM_SDB_SESSION ses = SessionOfUtc(UtcSecOfDay(m_lastBar, UtcOffsetNow()));
      f.session = SessionText(ses);
      f.sessionAllowed = SessionAllowed(ses, m_sessions);
      f.spreadPoints = (f.point > 0.0) ? (long)MathRound((f.ask - f.bid) / f.point) : 0;
      f.newsStatus = SDB_NEWS_STATUS_DISABLED;
      f.newsBlocked = false;
      f.newsDetail = "";
      f.newsNext = "";
      if(m_news != NULL)
        {
         m_news.Refresh(TimeTradeServer());
         f.newsStatus = m_news.Status();
         f.newsBlocked = m_news.Blocked(m_lastBar, f.newsDetail);
         f.newsNext = m_news.NearestText(m_lastBar);
        }
     }

   // Lot dan pre-trade check Fase 1, lalu order; zona Used hanya setelah terisi (Req 4.7, 5.1–5.3).
   bool Execute(const SdbSignalFacts &f, const SdbDecision &d, const long id, string &stage, string &detail)
     {
      if(m_rm == NULL || m_exe == NULL)
        {
         stage = SDB_REJECT_STAGE_OTHER;
         detail = "risiko/eksekusi tidak tersedia";
         return false;
        }
      OrderRequest req;
      ZeroMemory(req);
      req.isBuy = (f.dir == SDB_DIR_BULL);
      req.sl = d.stops.sl;
      req.tp = d.stops.tp;
      req.signalId = id;
      if(!m_rm.CalcVolume(req, stage, detail) || !m_rm.PreTradeCheck(req, stage, detail))
         return false;
      OrderResult res;
      if(!m_exe.OpenMarket(req, res))
        {
         stage = (res.rejectStage != "") ? res.rejectStage : SDB_REJECT_STAGE_OTHER;
         detail = res.detail;
         return false;
        }
      if(!m_zb.MarkUsed(f.zone.id))
         LogError("Signals", "zona tidak bisa ditandai Used, posisi tetap | zona=" + f.zone.id);
      stage = "";
      detail = "";
      return true;
     }

   void Record(const SdbSignalFacts &f, const SdbDecision &d, const SdbBias &bias, const datetime t, const long id,
               const string status, const string stage, const string detail)
     {
      SignalRecord s;
      s.id = id;
      s.magic = m_magic;
      s.symbol = m_symbol;
      s.time = t;
      s.direction = (f.dir == SDB_DIR_BULL) ? SDB_DIRECTION_BUY : SDB_DIRECTION_SELL;
      s.style = m_style;
      s.zoneRef = f.zone.id;
      s.scoreTotal = d.total;
      s.spreadPoints = SymbolInfoInteger(m_symbol, SYMBOL_SPREAD);
      s.status = status;
      s.rejectStage = stage;
      s.rejectDetail = detail;
      s.contextJson = SignalContextJson(f, d, m_params, bias.reason);
      s.scoreZone = d.zoneScore;
      s.scoreTrend = d.trendScore;
      s.scorePa = d.paScore;
      if(m_sink != NULL)
         m_sink.OnSignal(s);
      string text = StringFormat("%s %s %s zona=%s skor=%d (%.1f%%) pola=%s", TimeToString(t), s.direction, status, f.zone.id, d.total,
                                 d.pct, f.pattern.code);
      if(status == SDB_SIGNAL_STATUS_ACCEPTED)
         LogInfo("Signals", "sinyal diterima | " + text + StringFormat(" sl=%s tp=%s rr=%.2f", DoubleToString(d.stops.sl, f.digits),
                                                                         DoubleToString(d.stops.tp, f.digits), d.stops.rr));
      else
         LogDebug("Signals", "kandidat ditolak | " + text + " tahap=" + stage + " " + detail);
     }

public:
                     CSignalEngine(void) : m_magic(0), m_ltf(PERIOD_CURRENT), m_ms(NULL), m_zb(NULL), m_pt(NULL), m_rs(NULL),
                     m_rm(NULL), m_exe(NULL), m_acc(NULL), m_sink(NULL), m_news(NULL), m_state(NULL), m_login(0), m_runKey(0), m_lastBar(0),
                     m_day(0) { ZeroMemory(m_counts); }

   void Init(const string symbol, const long magic, const ENUM_TIMEFRAMES ltf, const SdbSignalParams &p, CMarketStructure *ms,
             CZoneBook *zb, CPaTrigger *pt, CRiskState *rs, CRiskManager *rm, CExecutor *exe, CAccount *acc,
             ISdbEventSink *sink, const ENUM_SDB_TRADING_STYLE style, const SdbSessionParams &sessions, const int testerUtcOffsetHours,
             CNewsFilter *news)
     {
      m_symbol = symbol;
      m_magic = magic;
      m_ltf = ltf;
      m_params = p;
      m_style = SdbStyleText(style);
      m_sessions = sessions;
      m_news = news;
      m_testerUtcOffsetH = testerUtcOffsetHours;
      if(!SessionFilterOn(sessions))
         LogInfo("Signals", "filter sesi mati: ketiga input sesi false, entry diizinkan 24 jam");
      m_ms = ms;
      m_zb = zb;
      m_pt = pt;
      m_rs = rs;
      m_rm = rm;
      m_exe = exe;
      m_acc = acc;
      m_sink = sink;
      m_lastBar = 0;
      m_day = 0;
      ZeroMemory(m_counts);
     }

   // Dari EnsureState: penanda bar per magic dan kunci ID sinyal (login, run_key).
   void SetState(CState *state, const long login, const long runKey)
     {
      m_state = state;
      m_login = login;
      m_runKey = runKey;
     }

   // true bila bar LTF baru dinilai (kandidat atau bukan); false bila tidak ada bar baru, sudah dinilai, basi, atau belum siap.
   bool OnTick()
     {
      if(m_pt == NULL || m_ms == NULL || m_zb == NULL)
         return false;
      datetime t = m_pt.LastBarTime();
      if(t == 0 || t == m_lastBar)
         return false;
      m_lastBar = t;
      if(!ClaimBar(t))
         return false;
      RollDay(t);
      if(StaleLtfBar(t, PeriodSeconds(m_ltf), TimeCurrent()))
        {
         LogDebug("Signals", "bar basi tidak dinilai | bar=" + TimeToString(t));
         return false;
        }
      SdbBias bias;
      m_ms.Bias(bias);
      if(bias.reason == SDB_BIAS_DATA || !m_zb.Ready() || !m_pt.Ready())
        {
         LogThrottled(SDB_LOG_WARN, "signals-not-ready", SDB_LOG_THROTTLE_DEFAULT_SEC, "Signals",
                      "analisis belum siap (histori kurang), bar tidak dinilai");
         return false;
        }
      m_counts.evaluated++;
      if(bias.dir == SDB_DIR_NONE)
        {
         m_counts.noBias++;
         return true;
        }
      MqlRates bar;
      m_pt.LastBar(bar);
      SdbZone zone;
      if(!m_zb.TouchedZone(bias.dir, bar.low, bar.high, zone))
        {
         m_counts.noZone++;
         return true;
        }
      m_counts.candidates++;
      SdbSignalFacts f;
      CollectFacts(bias, zone, f);
      SdbDecision d;
      EvaluateSignal(f, m_params, d);
      long id = SignalIdOf(m_login, m_runKey, m_magic, t);
      string stage = d.stage, detail = d.detail;
      bool ok = (stage == "") && Execute(f, d, id, stage, detail);
      if(ok)
         m_counts.accepted++;
      Record(f, d, bias, t, id, ok ? SDB_SIGNAL_STATUS_ACCEPTED : SDB_SIGNAL_STATUS_REJECTED, stage, detail);
      return true;
     }

   void Counts(SdbSignalCounts &out) const { out = m_counts; }

   void LogDaySummary()
     {
      if(m_counts.evaluated == 0)
         return;
      LogInfo("Signals", StringFormat("ringkasan gerbang | hari=%s bar=%d tanpa_bias=%d tanpa_zona=%d kandidat=%d diterima=%d",
                                      TimeToString((datetime)(m_day * 86400), TIME_DATE), m_counts.evaluated, m_counts.noBias,
                                      m_counts.noZone, m_counts.candidates, m_counts.accepted));
     }
  };

#endif // SDB_SIGNALS_SIGNALENGINE_MQH
