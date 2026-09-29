//+------------------------------------------------------------------+
//| TestEventSink.mqh — interface event sink, CNullSink, dan CFakeSink
//| yang dipakai suite lain untuk meng-assert event (spec 02 Req 6).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTEVENTSINK_MQH
#define SDB_SUITES_TESTEVENTSINK_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/FakeSink.mqh>
#include <SDBot/Core/EventSink.mqh>

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

   TfEndSuite();
  }

#endif // SDB_SUITES_TESTEVENTSINK_MQH
