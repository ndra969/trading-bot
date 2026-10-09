//+------------------------------------------------------------------+
//| StructureRules.mqh — analisis struktur sebagai fungsi murni di atas
//| array MqlRates urut waktu naik (indeks 0 tertua, terakhir = bar
//| tertutup terbaru): swing fractal berjeda, BOS dan arah struktur,
//| EMA, bias HTF, skor keselarasan tren (spec 10 Req 2–6; design §3.1).
//| Hanya bar tertutup yang masuk; hasil sebuah bar hanya bergantung
//| pada bar sampai bar itu (tanpa repaint).
//+------------------------------------------------------------------+
#ifndef SDB_ANALYSIS_STRUCTURERULES_MQH
#define SDB_ANALYSIS_STRUCTURERULES_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>

#define SDB_BIAS_OK        "OK"
#define SDB_BIAS_STRUCTURE "STRUCTURE"   // struktur HTF netral
#define SDB_BIAS_EMA       "EMA"         // arah EMA HTF netral
#define SDB_BIAS_CONFLICT  "CONFLICT"    // struktur dan EMA berlawanan
#define SDB_BIAS_DATA      "DATA"        // histori HTF kurang

// High lebih tinggi dari n bar kiri (ketat) dan tidak lebih rendah dari n bar kanan: pada high sama persis,
// hanya bar lebih awal yang menjadi swing (Req 2.2).
bool IsSwingHigh(const MqlRates &r[], const int i, const int n)
  {
   if(n < 1 || i - n < 0 || i + n >= ArraySize(r))
      return false;
   for(int k = 1; k <= n; k++)
      if(r[i - k].high >= r[i].high || r[i + k].high > r[i].high)
         return false;
   return true;
  }

bool IsSwingLow(const MqlRates &r[], const int i, const int n)
  {
   if(n < 1 || i - n < 0 || i + n >= ArraySize(r))
      return false;
   for(int k = 1; k <= n; k++)
      if(r[i - k].low <= r[i].low || r[i + k].low < r[i].low)
         return false;
   return true;
  }

void StPushSwing(SdbSwing &out[], const MqlRates &r[], const int i, const bool isHigh)
  {
   int m = ArraySize(out);
   ArrayResize(out, m + 1, 64);
   out[m].index = i;
   out[m].time = r[i].time;
   out[m].price = isHigh ? r[i].high : r[i].low;
   out[m].isHigh = isHigh;
  }

// Swing yang kanannya sudah lengkap (diakui setelah n bar kanan tutup), urut indeks naik (Req 2.1).
int FindSwings(const MqlRates &r[], const int n, SdbSwing &out[])
  {
   ArrayFree(out);
   int last = ArraySize(r) - 1;
   for(int i = n; i + n <= last; i++)
     {
      if(IsSwingHigh(r, i, n))
         StPushSwing(out, r, i, true);
      if(IsSwingLow(r, i, n))
         StPushSwing(out, r, i, false);
     }
   return ArraySize(out);
  }

// Swing yang aktif di bar b: swing terbaru jenis itu yang terkonfirmasi sebelum b (idx + n < b).
int StActiveSwing(const SdbSwing &sw[], const int n, const int b, const bool isHigh)
  {
   int found = -1;
   for(int k = 0; k < ArraySize(sw); k++)
     {
      if(sw[k].index + n >= b)
         break;
      if(sw[k].isHigh == isHigh)
         found = k;
     }
   return found;
  }

// BOS: close bar menembus swing aktif yang belum pernah ditembus; arah = BOS terakhir di jendela (Req 3.1–3.3).
// Riwayat tembusan dihitung dari bar pertama agar hasil tidak bergantung pada lebar jendela.
void StructureOf(const MqlRates &r[], const SdbSwing &sw[], const int n, const int lookback, SdbStructure &out)
  {
   ZeroMemory(out);
   out.dir = SDB_DIR_NONE;
   int last = ArraySize(r) - 1;
   int windowStart = MathMax(0, last - lookback + 1);
   int brokenHigh = -1, brokenLow = -1;   // swing (indeks sw[]) yang sudah ditembus
   for(int b = 0; b <= last; b++)
     {
      int hi = StActiveSwing(sw, n, b, true);
      int lo = StActiveSwing(sw, n, b, false);
      ENUM_SDB_DIR bos = SDB_DIR_NONE;
      double level = 0.0;
      if(hi >= 0 && hi != brokenHigh && r[b].close > sw[hi].price)
        {
         brokenHigh = hi;
         bos = SDB_DIR_BULL;
         level = sw[hi].price;
        }
      else if(lo >= 0 && lo != brokenLow && r[b].close < sw[lo].price)
        {
         brokenLow = lo;
         bos = SDB_DIR_BEAR;
         level = sw[lo].price;
        }
      if(bos != SDB_DIR_NONE && b >= windowStart)
        {
         out.dir = bos;
         out.bosLevel = level;
         out.bosTime = r[b].time;
        }
     }
   for(int k = 0; k < ArraySize(sw); k++)
     {
      if(sw[k].index + n > last)
         break;
      out.swings++;
      if(sw[k].isHigh)
        {
         out.lastHigh = sw[k].price;
         out.lastHighTime = sw[k].time;
        }
      else
        {
         out.lastLow = sw[k].price;
         out.lastLowTime = sw[k].time;
        }
     }
  }

