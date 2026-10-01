//+------------------------------------------------------------------+
//| TestNotifier.mqh — CNotifier dengan transport palsu, sink palsu, dan
//| waktu di-override (spec 08 Req 1–3, 6; design §3.6; TC-NR-01..21).
//| Dua notifier dengan login sama = dua instance di satu akun. Prefix
//| SDBTEST dan login palsu agar Global Variables akun sungguhan aman.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTNOTIFIER_MQH
#define SDB_SUITES_TESTNOTIFIER_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/FakeSink.mqh>
#include <SDBotTests/FakeTransport.mqh>
#include <SDBot/Notify/Notifier.mqh>

#define TNR_PREFIX "SDBTEST"
#define TNR_LOGIN  990002
#define TNR_T0     1790762405   // 2026.10.01 10:00:05

SdbNtContext TnrCtx()
  {
   SdbNtContext c;
   c.symbol = "EURUSDc";
   c.accountTag = "CENT";
   c.eaVersion = "1.07";
   c.currency = "USC";
   c.digits = 5;
   return c;
  }

AlertEvent TnrAlert(const string type, const ENUM_SDB_SEVERITY sev, const string key, const long time = TNR_T0)
  {
   AlertEvent a;
   a.type = type;
   a.severity = sev;
   a.message = "uji " + type;
   a.symbol = "EURUSDc";
   a.magic = 2026091901;
   a.time = (datetime)time;
   a.key = key;
   return a;
  }

TradeRecord TnrTrade(const long positionId, const string direction, const string source)
  {
   TradeRecord t;
   t.positionId = positionId;
   t.magic = 2026091901;
   t.symbol = "EURUSDc";
   t.direction = direction;
   t.source = source;
   t.volumeInitial = 0.10;
   t.priceRequested = 1.1;
   t.priceOpen = 1.1;
   t.slippagePoints = 0;
   t.spreadPoints = 8;
   t.slInitial = 1.098;
   t.tpInitial = 1.104;
   t.riskMoney = 20.0;
   t.riskPct = 0.5;
   t.signalId = SDB_NULL_LONG;
   t.eaVersion = "1.07";
   t.openedAt = (datetime)TNR_T0;
   return t;
  }

void TnrClean()
  {
   CState s;
   s.Init(TNR_PREFIX, TNR_LOGIN);
   s.DeleteAll();
  }

double TnrQuotaGv()
  {
   string key = TNR_PREFIX + "_" + IntegerToString(TNR_LOGIN) + "_" + SDB_GV_NT_QUOTA;
   return GlobalVariableCheck(key) ? GlobalVariableGet(key) : -1.0;
  }

// Satu instance siap pakai: state GV uji, waktu TNR_T0.
void TnrSetup(CNotifier &n, CState &st, CFakeSink &store, CFakeTransport &tr, const string keyPrefix)
  {
   st.Init(TNR_PREFIX, TNR_LOGIN);
   n.Init(GetPointer(store), GetPointer(tr), TnrCtx());
   n.SetState(GetPointer(st));
   n.SetKeyPrefix(keyPrefix);
   n.SetNowOverride(TNR_T0);
  }

void TnrBasics()
  {
   TnrClean();
   CNotifier n;
   CState st;
   CFakeSink store;
   CFakeTransport tr;
   TnrSetup(n, st, store, tr, "A");
   n.OnAlert(TnrAlert("DD_INFO", SDB_SEV_INFO, "k1"));
   n.OnTimer();
   SdbOutMessage m;
   AlertStatus s;
   AssertTrue("TC-NR-01", "alert terkirim, status SENT attempts 1 dengan key sama",
              tr.Count() == 1 && tr.At(0, m) && m.key == "k1" && store.StatusOf("k1", s) && s.status == "SENT" &&
              s.attempts == 1 && s.sentAt == (datetime)TNR_T0 && s.reason == "");

   n.OnTradeOpened(TnrTrade(77, "SELL", "EA"));
   AlertEvent stored;
   bool hasRow = store.CountAlertType("TRADE_OPENED") == 1 && store.LastAlert(stored);
   n.OnTimer();
   AssertTrue("TC-NR-02", "posisi dibuka: baris alerts TRADE_OPENED + pesan dengan key sama",
              hasRow && tr.CountType("TRADE_OPENED") == 1 && tr.At(1, m) && m.key == stored.key && stored.key != "");

   n.OnTradeOpened(TnrTrade(78, "BUY", "RECONCILED"));
   n.OnTimer();
   AssertTrue("TC-NR-03", "RECONCILED: tanpa pesan dan tanpa baris",
              store.CountAlertType("TRADE_OPENED") == 1 && tr.Count() == 2 && n.QueueSize() == 0);

   ClosureRecord c;
   c.positionId = 77;
   c.magic = 2026091901;
   c.symbol = "EURUSDc";
   c.reason = "TP";
   c.volumeTotal = 0.10;
   c.netProfit = 41.2;
   c.rResult = 2.06;
   c.holdingSec = 600;
   c.closedAt = (datetime)TNR_T0;
   n.OnClosure(c);
   n.OnTimer();
   AssertTrue("TC-NR-04", "posisi tutup memakai arah dari pembukaan",
              tr.CountType("TRADE_CLOSED") == 1 && tr.At(2, m) && StringFind(m.text, " SELL <code>0.10</code>") > 0 &&
              store.CountAlertType("TRADE_CLOSED") == 1);
   TnrClean();
  }

