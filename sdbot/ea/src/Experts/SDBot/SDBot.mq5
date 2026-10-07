//+------------------------------------------------------------------+
//| SDBot.mq5 — EA Supply & Demand + konfluensi (PRD-EA).
//| v1.24 (perbaikan throttle log di tester; 1.23 RSI divergence bayangan; 1.22 breakout & retest; 1.21 trendline, CConfirmations; 1.20 Fibonacci bayangan; 1.19 skema v4; 1.18 perbaikan lot-fit; spec 16 filter berita, Fase 4 selesai di 1.17; Fase 3 selesai di 1.12): hanya meneruskan event ke CSdbApp (spec 04 Req 6.6),
//| yang memegang validasi input dan akun, state bersama, pencatatan
//| SQLite, CExecutor, risk management (spec 05), dan manajemen posisi
//| (BE, partial, trailing ATR, closure, rekonsiliasi), metrik OnTester, notifier
//| (Telegram, push HP, heartbeat, laporan harian), analisis struktur, bias HTF,
//| peta zona S&D, pola candle LTF, dan pipeline sinyal yang membuka posisi sendiri
//| (bias + zona + trigger PA, skor, SL/TP dari zona) lewat jalur risiko Fase 1.
//+------------------------------------------------------------------+
#property copyright "SDBot"
#property version   "1.24"
#property description "SDBot EA v1.24: entry S&D (bias HTF, zona H1, trigger PA M15, skor), risk management, manajemen posisi, pencatatan SQLite, notifikasi Telegram."

#define SDB_EA_VERSION "1.24"   // sama dengan #property version

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
