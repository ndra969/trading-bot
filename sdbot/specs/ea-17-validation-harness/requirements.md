# Requirements — Alat ukur in-sample / out-of-sample

Status: Done (2026-10-06)
Use case: UC-50, UC-51, UC-52 ([fase-5-overview.md](../fase-5-overview.md))
Asal: PRD-EA §Pengujian dan kriteria penerimaan (tahap 2–3), §Skor konfluensi, §Roadmap Fase 5; PC-25; python-bot-lessons §1 (skor tidak memprediksi profit)
Butuh: spec 16 (backtest dasar dengan filter), perbaikan 1.18

## Pendahuluan

Spec ini membangun alat untuk membuktikan apakah suatu perubahan strategi memperbaiki hasil:
- backtest dasar dengan periode bernama in-sample (IS) dan out-of-sample (OOS) memakai real ticks;
- laporan profit factor, drawdown, dan expectancy per periode;
- laporan hasil per nilai komponen skor, termasuk komponen bayangan;
- penanda aktif/bayangan di `signal_scores`, yang disiapkan untuk komponen Fase 5.

Strategi EA tidak berubah: skor, gerbang, dan entry sama dengan 1.18.

Bukti selesai:
- pytest laporan lulus;
- suite Storage lulus untuk skema v4;
- satu run IS + OOS versi 1.19 tercatat sebagai acuan Fase 5.

## Glosarium

- **IS (in-sample):** periode untuk mengembangkan dan menyetel: 2024-04-01..2026-07-01, OHLC M1 (awalnya 2025-10-01, diubah setelah pengukuran Req 5).
- **OOS (out-of-sample):** periode setelah IS yang hanya dipakai menilai: 2026-07-01..2026-10-01, OHLC M1.
- **REAL:** 2026-01-05..2026-10-01 dengan real ticks, untuk cek realisme (real ticks server cent tidak ada sebelum 2026-01-05).
- **Real ticks:** model tester "Every tick based on real ticks" (`Model=4`), dengan tick dan spread asli server akun cent.
- **Profit factor (PF):** total `net_profit` trade untung ÷ |total `net_profit` trade rugi|.
- **Drawdown maks (DD):** penurunan terbesar dari puncak balance ke titik terendah sesudahnya, dalam persen, dihitung dari urutan closure satu run.
- **Komponen bayangan:** komponen skor yang dicatat tetapi tidak masuk skor gerbang (PC-25).

## Requirements

### Requirement 1: Periode bernama dan real ticks
**User story:** Sebagai developer, saya ingin menjalankan backtest dasar pada periode IS atau OOS dengan satu perintah, agar periode OOS tidak tercampur saat menyetel.

#### Acceptance criteria
1. Runner WAJIB menerima pilihan periode `IS`, `OOS`, atau `ALL` untuk backtest dasar. Batas tanggal dan model setiap periode WAJIB dibaca dari satu file konfigurasi di repo, bukan dari kode.
2. Periode `IS` dan `OOS` WAJIB memakai model yang sama, dari file konfigurasi. Diubah 2026-10-05 (opsi A) setelah pengukuran Req 5: real ticks server cent hanya ada sejak 2026-01-05, jadi IS dan OOS memakai OHLC M1, dan periode `REAL` (real ticks) dipakai sebagai cek realisme.
3. Tanggal dan model yang ditulis langsung (opsi `-FromDate`, `-ToDate`, `-Model`) WAJIB tetap bisa dipakai, dan WAJIB menang atas periode bernama.
4. Setiap run WAJIB mencatat label periode dan model, sehingga laporan bisa membedakan run IS, OOS, dan run bebas.
5. JIKA tester menjalankan simbol tanpa real ticks di sebagian periode (tick hasil generate atau histori kosong) MAKA runner WAJIB menandai simbol itu di laporan, bukan diam-diam lolos.
6. Backtest WAJIB berjalan dengan satu agen tester. Durasi setiap simbol WAJIB dicatat agar beban CPU terukur.

### Requirement 2: Metrik kinerja per periode
**User story:** Sebagai trader, saya ingin melihat profit factor, drawdown, dan expectancy per periode, agar bisa membandingkan dengan kriteria penerimaan PRD.

#### Acceptance criteria
1. Laporan WAJIB menampilkan per simbol dan total: jumlah trade, win rate, R total, R per trade, PF, dan DD maks.
2. PF WAJIB dihitung dari uang (`net_profit`, termasuk komisi dan swap), bukan dari R.
3. DD maks per simbol WAJIB dihitung dari urutan closure run itu, mulai dari deposit awal tester.
4. DD total WAJIB dinyatakan dalam R, dari kurva R gabungan semua simbol yang diurutkan menurut waktu tutup.
5. JIKA tidak ada trade rugi MAKA PF WAJIB tampil "∞" tanpa error. JIKA tidak ada trade MAKA PF dan DD WAJIB tampil "-".
6. Laporan WAJIB menampilkan, sebagai informasi, status kriteria PRD tahap 2 (PF ≥ 1,3, DD ≤ 15%) dan tahap 3 (PF dan DD OOS tidak memburuk > 30% dibanding IS). Kriteria ini tidak mengubah kode keluar backtest dasar; kriteria jumlah trade tetap seperti PC-22.
7. Laporan WAJIB bisa membandingkan dua kelompok run per periode (misalnya versi baru vs acuan) dalam satu tabel.

