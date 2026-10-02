//+------------------------------------------------------------------+
//| TestZoneBook.mqh — CZoneBook dengan data terminal: bangun ulang per
//| bar, penanda Used di GV lintas objek, pembersihan GV lama, tanpa
//| status bersama (spec 11 Req 3; design §3.2; TC-ZB-01..04).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTZONEBOOK_MQH
#define SDB_SUITES_TESTZONEBOOK_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Analysis/ZoneBook.mqh>

#define TZB_LOGIN 990004
#define TZB_MAGIC 2026091950

SdbZoneParams ZbParams()
  {
   SdbZoneParams p;
   p.minWidthAtr = 0.3;
   p.maxWidthAtr = 2.0;
   p.minLegAtr = 1.5;
   p.legBars = 10;
   p.maxAge = 100;
   p.strength = 2;
   return p;
  }

void RunTestZoneBook()
  {
   TfBeginSuite("ZoneBook");
   CState st;
   st.Init("SDBTEST", TZB_LOGIN);
   st.DeleteAll();

   CZoneBook book;
   book.Init(_Symbol, PERIOD_H1, ZbParams(), TZB_MAGIC);
   bool first = book.OnTick();
   bool second = book.OnTick();
   SdbZone zones[];
   int n = book.Zones(zones);
   AssertTrue("TC-ZB-01", StringFormat("bangun ulang sekali per bar H1 (%d zona)", n), first && !second && book.Ready() && n > 0);

   AssertTrue("TC-ZB-04", "tanpa status bersama: peta jadi, tidak ada Used", book.CountUsed() == 0);

   book.SetState(GetPointer(st));
   book.OnTick();
   n = book.Zones(zones);
   string id = "";
   for(int i = 0; i < n && id == ""; i++)
      if(ZoneValid(zones[i]))
         id = zones[i].id;
   bool marked = id != "" && book.MarkUsed(id) && book.IsUsed(id);
   CZoneBook again;
   again.Init(_Symbol, PERIOD_H1, ZbParams(), TZB_MAGIC);
   again.SetState(GetPointer(st));
   again.OnTick();
   SdbZone z2[];
   int m = again.Zones(z2);
   bool usedInMap = false;
   for(int i = 0; i < m; i++)
      if(z2[i].id == id && z2[i].used && !ZoneValid(z2[i]))
         usedInMap = true;
   AssertTrue("TC-ZB-02", "MarkUsed bertahan ke objek baru lewat GV (" + id + ")", marked && again.IsUsed(id) && usedInMap && again.CountUsed() >= 1);

   string oldName = IntegerToString(TZB_MAGIC) + "_" + SDB_GV_ZONE_USED + "_1000000_D";
   st.Set(oldName, 1.0, false);
   CZoneBook clean;
   clean.Init(_Symbol, PERIOD_H1, ZbParams(), TZB_MAGIC);
   clean.SetState(GetPointer(st));
   clean.OnTick();
   AssertTrue("TC-ZB-03", "GV Used zona yang sudah kedaluwarsa dihapus; GV aktif tetap",
              !GlobalVariableCheck(st.Key(oldName)) && clean.IsUsed(id));
   st.DeleteAll();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTZONEBOOK_MQH
