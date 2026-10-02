//+------------------------------------------------------------------+
//| Notifier.mqh — CNotifier: event sink yang mengubah alert dan event
//| trade menjadi notifikasi (spec 08 Req 1–3, 6; design §3.6), plus push
//| HP, pesan berjadwal (heartbeat, laporan harian), start dan stop
//| (spec 09). Penilaian (cooldown, kuota) saat event masuk; pengiriman
//| hanya dari OnTimer (maks 2 per siklus) atau Drain saat deinit. Status
//| kirim dilaporkan ke store (Logger) lewat OnAlertStatus; notifier
//| tidak menulis DB dan tidak memanggil modul trading (RULES).
//+------------------------------------------------------------------+
#ifndef SDB_NOTIFY_NOTIFIER_MQH
#define SDB_NOTIFY_NOTIFIER_MQH

#include <SDBot/Core/EventSink.mqh>
#include <SDBot/Core/State.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Notify/NotifyRules.mqh>
#include <SDBot/Notify/NotifyFormat.mqh>
#include <SDBot/Notify/Transport.mqh>
#include <SDBot/Notify/Push.mqh>
#include <SDBot/Notify/StatusSource.mqh>
#include <SDBot/Notify/NotifySchedule.mqh>
#include <SDBot/Notify/DailyStats.mqh>

