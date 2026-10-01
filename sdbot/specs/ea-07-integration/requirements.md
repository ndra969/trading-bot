# Requirements — 07 Integrasi dan penutup Fase 1

Status: Done (2026-10-01)
Use case: UC-06 (verifikasi), UC-17, UC-18, UC-19 (query dasar) ([overview](../fase-1-overview.md))
Asal: PRD-EA §Pengujian dan kriteria penerimaan (metrik `OnTester`), §Instalasi (preset), §Roadmap Fase 1; ea-foundation R19.1–19.2, R20.2–20.3; RULES §Definition of done; PC-08 (`run_key`), PC-10 (12 simbol, preset per simbol)
Butuh: spec 01–06

## Pendahuluan

Spec penutup Fase 1: metrik optimasi `OnTester`, preset `.set` untuk 12 simbol bot Python, query analisis dasar, checklist manual, regresi penuh lewat runner, serta pembaruan dokumen dan versi (EA `1.06`). Tidak ada modul trading baru di sini; EA tetap tidak membuka posisi sampai Fase 3.

Selesai jika seluruh suite unit test dan semua skenario (SC-00..SC-09) PASS dalam satu run `run-ea-tests.ps1 -All`, query lolos pytest, checklist manual Fase 1 tercatat, dokumen induk PRD/RULES sudah memuat PC-01..PC-11, dan Definition of Done RULES terpenuhi.

## Glosarium

- **Kategori aset**: forex major, forex cross, komoditas, crypto (PC-10, spec 05).
- **Pass optimasi**: satu kombinasi input yang dijalankan Strategy Tester dalam mode optimasi.

## Requirements

### Requirement 1: Metrik optimasi

**User story:** Sebagai developer, saya ingin optimasi Strategy Tester memilih setelan dengan expectancy tinggi dan drawdown rendah, sesuai PRD.

#### Acceptance criteria

1.1. `OnTester` WAJIB mengembalikan expectancy per trade dalam R ÷ max drawdown relatif equity (%), dengan R dari closure posisi instance yang dihitung di memori selama run.
1.2. JIKA jumlah trade dengan R diketahui < 30 atau drawdown = 0 MAKA metrik WAJIB 0, agar pass dengan sedikit trade tidak terpilih.
1.3. SELAMA optimasi EA WAJIB tidak menulis file DB apa pun.
1.4. Metrik WAJIB dihitung dengan cara yang sama di EA utama dan harness.

### Requirement 2: Preset per simbol

**User story:** Sebagai trader, saya ingin file `.set` siap pakai untuk setiap simbol bot Python, agar pemasangan di banyak chart konsisten.

#### Acceptance criteria

2.1. Repo WAJIB berisi `Presets/SDBot_DAY_<SIMBOL>c.set` untuk 12 simbol PC-10 (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURJPY, GBPJPY, XAUUSD, XAGUSD, BTCUSD), masing-masing dengan `InpSymbolSuffix = c` dan magic sesuai pemetaan PC-10 (…01–…12).
2.2. Setiap preset WAJIB mencantumkan kategori asetnya di komentar, dan memakai nilai input yang sama untuk batas akun (risiko, drawdown, rugi harian, batas posisi per kategori).
2.3. Preset WAJIB berisi `InpAllowLiveTrading = false` sebagai default aman, dengan komentar cara mengaktifkannya untuk akun cent.
2.4. Preset WAJIB tidak berisi nilai rahasia apa pun.
2.5. Setiap preset WAJIB lolos `ValidateInputValues`, dan magic setiap preset WAJIB unik (diuji otomatis dengan membaca file preset).
2.6. KETIKA preset dimuat di chart yang simbolnya berbeda dengan simbol preset MAKA EA WAJIB mencatat WARN sekali saat init (EA tetap jalan).

### Requirement 3: Query analisis dasar

**User story:** Sebagai trader, saya ingin query siap pakai untuk menilai hasil, sebelum panel backoffice ada.

#### Acceptance criteria

3.1. `tools/queries/` WAJIB berisi query untuk: ringkasan per simbol dan versi EA (jumlah, win rate, profit factor, expectancy R); distribusi alasan tutup; kebocoran BE (closure `BE_STOP` dengan MFE ≥ 1R); loser yang tidak pernah profit (MFE < 0.2R); performa per `input_hash` sesi; operasi saldo; alert per severity; hasil per run backtest (`run_key`).
3.2. Setiap query yang menggabungkan tabel posisi WAJIB memakai kunci `login + run_key + position_id` (PC-08).
3.3. Setiap query WAJIB dijalankan otomatis terhadap fixture `data_latest_sample.sqlite` dan menghasilkan kolom yang diharapkan serta minimal satu baris.

