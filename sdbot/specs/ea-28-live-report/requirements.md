# Requirements — Laporan live (spec 28)

Status: Done (2026-10-10)
Use case: UC-70 ([fase-6-overview.md](../fase-6-overview.md))
Asal: PRD-EA §Pengujian dan kriteria penerimaan (tahap 3 dan 4: PF, DD, error kritis, slippage), §Data dan database (`trades`, `closures`, `signals`, `alerts`, `sessions`); Fase 6 keputusan 2 (penilaian dalam R)
Butuh: live v1.25 berjalan (sejak 2026-10-09); tidak bergantung pada spec 27

## Pendahuluan

Spec ini membuat alat `tools/live_report.py` yang meringkas DB live (`Common\Files\sdbot.sqlite`) untuk satu periode. Laporan ini dipakai berkala selama Fase 6 dan menjadi bahan spec 30 (penerimaan).

Alat hanya membaca DB (`mode=ro`). EA, preset, dan DB live tidak diubah.

Di luar lingkup:
- pencocokan dengan backtest (spec 29);
- pengiriman laporan lewat Telegram;
- backoffice.

Bukti selesai:
- pytest ALL PASS (TS-120 dan seterusnya);
- laporan berhasil dibuat untuk DB live yang sebenarnya, periode sejak 2026-10-09.

## Glosarium

- **Periode**: rentang waktu UTC `[from, to)`. Sebuah trade masuk periode bila waktu **tutupnya** di dalam rentang. Kandidat dan alert masuk berdasarkan waktunya sendiri.
- **R**: hasil closure dalam kelipatan risiko awal (`closures.r_result`).
- **DD dalam R**: penurunan terbesar dari puncak kumulatif R, diurutkan menurut waktu tutup.
- **Slippage dalam R**: |harga buka − harga diminta| ÷ |harga buka − SL awal|.

## Requirements

### Requirement 1: Pilihan data
**User story:** Sebagai trader, saya ingin memilih periode dan versi yang dilaporkan, agar hasil setiap tahap live bisa dibandingkan.

#### Acceptance criteria
1. Alat WAJIB menerima `--db` (default: `sdbot.sqlite` di folder Common MT5), `--from` dan `--to` (tanggal UTC `YYYY-MM-DD`; default dari sesi LIVE pertama sampai sekarang), dan `--version` (opsional, misalnya `1.25`).
2. Alat WAJIB hanya memakai sesi `mode = 'LIVE'`. Sesi tester tidak pernah ikut.
3. BILA `--version` diisi, alat WAJIB hanya memakai sesi dengan `ea_version` itu.
4. JIKA DB tidak ada atau tidak bisa dibuka read-only, MAKA alat WAJIB keluar dengan kode 1 dan pesan yang jelas. Format argumen salah → kode 2.

### Requirement 2: Hasil trade
**User story:** Sebagai trader, saya ingin melihat hasil trade dalam R, agar bisa dibandingkan dengan backtest yang risikonya berbeda.

#### Acceptance criteria
1. Laporan WAJIB memuat, untuk seluruh periode dan per simbol:
   - jumlah trade tutup, win%, total R, R per trade;
   - PF (dari `net_profit`) dan PF dalam R (jumlah R positif ÷ jumlah R negatif);
   - DD dalam R.
2. Laporan WAJIB memuat sebaran alasan tutup (jumlah dan R rata-rata), memakai pengelompokan yang sama dengan `exit_report.py`.
3. Laporan WAJIB menyebut posisi yang masih terbuka di akhir periode (trade tanpa closure), per simbol.
4. JIKA tidak ada trade tutup, MAKA bagian hasil WAJIB menulis 0 trade tanpa error pembagian. Ini kondisi normal di awal Fase 6.

### Requirement 3: Eksekusi
**User story:** Sebagai developer, saya ingin melihat kualitas eksekusi live, agar slippage dan spread bisa dinilai (PRD tahap 4).

#### Acceptance criteria
1. Laporan WAJIB memuat slippage entry rata-rata dan maksimum, dalam point dan dalam R, keseluruhan dan per simbol.
2. Laporan WAJIB memuat spread saat entry rata-rata per simbol (point).
3. Slippage dari closure (`closures.slippage_points`) WAJIB dilaporkan terpisah per alasan tutup (SL, TP, BE_STOP, TRAIL_STOP).

### Requirement 4: Kandidat, alert, dan kesehatan
**User story:** Sebagai trader, saya ingin tahu apakah EA sehat dan kenapa kandidat ditolak, agar periode tanpa trade bisa dijelaskan.

#### Acceptance criteria
1. Laporan WAJIB memuat jumlah kandidat per tahap (ACCEPTED dan setiap `reject_stage`), keseluruhan dan per simbol.
2. Laporan WAJIB memuat jumlah alert per tipe, severity, dan status kirim (`SENT`, `FAILED`, `SKIPPED`, `PENDING`). Alert CRITICAL dan HIGH WAJIB didaftar satu per satu (waktu, simbol, tipe, pesan singkat).
3. Laporan WAJIB memuat daftar sesi (simbol, magic, versi, mulai, akhir, alasan akhir), serta celah waktu tanpa sesi aktif per simbol selama periode yang lebih dari 30 menit.
4. Laporan WAJIB menandai simbol yang tidak punya sesi aktif di akhir periode.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Belum ada trade sama sekali | Bagian hasil dan eksekusi menulis 0 / "-"; kandidat dan alert tetap dilaporkan | 2.4 |
| EC-02 | Sesi dengan setelan salah (misalnya magic dobel 2026-10-08) | Tetap dilaporkan apa adanya di daftar sesi; tidak disaring otomatis | 4.3 |
| EC-03 | Trade dibuka sebelum `--from` dan ditutup di dalam periode | Dihitung (berdasarkan waktu tutup) | 2.1 |
| EC-04 | Partial close lalu tutup akhir | Satu trade, satu R akhir (sesuai baris closure yang ada) | 2.1 |
| EC-05 | Terminal mati beberapa jam (PC mati) | Muncul sebagai celah sesi > 30 menit | 4.3 |
| EC-06 | `price_requested` atau SL awal kosong/0 | Slippage dalam R ditulis "-" untuk trade itu, tidak membuat laporan gagal | 3.1 |
| EC-07 | DB live sedang ditulis EA | Dibuka read-only; tidak mengunci dan tidak gagal | 1.4 |
| EC-08 | Beberapa versi dalam satu periode | Tanpa `--version` semua digabung; daftar sesi menyebut versinya | 1.3, 4.3 |

## Keputusan

- Keluaran teks di terminal (gaya `exit_report.py`), ditambah opsi `--out FILE` yang menulis teks yang sama untuk arsip.
