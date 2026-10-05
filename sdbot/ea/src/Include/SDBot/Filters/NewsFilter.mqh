//+------------------------------------------------------------------+
//| NewsFilter.mqh — CNewsFilter: event kalender berdampak untuk mata
//| uang simbol di cache memori (spec 16 Req 1–3; design §3.2).
//| Live: kalender MT5 (CalendarValueHistory) dimuat ulang tiap 15
//| menit. Tester: CSV ExportCalendar dari Common\Files sekali saat
//| init. Kalender tidak terbaca = filter OFF (entry tidak diblokir) +
//| satu alert NEWS_FILTER_OFF per sesi lewat event sink.
//+------------------------------------------------------------------+
#ifndef SDB_FILTERS_NEWSFILTER_MQH
#define SDB_FILTERS_NEWSFILTER_MQH

#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Core/EventSink.mqh>
#include <SDBot/Filters/NewsRules.mqh>

#define SDB_NEWS_STATUS_ON       "ON"
#define SDB_NEWS_STATUS_OFF      "OFF"
#define SDB_NEWS_STATUS_DISABLED "DISABLED"
#define SDB_NEWS_CALENDAR_CCY    "USD,EUR,GBP,JPY,CHF,AUD,CAD,NZD,CNY"   // mata uang yang punya event di kalender MT5
#define SDB_NEWS_RETRY_SEC       60                                      // live: coba lagi lebih cepat setelah gagal

