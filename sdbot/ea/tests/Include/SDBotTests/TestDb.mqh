//+------------------------------------------------------------------+
//| TestDb.mqh — helper database SQLite untuk suite uji: buka file segar
//| di folder Common, jalankan SQL, baca satu nilai, bind integer 64-bit.
//| Dipakai EnvCheck (spec 01) dan suite Storage (spec 03).
//+------------------------------------------------------------------+
#ifndef SDB_SDBOTTESTS_TESTDB_MQH
#define SDB_SDBOTTESTS_TESTDB_MQH

// Selalu mulai dari file kosong agar hasil uji tidak bergantung pada run sebelumnya.
int TdbOpenFresh(const string file)
  {
   if(FileIsExist(file, FILE_COMMON))
      FileDelete(file, FILE_COMMON);
   int db = DatabaseOpen(file, DATABASE_OPEN_READWRITE | DATABASE_OPEN_CREATE | DATABASE_OPEN_COMMON);
   if(db == INVALID_HANDLE)
      Print("[SDB][ERROR][TestDb] DatabaseOpen gagal | file=", file, " err=", GetLastError());
   return db;
  }

// Kegagalan SQL yang disengaja (misalnya uji CHECK) tetap dicetak agar jejaknya terlihat.
bool TdbExec(const int db, const string sql)
  {
   if(DatabaseExecute(db, sql))
      return true;
   Print("[SDB][INFO][TestDb] SQL ditolak | err=", GetLastError(), " sql=", sql);
   return false;
  }

string TdbScalarText(const int db, const string sql)
  {
   string value = "";
   int stmt = DatabasePrepare(db, sql);
   if(stmt == INVALID_HANDLE)
     {
      Print("[SDB][ERROR][TestDb] DatabasePrepare gagal | err=", GetLastError(), " sql=", sql);
      return value;
     }
   if(DatabaseRead(stmt))
      DatabaseColumnText(stmt, 0, value);
   DatabaseFinalize(stmt);
   return value;
  }

long TdbScalarInt(const int db, const string sql)
  {
   long value = -1;
   int stmt = DatabasePrepare(db, sql);
   if(stmt == INVALID_HANDLE)
     {
      Print("[SDB][ERROR][TestDb] DatabasePrepare gagal | err=", GetLastError(), " sql=", sql);
      return value;
     }
   if(DatabaseRead(stmt))
      DatabaseColumnLong(stmt, 0, value);
   DatabaseFinalize(stmt);
   return value;
  }

// Parameter bind index di MQL5 dimulai dari 0 untuk placeholder ?1.
bool TdbInsertBoundLong(const int db, const string sql, const long v)
  {
   int stmt = DatabasePrepare(db, sql);
   if(stmt == INVALID_HANDLE)
      return false;
   bool ok = DatabaseBind(stmt, 0, v);
   if(ok)
     {
      ResetLastError();     // error lama tidak boleh ikut terbaca sebagai hasil statement ini
      DatabaseRead(stmt);   // statement tanpa baris hasil: Read menjalankannya
      ok = (GetLastError() == 0 || GetLastError() == ERR_DATABASE_NO_MORE_DATA);
     }
   DatabaseFinalize(stmt);
   return ok;
  }

void TdbCloseAndDelete(const int db, const string file)
  {
   if(db != INVALID_HANDLE)
      DatabaseClose(db);
   FileDelete(file, FILE_COMMON);
   FileDelete(file + "-wal", FILE_COMMON);
   FileDelete(file + "-shm", FILE_COMMON);
  }

#endif // SDB_SDBOTTESTS_TESTDB_MQH
