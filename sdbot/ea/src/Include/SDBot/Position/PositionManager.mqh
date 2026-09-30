//+------------------------------------------------------------------+
//| PositionManager.mqh — CPositionManager: per tick untuk setiap posisi
//| instance (spec 06 Req 1–5, design §4.4): SL yang hilang, partial,
//| lalu satu modifikasi SL terbaik (BE atau trailing ATR). Status BE dan
//| partial disimpulkan dari posisi MT5 (Req 1.4). Kegagalan dicoba ulang
//| tiap 30 detik maks 3 kali per aksi, lalu satu MODIFY_FAILED + alert.
//+------------------------------------------------------------------+
#ifndef SDB_POSITION_POSITIONMANAGER_MQH
#define SDB_POSITION_POSITIONMANAGER_MQH

#include <SDBot/Core/InputRules.mqh>
#include <SDBot/Account/Account.mqh>
#include <SDBot/Execution/Executor.mqh>
#include <SDBot/Position/PositionCache.mqh>
#include <SDBot/Position/PositionMath.mqh>

// Pasar dan simbol untuk satu tick, dibaca sekali lalu dipakai semua posisi.
struct PmMarket
  {
   double            bid;
   double            ask;
   double            point;
   int               digits;
   int               spreadPts;
   int               stopsLevel;
   double            step;
   double            vMin;
   double            atr;             // 0 = belum tersedia (Req 4.4)
   datetime          ltfBar;
   datetime          now;
  };

