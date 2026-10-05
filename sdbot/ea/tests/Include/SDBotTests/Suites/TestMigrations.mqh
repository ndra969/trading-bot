//+------------------------------------------------------------------+
//| TestMigrations.mqh — CSdbMigrationRunner terhadap file SQLite nyata
//| di folder Common: DB kosong, buka ulang, DB lebih baru, migrasi gagal
//| (sumber palsu), checksum berubah (spec 03 task 6, TC-DB-01..05).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTMIGRATIONS_MQH
#define SDB_SUITES_TESTMIGRATIONS_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/TestDb.mqh>
#include <SDBotTests/FakeSink.mqh>
#include <SDBot/Storage/MigrationRunner.mqh>
#include <SDBot/Storage/Migrations.mqh>

#define TM_FILE     "sdbot_unittest_migrations.sqlite"
#define TM_BY       "SDBot test login=0 magic=2026091900"
#define TM_NOW      1790000000

// Migrasi asli v1, lalu v2 yang pernyataan keduanya gagal. failFirst = v1 sendiri yang gagal.
class CFailingMigrations : public ISdbMigrationSource
  {
private:
   CSdbDataMigrations m_real;
   bool               m_failFirst;

public:
                     CFailingMigrations(const bool failFirst) : m_failFirst(failFirst) {}
   int    Count()              { return m_failFirst ? 1 : 2; }
   int    Version(const int i) { return i + 1; }
   string Name(const int i)    { return (i == 0 && !m_failFirst) ? m_real.Name(0) : "broken"; }
   string Checksum(const int i){ return (i == 0 && !m_failFirst) ? m_real.Checksum(0) : "00"; }
   int    Statements(const int i, string &out[])
     {
      if(i == 0 && !m_failFirst)
         return m_real.Statements(0, out);
      ArrayResize(out, 2);
      out[0] = "CREATE TABLE t_partial (x INTEGER)";
      out[1] = "INSERT INTO no_such_table VALUES (1)";
      return 2;
     }
  };

