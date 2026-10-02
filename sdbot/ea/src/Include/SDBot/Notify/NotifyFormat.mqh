//+------------------------------------------------------------------+
//| NotifyFormat.mqh — format pesan notifier gaya bot Python: emoji per
//| level, penanda SDBot, HTML Telegram ter-escape, potong 4096 karakter
//| (spec 08 Req 1.2, 1.3, 4; design §3.4, §4.4). Fungsi murni.
//| Emoji dan tanda baca non-ASCII dibangun dari code point (NtCp), agar
//| hasil tidak bergantung pada encoding file sumber saat compile.
//+------------------------------------------------------------------+
#ifndef SDB_NOTIFY_NOTIFYFORMAT_MQH
#define SDB_NOTIFY_NOTIFYFORMAT_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/SchemaEnums.mqh>

#define SDB_NT_CLOSE_TAGS_MAX 3   // b, i, code bersarang paling dalam yang dipakai template

// Satu code point Unicode sebagai string UTF-16 (pasangan surrogate di atas U+FFFF).
string NtCp(const uint cp)
  {
   ushort u[];
   if(cp > 0xFFFF)
     {
      uint v = cp - 0x10000;
      ArrayResize(u, 2);
      u[0] = (ushort)(0xD800 + (v >> 10));
      u[1] = (ushort)(0xDC00 + (v & 0x3FF));
     }
   else
     {
      ArrayResize(u, 1);
      u[0] = (ushort)cp;
     }
   return ShortArrayToString(u);
  }

string NtDot() { return " " + NtCp(0x00B7) + " "; }

// & dulu agar entitas hasil escape tidak di-escape lagi (python-bot-lessons §2).
string NtEscape(const string s)
  {
   string r = s;
   StringReplace(r, "&", "&amp;");
   StringReplace(r, "<", "&lt;");
   StringReplace(r, ">", "&gt;");
   return r;
  }

string NtLevelEmoji(const ENUM_SDB_NT_LEVEL lv)
  {
   switch(lv)
     {
      case SDB_NT_CRITICAL: return NtCp(0x1F6A8);
      case SDB_NT_HIGH:     return NtCp(0x274C);
      case SDB_NT_MEDIUM:   return NtCp(0x26A0) + NtCp(0xFE0F);
      case SDB_NT_SUCCESS:  return NtCp(0x2705);
      default:              return NtCp(0x2139) + NtCp(0xFE0F);
     }
  }

// SUCCESS hanya tampilan: BE, partial, dan posisi tutup profit (design §8.1, §8.4).
ENUM_SDB_NT_LEVEL NtLevelOf(const ENUM_SDB_SEVERITY sev, const string type, const double netProfit)
  {
   if(type == SDB_ALERT_TYPE_BE_MOVED || type == SDB_ALERT_TYPE_PARTIAL_CLOSED)
      return SDB_NT_SUCCESS;
   if(type == SDB_ALERT_TYPE_TRADE_CLOSED)
      return netProfit > 0.0 ? SDB_NT_SUCCESS : SDB_NT_INFO;
   switch(sev)
     {
      case SDB_SEV_CRITICAL: return SDB_NT_CRITICAL;
      case SDB_SEV_HIGH:     return SDB_NT_HIGH;
      case SDB_SEV_MEDIUM:   return SDB_NT_MEDIUM;
      default:               return SDB_NT_INFO;
     }
  }

