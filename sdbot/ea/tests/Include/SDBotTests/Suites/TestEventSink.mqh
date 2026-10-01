//+------------------------------------------------------------------+
//| TestEventSink.mqh — interface event sink, CNullSink, dan CFakeSink
//| yang dipakai suite lain untuk meng-assert event (spec 02 Req 6).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTEVENTSINK_MQH
#define SDB_SUITES_TESTEVENTSINK_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/FakeSink.mqh>
#include <SDBot/Core/EventSink.mqh>
#include <SDBot/App/TeeSink.mqh>

void RunTestEventSink()
  {
   TfBeginSuite("EventSink");

   // TC-LG-02a: CFakeSink menyimpan alert dan snapshot yang dikirim lewat interface.
   CFakeSink fake;
   ISdbEventSink *sink = GetPointer(fake);
   AlertEvent alert;
   alert.type = "CONN_DOWN";
   alert.severity = SDB_SEV_MEDIUM;
   alert.message = "terputus 5 menit";
   alert.symbol = "EURUSDc";
   alert.magic = 2026091901;
   alert.time = D'2026.09.29 10:00:00';
   sink.OnAlert(alert);
   AccountSnapshot snap;
   snap.login = 12345;
   snap.currency = "USC";
   sink.OnAccount(snap);

   AssertIntEq("TC-LG-02a", "satu alert tersimpan", fake.CountAlert(), 1);
   AlertEvent got;
   bool hasAlert = fake.LastAlert(got);
   AssertTrue("TC-LG-02b", "alert terakhir tersedia", hasAlert);
   AssertStrEq("TC-LG-02c", "type alert sama", got.type, "CONN_DOWN");
   AssertIntEq("TC-LG-02d", "severity alert sama", (long)got.severity, (long)SDB_SEV_MEDIUM);
   AssertIntEq("TC-LG-02e", "satu snapshot akun tersimpan", fake.CountAccount(), 1);
   AccountSnapshot gotSnap;
   AssertTrue("TC-LG-02f", "snapshot terakhir berisi login dan mata uang",
              fake.LastAccount(gotSnap) && gotSnap.login == 12345 && gotSnap.currency == "USC");
   fake.Reset();
   AssertIntEq("TC-LG-02g", "Reset mengosongkan alert", fake.CountAlert(), 0);

   // TC-LG-03a: CNullSink menerima semua event tanpa efek dan tanpa cadangan SL.
   CNullSink nullSink;
   ISdbEventSink *ns = GetPointer(nullSink);
   ns.OnAlert(alert);
   ns.OnAccount(snap);
   double sl = 123.0;
   bool found = ns.FindInitialSl(12345, 1, sl);
   AssertTrue("TC-LG-03a", "CNullSink.FindInitialSl false dan sl 0", !found && sl == 0.0);

   // TC-ES-10 (spec 08 Req 5.1): tee memberi key unik pada alert tanpa key, sama untuk semua sink.
   CFakeSink a1, a2, a3;
   CTeeSink tee;
   tee.Add(GetPointer(a1));
   tee.Add(GetPointer(a2));
   tee.Add(GetPointer(a3));
   tee.SetKeyPrefix("2026091901-100-7");
   AlertEvent noKey;   // seperti modul Fase 1: key tidak diisi (string NULL)
   noKey.type = "CONN_DOWN";
   noKey.severity = SDB_SEV_MEDIUM;
   noKey.message = "terputus";
   tee.OnAlert(noKey);
   tee.OnAlert(noKey);
   AlertEvent g1, g2, g3;
   bool all3 = a1.CountAlert() == 2 && a2.CountAlert() == 2 && a3.CountAlert() == 2;
   AssertTrue("TC-ES-10a", "ketiga sink menerima dua alert", all3);
   a1.LastAlert(g1);
   a2.LastAlert(g2);
   a3.LastAlert(g3);
   AssertTrue("TC-ES-10b", "key sama di semua sink dan berprefix", g1.key != "" && g1.key == g2.key && g2.key == g3.key &&
              StringFind(g1.key, "2026091901-100-7-") == 0);
   AlertEvent first;
   a1.AlertAt(0, first);
   AssertTrue("TC-ES-10c", "key unik per alert", first.key != "" && first.key != g1.key);

   // TC-ES-11 (Req 6.2): alert yang sudah punya key (requeue) tidak diganti.
   AlertEvent keyed = alert;
   keyed.key = "row-42";
   tee.OnAlert(keyed);
   a2.LastAlert(g2);
   AssertStrEq("TC-ES-11", "key asal dipertahankan", g2.key, "row-42");

   // TC-ES-12 (Req 5.3): status kirim diteruskan ke semua sink.
   AlertStatus st;
   st.key = "row-42";
   st.status = "SENT";
   st.attempts = 1;
   st.sentAt = D'2026.10.01 10:00:00';
   st.reason = "";
   tee.OnAlertStatus(st);
   AlertStatus gs;
   AssertTrue("TC-ES-12", "status sampai ke sink dengan key yang sama",
              a1.CountStatus() == 1 && a3.CountStatus() == 1 && a3.LastStatus(gs) && gs.key == "row-42" && gs.status == "SENT");

   TfEndSuite();
  }

#endif // SDB_SUITES_TESTEVENTSINK_MQH
