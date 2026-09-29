//+------------------------------------------------------------------+
//| TestEnvCheck.mqh — memastikan fitur SQLite dan waktu yang dipakai
//| spec 03 benar-benar tersedia di MT5 (TC-ENV-01..08).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTENVCHECK_MQH
#define SDB_SUITES_TESTENVCHECK_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBotTests/TestDb.mqh>

#define SDB_ENVCHECK_DB "sdbot_envcheck.sqlite"

// "3.53.0" -> 3053000, agar versi bisa dibandingkan sebagai angka.
long EnvVersionNumber(const string version)
  {
   string parts[];
   if(StringSplit(version, '.', parts) < 2)
      return 0;
   long major = StringToInteger(parts[0]);
   long minor = StringToInteger(parts[1]);
   long patch = (ArraySize(parts) > 2) ? StringToInteger(parts[2]) : 0;
   return major * 1000000 + minor * 1000 + patch;
  }

void RunTestEnvCheck()
  {
   TfBeginSuite("EnvCheck");
   int db = TdbOpenFresh(SDB_ENVCHECK_DB);
   if(!AssertTrue("TC-ENV-00", "database uji bisa dibuat di folder Common", db != INVALID_HANDLE))
     {
      TfEndSuite();
      return;
     }

   // TC-ENV-01: UPSERT butuh SQLite >= 3.24.0
   string version = TdbScalarText(db, "SELECT sqlite_version()");
   TfInfo("sqlite_version=" + version);
   AssertTrue("TC-ENV-01", "SQLite >= 3.24.0 (versi " + version + ")", EnvVersionNumber(version) >= 3024000);

   // TC-ENV-02: CHECK menolak nilai di luar himpunan
   TdbExec(db, "CREATE TABLE env_check (x TEXT NOT NULL CHECK (x IN ('A','B')))");
   bool okValid = TdbExec(db, "INSERT INTO env_check (x) VALUES ('A')");
   bool okInvalid = TdbExec(db, "INSERT INTO env_check (x) VALUES ('C')");
   AssertTrue("TC-ENV-02", "CHECK menerima 'A' dan menolak 'C'", okValid && !okInvalid);

   // TC-ENV-03: ON CONFLICT DO NOTHING tidak membuat baris ganda
   TdbExec(db, "CREATE TABLE env_upsert (k INTEGER PRIMARY KEY, v TEXT NOT NULL)");
   TdbExec(db, "INSERT INTO env_upsert (k, v) VALUES (1, 'a')");
   bool okNothing = TdbExec(db, "INSERT INTO env_upsert (k, v) VALUES (1, 'b') ON CONFLICT DO NOTHING");
   AssertTrue("TC-ENV-03", "DO NOTHING: 1 baris, nilai tetap 'a'",
              okNothing && TdbScalarInt(db, "SELECT COUNT(*) FROM env_upsert") == 1 &&
              TdbScalarText(db, "SELECT v FROM env_upsert WHERE k = 1") == "a");

   // TC-ENV-04: ON CONFLICT DO UPDATE memperbarui nilai
   bool okUpdate = TdbExec(db, "INSERT INTO env_upsert (k, v) VALUES (1, 'c') ON CONFLICT(k) DO UPDATE SET v = excluded.v");
   AssertTrue("TC-ENV-04", "DO UPDATE: nilai menjadi 'c'",
              okUpdate && TdbScalarText(db, "SELECT v FROM env_upsert WHERE k = 1") == "c");

   // TC-ENV-05: mode WAL di file Common
   string mode = TdbScalarText(db, "PRAGMA journal_mode=WAL");
   AssertStrEq("TC-ENV-05", "PRAGMA journal_mode=WAL", mode, "wal");

   // TC-ENV-06: BEGIN IMMEDIATE lalu COMMIT menyimpan, lalu ROLLBACK membatalkan
   TdbExec(db, "CREATE TABLE env_tx (n INTEGER NOT NULL)");
   bool okCommit = TdbExec(db, "BEGIN IMMEDIATE") && TdbExec(db, "INSERT INTO env_tx (n) VALUES (1)") &&
                   TdbExec(db, "COMMIT");
   bool okRollback = TdbExec(db, "BEGIN IMMEDIATE") && TdbExec(db, "INSERT INTO env_tx (n) VALUES (2)") &&
                     TdbExec(db, "ROLLBACK");
   AssertTrue("TC-ENV-06", "COMMIT menyimpan 1 baris, ROLLBACK membatalkan baris kedua",
              okCommit && okRollback && TdbScalarInt(db, "SELECT COUNT(*) FROM env_tx") == 1);

   // TC-ENV-08: ID 64-bit (ticket MT5) tersimpan utuh lewat parameter bind
   TdbExec(db, "CREATE TABLE env_big (id INTEGER NOT NULL)");
   long big = (long)1 << 40;
   AssertTrue("TC-ENV-08", "bind 2^40 lalu baca kembali sama",
              TdbInsertBoundLong(db, "INSERT INTO env_big (id) VALUES (?1)", big) &&
              TdbScalarInt(db, "SELECT id FROM env_big") == big);

   TdbCloseAndDelete(db, SDB_ENVCHECK_DB);

   // TC-ENV-07: hubungan TimeGMT dan TimeTradeServer
   datetime gmt = TimeGMT();
   datetime server = TimeTradeServer();
   TfInfo("time_gmt=" + TimeToString(gmt, TIME_DATE | TIME_SECONDS) +
          " time_trade_server=" + TimeToString(server, TIME_DATE | TIME_SECONDS) +
          " selisih_detik=" + IntegerToString((long)(server - gmt)));
   if(MQLInfoInteger(MQL_TESTER))
      AssertTrue("TC-ENV-07", "di tester TimeGMT sama dengan TimeTradeServer", gmt == server);
   else
      AssertTrue("TC-ENV-07", "di terminal live selisih waktu server kelipatan 15 menit",
                 ((long)(server - gmt)) % 900 == 0);

   TfEndSuite();
  }

#endif // SDB_SUITES_TESTENVCHECK_MQH
