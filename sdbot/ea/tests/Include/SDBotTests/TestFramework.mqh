//+------------------------------------------------------------------+
//| TestFramework.mqh — framework unit test SDBot: assert dengan ID test
//| case, hitungan PASS/FAIL per suite dan per run, dan file hasil di
//| Common\Files\sdbot_test_<runId>.txt yang dibaca run-ea-tests.ps1.
//|
//| Format baris (juga dicetak ke tab Experts):
//|   RUN <id> START | SUITE <nama> | PASS <tc> <desc>
//|   FAIL <tc> <desc> | expected=<x> actual=<y> | INFO <teks>
//|   SUITE_END <nama> pass=<n> fail=<m> | RUN <id> END pass=<N> fail=<M>
//+------------------------------------------------------------------+
#ifndef SDB_SDBOTTESTS_TESTFRAMEWORK_MQH
#define SDB_SDBOTTESTS_TESTFRAMEWORK_MQH

// State framework ada di kode uji saja; aturan "tanpa variabel global" RULES berlaku
// untuk modul EA, bukan untuk harness uji.
string g_tfRunId      = "";
string g_tfSuite      = "";
int    g_tfFile       = INVALID_HANDLE;
int    g_tfPass       = 0;
int    g_tfFail       = 0;
int    g_tfSuitePass  = 0;
int    g_tfSuiteFail  = 0;
bool   g_tfMuted      = false;

// Setiap baris langsung di-flush: bila EA uji berhenti di tengah, runner melihat
// file tanpa baris END dan menganggap run gagal.
void TfWriteLine(const string line)
  {
   Print(line);
   if(g_tfFile != INVALID_HANDLE)
     {
      FileWrite(g_tfFile, line);
      FileFlush(g_tfFile);
     }
  }

string TfNum(const double v)
  {
   return StringFormat("%.10g", v);
  }

void TfRecord(const bool ok, const string id, const string desc, const string detail)
  {
   if(ok)
     {
      g_tfPass++;
      g_tfSuitePass++;
     }
   else
     {
      g_tfFail++;
      g_tfSuiteFail++;
     }
   if(g_tfMuted)
      return;
   if(ok)
      TfWriteLine("PASS " + id + " " + desc);
   else
      TfWriteLine("FAIL " + id + " " + desc + " | " + detail);
  }

void TfBeginRun(const string runId)
  {
   g_tfRunId = runId;
   g_tfPass = 0;
   g_tfFail = 0;
   g_tfMuted = false;
   string name = "sdbot_test_" + runId + ".txt";
   g_tfFile = FileOpen(name, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(g_tfFile == INVALID_HANDLE)
      Print("[SDB][ERROR][Tests] file hasil tidak bisa dibuka | file=", name, " err=", GetLastError());
   TfWriteLine("RUN " + runId + " START");
  }

int TfEndRun()
  {
   TfWriteLine("RUN " + g_tfRunId + " END pass=" + IntegerToString(g_tfPass) +
               " fail=" + IntegerToString(g_tfFail));
   if(g_tfFile != INVALID_HANDLE)
     {
      FileClose(g_tfFile);
      g_tfFile = INVALID_HANDLE;
     }
   return g_tfFail;
  }

void TfBeginSuite(const string suite)
  {
   g_tfSuite = suite;
   g_tfSuitePass = 0;
   g_tfSuiteFail = 0;
   TfWriteLine("SUITE " + suite);
  }

void TfEndSuite()
  {
   TfWriteLine("SUITE_END " + g_tfSuite + " pass=" + IntegerToString(g_tfSuitePass) +
               " fail=" + IntegerToString(g_tfSuiteFail));
  }

int  TfPassCount() { return g_tfPass; }
int  TfFailCount() { return g_tfFail; }

// Dipakai self-test untuk mengembalikan hitungan setelah assert yang sengaja gagal.
void TfSetCounts(const int pass, const int fail)
  {
   g_tfSuitePass += pass - g_tfPass;
   g_tfSuiteFail += fail - g_tfFail;
   g_tfPass = pass;
   g_tfFail = fail;
  }

void TfMute(const bool mute) { g_tfMuted = mute; }

void TfInfo(const string text)
  {
   if(!g_tfMuted)
      TfWriteLine("INFO " + text);
  }

bool AssertEq(const string id, const string desc, const double actual, const double expected,
              const double tol = 1e-9)
  {
   bool ok = MathAbs(actual - expected) <= tol;
   TfRecord(ok, id, desc, "expected=" + TfNum(expected) + " actual=" + TfNum(actual));
   return ok;
  }

bool AssertIntEq(const string id, const string desc, const long actual, const long expected)
  {
   bool ok = (actual == expected);
   TfRecord(ok, id, desc, "expected=" + IntegerToString(expected) + " actual=" + IntegerToString(actual));
   return ok;
  }

bool AssertTrue(const string id, const string desc, const bool cond)
  {
   TfRecord(cond, id, desc, "expected=true actual=false");
   return cond;
  }

bool AssertStrEq(const string id, const string desc, const string actual, const string expected)
  {
   bool ok = (actual == expected);
   TfRecord(ok, id, desc, "expected=\"" + expected + "\" actual=\"" + actual + "\"");
   return ok;
  }

#endif // SDB_SDBOTTESTS_TESTFRAMEWORK_MQH
