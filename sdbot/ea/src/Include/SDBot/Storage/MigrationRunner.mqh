//+------------------------------------------------------------------+
//| MigrationRunner.mqh — menerapkan migrasi skema yang dibawa EA ke DB
//| yang sudah terbuka (spec 03 Req 4, design §4.2 langkah 4–7). Hanya
//| maju; tiap migrasi satu transaksi BEGIN IMMEDIATE dan versi dibaca
//| ulang di dalamnya agar instance lain tidak menerapkannya dua kali.
//+------------------------------------------------------------------+
#ifndef SDB_STORAGE_MIGRATIONRUNNER_MQH
#define SDB_STORAGE_MIGRATIONRUNNER_MQH

#include <SDBot/Core/EventSink.mqh>
#include <SDBot/Core/Utils.mqh>
#include <SDBot/Core/SchemaEnums.mqh>
#include <SDBot/Storage/MigrationSource.mqh>

enum ENUM_SDB_MIGRATE_RESULT
  {
   SDB_MIGRATE_OK = 0,
   SDB_MIGRATE_NEWER_DB = 1,   // DB dibuat EA yang lebih baru: jangan menulis (4.5)
   SDB_MIGRATE_FAILED = 2      // migrasi atau akses DB gagal: DB di versi sebelumnya (4.4)
  };

