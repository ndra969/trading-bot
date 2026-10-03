//+------------------------------------------------------------------+
//| TestPosition.mqh — modul posisi terhadap akun Strategy Tester
//| sungguhan (spec 06, TC-PS-xx): alertOnFail CExecutor, cache posisi,
//| kepemilikan dari deal pembuka, closure tepat sekali. Hanya di tester.
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTPOSITION_MQH
#define SDB_SUITES_TESTPOSITION_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/Suites/TestRisk.mqh>   // CTrkRig, TrkRequest
#include <SDBot/Position/PositionCache.mqh>
#include <SDBot/Position/ClosureTracker.mqh>
#include <SDBot/Position/Reconciler.mqh>

// TC-PS-02 (Req 5.3): kegagalan modify/partial dari manajer posisi tidak memicu alert CExecutor.
void RunTestPositionAlertOnFail(CTrkRig &r)
  {
   OrderRequest rq = TrkRequest(_Symbol, true, 300, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN) * 2);
   OrderResult ro;
   if(!r.exe.OpenMarket(rq, ro))
     {
      AssertTrue("TC-PS-02", "posisi uji terbuka | " + ro.rejectStage + " " + ro.detail, false);
      return;
     }
   string why;
   double better = rq.sl + 50 * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   r.sink.Reset();
   r.exe.SetForceRetcodeForTest(TRADE_RETCODE_REJECT);
   ENUM_SDB_EXEC quiet = r.exe.ModifySl((ulong)ro.positionId, better, why, false);
   ENUM_SDB_EXEC quietPartial = r.exe.ClosePartial((ulong)ro.positionId, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), why, false);
   int alertsQuiet = r.sink.CountAlert();
   ENUM_SDB_EXEC loud = r.exe.ModifySl((ulong)ro.positionId, better, why);
   int alertsLoud = r.sink.CountAlertType(SDB_ALERT_TYPE_MODIFY_FAILED);
   r.exe.SetForceRetcodeForTest(0);
   r.exe.CloseAllSdbot();
   AssertTrue("TC-PS-02", StringFormat("retcode REJECT: alertOnFail=false -> FAILED tanpa alert (%d); default -> FAILED + 1 MODIFY_FAILED (%d)",
                                       alertsQuiet, alertsLoud),
              quiet == SDB_EXEC_FAILED && quietPartial == SDB_EXEC_FAILED && alertsQuiet == 0 &&
              loud == SDB_EXEC_FAILED && alertsLoud == 1);
  }

// TC-PS-05 (temuan backtest dasar spec 13): retcode MARKET_CLOSED -> SKIPPED (dicoba tick berikutnya tanpa dihitung gagal),
// satu kiriman, tanpa alert walau alertOnFail, tanpa log ERROR.
void RunTestPositionMarketClosed(CTrkRig &r)
  {
   OrderRequest rq = TrkRequest(_Symbol, true, 300, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN) * 2);
   OrderResult ro;
   if(!r.exe.OpenMarket(rq, ro))
     {
      AssertTrue("TC-PS-05", "posisi uji terbuka | " + ro.rejectStage + " " + ro.detail, false);
      return;
     }
   string why;
   double better = rq.sl + 50 * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   r.sink.Reset();
   SdbLogCaptureStart();   // suite sudah menangkap log; mulai ulang agar hanya baris kasus ini yang dihitung
   long sentBefore = r.exe.SendCount();
   r.exe.SetForceRetcodeForTest(TRADE_RETCODE_MARKET_CLOSED);
   ENUM_SDB_EXEC m = r.exe.ModifySl((ulong)ro.positionId, better, why);
   ENUM_SDB_EXEC p = r.exe.ClosePartial((ulong)ro.positionId, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), why);
   r.exe.SetForceRetcodeForTest(0);
   long sent = r.exe.SendCount() - sentBefore;
   int errors = 0;
   for(int i = 0; i < SdbLogCapturedCount(); i++)
      if(StringFind(SdbLogCaptured(i), "[ERROR]") >= 0)
         errors++;
   int alerts = r.sink.CountAlert();
   r.exe.CloseAllSdbot();
   AssertTrue("TC-PS-05", StringFormat("MARKET_CLOSED: modify %s, partial %s, kiriman %I64d, alert %d, log ERROR %d",
                                       EnumToString(m), EnumToString(p), sent, alerts, errors),
              m == SDB_EXEC_SKIPPED && p == SDB_EXEC_SKIPPED && sent == 2 && alerts == 0 && errors == 0);
  }