### Requirement 3: Hasil per nilai komponen skor
**User story:** Sebagai developer, saya ingin melihat hasil trade per nilai setiap komponen skor di IS dan OOS, agar keputusan aktivasi komponen berdasarkan data.

#### Acceptance criteria
1. Laporan komponen WAJIB mengelompokkan trade tertutup per (komponen, nilai skor). Isinya jumlah trade, win rate, R per trade, dan R total, dengan IS dan OOS berdampingan.
2. Komponen aktif dan bayangan WAJIB dilaporkan dengan cara yang sama, dengan penanda aktif/bayangan.
3. Kelompok dengan < 20 trade WAJIB ditandai "sampel kecil".
4. Untuk setiap komponen, laporan WAJIB menampilkan status aturan aktivasi PC-25: kelompok nilai tertinggi lebih baik dari kelompok 0 di IS dan OOS, masing-masing ≥ 20 trade. Hasilnya `TERBUKTI`, `TIDAK`, atau `SAMPEL KURANG`.
5. Laporan komponen WAJIB juga bisa dijalankan atas semua kandidat (bukan hanya trade): distribusi nilai komponen per tahap tolak. Ini menunjukkan seberapa sering komponen bernilai, sebelum ada trade.

### Requirement 4: Penanda aktif/bayangan di `signal_scores`
**User story:** Sebagai developer, saya ingin setiap baris skor komponen menyatakan apakah ia ikut skor gerbang, agar komponen bayangan Fase 5 tidak tercampur dengan skor gerbang.

#### Acceptance criteria
1. Skema data WAJIB naik ke v4 dengan kolom `signal_scores.active` (1 = ikut skor gerbang, 0 = bayangan), lewat migrasi dari v3 tanpa kehilangan data. Baris lama menjadi `active = 1`.
2. EA WAJIB mengisi `active = 1` untuk ZONE, TREND, dan PA.
3. `signals.score_total` WAJIB tetap hanya menjumlahkan komponen aktif.
4. Backoffice (API repo, fixture, `schema.py check`) WAJIB diperbarui dalam perubahan yang sama (RULES: perubahan skema dalam satu change).

### Requirement 5: Kedalaman histori real ticks
**User story:** Sebagai developer, saya ingin tahu sejak kapan real ticks tersedia per simbol di server cent, agar periode IS dan OOS (dan target PRD 3+ tahun) bisa ditetapkan dengan realistis.

#### Acceptance criteria
1. Alat WAJIB mengukur tanggal tick tertua yang tersedia per simbol (12 simbol preset) di terminal uji, lalu mencetaknya.
2. Hasil pengukuran WAJIB dicatat di baris Hasil task dan dipakai menetapkan periode di file konfigurasi (Req 1.1).
3. JIKA histori < 12 bulan untuk suatu simbol MAKA simbol itu WAJIB ditandai di konfigurasi, dan laporan WAJIB menyebutnya.

### Requirement 6: Acuan Fase 5
**User story:** Sebagai developer, saya ingin hasil IS dan OOS versi tanpa komponen konfirmasi tercatat sebagai acuan, agar setiap spec komponen bisa dibandingkan dengannya.

#### Acceptance criteria
1. Backtest dasar IS dan OOS 12 simbol dengan versi 1.19 WAJIB dijalankan sekali, dan nomor sesi DB-nya dicatat sebagai acuan di spec dan di README spec.
2. Hasil acuan (trade, PF, DD, R per trade per periode) WAJIB dicatat di CHANGELOG.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Server tidak punya real ticks untuk awal periode IS | Simbol ditandai di laporan; periode disesuaikan lewat konfigurasi | 1.5, 5.3 |
| EC-02 | Run diulang untuk periode yang sama | Laporan memakai kelompok sesi yang dipilih (penanda sesi), tidak mencampur run lama | 2.7 |
| EC-03 | Satu simbol tanpa trade di OOS | Baris tampil dengan "-", total tetap dihitung | 2.5 |
| EC-04 | Semua trade untung (tidak ada rugi) | PF "∞" | 2.5 |
| EC-05 | DB tester masih skema v3 | Migrasi v4 berjalan saat EA init, baris lama `active = 1` | 4.1 |
| EC-06 | Komponen belum pernah dicatat (FIB belum ada) | Komponen tidak tampil, tanpa error | 3.1 |
| EC-07 | Kelompok nilai 0 tidak ada (komponen selalu bernilai) | Status `SAMPEL KURANG` | 3.4 |
| EC-08 | Real ticks 12 simbol jauh lebih lama dari OHLC M1 | Durasi per simbol dicatat; batas waktu per run bisa dinaikkan lewat opsi | 1.6 |
| EC-09 | Opsi tanggal bebas dipakai bersama periode bernama | Tanggal bebas menang, label run "CUSTOM" | 1.3, 1.4 |
| EC-10 | Trade dibuka di akhir periode dan ditutup tester saat run berakhir | Closure tetap dihitung (alasan tutup tester), sama seperti backtest dasar sekarang | 2.1 |

## Pertanyaan terbuka

- Apakah periode awal (IS 2025-10..2026-06, OOS 2026-07..2026-10) dipertahankan bila histori real ticks ternyata lebih panjang, atau IS diperpanjang ke belakang agar mendekati PRD 3+ tahun? Usulan: perpanjang IS ke belakang sejauh histori tersedia, OOS tetap 3 bulan terakhir.
- Versi 1.19 untuk perubahan skema saja (strategi sama dengan 1.18)? Usulan: ya, karena `sessions.ea_version` membedakan data skema v4.
