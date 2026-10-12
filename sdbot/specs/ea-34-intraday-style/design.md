# Design — Gaya intraday H1/M15/M5 (H7)

Status: Done (2026-10-13)
Requirements: [requirements.md](requirements.md) (Approved 2026-10-12)

## 1. Overview

- **Gaya baru.** `ENUM_SDB_TRADING_STYLE` mendapat `SDB_STYLE_INTRADAY = 4`. Nilainya ditambahkan di akhir, jadi nilai angka di preset lama tidak bergeser. `StyleTimeframes` memetakannya ke H1/M15/M5, dan `SdbStyleText` ke `"INTRADAY"`. Komponen lain (struktur, zona, trigger, sinyal, posisi, trailing ATR LTF) sudah membaca timeframe dari `StyleTimeframes`, jadi tidak berubah.
- **Skema v5.** `signals.style` punya `CHECK (style IN (...))`, dan SQLite tidak bisa mengubah CHECK di tempat. Migrasi `0005_style_intraday.sql` membangun ulang tabel `signals` (buat tabel baru dengan CHECK + `INTRADAY`, salin data, hapus tabel lama, ganti nama, buat ulang indeks). `enums.md` ditambah `INTRADAY`. `schema.py build` menghasilkan ulang `SchemaEnums.mqh`, `Migrations.mqh`, `data_db.sql`, dan fixture. EA menerapkan migrasi sendiri saat start, termasuk di live.
- **Pengukuran.** Tiga varian IS lewat `-SetInput`, lalu aturan pilih §5, lalu OOS + REAL. Laporan tambahan: frekuensi per bulan dan lama posisi rata-rata.

## 2. Komponen

| Komponen | Perubahan | Murni | Kriteria |
|---|---|---|---|
| `Core/Types.mqh` | `SDB_STYLE_INTRADAY = 4` | — | 1.1, 1.2 |
| `Core/Utils.mqh` | `StyleTimeframes`: `case SDB_STYLE_INTRADAY: H1/M15/M5` | ya | 1.1, 1.2 |
| `Signals/SignalEngine.mqh` | `SdbStyleText`: `INTRADAY` | ya | 1.4 |
| `shared/schema/enums.md` | `trading_style` + `INTRADAY` | — | 1.4 |
| `shared/schema/migrations/data/0005_style_intraday.sql` | rebuild `signals` dengan CHECK baru, data dan indeks dipertahankan | — | 1.4 |
| Hasil `schema.py build` | `SchemaEnums.mqh`, `Migrations.mqh`, `data_db.sql`, fixture v5, lock | — | 1.4 |
| `Core/InputRules.mqh` | rentang `InpTradingStyle` sampai 4 (bila divalidasi) | — | 1.1 |
| `tools/periods.py` / `baseline_report.py` | kolom frekuensi per bulan dan lama posisi rata-rata (bila belum ada; diputuskan saat task) | ya | 2.2 |
| `ea/tests/scenarios/SC-34_*` | harness pipeline EURUSDc INTRADAY | — | 1.3, 1.4 |
| README, `docs/flows/` | baris gaya | — | 1.1 |
| Versi | 1.32 (gaya baru + skema v5); default berubah hanya bila diterima | — | 3.3 |

## 3. Migrasi 0005

```sql
CREATE TABLE signals_v5 (... kolom sama persis dengan v4 ...,
  style TEXT NOT NULL CHECK (style IN ('SCALPING','DAY','SWING','POSITION','INTRADAY')), ...);
INSERT INTO signals_v5 SELECT * FROM signals;
DROP TABLE signals;
ALTER TABLE signals_v5 RENAME TO signals;
-- indeks signals dibuat ulang sama dengan v4
```

Daftar kolom diambil dari `data_db.sql` v4, dengan urutan kolom yang sama, sehingga `SELECT *` aman. `check` membuktikan migrasi pada DB contoh (seed v1..v4) tanpa kehilangan baris.

DB tester berukuran besar (~1,8 GB). Migrasi dijalankan sekali oleh EA saat backtest pertama 1.32, dan dicatat waktunya. DB live kecil.

## 4. Error handling