string NtTitle(const string type)
  {
   if(type == SDB_ALERT_TYPE_TRADE_OPENED)     return "Posisi dibuka";
   if(type == SDB_ALERT_TYPE_TRADE_CLOSED)     return "Posisi ditutup";
   if(type == SDB_ALERT_TYPE_BE_MOVED)         return "SL ke break-even";
   if(type == SDB_ALERT_TYPE_PARTIAL_CLOSED)   return "Partial close";
   if(type == SDB_ALERT_TYPE_SL_RESTORED)      return "SL dipasang kembali";
   if(type == SDB_ALERT_TYPE_SL_MISSING)       return "Posisi tanpa SL";
   if(type == SDB_ALERT_TYPE_DD_INFO)          return "Drawdown 5%";
   if(type == SDB_ALERT_TYPE_DD_REDUCE)        return "Drawdown 10%: lot x 0.5";
   if(type == SDB_ALERT_TYPE_DD_STOP)          return "Drawdown 15%: emergency stop";
   if(type == SDB_ALERT_TYPE_DD_RECOVERED)     return "Drawdown pulih";
   if(type == SDB_ALERT_TYPE_DAILY_LOSS)       return "Rugi harian: entry di-pause";
   if(type == SDB_ALERT_TYPE_MARGIN_LOW)       return "Margin rendah";
   if(type == SDB_ALERT_TYPE_MARGIN_OK)        return "Margin normal";
   if(type == SDB_ALERT_TYPE_CLOSE_ALL_FAILED) return "Close all gagal";
   if(type == SDB_ALERT_TYPE_EMERGENCY_RESET)  return "Emergency stop dibuka";
   if(type == SDB_ALERT_TYPE_STATE_RESET)      return "Status bersama di-reset";
   if(type == SDB_ALERT_TYPE_CONN_DOWN)        return "Koneksi terputus";
   if(type == SDB_ALERT_TYPE_CONN_UP)          return "Koneksi pulih";
   if(type == SDB_ALERT_TYPE_ORDER_FAILED)     return "Order gagal";
   if(type == SDB_ALERT_TYPE_MODIFY_FAILED)    return "Modifikasi posisi gagal";
   if(type == SDB_ALERT_TYPE_BALANCE_OP)       return "Operasi saldo";
   if(type == SDB_ALERT_TYPE_ACCOUNT_REJECTED) return "Akun ditolak";
   if(type == SDB_ALERT_TYPE_DB_UNAVAILABLE)   return "Database tidak bisa ditulis";
   if(type == SDB_ALERT_TYPE_DB_RECOVERED)     return "Database pulih";
   if(type == SDB_ALERT_TYPE_DB_NEWER_SCHEMA)  return "Database versi lebih baru";
   if(type == SDB_ALERT_TYPE_MIGRATION_FAILED) return "Migrasi database gagal";
   return type;
  }

string NtHeader(const SdbNtContext &c, const ENUM_SDB_NT_LEVEL lv)
  {
   return NtLevelEmoji(lv) + " <b>SDBot</b>" + NtDot() + NtEscape(c.symbol) + NtDot() + NtEscape(c.accountTag) +
          NtDot() + "v" + NtEscape(c.eaVersion);
  }

string NtCode(const string s) { return "<code>" + s + "</code>"; }

string NtPrice(const double p, const int digits) { return DoubleToString(p, digits); }

string NtMoney(const double v, const string ccy) { return DoubleToString(v, 2) + " " + NtEscape(ccy); }

string NtR(const double r) { return r == SDB_NULL_DOUBLE ? "-" : DoubleToString(r, 2); }

// Lot: minimal 2 desimal, sampai 3 bila langkah volume lebih kecil (mis. crypto).
string NtVolume(const double v)
  {
   string s = DoubleToString(v, 3);
   if(StringSubstr(s, StringLen(s) - 1) == "0")
      s = StringSubstr(s, 0, StringLen(s) - 1);
   return s;
  }

string NtDuration(const long sec)
  {
   if(sec < 60)
      return IntegerToString(sec) + "d";
   if(sec < 3600)
      return IntegerToString(sec / 60) + "m";
   return IntegerToString(sec / 3600) + "j " + IntegerToString((sec % 3600) / 60) + "m";
  }

string NtTruncMark() { return "\n" + NtCp(0x2026) + " (dipotong)"; }

// Panjang penutup untuk tag yang masih terbuka, mis. "</code></b>".
string NtClosers(const string &stack[], const int depth)
  {
   string r = "";
   for(int i = depth - 1; i >= 0; i--)
      r += "</" + stack[i] + ">";
   return r;
  }

// Potong <= maxLen tanpa memotong tag, entitas, atau pasangan surrogate; tag terbuka ditutup (Req 4.5).
string NtTruncate(const string html, const int maxLen)
  {
   int n = StringLen(html);
   if(n <= maxLen)
      return html;
   string mark = NtTruncMark();
   string stack[SDB_NT_CLOSE_TAGS_MAX + 1];
   int depth = 0;
   int bestPos = 0;
   string bestClose = "";
   int i = 0;
   while(i < n)
     {
      // Posisi i adalah batas aman: semua sebelum i utuh.
      string closers = NtClosers(stack, depth);
      if(i + StringLen(closers) + StringLen(mark) > maxLen)
         break;
      bestPos = i;
      bestClose = closers;
      ushort ch = StringGetCharacter(html, i);
      if(ch == '<')
        {
         int end = StringFind(html, ">", i);
         if(end < 0)
            break;
         string tag = StringSubstr(html, i + 1, end - i - 1);
         if(StringSubstr(tag, 0, 1) == "/")
           {
            if(depth > 0)
               depth--;
           }
         else if(depth <= SDB_NT_CLOSE_TAGS_MAX)
            stack[depth++] = tag;
         i = end + 1;
        }
      else if(ch == '&')
        {
         int end = StringFind(html, ";", i);
         i = (end < 0) ? i + 1 : end + 1;
        }
      else if(ch >= 0xD800 && ch <= 0xDBFF)
         i += 2;
      else
         i++;
     }
   return StringSubstr(html, 0, bestPos) + bestClose + mark;
  }

