//+------------------------------------------------------------------+
//| ClosureTracker.mqh — CClosureTracker: deal dan closure posisi milik
//| instance ini (spec 06 Req 6, design §4.5). Kepemilikan dari deal
//| pembuka, bukan magic deal penutup, agar close all lintas instance
//| (spec 05) tetap tercatat pemilik (EC-15). Tepat sekali: deal bertiket
//| <= GV LAST_DEAL per magic sudah diproses; DB punya kunci unik.
//+------------------------------------------------------------------+
#ifndef SDB_POSITION_CLOSURETRACKER_MQH
#define SDB_POSITION_CLOSURETRACKER_MQH

#include <SDBot/Core/State.mqh>
#include <SDBot/Position/PositionCache.mqh>
#include <SDBot/Position/ClosureRules.mqh>
#include <SDBot/Position/PositionMath.mqh>

class CClosureTracker
  {
private:
   long              m_magic;
   string            m_symbol;
   CPositionCache   *m_cache;
   CState           *m_state;
   ISdbEventSink    *m_sink;
   CNullSink         m_nullSink;
   int               m_bufferPts;
   double            m_totalR;
   int               m_tradesWithR;

   string LastDealName() const     { return IntegerToString(m_magic) + "_LAST_DEAL"; }
   string LastDealTimeName() const { return IntegerToString(m_magic) + "_LAST_DEAL_TIME"; }

   void MarkProcessed(const ulong ticket, const datetime t)
     {
      m_state.Set(LastDealName(), (double)ticket, false);
      m_state.Set(LastDealTimeName(), (double)t, true);
     }

   // Harga pemicu SL/TP: harga order penutup (order stop yang teraktivasi), atau harga deal.
   double LevelPrice(const ulong order, const double dealPrice)
     {
      if(order > 0 && HistoryOrderSelect(order))
        {
         double p = HistoryOrderGetDouble(order, ORDER_PRICE_OPEN);
         if(p > 0.0)
            return p;
        }
      return dealPrice;
     }

   // MFE/MAE dari bar M1 antara buka dan tutup (Req 6.5).
   void MfeMae(const PositionCacheEntry &e, const datetime closeTime, ClosureRecord &c)
     {
      double highs[], lows[];
      double r = (e.initialSl > 0.0) ? MathAbs(e.entry - e.initialSl) : 0.0;
      int nh = CopyHigh(e.symbol, PERIOD_M1, e.entryTime, closeTime, highs);
      int nl = CopyLow(e.symbol, PERIOD_M1, e.entryTime, closeTime, lows);
      if(nh <= 0 || nl <= 0)
        {
         ArrayFree(highs);
         ArrayFree(lows);
         LogInfo("Position", "bar M1 tidak tersedia, MFE/MAE kosong | pos=" + IntegerToString((long)e.positionId));
        }
      MfeMaeInR(e.isBuy, e.entry, r, highs, lows, c.mfeR, c.maeR);
     }

   // Req 6.2–6.6: jumlahkan semua deal posisi, alasan dari deal penutup terakhir.
   bool EmitClosure(const ulong positionId)
     {
      PositionCacheEntry e;
      if(!m_cache.Get(positionId, e) || !HistorySelectByPosition(positionId))
         return false;
      ClosureRecord c;
      ZeroMemory(c);
      int outs = 0;
      ulong lastOut = 0;
      for(int i = 0; i < HistoryDealsTotal(); i++)
        {
         ulong d = HistoryDealGetTicket(i);
         c.profit += HistoryDealGetDouble(d, DEAL_PROFIT);
         c.commission += HistoryDealGetDouble(d, DEAL_COMMISSION);
         c.swap += HistoryDealGetDouble(d, DEAL_SWAP);
         c.fee += HistoryDealGetDouble(d, DEAL_FEE);
         long entry = HistoryDealGetInteger(d, DEAL_ENTRY);
         if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY)
           {
            c.volumeTotal += HistoryDealGetDouble(d, DEAL_VOLUME);
            outs++;
            lastOut = d;
           }
        }
      if(lastOut == 0)
         return false;
      int digits = (int)SymbolInfoInteger(e.symbol, SYMBOL_DIGITS);
      double point = SymbolInfoDouble(e.symbol, SYMBOL_POINT);
      long reason = HistoryDealGetInteger(lastOut, DEAL_REASON);
      double price = HistoryDealGetDouble(lastOut, DEAL_PRICE);
      double level = LevelPrice((ulong)HistoryDealGetInteger(lastOut, DEAL_ORDER), price);
      double beSl = (e.beSl > 0.0) ? e.beSl : BreakevenSl(e.isBuy, e.entry, (int)SymbolInfoInteger(e.symbol, SYMBOL_SPREAD),
                                                         0, m_bufferPts, point, digits);
      c.positionId = (long)positionId;
      c.magic = m_magic;
      c.symbol = e.symbol;
      c.closedAt = (datetime)HistoryDealGetInteger(lastOut, DEAL_TIME);
      c.reason = MapCloseReason(reason, e.isBuy, e.entry, level, beSl, m_bufferPts + SDB_CLOSE_REASON_TOLERANCE_PTS, point,
                                IsSdbotMagic(HistoryDealGetInteger(lastOut, DEAL_MAGIC)));
      bool hasLevel = (reason == DEAL_REASON_SL || reason == DEAL_REASON_TP);
      c.levelPrice = hasLevel ? level : SDB_NULL_DOUBLE;
      c.slippagePoints = hasLevel ? (long)MathRound((e.isBuy ? price - level : level - price) / point) : SDB_NULL_LONG;
      c.priceClose = price;
      c.netProfit = c.profit + c.commission + c.swap + c.fee;
      c.rResult = ResultInR(c.netProfit, e.riskMoney);
      MfeMae(e, c.closedAt, c);
      c.holdingSec = (long)(c.closedAt - e.entryTime);
      c.partialDone = e.partialDone || outs > 1;
      c.trailActivated = e.trailDone || c.reason == SDB_CLOSE_REASON_TRAIL_STOP;
      c.beActivated = e.beDone || c.trailActivated || c.reason == SDB_CLOSE_REASON_BE_STOP;
      m_sink.OnClosure(c);
      NoteResult(c.rResult);
      m_cache.Remove(positionId);
      LogInfo("Position", StringFormat("posisi tutup | pos=%I64u alasan=%s net=%.2f R=%s", positionId, c.reason, c.netProfit,
                                       c.rResult == SDB_NULL_DOUBLE ? "?" : DoubleToString(c.rResult, 2)));
      return true;
     }

