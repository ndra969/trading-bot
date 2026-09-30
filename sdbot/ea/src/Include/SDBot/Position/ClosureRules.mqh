//+------------------------------------------------------------------+
//| ClosureRules.mqh — aturan closure murni (spec 06 design §4.2):
//| pemetaan enum deal MT5 ke teks DB, alasan tutup yang membedakan
//| SL / BE_STOP / TRAIL_STOP (pelajaran bot Python: kebocoran BE harus
//| terukur), R hasil, dan MFE/MAE dalam R dari bar M1.
//+------------------------------------------------------------------+
#ifndef SDB_POSITION_CLOSURERULES_MQH
#define SDB_POSITION_CLOSURERULES_MQH

#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/SchemaEnums.mqh>

string DealEntryText(const long dealEntry)
  {
   switch((int)dealEntry)
     {
      case DEAL_ENTRY_IN:     return SDB_DEAL_ENTRY_IN;
      case DEAL_ENTRY_OUT:    return SDB_DEAL_ENTRY_OUT;
      case DEAL_ENTRY_INOUT:  return SDB_DEAL_ENTRY_INOUT;
      case DEAL_ENTRY_OUT_BY: return SDB_DEAL_ENTRY_OUT_BY;
      default:                return "";
     }
  }

// "" = bukan deal trading (saldo, kredit, komisi, ...): diabaikan tracker (Req 6.7).
string DealTypeText(const long dealType)
  {
   if(dealType == DEAL_TYPE_BUY)
      return SDB_DEAL_TYPE_BUY;
   if(dealType == DEAL_TYPE_SELL)
      return SDB_DEAL_TYPE_SELL;
   return "";
  }

string DealReasonText(const long dealReason)
  {
   switch((int)dealReason)
     {
      case DEAL_REASON_CLIENT:   return SDB_DEAL_REASON_CLIENT;
      case DEAL_REASON_MOBILE:   return SDB_DEAL_REASON_MOBILE;
      case DEAL_REASON_WEB:      return SDB_DEAL_REASON_WEB;
      case DEAL_REASON_EXPERT:   return SDB_DEAL_REASON_EXPERT;
      case DEAL_REASON_SL:       return SDB_DEAL_REASON_SL;
      case DEAL_REASON_TP:       return SDB_DEAL_REASON_TP;
      case DEAL_REASON_SO:       return SDB_DEAL_REASON_SO;
      case DEAL_REASON_ROLLOVER: return SDB_DEAL_REASON_ROLLOVER;
      case DEAL_REASON_VMARGIN:  return SDB_DEAL_REASON_VMARGIN;
      case DEAL_REASON_SPLIT:    return SDB_DEAL_REASON_SPLIT;
      default:                   return SDB_DEAL_REASON_OTHER;
     }
  }

// Req 6.3. Untuk SL: level = harga pemicu SL; beSl = titik BE posisi (harga buka bila BE belum pernah dipasang).
// Lebih baik dari titik BE + toleransi -> TRAIL_STOP; di antara harga buka dan itu -> BE_STOP; sisi rugi -> SL.
string MapCloseReason(const long dealReason, const bool isBuy, const double entry, const double levelPrice, const double beSl,
                      const int tolerancePts, const double point, const bool closedBySdbot)
  {
   switch((int)dealReason)
     {
      case DEAL_REASON_TP:
         return SDB_CLOSE_REASON_TP;
      case DEAL_REASON_SL:
        {
         double be = (beSl > 0.0) ? beSl : entry;
         double tol = tolerancePts * point;
         if(isBuy ? levelPrice > be + tol : levelPrice < be - tol)
            return SDB_CLOSE_REASON_TRAIL_STOP;
         if(isBuy ? levelPrice >= entry - point / 2 : levelPrice <= entry + point / 2)
            return SDB_CLOSE_REASON_BE_STOP;
         return SDB_CLOSE_REASON_SL;
        }
      case DEAL_REASON_CLIENT:
      case DEAL_REASON_MOBILE:
      case DEAL_REASON_WEB:
         return SDB_CLOSE_REASON_MANUAL;
      case DEAL_REASON_SO:
         return SDB_CLOSE_REASON_STOP_OUT;
      case DEAL_REASON_EXPERT:
         return closedBySdbot ? SDB_CLOSE_REASON_EA_CLOSE : SDB_CLOSE_REASON_OTHER;
      case DEAL_REASON_ROLLOVER:
         return SDB_CLOSE_REASON_ROLLOVER;
      default:
         return SDB_CLOSE_REASON_OTHER;
     }
  }

// Req 6.4: NULL bila risiko awal tidak diketahui atau 0.
double ResultInR(const double netProfit, const double riskMoney)
  {
   if(riskMoney == SDB_NULL_DOUBLE || riskMoney <= 0.0)
      return SDB_NULL_DOUBLE;
   return netProfit / riskMoney;
  }

// Req 6.5: ekstrem harga selama posisi terbuka, dalam R dan tidak negatif. Tanpa bar -> NULL.
void MfeMaeInR(const bool isBuy, const double entry, const double rDist, const double &highs[], const double &lows[],
               double &mfeR, double &maeR)
  {
   mfeR = SDB_NULL_DOUBLE;
   maeR = SDB_NULL_DOUBLE;
   int n = MathMin(ArraySize(highs), ArraySize(lows));
   if(n == 0 || rDist <= 0.0)
      return;
   double hi = highs[ArrayMaximum(highs, 0, n)];
   double lo = lows[ArrayMinimum(lows, 0, n)];
   mfeR = MathMax(0.0, (isBuy ? hi - entry : entry - lo) / rDist);
   maeR = MathMax(0.0, (isBuy ? entry - lo : hi - entry) / rDist);
  }

#endif // SDB_POSITION_CLOSURERULES_MQH
