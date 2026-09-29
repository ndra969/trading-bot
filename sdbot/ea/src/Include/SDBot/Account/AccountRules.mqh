//+------------------------------------------------------------------+
//| AccountRules.mqh — aturan keputusan akun, izin trading, dan koneksi
//| sebagai fungsi murni (spec 02 Req 2–3), agar semua kombinasi akun
//| (demo, real, cent, netting) bisa diuji tanpa akun sungguhan.
//+------------------------------------------------------------------+
#ifndef SDB_ACCOUNT_ACCOUNTRULES_MQH
#define SDB_ACCOUNT_ACCOUNTRULES_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>

// Akun cent terbaca sebagai REAL oleh MT5; dibedakan dari mata uang akunnya.
ENUM_SDB_ACCOUNT_TYPE AccountTypeOf(const ENUM_ACCOUNT_TRADE_MODE mode, const string currency)
  {
   if(mode != ACCOUNT_TRADE_MODE_REAL)
      return SDB_ACC_DEMO;
   if(currency != "" && StringFind("," + SDB_CENT_CURRENCIES + ",", "," + currency + ",") >= 0)
      return SDB_ACC_CENT;
   return SDB_ACC_REAL;
  }

string ArJoin(const string a, const string b) { return (a == "") ? b : a + "; " + b; }

// true bila akun boleh dipakai. Semua alasan penolakan digabung dalam reason.
bool EvaluateAccount(const ENUM_ACCOUNT_TRADE_MODE mode, const ENUM_ACCOUNT_MARGIN_MODE margin,
                     const bool allowLive, string &reason)
  {
   reason = "";
   if(mode == ACCOUNT_TRADE_MODE_REAL && !allowLive)
      reason = ArJoin(reason, "akun real (termasuk cent) dan InpAllowLiveTrading=false");
   if(margin == ACCOUNT_MARGIN_MODE_RETAIL_NETTING)
      reason = ArJoin(reason, "mode margin NETTING tidak didukung, SDBot butuh HEDGING");
   else if(margin == ACCOUNT_MARGIN_MODE_EXCHANGE)
      reason = ArJoin(reason, "mode margin EXCHANGE tidak didukung, SDBot butuh HEDGING");
   return reason == "";
  }

bool SymbolMatchesSuffix(const string symbol, const string suffix)
  {
   int ls = StringLen(symbol);
   int lf = StringLen(suffix);
   if(lf == 0)
      return true;
   if(lf > ls)
      return false;
   return StringSubstr(symbol, ls - lf) == suffix;
  }

// true bila boleh trading. why menyebut semua izin yang mati, dengan nama properti MT5-nya.
bool TradePermission(const bool connected, const bool terminalTrade, const bool mqlTrade, const bool accTrade,
                     const bool accExpert, const ENUM_SYMBOL_TRADE_MODE symMode, string &why)
  {
   why = "";
   if(!connected)
      why = ArJoin(why, "TERMINAL_CONNECTED=false");
   if(!terminalTrade)
      why = ArJoin(why, "TERMINAL_TRADE_ALLOWED=false (tombol Algo Trading)");
   if(!mqlTrade)
      why = ArJoin(why, "MQL_TRADE_ALLOWED=false (izin trading EA)");
   if(!accTrade)
      why = ArJoin(why, "ACCOUNT_TRADE_ALLOWED=false");
   if(!accExpert)
      why = ArJoin(why, "ACCOUNT_TRADE_EXPERT=false");
   if(symMode != SYMBOL_TRADE_MODE_FULL)
      why = ArJoin(why, "SYMBOL_TRADE_MODE=" + EnumToString(symMode));
   return why == "";
  }

// Satu langkah pengecekan koneksi per siklus timer. State (downSince, lastAlert, alerted)
// dipegang pemanggil agar urutan waktu apa pun bisa diuji.
ENUM_SDB_CONN_ACTION ConnectionStep(const bool connected, const datetime now, datetime &downSince,
                                    datetime &lastAlert, bool &alerted)
  {
   if(connected)
     {
      bool wasAlerted = alerted;
      downSince = 0;
      lastAlert = 0;
      alerted = false;
      return wasAlerted ? SDB_CONN_ALERT_RECOVERED : SDB_CONN_NONE;
     }
   if(downSince == 0)
     {
      downSince = now;
      return SDB_CONN_LOG_DOWN;
     }
   if(now - downSince < SDB_DISCONNECT_ALERT_SEC)
      return SDB_CONN_NONE;
   if(lastAlert != 0 && now - lastAlert < SDB_CONN_ALERT_REPEAT_SEC)
      return SDB_CONN_NONE;
   lastAlert = now;
   alerted = true;
   return SDB_CONN_ALERT_MEDIUM;
  }

#endif // SDB_ACCOUNT_ACCOUNTRULES_MQH