void TnrQueueOrder()
  {
   TnrClean();
   CNotifier n;
   CState st;
   CFakeSink store;
   CFakeTransport tr;
   TnrSetup(n, st, store, tr, "A");
   for(int i = 1; i <= 5; i++)
      n.OnAlert(TnrAlert("TEST_" + IntegerToString(i), SDB_SEV_INFO, "i" + IntegerToString(i)));
   n.OnAlert(TnrAlert("DD_STOP", SDB_SEV_CRITICAL, "c1"));
   n.OnTimer();
   SdbOutMessage m;
   AssertTrue("TC-NR-05", "Critical dikirim pertama", tr.At(0, m) && m.key == "c1");
   AssertTrue("TC-NR-06", "satu siklus maksimal 2 pesan", tr.Count() == 2 && n.QueueSize() == 4);
   TnrClean();
  }

void TnrCooldown()
  {
   TnrClean();
   CNotifier a, b;
   CState sa, sb;
   CFakeSink fa, fb;
   CFakeTransport ta, tb;
   TnrSetup(a, sa, fa, ta, "A");
   TnrSetup(b, sb, fb, tb, "B");
   a.OnAlert(TnrAlert("CONN_DOWN", SDB_SEV_MEDIUM, "k1"));
   a.SetNowOverride(TNR_T0 + 299);
   a.OnAlert(TnrAlert("CONN_DOWN", SDB_SEV_MEDIUM, "k2"));
   a.SetNowOverride(TNR_T0 + 300);
   a.OnAlert(TnrAlert("CONN_DOWN", SDB_SEV_MEDIUM, "k3"));
   AlertStatus s;
   AssertTrue("TC-NR-07", "Medium ke-2 dalam 299 detik COOLDOWN, ke-3 di 300 detik lolos",
              fa.StatusOf("k2", s) && s.status == "SKIPPED" && s.reason == "COOLDOWN" && !fa.StatusOf("k3", s) && a.QueueSize() == 2);

   TnrClean();
   a.SetNowOverride(TNR_T0 + 1000);
   b.SetNowOverride(TNR_T0 + 1000);
   a.OnAlert(TnrAlert("CONN_DOWN", SDB_SEV_MEDIUM, "a1"));
   b.OnAlert(TnrAlert("CONN_DOWN", SDB_SEV_MEDIUM, "b1"));
   AssertTrue("TC-NR-08", "tipe akun: dua instance bersamaan, satu lolos satu COOLDOWN",
              a.QueueSize() == 3 && b.QueueSize() == 0 && fb.StatusOf("b1", s) && s.reason == "COOLDOWN");
   a.OnAlert(TnrAlert("ORDER_FAILED", SDB_SEV_MEDIUM, "a2"));
   b.OnAlert(TnrAlert("ORDER_FAILED", SDB_SEV_MEDIUM, "b2"));
   AssertTrue("TC-NR-09", "tipe instance: keduanya lolos", a.QueueSize() == 4 && b.QueueSize() == 1);

   a.SetState(NULL);
   a.SetNowOverride(TNR_T0 + 5000);
   a.OnAlert(TnrAlert("CONN_UP", SDB_SEV_INFO, "m1"));
   a.OnAlert(TnrAlert("CONN_UP", SDB_SEV_INFO, "m2"));
   AssertTrue("TC-NR-19", "tanpa GV: cooldown akun di memori", fa.StatusOf("m2", s) && s.reason == "COOLDOWN" && !fa.StatusOf("m1", s));
   TnrClean();
  }

