//+------------------------------------------------------------------+
//| SDBot.mq5 — EA Supply & Demand + konfluensi (PRD-EA).
//| Versi kerangka (spec 01): belum ada logika trading. Mulai spec 04,
//| file ini hanya meneruskan event ke CSdbApp.
//+------------------------------------------------------------------+
#property copyright "SDBot"
#property version   "1.00"
#property description "SDBot EA - kerangka v1.00 (spec 01). Tidak mengirim order apa pun."

int OnInit()
  {
   // Fungsi log SDBot baru ada di spec 02; format baris sudah mengikuti RULES.
   Print("[SDB][INFO][App][", _Symbol, "] SDBot kerangka v1.00 aktif, tidak ada logika trading");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   Print("[SDB][INFO][App][", _Symbol, "] SDBot kerangka berhenti | reason=", reason);
  }

void OnTick()
  {
  }
