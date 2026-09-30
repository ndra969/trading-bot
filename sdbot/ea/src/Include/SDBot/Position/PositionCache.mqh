//+------------------------------------------------------------------+
//| PositionCache.mqh — CPositionCache: nilai mahal per posisi yang tidak
//| berubah selama posisi terbuka (spec 06 design §4.3): kepemilikan dari
//| deal pembuka, SL awal (komentar -> ORDER_SL -> DB), volume awal,
//| risiko awal, komisi; plus penghitung retry per aksi. Status BE dan
//| partial tetap dibaca dari posisi MT5, bukan dari cache (Req 1.4).
//+------------------------------------------------------------------+
#ifndef SDB_POSITION_POSITIONCACHE_MQH
#define SDB_POSITION_POSITIONCACHE_MQH

#include <SDBot/Core/EventSink.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Execution/ExecutionRules.mqh>

class CPositionCache
  {
private:
   long              m_magic;
   string            m_symbol;
   ISdbEventSink    *m_sink;
   CNullSink         m_nullSink;
   bool              m_skipComment;     // hook uji: komentar tidak bisa diubah di tester (EC-08)
   PositionCacheEntry m_entries[];

   int Find(const ulong positionId) const
     {
      for(int i = 0; i < ArraySize(m_entries); i++)
         if(m_entries[i].positionId == positionId)
            return i;
      return -1;
     }

   // Req 1.2: komentar SDB|<SL>|<ID> -> ORDER_SL order pembuka -> tabel trades.
   void FindInitialSl(PositionCacheEntry &e, const string comment, const ulong order)
     {
      double sl = 0.0;
      string id = "";
      e.slSource = SDB_SL_SRC_NONE;
      e.initialSl = 0.0;
      if(!m_skipComment && ParseOrderComment(comment, sl, id) && sl > 0.0)
        {
         e.initialSl = sl;
         e.slSource = SDB_SL_SRC_COMMENT;
         return;
        }
      if(order > 0 && HistoryOrderSelect(order) && HistoryOrderGetDouble(order, ORDER_SL) > 0.0)
        {
         e.initialSl = HistoryOrderGetDouble(order, ORDER_SL);
         e.slSource = SDB_SL_SRC_ORDER;
         return;
        }
      if(m_sink.FindInitialSl(AccountInfoInteger(ACCOUNT_LOGIN), e.positionId, sl) && sl > 0.0)
        {
         e.initialSl = sl;
         e.slSource = SDB_SL_SRC_DB;
        }
     }

   // Dari history posisi: deal pembuka menentukan pemilik, arah, harga, waktu, volume awal, dan komisi.
   bool Build(const ulong positionId, PositionCacheEntry &e)
     {
      ZeroMemory(e);
      e.positionId = positionId;
      e.riskMoney = SDB_NULL_DOUBLE;
      if(!HistorySelectByPosition(positionId))
         return false;
      for(int i = 0; i < HistoryDealsTotal(); i++)
        {
         ulong d = HistoryDealGetTicket(i);
         if(HistoryDealGetInteger(d, DEAL_ENTRY) != DEAL_ENTRY_IN)
            continue;
         e.symbol = HistoryDealGetString(d, DEAL_SYMBOL);
         e.owned = HistoryDealGetInteger(d, DEAL_MAGIC) == m_magic && e.symbol == m_symbol;
         e.isBuy = HistoryDealGetInteger(d, DEAL_TYPE) == DEAL_TYPE_BUY;
         e.entry = HistoryDealGetDouble(d, DEAL_PRICE);
         e.entryTime = (datetime)HistoryDealGetInteger(d, DEAL_TIME);
         e.initialVolume = HistoryDealGetDouble(d, DEAL_VOLUME);
         e.commission = MathAbs(HistoryDealGetDouble(d, DEAL_COMMISSION)) * 2.0;
         string comment = HistoryDealGetString(d, DEAL_COMMENT);
         ulong order = (ulong)HistoryDealGetInteger(d, DEAL_ORDER);
         if(e.owned)
           {
            FindInitialSl(e, comment, order);
            double p = 0.0;
            if(e.initialSl > 0.0 &&
               OrderCalcProfit(e.isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, e.symbol, e.initialVolume, e.entry, e.initialSl, p))
               e.riskMoney = MathMax(0.0, -p);
           }
         return true;
        }
      return false;   // deal pembuka belum ada di history (sinkronisasi); dicoba lagi berikutnya
     }

public:
                     CPositionCache(void) : m_magic(0), m_sink(NULL), m_skipComment(false) {}

   void Init(const long magic, const string symbol, ISdbEventSink *sink)
     {
      m_magic = magic;
      m_symbol = symbol;
      m_sink = (sink == NULL) ? GetPointer(m_nullSink) : sink;
      ArrayFree(m_entries);
     }

   // true bila entri ada atau berhasil dibangun dari history.
   bool Get(const ulong positionId, PositionCacheEntry &e)
     {
      int i = Find(positionId);
      if(i >= 0)
        {
         e = m_entries[i];
         return true;
        }
      if(!Build(positionId, e))
         return false;
      int n = ArraySize(m_entries);
      ArrayResize(m_entries, n + 1);
      m_entries[n] = e;
      return true;
     }

   // Glosarium "posisi instance": deal pembuka bermagic dan bersimbol instance ini (EC-15).
   bool Owned(const ulong positionId)
     {
      PositionCacheEntry e;
      return Get(positionId, e) && e.owned;
     }

   void Update(const PositionCacheEntry &e)
     {
      int i = Find(e.positionId);
      if(i >= 0)
         m_entries[i] = e;
     }

   // Req 7.4.
   void Remove(const ulong positionId)
     {
      int i = Find(positionId);
      if(i < 0)
         return;
      int last = ArraySize(m_entries) - 1;
      if(i != last)
         m_entries[i] = m_entries[last];
      ArrayResize(m_entries, last);
     }

   int  Count() const                        { return ArraySize(m_entries); }
   void SetSkipCommentForTest(const bool v)  { m_skipComment = v; }
  };

#endif // SDB_POSITION_POSITIONCACHE_MQH