### Requirement 4: Regresi penuh

**User story:** Sebagai developer, saya ingin satu perintah yang membuktikan seluruh Fase 1 masih bekerja.

#### Acceptance criteria

4.1. `run-ea-tests.ps1 -All` WAJIB menjalankan semua suite unit test dan semua skenario di `ea/tests/scenarios`, lalu menampilkan ringkasan per suite dan skenario; exit 0 hanya jika semuanya PASS.
4.2. Skenario optimasi SC-09 WAJIB membuktikan bahwa optimasi 2 pass tidak mengubah file DB tester dan menghasilkan nilai metrik custom di laporan optimasi.
4.3. Regresi penuh WAJIB selesai di bawah 30 menit, dan durasinya dicatat di laporan.

### Requirement 5: Checklist manual dan dokumen

**User story:** Sebagai trader, saya ingin semua uji yang tidak bisa diotomatisasi tercatat dan dicentang sebelum Fase 1 dinyatakan selesai.

#### Acceptance criteria

5.1. `ea/tests/manual-checklist.md` WAJIB berisi semua MC-xx dari spec 01–06 dan skenario uji fungsi wajib PRD, dengan kolom tanggal, hasil, dan catatan. Item yang baru bisa dicek di Fase 3 diberi tanda dan belum dicentang.
5.2. Diagram alur di `sdbot/docs/flows/` WAJIB dibuat untuk init, tick, timer, eksekusi order, risk monitor, dan closure, sesuai kode v1.06.
5.3. `sdbot/CHANGELOG.md` WAJIB mencatat versi EA 1.00–1.06 dan ringkasan hasil regresi.
5.4. Dokumen induk PRD-EA, PRD-Backoffice, dan RULES (claude.ai) beserta salinan repo WAJIB memuat keputusan PC-01..PC-11, lewat skill `sdbot-docs-sync`.
5.5. EA WAJIB naik ke versi `1.06` sebagai penanda Fase 1 selesai.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Pass optimasi tanpa trade | Metrik 0 | 1.2 |
| EC-02 | Preset EURUSDc dimuat di chart GBPUSDc | EA jalan, WARN sekali di init | 2.6 |
| EC-03 | Salah satu skenario gagal di tengah regresi | Regresi lanjut ke skenario berikutnya, ringkasan akhir FAIL dengan daftar yang gagal | 4.1 |
| EC-04 | Data historis tester kurang untuk salah satu skenario | Skenario itu FAIL dengan pesan data, bukan PASS | 4.1 |
| EC-05 | NZDUSDc tidak tersedia di akun | Preset tetap ada; EA di chart yang tidak ada tidak bisa dipasang (dicatat di checklist) | 2.1 |
| EC-06 | Closure dengan R kosong (SL awal tidak diketahui) | Tidak dihitung di expectancy maupun jumlah trade metrik | 1.1, 1.2 |
| EC-07 | Magic dua preset sama karena salah salin | Uji preset gagal | 2.5 |
| EC-08 | Optimasi di agen tester (bukan terminal utama) | Tidak ada file DB yang dibuat atau diubah | 1.3, 4.2 |

## Keputusan (disetujui 2026-10-01, dicatat sebagai PC-12)

1. **Isi preset Fase 1 sama untuk semua simbol kecuali magic dan komentar kategori.** Input yang berbeda per kategori di bot Python (spread maks, sesi, jarak SL/TP) baru ada di Fase 3–4, jadi nilai per kategori dari `config/active_symbols.yaml` dicantumkan sebagai komentar referensi di preset dan dipakai saat input itu dibuat. BE/partial/trailing tetap berbasis R dan ATR sesuai PRD (bukan pip tetap seperti bot Python).
2. **Risiko per trade tetap 0.5% (PRD)**, bukan 0.1% seperti bot Python saat ini; preset bisa diturunkan saat tahap live akun cent bila Anda mau.
3. **Skenario optimasi diberi ID SC-09** karena SC-08 sudah dipakai (restart, spec 04).
4. **Input baru `InpPresetTag`** (simbol preset, default kosong) untuk EC-02; kosong = tidak dicek.
5. Tetap dari draft: versi `1.00` → `1.06` sepanjang Fase 1 (`2.00` setelah validasi Fase 6); minimal 30 trade untuk metrik; `InpAllowLiveTrading = false` di preset.

## Pertanyaan terbuka

- Tidak ada selain keputusan di atas.
