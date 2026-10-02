//+------------------------------------------------------------------+
//| DailyStats.mqh — kumpulkan deal satu hari server dari history MT5
//| untuk laporan harian (spec 09 Req 6.2; design §3.7). Posisi SDBot
//| dikenali dari deal pembukanya (blok magic), karena deal penutup
//| manual (HP) bermagic 0. Agregasi ada di Schedule.mqh (DayStats).
//+------------------------------------------------------------------+
#ifndef SDB_NOTIFY_DAILYSTATS_MQH
#define SDB_NOTIFY_DAILYSTATS_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Utils.mqh>

void DsPushRow(SdbDealRow &rows[], const ulong ticket, const int kind)
  {
   int n = ArraySize(rows);
   ArrayResize(rows, n + 1, 64);
   rows[n].ticket = (long)ticket;
   rows[n].positionId = HistoryDealGetInteger(ticket, DEAL_POSITION_ID);
   rows[n].symbol = HistoryDealGetString(ticket, DEAL_SYMBOL);
   rows[n].kind = kind;
   rows[n].time = (long)HistoryDealGetInteger(ticket, DEAL_TIME);
   double profit = HistoryDealGetDouble(ticket, DEAL_PROFIT);
   rows[n].net = (kind == SDB_DS_KIND_BALANCE) ? 0.0 : profit + HistoryDealGetDouble(ticket, DEAL_COMMISSION) +
                 HistoryDealGetDouble(ticket, DEAL_SWAP) + HistoryDealGetDouble(ticket, DEAL_FEE);
   rows[n].amount = (kind == SDB_DS_KIND_BALANCE) ? profit : 0.0;
  }

// Semua deal posisi itu (hari mana pun) bila deal pembukanya bermagic SDBot.
bool DsAddPosition(const long positionId, SdbDealRow &rows[])
  {
   if(!HistorySelectByPosition(positionId))
      return false;
   int total = HistoryDealsTotal();
   if(total == 0)
      return true;
   ulong first = HistoryDealGetTicket(0);
   if(first == 0 || !IsSdbotMagic(HistoryDealGetInteger(first, DEAL_MAGIC)))
      return true;
   for(int i = 0; i < total; i++)
     {
      ulong t = HistoryDealGetTicket(i);
      if(t == 0)
         continue;
      long entry = HistoryDealGetInteger(t, DEAL_ENTRY);
      DsPushRow(rows, t, entry == DEAL_ENTRY_IN ? SDB_DS_KIND_IN : SDB_DS_KIND_OUT);
     }
   return true;
  }

// false = history tidak terbaca (laporan ditunda, hari tidak ditandai selesai).
bool SdbCollectDay(const long dayStart, SdbDealRow &rows[], long &openIds[])
  {
   ArrayFree(rows);
   ArrayFree(openIds);
   if(!HistorySelect((datetime)dayStart, (datetime)(dayStart + 86400 - 1)))
      return false;
   long positions[];
   for(int i = 0; i < HistoryDealsTotal(); i++)
     {
      ulong t = HistoryDealGetTicket(i);
      if(t == 0)
         continue;
      long type = HistoryDealGetInteger(t, DEAL_TYPE);
      if(type == DEAL_TYPE_BALANCE || type == DEAL_TYPE_CREDIT)
         DsPushRow(rows, t, SDB_DS_KIND_BALANCE);
      else if(type == DEAL_TYPE_BUY || type == DEAL_TYPE_SELL)
        {
         long id = HistoryDealGetInteger(t, DEAL_POSITION_ID);
         bool known = false;
         for(int k = 0; k < ArraySize(positions) && !known; k++)
            known = (positions[k] == id);
         if(!known)
           {
            int n = ArraySize(positions);
            ArrayResize(positions, n + 1);
            positions[n] = id;
           }
        }
     }
   for(int i = 0; i < ArraySize(positions); i++)
      if(!DsAddPosition(positions[i], rows))
         return false;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) != 0)
        {
         int n = ArraySize(openIds);
         ArrayResize(openIds, n + 1);
         openIds[n] = PositionGetInteger(POSITION_IDENTIFIER);
        }
   return true;
  }

#endif // SDB_NOTIFY_DAILYSTATS_MQH