// TC-PS-01 (Req 1.1, 1.2, EC-08): SL awal dari komentar; tanpa komentar dari ORDER_SL order pembuka.
void RunTestPositionCache(CTrkRig &r)
  {
   OrderRequest rq = TrkRequest(_Symbol, false, 250, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN) * 3);
   OrderResult ro;
   bool opened = r.exe.OpenMarket(rq, ro);
   CPositionCache c1, c2;
   c1.Init(r.inputs.magic, _Symbol, GetPointer(r.sink));
   c2.Init(r.inputs.magic, _Symbol, GetPointer(r.sink));
   c2.SetSkipCommentForTest(true);
   PositionCacheEntry e1, e2;
   bool g1 = opened && c1.Get((ulong)ro.positionId, e1);
   bool g2 = opened && c2.Get((ulong)ro.positionId, e2);
   double sl = NormalizeDouble(rq.sl, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
   bool other = c1.Owned(123456789);
   r.exe.CloseAllSdbot();
   AssertTrue("TC-PS-01", StringFormat("SL awal: komentar %s %.5f, tanpa komentar %s %.5f; volume awal %.2f; risiko %.2f; milik instance",
                                       EnumToString(e1.slSource), e1.initialSl, EnumToString(e2.slSource), e2.initialSl,
                                       e1.initialVolume, e1.riskMoney),
              g1 && g2 && e1.owned && !e1.isBuy && e1.slSource == SDB_SL_SRC_COMMENT && MathAbs(e1.initialSl - sl) < 1e-9 &&
              e2.slSource == SDB_SL_SRC_ORDER && MathAbs(e2.initialSl - sl) < 1e-9 &&
              MathAbs(e1.initialVolume - rq.volume) < 1e-9 && e1.riskMoney > 0.0 && e1.riskMoney != SDB_NULL_DOUBLE && !other);
  }

ulong TpsLastDeal(const ulong positionId, const ENUM_DEAL_ENTRY entry)
  {
   ulong found = 0;
   if(HistorySelectByPosition(positionId))
      for(int i = 0; i < HistoryDealsTotal(); i++)
        {
         ulong d = HistoryDealGetTicket(i);
         if(HistoryDealGetInteger(d, DEAL_ENTRY) == entry)
            found = d;
        }
   return found;
  }