- Migrasi gagal di tengah: perilaku migrasi yang ada (transaksi per migrasi di `Migrations.mqh`, EA tetap trading tanpa DB dan mengirim satu alert Info). Tidak ada aturan baru.
- Histori M5 kurang di awal backtest: `MarkNotReady` yang ada.

## 5. Aturan pilih (ditulis sebelum OOS)

Acuan 1.31 (DAY, R:R 2,0): IS 121 trade, +19,8R; OOS 21 trade, +8,84R; REAL 55 trade, +12,32R.

1. Varian lolos IS bila:
   - IS ≥ 242 trade (≥ 2× acuan);
   - ≥ 10 trade per simbol;
   - R per trade ≥ +0,05 dan PF ≥ 1,10;
   - total R IS ≥ +19,8R.
2. Dari yang lolos, pilih total R IS tertinggi. Bila selisih < 2R, pilih yang R per tradenya lebih tinggi.
3. Bila tidak ada yang lolos, H7 ditolak.
4. Konfirmasi (sekali): DITERIMA bila di OOS dan REAL:
   - total R ≥ acuan (OOS ≥ +8,84R, REAL ≥ +12,32R);
   - R per trade ≥ +0,05;
   - trade ≥ 2× acuan (OOS ≥ 42, REAL ≥ 110).

## 6. Test case

| ID | Kasus | Harapan | Kriteria |
|---|---|---|---|
| TC-CU-xx | `StyleTimeframes(INTRADAY)` = H1/M15/M5; empat gaya lama tidak berubah | sesuai | 1.1, 1.2 |
| TC-SE-xx | `SdbStyleText(INTRADAY)` = `"INTRADAY"`, nilai lama tetap | sesuai | 1.4 |
| TC-IR-04 | `InpTradingStyle` 4 lolos validasi, 5 ditolak (bila ada validasi rentang) | sesuai | 1.1 |
| TS (schema) | `schema.py check` v5 dengan seed v1..v4: jumlah baris `signals` sama sebelum/sesudah, CHECK menerima `INTRADAY` dan menolak nilai lain | sesuai | 1.4 |
| SC-34 | **Given** harness pipeline EURUSDc 2026.08.01–2026.09.26, `InpTradingStyle=4`. **Then** ≥ 1 kandidat dengan `style='INTRADAY'`; bar kandidat kelipatan 5 menit; ≥ 1 ACCEPTED | sesuai | 1.3, 1.4 |
| REG | `-All` dengan default | semua PASS | 1.2 |
| RUN-01 | IS: V1 `InpTradingStyle=4`; V2 `InpTradingStyle=4,InpMinRR=1.5`; V3 `InpMinRR=1.5` | laporan Req 2.2, aturan §5 | 2.1–2.5 |
| RUN-02 | Varian terpilih OOS + REAL | aturan §5.4 | 3.1, 3.2 |

ID TC lanjut dari suite masing-masing saat task ditulis.

## 7. Traceability

| Req | Komponen | Uji |
|---|---|---|
| 1.1, 1.2 | Types, Utils, InputRules | TC-CU, TC-IR-04, REG |
| 1.3 | pipeline (tidak berubah) | SC-34 |
| 1.4 | SdbStyleText, enums, migrasi 0005, generate | TC-SE, TS schema, SC-34 |
| 1.5 | MarkNotReady (tidak berubah) | REG |
| 2.1–2.5 | runner, laporan, aturan §5 | RUN-01 |
| 3.1–3.5 | runner, default, preset, PC | RUN-02 |

## 8. Keputusan yang perlu disetujui

1. **`INTRADAY` sebagai gaya baru dengan nilai 4**, bukan mengubah gaya SCALPING. Gaya lama tetap tersedia, dan nilai angka di preset lama tidak bergeser.
2. **Migrasi skema v5 dengan rebuild tabel `signals`**, karena CHECK tidak bisa diubah di tempat. Alternatifnya mencatat INTRADAY sebagai `DAY`, tetapi itu membuat data menyesatkan.
3. **Parameter strategi tidak disetel ulang untuk gaya baru** (semua berbasis ATR). Bila gagal karena parameter, spec penyetelan dibuat terpisah.
4. **Aturan pilih §5**, termasuk syarat total R dan frekuensi di OOS dan REAL.
5. **Versi 1.32** untuk gaya baru + skema v5.
