//+------------------------------------------------------------------+
//| Executor.mqh — CExecutor: satu-satunya pintu ke broker (spec 04
//| Req 1–5, design §4.2). Memiliki CTrade; keputusan (validasi, retry,
//| komentar, ID permintaan) diambil dari ExecutionRules.mqh. Hanya
//| menyentuh posisi dengan magic dan simbol instance ini.
//+------------------------------------------------------------------+
#ifndef SDB_EXECUTION_EXECUTOR_MQH
#define SDB_EXECUTION_EXECUTOR_MQH

#include <Trade/Trade.mqh>
#include <SDBot/Core/EventSink.mqh>
#include <SDBot/Core/State.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Account/Account.mqh>
#include <SDBot/Execution/ExecutionRules.mqh>

class CExecutor
  {
private:
   CTrade            m_trade;
   long              m_magic;
   string            m_symbol;
   CAccount         *m_acc;
   CState           *m_state;
   ISdbEventSink    *m_sink;
   CNullSink         m_nullSink;
   string            m_eaVersion;
   long              m_sendCount;
   long              m_memCounter;    // cadangan bila GV penghitung gagal ditulis

   void SendAlert(const string type, const string message)
     {
      AlertEvent a;
      a.type = type;
      a.severity = SDB_SEV_MEDIUM;
      a.message = message;
      a.symbol = m_symbol;
      a.magic = m_magic;
      a.time = TimeCurrent();
      m_sink.OnAlert(a);
     }

   string CounterName() const { return IntegerToString(m_magic) + "_REQ_COUNTER"; }

   // Dinaikkan dan di-flush sebelum kiriman pertama, agar restart tidak mengulang ID (Req 5.3, EC-14).
   string NextRequestId()
     {
      long c = m_memCounter + 1;
      bool ready = (m_state != NULL && m_state.IsReady());
      if(ready)
         c = MathMax(c, (long)m_state.Get(CounterName(), 0) + 1);
      m_memCounter = c;
      if(!ready || !m_state.Set(CounterName(), (double)c, true))
         LogThrottled(SDB_LOG_ERROR, "exec_req_counter", SDB_LOG_THROTTLE_DEFAULT_SEC, "Execution",
                      "penghitung ID permintaan tidak tersimpan di GV, memakai penghitung memori | counter=" + IntegerToString(c));
      return MakeRequestId(m_magic, c);
     }

   bool EndsWithRequestId(const string comment, const string requestId) const
     {
      string tail = "|" + requestId;
      int pos = StringFind(comment, tail);
      return pos >= 0 && pos == StringLen(comment) - StringLen(tail);
     }

   // Setelah retcode ambigu: posisi terbuka atau deal masuk dengan ID yang sama (Req 2.3, EC-01, EC-13).
   bool FindByRequestId(const string requestId, OrderResult &res)
     {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong ticket = PositionGetTicket(i);
         if(ticket == 0 || PositionGetInteger(POSITION_MAGIC) != m_magic || PositionGetString(POSITION_SYMBOL) != m_symbol)
            continue;
         if(!EndsWithRequestId(PositionGetString(POSITION_COMMENT), requestId))
            continue;
         res.positionId = PositionGetInteger(POSITION_IDENTIFIER);
         res.priceFilled = PositionGetDouble(POSITION_PRICE_OPEN);
         res.volumeFilled = PositionGetDouble(POSITION_VOLUME);
         return true;
        }
      datetime now = TimeCurrent();
      if(!HistorySelect(now - SDB_AMBIGUOUS_LOOKBACK_SEC, now + 60))
         return false;
      for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
        {
         ulong deal = HistoryDealGetTicket(i);
         if(deal == 0 || HistoryDealGetInteger(deal, DEAL_MAGIC) != m_magic || HistoryDealGetString(deal, DEAL_SYMBOL) != m_symbol ||
            HistoryDealGetInteger(deal, DEAL_ENTRY) != DEAL_ENTRY_IN)
            continue;
         if(!EndsWithRequestId(HistoryDealGetString(deal, DEAL_COMMENT), requestId))
            continue;
         res.dealTicket = (long)deal;
         res.positionId = HistoryDealGetInteger(deal, DEAL_POSITION_ID);
         res.priceFilled = HistoryDealGetDouble(deal, DEAL_PRICE);
         res.volumeFilled = HistoryDealGetDouble(deal, DEAL_VOLUME);
         return true;
        }
      return false;
     }

   // Total volume semua posisi simbol ini searah (SYMBOL_VOLUME_LIMIT berlaku per simbol dan arah).
   double SymbolVolume(const bool isBuy)
     {
      double total = 0.0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         if(PositionGetTicket(i) == 0 || PositionGetString(POSITION_SYMBOL) != m_symbol)
            continue;
         bool buy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
         if(buy == isBuy)
            total += PositionGetDouble(POSITION_VOLUME);
        }
      return total;
     }

   bool Reject(OrderResult &res, const string stage, const string detail)
     {
      res.ok = false;
      res.rejectStage = stage;
      res.detail = detail;
      LogThrottled(SDB_LOG_WARN, "exec_reject_" + stage, SDB_LOG_THROTTLE_DEFAULT_SEC, "Execution",
                   "order ditolak sebelum kirim | stage=" + stage + " " + detail);
      return false;
     }

   // Validasi terhadap harga terbaru; dipanggil sebelum kiriman pertama dan setiap ulangan (Req 2.2).
   bool ValidateNow(const OrderRequest &req, const double sl, const double tp, double &price, OrderResult &res)
     {
      MqlTick tick;
      if(!SymbolInfoTick(m_symbol, tick) || tick.ask <= 0.0 || tick.bid <= 0.0)
         return Reject(res, SDB_REJECT_STAGE_OTHER, "harga simbol belum tersedia " + ErrText(GetLastError()));
      double point = SymbolInfoDouble(m_symbol, SYMBOL_POINT);
      price = req.isBuy ? tick.ask : tick.bid;
      res.priceRequested = price;
      res.spreadPts = (long)MathRound((tick.ask - tick.bid) / point);
      string why;
      string stage = ValidateOrderSides(req.isBuy, price, sl, tp);
      if(stage != "")
         return Reject(res, stage, StringFormat("SL %s / TP %s di sisi harga yang salah (harga %s)",
                                               DoubleToString(sl, 8), DoubleToString(tp, 8), DoubleToString(price, 8)));
      if(!CheckStops(price, sl, tp, (int)SymbolInfoInteger(m_symbol, SYMBOL_TRADE_STOPS_LEVEL),
                     (int)SymbolInfoInteger(m_symbol, SYMBOL_TRADE_FREEZE_LEVEL), (int)res.spreadPts, point, why))
         return Reject(res, SDB_REJECT_STAGE_SL_TOO_CLOSE, why);
      if(!CheckVolume(req.volume, SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MIN), SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MAX),
                      SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_STEP), SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_LIMIT),
                      SymbolVolume(req.isBuy), why))
         return Reject(res, SDB_REJECT_STAGE_INVALID_VOLUME, why);
      return true;
     }

   // OrderCheck sebelum setiap kiriman (Req 1.6).
   bool PreCheck(const OrderRequest &req, const double price, const double sl, const double tp, const string comment, OrderResult &res)
     {
      MqlTradeRequest rq;
      MqlTradeCheckResult cr;
      ZeroMemory(rq);
      ZeroMemory(cr);
      rq.action = TRADE_ACTION_DEAL;
      rq.symbol = m_symbol;
      rq.magic = (ulong)m_magic;
      rq.volume = req.volume;
      rq.type = req.isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      rq.price = price;
      rq.sl = sl;
      rq.tp = tp;
      rq.deviation = SDB_MAX_DEVIATION_POINTS;
      rq.type_filling = PickFillingMode(SymbolInfoInteger(m_symbol, SYMBOL_FILLING_MODE));
      rq.comment = comment;
      if(OrderCheck(rq, cr))
         return true;
      res.retcode = cr.retcode;
      string detail = StringFormat("OrderCheck retcode=%u %s margin_free=%.2f", cr.retcode, cr.comment, cr.margin_free);
      if(cr.retcode == TRADE_RETCODE_NO_MONEY || cr.margin_free < 0.0)
         return Reject(res, SDB_REJECT_STAGE_MARGIN_LOW, detail);
      return Reject(res, SDB_REJECT_STAGE_BROKER_REJECTED, detail);
     }

   // Harga isi, volume, position ID, risiko, lalu TradeRecord ke sink (Req 3).
   void RecordFill(const OrderRequest &req, const double sl, const double tp, OrderResult &res)
     {
      int digits = (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS);
      double point = SymbolInfoDouble(m_symbol, SYMBOL_POINT);
      datetime openedAt = TimeCurrent();
      if(res.dealTicket > 0 && HistoryDealSelect((ulong)res.dealTicket))
        {
         if(res.positionId <= 0)
            res.positionId = HistoryDealGetInteger((ulong)res.dealTicket, DEAL_POSITION_ID);
         if(res.priceFilled <= 0.0)
            res.priceFilled = HistoryDealGetDouble((ulong)res.dealTicket, DEAL_PRICE);
         if(res.volumeFilled <= 0.0)
            res.volumeFilled = HistoryDealGetDouble((ulong)res.dealTicket, DEAL_VOLUME);
         openedAt = (datetime)HistoryDealGetInteger((ulong)res.dealTicket, DEAL_TIME);
        }
      if(res.volumeFilled <= 0.0)
         res.volumeFilled = req.volume;
      if(res.priceFilled <= 0.0)
        {
         res.priceFilled = res.priceRequested;
         res.slippagePts = SDB_NULL_LONG;
         LogWarn("Execution", "harga isi tidak diketahui, dicatat = harga diminta | id=" + res.requestId);
        }
      else
         res.slippagePts = SlippagePoints(req.isBuy, res.priceRequested, res.priceFilled, point);
      if(res.volumeFilled < req.volume - SDB_VOLUME_EPS)
         LogWarn("Execution", StringFormat("partial fill | diminta=%.2f terisi=%.2f id=%s", req.volume, res.volumeFilled, res.requestId));

      double profitAtSl = 0.0;
      double balance = AccountInfoDouble(ACCOUNT_BALANCE);
      res.riskMoney = SDB_NULL_DOUBLE;
      if(OrderCalcProfit(req.isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, m_symbol, res.volumeFilled, res.priceFilled, sl, profitAtSl))
         res.riskMoney = -profitAtSl;
      else
         LogWarn("Execution", "risiko uang tidak bisa dihitung | " + ErrText(GetLastError()));

      TradeRecord t;
      t.positionId = res.positionId;
      t.magic = m_magic;
      t.symbol = m_symbol;
      t.direction = req.isBuy ? SDB_DIRECTION_BUY : SDB_DIRECTION_SELL;
      t.source = SDB_TRADE_SOURCE_EA;
      t.volumeInitial = res.volumeFilled;
      t.priceRequested = res.priceRequested;
      t.priceOpen = res.priceFilled;
      t.slippagePoints = res.slippagePts;
      t.spreadPoints = res.spreadPts;
      t.slInitial = sl;
      t.tpInitial = tp;
      t.riskMoney = res.riskMoney;
      t.riskPct = (res.riskMoney != SDB_NULL_DOUBLE && balance > 0.0) ? res.riskMoney / balance * 100.0 : SDB_NULL_DOUBLE;
      t.signalId = req.signalId;
      t.eaVersion = m_eaVersion;
      t.openedAt = openedAt;
      m_sink.OnTradeOpened(t);
      LogInfo("Execution", StringFormat("order terisi | %s %.2f @ %s sl=%s tp=%s pos=%I64d id=%s slip=%s",
                                        t.direction, res.volumeFilled, DoubleToString(res.priceFilled, digits),
                                        DoubleToString(sl, digits), DoubleToString(tp, digits), res.positionId,
                                        res.requestId, res.slippagePts == SDB_NULL_LONG ? "?" : IntegerToString(res.slippagePts)));
     }

   bool SelectOwn(const ulong positionId)
     {
      return PositionSelectByTicket(positionId) && PositionGetInteger(POSITION_MAGIC) == m_magic &&
             PositionGetString(POSITION_SYMBOL) == m_symbol;
     }

   // Satu langkah retry bersama untuk modify/close (Req 4.6). true = berhenti dengan hasil di out.
   bool HandleRetcode(const int attempt, const string op, const string alertType, const ulong positionId,
                      ENUM_SDB_EXEC &out, string &why)
     {
      uint rc = m_trade.ResultRetcode();
      ENUM_SDB_NEXT_STEP step = NextStep(ClassifyRetcode(rc), attempt, false);
      if(step == SDB_STEP_SUCCEED)
        {
         out = SDB_EXEC_OK;
         return true;
        }
      if(step == SDB_STEP_GONE)
        {
         out = SDB_EXEC_GONE;
         return true;
        }
      why = StringFormat("%s retcode=%u %s", op, rc, m_trade.ResultRetcodeDescription());
      if(step == SDB_STEP_RETRY)
        {
         LogWarn("Execution", why + " | ulang ke-" + IntegerToString(attempt) + " pos=" + IntegerToString((long)positionId));
         Sleep(SDB_RETRY_DELAY_MS);
         return false;
        }
      LogError("Execution", why + " | menyerah pos=" + IntegerToString((long)positionId));
      SendAlert(alertType, StringFormat("%s gagal untuk posisi %I64d: %s", op, (long)positionId, why));
      out = SDB_EXEC_FAILED;
      return true;
     }