long TmTableExists(const int db, const string name)
  {
   return TdbScalarInt(db, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='" + name + "'");
  }

bool TmCapturedContains(const string a, const string b)
  {
   for(int i = 0; i < SdbLogCapturedCount(); i++)
      if(StringFind(SdbLogCaptured(i), a) >= 0 && StringFind(SdbLogCaptured(i), b) >= 0)
         return true;
   return false;
  }

void RunTestMigrations()
  {
   TfBeginSuite("Migrations");
   SdbLogCaptureStart();
   CSdbDataMigrations real;
   AlertEvent alert;

   // TC-DB-01: DB kosong -> semua migrasi diterapkan dan tercatat
   int db = TdbOpenFresh(TM_FILE);
   CFakeSink fake;
   CSdbMigrationRunner runner;
   runner.Init(GetPointer(fake), _Symbol, SDB_MAGIC_HARNESS);
   ENUM_SDB_MIGRATE_RESULT r1 = runner.Run(db, GetPointer(real), TM_BY, TM_NOW);
   AssertIntEq("TC-DB-01a", "DB kosong: hasil OK", r1, SDB_MIGRATE_OK);
   AssertIntEq("TC-DB-01b", "versi DB = SDB_SCHEMA_LATEST", runner.DbVersion(db), SDB_SCHEMA_LATEST);
   AssertIntEq("TC-DB-01c", "schema_migrations berisi semua versi",
               TdbScalarInt(db, "SELECT COUNT(*) FROM schema_migrations"), SDB_SCHEMA_LATEST);
   AssertTrue("TC-DB-01e", "skema v4 (spec 17): signal_scores.active ada, default 1",
              SDB_SCHEMA_LATEST == 4 && TdbScalarInt(db, "SELECT COUNT(*) FROM pragma_table_info('signal_scores') WHERE name='active' AND dflt_value='1'") == 1);
   AssertTrue("TC-DB-01d", "tabel skema v1 dibuat (trades, closures, view v_trade_results)",
              TmTableExists(db, "trades") == 1 && TmTableExists(db, "closures") == 1 &&
              TdbScalarInt(db, "SELECT COUNT(*) FROM sqlite_master WHERE type='view' AND name='v_trade_results'") == 1);
   AssertTrue("TC-DB-01e", "baris migrasi mencatat checksum, waktu, dan applied_by",
              TdbScalarText(db, "SELECT checksum FROM schema_migrations WHERE version=1") == real.Checksum(0) &&
              TdbScalarInt(db, "SELECT applied_at FROM schema_migrations WHERE version=1") == TM_NOW &&
              TdbScalarText(db, "SELECT applied_by FROM schema_migrations WHERE version=1") == TM_BY);
   AssertIntEq("TC-DB-01f", "tanpa alert", fake.CountAlert(), 0);

   // TC-DB-02: dijalankan lagi -> tidak ada baris ganda, tidak ada error
   ENUM_SDB_MIGRATE_RESULT r2 = runner.Run(db, GetPointer(real), TM_BY, TM_NOW + 60);
   AssertTrue("TC-DB-02", "run kedua: OK, satu baris per versi, applied_at tidak berubah",
              r2 == SDB_MIGRATE_OK && TdbScalarInt(db, "SELECT COUNT(*) FROM schema_migrations") == SDB_SCHEMA_LATEST &&
              TdbScalarInt(db, "SELECT applied_at FROM schema_migrations WHERE version=1") == TM_NOW);

   // TC-DB-05: checksum tercatat diubah -> WARN dengan versinya, tetap OK
   TdbExec(db, "UPDATE schema_migrations SET checksum='edited' WHERE version=1");
   ENUM_SDB_MIGRATE_RESULT r5 = runner.Run(db, GetPointer(real), TM_BY, TM_NOW);
   AssertTrue("TC-DB-05", "checksum beda: OK, satu selisih, log WARN menyebut v1",
              r5 == SDB_MIGRATE_OK && runner.ChecksumMismatches() == 1 && TmCapturedContains("WARN", "v1"));

   // TC-DB-03: versi DB lebih baru dari yang dikenal EA -> tidak boleh menulis, alert High
   TdbExec(db, "INSERT INTO schema_migrations VALUES (999, 'future', 'x', 0, 'future EA')");
   fake.Reset();
   ENUM_SDB_MIGRATE_RESULT r3 = runner.Run(db, GetPointer(real), TM_BY, TM_NOW);
   bool hasAlert = fake.LastAlert(alert);
   AssertIntEq("TC-DB-03a", "DB versi 999: hasil NEWER_DB", r3, SDB_MIGRATE_NEWER_DB);
   AssertTrue("TC-DB-03b", "alert High DB_NEWER_SCHEMA menyebut kedua versi",
              hasAlert && alert.type == SDB_ALERT_TYPE_DB_NEWER_SCHEMA && alert.severity == SDB_SEV_HIGH &&
              StringFind(alert.message, "999") >= 0 && StringFind(alert.message, IntegerToString(SDB_SCHEMA_LATEST)) >= 0);
   TdbCloseAndDelete(db, TM_FILE);

   // TC-DB-04: migrasi v2 gagal di pernyataan kedua -> rollback, versi tetap 1, alert High
   db = TdbOpenFresh(TM_FILE);
   fake.Reset();
   CFailingMigrations bad(false);
   ENUM_SDB_MIGRATE_RESULT r4 = runner.Run(db, GetPointer(bad), TM_BY, TM_NOW);
   hasAlert = fake.LastAlert(alert);
   AssertIntEq("TC-DB-04a", "v2 gagal: hasil FAILED", r4, SDB_MIGRATE_FAILED);
   AssertIntEq("TC-DB-04b", "versi DB tetap 1", runner.DbVersion(db), 1);
   AssertIntEq("TC-DB-04c", "pernyataan pertama v2 ikut di-rollback", TmTableExists(db, "t_partial"), 0);
   AssertTrue("TC-DB-04d", "alert High MIGRATION_FAILED menyebut v2",
              hasAlert && alert.type == SDB_ALERT_TYPE_MIGRATION_FAILED && alert.severity == SDB_SEV_HIGH &&
              StringFind(alert.message, "v2") >= 0 && runner.LastError() != "");
   bool txFree = DatabaseExecute(db, "BEGIN IMMEDIATE");
   if(txFree)
      DatabaseExecute(db, "ROLLBACK");
   AssertTrue("TC-DB-04e", "tidak ada transaksi yang tertinggal terbuka", txFree);
   TdbCloseAndDelete(db, TM_FILE);

   // TC-DB-04f: v1 gagal di DB kosong -> versi 0, schema_migrations kosong
   db = TdbOpenFresh(TM_FILE);
   CFailingMigrations badFirst(true);
   ENUM_SDB_MIGRATE_RESULT r4f = runner.Run(db, GetPointer(badFirst), TM_BY, TM_NOW);
   AssertTrue("TC-DB-04f", "v1 gagal: FAILED, versi 0, tanpa tabel parsial",
              r4f == SDB_MIGRATE_FAILED && runner.DbVersion(db) == 0 && TmTableExists(db, "t_partial") == 0);
   TdbCloseAndDelete(db, TM_FILE);

   // Sink NULL: alert dibuang tanpa crash
   db = TdbOpenFresh(TM_FILE);
   CSdbMigrationRunner noSink;
   noSink.Init(NULL, _Symbol, SDB_MAGIC_HARNESS);
   AssertIntEq("TC-DB-04g", "sink NULL: migrasi gagal tetap FAILED tanpa crash",
               noSink.Run(db, GetPointer(badFirst), TM_BY, TM_NOW), SDB_MIGRATE_FAILED);
   TdbCloseAndDelete(db, TM_FILE);

   SdbLogCaptureStop();
   TfEndSuite();
  }

#endif // SDB_SUITES_TESTMIGRATIONS_MQH