class CPositionManager
  {
private:
   string            m_symbol;
   long              m_magic;
   InputValues       m_in;
   ENUM_TIMEFRAMES   m_ltf;
   int               m_atrHandle;
   CExecutor        *m_exe;
   CAccount         *m_acc;
   CPositionCache   *m_cache;
   ISdbEventSink    *m_sink;
   CNullSink         m_nullSink;

   void Event(const ulong ticket, const string type, const double slOld, const double slNew, const double volume,
              const double price, const int spreadPts, const string detail)
     {
      PositionEvent e;
      e.positionId = (long)ticket;
      e.time = TimeCurrent();
      e.type = type;
      e.slOld = slOld;
      e.slNew = slNew;
      e.volume = volume;
      e.price = price;
      e.spreadPoints = spreadPts;
      e.detail = detail;
      m_sink.OnPositionEvent(e);
     }

   void Alert(const string type, const ENUM_SDB_SEVERITY sev, const string message)
     {
      AlertEvent a;
      a.type = type;
      a.severity = sev;
      a.message = message;
      a.symbol = m_symbol;
      a.magic = m_magic;
      a.time = TimeCurrent();
      m_sink.OnAlert(a);
     }

   bool ReadMarket(PmMarket &m)
     {
      MqlTick t;
      if(!SymbolInfoTick(m_symbol, t) || t.bid <= 0.0 || t.ask <= 0.0)
         return false;
      m.bid = t.bid;
      m.ask = t.ask;
      m.point = SymbolInfoDouble(m_symbol, SYMBOL_POINT);
      m.digits = (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS);
      m.spreadPts = (int)MathRound((t.ask - t.bid) / m.point);
      m.stopsLevel = (int)SymbolInfoInteger(m_symbol, SYMBOL_TRADE_STOPS_LEVEL);
      m.step = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_STEP);
      m.vMin = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MIN);
      m.ltfBar = iTime(m_symbol, m_ltf, 0);
      m.now = TimeLocal();
      double buf[];
      m.atr = (m_atrHandle != INVALID_HANDLE && CopyBuffer(m_atrHandle, 0, 1, 1, buf) == 1) ? buf[0] : 0.0;
      if(m.atr <= 0.0)
         LogThrottled(SDB_LOG_DEBUG, "pos_atr", SDB_LOG_THROTTLE_DEFAULT_SEC, "Position", "ATR belum tersedia, trailing dilewati");
      return true;
     }

   // Req 5.3: penghitung retry di-reset bila kondisi posisi (SL atau volume) berubah.
   void ResetFailsIfChanged(PositionCacheEntry &e, const double sl, const double vol)
     {
      for(int a = 0; a < SDB_ACT_COUNT; a++)
         if(e.fails[a] > 0 && (MathAbs(e.failKeySl[a] - sl) > 1e-10 || MathAbs(e.failKeyVol[a] - vol) > 1e-10))
           {
            e.fails[a] = 0;
            e.failAlerted[a] = false;
           }
     }

   void NoteFail(PositionCacheEntry &e, const ENUM_SDB_POS_ACTION a, const ulong ticket, const double sl, const double vol,
                 const datetime now, const string op, const string why)
     {
      e.fails[a]++;
      e.lastFail[a] = now;
      e.failKeySl[a] = sl;
      e.failKeyVol[a] = vol;
      LogWarn("Position", StringFormat("%s gagal ke-%d | pos=%I64u %s", op, e.fails[a], ticket, why));
      if(e.fails[a] < SDB_MODIFY_MAX_ATTEMPTS || e.failAlerted[a])
         return;
      e.failAlerted[a] = true;
      if(a == SDB_ACT_RESTORE)
        {
         Alert(SDB_ALERT_TYPE_SL_MISSING, SDB_SEV_CRITICAL,
               StringFormat("Posisi %I64u TANPA SL: pemasangan ulang gagal %d kali (%s)", ticket, e.fails[a], why));
         return;
        }
      Event(ticket, SDB_POSITION_EVENT_MODIFY_FAILED, sl, SDB_NULL_DOUBLE, vol, 0.0, 0, op + ": " + why);
      Alert(SDB_ALERT_TYPE_MODIFY_FAILED, SDB_SEV_MEDIUM, StringFormat("%s posisi %I64u gagal %d kali: %s", op, ticket, e.fails[a], why));
     }

   // Req 5.5: SL dihapus manual -> SL awal bila valid, atau SL valid terdekat.
   void TryRestoreSl(PositionCacheEntry &e, const ulong ticket, const PmMarket &m, const double vol)
     {
      if(!RetryDue(e.fails[SDB_ACT_RESTORE], e.lastFail[SDB_ACT_RESTORE], m.now))
         return;
      double price = e.isBuy ? m.bid : m.ask;
      double target = RestoreSl(e.isBuy, e.initialSl, price, m.stopsLevel, m.spreadPts, m.point, m.digits);
      string why;
      ENUM_SDB_EXEC r = m_exe.ModifySl(ticket, target, why, false);
      if(r == SDB_EXEC_OK)
        {
         Event(ticket, SDB_POSITION_EVENT_SL_RESTORED, SDB_NULL_DOUBLE, target, vol, price, m.spreadPts, "");
         Alert(SDB_ALERT_TYPE_SL_RESTORED, SDB_SEV_HIGH, StringFormat("SL posisi %I64u hilang, dipasang kembali di %s", ticket,
                                                                     DoubleToString(target, m.digits)));
        }
      else if(r != SDB_EXEC_GONE)
         NoteFail(e, SDB_ACT_RESTORE, ticket, 0.0, vol, m.now, "pasang ulang SL", why);
     }

   // Req 3: partial dari volume awal; dilewati sekali bila volume terlalu kecil. true = posisi masih ada.
   bool Partial(PositionCacheEntry &e, const ulong ticket, const PmMarket &m, const double sl, double &vol)
     {
      bool skip = false;
      double pv = PartialVolume(e.initialVolume, m_in.partialPct, m.step, m.vMin, vol, skip);
      double price = e.isBuy ? m.bid : m.ask;
      if(skip)
        {
         if(!e.partialSkippedLogged)
           {
            e.partialSkippedLogged = true;
            Event(ticket, SDB_POSITION_EVENT_PARTIAL_SKIPPED, SDB_NULL_DOUBLE, SDB_NULL_DOUBLE, vol, price, m.spreadPts,
                  StringFormat("volume awal %.2f terlalu kecil untuk %.0f%%", e.initialVolume, m_in.partialPct));
           }
         return true;
        }
      if(!RetryDue(e.fails[SDB_ACT_PARTIAL], e.lastFail[SDB_ACT_PARTIAL], m.now))
         return true;
      string why;
      ENUM_SDB_EXEC r = m_exe.ClosePartial(ticket, pv, why, false);
      if(r == SDB_EXEC_GONE)
         return false;
      if(r == SDB_EXEC_FAILED)
         NoteFail(e, SDB_ACT_PARTIAL, ticket, sl, vol, m.now, "partial", why);
      if(r != SDB_EXEC_OK)
         return true;
      e.partialDone = true;
      Event(ticket, SDB_POSITION_EVENT_PARTIAL, SDB_NULL_DOUBLE, SDB_NULL_DOUBLE, pv, price, m.spreadPts, "");
      Alert(SDB_ALERT_TYPE_PARTIAL_CLOSED, SDB_SEV_INFO, StringFormat("Partial %.2f lot posisi %I64u di %s", pv, ticket,
                                                                     DoubleToString(price, m.digits)));
      if(!PositionSelectByTicket(ticket))
         return false;
      vol = PositionGetDouble(POSITION_VOLUME);
      return true;
     }

   // Nilai uang 1 point untuk volume ini: komisi dikonversi ke point (Req 2.1).
   double MoneyPerPoint(const bool isBuy, const double vol, const double open, const double point)
     {
      double p = 0.0;
      if(!OrderCalcProfit(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, m_symbol, vol, open, isBuy ? open + point : open - point, p))
         return 0.0;
      return MathAbs(p);
     }

   // Req 2, 4, 5.2: satu modifikasi SL terbaik antara BE dan trailing.
   void MoveSl(PositionCacheEntry &e, const ulong ticket, const PmMarket &m, const double open, const double sl, const double vol,
               const double profitR, const bool known)
     {
      bool beActive = IsBreakevenActive(e.isBuy, open, sl);
      double price = e.isBuy ? m.bid : m.ask;
      double beCand = 0.0;
      if(ShouldBreakeven(profitR, m_in.breakevenR, beActive, known))
         beCand = BreakevenSl(e.isBuy, open, m.spreadPts, CommissionPoints(e.commission * vol / MathMax(e.initialVolume, 1e-9),
                              MoneyPerPoint(e.isBuy, vol, open, m.point)), m_in.breakevenBufferPoints, m.point, m.digits);
      double trailCand = (beActive && m.atr > 0.0) ? TrailingSl(e.isBuy, price, m.atr, m_in.trailAtrMult, m.digits) : 0.0;
      double best = PickBestSl(e.isBuy, sl, beCand, trailCand, SDB_MIN_SL_STEP_POINTS, m.point);
      if(best <= 0.0)
         return;
      ENUM_SDB_POS_ACTION act = (trailCand > 0.0 && MathAbs(best - trailCand) < m.point / 2) ? SDB_ACT_TRAIL : SDB_ACT_BE;
      if(!RetryDue(e.fails[act], e.lastFail[act], m.now))
         return;
      string why;
      ENUM_SDB_EXEC r = m_exe.ModifySl(ticket, best, why, false);
      if(r == SDB_EXEC_FAILED)
         NoteFail(e, act, ticket, sl, vol, m.now, act == SDB_ACT_BE ? "breakeven" : "trailing", why);
      if(r != SDB_EXEC_OK)
         return;   // SKIPPED: SL belum valid terhadap harga/stops, dicoba tick berikutnya tanpa dihitung gagal (Req 2.2)
      if(act == SDB_ACT_BE)
        {
         e.beSl = best;
         e.beDone = true;
         Event(ticket, SDB_POSITION_EVENT_BE, sl, best, vol, price, m.spreadPts, "");
         Alert(SDB_ALERT_TYPE_BE_MOVED, SDB_SEV_INFO, StringFormat("Breakeven posisi %I64u: SL %s -> %s", ticket,
                                                                  DoubleToString(sl, m.digits), DoubleToString(best, m.digits)));
         return;
        }
      bool first = !e.trailDone;
      e.trailDone = true;
      if(first || e.lastTrailEventBar != m.ltfBar)   // Req 4.5: paling sering satu event per bar LTF
        {
         e.lastTrailEventBar = m.ltfBar;
         Event(ticket, SDB_POSITION_EVENT_TRAILING, sl, best, vol, price, m.spreadPts, "");
        }
     }

   void Manage(const ulong ticket, const PmMarket &m)
     {
      if(!PositionSelectByTicket(ticket))
         return;
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double vol = PositionGetDouble(POSITION_VOLUME);
      PositionCacheEntry e;
      if(!m_cache.Get(ticket, e))
         return;
      bool known = (e.slSource != SDB_SL_SRC_NONE);
      if(!known && !e.slUnknownLogged)
        {
         e.slUnknownLogged = true;
         LogError("Position", "SL awal tidak diketahui, BE dan partial dilewati | pos=" + IntegerToString((long)ticket));
        }
      ResetFailsIfChanged(e, sl, vol);
      e.beDone = e.beDone || IsBreakevenActive(e.isBuy, open, sl);   // setelah restart: disimpulkan dari posisi
      e.partialDone = e.partialDone || vol < e.initialVolume - 1e-9;
      if(sl <= 0.0)
         TryRestoreSl(e, ticket, m, vol);
      else
        {
         double profitR = ProfitInR(e.isBuy, open, e.initialSl, e.isBuy ? m.bid : m.ask);
         bool alive = true;
         if(ShouldPartial(profitR, m_in.partialR, vol, e.initialVolume, known))
            alive = Partial(e, ticket, m, sl, vol);
         if(alive && PositionSelectByTicket(ticket))
            MoveSl(e, ticket, m, open, PositionGetDouble(POSITION_SL), vol, profitR, known);
        }
      m_cache.Update(e);
     }

