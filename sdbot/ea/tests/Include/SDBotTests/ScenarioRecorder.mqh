//+------------------------------------------------------------------+
//| ScenarioRecorder.mqh — CScenarioRecorder: sink pengamat harness
//| (spec 04 Req 7.6, design §4.6). Menyimpan event yang dikirim modul,
//| hasil setiap OpenMarket, ID sesi tiap init, dan posisi sebelum/
//| sesudah restart. Hidup di luar CSdbApp agar selamat dari restart.
//+------------------------------------------------------------------+
#ifndef SDB_SDBOTTESTS_SCENARIORECORDER_MQH
#define SDB_SDBOTTESTS_SCENARIORECORDER_MQH

#include <SDBot/Core/EventSink.mqh>

// Sampel analisis struktur satu bar (SC-12): hasil yang dipakai EA selama run.
struct SdbAnalysisSample
  {
   ENUM_TIMEFRAMES   tf;
   datetime          barTime;
   bool              ready;
   int               structDir;
   double            bosLevel;
   datetime          bosTime;
   int               emaDir;
   double            ema;
   int               bias;            // HTF saja
   datetime          recordedAt;      // TimeCurrent saat direkam (sebelum/sesudah restart)
  };

class CScenarioRecorder : public ISdbEventSink
  {
private:
   TradeRecord       m_trades[];
   AlertEvent        m_alerts[];
   datetime          m_snapshotTimes[];
   OrderResult       m_opens[];
   datetime          m_openTimes[];
   long              m_sessions[];
   long              m_posBeforeRestart[];
   long              m_posAfterRestart[];
   datetime          m_firstStoppedAt;     // sampel timer pertama dengan STOPPED aktif
   datetime          m_lastOpenWhileStopped; // sampel terakhir STOPPED dengan posisi SDBot masih ada
   datetime          m_restartAt;
   datetime          m_reattachAt;
   long              m_restartPosition;
   BalanceOpRecord   m_balanceOps[];
   AlertStatus       m_statuses[];
   double            m_withdrawAmount;     // SC-07: penarikan harness, puncak dan level DD sebelum/sesudah diproses
   double            m_peakBefore;
   int               m_levelBefore;
   double            m_peakAfter;
   int               m_levelAfter;
   bool              m_afterSampled;
   int               m_notifyQueueAtStop;   // antrean notifier setelah deinit (SC-10)
   SdbAnalysisSample m_samples[];           // analisis HTF/MTF per bar baru (SC-12)
   long              m_sends;           // jumlah OrderSend dari semua CExecutor (termasuk sebelum restart)
   DealRecord        m_dealRecs[];
   PositionEvent     m_events[];
   ClosureRecord     m_closureRecs[];

   static void PushLong(long &arr[], const long v)
     {
      int n = ArraySize(arr);
      ArrayResize(arr, n + 1);
      arr[n] = v;
     }

public:
                     CScenarioRecorder(void) : m_withdrawAmount(0), m_peakBefore(0), m_levelBefore(-1), m_peakAfter(0), m_levelAfter(-1), m_afterSampled(false), m_firstStoppedAt(0), m_lastOpenWhileStopped(0), m_restartAt(0), m_reattachAt(0), m_restartPosition(0), m_notifyQueueAtStop(-1), m_sends(0) {}

   //--- ISdbEventSink
   // Jam timer (TimeLocal), bukan a.time: a.time = waktu tick terakhir, yang tertinggal dari jadwal
   // snapshot saat tidak ada tick, sehingga jedanya tampak 59 atau 31 detik.
   void OnAccount(const AccountSnapshot &a)
     {
      int n = ArraySize(m_snapshotTimes);
      ArrayResize(m_snapshotTimes, n + 1);
      m_snapshotTimes[n] = TimeLocal();
     }
   void OnTradeOpened(const TradeRecord &t)
     {
      int n = ArraySize(m_trades);
      ArrayResize(m_trades, n + 1);
      m_trades[n] = t;
     }
   void OnAlert(const AlertEvent &a)
     {
      int n = ArraySize(m_alerts);
      ArrayResize(m_alerts, n + 1);
      m_alerts[n] = a;
     }
   void OnDeal(const DealRecord &d)
     {
      int n = ArraySize(m_dealRecs);
      ArrayResize(m_dealRecs, n + 1);
      m_dealRecs[n] = d;
     }
   void OnPositionEvent(const PositionEvent &e)
     {
      int n = ArraySize(m_events);
      ArrayResize(m_events, n + 1);
      m_events[n] = e;
     }
   void OnClosure(const ClosureRecord &c)
     {
      int n = ArraySize(m_closureRecs);
      ArrayResize(m_closureRecs, n + 1);
      m_closureRecs[n] = c;
     }
   void OnBalanceOp(const BalanceOpRecord &b)
     {
      int n = ArraySize(m_balanceOps);
      ArrayResize(m_balanceOps, n + 1);
      m_balanceOps[n] = b;
     }
   void OnAlertStatus(const AlertStatus &s)
     {
      int n = ArraySize(m_statuses);
      ArrayResize(m_statuses, n + 1);
      m_statuses[n] = s;
     }
   bool FindInitialSl(const long login, const ulong positionId, double &sl) { sl = 0.0; return false; }

   //--- Catatan dari harness
   void AddOpenResult(const OrderResult &r, const datetime time)
     {
      int n = ArraySize(m_opens);
      ArrayResize(m_opens, n + 1);
      ArrayResize(m_openTimes, n + 1);
      m_opens[n] = r;
      m_openTimes[n] = time;
     }
   void NoteStoppedSample(const datetime t, const int sdbotPositions)
     {
      if(m_firstStoppedAt == 0)
         m_firstStoppedAt = t;
      if(sdbotPositions > 0)
         m_lastOpenWhileStopped = t;
     }
   void NoteRestart(const datetime t)              { m_restartAt = t; }
   void NoteReattach(const datetime t)             { m_reattachAt = t; }
   datetime ReattachAt() const                     { return m_reattachAt; }
   void NoteRestartPosition(const long id)         { m_restartPosition = id; }
   long RestartPosition() const                    { return m_restartPosition; }
   void NoteWithdraw(const double amount, const double peak, const int level)
     {
      m_withdrawAmount = amount;
      m_peakBefore = peak;
      m_levelBefore = level;
     }
   // Dipanggil harness setiap timer; mengambil sampel sekali, tepat setelah operasi saldo pertama tercatat.
   void NoteAfterBalanceOp(const double peak, const int level)
     {
      if(m_afterSampled || ArraySize(m_balanceOps) == 0)
         return;
      m_afterSampled = true;
      m_peakAfter = peak;
      m_levelAfter = level;
     }
   int    BalanceOpCount() const                   { return ArraySize(m_balanceOps); }
   bool   BalanceOpAt(const int i, BalanceOpRecord &b) const
     {
      if(i < 0 || i >= ArraySize(m_balanceOps))
         return false;
      b = m_balanceOps[i];
      return true;
     }
   double WithdrawAmount() const { return m_withdrawAmount; }
   double PeakBefore() const     { return m_peakBefore; }
   int    LevelBefore() const    { return m_levelBefore; }
   double PeakAfter() const      { return m_peakAfter; }
   int    LevelAfter() const     { return m_levelAfter; }
   datetime FirstStoppedAt() const                 { return m_firstStoppedAt; }
   datetime LastOpenWhileStopped() const           { return m_lastOpenWhileStopped; }
   datetime RestartAt() const                      { return m_restartAt; }
   void AddSession(const long sessionId)           { PushLong(m_sessions, sessionId); }
   void AddSends(const long n)                     { m_sends += n; }
   void AddPositionBeforeRestart(const long id)    { PushLong(m_posBeforeRestart, id); }
   void AddPositionAfterRestart(const long id)     { PushLong(m_posAfterRestart, id); }

   //--- Bacaan untuk pemeriksa skenario
   int  TradeCount() const                  { return ArraySize(m_trades); }
   bool TradeAt(const int i, TradeRecord &t) const
     {
      if(i < 0 || i >= ArraySize(m_trades))
         return false;
      t = m_trades[i];
      return true;
     }
   int  DealCount() const                   { return ArraySize(m_dealRecs); }
   bool DealAt(const int i, DealRecord &d) const
     {
      if(i < 0 || i >= ArraySize(m_dealRecs))
         return false;
      d = m_dealRecs[i];
      return true;
     }
   long LastPartialPosition() const
     {
      for(int i = ArraySize(m_events) - 1; i >= 0; i--)
         if(m_events[i].type == SDB_POSITION_EVENT_PARTIAL)
            return m_events[i].positionId;
      return 0;
     }
   bool WasOpenBeforeRestart(const long id) const
     {
      for(int i = 0; i < ArraySize(m_posBeforeRestart); i++)
         if(m_posBeforeRestart[i] == id)
            return true;
      return false;
     }
   // Posisi yang pertama kali melakukan partial; 0 = belum ada.
   long FirstPartialPosition() const
     {
      for(int i = 0; i < ArraySize(m_events); i++)
         if(m_events[i].type == SDB_POSITION_EVENT_PARTIAL)
            return m_events[i].positionId;
      return 0;
     }
   int  EventCount() const                  { return ArraySize(m_events); }
   bool EventAt(const int i, PositionEvent &e) const
     {
      if(i < 0 || i >= ArraySize(m_events))
         return false;
      e = m_events[i];
      return true;
     }
   int  ClosureCount() const                { return ArraySize(m_closureRecs); }
   bool ClosureAt(const int i, ClosureRecord &c) const
     {
      if(i < 0 || i >= ArraySize(m_closureRecs))
         return false;
      c = m_closureRecs[i];
      return true;
     }
   int  AlertCount() const                  { return ArraySize(m_alerts); }
   bool AlertAt(const int i, AlertEvent &a) const
     {
      if(i < 0 || i >= ArraySize(m_alerts))
         return false;
      a = m_alerts[i];
      return true;
     }
   int      SnapshotCount() const           { return ArraySize(m_snapshotTimes); }
   datetime SnapshotTime(const int i) const { return m_snapshotTimes[i]; }
   int  OpenCount() const                   { return ArraySize(m_opens); }
   bool OpenAt(const int i, OrderResult &r) const
     {
      if(i < 0 || i >= ArraySize(m_opens))
         return false;
      r = m_opens[i];
      return true;
     }
   datetime OpenTimeAt(const int i) const   { return m_openTimes[i]; }
   int  OpenOkCount() const
     {
      int n = 0;
      for(int i = 0; i < ArraySize(m_opens); i++)
         if(m_opens[i].ok)
            n++;
      return n;
     }
   int  SessionCount() const                { return ArraySize(m_sessions); }
   long SessionAt(const int i) const        { return m_sessions[i]; }
   long Sends() const                       { return m_sends; }
   int  PositionsBeforeRestart() const      { return ArraySize(m_posBeforeRestart); }
   long PositionBeforeRestartAt(const int i) const { return m_posBeforeRestart[i]; }
   bool HasPositionAfterRestart(const long id) const
     {
      for(int i = 0; i < ArraySize(m_posAfterRestart); i++)
         if(m_posAfterRestart[i] == id)
            return true;
      return false;
     }

   // "1,2,3" untuk klausa SQL IN; "0" bila belum ada sesi (tidak cocok dengan id mana pun).
   void SetNotifyQueueAtStop(const int n)   { m_notifyQueueAtStop = n; }
   void AddAnalysisSample(const SdbAnalysisSample &s)
     {
      int n = ArraySize(m_samples);
      ArrayResize(m_samples, n + 1, 512);
      m_samples[n] = s;
     }
   int  SampleCount() const                 { return ArraySize(m_samples); }
   bool SampleAt(const int i, SdbAnalysisSample &out) const
     {
      if(i < 0 || i >= ArraySize(m_samples))
         return false;
      out = m_samples[i];
      return true;
     }
   int  NotifyQueueAtStop() const           { return m_notifyQueueAtStop; }

   string SessionIdList() const
     {
      string s = "";
      for(int i = 0; i < ArraySize(m_sessions); i++)
         s += (i > 0 ? "," : "") + IntegerToString(m_sessions[i]);
      return (s == "") ? "0" : s;
     }
  };

#endif // SDB_SDBOTTESTS_SCENARIORECORDER_MQH