public:
                     CExecutor(void) : m_magic(0), m_acc(NULL), m_state(NULL), m_sink(NULL), m_sendCount(0), m_memCounter(0) {}

   bool Init(const long magic, const string symbol, CAccount *acc, CState *state, ISdbEventSink *sink, const string eaVersion)
     {
      m_magic = magic;
      m_symbol = symbol;
      m_acc = acc;
      m_state = state;
      m_sink = (sink == NULL) ? GetPointer(m_nullSink) : sink;
      m_eaVersion = eaVersion;
      m_trade.SetExpertMagicNumber((ulong)magic);
      m_trade.SetDeviationInPoints(SDB_MAX_DEVIATION_POINTS);
      m_trade.SetAsyncMode(false);
      m_trade.SetTypeFilling(PickFillingMode(SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE)));
      m_trade.LogLevel(LOG_LEVEL_NO);   // semua log lewat Utils.mqh
      return true;
     }

   // Market order dengan SL dan TP wajib. false = ditolak atau gagal; alasan di res (Req 3.4).
   bool OpenMarket(const OrderRequest &req, OrderResult &res)
     {
      ZeroMemory(res);
      res.slippagePts = SDB_NULL_LONG;
      res.riskMoney = SDB_NULL_DOUBLE;
      string why;
      if(m_acc == NULL || !m_acc.CanTrade(why))
         return Reject(res, SDB_REJECT_STAGE_NOT_TRADABLE, why);
      int digits = (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS);
      double sl = NormalizeDouble(req.sl, digits);
      double tp = NormalizeDouble(req.tp, digits);
      res.requestId = NextRequestId();
      string comment = BuildOrderComment(sl, digits, res.requestId);
      for(int attempt = 1; ; attempt++)
        {
         res.attempts = attempt;
         double price;
         if(!ValidateNow(req, sl, tp, price, res) || !PreCheck(req, price, sl, tp, comment, res))
            return false;
         m_sendCount++;
         if(req.isBuy)
            m_trade.Buy(req.volume, m_symbol, price, sl, tp, comment);
         else
            m_trade.Sell(req.volume, m_symbol, price, sl, tp, comment);
         res.retcode = m_trade.ResultRetcode();
         res.dealTicket = (long)m_trade.ResultDeal();
         res.priceFilled = m_trade.ResultPrice();
         res.volumeFilled = m_trade.ResultVolume();
         ENUM_SDB_RETCODE_CLASS cls = ClassifyRetcode(res.retcode);
         bool found = (cls == SDB_RC_AMBIGUOUS) && FindByRequestId(res.requestId, res);
         ENUM_SDB_NEXT_STEP step = NextStep(cls, attempt, found);
         if(step == SDB_STEP_SUCCEED)
           {
            res.ok = true;
            RecordFill(req, sl, tp, res);
            return true;
           }
         string desc = StringFormat("retcode=%u %s", res.retcode, m_trade.ResultRetcodeDescription());
         if(step == SDB_STEP_RETRY)
           {
            LogWarn("Execution", "kirim order diulang | " + desc + " ke-" + IntegerToString(attempt) + " id=" + res.requestId);
            Sleep(SDB_RETRY_DELAY_MS);
            continue;
           }
         res.rejectStage = SDB_REJECT_STAGE_BROKER_REJECTED;
         res.detail = desc;
         LogError("Execution", "order gagal | " + desc + " percobaan=" + IntegerToString(attempt) + " id=" + res.requestId);
         SendAlert(SDB_ALERT_TYPE_ORDER_FAILED, StringFormat("Order %s %.2f gagal setelah %d percobaan: %s",
                                                             req.isBuy ? "BUY" : "SELL", req.volume, attempt, desc));
         return false;
        }
      return false;
     }

   // SL hanya membaik (Req 4.2); "tidak ada perubahan" = berhasil (4.3); posisi hilang = GONE (4.4).
   ENUM_SDB_EXEC ModifySl(const ulong positionId, const double newSl, string &why)
     {
      why = "";
      int digits = (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS);
      double target = NormalizeDouble(newSl, digits);
      for(int attempt = 1; ; attempt++)
        {
         if(!SelectOwn(positionId))
            return SDB_EXEC_GONE;
         bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
         double oldSl = PositionGetDouble(POSITION_SL);
         if(attempt > 1 && MathAbs(oldSl - target) < SymbolInfoDouble(m_symbol, SYMBOL_POINT) / 2)
            return SDB_EXEC_OK;   // kiriman sebelumnya ternyata sudah diterapkan
         if(!IsModifySlAllowed(isBuy, oldSl, target, SymbolInfoDouble(m_symbol, SYMBOL_BID), SymbolInfoDouble(m_symbol, SYMBOL_ASK),
                               (int)SymbolInfoInteger(m_symbol, SYMBOL_TRADE_STOPS_LEVEL),
                               (int)SymbolInfoInteger(m_symbol, SYMBOL_TRADE_FREEZE_LEVEL), SymbolInfoDouble(m_symbol, SYMBOL_POINT), why))
           {
            LogDebug("Execution", "modify SL dilewati | " + why);
            return SDB_EXEC_SKIPPED;
           }
         m_sendCount++;
         m_trade.PositionModify(positionId, target, PositionGetDouble(POSITION_TP));
         ENUM_SDB_EXEC out;
         if(HandleRetcode(attempt, "modify SL", SDB_ALERT_TYPE_MODIFY_FAILED, positionId, out, why))
            return out;
        }
      return SDB_EXEC_FAILED;
     }

   ENUM_SDB_EXEC ClosePartial(const ulong positionId, const double volume, string &why)
     {
      why = "";
      double startVol = -1.0;
      for(int attempt = 1; ; attempt++)
        {
         if(!SelectOwn(positionId))
            return (attempt > 1) ? SDB_EXEC_OK : SDB_EXEC_GONE;
         double posVol = PositionGetDouble(POSITION_VOLUME);
         if(startVol < 0.0)
            startVol = posVol;
         else if(posVol <= startVol - volume + SDB_VOLUME_EPS)
            return SDB_EXEC_OK;   // kiriman sebelumnya ternyata terisi
         if(!IsPartialVolumeValid(volume, posVol, SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MIN),
                                  SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_STEP), why))
           {
            LogWarn("Execution", "tutup sebagian ditolak | " + why);
            return SDB_EXEC_SKIPPED;
           }
         m_sendCount++;
         m_trade.PositionClosePartial(positionId, volume);
         ENUM_SDB_EXEC out;
         if(HandleRetcode(attempt, "tutup sebagian", SDB_ALERT_TYPE_ORDER_FAILED, positionId, out, why))
            return out;
        }
      return SDB_EXEC_FAILED;
     }

   ENUM_SDB_EXEC ClosePosition(const ulong positionId, string &why)
     {
      why = "";
      for(int attempt = 1; ; attempt++)
        {
         if(!SelectOwn(positionId))
            return (attempt > 1) ? SDB_EXEC_OK : SDB_EXEC_GONE;
         m_sendCount++;
         m_trade.PositionClose(positionId);
         ENUM_SDB_EXEC out;
         if(HandleRetcode(attempt, "tutup posisi", SDB_ALERT_TYPE_ORDER_FAILED, positionId, out, why))
            return out;
        }
      return SDB_EXEC_FAILED;
     }

   int CountOwnPositions()
     {
      int n = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
         if(PositionGetTicket(i) != 0 && PositionGetInteger(POSITION_MAGIC) == m_magic &&
            PositionGetString(POSITION_SYMBOL) == m_symbol)
            n++;
      return n;
     }

   long SendCount() const { return m_sendCount; }
  };

#endif // SDB_EXECUTION_EXECUTOR_MQH