class CSdbMigrationRunner
  {
private:
   ISdbEventSink    *m_sink;
   string            m_symbol;
   long              m_magic;
   int               m_mismatch;
   string            m_error;

   void SendAlert(const string type, const string message)
     {
      if(m_sink == NULL)
         return;
      AlertEvent a;
      a.type = type;
      a.severity = SDB_SEV_HIGH;
      a.message = message;
      a.symbol = m_symbol;
      a.magic = m_magic;
      a.time = TimeCurrent();
      m_sink.OnAlert(a);
     }

   ENUM_SDB_MIGRATE_RESULT Fail(const int db, const bool inTx, const string what)
     {
      m_error = what;
      if(inTx)
         DatabaseExecute(db, "ROLLBACK");
      LogError("Storage", "migrasi gagal | " + what);
      SendAlert(SDB_ALERT_TYPE_MIGRATION_FAILED, "Migrasi database gagal, EA lanjut trading tanpa menulis DB: " + what);
      return SDB_MIGRATE_FAILED;
     }

   bool Exec(const int db, const string sql, string &err)
     {
      ResetLastError();
      if(DatabaseExecute(db, sql))
         return true;
      err = ErrText(GetLastError());
      return false;
     }

   bool Record(const int db, const int version, const string name, const string checksum,
               const string appliedBy, const long nowUtc, string &err)
     {
      int stmt = DatabasePrepare(db, "INSERT INTO schema_migrations (version, name, checksum, applied_at, applied_by) "
                                     "VALUES (?1, ?2, ?3, ?4, ?5)");
      if(stmt == INVALID_HANDLE)
        {
         err = ErrText(GetLastError());
         return false;
        }
      bool ok = DatabaseBind(stmt, 0, (long)version) && DatabaseBind(stmt, 1, name) &&
                DatabaseBind(stmt, 2, checksum) && DatabaseBind(stmt, 3, nowUtc) && DatabaseBind(stmt, 4, appliedBy);
      if(ok)
        {
         ResetLastError();
         DatabaseRead(stmt);   // statement tanpa baris hasil: Read menjalankannya
         int code = GetLastError();
         ok = (code == 0 || code == ERR_DATABASE_NO_MORE_DATA);
         if(!ok)
            err = ErrText(code);
        }
      else
         err = ErrText(GetLastError());
      DatabaseFinalize(stmt);
      return ok;
     }

   // Checksum yang tercatat berbeda dengan yang dibawa EA: hanya WARN, EA tetap jalan (4.6).
   void CompareChecksums(const int db, ISdbMigrationSource *src)
     {
      m_mismatch = 0;
      int stmt = DatabasePrepare(db, "SELECT version, checksum FROM schema_migrations ORDER BY version");
      if(stmt == INVALID_HANDLE)
         return;
      while(DatabaseRead(stmt))
        {
         long version;
         string recorded;
         DatabaseColumnLong(stmt, 0, version);
         DatabaseColumnText(stmt, 1, recorded);
         for(int i = 0; i < src.Count(); i++)
           {
            if(src.Version(i) != version)
               continue;
            if(src.Checksum(i) != recorded)
              {
               m_mismatch++;
               LogWarn("Storage", StringFormat("checksum migrasi v%d di DB berbeda dengan yang dibawa EA | db=%s ea=%s",
                                               version, recorded, src.Checksum(i)));
              }
            break;
           }
        }
      DatabaseFinalize(stmt);
     }

public:
                     CSdbMigrationRunner(void) : m_sink(NULL), m_magic(0), m_mismatch(0) {}

   // sink NULL = alert dibuang (misalnya saat optimasi).
   void Init(ISdbEventSink *sink, const string symbol, const long magic)
     {
      m_sink = sink;
      m_symbol = symbol;
      m_magic = magic;
     }

   // Versi tertinggi yang tercatat; 0 = belum ada migrasi; -1 = tabel belum ada atau error.
   int DbVersion(const int db)
     {
      int stmt = DatabasePrepare(db, "SELECT COALESCE(MAX(version), 0) FROM schema_migrations");
      if(stmt == INVALID_HANDLE)
         return -1;
      long v = -1;
      if(DatabaseRead(stmt))
         DatabaseColumnLong(stmt, 0, v);
      DatabaseFinalize(stmt);
      return (int)v;
     }

   ENUM_SDB_MIGRATE_RESULT Run(const int db, ISdbMigrationSource *src, const string appliedBy, const long nowUtc)
     {
      m_error = "";
      m_mismatch = 0;
      string err = "";
      if(!Exec(db, "CREATE TABLE IF NOT EXISTS schema_migrations (\n"
                   "  version     INTEGER PRIMARY KEY,\n"
                   "  name        TEXT    NOT NULL,\n"
                   "  checksum    TEXT    NOT NULL,\n"
                   "  applied_at  INTEGER NOT NULL,\n"
                   "  applied_by  TEXT    NOT NULL\n"
                   ")", err))
         return Fail(db, false, "buat schema_migrations " + err);

      int count = src.Count();
      int latest = (count > 0) ? src.Version(count - 1) : 0;
      int current = DbVersion(db);
      if(current < 0)
         return Fail(db, false, "baca versi DB " + ErrText(GetLastError()));
      if(current > latest)
        {
         m_error = StringFormat("versi DB %d lebih baru dari versi skema EA %d", current, latest);
         LogError("Storage", m_error + ", DB tidak ditulis");
         SendAlert(SDB_ALERT_TYPE_DB_NEWER_SCHEMA,
                   StringFormat("Database dibuat EA yang lebih baru (versi DB %d, versi EA %d). EA lanjut trading tanpa menulis DB.",
                                current, latest));
         return SDB_MIGRATE_NEWER_DB;
        }

      for(int i = 0; i < count; i++)
        {
         int version = src.Version(i);
         if(version <= current)
            continue;
         if(!Exec(db, "BEGIN IMMEDIATE", err))
            return Fail(db, false, StringFormat("v%d: BEGIN IMMEDIATE %s", version, err));
         int reread = DbVersion(db);   // instance lain mungkin baru saja menerapkannya (4.3)
         if(reread >= version)
           {
            DatabaseExecute(db, "ROLLBACK");
            current = reread;
            continue;
           }
         string stmts[];
         int n = src.Statements(i, stmts);
         for(int s = 0; s < n; s++)
            if(!Exec(db, stmts[s], err))
               return Fail(db, true, StringFormat("v%d %s pernyataan %d/%d %s", version, src.Name(i), s + 1, n, err));
         if(!Record(db, version, src.Name(i), src.Checksum(i), appliedBy, nowUtc, err))
            return Fail(db, true, StringFormat("v%d catat schema_migrations %s", version, err));
         if(!Exec(db, "COMMIT", err))
            return Fail(db, true, StringFormat("v%d COMMIT %s", version, err));
         current = version;
         LogInfo("Storage", StringFormat("migrasi v%d %s diterapkan", version, src.Name(i)));
        }

      CompareChecksums(db, src);
      return SDB_MIGRATE_OK;
     }

   int    ChecksumMismatches() const     { return m_mismatch; }
   string LastError() const              { return m_error; }
  };

#endif // SDB_STORAGE_MIGRATIONRUNNER_MQH