string NtFormatAlert(const SdbNtContext &c, const AlertEvent &a)
  {
   ENUM_SDB_NT_LEVEL lv = NtLevelOf(a.severity, a.type, 0.0);
   return NtTruncate(NtHeader(c, lv) + "\n<b>" + NtEscape(NtTitle(a.type)) + "</b>\n" + NtEscape(a.message), SDB_NT_MAX_LEN);
  }

string NtFormatOpened(const SdbNtContext &c, const TradeRecord &t)
  {
   string risk = (t.riskPct == SDB_NULL_DOUBLE) ? NtCode("-") : NtCode(DoubleToString(t.riskPct, 2) + "%");
   string money = (t.riskMoney == SDB_NULL_DOUBLE) ? "" : " (" + NtCode(NtMoney(t.riskMoney, c.currency)) + ")";
   string s = NtHeader(c, SDB_NT_INFO) + "\n<b>" + NtTitle(SDB_ALERT_TYPE_TRADE_OPENED) + "</b>\n" +
              NtCp(0x1F4CA) + " " + NtEscape(t.direction) + " " + NtCode(NtVolume(t.volumeInitial)) + " @ " +
              NtCode(NtPrice(t.priceOpen, c.digits)) + "\n" +
              NtCp(0x1F6D1) + " SL " + NtCode(NtPrice(t.slInitial, c.digits)) + NtDot() +
              NtCp(0x1F3AF) + " TP " + NtCode(NtPrice(t.tpInitial, c.digits)) + "\n" +
              NtCp(0x2696) + NtCp(0xFE0F) + " Risiko " + risk + money + "\n" +
              NtCp(0x1F194) + " " + NtCode(IntegerToString(t.positionId));
   return NtTruncate(s, SDB_NT_MAX_LEN);
  }

string NtFormatClosed(const SdbNtContext &c, const ClosureRecord &cl, const string direction)
  {
   ENUM_SDB_NT_LEVEL lv = NtLevelOf(SDB_SEV_INFO, SDB_ALERT_TYPE_TRADE_CLOSED, cl.netProfit);
   string s = NtHeader(c, lv) + "\n<b>" + NtTitle(SDB_ALERT_TYPE_TRADE_CLOSED) + ": " + NtEscape(cl.reason) + "</b>\n" +
              NtCp(0x1F4CA) + " " + NtEscape(direction) + " " + NtCode(NtVolume(cl.volumeTotal)) + NtDot() +
              NtCp(0x1F194) + " " + NtCode(IntegerToString(cl.positionId)) + "\n" +
              NtCp(0x1F4B5) + " Profit <b>" + NtMoney(cl.netProfit, c.currency) + "</b>" + NtDot() + "R " + NtCode(NtR(cl.rResult)) + "\n" +
              NtCp(0x23F1) + NtCp(0xFE0F) + " Lama " + NtCode(NtDuration(cl.holdingSec));
   return NtTruncate(s, SDB_NT_MAX_LEN);
  }

//--- Pesan berjadwal (spec 09 design §4.4). Heartbeat dan laporan tentang akun: penanda AKUN <login>.

// 1234567.891 -> "1,234,567.89" (tanpa tanda).
string NtGroupDigits(const double v)
  {
   string s = DoubleToString(MathAbs(v), 2);
   int dot = StringFind(s, ".");
   string whole = StringSubstr(s, 0, dot);
   string out = "";
   int n = StringLen(whole);
   for(int i = 0; i < n; i++)
     {
      if(i > 0 && (n - i) % 3 == 0)
         out += ",";
      out += StringSubstr(whole, i, 1);
     }
   return out + StringSubstr(s, dot);
  }

string NtMoneyGrouped(const double v, const string ccy)
  {
   return (v < 0.0 && MathAbs(v) >= 0.005 ? "-" : "") + NtGroupDigits(v) + " " + NtEscape(ccy);
  }

// "+120.00", "-48.00", "0.00": P&L per simbol di laporan.
string NtSigned(const double v)
  {
   if(MathAbs(v) < 0.005)
      return "0.00";
   return (v > 0.0 ? "+" : "-") + NtGroupDigits(v);
  }

string NtHeaderWith(const string emoji, const SdbNtContext &c, const string subject)
  {
   return emoji + " <b>SDBot</b>" + NtDot() + subject + NtDot() + NtEscape(c.accountTag) + NtDot() + "v" + NtEscape(c.eaVersion);
  }

