//+------------------------------------------------------------------+
//| Reconciler.mqh — CReconciler: sekali saat status bersama siap (spec 06
//| Req 7, design §4.6): TradeRecord RECONCILED untuk posisi terbuka milik
//| instance, lalu deal dan closure yang terlewat saat EA mati. Pengulangan
//| aman: kunci unik DB dan GV LAST_DEAL per magic.
//+------------------------------------------------------------------+
#ifndef SDB_POSITION_RECONCILER_MQH
#define SDB_POSITION_RECONCILER_MQH

#include <SDBot/Position/ClosureTracker.mqh>

class CReconciler
  {
private:
   long              m_magic;
   string            m_symbol;
   CPositionCache   *m_cache;
   CClosureTracker  *m_tracker;
   ISdbEventSink    *m_sink;
   CNullSink         m_nullSink;
   string            m_eaVersion;

   // Req 7.1: SL awal tidak diketahui -> SL sekarang, risiko kosong, WARN.
   void RecordOpenPosition(const ulong ticket)
     {
      PositionCacheEntry e;
      if(!m_cache.Get(ticket, e) || !e.owned)
         return;
      TradeRecord t;
      t.positionId = (long)ticket;
      t.magic = m_magic;
      t.symbol = e.symbol;
      t.direction = e.isBuy ? SDB_DIRECTION_BUY : SDB_DIRECTION_SELL;
      t.source = SDB_TRADE_SOURCE_RECONCILED;
      t.volumeInitial = e.initialVolume;
      t.priceRequested = SDB_NULL_DOUBLE;
      t.priceOpen = e.entry;
      t.slippagePoints = SDB_NULL_LONG;
      t.spreadPoints = SDB_NULL_LONG;
      t.slInitial = e.initialSl;
      t.tpInitial = PositionGetDouble(POSITION_TP);
      t.riskMoney = e.riskMoney;
      double balance = AccountInfoDouble(ACCOUNT_BALANCE);
      t.riskPct = (e.riskMoney != SDB_NULL_DOUBLE && balance > 0.0) ? e.riskMoney / balance * 100.0 : SDB_NULL_DOUBLE;
      t.signalId = SDB_NULL_LONG;
      t.eaVersion = m_eaVersion;
      t.openedAt = e.entryTime;
      if(e.slSource == SDB_SL_SRC_NONE)
        {
         t.slInitial = PositionGetDouble(POSITION_SL);
         LogWarn("Position", "SL awal posisi tidak diketahui, dicatat SL sekarang | pos=" + IntegerToString((long)ticket));
        }
      m_sink.OnTradeOpened(t);
     }

public:
                     CReconciler(void) : m_magic(0), m_cache(NULL), m_tracker(NULL), m_sink(NULL) {}

   void Init(const long magic, const string symbol, CPositionCache *cache, CClosureTracker *tracker, ISdbEventSink *sink,
             const string eaVersion)
     {
      m_magic = magic;
      m_symbol = symbol;
      m_cache = cache;
      m_tracker = tracker;
      m_sink = (sink == NULL) ? GetPointer(m_nullSink) : sink;
      m_eaVersion = eaVersion;
     }

   void Run()
     {
      int open = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong ticket = PositionGetTicket(i);
         if(ticket == 0 || PositionGetInteger(POSITION_MAGIC) != m_magic || PositionGetString(POSITION_SYMBOL) != m_symbol)
            continue;
         RecordOpenPosition(ticket);
         open++;
        }
      // Req 7.2: tiket dikumpulkan dulu; ProcessDeal memanggil HistorySelectByPosition yang mengganti seleksi history.
      datetime now = TimeCurrent();
      datetime lastTime = m_tracker.LastDealTime();
      datetime from = (lastTime > 0) ? lastTime - 86400 : now - SDB_RECONCILE_LOOKBACK_DAYS * 86400;
      ulong last = m_tracker.LastDeal();
      ulong tickets[];
      if(HistorySelect(from, now + 60))
         for(int i = 0; i < HistoryDealsTotal(); i++)
           {
            ulong d = HistoryDealGetTicket(i);
            if(d > last)
              {
               int n = ArraySize(tickets);
               ArrayResize(tickets, n + 1);
               tickets[n] = d;
              }
           }
      int processed = 0;
      for(int i = 0; i < ArraySize(tickets); i++)
         if(m_tracker.ProcessDeal(tickets[i]))
            processed++;
      LogInfo("Position", StringFormat("rekonsiliasi | posisi terbuka=%d deal terlewat diproses=%d", open, processed));
     }
  };

#endif // SDB_POSITION_RECONCILER_MQH
