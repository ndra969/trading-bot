//+------------------------------------------------------------------+
//| ZoneBook.mqh — CZoneBook: peta zona MTF instance, dibangun ulang
//| penuh dari ZonesNeeded bar tertutup setiap bar MTF baru, ditambah
//| penanda Used di Global Variable per magic (spec 11 Req 3–4; design
//| §3.2). Peta = fungsi murni dari bar + daftar Used, sehingga jalan
//| terus dan restart memberi hasil sama. Tidak dari DB (PRD).
//+------------------------------------------------------------------+
#ifndef SDB_ANALYSIS_ZONEBOOK_MQH
#define SDB_ANALYSIS_ZONEBOOK_MQH

#include <SDBot/Core/State.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Analysis/BarCache.mqh>
#include <SDBot/Analysis/ZoneRules.mqh>

class CZoneBook
  {
private:
   string            m_symbol;
   ENUM_TIMEFRAMES   m_tf;
   SdbZoneParams     m_params;
   long              m_magic;
   CState           *m_state;          // NULL sampai akun PASSED: tanpa penanda Used
   CBarCache         m_cache;
   SdbZone           m_zones[];
   string            m_used[];
   bool              m_dirty;          // penanda Used berubah: bangun ulang walau tidak ada bar baru
   bool              m_ready;
   double            m_lastAtr;        // ATR(14) MTF bar tertutup terakhir (SL sinyal, spec 13)

   bool StateReady() const { return m_state != NULL && m_state.IsReady(); }

   // "<magic>_ZU_" : nama GV tanpa prefix akun.
   string UsedPrefix() const { return IntegerToString(m_magic) + "_" + SDB_GV_ZONE_USED + "_"; }

   // ID "H1-<epoch>-D" -> nama GV "<magic>_ZU_<epoch>_D" (timeframe tetap MTF instance).
   bool UsedName(const string zoneId, string &name) const
     {
      string parts[];
      if(StringSplit(zoneId, '-', parts) != 3)
         return false;
      name = UsedPrefix() + parts[1] + "_" + parts[2];
      return true;
     }

   void LoadUsed()
     {
      ArrayFree(m_used);
      if(!StateReady())
         return;
      string prefix = m_state.Key(UsedPrefix());
      for(int i = GlobalVariablesTotal() - 1; i >= 0; i--)
        {
         string name = GlobalVariableName(i);
         if(StringFind(name, prefix) != 0)
            continue;
         string rest[];
         if(StringSplit(StringSubstr(name, StringLen(prefix)), '_', rest) != 2)
            continue;
         int n = ArraySize(m_used);
         ArrayResize(m_used, n + 1);
         m_used[n] = ZoneId(m_tf, (datetime)StringToInteger(rest[0]), rest[1] == "D");
        }
     }

   // Penanda Used zona yang sudah lewat usia maksimum (dalam bar) dihapus agar GV tidak menumpuk (Req 3.4).
   void CleanupUsed(const MqlRates &r[])
     {
      if(!StateReady())
         return;
      long cutoff = (long)ZoneUsedCutoff(r, m_params.maxAge);
      string prefix = m_state.Key(UsedPrefix());
      bool removed = false;
      for(int i = GlobalVariablesTotal() - 1; i >= 0; i--)
        {
         string name = GlobalVariableName(i);
         if(StringFind(name, prefix) != 0)
            continue;
         string rest[];
         if(StringSplit(StringSubstr(name, StringLen(prefix)), '_', rest) == 2 && StringToInteger(rest[0]) < cutoff)
           {
            GlobalVariableDel(name);
            removed = true;
           }
        }
      if(removed)
         LoadUsed();
     }

   bool Rebuild()
     {
      MqlRates r[];
      if(m_cache.Copy(r) == 0)
        {
         m_ready = false;
         return false;
        }
      CleanupUsed(r);
      BuildZones(r, m_params, m_tf, m_used, m_zones);
      double atr[];
      m_lastAtr = AtrSeries(r, SDB_ZONE_ATR_PERIOD, atr) ? atr[ArraySize(atr) - 1] : 0.0;
      m_ready = true;
      m_dirty = false;
      LogDebug("Zones", StringFormat("peta %s | fresh=%d tested=%d lemah=%d invalid=%d kedaluwarsa=%d used=%d", EnumToString(m_tf),
                                     CountByStatus(SDB_ZONE_FRESH), CountByStatus(SDB_ZONE_TESTED), CountByStatus(SDB_ZONE_WEAK),
                                     CountByStatus(SDB_ZONE_INVALID), CountByStatus(SDB_ZONE_EXPIRED), CountUsed()));
      return true;
     }

public:
                     CZoneBook(void) : m_tf(PERIOD_CURRENT), m_magic(0), m_state(NULL), m_dirty(false), m_ready(false), m_lastAtr(0.0) {}

   void Init(const string symbol, const ENUM_TIMEFRAMES mtf, const SdbZoneParams &p, const long magic)
     {
      m_symbol = symbol;
      m_tf = mtf;
      m_params = p;
      m_magic = magic;
      m_state = NULL;
      m_dirty = false;
      m_ready = false;
      ArrayFree(m_zones);
      ArrayFree(m_used);
      m_cache.Init(symbol, mtf, ZonesNeeded(p));
     }

   // GV siap (akun PASSED): baca penanda Used, bangun ulang di tick berikutnya.
   void SetState(CState *state)
     {
      m_state = state;
      LoadUsed();
      m_dirty = true;
     }

   // true bila peta dibangun ulang (bar MTF baru atau penanda Used berubah).
   bool OnTick()
     {
      bool fresh = m_cache.Refresh();
      if(!m_cache.Ready())
        {
         m_ready = false;
         ArrayFree(m_zones);
         LogThrottled(SDB_LOG_WARN, "zones-data-" + EnumToString(m_tf), SDB_LOG_THROTTLE_DEFAULT_SEC, "Zones",
                      "histori " + EnumToString(m_tf) + " kurang dari " + IntegerToString(ZonesNeeded(m_params)) + " bar, peta zona kosong");
         return false;
        }
      if(!fresh && !m_dirty)
         return false;
      return Rebuild();
     }

   bool Ready() const { return m_ready && m_lastAtr > 0.0; }
   double LastAtr() const { return m_lastAtr; }
   datetime LastBarTime() const { return m_cache.LastClosedTime(); }
   ENUM_TIMEFRAMES Timeframe() const { return m_tf; }
   void Params(SdbZoneParams &out) const { out = m_params; }

   // Bar MTF tertutup yang dipakai Rebuild(); zone.swingIdx menunjuk ke array ini (Fibonacci, spec 18).
   int Rates(MqlRates &out[]) const { return m_cache.Copy(out); }

   int Zones(SdbZone &out[]) const
     {
      ArrayFree(out);
      int n = ArraySize(m_zones);
      ArrayResize(out, n);
      for(int i = 0; i < n; i++)
         out[i] = m_zones[i];
      return n;
     }

   int CountByStatus(const ENUM_SDB_ZONE_STATUS s) const
     {
      int n = 0;
      for(int i = 0; i < ArraySize(m_zones); i++)
         if(m_zones[i].status == s)
            n++;
      return n;
     }

   int CountUsed() const
     {
      int n = 0;
      for(int i = 0; i < ArraySize(m_zones); i++)
         if(m_zones[i].used)
            n++;
      return n;
     }

   bool TouchedZone(const ENUM_SDB_DIR dir, const double low, const double high, SdbZone &out) const
     {
      int i = ::TouchedZone(m_zones, dir, low, high);
      if(i < 0)
         return false;
      out = m_zones[i];
      return true;
     }

   bool OppositeZone(const ENUM_SDB_DIR dir, const double price, SdbZone &out) const
     {
      int i = ::OppositeZone(m_zones, dir, price);
      if(i < 0)
         return false;
      out = m_zones[i];
      return true;
     }

   // Satu zona satu entry (PRD, Req 2.4): GV dengan flush, lalu peta dibangun ulang segera.
   bool MarkUsed(const string zoneId)
     {
      string name;
      if(!StateReady() || !UsedName(zoneId, name) || !m_state.Set(name, 1.0, true))
         return false;
      if(!ZoneInList(zoneId, m_used))
        {
         int n = ArraySize(m_used);
         ArrayResize(m_used, n + 1);
         m_used[n] = zoneId;
        }
      m_dirty = true;
      if(m_cache.Ready())
         Rebuild();
      return true;
     }

   bool IsUsed(const string zoneId) const { return ZoneInList(zoneId, m_used); }
  };

#endif // SDB_ANALYSIS_ZONEBOOK_MQH