public:
                     CPositionManager(void) : m_magic(0), m_ltf(PERIOD_M15), m_atrHandle(INVALID_HANDLE), m_exe(NULL),
                     m_acc(NULL), m_cache(NULL), m_sink(NULL) {}

   bool Init(const string symbol, const long magic, const InputValues &inputs, const ENUM_TIMEFRAMES ltf, const int atrHandle,
             CExecutor *exe, CAccount *acc, CPositionCache *cache, ISdbEventSink *sink)
     {
      m_symbol = symbol;
      m_magic = magic;
      m_in = inputs;
      m_ltf = ltf;
      m_atrHandle = atrHandle;
      m_exe = exe;
      m_acc = acc;
      m_cache = cache;
      m_sink = (sink == NULL) ? GetPointer(m_nullSink) : sink;
      return exe != NULL && acc != NULL && cache != NULL;
     }

   // Req 5.1, 5.6: tiket dikumpulkan dulu karena partial/modify mengubah daftar posisi.
   void OnTick()
     {
      string why;
      if(m_acc == NULL || !m_acc.CanTrade(why))
         return;
      PmMarket m;
      if(!ReadMarket(m))
         return;
      ulong tickets[];
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong t = PositionGetTicket(i);
         if(t == 0 || PositionGetInteger(POSITION_MAGIC) != m_magic || PositionGetString(POSITION_SYMBOL) != m_symbol)
            continue;
         int n = ArraySize(tickets);
         ArrayResize(tickets, n + 1);
         tickets[n] = t;
        }
      for(int i = 0; i < ArraySize(tickets); i++)
         Manage(tickets[i], m);
     }
  };

#endif // SDB_POSITION_POSITIONMANAGER_MQH
