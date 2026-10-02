//+------------------------------------------------------------------+
//| NotifySchedule.mqh — CNotifySchedule: status bersama pesan berjadwal
//| di Global Variables akun (spec 09 Req 4–6; design §3.6, §4.5):
//| penanda hidup, lease pemimpin, jadwal heartbeat, hari laporan, dan
//| jumlah pesan yang ditahan kuota. Semua perubahan lintas instance
//| memakai compare-and-set; aturan murninya di Schedule.mqh.
//+------------------------------------------------------------------+
#ifndef SDB_NOTIFY_NOTIFYSCHEDULE_MQH
#define SDB_NOTIFY_NOTIFYSCHEDULE_MQH

#include <SDBot/Core/State.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Notify/Schedule.mqh>
#include <SDBot/Notify/NotifyRules.mqh>

class CNotifySchedule
  {
private:
   CState           *m_state;
   long              m_magic;
   bool              m_leader;
   long              m_lastRenew;

   bool Ready() const { return m_state != NULL && m_state.IsReady() && m_magic > 0; }
   int  MyIdx() const { return (int)(m_magic - SDB_MAGIC_HARNESS); }

   double GetOrCreate(const string name, const double initial)
     {
      if(!GlobalVariableCheck(m_state.Key(name)))
         m_state.Set(name, initial, false);
      return m_state.Get(name, initial);
     }

   bool Cas(const string name, const double newValue, const double expected)
     {
      return GlobalVariableSetOnCondition(m_state.Key(name), newValue, expected);
     }

   void RenewLease(const long now)
     {
      double cur = GetOrCreate(SDB_GV_NT_LEADER, 0.0);
      m_leader = LeaseCanTake(cur, MyIdx(), now, SDB_NT_LEASE_TTL_SEC) &&
                 Cas(SDB_GV_NT_LEADER, LeaseEncode(MyIdx(), now), cur);
     }

public:
                     CNotifySchedule(void) : m_state(NULL), m_magic(0), m_leader(false), m_lastRenew(0) {}

   void Init(CState *state, const long magic)
     {
      m_state = state;
      m_magic = magic;
      m_leader = false;
      m_lastRenew = 0;
     }
   void SetState(CState *state) { m_state = state; }
   bool IsLeader() const        { return m_leader; }

   // Tiap SDB_NT_LEASE_RENEW_SEC: tandai hidup dan coba/perbarui lease (Req 4.1, 4.4).
   void Tick(const long now)
     {
      if(!Ready() || (m_lastRenew > 0 && now - m_lastRenew < SDB_NT_LEASE_RENEW_SEC))
         return;
      m_lastRenew = now;
      m_state.Set(SDB_GV_NT_ALIVE_PREFIX + IntegerToString(m_magic), (double)now, false);
      RenewLease(now);
     }

   // Berhenti normal: lease dilepas agar instance lain memimpin di siklus berikutnya (Req 4.3).
   void Release()
     {
      if(!Ready() || !m_leader)
         return;
      double cur = m_state.Get(SDB_GV_NT_LEADER, 0.0);
      int idx;
      long at;
      LeaseDecode(cur, idx, at);
      if(idx == MyIdx())
         Cas(SDB_GV_NT_LEADER, 0.0, cur);
      m_leader = false;
     }

   // true = pemimpin ini yang mengirim heartbeat sekarang (sudah ditandai di GV akun).
   bool ClaimHeartbeat(const long now, const int minutes)
     {
      if(!Ready() || !m_leader || minutes <= 0)
         return false;
      if(!GlobalVariableCheck(m_state.Key(SDB_GV_NT_HB_AT)))
        {
         m_state.Set(SDB_GV_NT_HB_AT, (double)now, false);   // pemasangan pertama: tanpa heartbeat retroaktif
         return false;
        }
      double last = m_state.Get(SDB_GV_NT_HB_AT, (double)now);
      return HeartbeatDue((long)last, now, minutes) && Cas(SDB_GV_NT_HB_AT, (double)now, last);
     }

   // Hari yang belum dilaporkan (lama ke baru). GV baru = kemarin: hari pemasangan ikut dilaporkan besok,
   // hari sebelum pemasangan tidak (keputusan design §8.6; temuan SC-11).
   int DueReportDays(const long now, long &days[], double &last)
     {
      ArrayFree(days);
      if(!Ready() || !m_leader)
         return 0;
      long today = ServerDayStart(now);
      if(!GlobalVariableCheck(m_state.Key(SDB_GV_NT_REPORT_DAY)))
        {
         m_state.Set(SDB_GV_NT_REPORT_DAY, (double)(today - SDB_DAY_SEC), false);
         return 0;
        }
      last = m_state.Get(SDB_GV_NT_REPORT_DAY, (double)today);
      return ReportDays((long)last, today, days);
     }

   // Tandai hari sudah diproses; kalah compare-and-set = instance lain yang melaporkan.
   bool ClaimReportDay(const long day, const double expected)
     {
      return Ready() && Cas(SDB_GV_NT_REPORT_DAY, (double)day, expected);
     }

   int CountAlive(const long now)
     {
      if(!Ready())
         return 0;
      string prefix = m_state.Key(SDB_GV_NT_ALIVE_PREFIX);
      int alive = 0;
      for(int i = GlobalVariablesTotal() - 1; i >= 0; i--)
        {
         string name = GlobalVariableName(i);
         if(StringFind(name, prefix) == 0 && (long)GlobalVariableGet(name) >= now - SDB_NT_LEASE_TTL_SEC)
            alive++;
        }
      return alive;
     }

   // GV NT_HELD = jam x 1000 + jumlah ditahan kuota di jam itu (semua instance).
   void AddHeld(const long now)
     {
      if(!Ready())
         return;
      long hour = NtQuotaHour(now);
      for(int r = 0; r < SDB_CAS_RETRY; r++)
        {
         double old = GetOrCreate(SDB_GV_NT_HELD, 0.0);
         long stored = (long)MathRound(old);
         long count = (stored / SDB_NT_QUOTA_HOUR_FACTOR == hour) ? stored % SDB_NT_QUOTA_HOUR_FACTOR : 0;
         if(Cas(SDB_GV_NT_HELD, (double)(hour * SDB_NT_QUOTA_HOUR_FACTOR + count + 1), old))
            return;
        }
     }

   int HeldPreviousHour(const long now)
     {
      if(!Ready())
         return 0;
      long stored = (long)MathRound(m_state.Get(SDB_GV_NT_HELD, 0.0));
      return (stored / SDB_NT_QUOTA_HOUR_FACTOR == NtQuotaHour(now) - 1) ? (int)(stored % SDB_NT_QUOTA_HOUR_FACTOR) : 0;
     }
  };

#endif // SDB_NOTIFY_NOTIFYSCHEDULE_MQH
