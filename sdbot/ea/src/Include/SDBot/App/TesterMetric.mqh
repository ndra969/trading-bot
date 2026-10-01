//+------------------------------------------------------------------+
//| TesterMetric.mqh — metrik optimasi OnTester (spec 07 Req 1, PRD:
//| expectancy per trade dalam R dibagi max drawdown). Fungsi murni.
//+------------------------------------------------------------------+
#ifndef SDB_APP_TESTERMETRIC_MQH
#define SDB_APP_TESTERMETRIC_MQH

// 0 bila trade dengan R < minTrades (pass dengan sedikit trade tidak boleh terpilih) atau DD <= 0.
double TesterMetric(const double totalR, const int trades, const double maxDdPct, const int minTrades)
  {
   if(trades < minTrades || trades <= 0 || maxDdPct <= 0.0)
      return 0.0;
   return (totalR / trades) / maxDdPct;
  }

#endif // SDB_APP_TESTERMETRIC_MQH
