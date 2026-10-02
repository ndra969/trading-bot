//+------------------------------------------------------------------+
//| TestZones.mqh — ATR, calon zona, status, peta, pemilihan, skor;
//| fungsi murni (spec 11 design §3.1, §6.1; TC-ZN-01..25). Bar dibuat
//| tangan; ATR untuk kasus zona dibuat konstan 0.0010 agar lebar dan
//| gerak keluar bisa dihitung manual.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTZONES_MQH
#define SDB_SUITES_TESTZONES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Analysis/ZoneRules.mqh>

#define TZN_T0  D'2026.06.01 00:00'
#define TZN_ATR 0.0010

void ZnAdd(MqlRates &r[], const double o, const double h, const double l, const double c)
  {
   int n = ArraySize(r);
   ArrayResize(r, n + 1);
   r[n].time = TZN_T0 + n * 3600;
   r[n].open = o;
   r[n].high = h;
   r[n].low = l;
   r[n].close = c;
   r[n].tick_volume = 1;
   r[n].real_volume = 0;
   r[n].spread = 0;
  }

void ZnAtr(const MqlRates &r[], double &atr[])
  {
   ArrayResize(atr, ArraySize(r));
   ArrayInitialize(atr, TZN_ATR);
  }

SdbZoneParams ZnParams()
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

SdbSwing ZnSwing(const MqlRates &r[], const int i, const bool isHigh)
  {
   SdbSwing s;
   s.index = i;
   s.time = r[i].time;
   s.price = isHigh ? r[i].high : r[i].low;
   s.isHigh = isHigh;
   return s;
  }

// Demand di bar 2: low 1.1000, badan atas = 1.1000 + top; close bar 3.. sesuai legCloses lalu datar di lastClose.
void ZnDemand(MqlRates &r[], const double top, const double &legCloses[], const int total)
  {
   ArrayFree(r);
   ZnAdd(r, 1.1020, 1.1030, 1.1010, 1.1015);
   ZnAdd(r, 1.1015, 1.1020, 1.1005, 1.1010);
   ZnAdd(r, 1.1000 + top, 1.1000 + top + 0.0002, 1.1000, 1.1000 + top / 2.0);
   double prev = r[2].close;
   for(int i = 3; i < total; i++)
     {
      double c = (i - 3 < ArraySize(legCloses)) ? legCloses[i - 3] : legCloses[ArraySize(legCloses) - 1];
      ZnAdd(r, prev, MathMax(prev, c) + 0.0002, MathMax(MathMin(prev, c) - 0.0002, 1.1003), c);
      prev = c;
     }
  }

