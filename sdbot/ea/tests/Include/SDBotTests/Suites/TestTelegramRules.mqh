//+------------------------------------------------------------------+
//| TestTelegramRules.mqh — permintaan dan respons Telegram, teks polos,
//| teks push, batas push; fungsi murni (spec 09 Req 1.3, 2, 3;
//| design §3.1, §4.3; TC-TG-01..14).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTTELEGRAMRULES_MQH
#define SDB_SUITES_TESTTELEGRAMRULES_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Notify/TelegramRules.mqh>
#include <SDBot/Notify/TelegramTransport.mqh>

// TC-TG-15..17: langkah CTelegramTransport.Send yang bisa diuji tanpa jaringan (spec 09 Req 2.3, 2.5, 2.7).
SdbOutMessage TtgMsg()
  {
   SdbOutMessage m;
   m.key = "k";
   m.type = "TEST";
   m.text = "<b>uji</b>";
   m.silent = false;
   m.severity = SDB_SEV_INFO;
   return m;
  }

void RunTestTelegramTransport()
  {
   CTelegramTransport off;
   off.Init("123:ABC", "-100", NULL);
   off.Disable("uji");
   SdbSendResult r = off.Send(TtgMsg());
   AssertTrue("TC-TG-15", "nonaktif: PERMANENT TELEGRAM_OFF tanpa WebRequest",
              r.code == SDB_SEND_PERMANENT && r.note == "TELEGRAM_OFF" && off.IsDisabled() && off.WebRequestCount() == 0);

   CState st;
   st.Init("SDBTEST", 990003);
   st.DeleteAll();
   CTelegramTransport gap;
   gap.Init("123:ABC", "-100", GetPointer(st));
   st.Set(SDB_GV_NT_TG_NEXT, (double)(GetTickCount64() + 4500), false);
   r = gap.Send(TtgMsg());
   AssertTrue("TC-TG-16", StringFormat("jarak kirim bersama: GV NT_TG_NEXT di depan -> LIMITED %d detik tanpa WebRequest", r.retryAfterSec),
              r.code == SDB_SEND_LIMITED && r.retryAfterSec == 5 && gap.WebRequestCount() == 0 && !gap.IsDisabled());
   st.DeleteAll();

   CTelegramTransport empty;
   empty.Init("", "-100", NULL);
   SdbSendResult e = empty.Send(TtgMsg());
   CTelegramTransport tester;
   tester.Init("123:ABC", "-100", NULL);
   SdbSendResult t = tester.Send(TtgMsg());
   bool testerOk = !MQLInfoInteger(MQL_TESTER) || (t.disable && t.code == SDB_SEND_PERMANENT && tester.WebRequestCount() == 0);
   AssertTrue("TC-TG-17", "token kosong / Strategy Tester: nonaktif, tidak pernah WebRequest",
              e.disable && e.code == SDB_SEND_PERMANENT && empty.WebRequestCount() == 0 && testerOk &&
              StringFind(empty.DisabledReason(), "kosong") >= 0);
  }