class CNewsFilter
  {
private:
   string            m_symbol;
   string            m_base;
   string            m_quote;
   SdbNewsParams     m_p;
   bool              m_tester;
   string            m_csv;
   ISdbEventSink    *m_sink;
   long              m_magic;
   SdbNewsEvent      m_ev[];
   datetime          m_nextLoad;
   string            m_status;
   bool              m_alerted;

   bool CalendarCcy(const string c) const
     {
      return StringLen(c) == 3 && StringFind("," + SDB_NEWS_CALENDAR_CCY + ",", "," + c + ",") >= 0;
     }

   void SetOff(const string reason)
     {
      bool was = (m_status == SDB_NEWS_STATUS_OFF);
      m_status = SDB_NEWS_STATUS_OFF;
      if(!was)
         LogWarn("News", "filter berita OFF, entry tidak diblokir karena berita | " + reason);
      if(m_alerted || m_sink == NULL)
         return;
      m_alerted = true;
      AlertEvent a;
      a.type = SDB_ALERT_TYPE_NEWS_FILTER_OFF;
      a.severity = SDB_SEV_HIGH;
      a.message = "Proteksi berita OFF untuk " + m_symbol + ": " + reason + ". Entry tetap berjalan tanpa blackout berita.";
      a.symbol = m_symbol;
      a.magic = m_magic;
      a.time = TimeCurrent();
      m_sink.OnAlert(a);
     }

   void SetOn(const int count)
     {
      if(m_status == SDB_NEWS_STATUS_OFF)
         LogInfo("News", StringFormat("filter berita aktif lagi | event=%d", count));
      m_status = SDB_NEWS_STATUS_ON;
     }

   void LoadCsv()
     {
      ArrayFree(m_ev);
      ResetLastError();
      int h = FileOpen(m_csv, FILE_READ | FILE_TXT | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ);
      if(h == INVALID_HANDLE)
        {
         SetOff("CSV kalender " + m_csv + " tidak ada di Common\\Files (" + ErrText(GetLastError()) + ")");
         return;
        }
      int bad = 0, all = 0;
      while(!FileIsEnding(h))
        {
         string line = FileReadString(h);
         if(StringLen(line) == 0)
            continue;
         all++;
         SdbNewsEvent e;
         if(!ParseCalendarLine(line, e))
           {
            bad++;
            continue;
           }
         if(!EventForSymbol(e, m_base, m_quote))
            continue;
         int n = ArraySize(m_ev);
         ArrayResize(m_ev, n + 1, 256);
         m_ev[n] = e;
        }
      FileClose(h);
      if(bad > 0)
         LogWarn("News", StringFormat("CSV kalender %s: %d dari %d baris rusak dilewati", m_csv, bad, all));
      if(all - bad <= 0)
        {
         SetOff("CSV kalender " + m_csv + " tanpa event valid");
         return;
        }
      LogInfo("News", StringFormat("CSV kalender %s dimuat | event simbol=%d dari %d baris", m_csv, ArraySize(m_ev), all));
      SetOn(ArraySize(m_ev));
     }

   bool LoadLiveCcy(const string ccy, const datetime now, SdbNewsEvent &out[])
     {
      MqlCalendarValue vals[];
      ResetLastError();
      if(CalendarValueHistory(vals, now - 86400, now + 2 * 86400, NULL, ccy) < 0)
         return false;
      for(int i = 0; i < ArraySize(vals); i++)
        {
         MqlCalendarEvent ev;
         if(!CalendarEventById(vals[i].event_id, ev))
            continue;
         SdbNewsEvent e;
         e.time = vals[i].time;
         e.ccy = ccy;
         e.impact = (ev.importance == CALENDAR_IMPORTANCE_HIGH) ? SDB_NEWS_HIGH :
                    (ev.importance == CALENDAR_IMPORTANCE_MODERATE ? SDB_NEWS_MEDIUM : SDB_NEWS_LOW);
         e.id = (long)ev.id;
         e.name = ev.name;
         int n = ArraySize(out);
         ArrayResize(out, n + 1, 64);
         out[n] = e;
        }
      return true;
     }

   void LoadLive(const datetime now)
     {
      SdbNewsEvent fresh[];
      string ccys[2];
      ccys[0] = m_base;
      ccys[1] = m_quote;
      int asked = 0;
      for(int i = 0; i < 2; i++)
        {
         if(!CalendarCcy(ccys[i]))
            continue;
         asked++;
         if(!LoadLiveCcy(ccys[i], now, fresh))
           {
            SetOff("kalender MT5 tidak terbaca untuk " + ccys[i] + " (" + ErrText(GetLastError()) + ")");
            m_nextLoad = now + SDB_NEWS_RETRY_SEC;
            return;
           }
        }
      if(asked == 0)
        {
         SetOff("mata uang " + m_base + "/" + m_quote + " tidak ada di kalender MT5");
         m_nextLoad = now + SDB_NEWS_REFRESH_SEC;
         return;
        }
      ArrayFree(m_ev);
      ArrayResize(m_ev, ArraySize(fresh));   // ArrayCopy tidak bisa untuk struct berisi string
      for(int i = 0; i < ArraySize(fresh); i++)
         m_ev[i] = fresh[i];
      m_nextLoad = now + SDB_NEWS_REFRESH_SEC;
      SetOn(ArraySize(m_ev));
     }

public:
                     CNewsFilter(void) : m_tester(false), m_sink(NULL), m_magic(0), m_nextLoad(0), m_status(SDB_NEWS_STATUS_DISABLED),
                     m_alerted(false) {}

   void Init(const string symbol, const string base, const string quote, const SdbNewsParams &p, const bool tester, const string csvFile,
             ISdbEventSink *sink, const long magic)
     {
      m_symbol = symbol;
      m_base = base;
      m_quote = quote;
      m_p = p;
      m_tester = tester;
      m_csv = csvFile;
      m_sink = sink;
      m_magic = magic;
      m_nextLoad = 0;
      m_alerted = false;
      ArrayFree(m_ev);
      m_status = p.enabled ? SDB_NEWS_STATUS_ON : SDB_NEWS_STATUS_DISABLED;
      if(p.enabled && tester)
         LoadCsv();
     }

   // Live: muat ulang bila jadwal muat tercapai (15 menit; 60 detik setelah gagal). Tester: tidak berbuat apa-apa.
   void Refresh(const datetime serverNow)
     {
      if(!m_p.enabled || m_tester || serverNow < m_nextLoad)
         return;
      LoadLive(serverNow);
     }

   string Status() const { return m_status; }
   int EventCount() const { return ArraySize(m_ev); }

   bool Blocked(const datetime bar, string &detail) const
     {
      detail = "";
      if(m_status != SDB_NEWS_STATUS_ON)
         return false;
      int i = FindBlackout(m_ev, bar, m_base, m_quote, m_p);
      if(i < 0)
         return false;
      detail = BlackoutDetail(m_ev[i], bar);
      return true;
     }

   string NearestText(const datetime bar) const
     {
      if(m_status != SDB_NEWS_STATUS_ON)
         return "";
      int i = NearestUpcoming(m_ev, bar, m_base, m_quote, 86400);
      return i < 0 ? "" : BlackoutDetail(m_ev[i], bar);
     }
  };

#endif // SDB_FILTERS_NEWSFILTER_MQH