string NtAccountSubject(const SdbNtContext &c) { return "AKUN " + IntegerToString(c.login); }

string NtFormatHeartbeat(const SdbNtContext &c, const SdbHeartbeat &h)
  {
   string s = NtHeaderWith(NtLevelEmoji(SDB_NT_INFO), c, NtAccountSubject(c)) + "\n<b>Heartbeat</b>\n" +
              NtCp(0x1F4B0) + " Balance " + NtCode(NtMoneyGrouped(h.balance, c.currency)) + NtDot() +
              "Equity " + NtCode(NtMoneyGrouped(h.equity, c.currency)) + "\n" +
              NtCp(0x1F4C9) + " DD dari puncak " + NtCode(DoubleToString(h.ddPct, 2) + "%") + NtDot() +
              "Status " + NtCode(NtEscape(h.riskStatus)) + "\n" +
              NtCp(0x1F4C8) + " Posisi SDBot " + NtCode(IntegerToString(h.sdbotPositions)) + NtDot() +
              "Instance hidup " + NtCode(IntegerToString(h.instancesAlive)) + "\n" +
              NtCp(0x1F515) + " Ditahan kuota jam lalu " + NtCode(IntegerToString(h.heldLastHour));
   return NtTruncate(s, SDB_NT_MAX_LEN);
  }

string NtFormatDailyReport(const SdbNtContext &c, const SdbDayStats &d)
  {
   string day = TimeToString((datetime)d.dayStart, TIME_DATE);
   StringReplace(day, ".", "-");
   string winRate = (d.closed > 0) ? DoubleToString(100.0 * d.wins / d.closed, 1) + "%" : "-";
   string s = NtHeaderWith(NtCp(d.net >= 0.0 ? 0x1F4C8 : 0x1F4C9), c, NtAccountSubject(c)) +
              "\n<b>Laporan harian " + day + "</b>\n" +
              NtCp(0x1F4B5) + " P&amp;L <b>" + NtSigned(d.net) + " " + NtEscape(c.currency) + "</b>" + NtDot() +
              NtCp(0x1F522) + " Posisi tutup " + NtCode(IntegerToString(d.closed)) + NtDot() +
              NtCp(0x1F3AF) + " Win rate " + NtCode(winRate) + "\n";
   string symbols = "";
   for(int i = 0; i < d.symbolCount; i++)
      symbols += (i > 0 ? NtDot() : "") + NtEscape(d.symbols[i]) + " " + NtCode(NtSigned(d.symbolNet[i]));
   if(symbols != "")
      s += symbols + "\n";
   s += NtCp(0x1F3E6) + " Operasi saldo " + NtCode(NtMoneyGrouped(d.balanceOps, c.currency)) + NtDot() +
        NtCp(0x1F4B0) + " Balance " + NtCode(NtMoneyGrouped(d.balanceNow, c.currency));
   return NtTruncate(s, SDB_NT_MAX_LEN);
  }

string NtFormatStart(const SdbNtContext &c, const SdbStartInfo &s)
  {
   string previous;
   if(!s.hasPrevious)
      previous = "Sesi pertama";
   else if(s.previousAbnormal)
      previous = NtLevelEmoji(SDB_NT_MEDIUM) + " Sesi lalu tidak ditutup normal";
   else
      previous = NtCp(0x1F558) + " Sesi lalu berhenti " + NtCode(TimeToString(s.previousEndedAt, TIME_DATE | TIME_MINUTES)) +
                 " (" + NtCode(NtEscape(s.previousReason)) + ")";
   string text = NtHeaderWith(NtCp(0x1F680), c, NtEscape(c.symbol)) + "\n<b>SDBot aktif</b>\n" +
                 NtCp(0x1F522) + " Magic " + NtCode(IntegerToString(s.magic)) + NtDot() +
                 "Preset " + NtCode(s.presetTag == "" ? "-" : NtEscape(s.presetTag)) + "\n" +
                 NtLevelEmoji(SDB_NT_SUCCESS) + " Validasi akun " + NtCode(NtEscape(s.validation)) + "\n" + previous;
   return NtTruncate(text, SDB_NT_MAX_LEN);
  }

string NtFormatStop(const SdbNtContext &c, const string reason)
  {
   return NtHeaderWith(NtCp(0x1F6D1), c, NtEscape(c.symbol)) + "\n<b>SDBot berhenti</b>\nAlasan " + NtCode(NtEscape(reason));
  }

#endif // SDB_NOTIFY_NOTIFYFORMAT_MQH