public:
                     CClosureTracker(void) : m_magic(0), m_cache(NULL), m_state(NULL), m_sink(NULL), m_bufferPts(0), m_totalR(0.0), m_tradesWithR(0) {}

   void Init(const long magic, const string symbol, CPositionCache *cache, CState *state, ISdbEventSink *sink, const int bufferPts)
     {
      m_magic = magic;
      m_symbol = symbol;
      m_cache = cache;
      m_state = state;
      m_sink = (sink == NULL) ? GetPointer(m_nullSink) : sink;
      m_bufferPts = bufferPts;
     }

   // Metrik OnTester (spec 07 Req 1.1, EC-06): R closure yang diketahui, di memori selama run.
   void NoteResult(const double rResult)
     {
      if(rResult == SDB_NULL_DOUBLE)
         return;
      m_totalR += rResult;
      m_tradesWithR++;
     }
   double TotalR() const      { return m_totalR; }
   int    TradesWithR() const { return m_tradesWithR; }

   ulong LastDeal() { return (m_state != NULL && m_state.IsReady()) ? (ulong)m_state.Get(LastDealName(), 0.0) : 0; }
   datetime LastDealTime() { return (m_state != NULL && m_state.IsReady()) ? (datetime)(long)m_state.Get(LastDealTimeName(), 0.0) : 0; }

   void OnTransaction(const MqlTradeTransaction &t)
     {
      if(t.type == TRADE_TRANSACTION_DEAL_ADD && t.deal > 0)
         ProcessDeal(t.deal);
     }

   // true = deal milik posisi instance ini diproses sekarang (Req 6.1, 6.7).
   bool ProcessDeal(const ulong dealTicket)
     {
      if(m_state == NULL || !m_state.IsReady() || dealTicket <= LastDeal() || !HistoryDealSelect(dealTicket))
         return false;
      DealRecord d;
      d.dealTicket = (long)dealTicket;
      d.positionId = HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID);
      d.magic = m_magic;
      d.symbol = HistoryDealGetString(dealTicket, DEAL_SYMBOL);
      d.time = (datetime)HistoryDealGetInteger(dealTicket, DEAL_TIME);
      d.entry = DealEntryText(HistoryDealGetInteger(dealTicket, DEAL_ENTRY));
      d.dealType = DealTypeText(HistoryDealGetInteger(dealTicket, DEAL_TYPE));
      d.volume = HistoryDealGetDouble(dealTicket, DEAL_VOLUME);
      d.price = HistoryDealGetDouble(dealTicket, DEAL_PRICE);
      d.reason = DealReasonText(HistoryDealGetInteger(dealTicket, DEAL_REASON));
      d.profit = HistoryDealGetDouble(dealTicket, DEAL_PROFIT);
      d.commission = HistoryDealGetDouble(dealTicket, DEAL_COMMISSION);
      d.swap = HistoryDealGetDouble(dealTicket, DEAL_SWAP);
      d.fee = HistoryDealGetDouble(dealTicket, DEAL_FEE);
      if(d.dealType == "" || d.positionId <= 0 || !m_cache.Owned((ulong)d.positionId))
         return false;
      m_sink.OnDeal(d);
      MarkProcessed(dealTicket, d.time);
      bool closing = (d.entry == SDB_DEAL_ENTRY_OUT || d.entry == SDB_DEAL_ENTRY_OUT_BY);
      if(closing && !PositionSelectByTicket((ulong)d.positionId) && !EmitClosure((ulong)d.positionId))
         LogThrottled(SDB_LOG_ERROR, "pos_closure", SDB_LOG_THROTTLE_DEFAULT_SEC, "Position",
                      "closure tidak bisa disusun dari history | pos=" + IntegerToString(d.positionId));
      return true;
     }
  };

#endif // SDB_POSITION_CLOSURETRACKER_MQH