void RunTestZonesCandidate()
  {
   MqlRates r[];
   for(int i = 0; i < 50; i++)
      ZnAdd(r, 1.1000, 1.1005, 1.0995, 1.1000);
   double atr[];
   bool ok = AtrSeries(r, 14, atr);
   AssertTrue("TC-ZN-01", "TR konstan 0.0010: ATR 0.0010", ok && MathAbs(atr[49] - 0.0010) < 1e-12 && MathAbs(atr[13] - 0.0010) < 1e-12);
   ZnAdd(r, 1.1025, 1.1030, 1.1025, 1.1028);
   ok = AtrSeries(r, 14, atr);
   AssertTrue("TC-ZN-02", StringFormat("gap: TR = high - close sebelumnya 0.0030 (ATR %.7f)", ok ? atr[50] : -1),
              ok && MathAbs(atr[50] - (0.0010 * 13 + 0.0030) / 14) < 1e-12 && !AtrSeries(r, 20, atr));

   AssertTrue("TC-ZN-03", "ID zona deterministik", ZoneId(PERIOD_H1, (datetime)1790812800, true) == "H1-1790812800-D" &&
              ZoneId(PERIOD_H1, (datetime)1790812800, false) == "H1-1790812800-S");

   double leg[] = {1.1015, 1.1028, 1.1030};
   ZnDemand(r, 0.0008, leg, 15);
   ZnAtr(r, atr);
   SdbZone z;
   ok = ZoneCandidate(r, atr, ZnSwing(r, 2, false), ZnParams(), z);
   AssertTrue("TC-ZN-04", StringFormat("demand: distal 1.1000, proximal 1.1008, lebar 0.8, keluar 2.0 di bar 4 (lebar %.3f keluar %.3f aktif %d)",
                                       z.widthAtr, z.legAtr, z.activeIdx),
              ok && z.demand && MathAbs(z.distal - 1.1000) < 1e-9 && MathAbs(z.proximal - 1.1008) < 1e-9 &&
              MathAbs(z.widthAtr - 0.8) < 1e-6 && MathAbs(z.legAtr - 2.0) < 1e-6 && z.activeIdx == 4 && z.swingIdx == 2);

   ArrayFree(r);
   ZnAdd(r, 1.1080, 1.1090, 1.1070, 1.1085);
   ZnAdd(r, 1.1085, 1.1095, 1.1080, 1.1090);
   ZnAdd(r, 1.1092, 1.1100, 1.1090, 1.1096);
   ZnAdd(r, 1.1096, 1.1097, 1.1080, 1.1083);
   ZnAdd(r, 1.1083, 1.1088, 1.1070, 1.1072);
   for(int i = 0; i < 10; i++)
      ZnAdd(r, 1.1072, 1.1075, 1.1068, 1.1072);
   ZnAtr(r, atr);
   ok = ZoneCandidate(r, atr, ZnSwing(r, 2, true), ZnParams(), z);
   AssertTrue("TC-ZN-05", StringFormat("supply: distal 1.1100, proximal 1.1092, keluar 2.0 (keluar %.3f)", z.legAtr),
              ok && !z.demand && MathAbs(z.distal - 1.1100) < 1e-9 && MathAbs(z.proximal - 1.1092) < 1e-9 &&
              MathAbs(z.widthAtr - 0.8) < 1e-6 && MathAbs(z.legAtr - 2.0) < 1e-6);

   double big[] = {1.1040, 1.1060};
   double tops[] = {0.00029, 0.00030, 0.0020, 0.00201};
   bool expect[] = {false, true, true, false};
   bool widthOk = true;
   for(int k = 0; k < 4; k++)
     {
      ZnDemand(r, tops[k], big, 15);
      ZnAtr(r, atr);
      widthOk = widthOk && (ZoneCandidate(r, atr, ZnSwing(r, 2, false), ZnParams(), z) == expect[k]);
     }
   AssertTrue("TC-ZN-06", "lebar 0.29 tolak, 0.30 terima, 2.0 terima, 2.01 tolak", widthOk);

   double leg149[] = {1.1015, 1.10229};
   double leg150[] = {1.1015, 1.1023};
   ZnDemand(r, 0.0008, leg149, 15);
   ZnAtr(r, atr);
   bool rejected = !ZoneCandidate(r, atr, ZnSwing(r, 2, false), ZnParams(), z);
   ZnDemand(r, 0.0008, leg150, 15);
   ZnAtr(r, atr);
   AssertTrue("TC-ZN-07", "gerak keluar 1.49 ATR tolak, 1.50 terima",
              rejected && ZoneCandidate(r, atr, ZnSwing(r, 2, false), ZnParams(), z));

   double late[] = {1.1012, 1.1012, 1.1012, 1.1012, 1.1012, 1.1012, 1.1012, 1.1012, 1.1012, 1.1012, 1.1030};
   ZnDemand(r, 0.0008, late, 20);
   ZnAtr(r, atr);
   AssertTrue("TC-ZN-08", "gerak keluar baru tercapai di bar ke-11 (legBars 10): tolak", !ZoneCandidate(r, atr, ZnSwing(r, 2, false), ZnParams(), z));

   double fast[] = {1.1030, 1.1030, 1.1030};
   ZnDemand(r, 0.0008, fast, 15);
   ZnAtr(r, atr);
   ok = ZoneCandidate(r, atr, ZnSwing(r, 2, false), ZnParams(), z);
   AssertTrue("TC-ZN-09", StringFormat("keluar tercapai di s+1: aktif di s+2 (konfirmasi swing) (%d)", z.activeIdx), ok && z.activeIdx == 4);

   double slow[] = {1.1012, 1.1012, 1.1012, 1.1012, 1.1030};
   ZnDemand(r, 0.0008, slow, 15);
   ZnAtr(r, atr);
   ok = ZoneCandidate(r, atr, ZnSwing(r, 2, false), ZnParams(), z);
   AssertTrue("TC-ZN-10", StringFormat("keluar tercapai di s+5: aktif di s+5 (%d)", z.activeIdx), ok && z.activeIdx == 7 && z.activeTime == r[7].time);
  }