void TnrQuota()
  {
   TnrClean();
   CNotifier a, b;
   CState sa, sb;
   CFakeSink fa, fb;
   CFakeTransport ta, tb;
   TnrSetup(a, sa, fa, ta, "A");
   TnrSetup(b, sb, fb, tb, "B");
   for(int i = 1; i <= 21; i++)
     {
      CNotifier *n = (i % 2 == 0) ? GetPointer(b) : GetPointer(a);
      n.OnAlert(TnrAlert("TEST_Q" + IntegerToString(i), SDB_SEV_INFO, "q" + IntegerToString(i)));
     }
   AlertStatus s;
   AssertTrue("TC-NR-10", "21 Info dalam satu jam: 20 lolos, 1 QUOTA",
              a.QueueSize() + b.QueueSize() == 20 && fa.StatusOf("q21", s) && s.reason == "QUOTA" &&
              a.HeldInHour() + b.HeldInHour() == 1);
   double before = TnrQuotaGv();
   a.OnAlert(TnrAlert("DD_STOP", SDB_SEV_CRITICAL, "c1"));
   AssertTrue("TC-NR-11", "kuota habis: Critical tetap masuk, GV kuota tidak berubah",
              a.QueueSize() == 11 && !fa.StatusOf("c1", s) && TnrQuotaGv() == before);
   sa.Init(TNR_PREFIX, TNR_LOGIN);
   GlobalVariableDel(sa.Key(SDB_GV_NT_QUOTA));
   a.OnAlert(TnrAlert("TEST_Q22", SDB_SEV_INFO, "q22"));
   AssertTrue("TC-NR-20", "GV kuota dihapus: mulai lagi dari 1",
              !fa.StatusOf("q22", s) && TnrQuotaGv() == (double)(NtQuotaHour(TNR_T0) * SDB_NT_QUOTA_HOUR_FACTOR + 1));

   // TC-NR-22: pesan yang ditahan kuota tidak memakai cooldown tipenya.
   TnrClean();
   long h2 = (NtQuotaHour(TNR_T0) + 3) * 3600 - 100;   // 100 detik sebelum jam berganti
   a.SetNowOverride(h2);
   for(int i = 1; i <= SDB_NT_QUOTA_PER_HOUR; i++)
      a.OnAlert(TnrAlert("TEST_H" + IntegerToString(i), SDB_SEV_INFO, "h" + IntegerToString(i)));
   a.OnAlert(TnrAlert("CONN_DOWN", SDB_SEV_MEDIUM, "cq1"));
   a.SetNowOverride(h2 + 150);   // jam kuota baru, masih dalam cooldown 300 detik bila cq1 memakainya
   a.OnAlert(TnrAlert("CONN_DOWN", SDB_SEV_MEDIUM, "cq2"));
   AssertTrue("TC-NR-22", "ditahan QUOTA tidak memakai cooldown: 150 detik kemudian di jam baru tipe sama lolos",
              fa.StatusOf("cq1", s) && s.reason == "QUOTA" && !fa.StatusOf("cq2", s));
   TnrClean();
  }

void TnrTransportResults()
  {
   TnrClean();
   CNotifier n;
   CState st;
   CFakeSink store;
   CFakeTransport tr;
   TnrSetup(n, st, store, tr, "A");
   AlertStatus s;

   tr.Script("LIMITED:3600");
   n.OnAlert(TnrAlert("TEST_S", SDB_SEV_INFO, "s1"));
   n.OnAlert(TnrAlert("DD_STOP", SDB_SEV_CRITICAL, "c1"));
   n.OnTimer();
   n.SetNowOverride(TNR_T0 + 1801);
   n.OnTimer();
   AssertTrue("TC-NR-12", "dibatasi lama: Info STALE, Critical tetap antre",
              store.StatusOf("s1", s) && s.reason == "STALE" && n.QueueSize() == 1 && tr.Calls() == 1);

   CNotifier n2;
   CFakeSink st2;
   CFakeTransport t2;
   TnrClean();
   TnrSetup(n2, st, st2, t2, "B");
   t2.Script("TEMP");
   n2.OnAlert(TnrAlert("TEST_T", SDB_SEV_INFO, "t1"));
   n2.OnTimer();
   int afterFirst = t2.Calls();
   n2.SetNowOverride(TNR_T0 + 1);
   n2.OnTimer();
   n2.SetNowOverride(TNR_T0 + 2);
   n2.OnTimer();
   AssertTrue("TC-NR-13", "TEMP: 3 percobaan di 3 siklus lalu FAILED TRANSPORT_TEMP",
              afterFirst == 1 && t2.Calls() == 3 && st2.StatusOf("t1", s) && s.status == "FAILED" && s.attempts == 3 &&
              s.reason == "TRANSPORT_TEMP" && n2.QueueSize() == 0);

   t2.Script("PERM");
   n2.OnAlert(TnrAlert("TEST_P", SDB_SEV_INFO, "p1"));
   n2.OnTimer();
   AssertTrue("TC-NR-14", "PERMANENT: FAILED attempts 1",
              st2.StatusOf("p1", s) && s.status == "FAILED" && s.attempts == 1 && s.reason == "TRANSPORT_PERMANENT");

   t2.Script("LIMITED:60,OK");
   int calls0 = t2.Calls();
   n2.SetNowOverride(TNR_T0 + 100);
   n2.OnAlert(TnrAlert("TEST_L", SDB_SEV_INFO, "l1"));
   n2.OnTimer();
   n2.SetNowOverride(TNR_T0 + 130);
   n2.OnTimer();
   int callsMid = t2.Calls();
   n2.SetNowOverride(TNR_T0 + 160);
   n2.OnTimer();
   AssertTrue("TC-NR-15", "LIMITED 60: diam 60 detik, lalu SENT attempts 1",
              callsMid == calls0 + 1 && t2.Calls() == calls0 + 2 && st2.StatusOf("l1", s) && s.status == "SENT" && s.attempts == 1);
   TnrClean();
  }