// TC-PS-03 (Req 6.1–6.3, EC-15): posisi ditutup close all dari instance lain -> pemilik mencatat EA_CLOSE.
void RunTestPositionOwnership(CTrkRig &r)
  {
   OrderRequest rq = TrkRequest(_Symbol, true, 300, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   OrderResult ro;
   bool opened = r.exe.OpenMarket(rq, ro);
   CExecutor other;
   other.Init(2026091901, _Symbol, GetPointer(r.acc), GetPointer(r.st), GetPointer(r.sink), "test");
   other.CloseAllSdbot();
   ulong outDeal = TpsLastDeal((ulong)ro.positionId, DEAL_ENTRY_OUT);
   long outMagic = HistoryDealSelect(outDeal) ? HistoryDealGetInteger(outDeal, DEAL_MAGIC) : -1;

   CFakeSink ownerSink, otherSink;
   CPositionCache ownerCache, otherCache;
   ownerCache.Init(r.inputs.magic, _Symbol, GetPointer(ownerSink));
   otherCache.Init(2026091901, _Symbol, GetPointer(otherSink));
   CClosureTracker owner, stranger;
   owner.Init(r.inputs.magic, _Symbol, GetPointer(ownerCache), GetPointer(r.st), GetPointer(ownerSink), r.inputs.breakevenBufferPoints);
   stranger.Init(2026091901, _Symbol, GetPointer(otherCache), GetPointer(r.st), GetPointer(otherSink), r.inputs.breakevenBufferPoints);
   bool ownerDid = owner.ProcessDeal(outDeal);
   bool strangerDid = stranger.ProcessDeal(outDeal);
   ClosureRecord c;
   bool haveClosure = ownerSink.LastClosure(c);
   AssertTrue("TC-PS-03", StringFormat("deal penutup bermagic %I64d: pemilik mencatat deal + closure %s; instance lain mengabaikan",
                                       outMagic, haveClosure ? c.reason : "-"),
              opened && outDeal > 0 && outMagic == 2026091901 && ownerDid && !strangerDid && ownerSink.CountDeal() == 1 &&
              haveClosure && c.reason == SDB_CLOSE_REASON_EA_CLOSE && c.positionId == ro.positionId &&
              otherSink.CountDeal() == 0 && otherSink.CountClosure() == 0);
  }

// TC-PS-04 (Req 6.1, 6.2, EC-20): deal yang sama diproses dua kali -> tetap satu deal dan satu closure.
void RunTestPositionOnce(CTrkRig &r)
  {
   OrderRequest rq = TrkRequest(_Symbol, false, 300, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   OrderResult ro;
   bool opened = r.exe.OpenMarket(rq, ro);
   string why;
   r.exe.ClosePosition((ulong)ro.positionId, why);
   ulong inDeal = TpsLastDeal((ulong)ro.positionId, DEAL_ENTRY_IN);
   ulong outDeal = TpsLastDeal((ulong)ro.positionId, DEAL_ENTRY_OUT);
   CFakeSink sink;
   CPositionCache cache;
   cache.Init(r.inputs.magic, _Symbol, GetPointer(sink));
   CClosureTracker t;
   t.Init(r.inputs.magic, _Symbol, GetPointer(cache), GetPointer(r.st), GetPointer(sink), r.inputs.breakevenBufferPoints);
   bool a = t.ProcessDeal(inDeal);
   bool b = t.ProcessDeal(outDeal);
   bool c = t.ProcessDeal(outDeal);
   ClosureRecord cl;
   sink.LastClosure(cl);
   AssertTrue("TC-PS-04", StringFormat("IN lalu OUT dua kali: deal %d, closure %d, alasan %s, R hasil %.3f",
                                       sink.CountDeal(), sink.CountClosure(), cl.reason, cl.rResult),
              opened && a && b && !c && sink.CountDeal() == 2 && sink.CountClosure() == 1 &&
              cl.reason == SDB_CLOSE_REASON_EA_CLOSE && cl.rResult != SDB_NULL_DOUBLE && cache.Count() == 0);
  }

// TC-IN-06 (spec 07 Req 1.1, EC-06): R closure dijumlahkan di memori; R kosong tidak dihitung.
void RunTestPositionMetric(CTrkRig &r)
  {
   CPositionCache cache;
   cache.Init(r.inputs.magic, _Symbol, GetPointer(r.sink));
   CClosureTracker t;
   t.Init(r.inputs.magic, _Symbol, GetPointer(cache), GetPointer(r.st), GetPointer(r.sink), r.inputs.breakevenBufferPoints);
   t.NoteResult(2.0);
   t.NoteResult(SDB_NULL_DOUBLE);
   t.NoteResult(-1.0);
   AssertTrue("TC-IN-06", StringFormat("R 2.0, NULL, -1.0 -> total %.2f dari %d trade", t.TotalR(), t.TradesWithR()),
              MathAbs(t.TotalR() - 1.0) < 1e-12 && t.TradesWithR() == 2);
  }

void RunTestPosition()
  {
   TfBeginSuite("Position");
   if(!MQLInfoInteger(MQL_TESTER))
     {
      TfInfo("suite Position dilewati: hanya di Strategy Tester (membuka posisi)");
      TfEndSuite();
      return;
     }
   string prefix = TRK_PREFIX + "_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "_";
   GlobalVariablesDeleteAll(prefix);
   SdbLogCaptureStart();
   CTrkRig r;
   if(!r.Setup(_Symbol))
      AssertTrue("TC-PS-00", "rig posisi siap (akun tester lolos validasi)", false);
   else
     {
      RunTestPositionAlertOnFail(r);
      RunTestPositionMarketClosed(r);
      RunTestPositionCache(r);
      RunTestPositionOwnership(r);
      RunTestPositionOnce(r);
      RunTestPositionMetric(r);
     }
   SdbLogCaptureStop();
   GlobalVariablesDeleteAll(prefix);
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTPOSITION_MQH