// Bar sesudah aktivasi: open = close sebelumnya, high = max(open, close) + 0.0002.
void ZnBar(MqlRates &r[], const double low, const double close)
  {
   double o = r[ArraySize(r) - 1].close;
   ZnAdd(r, o, MathMax(o, close) + 0.0002, low, close);
  }

// Zona demand TC-ZN-04 (distal 1.1000, proximal 1.1008), aktif di bar 4, lalu jalur harga.
SdbZone ZnStatusOf(MqlRates &r[], const double &lows[], const double &closes[], const int flatTo = 0)
  {
   double leg[] = {1.1015, 1.1028};
   ZnDemand(r, 0.0008, leg, 5);
   for(int i = 0; i < ArraySize(lows); i++)
      ZnBar(r, lows[i], closes[i]);
   while(ArraySize(r) < flatTo)
      ZnBar(r, 1.1020, 1.1025);
   double atr[];
   ZnAtr(r, atr);
   SdbZone z;
   ZoneCandidate(r, atr, ZnSwing(r, 2, false), ZnParams(), z);
   ZoneStatus(r, ZnParams(), z);
   return z;
  }

// Seri untuk BuildZones: `prefix` bar datar (TR 0.0010), swing demand di indeks prefix, lalu closes sesudahnya.
void ZnSeries(MqlRates &r[], const int prefix, const double &closesAfter[], const int flatTo)
  {
   ArrayFree(r);
   for(int i = 0; i < prefix; i++)
      ZnAdd(r, 1.1020, 1.1025, 1.1015, 1.1020);
   ZnAdd(r, 1.1018, 1.1020, 1.1000, 1.1008);
   for(int i = 0; i < ArraySize(closesAfter); i++)
     {
      double o = r[ArraySize(r) - 1].close, c = closesAfter[i];
      ZnAdd(r, o, MathMax(o, c) + 0.0002, MathMax(MathMin(o, c) - 0.0002, 1.1010), c);
     }
   while(ArraySize(r) < flatTo)
     {
      double c = r[ArraySize(r) - 1].close;
      ZnAdd(r, c, c + 0.0005, c - 0.0005, c);
     }
  }

SdbZone ZnManual(const bool demand, const datetime t, const double distal, const double proximal, const ENUM_SDB_ZONE_STATUS st, const bool used)
  {
   SdbZone z;
   ZeroMemory(z);
   z.id = ZoneId(PERIOD_H1, t, demand);
   z.demand = demand;
   z.swingTime = t;
   z.distal = distal;
   z.proximal = proximal;
   z.status = st;
   z.used = used;
   return z;
  }