void RunTestTelegramRules()
  {
   TfBeginSuite("TelegramRules");

   ushort ctl[] = {1};
   string raw = "a\"b\\c\nd\te" + ShortArrayToString(ctl);
   AssertStrEq("TC-TG-01", "escape JSON: kutip, backslash, baris baru, tab, kontrol",
               TgJsonEscape(raw), "a\\\"b\\\\c\\nd\\te\\u0001");
   AssertStrEq("TC-TG-02", "body HTML tanpa bunyi",
               TgBody("-100123", "x", true, true),
               "{\"chat_id\":\"-100123\",\"text\":\"x\",\"disable_notification\":true,\"parse_mode\":\"HTML\"}");
   AssertStrEq("TC-TG-03", "body teks polos berbunyi tanpa parse_mode",
               TgBody("-100123", "x", false, false),
               "{\"chat_id\":\"-100123\",\"text\":\"x\",\"disable_notification\":false}");
   AssertTrue("TC-TG-04", "URL dan samaran token",
              TgUrl("123:ABC") == "https://api.telegram.org/bot123:ABC/sendMessage" &&
              TgMask("gagal bot123:ABC/sendMessage", "123:ABC") == "gagal bot***/sendMessage" &&
              TgMask("tanpa token", "") == "tanpa token");
   AssertTrue("TC-TG-05", "retry_after dari body 429; tidak ada = 0",
              TgRetryAfter("{\"ok\":false,\"error_code\":429,\"parameters\":{\"retry_after\":30}}") == 30 &&
              TgRetryAfter("{}") == 0);
   AssertTrue("TC-TG-06", "URL belum diizinkan (4014) dan alamat tidak valid (5200) = CONFIG",
              TgClassify(-1, 4014, "") == SDB_TG_CONFIG && TgClassify(-1, 5200, "") == SDB_TG_CONFIG);
   AssertTrue("TC-TG-07", "koneksi, timeout, permintaan gagal = TEMP",
              TgClassify(-1, 5201, "") == SDB_TG_TEMP && TgClassify(-1, 5202, "") == SDB_TG_TEMP &&
              TgClassify(-1, 5203, "") == SDB_TG_TEMP);
   AssertTrue("TC-TG-08", "200 ok:true = OK, 200 tanpa ok:true = TEMP",
              TgClassify(200, 0, "{\"ok\":true,\"result\":{}}") == SDB_TG_OK && TgClassify(200, 0, "{\"ok\":false}") == SDB_TG_TEMP);
   AssertIntEq("TC-TG-09", "429 = LIMITED", TgClassify(429, 0, "{\"parameters\":{\"retry_after\":5}}"), SDB_TG_LIMITED);
   AssertTrue("TC-TG-10", "400: parse error, chat not found = CONFIG, lain = PERMANENT",
              TgClassify(400, 0, "{\"description\":\"Bad Request: can't parse entities: unsupported start tag\"}") == SDB_TG_PARSE_ERROR &&
              TgIsParseError("{\"description\":\"Bad Request: can't parse entities: x\"}") &&
              TgClassify(400, 0, "{\"description\":\"Bad Request: chat not found\"}") == SDB_TG_CONFIG &&
              TgClassify(400, 0, "{\"description\":\"Bad Request: message text is empty\"}") == SDB_TG_PERMANENT);
   AssertTrue("TC-TG-11", "401, 403, 404 = CONFIG; 502 = TEMP",
              TgClassify(401, 0, "") == SDB_TG_CONFIG && TgClassify(403, 0, "") == SDB_TG_CONFIG &&
              TgClassify(404, 0, "") == SDB_TG_CONFIG && TgClassify(502, 0, "") == SDB_TG_TEMP);
   AssertStrEq("TC-TG-12", "teks polos: tag dibuang, entitas dikembalikan", NtPlainText("<b>R&amp;D</b> &lt;5 &gt;3"), "R&D <5 >3");

   string longText = "";
   for(int i = 0; i < 40; i++)
      longText += "baris " + IntegerToString(i) + "\n";
   string push = NtPushText(longText, 255);
   AssertTrue("TC-TG-13", "push <= 255, tanpa baris baru, diakhiri elipsis",
              StringLen(push) <= 255 && StringFind(push, "\n") < 0 && StringGetCharacter(push, StringLen(push) - 1) == 0x2026 &&
              NtPushText("pendek\nsaja", 255) == "pendek saja");

   ulong now = 1000000;
   ulong one[] = {now - 500};
   ulong two[] = {now - 900, now - 100};
   ulong ten[];
   ArrayResize(ten, 10);
   for(int i = 0; i < 10; i++)
      ten[i] = now - 59000 + (ulong)i * 1000;
   ulong tenOld[];
   ArrayResize(tenOld, 10);
   for(int i = 0; i < 10; i++)
      tenOld[i] = now - 60001 + (ulong)i * 5000;
   tenOld[0] = now - 60001;
   AssertTrue("TC-TG-14", "push: 1 dalam 1 detik boleh, 2 tidak; 10 dalam 60 detik tidak; tertua lewat 60 detik boleh",
              PushAllowed(one, now) && !PushAllowed(two, now) && !PushAllowed(ten, now) && PushAllowed(tenOld, now));

   RunTestTelegramTransport();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTTELEGRAMRULES_MQH