void TnrRestartAndOverflow()
  {
   TnrClean();
   CNotifier n;
   CState st;
   CFakeSink store;
   CFakeTransport tr;
   TnrSetup(n, st, store, tr, "A");
   n.Requeue(TnrAlert("DD_STOP", SDB_SEV_CRITICAL, "c0"));
   for(int i = 1; i <= 99; i++)
     {
      n.SetNowOverride(TNR_T0 + i);
      n.Requeue(TnrAlert("TEST_O" + IntegerToString(i), SDB_SEV_INFO, "o" + IntegerToString(i)));
     }
   n.SetNowOverride(TNR_T0 + 200);
   n.OnAlert(TnrAlert("TEST_NEW", SDB_SEV_INFO, "new"));
   AlertStatus s;
   AssertTrue("TC-NR-16", "antrean penuh: Info tertua OVERFLOW, Critical tetap",
              n.QueueSize() == 100 && store.StatusOf("o1", s) && s.reason == "OVERFLOW" && !store.StatusOf("c0", s) &&
              !store.StatusOf("new", s));

   CNotifier d;
   CFakeSink ds;
   CFakeTransport dt;
   TnrClean();
   TnrSetup(d, st, ds, dt, "D");
   d.Requeue(TnrAlert("TEST_I1", SDB_SEV_INFO, "i1"));
   d.Requeue(TnrAlert("DD_STOP", SDB_SEV_CRITICAL, "row-5"));
   d.Requeue(TnrAlert("TEST_I2", SDB_SEV_INFO, "i2"));
   d.Requeue(TnrAlert("CLOSE_ALL_FAILED", SDB_SEV_CRITICAL, "c2"));
   d.Requeue(TnrAlert("TEST_I3", SDB_SEV_INFO, "i3"));
   d.DrainCritical(SDB_NT_DRAIN_MS);
   SdbOutMessage m0, m1;
   AssertTrue("TC-NR-17", "deinit: hanya Critical yang dikirim",
              dt.Count() == 2 && dt.At(0, m0) && dt.At(1, m1) && m0.severity == SDB_SEV_CRITICAL && m1.severity == SDB_SEV_CRITICAL &&
              d.QueueSize() == 3);
   AssertTrue("TC-NR-18", "Critical requeue terkirim dengan key asal", m0.key == "row-5" && ds.StatusOf("row-5", s) && s.status == "SENT");

   CNotifier w;
   CFakeSink ws;
   CFakeTransport wt;
   TnrClean();
   TnrSetup(w, st, ws, wt, "W");
   w.OnAlert(TnrAlert("TEST_W", SDB_SEV_INFO, "w1", TNR_T0 - 36000));
   w.SetNowOverride(TNR_T0 + 10);
   w.OnTimer();
   AssertTrue("TC-NR-21", "umur dari waktu masuk antrean, bukan AlertEvent.time", ws.StatusOf("w1", s) && s.status == "SENT");
   TnrClean();
  }

void RunTestNotifier()
  {
   TfBeginSuite("Notifier");
   TnrBasics();
   TnrQueueOrder();
   TnrCooldown();
   TnrQuota();
   TnrTransportResults();
   TnrRestartAndOverflow();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTNOTIFIER_MQH
