# Requirements — 05 Risk management

Status: Draft
Use case: UC-07 (lot, pre-trade), UC-09, UC-10, UC-11, UC-12, UC-13, UC-16 (STOPPED) ([overview](../fase-1-overview.md))
Asal: ea-foundation R5, R11–R15, R21, pertanyaan R2-1
Butuh: spec 04

## Pendahuluan

Spec ini membangun seluruh pengaman risiko PRD: perhitungan lot dari risiko persen, pre-trade check berurutan, pemantauan drawdown dan rugi harian setiap detik, emergency stop yang hanya bisa dibuka manual, status bersama antar-instance, dan penyesuaian untuk deposit/penarikan.

Selesai jika suite `RiskMath` dan `RiskState` ALL PASS, skenario SC-02, SC-03, SC-03r, SC-05, dan SC-07 PASS lewat runner, dan MC-RK-01..02 dicek.

## Glosarium

- **Posisi SDBot**: posisi dengan magic di blok SDBot (keputusan R2-1) di simbol mana pun.
- **Risiko posisi**: nilai uang jika posisi kena SL saat ini. Nol jika SL sudah di titik impas atau lebih baik.
- **Level drawdown**: NORMAL, INFO (≥ 5%), REDUCE (≥ `InpDDReducePct`), STOP (≥ `InpDDStopPct`).

## Requirements

### Requirement 1: Perhitungan lot

**User story:** Sebagai trader, saya ingin lot dihitung dari risiko persen dan nilai uang sebenarnya, agar risiko per trade benar untuk pair USD dan JPY di akun cent.

#### Acceptance criteria

1.1. EA WAJIB menghitung lot = balance × risiko efektif% ÷ nilai uang jarak entry–SL per 1 lot, dengan nilai uang dari `OrderCalcProfit()` pada harga yang akan dieksekusi.
1.2. EA WAJIB membulatkan lot ke bawah sesuai `SYMBOL_VOLUME_STEP`, tahan terhadap galat floating point (0.29 tetap 0.29).
1.3. JIKA lot hasil pembulatan < `SYMBOL_VOLUME_MIN` MAKA entry WAJIB ditolak dengan alasan `LOT_BELOW_MIN`, tidak dibulatkan ke atas.
1.4. JIKA lot > `SYMBOL_VOLUME_MAX` MAKA EA WAJIB memakai `SYMBOL_VOLUME_MAX` dan mencatat log WARN.
1.5. SELAMA flag lot × 0.5 aktif, risiko efektif WAJIB setengah dari `InpRiskPerTradePct`.
1.6. JIKA `OrderCalcProfit()` gagal atau nilai uang per lot ≤ 0 MAKA entry WAJIB ditolak dengan alasan dan kode error.

### Requirement 2: Pre-trade check

**User story:** Sebagai developer, saya ingin satu pintu pemeriksaan risiko sebelum setiap entry, agar strategi di fase berikutnya tidak bisa melewati aturan risiko.

#### Acceptance criteria

2.1. EA WAJIB menjalankan pemeriksaan pre-trade sebelum setiap entry, dengan urutan: boleh trading dan tidak STOPPED/pause → risiko per trade → total risiko terbuka → eksposur mata uang (lolos sampai Fase 4) → margin.
2.2. KETIKA pemeriksaan menolak MAKA EA WAJIB mengembalikan alasan dari `enums.md` (`STOPPED`, `DAILY_PAUSE`, `NOT_TRADABLE`, `MAX_OPEN_RISK`, `MARGIN_LOW`, …) dan detail angka.
2.3. JIKA risiko semua posisi SDBot di akun + risiko order baru > `InpMaxOpenRiskPct` dari balance MAKA pemeriksaan WAJIB menolak.
2.4. Risiko posisi yang SL-nya sudah di titik impas atau lebih baik WAJIB dihitung 0.
2.5. JIKA margin level setelah order < 200% MAKA pemeriksaan WAJIB menolak.
2.6. SELAMA akun tidak punya posisi (margin 0), margin level WAJIB dianggap tidak terbatas.

### Requirement 3: Puncak equity dan drawdown

**User story:** Sebagai trader, saya ingin drawdown dipantau terus, agar kerugian besar dihentikan walau tidak ada sinyal baru.

#### Acceptance criteria

3.1. EA WAJIB menjalankan pemantauan setiap 1 detik di `OnTimer`, terpisah dari logika entry, sebelum penulisan DB.
3.2. KETIKA equity melebihi puncak equity MAKA EA WAJIB memperbarui puncak di Global Variable.
3.3. KETIKA level drawdown berubah ke INFO MAKA EA WAJIB mengirim alert Info `DD_INFO`, sekali per transisi.
3.4. KETIKA level menjadi REDUCE MAKA EA WAJIB mengaktifkan flag lot × 0.5 dan mengirim alert High `DD_REDUCE`.
3.5. KETIKA level turun dari REDUCE karena drawdown < 8% MAKA EA WAJIB mencabut flag dan mengirim alert Info `DD_RECOVERED`.
3.6. KETIKA drawdown ≥ `InpDDStopPct` MAKA EA WAJIB menyetel STOPPED, menutup semua posisi SDBot, dan mengirim alert Critical `DD_STOP`.
3.7. KETIKA margin level turun di bawah 300% atau naik kembali di atasnya MAKA EA WAJIB mengirim alert High atau Info, sekali per perubahan.

### Requirement 4: Batas rugi harian

**User story:** Sebagai trader, saya ingin entry berhenti setelah rugi harian mencapai batas, agar satu hari buruk tidak merusak akun.

