# Requirements — 07 Integrasi dan penutup Fase 1

Status: Draft
Use case: UC-06 (verifikasi), UC-17, UC-18, UC-19 (query dasar) ([overview](../fase-1-overview.md))
Asal: ea-foundation R19.1–19.2, R20.2–20.3, RULES §Definition of done
Butuh: spec 01–06

## Pendahuluan

Spec penutup Fase 1: metrik optimasi `OnTester`, preset `.set` per simbol, query analisis dasar, checklist manual, regresi penuh lewat runner, serta pembaruan dokumen dan versi. Tidak ada modul trading baru di sini.

Selesai jika seluruh suite unit test dan skenario SC-00..SC-08 PASS dalam satu run `run-ea-tests.ps1 -All`, checklist manual Fase 1 dicek, dan Definition of Done RULES terpenuhi.

## Requirements

### Requirement 1: Metrik optimasi

**User story:** Sebagai developer, saya ingin optimasi Strategy Tester memilih setelan dengan expectancy tinggi dan drawdown rendah, sesuai PRD.

#### Acceptance criteria

1.1. `OnTester` WAJIB mengembalikan expectancy per trade dalam R ÷ max drawdown relatif equity (%), dengan R dari closure yang dihitung di memori.
1.2. JIKA jumlah trade < `SDB_TESTER_MIN_TRADES` (30) atau drawdown = 0 MAKA metrik WAJIB 0, agar pass dengan sedikit trade tidak terpilih.
1.3. SELAMA optimasi EA WAJIB tidak menulis DB dan tidak memanggil `WebRequest` atau fungsi kalender.

### Requirement 2: Preset

**User story:** Sebagai trader, saya ingin file `.set` siap pakai per pair, agar pemasangan di empat chart konsisten.

#### Acceptance criteria

2.1. Repo WAJIB berisi `Presets/SDBot_DAY_<PAIR>c.set` untuk EURUSD, GBPUSD, EURJPY, dan GBPJPY dengan input Fase 1, `InpSymbolSuffix = c`, dan magic berbeda dalam blok SDBot.
2.2. Preset WAJIB berisi `InpAllowLiveTrading = false` sebagai default aman, dengan komentar cara mengaktifkannya untuk akun cent.
2.3. Preset WAJIB tidak berisi nilai rahasia apa pun.
2.4. Setiap preset WAJIB lolos `ValidateInputValues` (diuji otomatis dengan membaca file preset).

### Requirement 3: Query analisis dasar

**User story:** Sebagai trader, saya ingin query siap pakai untuk menilai hasil, sebelum panel backoffice ada.

#### Acceptance criteria

3.1. `tools/queries/` WAJIB berisi query untuk: ringkasan per simbol dan versi EA (jumlah, win rate, profit factor, expectancy R); distribusi alasan tutup; kebocoran BE (closure `BE_STOP` dengan MFE ≥ 1R); loser yang tidak pernah profit (MFE < 0.2R); performa per sesi input; operasi saldo; alert per severity.
3.2. Setiap query WAJIB dijalankan otomatis terhadap fixture `data_latest_sample.sqlite` dan menghasilkan kolom yang diharapkan.

### Requirement 4: Regresi penuh

**User story:** Sebagai developer, saya ingin satu perintah yang membuktikan seluruh Fase 1 masih bekerja.

#### Acceptance criteria

4.1. `run-ea-tests.ps1 -All` WAJIB menjalankan semua suite unit test dan skenario SC-00..SC-08, lalu menampilkan ringkasan per suite dan skenario.
4.2. Skenario SC-08 WAJIB membuktikan optimasi 2 pass tidak mengubah `sdbot_tester.sqlite` dan mengembalikan metrik.
4.3. Regresi penuh WAJIB selesai dalam waktu yang dicatat di laporan (target < 30 menit) agar layak dijalankan sebelum setiap merge.

### Requirement 5: Checklist manual dan dokumen

**User story:** Sebagai trader, saya ingin semua uji yang tidak bisa diotomatisasi tercatat dan dicentang sebelum Fase 1 dinyatakan selesai.

#### Acceptance criteria

5.1. `ea/tests/manual-checklist.md` WAJIB berisi semua MC-xx dari spec 02–06, dengan kolom tanggal, hasil, dan catatan. Item bertanda Fase 3 tetap tercantum dan belum dicentang.
5.2. Diagram alur di `sdbot/docs/flows/` WAJIB diperbarui untuk init, tick, timer, eksekusi order, risk monitor, dan closure.
5.3. `sdbot/CHANGELOG.md` WAJIB mencatat versi EA Fase 1 dan ringkasan hasil regresi.
5.4. PRD-EA, PRD-Backoffice, dan RULES WAJIB sudah mencerminkan keputusan yang disetujui di spec 01–06 (dokumen induk di claude.ai + salinan repo).

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Optimasi pass tanpa trade | Metrik 0 | 1.2 |
| EC-02 | Preset dimuat di chart pair lain (EURUSDc preset di GBPUSDc) | EA jalan, tetapi magic preset menandai pair yang salah; log WARN jika simbol di nama preset berbeda dengan simbol chart (dari input `InpPresetTag`) | 2.1 |
| EC-03 | Salah satu skenario gagal di tengah regresi | Regresi lanjut ke skenario berikutnya, ringkasan akhir FAIL dengan daftar yang gagal | 4.1 |
| EC-04 | Data historis tester kurang untuk salah satu skenario | Skenario itu FAIL dengan pesan data, bukan PASS | 4.1 |