// EMA close: benih SMA `period` bar pertama, alpha = 2 / (period + 1). Minimal 3 x periode bar agar
// konvergen dan deterministik terhadap jumlah bar yang disalin (Req 4.1, 4.3). Indeks < period-1 = 0.
bool EmaSeries(const MqlRates &r[], const int period, double &ema[])
  {
   int n = ArraySize(r);
   ArrayFree(ema);
   if(period < 1 || n < SDB_EMA_WARMUP_MULT * period)
      return false;
   ArrayResize(ema, n);
   ArrayInitialize(ema, 0.0);
   double sum = 0.0;
   for(int i = 0; i < period; i++)
      sum += r[i].close;
   ema[period - 1] = sum / period;
   double alpha = 2.0 / (period + 1.0);
   for(int i = period; i < n; i++)
      ema[i] = ema[i - 1] + alpha * (r[i].close - ema[i - 1]);
   return true;
  }

// Close di atas EMA dan EMA naik dibanding slopeBars bar sebelumnya = BULL; kebalikan = BEAR (Req 4.2).
ENUM_SDB_DIR EmaDirectionOf(const double close, const double &ema[], const int slopeBars)
  {
   int last = ArraySize(ema) - 1;
   if(last - slopeBars < 0)
      return SDB_DIR_NONE;
   double now = ema[last], before = ema[last - slopeBars];
   if(close > now && now > before)
      return SDB_DIR_BULL;
   if(close < now && now < before)
      return SDB_DIR_BEAR;
   return SDB_DIR_NONE;
  }

// Bias HTF per mode (spec 27 design §3.1). Struktur NONE selalu NONE.
ENUM_SDB_DIR BiasOf(const ENUM_SDB_DIR structureDir, const ENUM_SDB_DIR emaDir, const ENUM_SDB_BIAS_MODE mode)
  {
   if(structureDir == SDB_DIR_NONE)
      return SDB_DIR_NONE;
   if(mode == SDB_BIAS_STRUCTURE_ONLY)
      return structureDir;
   if(mode == SDB_BIAS_NOT_OPPOSED)
      return (emaDir == SDB_DIR_NONE || emaDir == structureDir) ? structureDir : SDB_DIR_NONE;
   return (structureDir == emaDir) ? structureDir : SDB_DIR_NONE;
  }

// Alasan bias untuk telemetri (spec 10 Req 5.4): OK tepat bila BiasOf memberi arah (spec 27 Req 1.6).
string BiasReasonOf(const SdbTfAnalysis &htf, const ENUM_SDB_BIAS_MODE mode)
  {
   if(!htf.ready)
      return SDB_BIAS_DATA;
   if(htf.st.dir == SDB_DIR_NONE)
      return SDB_BIAS_STRUCTURE;
   if(BiasOf(htf.st.dir, htf.emaDir, mode) != SDB_DIR_NONE)
      return SDB_BIAS_OK;
   return (htf.emaDir == SDB_DIR_NONE) ? SDB_BIAS_EMA : SDB_BIAS_CONFLICT;
  }

// Keselarasan tren di MTF (PRD 15 poin): struktur dan EMA searah = 15, salah satu = 7 (Req 6.1).
int TrendScore(const ENUM_SDB_DIR signalDir, const SdbTfAnalysis &mtf)
  {
   if(signalDir == SDB_DIR_NONE || !mtf.ready)
      return 0;
   int hits = (mtf.st.dir == signalDir ? 1 : 0) + (mtf.emaDir == signalDir ? 1 : 0);
   return hits == 2 ? 15 : (hits == 1 ? 7 : 0);
  }

int BarsNeeded(const int strength, const int lookback, const int emaPeriod, const int slopeBars)
  {
   return MathMax(lookback + 2 * strength + 1, SDB_EMA_WARMUP_MULT * emaPeriod + slopeBars + 1);
  }

// Analisis satu timeframe dari bar tertutup (Req 1.3, 7.1).
void AnalyzeTf(const MqlRates &r[], const SdbStructureParams &p, SdbTfAnalysis &out)
  {
   ZeroMemory(out);
   out.st.dir = SDB_DIR_NONE;
   out.emaDir = SDB_DIR_NONE;
   int n = ArraySize(r);
   if(n > 0)
      out.barTime = r[n - 1].time;
   double ema[];
   if(n < BarsNeeded(p.strength, p.lookback, p.emaPeriod, p.slopeBars) || !EmaSeries(r, p.emaPeriod, ema))
     {
      out.ready = false;
      out.reason = "data kurang";
      return;
     }
   SdbSwing sw[];
   FindSwings(r, p.strength, sw);
   StructureOf(r, sw, p.strength, p.lookback, out.st);
   out.ema = ema[n - 1];
   out.emaDir = EmaDirectionOf(r[n - 1].close, ema, p.slopeBars);
   out.ready = true;
   out.reason = "";
  }

#endif // SDB_ANALYSIS_STRUCTURERULES_MQH
