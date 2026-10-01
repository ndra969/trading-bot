//+------------------------------------------------------------------+
//| TestNotifyFormat.mqh — format pesan notifier, fungsi murni
//| (spec 08 Req 1.2, 1.3, 4; design §3.4, §4.4; katalog TC-NF-01..18).
//| Emoji dibandingkan lewat code unit UTF-16 agar tidak bergantung pada
//| encoding file sumber.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTNOTIFYFORMAT_MQH
#define SDB_SUITES_TESTNOTIFYFORMAT_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Notify/NotifyFormat.mqh>

SdbNtContext NfTestCtx(const string symbol, const int digits, const string tag = "CENT")
  {
   SdbNtContext c;
   c.symbol = symbol;
   c.accountTag = tag;
   c.eaVersion = "1.07";
   c.currency = "USC";
   c.digits = digits;
   return c;
  }

// Tag yang masih terbuka setelah dipotong (b, i, code); 0 = seimbang.
int NfOpenTags(const string html)
  {
   int open = 0;
   string tags[] = {"b", "i", "code"};
   for(int t = 0; t < ArraySize(tags); t++)
     {
      int pos = 0, opened = 0, closed = 0;
      while((pos = StringFind(html, "<" + tags[t] + ">", pos)) >= 0) { opened++; pos++; }
      pos = 0;
      while((pos = StringFind(html, "</" + tags[t] + ">", pos)) >= 0) { closed++; pos++; }
      open += opened - closed;
     }
   return open;
  }

bool NfEndsWith(const string s, const string tail)
  {
   int n = StringLen(s), m = StringLen(tail);
   return n >= m && StringSubstr(s, n - m) == tail;
  }

