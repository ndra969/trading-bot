//+------------------------------------------------------------------+
//| MigrationSource.mqh — sumber migrasi untuk CSdbMigrationRunner.
//| Implementasi nyata di-generate (Migrations.mqh); uji memakai sumber
//| palsu agar migrasi gagal bisa disuntik (spec 03 Req 4, TC-DB-04).
//+------------------------------------------------------------------+
#ifndef SDB_STORAGE_MIGRATIONSOURCE_MQH
#define SDB_STORAGE_MIGRATIONSOURCE_MQH

// Migrasi diurutkan menaik menurut versi; indeks i = 0..Count()-1.
interface ISdbMigrationSource
  {
   int    Count();
   int    Version(const int i);
   string Name(const int i);
   string Checksum(const int i);
   int    Statements(const int i, string &out[]);   // pernyataan sudah dipisah, tanpa ';'
  };

#endif // SDB_STORAGE_MIGRATIONSOURCE_MQH
