//+------------------------------------------------------------------+
//| ExposureRules.mqh — eksposur mata uang dengan arah sebagai fungsi
//| murni (spec 15 Req 1–2; design §3.1; PC-21, PC-23). Satu posisi =
//| dua kaki: BUY = mata uang dasar long + kuotasi short, SELL
//| kebalikannya. Long dan short dihitung terpisah (bug bot Python:
//| arah SELL pernah diabaikan).
//+------------------------------------------------------------------+
#ifndef SDB_RISK_EXPOSURERULES_MQH
#define SDB_RISK_EXPOSURERULES_MQH

// Kaki satu posisi; mata uang kosong atau dasar = kuotasi -> 0 kaki (Req 1.4).
int LegsOf(const string base, const string quote, const bool isBuy, string &ccy[], int &dir[])
  {
   ArrayFree(ccy);
   ArrayFree(dir);
   if(base == "" || quote == "" || base == quote)
      return 0;
   ArrayResize(ccy, 2);
   ArrayResize(dir, 2);
   ccy[0] = base;
   dir[0] = isBuy ? 1 : -1;
   ccy[1] = quote;
   dir[1] = -dir[0];
   return 2;
  }

void AddLegs(const string base, const string quote, const bool isBuy, string &ccy[], int &dir[])
  {
   string c[];
   int d[];
   int n = LegsOf(base, quote, isBuy, c, d);
   for(int i = 0; i < n; i++)
     {
      int m = ArraySize(ccy);
      ArrayResize(ccy, m + 1);
      ArrayResize(dir, m + 1);
      ccy[m] = c[i];
      dir[m] = d[i];
     }
  }

int SameDirectionCount(const string &ccy[], const int &dir[], const string c, const int d)
  {
   int n = 0;
   for(int i = 0; i < MathMin(ArraySize(ccy), ArraySize(dir)); i++)
      if(ccy[i] == c && dir[i] == d)
         n++;
   return n;
  }

string DirText(const int d) { return d > 0 ? "long" : "short"; }

// Order baru lolos bila tidak ada kakinya yang sudah punya `limit` posisi searah; limit <= 0 = mati (Req 2.1, 2.3).
bool ExposureAllowed(const string &ccy[], const int &dir[], const string base, const string quote, const bool isBuy, const int limit,
                     string &detail)
  {
   detail = "";
   if(limit <= 0)
      return true;
   string c[];
   int d[];
   int n = LegsOf(base, quote, isBuy, c, d);
   for(int i = 0; i < n; i++)
     {
      int have = SameDirectionCount(ccy, dir, c[i], d[i]);
      if(have >= limit)
        {
         detail = StringFormat("%s %s %d/%d", c[i], DirText(d[i]), have, limit);
         return false;
        }
     }
   return true;
  }

#endif // SDB_RISK_EXPOSURERULES_MQH
