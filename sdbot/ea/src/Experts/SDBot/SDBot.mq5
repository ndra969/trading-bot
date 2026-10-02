//+------------------------------------------------------------------+
//| SDBot.mq5 — EA Supply & Demand + konfluensi (PRD-EA).
//| v1.11 (spec 12 trigger PA): hanya meneruskan event ke CSdbApp (spec 04 Req 6.6),
//| yang memegang validasi input dan akun, state bersama, pencatatan
//| SQLite, CExecutor, risk management (spec 05), dan manajemen posisi
//| (BE, partial, trailing ATR, closure, rekonsiliasi), metrik OnTester, notifier
//| (Telegram, push HP, heartbeat, laporan harian), analisis struktur, bias HTF, dan
//| peta zona S&D, pola candle LTF (belum dipakai untuk entry). Belum ada logika entry:
//| EA ini tidak membuka posisi sebelum Fase 3 (spec 04 Req 6.7).
//+------------------------------------------------------------------+
#property copyright "SDBot"
#property version   "1.11"
#property description "SDBot EA v1.11: risk management, manajemen posisi, pencatatan SQLite, notifikasi Telegram, bias HTF, zona S&D, pola PA. Tidak membuka posisi apa pun."

#define SDB_EA_VERSION "1.11"   // sama dengan #property version

#include <SDBot/Core/Inputs.mqh>
#include <SDBot/App/SdbApp.mqh>

CSdbApp g_app;

int OnInit()
  {
   return g_app.OnInit(CurrentAppConfig(SDB_APP_LIVE, SDB_EA_VERSION));
  }

void OnTick()
  {
   g_app.OnTick();
  }

void OnTimer()
  {
   g_app.OnTimer();
  }

void OnTradeTransaction(const MqlTradeTransaction &t, const MqlTradeRequest &rq, const MqlTradeResult &rs)
  {
   g_app.OnTradeTransaction(t, rq, rs);
  }

double OnTester()
  {
   return g_app.OnTester();
  }

void OnDeinit(const int reason)
  {
   g_app.OnDeinit(reason);
  }
