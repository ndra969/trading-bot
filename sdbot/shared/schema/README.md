# Skema database SDBot

Kontrak data antara EA (MQL5) dan backoffice (Python). EA dan API mengikuti folder ini, bukan sebaliknya. Detail keputusan: [spec 03 design](../../specs/ea-03-storage-migrations/design.md).

## File

| File | Isi | Diedit |
|---|---|---|
| `enums.md` | Nilai teks setiap enum dan kolom yang memakainya | Tangan |
| `migrations/data/NNNN_*.sql` | Migrasi `sdbot.sqlite` / `sdbot_tester.sqlite`, satu file per versi | Tangan (dibuat lewat `schema.py new`) |
| `migrations/data/seed_sample.sql` | Data contoh per versi (`-- @version N`) | Tangan |
| `migrations/data/migrations.lock.json` | Checksum dan status rilis setiap migrasi | **Hasil generate** |
| `data_db.sql` | Snapshot skema terbaru, untuk dibaca | **Hasil generate** |
| `fixtures/data_latest_empty.sqlite`, `fixtures/data_latest_sample.sqlite` | DB kosong dan DB berisi data contoh, untuk uji | **Hasil generate** |
| `ea/src/Include/SDBot/Storage/Migrations.mqh` | Migrasi yang dibawa EA | **Hasil generate** |
| `ea/src/Include/SDBot/Core/SchemaEnums.mqh` | Konstanta enum untuk kode EA | **Hasil generate** |

File hasil generate tidak boleh diedit tangan; pre-commit menolaknya.

## Mengubah skema

```powershell
uv run python sdbot/tools/schema.py new data "tambah kolom x"   # buat 0002_tambah_kolom_x.sql
# tulis SQL maju di file itu (tanpa BEGIN/COMMIT/PRAGMA/ATTACH/TRIGGER)
# tambahkan blok "-- @version 2" di seed_sample.sql bila ada tabel/kolom baru
uv run python sdbot/tools/schema.py build                       # generate ulang semua file di atas
git commit                                                      # pre-commit menjalankan schema.py check + pytest
```

Saat EA versi baru dipasang, EA menerapkan migrasi yang belum ada ke DB-nya sendiri dan mencatatnya di tabel `schema_migrations`. Tidak ada langkah manual di MT5 atau di file DB.

Aturan:
- Migrasi hanya maju. Membatalkan perubahan = migrasi baru.
- Migrasi yang sudah ikut rilis EA (`schema.py release`) tidak boleh diubah; `check` akan gagal.
- Kolom `NOT NULL` baru di tabel berisi data harus punya `DEFAULT`; `check` mengujinya dengan data contoh.

## Aturan data

- Semua waktu UTC epoch detik. `accounts.server_utc_offset_sec` menyimpan selisih waktu server. Di `sdbot_tester.sqlite`, waktu adalah waktu server tester (di tester `TimeGMT() == TimeTradeServer()`).
- Ticket dan ID MT5 disimpan `INTEGER` 64-bit.
- `trades`, `deals`, `closures`, `balance_ops` unik per `login` + ID MT5; penulisan ulang yang sama tidak membuat baris ganda.
- `sdbot.sqlite` hanya berisi data live. Backtest menulis `sdbot_tester.sqlite`; optimasi tidak menulis DB.
- Tanpa foreign key: DB adalah log dan tidak boleh menolak baris.
