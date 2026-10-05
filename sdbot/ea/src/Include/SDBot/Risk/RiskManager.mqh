//+------------------------------------------------------------------+
//| RiskManager.mqh — CRiskManager: pintu risiko sebelum setiap entry
//| (spec 05 Req 1, 2; design §4.3): lot dari risiko persen dan
//| pre-trade check berurutan. Tidak pernah mengirim order sendiri; entry
//| tetap lewat CExecutor (Req 2.7).
//+------------------------------------------------------------------+
#ifndef SDB_RISK_RISKMANAGER_MQH
#define SDB_RISK_RISKMANAGER_MQH

#include <SDBot/Core/InputRules.mqh>
#include <SDBot/Account/Account.mqh>
#include <SDBot/Execution/Executor.mqh>
#include <SDBot/Risk/RiskState.mqh>
#include <SDBot/Risk/ExposureRules.mqh>

class CRiskManager
  {
private:
   string            m_symbol;
   CRiskState       *m_rs;
   CExecutor        *m_exe;
   CAccount         *m_acc;
   InputValues       m_in;
   int               m_limits[4];     // urutan ENUM_SDB_ASSET_CLASS: major, cross, komoditas, crypto
   double            m_marginOverride; // hook uji; < 0 = pakai OrderCheck
   double            m_balanceOverride; // hook uji; <= 0 = balance akun

   bool Reject(string &stage, string &detail, const string s, const string d)
     {
      stage = s;
      detail = d;
      LogThrottled(SDB_LOG_WARN, "risk_reject_" + s, SDB_LOG_THROTTLE_DEFAULT_SEC, "Risk", "entry ditolak | stage=" + s + " " + d);
      return false;
     }

   double EntryPrice(const bool isBuy)
     {
      MqlTick t;
      if(!SymbolInfoTick(m_symbol, t))
         return 0.0;
      return isBuy ? t.ask : t.bid;
     }

   // Rugi uang bila order kena SL (positif). false bila tidak bisa dihitung.
   bool OrderLossMoney(const OrderRequest &req, const double volume, double &loss)
     {
      double price = EntryPrice(req.isBuy);
      double p = 0.0;
      if(price <= 0.0 || !OrderCalcProfit(req.isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, m_symbol, volume, price, req.sl, p))
         return false;
      loss = -p;
      return true;
     }

   ENUM_SDB_ASSET_CLASS ClassOfSymbol(const string symbol)
     {
      return AssetClassOf(SymbolInfoString(symbol, SYMBOL_CURRENCY_BASE), SymbolInfoString(symbol, SYMBOL_CURRENCY_PROFIT));
     }

   double Balance() const { return (m_balanceOverride > 0.0) ? m_balanceOverride : AccountInfoDouble(ACCOUNT_BALANCE); }

   double EffRiskPct() { return EffectiveRiskPct(m_in.riskPerTradePct, m_rs.IsLotReduced()); }

public:
                     CRiskManager(void) : m_rs(NULL), m_exe(NULL), m_acc(NULL), m_marginOverride(-1.0), m_balanceOverride(0.0) {}

   bool Init(const string symbol, CRiskState *rs, CExecutor *exe, CAccount *acc, const InputValues &inputs)
     {
      m_symbol = symbol;
      m_rs = rs;
      m_exe = exe;
      m_acc = acc;
      m_in = inputs;
      m_limits[SDB_CLASS_FOREX_MAJOR] = inputs.maxPosForexMajor;
      m_limits[SDB_CLASS_FOREX_CROSS] = inputs.maxPosForexCross;
      m_limits[SDB_CLASS_COMMODITY] = inputs.maxPosCommodity;
      m_limits[SDB_CLASS_CRYPTO] = inputs.maxPosCrypto;
      return rs != NULL && exe != NULL && acc != NULL;
     }

   // Req 1: mengisi req.volume dari risiko efektif, balance, dan nilai uang jarak entry-SL.
   bool CalcVolume(OrderRequest &req, string &stage, string &detail)
     {
      double lossPerLot = 0.0;
      if(!OrderLossMoney(req, 1.0, lossPerLot))
         return Reject(stage, detail, SDB_REJECT_STAGE_OTHER, "OrderCalcProfit gagal " + ErrText(GetLastError()));
      double balance = Balance();
      ENUM_SDB_LOT_FLAG flag;
      double lot = CalcLotSize(balance, EffRiskPct(), lossPerLot, SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_STEP),
                               SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MIN), SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MAX), flag);
      string d = StringFormat("balance=%.2f risiko=%.3f%% uang/lot=%.4f", balance, EffRiskPct(), lossPerLot);
      if(flag == SDB_LOT_INVALID)
         return Reject(stage, detail, SDB_REJECT_STAGE_OTHER, "nilai uang per lot tidak valid | " + d);
      if(flag == SDB_LOT_BELOW_MIN)
         return Reject(stage, detail, SDB_REJECT_STAGE_LOT_BELOW_MIN,
                       StringFormat("lot < minimum %.2f | %s", SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MIN), d));
      if(flag == SDB_LOT_CAPPED_MAX)
         LogWarn("Risk", StringFormat("lot dibatasi SYMBOL_VOLUME_MAX %.2f | %s", lot, d));
      // OrderCalcProfit membulatkan uang ke digit akun, sehingga rugi lot akhir bisa sedikit di atas uang/lot x lot
      // (temuan SC-14 spec 13, TC-RK-14). Galat uang/lot 1 lot (sampai 0,26% di akun cent dengan kuotasi bukan USD)
      // dikali puluhan lot bisa butuh banyak step (TC-RK-19), jadi lot diturunkan proporsional dulu, lalu per step.
      double step = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_STEP), vMin = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MIN);
      double limit = balance * EffRiskPct() / 100.0, loss = 0.0;
      for(int i = 0; i < SDB_LOT_FIT_STEPS && OrderLossMoney(req, lot, loss) && RiskPctOf(loss, balance) > EffRiskPct() + SDB_RISK_EPS; i++)
         lot = RoundLotDown(MathMin(lot - step, lot * limit / loss), step);
      if(lot < vMin - 1e-9 || !OrderLossMoney(req, lot, loss) || RiskPctOf(loss, balance) > EffRiskPct() + SDB_RISK_EPS)
         return Reject(stage, detail, SDB_REJECT_STAGE_LOT_BELOW_MIN,
                       StringFormat("lot minimum %.2f melebihi risiko %.2f setelah pembulatan uang | %s", vMin, limit, d));
      req.volume = lot;
      stage = "";
      detail = d;
      return true;
     }

   // Req 2.1: urutan tetap, berhenti di penolakan pertama. Status dibaca dari GV setiap kali (6.2).
   bool PreTradeCheck(const OrderRequest &req, string &stage, string &detail)
     {
      string why;
      if(m_acc == NULL || !m_acc.CanTrade(why))
         return Reject(stage, detail, SDB_REJECT_STAGE_NOT_TRADABLE, why);
      if(!m_rs.IsReady())
         return Reject(stage, detail, SDB_REJECT_STAGE_NOT_TRADABLE, "status risiko bersama belum siap");
      if(m_rs.IsStopped())
         return Reject(stage, detail, SDB_REJECT_STAGE_STOPPED, "emergency stop aktif, butuh reset manual");
      if(m_rs.IsDailyPaused())
         return Reject(stage, detail, SDB_REJECT_STAGE_DAILY_PAUSE, "batas rugi harian tercapai");
      double balance = Balance();
      double loss = 0.0;
      if(!OrderLossMoney(req, req.volume, loss))
         return Reject(stage, detail, SDB_REJECT_STAGE_OTHER, "OrderCalcProfit gagal " + ErrText(GetLastError()));
      double newPct = RiskPctOf(loss, balance);
      if(newPct > EffRiskPct() + SDB_RISK_EPS)
         return Reject(stage, detail, SDB_REJECT_STAGE_RISK_PER_TRADE,
                       StringFormat("risiko order %.5f%% > %.5f%% (vol %.2f, rugi %.4f, balance %.2f, sl %s)", newPct, EffRiskPct(), req.volume,
                                    loss, balance, DoubleToString(req.sl, (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS))));
      double openPct = RiskPctOf(OpenRiskMoney(), balance);
      if(openPct + newPct > m_in.maxOpenRiskPct + SDB_RISK_EPS)
         return Reject(stage, detail, SDB_REJECT_STAGE_MAX_OPEN_RISK,
                       StringFormat("terbuka %.2f%% + order %.2f%% > %.2f%%", openPct, newPct, m_in.maxOpenRiskPct));
      ENUM_SDB_ASSET_CLASS cls = ClassOfSymbol(m_symbol);
      int count = CountSdbotPositionsInClass(cls);
      int limit = ClassPositionLimit(cls, m_limits);
      if(count >= limit)
         return Reject(stage, detail, SDB_REJECT_STAGE_CLASS_POSITION_LIMIT,
                       StringFormat("%s: %d posisi >= batas %d", EnumToString(cls), count, limit));
      // Eksposur mata uang dengan arah (spec 15 Req 2.1-2.2): setelah batas kategori, sebelum margin.
      string legCcy[];
      int legDir[];
      CollectSdbotLegs(legCcy, legDir);
      string expDetail;
      if(!ExposureAllowed(legCcy, legDir, CurrencyOf(m_symbol, SYMBOL_CURRENCY_BASE), CurrencyOf(m_symbol, SYMBOL_CURRENCY_PROFIT), req.isBuy,
                          m_in.maxSameDirectionPerCurrency, expDetail))
         return Reject(stage, detail, SDB_REJECT_STAGE_CURRENCY_EXPOSURE, expDetail);
      double ml = (m_marginOverride >= 0.0) ? m_marginOverride : m_exe.MarginLevelAfter(req);
      if(ml < SDB_MARGIN_BLOCK_PCT)
         return Reject(stage, detail, SDB_REJECT_STAGE_MARGIN_LOW, StringFormat("margin level sesudah order %.0f%% < %.0f%%", ml, SDB_MARGIN_BLOCK_PCT));
      stage = "";
      detail = StringFormat("risiko %.3f%%, terbuka %.2f%%, %s %d/%d, margin %.0f%%", newPct, openPct, EnumToString(cls), count, limit, ml);
      return true;
     }

   // Req 2.4, 2.5: semua posisi SDBot di akun, simbol mana pun.
   double OpenRiskMoney()
     {
      double total = 0.0;
      double balance = Balance();
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         if(PositionGetTicket(i) == 0 || !IsSdbotMagic(PositionGetInteger(POSITION_MAGIC)))
            continue;
         bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
         string sym = PositionGetString(POSITION_SYMBOL);
         double open = PositionGetDouble(POSITION_PRICE_OPEN);
         double sl = PositionGetDouble(POSITION_SL);
         double p = 0.0;
         if(sl > 0.0 && !OrderCalcProfit(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, sym, PositionGetDouble(POSITION_VOLUME), open, sl, p))
           {
            LogThrottled(SDB_LOG_WARN, "risk_open_calc", SDB_LOG_THROTTLE_DEFAULT_SEC, "Risk",
                         "risiko posisi tidak bisa dihitung, dianggap 1% | pos=" + IntegerToString(PositionGetInteger(POSITION_IDENTIFIER)));
            sl = 0.0;
           }
         if(sl <= 0.0)
            LogThrottled(SDB_LOG_WARN, "risk_open_nosl", SDB_LOG_THROTTLE_DEFAULT_SEC, "Risk",
                         "posisi SDBot tanpa SL dihitung berisiko 1% balance | pos=" + IntegerToString(PositionGetInteger(POSITION_IDENTIFIER)));
         total += PositionRiskMoney(isBuy, open, sl, p, balance, SDB_NO_SL_RISK_PCT);
        }
      return total;
     }

   // Req 2.8: kategori posisi dari mata uang simbolnya, di semua simbol.
   // Mata uang dasar/kuotasi simbol; kosong = tidak menambah eksposur, WARN per simbol per menit (Req 1.4).
   string CurrencyOf(const string symbol, const ENUM_SYMBOL_INFO_STRING prop)
     {
      string c = SymbolInfoString(symbol, prop);
      if(c == "")
         LogThrottled(SDB_LOG_WARN, "exposure-ccy-" + symbol, SDB_LOG_THROTTLE_DEFAULT_SEC, "Risk",
                      "mata uang simbol " + symbol + " tidak terbaca, tidak dihitung di eksposur");
      return c;
     }

   // Kaki mata uang semua posisi SDBot di akun, simbol mana pun (Req 1.1-1.3; PC-02).
   void CollectSdbotLegs(string &ccy[], int &dir[])
     {
      ArrayFree(ccy);
      ArrayFree(dir);
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         if(PositionGetTicket(i) == 0 || !IsSdbotMagic(PositionGetInteger(POSITION_MAGIC)))
            continue;
         string sym = PositionGetString(POSITION_SYMBOL);
         bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
         AddLegs(CurrencyOf(sym, SYMBOL_CURRENCY_BASE), CurrencyOf(sym, SYMBOL_CURRENCY_PROFIT), isBuy, ccy, dir);
        }
     }

   int CountSdbotPositionsInClass(const ENUM_SDB_ASSET_CLASS c)
     {
      int n = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
         if(PositionGetTicket(i) != 0 && IsSdbotMagic(PositionGetInteger(POSITION_MAGIC)) &&
            ClassOfSymbol(PositionGetString(POSITION_SYMBOL)) == c)
            n++;
      return n;
     }

   //--- Hook uji: margin level rendah tidak bisa dipicu di tester tanpa melewati batas risiko lebih dulu.
   void SetMarginLevelForTest(const double v) { m_marginOverride = v; }
   void SetBalanceForTest(const double v)     { m_balanceOverride = v; }
  };

#endif // SDB_RISK_RISKMANAGER_MQH
