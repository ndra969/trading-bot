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

// TC-NF-20..24 (spec 09 design §4.4): heartbeat, laporan harian, start, stop, uang dengan pemisah ribuan.
void RunTestNotifyFormatScheduled()
  {
   string dot = NtCp(0x00B7);
   string nl = "\n";
   SdbNtContext c = NfTestCtx("EURUSDc", 5);
   c.login = 12345;
   c.eaVersion = "1.08";
   string acct = " <b>SDBot</b> " + dot + " AKUN 12345 " + dot + " CENT " + dot + " v1.08" + nl;

   SdbHeartbeat h;
   h.balance = 10234.5;
   h.equity = 10180.2;
   h.ddPct = 1.25;
   h.riskStatus = "normal";
   h.sdbotPositions = 3;
   h.instancesAlive = 12;
   h.heldLastHour = 0;
   string hb = NtLevelEmoji(SDB_NT_INFO) + acct + "<b>Heartbeat</b>" + nl +
               NtCp(0x1F4B0) + " Balance <code>10,234.50 USC</code> " + dot + " Equity <code>10,180.20 USC</code>" + nl +
               NtCp(0x1F4C9) + " DD dari puncak <code>1.25%</code> " + dot + " Status <code>normal</code>" + nl +
               NtCp(0x1F4C8) + " Posisi SDBot <code>3</code> " + dot + " Instance hidup <code>12</code>" + nl +
               NtCp(0x1F515) + " Ditahan kuota jam lalu <code>0</code>";
   AssertStrEq("TC-NF-20", "heartbeat sesuai contoh design", NtFormatHeartbeat(c, h), hb);

   SdbDayStats d;
   ZeroMemory(d);
   d.dayStart = 1790812800;   // 2026.10.01
   d.net = 152.4;
   d.closed = 7;
   d.wins = 4;
   d.symbolCount = 3;
   d.symbols[0] = "EURUSDc";
   d.symbolNet[0] = 120.0;
   d.symbols[1] = "XAUUSDc";
   d.symbolNet[1] = 80.4;
   d.symbols[2] = "GBPJPYc";
   d.symbolNet[2] = -48.0;
   d.balanceOps = 0.0;
   d.balanceNow = 10386.9;
   string rep = NtCp(0x1F4C8) + acct + "<b>Laporan harian 2026-10-01</b>" + nl +
                NtCp(0x1F4B5) + " P&amp;L <b>+152.40 USC</b> " + dot + " " + NtCp(0x1F522) + " Posisi tutup <code>7</code> " + dot + " " +
                NtCp(0x1F3AF) + " Win rate <code>57.1%</code>" + nl +
                "EURUSDc <code>+120.00</code> " + dot + " XAUUSDc <code>+80.40</code> " + dot + " GBPJPYc <code>-48.00</code>" + nl +
                NtCp(0x1F3E6) + " Operasi saldo <code>0.00 USC</code> " + dot + " " + NtCp(0x1F4B0) + " Balance <code>10,386.90 USC</code>";
   string got = NtFormatDailyReport(c, d);
   d.net = -12.0;
   d.closed = 0;
   d.symbolCount = 0;
   string neg = NtFormatDailyReport(c, d);
   AssertTrue("TC-NF-21", "laporan harian sesuai contoh; rugi = 1F4C9, tanpa posisi = win rate - dan tanpa baris simbol",
              got == rep && StringGetCharacter(neg, 1) == 0xDCC9 && StringFind(neg, "Win rate <code>-</code>") > 0 &&
              StringFind(neg, "EURUSDc") < 0);

   SdbStartInfo s;
   s.magic = 2026091901;
   s.presetTag = "EURUSDc";
   s.validation = "PASSED";
   s.hasPrevious = true;
   s.previousAbnormal = false;
   s.previousEndedAt = D'2026.10.01 22:15:00';
   s.previousReason = "REMOVE";
   string st1 = NtFormatStart(c, s);
   s.previousAbnormal = true;
   string st2 = NtFormatStart(c, s);
   s.hasPrevious = false;
   string st3 = NtFormatStart(c, s);
   AssertTrue("TC-NF-22", "start: emoji 1F680, simbol, magic, preset, validasi, sesi lalu normal / tidak normal / pertama",
              StringFind(st1, NtCp(0x1F680) + " <b>SDBot</b> " + dot + " EURUSDc ") == 0 && StringFind(st1, "<b>SDBot aktif</b>") > 0 &&
              StringFind(st1, "Magic <code>2026091901</code>") > 0 && StringFind(st1, "Preset <code>EURUSDc</code>") > 0 &&
              StringFind(st1, "Validasi akun <code>PASSED</code>") > 0 &&
              StringFind(st1, "Sesi lalu berhenti <code>2026.10.01 22:15</code> (<code>REMOVE</code>)") > 0 &&
              StringFind(st2, "Sesi lalu tidak ditutup normal") > 0 && StringFind(st3, "Sesi pertama") > 0);
   string stop = NtFormatStop(c, "CHARTCLOSE");
   AssertTrue("TC-NF-23", "stop: emoji 1F6D1, judul, alasan",
              StringFind(stop, NtCp(0x1F6D1) + " <b>SDBot</b> ") == 0 && StringFind(stop, "<b>SDBot berhenti</b>" + nl + "Alasan <code>CHARTCLOSE</code>") > 0);
   AssertTrue("TC-NF-24", "uang dengan pemisah ribuan dan tanda",
              NtMoneyGrouped(10234.5, "USC") == "10,234.50 USC" && NtMoneyGrouped(-48, "USC") == "-48.00 USC" &&
              NtMoneyGrouped(1234567.891, "USC") == "1,234,567.89 USC" && NtSigned(120) == "+120.00" && NtSigned(-48) == "-48.00" &&
              NtSigned(0) == "0.00");
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

   RunTestNotifyFormatScheduled();

   TfEndSuite();
  }

#endif // SDB_SUITES_TESTNOTIFYFORMAT_MQH