void RunTestNotifyFormat()
  {
   TfBeginSuite("NotifyFormat");
   string dot = NtCp(0x00B7);

   AssertStrEq("TC-NF-01", "escape & < >", NtEscape("margin < 300% & R>2"), "margin &lt; 300% &amp; R&gt;2");
   AssertStrEq("TC-NF-02", "input selalu teks mentah", NtEscape("&amp;"), "&amp;amp;");

   string h = NtHeader(NfTestCtx("EURUSDc", 5), SDB_NT_CRITICAL);
   AssertTrue("TC-NF-03a", "emoji Critical U+1F6A8 di awal",
              StringGetCharacter(h, 0) == 0xD83D && StringGetCharacter(h, 1) == 0xDEA8);
   AssertStrEq("TC-NF-03b", "header penanda SDBot, simbol, akun, versi", StringSubstr(h, 2),
               " <b>SDBot</b> " + dot + " EURUSDc " + dot + " CENT " + dot + " v1.07");
   AssertTrue("TC-NF-04", "tag TESTER", StringFind(NtHeader(NfTestCtx("EURUSDc", 5, "TESTER"), SDB_NT_INFO), " TESTER ") > 0);

   AssertTrue("TC-NF-05", "TRADE_CLOSED: net > 0 SUCCESS, 0 dan rugi INFO",
              NtLevelOf(SDB_SEV_INFO, "TRADE_CLOSED", 0.01) == SDB_NT_SUCCESS &&
              NtLevelOf(SDB_SEV_INFO, "TRADE_CLOSED", 0.0) == SDB_NT_INFO &&
              NtLevelOf(SDB_SEV_INFO, "TRADE_CLOSED", -5.0) == SDB_NT_INFO);
   AssertTrue("TC-NF-06", "BE dan partial SUCCESS; severity lain sesuai",
              NtLevelOf(SDB_SEV_INFO, "BE_MOVED", 0) == SDB_NT_SUCCESS && NtLevelOf(SDB_SEV_INFO, "PARTIAL_CLOSED", 0) == SDB_NT_SUCCESS &&
              NtLevelOf(SDB_SEV_HIGH, "DD_REDUCE", 0) == SDB_NT_HIGH && NtLevelOf(SDB_SEV_MEDIUM, "CONN_DOWN", 0) == SDB_NT_MEDIUM &&
              NtLevelOf(SDB_SEV_CRITICAL, "DD_STOP", 0) == SDB_NT_CRITICAL && NtLevelOf(SDB_SEV_INFO, "DD_INFO", 0) == SDB_NT_INFO);

   AssertTrue("TC-NF-07", "harga sesuai digit simbol",
              NtPrice(151.234, 3) == "151.234" && NtPrice(1.08345, 5) == "1.08345" && NtPrice(2345.67, 2) == "2345.67");
   AssertStrEq("TC-NF-08", "uang 2 desimal + mata uang", NtMoney(41.2, "USC"), "41.20 USC");
   AssertTrue("TC-NF-09", "R 2 desimal, NULL = -", NtR(2.0567) == "2.06" && NtR(SDB_NULL_DOUBLE) == "-");
   AssertTrue("TC-NF-10", "durasi d / m / j m",
              NtDuration(45) == "45d" && NtDuration(720) == "12m" && NtDuration(12300) == "3j 25m" && NtDuration(90000) == "25j 0m");

   // TC-NF-11: contoh "posisi dibuka" design §4.4.
   TradeRecord t;
   t.positionId = 123456;
   t.magic = 2026091901;
   t.symbol = "EURUSDc";
   t.direction = "BUY";
   t.source = "EA";
   t.volumeInitial = 0.10;
   t.priceOpen = 1.08345;
   t.slInitial = 1.08145;
   t.tpInitial = 1.08745;
   t.riskMoney = 20.0;
   t.riskPct = 0.5;
   string opened = NtLevelEmoji(SDB_NT_INFO) + " <b>SDBot</b> " + dot + " EURUSDc " + dot + " CENT " + dot + " v1.07\n" +
                   "<b>Posisi dibuka</b>\n" +
                   NtCp(0x1F4CA) + " BUY <code>0.10</code> @ <code>1.08345</code>\n" +
                   NtCp(0x1F6D1) + " SL <code>1.08145</code> " + dot + " " + NtCp(0x1F3AF) + " TP <code>1.08745</code>\n" +
                   NtCp(0x2696) + NtCp(0xFE0F) + " Risiko <code>0.50%</code> (<code>20.00 USC</code>)\n" +
                   NtCp(0x1F194) + " <code>123456</code>";
   AssertStrEq("TC-NF-11", "pesan posisi dibuka sesuai contoh", NtFormatOpened(NfTestCtx("EURUSDc", 5), t), opened);

   // TC-NF-12: contoh "posisi ditutup" design §4.4.
   ClosureRecord c;
   c.positionId = 123457;
   c.symbol = "USDJPYc";
   c.reason = "TP";
   c.volumeTotal = 0.10;
   c.netProfit = 41.2;
   c.rResult = 2.0567;
   c.holdingSec = 12300;
   string closed = NtLevelEmoji(SDB_NT_SUCCESS) + " <b>SDBot</b> " + dot + " USDJPYc " + dot + " CENT " + dot + " v1.07\n" +
                   "<b>Posisi ditutup: TP</b>\n" +
                   NtCp(0x1F4CA) + " SELL <code>0.10</code> " + dot + " " + NtCp(0x1F194) + " <code>123457</code>\n" +
                   NtCp(0x1F4B5) + " Profit <b>41.20 USC</b> " + dot + " R <code>2.06</code>\n" +
                   NtCp(0x23F1) + NtCp(0xFE0F) + " Lama <code>3j 25m</code>";
   AssertStrEq("TC-NF-12", "pesan posisi ditutup sesuai contoh", NtFormatClosed(NfTestCtx("USDJPYc", 3), c, "SELL"), closed);
   AssertTrue("TC-NF-12b", "emoji level: U+2705, U+2139 FE0F, U+274C, U+26A0 FE0F",
              NtLevelEmoji(SDB_NT_SUCCESS) == NtCp(0x2705) && NtLevelEmoji(SDB_NT_INFO) == NtCp(0x2139) + NtCp(0xFE0F) &&
              NtLevelEmoji(SDB_NT_HIGH) == NtCp(0x274C) && NtLevelEmoji(SDB_NT_MEDIUM) == NtCp(0x26A0) + NtCp(0xFE0F));

   AlertEvent a;
   a.type = "DD_STOP";
   a.severity = SDB_SEV_CRITICAL;
   a.message = "equity < 85% puncak & close all";
   a.symbol = "EURUSDc";
   string fa = NtFormatAlert(NfTestCtx("EURUSDc", 5), a);
   AssertTrue("TC-NF-13", "judul dan isi ter-escape",
              StringFind(fa, "\n<b>Drawdown 15%: emergency stop</b>\nequity &lt; 85% puncak &amp; close all") > 0 &&
              StringGetCharacter(fa, 0) == 0xD83D);
   AssertStrEq("TC-NF-14", "tipe asing = judulnya sendiri", NtTitle("FOO_BAR"), "FOO_BAR");

   string longText = "";
   for(int i = 0; i < 500; i++)
      longText += "abcdefghij";
   string cut = NtTruncate(longText, 4096);
   AssertTrue("TC-NF-15", "dipotong <= 4096 dengan penanda", StringLen(cut) <= 4096 && NfEndsWith(cut, NtTruncMark()));
   string withCode = StringSubstr(longText, 0, 4000) + "<code>" + StringSubstr(longText, 0, 200) + "</code>";
   cut = NtTruncate(withCode, 4096);
   AssertTrue("TC-NF-16", "tag <code> ditutup sebelum penanda",
              StringLen(cut) <= 4096 && NfOpenTags(cut) == 0 && NfEndsWith(cut, "</code>" + NtTruncMark()));
   string withEntity = StringSubstr(longText, 0, 4070) + "&amp;&amp;&amp;&amp;&amp;<b>bold</b>" + longText;
   cut = NtTruncate(withEntity, 4096);
   string body = StringSubstr(cut, 0, StringLen(cut) - StringLen(NtTruncMark()));
   int amp = StringFind(body, "&", 4070);
   bool entitiesWhole = true;
   while(amp >= 0)
     {
      if(StringSubstr(body, amp, 5) != "&amp;")
         entitiesWhole = false;
      amp = StringFind(body, "&", amp + 1);
     }
   AssertTrue("TC-NF-17", "entitas dan tag tidak terpotong",
              StringLen(cut) <= 4096 && entitiesWhole && NfOpenTags(cut) == 0 && StringFind(body, "<b") == StringFind(body, "<b>"));
   string exact = StringSubstr(longText, 0, 4096);
   AssertStrEq("TC-NF-18", "tepat 4096 tidak berubah", NtTruncate(exact, 4096), exact);

   TfEndSuite();
  }

#endif // SDB_SUITES_TESTNOTIFYFORMAT_MQH