#### Acceptance criteria

4.1. KETIKA rugi hari ini (balance awal hari − equity) ≥ `InpDailyLossPct` dari balance awal hari MAKA EA WAJIB menyetel pause harian dan mengirim alert High `DAILY_LOSS`, sekali per hari.
4.2. SELAMA pause harian EA WAJIB menolak entry baru dan tetap mengelola posisi.
4.3. KETIKA hari server berganti MAKA tepat satu instance di akun WAJIB mencabut pause dan menyimpan balance saat itu sebagai dasar hari baru.

### Requirement 5: Emergency stop

**User story:** Sebagai trader, saya ingin emergency stop bertahan sampai saya sendiri yang membukanya.

#### Acceptance criteria

5.1. SELAMA STOPPED dan masih ada posisi SDBot, EA WAJIB mencoba menutupnya setiap 5 detik saat pasar buka dan setiap 60 detik saat pasar tutup.
5.2. KETIKA pasar buka kembali MAKA percobaan pertama WAJIB dilakukan pada siklus timer berikutnya.
5.3. JIKA penutupan gagal 3 kali berturut-turut MAKA EA WAJIB mengirim alert Critical `CLOSE_ALL_FAILED`, lalu mengulangnya paling sering sekali per 15 menit selama masih gagal.
5.4. SELAMA STOPPED EA WAJIB menolak entry, termasuk setelah EA atau terminal di-restart.
5.5. KETIKA EA di-init dengan `InpResetEmergencyStop = true` sementara pada init sebelumnya nilainya `false`, dan STOPPED aktif, MAKA EA WAJIB membuka STOPPED, menyetel puncak equity ke equity saat ini, level ke NORMAL, dan mengirim alert Info `EMERGENCY_RESET`.
5.6. JIKA `InpResetEmergencyStop` tetap `true` pada init berikutnya MAKA EA WAJIB tidak mereset lagi dan mencatat WARN agar input dikembalikan ke `false`.
5.7. EA WAJIB tidak pernah membuka STOPPED lewat jalur lain.

### Requirement 6: Status bersama antar-instance

**User story:** Sebagai trader, saya ingin empat pair di satu akun tunduk pada batas akun yang sama.

#### Acceptance criteria

6.1. Puncak equity, STOPPED, pause harian, flag lot × 0.5, level drawdown, dasar hari, dan deal saldo terakhir WAJIB disimpan di Global Variables akun (spec 02).
6.2. KETIKA satu instance menyetel STOPPED atau pause MAKA instance lain WAJIB menolak entry mulai siklus timer berikutnya.
6.3. Pergantian hari dan operasi saldo WAJIB diproses tepat sekali per akun walau beberapa instance berjalan (compare-and-set).

### Requirement 7: Operasi saldo

**User story:** Sebagai trader, saya ingin deposit dan penarikan tidak terhitung sebagai profit atau rugi.

#### Acceptance criteria

7.1. KETIKA terjadi operasi saldo MAKA EA WAJIB menyesuaikan puncak equity dan balance awal hari sebesar nominalnya.
7.2. KETIKA EA di-init MAKA EA WAJIB memproses operasi saldo yang terjadi sejak deal saldo terakhir yang sudah diproses.
7.3. Setiap operasi saldo WAJIB diproses tepat sekali per akun.
7.4. EA WAJIB mencatat setiap operasi yang diproses ke `balance_ops` dan sebagai alert Info `BALANCE_OP`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Lot hitungan 0.29 (galat floating point jadi 0.2899999) | Tetap 0.29 | 1.2 |
| EC-02 | Balance cent sangat kecil (100 USC) | Semua entry `LOT_BELOW_MIN` | 1.3 |
| EC-03 | Posisi dari kemarin floating −2% saat pergantian hari | Rugi hari baru sudah 2% sejak awal (dasar = balance). Konsekuensi disadari dan dicatat | 4.1 |
| EC-04 | Empat instance melihat pergantian hari di detik yang sama | Hanya satu yang menyetel dasar hari | 4.3, 6.3 |
| EC-05 | Pergantian hari saat akhir pekan (tidak ada tick) | Diproses di timer walau tanpa tick; hari Senin tetap hari baru | 4.3 |
| EC-06 | Drawdown 15% saat akhir pekan | STOPPED segera, penutupan dicoba tiap 60 detik, berhasil saat pasar buka | 5.1, 5.2 |
| EC-07 | Trader lupa mengembalikan `InpResetEmergencyStop` ke false, lalu STOPPED lagi di kemudian hari | Restart tidak mereset otomatis | 5.6 |
| EC-08 | Deposit saat ada posisi terbuka | Puncak dan dasar hari naik sebesar deposit, drawdown tidak berubah | 7.1 |
| EC-09 | Penarikan saat EA mati | Diproses di init | 7.2 |
| EC-10 | Kredit/bonus negatif (broker menarik bonus) | Diperlakukan seperti penarikan | 7.1 |
| EC-11 | Equity melonjak karena tick buruk lalu kembali | Puncak ikut naik (sesuai PRD); dicatat sebagai risiko yang diketahui | 3.2 |
| EC-12 | Posisi hasil rekonsiliasi tanpa SL awal | Risiko dihitung dari SL saat ini | 2.4 |
| EC-13 | Drawdown berosilasi 9–10.5% | Flag tidak berkedip; kembali normal hanya di bawah 8% | 3.4, 3.5 |
| EC-14 | Chart GBPJPYc tertutup saat drawdown 15% | Posisi GBPJPYc tetap ditutup instance lain (jika R2-1 disetujui) | 3.6 |