void RunTestZonesStatus()
  {
   MqlRates r[];
   double l11[] = {1.1020, 1.1020, 1.1020};
   double c11[] = {1.1025, 1.1025, 1.1025};
   SdbZone z = ZnStatusOf(r, l11, c11);
   AssertTrue("TC-ZN-11", "tanpa sentuhan: Fresh", z.status == SDB_ZONE_FRESH && z.touches == 0);
   double l12[] = {1.1020, 1.1006, 1.1004, 1.1005, 1.1020};
   double c12[] = {1.1025, 1.1010, 1.1009, 1.1012, 1.1025};
   z = ZnStatusOf(r, l12, c12);
   AssertTrue("TC-ZN-12", StringFormat("satu masuk, tiga bar di dalam: Tested (%d sentuhan)", z.touches), z.status == SDB_ZONE_TESTED && z.touches == 1);
   double l13[] = {1.1006, 1.1020, 1.1007};
   double c13[] = {1.1010, 1.1025, 1.1011};
   z = ZnStatusOf(r, l13, c13);
   AssertTrue("TC-ZN-13", "dua kali masuk: Lemah", z.status == SDB_ZONE_WEAK && z.touches == 2);
   double l14[] = {1.1020, 1.0995};
   double c14[] = {1.1025, 1.0998};
   z = ZnStatusOf(r, l14, c14);
   AssertTrue("TC-ZN-14", "masuk lalu close di bawah distal di bar yang sama: Invalid", z.status == SDB_ZONE_INVALID);
   double l15[] = {1.0995, 1.1020, 1.1006};
   double c15[] = {1.0998, 1.1025, 1.1010};
   z = ZnStatusOf(r, l15, c15);
   AssertTrue("TC-ZN-15", "sentuhan sesudah Invalid: tetap Invalid", z.status == SDB_ZONE_INVALID);
   double none[];
   z = ZnStatusOf(r, none, none, 103);
   bool notYet = z.status == SDB_ZONE_FRESH;
   z = ZnStatusOf(r, none, none, 104);
   AssertTrue("TC-ZN-16", "usia 100 bar: belum; 101 bar: Kedaluwarsa", notYet && z.status == SDB_ZONE_EXPIRED);

   double after[] = {1.1030, 1.1045};
   ZnSeries(r, 45, after, 60);
   string used[];
   ArrayResize(used, 1);
   used[0] = ZoneId(PERIOD_H1, r[45].time, true);
   SdbZone map[];
   int n = BuildZones(r, ZnParams(), PERIOD_H1, used, map);
   int found = -1;
   for(int i = 0; i < n; i++)
      if(map[i].id == used[0])
         found = i;
   AssertTrue("TC-ZN-17", StringFormat("zona Fresh dengan ID di daftar Used: used, tidak valid (%d zona)", n),
              found >= 0 && map[found].status == SDB_ZONE_FRESH && map[found].used && !ZoneValid(map[found]));

   double slow[] = {1.1012, 1.1015};
   ZnSeries(r, 45, slow, 48);
   string noUsed[];
   n = BuildZones(r, ZnParams(), PERIOD_H1, noUsed, map);
   bool absent = true;
   for(int i = 0; i < n; i++)
      if(map[i].swingTime == r[45].time)
         absent = false;
   AssertTrue("TC-ZN-18", "swing terkonfirmasi tetapi gerak keluar belum tercapai: tidak ada di peta", absent);

   SdbZone zs[];
   ArrayResize(zs, 3);
   zs[0] = ZnManual(true, (datetime)100, 1.1000, 1.1010, SDB_ZONE_FRESH, false);
   zs[1] = ZnManual(true, (datetime)200, 1.1002, 1.1012, SDB_ZONE_TESTED, false);
   zs[2] = ZnManual(false, (datetime)300, 1.1015, 1.1005, SDB_ZONE_FRESH, false);
   int pick = TouchedZone(zs, SDB_DIR_BULL, 1.1004, 1.1009);
   zs[0].status = SDB_ZONE_TESTED;
   int newer = TouchedZone(zs, SDB_DIR_BULL, 1.1004, 1.1009);
   AssertTrue("TC-ZN-19", StringFormat("Fresh lebih dulu (%d), lalu yang terbaru (%d); supply tidak untuk BULL", pick, newer), pick == 0 && newer == 1);

   zs[0].status = SDB_ZONE_WEAK;
   zs[1].used = true;
   zs[2].status = SDB_ZONE_INVALID;
   AssertTrue("TC-ZN-20", "hanya Lemah / Used / Invalid: tidak ada", TouchedZone(zs, SDB_DIR_BULL, 1.1004, 1.1009) == -1 &&
              TouchedZone(zs, SDB_DIR_BEAR, 1.1004, 1.1016) == -1);

   SdbZone op[];
   ArrayResize(op, 3);
   op[0] = ZnManual(false, (datetime)100, 1.1110, 1.1100, SDB_ZONE_FRESH, false);
   op[1] = ZnManual(false, (datetime)200, 1.1060, 1.1050, SDB_ZONE_TESTED, false);
   op[2] = ZnManual(true, (datetime)300, 1.0940, 1.0950, SDB_ZONE_FRESH, false);
   AssertTrue("TC-ZN-21", "zona lawan terdekat: BUY -> supply 1.1050, SELL -> demand 1.0950",
              OppositeZone(op, SDB_DIR_BULL, 1.1000) == 1 && OppositeZone(op, SDB_DIR_BEAR, 1.1000) == 2);
   op[0].status = SDB_ZONE_INVALID;
   op[1].status = SDB_ZONE_INVALID;
   AssertTrue("TC-ZN-22", "tidak ada supply valid di atas: -1", OppositeZone(op, SDB_DIR_BULL, 1.1000) == -1);

   SdbZone sc = ZnManual(true, (datetime)1, 1.0, 1.1, SDB_ZONE_FRESH, false);
   int fresh = ZoneScore(sc);
   sc.status = SDB_ZONE_TESTED;
   int tested = ZoneScore(sc);
   sc.status = SDB_ZONE_WEAK;
   int weak = ZoneScore(sc);
   sc.status = SDB_ZONE_FRESH;
   sc.used = true;
   AssertTrue("TC-ZN-23", "skor zona 30 / 15 / 0 / Used 0", fresh == 30 && tested == 15 && weak == 0 && ZoneScore(sc) == 0);
   AssertIntEq("TC-ZN-24", "ZonesNeeded default = 156", ZonesNeeded(ZnParams()), 156);

   // TC-ZN-26 (temuan SC-13): batas pembersihan penanda Used dihitung dalam bar, bukan jam kalender.
   // 150 bar H1 dengan gap akhir pekan 48 jam di tengah: batas = waktu bar ke-(last - 100).
   MqlRates gap[];
   for(int i = 0; i < 150; i++)
     {
      ZnAdd(gap, 1.1, 1.1005, 1.0995, 1.1);
      if(i >= 75)
         gap[i].time += 48 * 3600;
     }
   datetime cutoff = ZoneUsedCutoff(gap, 100);
   AssertTrue("TC-ZN-26", StringFormat("batas Used = waktu bar 49 (%s), bukan waktu terakhir - 100 jam", TimeToString(cutoff)),
              cutoff == gap[49].time && cutoff != gap[149].time - 100 * 3600);

   ZnSeries(r, 45, after, 60);
   SdbZone m1[], m2[];
   BuildZones(r, ZnParams(), PERIOD_H1, noUsed, m1);
   BuildZones(r, ZnParams(), PERIOD_H1, noUsed, m2);
   string t1 = ZoneMapText(m1, 5);
   AssertTrue("TC-ZN-25", "peta dari data sama: sidik identik dan tidak kosong (" + t1 + ")", t1 != "" && t1 == ZoneMapText(m2, 5));
  }

void RunTestZones()
  {
   TfBeginSuite("Zones");
   RunTestZonesCandidate();
   RunTestZonesStatus();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTZONES_MQH