class CNotifier : public ISdbEventSink
  {
private:
   ISdbEventSink    *m_store;          // Logger: baris alerts event trade dan status kirim
   ISdbTransport    *m_transport;
   SdbNtContext      m_ctx;
   CState           *m_state;          // NULL = cooldown/kuota akun di memori (akun belum PASSED)
   SdbNtItem         m_queue[];
   long              m_nowOverride;
   string            m_keyPrefix;
   long              m_seq;
   long              m_waitUntil;      // transport minta jeda (LIMITED)
   string            m_cdTypes[];      // cooldown di memori: tipe instance, dan tipe akun tanpa GV
   long              m_cdAt[];
   double            m_quotaMem;       // kuota tanpa GV, format sama dengan GV NT_QUOTA
   long              m_heldHour;
   int               m_held;
   long              m_posIds[];       // arah posisi dari pembukaan, untuk pesan tutup
   string            m_posDirs[];
   ISdbPush         *m_push;           // NULL = tanpa push (uji spec 08)
   ISdbStatusSource *m_status;         // data heartbeat dari App
   CNotifySchedule   m_schedule;
   int               m_hbMinutes;
   long              m_magic;
   bool              m_telegramOff;
   bool              m_pushSetupWarned;
   string            m_pushTexts[];    // push tertunda karena batas terminal (Req 3.4)
   string            m_pushKeys[];     // "" = pemberitahuan tanpa baris alerts
   int               m_pushAttempts[];

   long Now() const
     {
      if(m_nowOverride > 0)
         return m_nowOverride;
      // TimeCurrent berhenti saat pasar tutup; waktu server berjalan dipakai di live (Req 2.9).
      return MQLInfoInteger(MQL_TESTER) ? (long)TimeCurrent() : (long)TimeTradeServer();
     }

   bool StateReady() const { return m_state != NULL && m_state.IsReady(); }

   void Report(const string key, const string status, const int attempts, const long sentAt, const string reason)
     {
      if(m_store == NULL)
         return;
      AlertStatus s;
      s.key = key;
      s.status = status;
      s.attempts = attempts;
      s.sentAt = (datetime)sentAt;
      s.reason = reason;
      m_store.OnAlertStatus(s);
     }

   //--- Cooldown dan kuota
   bool MemCooldownTake(const string slot, const long now, const int sec)
     {
      int n = ArraySize(m_cdTypes);
      for(int i = 0; i < n; i++)
         if(m_cdTypes[i] == slot)
           {
            if(!NtCooldownOk(m_cdAt[i], now, sec))
               return false;
            m_cdAt[i] = now;
            return true;
           }
      ArrayResize(m_cdTypes, n + 1);
      ArrayResize(m_cdAt, n + 1);
      m_cdTypes[n] = slot;
      m_cdAt[n] = now;
      return true;
     }

   // Compare-and-set agar instance lain yang menang lebih dulu tidak ditimpa (Req 2.5).
   bool GvCooldownTake(const string type, const long now, const int sec)
     {
      string name = SDB_GV_NT_CD_PREFIX + type;
      string key = m_state.Key(name);
      for(int r = 0; r < SDB_CAS_RETRY; r++)
        {
         if(!GlobalVariableCheck(key))
            m_state.Set(name, 0.0, false);
         double old = m_state.Get(name, 0.0);
         if(!NtCooldownOk((long)old, now, sec))
            return false;
         if(GlobalVariableSetOnCondition(key, (double)now, old))
            return true;
        }
      LogThrottled(SDB_LOG_ERROR, "nt-cas-" + name, SDB_LOG_THROTTLE_DEFAULT_SEC, "Notify", "compare-and-set cooldown gagal berulang | gv=" + key);
      return false;
     }

   // Cek tanpa memakai: pesan yang lalu ditahan kuota tidak boleh memakai cooldown tipenya.
   bool CooldownFree(const AlertEvent &a, const long now)
     {
      int sec = NtCooldownSec(a.severity, a.type);
      if(sec <= 0)
         return true;
      bool account = (NtScopeOf(a.type) == SDB_NT_SCOPE_ACCOUNT);
      if(account && StateReady())
         return NtCooldownOk((long)m_state.Get(SDB_GV_NT_CD_PREFIX + a.type, 0.0), now, sec);
      string slot = (account ? "A:" : "I:") + a.type;
      for(int i = 0; i < ArraySize(m_cdTypes); i++)
         if(m_cdTypes[i] == slot)
            return NtCooldownOk(m_cdAt[i], now, sec);
      return true;
     }

   bool CooldownTake(const AlertEvent &a, const long now)
     {
      int sec = NtCooldownSec(a.severity, a.type);
      if(sec <= 0)
         return true;
      bool account = (NtScopeOf(a.type) == SDB_NT_SCOPE_ACCOUNT);
      if(account && StateReady())
         return GvCooldownTake(a.type, now, sec);
      return MemCooldownTake((account ? "A:" : "I:") + a.type, now, sec);
     }

   bool QuotaTake(const long now)
     {
      double next = 0.0;
      if(!StateReady())
        {
         if(!NtQuotaTake(m_quotaMem, now, SDB_NT_QUOTA_PER_HOUR, next))
            return false;
         m_quotaMem = next;
         return true;
        }
      string key = m_state.Key(SDB_GV_NT_QUOTA);
      for(int r = 0; r < SDB_CAS_RETRY; r++)
        {
         if(!GlobalVariableCheck(key))
            m_state.Set(SDB_GV_NT_QUOTA, 0.0, false);
         double old = m_state.Get(SDB_GV_NT_QUOTA, 0.0);
         if(!NtQuotaTake(old, now, SDB_NT_QUOTA_PER_HOUR, next))
            return false;
         if(GlobalVariableSetOnCondition(key, next, old))
            return true;
        }
      LogThrottled(SDB_LOG_ERROR, "nt-cas-quota", SDB_LOG_THROTTLE_DEFAULT_SEC, "Notify", "compare-and-set kuota gagal berulang | gv=" + key);
      return false;
     }

   void NoteHeld(const long now)
     {
      long hour = NtQuotaHour(now);
      if(hour != m_heldHour)
        {
         m_heldHour = hour;
         m_held = 0;
        }
      m_held++;
     }

   //--- Antrean
   void RemoveAt(const int idx)
     {
      int n = ArraySize(m_queue);
      for(int i = idx; i < n - 1; i++)
         m_queue[i] = m_queue[i + 1];
      ArrayResize(m_queue, n - 1);
     }

   void Enqueue(const AlertEvent &a, const string text, const long now, const bool silent = false)
     {
      if(ArraySize(m_queue) >= SDB_NT_QUEUE_MAX)
        {
         int victim = NtOverflowVictim(m_queue);
         if(victim >= 0)
           {
            Report(m_queue[victim].msg.key, SDB_ALERT_STATUS_SKIPPED, m_queue[victim].attempts, 0, SDB_ALERT_STATUS_REASON_OVERFLOW);
            RemoveAt(victim);
            LogThrottled(SDB_LOG_WARN, "nt-overflow", SDB_LOG_THROTTLE_DEFAULT_SEC, "Notify", "antrean notifikasi penuh, pesan non-Critical tertua dibuang");
           }
        }
      int n = ArraySize(m_queue);
      ArrayResize(m_queue, n + 1, SDB_NT_QUEUE_MAX);
      m_queue[n].msg.key = a.key;
      m_queue[n].msg.type = a.type;
      m_queue[n].msg.text = text;
      m_queue[n].msg.silent = silent;
      m_queue[n].msg.severity = a.severity;
      m_queue[n].queuedAt = now;
      m_queue[n].attempts = 0;
      m_queue[n].notBefore = 0;
     }

   // Penilaian satu notifikasi (design §3.6): cooldown (cek), kuota non-Critical, cooldown (pakai), antre.
   // Cooldown baru dipakai setelah kuota lolos agar pesan yang ditahan kuota tidak menahan tipenya (SC-10).
   // bypass: pesan berjadwal dan start/stop, tanpa cooldown dan kuota (spec 09 Req 5.3, 7.3).
   void Admit(const AlertEvent &a, const string text, const bool bypass = false, const bool silent = false)
     {
      long now = Now();
      if(a.severity != SDB_SEV_CRITICAL && !bypass)
        {
         if(!CooldownFree(a, now))
           {
            Report(a.key, SDB_ALERT_STATUS_SKIPPED, 0, 0, SDB_ALERT_STATUS_REASON_COOLDOWN);
            return;
           }
         if(!QuotaTake(now))
           {
            NoteHeld(now);
            m_schedule.AddHeld(now);
            Report(a.key, SDB_ALERT_STATUS_SKIPPED, 0, 0, SDB_ALERT_STATUS_REASON_QUOTA);
            return;
           }
         if(!CooldownTake(a, now))   // instance lain menang di antara cek dan pakai
           {
            Report(a.key, SDB_ALERT_STATUS_SKIPPED, 0, 0, SDB_ALERT_STATUS_REASON_COOLDOWN);
            return;
           }
        }
      Enqueue(a, text, now, silent);
     }

   void DropStale(const long now)
     {
      for(int i = ArraySize(m_queue) - 1; i >= 0; i--)
         if(NtIsStale(m_queue[i].msg.severity, m_queue[i].queuedAt, now))
           {
            Report(m_queue[i].msg.key, SDB_ALERT_STATUS_SKIPPED, m_queue[i].attempts, 0, SDB_ALERT_STATUS_REASON_STALE);
            RemoveAt(i);
           }
     }

   string FailReason(const SdbSendResult &r) const
     {
      if(r.note == SDB_ALERT_STATUS_REASON_TELEGRAM_OFF)
         return SDB_ALERT_STATUS_REASON_TELEGRAM_OFF;
      return r.code == SDB_SEND_TEMP ? SDB_ALERT_STATUS_REASON_TRANSPORT_TEMP : SDB_ALERT_STATUS_REASON_TRANSPORT_PERMANENT;
     }

   // Satu percobaan kirim; true bila item keluar dari antrean.
   bool Deliver(const int idx, const long now)
     {
      SdbSendResult r = m_transport.Send(m_queue[idx].msg);
      if(r.disable)
         OnTransportDisabled(r.error);
      if(r.code != SDB_SEND_LIMITED)
         m_queue[idx].attempts++;
      int attempts = m_queue[idx].attempts;
      string key = m_queue[idx].msg.key;
      switch(NtAfterResult(r, attempts))
        {
         case SDB_NT_DONE_SENT:
            Report(key, SDB_ALERT_STATUS_SENT, attempts, now, r.note);
            RemoveAt(idx);
            return true;
         case SDB_NT_DONE_FAILED:
            LogThrottled(SDB_LOG_ERROR, "nt-failed-" + FailReason(r), SDB_LOG_THROTTLE_DEFAULT_SEC, "Notify",
                         "notifikasi gagal | key=" + key + " transport=" + m_transport.Name() + " error=" + r.error);
            if(m_queue[idx].msg.severity == SDB_SEV_CRITICAL)
               PushFor(key, m_queue[idx].msg.text, attempts, FailReason(r));   // spec 09 Req 3.1
            else
               Report(key, SDB_ALERT_STATUS_FAILED, attempts, 0, FailReason(r));
            RemoveAt(idx);
            return true;
         case SDB_NT_WAIT:
            m_waitUntil = now + MathMax(r.retryAfterSec, 1);
            LogInfo("Notify", "transport minta jeda " + IntegerToString(r.retryAfterSec) + " detik");
            return false;
         default:
            m_queue[idx].notBefore = now + SDB_TIMER_SEC;   // siklus berikutnya (Req 3.4)
            if(r.retryAfterSec > 0)
               m_waitUntil = now + r.retryAfterSec;      // gagal sementara: maks 1 kiriman per jeda (spec 09 Req 2.6)
            LogThrottled(SDB_LOG_WARN, "nt-temp", SDB_LOG_THROTTLE_DEFAULT_SEC, "Notify", "kirim gagal sementara, dicoba lagi | " + r.error);
            return false;
        }
     }

   //--- Push HP (spec 09 Req 3)
   void WarnPushSetup()
     {
      if(m_pushSetupWarned)
         return;
      m_pushSetupWarned = true;
      LogCritical("Notify", "push HP belum dikonfigurasi: aktifkan Tools > Options > Notifications dan isi MetaQuotes ID dari aplikasi MT5 di HP");
     }

   // Hasil push untuk baris alerts (key kosong = pemberitahuan tanpa baris). false = ditunda.
   bool PushResult(const string key, const int attempts, const int code)
     {
      if(code == SDB_PUSH_DEFERRED)
         return false;
      if(code == SDB_PUSH_NOT_SETUP)
         WarnPushSetup();
      if(key != "")
         Report(key, SDB_ALERT_STATUS_FAILED, attempts, 0,
                code == SDB_PUSH_OK ? SDB_ALERT_STATUS_REASON_PUSH_SENT : SDB_ALERT_STATUS_REASON_PUSH_FAILED);
      return true;
     }

   void QueuePush(const string key, const string text, const int attempts)
     {
      int n = ArraySize(m_pushTexts);
      if(n >= SDB_PUSH_QUEUE_MAX)
        {
         PushResult(key, attempts, SDB_PUSH_FAILED);
         return;
        }
      ArrayResize(m_pushTexts, n + 1);
      ArrayResize(m_pushKeys, n + 1);
      ArrayResize(m_pushAttempts, n + 1);
      m_pushTexts[n] = text;
      m_pushKeys[n] = key;
      m_pushAttempts[n] = attempts;
     }

   void PushFor(const string key, const string html, const int attempts, const string reasonWithoutPush)
     {
      if(m_push == NULL)
        {
         if(key != "")
            Report(key, SDB_ALERT_STATUS_FAILED, attempts, 0, reasonWithoutPush);
         return;
        }
      string text = NtPushText(NtPlainText(html), SDB_PUSH_MAX_LEN);
      if(ArraySize(m_pushTexts) > 0 || !PushResult(key, attempts, m_push.Send(text)))
         QueuePush(key, text, attempts);   // urutan push dijaga
     }

   void FlushPushes()
     {
      while(m_push != NULL && ArraySize(m_pushTexts) > 0)
        {
         if(!PushResult(m_pushKeys[0], m_pushAttempts[0], m_push.Send(m_pushTexts[0])))
            return;
         ArrayRemove(m_pushTexts, 0, 1);
         ArrayRemove(m_pushKeys, 0, 1);
         ArrayRemove(m_pushAttempts, 0, 1);
        }
     }

   // Error konfigurasi Telegram: sekali log CRITICAL dan sekali push pemberitahuan (spec 09 Req 2.3).
   void OnTransportDisabled(const string error)
     {
      if(m_telegramOff)
         return;
      m_telegramOff = true;
      LogCritical("Notify", "Telegram nonaktif sampai EA di-init ulang | " + error +
                  " | periksa daftar WebRequest (https://api.telegram.org), InpTelegramToken, InpTelegramChatID");
      PushFor("", "SDBot " + m_ctx.symbol + ": Telegram nonaktif (" + error + "). Alert Critical dikirim lewat push.", 0, "");
     }

   void RememberDirection(const long positionId, const string direction)
     {
      int n = ArraySize(m_posIds);
      ArrayResize(m_posIds, n + 1, 16);
      ArrayResize(m_posDirs, n + 1, 16);
      m_posIds[n] = positionId;
      m_posDirs[n] = direction;
     }

   // Arah dari pembukaan; bila EA baru start, dari deal pembuka di history; selain itu "-".
   string TakeDirection(const long positionId)
     {
      for(int i = 0; i < ArraySize(m_posIds); i++)
         if(m_posIds[i] == positionId)
           {
            string d = m_posDirs[i];
            int n = ArraySize(m_posIds);
            m_posIds[i] = m_posIds[n - 1];
            m_posDirs[i] = m_posDirs[n - 1];
            ArrayResize(m_posIds, n - 1);
            ArrayResize(m_posDirs, n - 1);
            return d;
           }
      if(HistorySelectByPosition(positionId) && HistoryDealsTotal() > 0)
        {
         ulong deal = HistoryDealGetTicket(0);
         if(deal > 0)
            return HistoryDealGetInteger(deal, DEAL_TYPE) == DEAL_TYPE_BUY ? SDB_DIRECTION_BUY : SDB_DIRECTION_SELL;
        }
      return "-";
     }

   AlertEvent OwnAlert(const string type, const string message, const long magic, const string symbol, const datetime time)
     {
      AlertEvent a;
      a.type = type;
      a.severity = SDB_SEV_INFO;
      a.message = message;
      a.symbol = symbol;
      a.magic = magic;
      a.time = time;
      m_seq++;
      a.key = m_keyPrefix + "-T" + IntegerToString(m_seq);
      return a;
     }

   // Pesan berjadwal, start, stop: tercatat di alerts, lewati cooldown dan kuota (spec 09 Req 5.3, 7.3).
   void EnqueueOwn(const string type, const string message, const string text, const bool silent)
     {
      AlertEvent a = OwnAlert(type, message, m_magic, m_ctx.symbol, (datetime)Now());
      if(m_store != NULL)
         m_store.OnAlert(a);
      Admit(a, text, true, silent);
     }

   void RunHeartbeat(const long now)
     {
      if(m_status == NULL || !m_schedule.ClaimHeartbeat(now, m_hbMinutes))
         return;
      SdbHeartbeat h;
      if(!m_status.HeartbeatData(h))
         return;
      h.instancesAlive = m_schedule.CountAlive(now);
      h.heldLastHour = m_schedule.HeldPreviousHour(now);
      EnqueueOwn(SDB_ALERT_TYPE_HEARTBEAT, StringFormat("balance %.2f dd %.2f%% %s", h.balance, h.ddPct, h.riskStatus),
                 NtFormatHeartbeat(m_ctx, h), true);
     }

   // Hari yang terlewat dilaporkan berurutan, sekali per hari per akun (spec 09 Req 6.1, 6.4).
   void RunReports(const long now)
     {
      long days[];
      double last = 0.0;
      int n = m_schedule.DueReportDays(now, days, last);
      for(int i = 0; i < n; i++)
        {
         SdbDealRow rows[];
         long open[];
         if(!SdbCollectDay(days[i], rows, open))
           {
            LogThrottled(SDB_LOG_WARN, "nt-report-history", SDB_LOG_THROTTLE_DEFAULT_SEC, "Notify", "history deal belum terbaca, laporan harian ditunda");
            return;
           }
         if(!m_schedule.ClaimReportDay(days[i], last))
            return;
         last = (double)days[i];
         SdbDayStats st;
         DayStats(rows, open, days[i], st);
         st.balanceNow = AccountInfoDouble(ACCOUNT_BALANCE);
         if(DayHasActivity(st))
            EnqueueOwn(SDB_ALERT_TYPE_DAILY_REPORT, StringFormat("%s net %.2f closed %d", TimeToString((datetime)days[i], TIME_DATE), st.net, st.closed),
                       NtFormatDailyReport(m_ctx, st), false);
        }
     }

public:
                     CNotifier(void) : m_store(NULL), m_transport(NULL), m_state(NULL), m_nowOverride(0), m_keyPrefix("0"), m_seq(0),
                     m_waitUntil(0), m_quotaMem(0.0), m_heldHour(0), m_held(0), m_push(NULL), m_status(NULL), m_hbMinutes(0),
                     m_magic(0), m_telegramOff(false), m_pushSetupWarned(false) {}

   void Init(ISdbEventSink *store, ISdbTransport *transport, const SdbNtContext &ctx)
     {
      m_store = store;
      m_transport = transport;
      m_ctx = ctx;
      m_state = NULL;
      ArrayFree(m_queue);
      ArrayFree(m_cdTypes);
      ArrayFree(m_cdAt);
      ArrayFree(m_posIds);
      ArrayFree(m_posDirs);
      m_waitUntil = 0;
      m_quotaMem = 0.0;
      m_held = 0;
      m_telegramOff = false;
      m_pushSetupWarned = false;
      ArrayFree(m_pushTexts);
      ArrayFree(m_pushKeys);
      ArrayFree(m_pushAttempts);
      m_schedule.Init(NULL, m_magic);
     }

   void SetContext(const SdbNtContext &ctx)  { m_ctx = ctx; }
   void SetState(CState *state)              { m_state = state; m_schedule.SetState(state); }
   void SetKeyPrefix(const string prefix)    { m_keyPrefix = prefix; m_seq = 0; }
   void SetNowOverride(const long now)       { m_nowOverride = now; }
   int  QueueSize() const                    { return ArraySize(m_queue); }
   // Pesan ditahan kuota di jam berjalan (untuk heartbeat spec 09).
   int  HeldInHour() const                   { return NtQuotaHour(Now()) == m_heldHour ? m_held : 0; }

   //--- Sink
   void OnAlert(const AlertEvent &a) { Admit(a, NtFormatAlert(m_ctx, a)); }

   void OnTradeOpened(const TradeRecord &t)
     {
      RememberDirection(t.positionId, t.direction);
      if(t.source == SDB_TRADE_SOURCE_RECONCILED)
         return;   // Req 1.4
      string msg = StringFormat("%s %s @ %s SL %s TP %s", t.direction, NtVolume(t.volumeInitial), NtPrice(t.priceOpen, m_ctx.digits),
                                NtPrice(t.slInitial, m_ctx.digits), NtPrice(t.tpInitial, m_ctx.digits));
      AlertEvent a = OwnAlert(SDB_ALERT_TYPE_TRADE_OPENED, msg, t.magic, t.symbol, t.openedAt);
      if(m_store != NULL)
         m_store.OnAlert(a);
      Admit(a, NtFormatOpened(m_ctx, t));
     }

   void OnClosure(const ClosureRecord &c)
     {
      string dir = TakeDirection(c.positionId);
      string msg = StringFormat("%s %s net %s R %s", c.reason, dir, NtMoney(c.netProfit, m_ctx.currency), NtR(c.rResult));
      AlertEvent a = OwnAlert(SDB_ALERT_TYPE_TRADE_CLOSED, msg, c.magic, c.symbol, c.closedAt);
      if(m_store != NULL)
         m_store.OnAlert(a);
      Admit(a, NtFormatClosed(m_ctx, c, dir));
     }

   void OnAccount(const AccountSnapshot &a)     { }
   void OnDeal(const DealRecord &d)             { }
   void OnPositionEvent(const PositionEvent &e) { }
   void OnBalanceOp(const BalanceOpRecord &b)   { }
   void OnAlertStatus(const AlertStatus &s)     { }
   bool FindInitialSl(const long login, const ulong positionId, double &sl) { sl = 0.0; return false; }

   //--- Siklus
   // Jadwal (pemimpin, heartbeat, laporan), push tertunda, buang pesan basi, lalu kirim paling banyak 2 (Req 3.3).
   void OnTimer()
     {
      if(m_transport == NULL)
         return;
      long now = Now();
      m_schedule.Tick(now);
      RunHeartbeat(now);
      RunReports(now);
      FlushPushes();
      DropStale(now);
      for(int sent = 0; sent < SDB_NT_MAX_PER_TIMER; sent++)
        {
         if(now < m_waitUntil)
            return;
         int idx = NtPickNext(m_queue, now);
         if(idx < 0)
            return;
         Deliver(idx, now);
        }
     }

   // Deinit: Critical lalu pesan stop dikirim dalam batas waktu (spec 08 Req 6.3, spec 09 Req 7.4); sisanya tetap PENDING.
   void Drain(const uint maxMs)
     {
      if(m_transport == NULL)
         return;
      uint start = GetTickCount();
      FlushPushes();
      for(int pass = 0; pass < 2; pass++)
        {
         int i = 0;
         while(i < ArraySize(m_queue) && GetTickCount() - start < maxMs)
           {
            bool match = (pass == 0) ? m_queue[i].msg.severity == SDB_SEV_CRITICAL : m_queue[i].msg.type == SDB_ALERT_TYPE_EA_STOP;
            if(!match)
              {
               i++;
               continue;
              }
            long now = Now();
            if(now < m_waitUntil || (!Deliver(i, now) && m_queue[i].notBefore == 0))
               return;   // dibatasi: tidak ada gunanya mencoba sisanya
           }
        }
      FlushPushes();
     }

   void SetPush(ISdbPush *push)                  { m_push = push; }
   void SetStatusSource(ISdbStatusSource *src)   { m_status = src; }
   void SetSchedule(const int heartbeatMinutes, const long magic)
     {
      m_hbMinutes = heartbeatMinutes;
      m_magic = magic;
      m_schedule.Init(m_state, magic);
     }
   bool IsLeader() const                         { return m_schedule.IsLeader(); }
   void ReleaseLeader()                          { m_schedule.Release(); }

   void SendStart(const SdbStartInfo &info)
     {
      EnqueueOwn(SDB_ALERT_TYPE_EA_START, "start magic " + IntegerToString(info.magic) + " " + info.validation,
                 NtFormatStart(m_ctx, info), true);
     }

   void SendStop(const string reasonText)
     {
      EnqueueOwn(SDB_ALERT_TYPE_EA_STOP, "stop " + reasonText, NtFormatStop(m_ctx, reasonText), true);
     }

   // Notifikasi dari sesi lalu (Req 6.2) atau uji: langsung antre dengan key asalnya.
   void Requeue(const AlertEvent &a) { Enqueue(a, NtFormatAlert(m_ctx, a), Now()); }
  };

#endif // SDB_NOTIFY_NOTIFIER_MQH
