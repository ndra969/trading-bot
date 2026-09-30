# Requirements — 05 Risk management

Status: Done (2026-09-30)
Use case: UC-07 (lot, pre-trade), UC-09, UC-10, UC-11, UC-12, UC-13, UC-16 (STOPPED) ([overview](../fase-1-overview.md))
Asal: PRD-EA §Risk management, §Notifikasi (severity), ea-foundation R5, R11–R15, R21, keputusan R2-1 (PC-02), spec 02 §4.5 (Global Variables), spec 04 Req 4.7 dan 7.4
Butuh: spec 04 (`CExecutor`, `CSdbApp`, harness, skema v2 `run_key`)

## Pendahuluan

Spec ini membangun seluruh pengaman risiko PRD: perhitungan lot dari risiko persen, pre-trade check berurutan, pemantauan drawdown, rugi harian, dan margin setiap detik, emergency stop yang hanya bisa dibuka manual, status bersama antar-instance, dan penyesuaian untuk deposit/penarikan. Harness spec 04 diubah agar setiap entry lewat pre-trade check dan perhitungan lot.

Tidak termasuk: eksposur per mata uang (Fase 4; di spec ini langkahnya selalu lolos), BE/partial/trailing dan pencatatan closure (spec 06), pengiriman alert ke Telegram (Fase 2; di spec ini alert hanya tersimpan di tabel `alerts`).

Selesai jika suite `RiskMath` dan `RiskState` ALL PASS, skenario SC-02, SC-03, SC-03r, SC-05, dan SC-07 PASS lewat runner, skenario spec 04 (SC-00, SC-06, SC-08) tetap PASS, EA naik ke v1.04, dan MC-RK-01..02 dicek.

## Glosarium

- **Posisi SDBot**: posisi dengan magic di blok SDBot `2026091900`–`2026091999` (keputusan R2-1, PC-02) di simbol mana pun. `…00` hanya dipakai harness di tester.
- **Risiko posisi**: nilai uang yang hilang jika posisi kena SL saat ini, dari volume posisi saat ini. Nol jika SL sudah di harga buka atau lebih baik.
- **Risiko terbuka**: jumlah risiko semua posisi SDBot di akun.
- **Level drawdown**: NORMAL, INFO (≥ 5%), REDUCE (≥ `InpDDReducePct`, default 10%), STOP (≥ `InpDDStopPct`, default 15%). Drawdown = (puncak equity − equity) ÷ puncak equity.
- **Hari server**: tanggal kalender dari `TimeTradeServer()`.
- **Kategori aset**: FOREX_MAJOR (pasangan mata uang dengan USD), FOREX_CROSS (pasangan tanpa USD, misalnya EURJPY), COMMODITY (XAU, XAG), CRYPTO (BTC). Ditentukan dari mata uang base dan quote simbol (PC-10).
- **Pasar buka**: simbol dalam sesi trading dan mode trading simbol mengizinkan menutup posisi.

## Requirements

### Requirement 1: Perhitungan lot

**User story:** Sebagai trader, saya ingin lot dihitung dari risiko persen dan nilai uang sebenarnya, agar risiko per trade benar untuk pair USD dan JPY di akun cent.

#### Acceptance criteria

1.1. EA WAJIB menghitung lot = balance × risiko efektif% ÷ nilai uang jarak entry–SL untuk 1 lot, dengan nilai uang dari `OrderCalcProfit()` pada harga entry terbaru dan SL permintaan.
1.2. EA WAJIB membulatkan lot ke bawah ke kelipatan `SYMBOL_VOLUME_STEP`, tahan terhadap galat floating point (0.29 tetap 0.29, 0.0379 menjadi 0.03).
1.3. JIKA lot hasil pembulatan < `SYMBOL_VOLUME_MIN` MAKA entry WAJIB ditolak dengan alasan `LOT_BELOW_MIN`, tidak pernah dibulatkan ke atas.
1.4. JIKA lot > `SYMBOL_VOLUME_MAX` MAKA EA WAJIB memakai `SYMBOL_VOLUME_MAX` dan mencatat log WARN.
1.5. SELAMA flag lot × 0.5 aktif, risiko efektif WAJIB setengah dari `InpRiskPerTradePct`.
1.6. JIKA `OrderCalcProfit()` gagal atau nilai uang per lot ≤ 0 MAKA entry WAJIB ditolak dengan alasan `OTHER` dan kode error di detail.

### Requirement 2: Pre-trade check

**User story:** Sebagai developer, saya ingin satu pintu pemeriksaan risiko sebelum setiap entry, agar strategi di fase berikutnya tidak bisa melewati aturan risiko.

#### Acceptance criteria

2.1. EA WAJIB menjalankan pre-trade check sebelum setiap entry, dengan urutan tetap: boleh trading → tidak STOPPED → tidak pause harian → risiko per trade → total risiko terbuka → batas posisi per kategori → eksposur mata uang (selalu lolos sampai Fase 4) → margin. Pemeriksaan berhenti di penolakan pertama.
2.2. KETIKA pemeriksaan menolak MAKA EA WAJIB mengembalikan alasan dari `enums.md` (`NOT_TRADABLE`, `STOPPED`, `DAILY_PAUSE`, `RISK_PER_TRADE`, `MAX_OPEN_RISK`, `CLASS_POSITION_LIMIT`, `MARGIN_LOW`) beserta detail angka (nilai dan batasnya).
2.3. JIKA risiko order baru (dari volume, entry, dan SL order itu) > risiko efektif per trade dari balance MAKA pemeriksaan WAJIB menolak dengan `RISK_PER_TRADE`. Ini menjaga entry yang volumenya tidak berasal dari Req 1 (misalnya lot tetap harness).
2.4. JIKA risiko terbuka + risiko order baru > `InpMaxOpenRiskPct` dari balance MAKA pemeriksaan WAJIB menolak dengan `MAX_OPEN_RISK`.
2.5. Risiko posisi yang SL-nya sudah di harga buka atau lebih baik WAJIB dihitung 0; posisi tanpa SL WAJIB dihitung dengan risiko sebesar risiko per trade maksimum (1% balance) dan dicatat WARN.
2.6. JIKA margin level setelah order < 200% MAKA pemeriksaan WAJIB menolak dengan `MARGIN_LOW`. SELAMA akun tidak punya posisi (margin 0), margin level sebelum order WAJIB dianggap tidak terbatas.
2.7. Setiap entry EA WAJIB lewat pre-trade check dan kemudian `CExecutor`; pre-trade check tidak mengirim order sendiri.
2.8. JIKA jumlah posisi SDBot di akun dengan kategori aset yang sama dengan simbol order ≥ batas kategori itu (input; default dari bot Python: forex major 5, forex cross 3, komoditas 1, crypto 1) MAKA pemeriksaan WAJIB menolak dengan `CLASS_POSITION_LIMIT`.

### Requirement 3: Puncak equity, drawdown, dan margin

**User story:** Sebagai trader, saya ingin drawdown dipantau terus, agar kerugian besar dihentikan walau tidak ada sinyal baru.

#### Acceptance criteria

3.1. EA WAJIB menjalankan pemantauan risiko setiap 1 detik di `OnTimer`, terpisah dari logika entry, setelah pemeriksaan akun dan sebelum snapshot akun serta flush DB.
3.2. KETIKA equity melebihi puncak equity MAKA EA WAJIB memperbarui puncak di Global Variable.
3.3. KETIKA level drawdown naik ke INFO MAKA EA WAJIB mengirim alert Info `DD_INFO`, sekali per transisi.
3.4. KETIKA level naik ke REDUCE MAKA EA WAJIB mengaktifkan flag lot × 0.5 dan mengirim alert High `DD_REDUCE`, sekali per transisi.
3.5. SELAMA level REDUCE, flag WAJIB tetap aktif sampai drawdown < 8%; KETIKA itu terjadi MAKA EA WAJIB mencabut flag dan mengirim alert Info `DD_RECOVERED`.
3.6. KETIKA drawdown ≥ `InpDDStopPct` MAKA EA WAJIB menyetel STOPPED, memulai penutupan semua posisi SDBot (Req 5), dan mengirim alert Critical `DD_STOP`.
3.7. KETIKA margin level turun di bawah 300% MAKA EA WAJIB mengirim alert High `MARGIN_LOW`; KETIKA naik kembali ke ≥ 300% MAKA alert Info `MARGIN_OK`; masing-masing sekali per perubahan.
3.8. Snapshot akun WAJIB membawa puncak equity dari status bersama, bukan equity saat ini.
3.9. Transisi level dan alert WAJIB dikirim tepat sekali per akun walau beberapa instance berjalan.

### Requirement 4: Batas rugi harian

**User story:** Sebagai trader, saya ingin entry berhenti setelah rugi harian mencapai batas, agar satu hari buruk tidak merusak akun.

#### Acceptance criteria

4.1. KETIKA rugi hari ini (balance awal hari − equity, termasuk floating) ≥ `InpDailyLossPct` dari balance awal hari MAKA EA WAJIB menyetel pause harian dan mengirim alert High `DAILY_LOSS`, sekali per hari.
4.2. SELAMA pause harian EA WAJIB menolak entry baru (`DAILY_PAUSE`) dan tetap mengelola posisi yang ada.
4.3. KETIKA hari server berganti MAKA tepat satu instance di akun WAJIB mencabut pause dan menyimpan balance saat itu sebagai balance awal hari baru.
4.4. Pergantian hari WAJIB terdeteksi dari timer walau tidak ada tick (akhir pekan, pasar sepi).

### Requirement 5: Emergency stop

**User story:** Sebagai trader, saya ingin emergency stop bertahan sampai saya sendiri yang membukanya.

#### Acceptance criteria

5.1. SELAMA STOPPED dan masih ada posisi SDBot, EA WAJIB mencoba menutupnya setiap 5 detik saat pasar buka dan setiap 60 detik saat pasar tutup.
5.2. KETIKA pasar buka kembali MAKA percobaan pertama WAJIB dilakukan pada siklus timer berikutnya.
5.3. JIKA penutupan gagal 3 kali berturut-turut saat pasar buka MAKA EA WAJIB mengirim alert Critical `CLOSE_ALL_FAILED`, lalu mengulangnya paling sering sekali per 15 menit selama masih gagal. Percobaan saat pasar tutup tidak dihitung sebagai gagal.
5.4. SELAMA STOPPED EA WAJIB menolak entry (`STOPPED`), termasuk setelah EA atau terminal di-restart.
5.5. KETIKA EA di-init dengan `InpResetEmergencyStop = true` sementara pada init sebelumnya nilainya `false`, dan STOPPED aktif, MAKA EA WAJIB membuka STOPPED, menyetel puncak equity ke equity saat ini, level ke NORMAL, mencabut flag lot × 0.5, dan mengirim alert Info `EMERGENCY_RESET`.
5.6. JIKA `InpResetEmergencyStop` tetap `true` pada init berikutnya MAKA EA WAJIB tidak mereset lagi dan mencatat WARN agar input dikembalikan ke `false`.
5.7. EA WAJIB tidak pernah membuka STOPPED lewat jalur lain (level drawdown yang turun, pergantian hari, restart).
5.8. Penutupan emergency WAJIB lewat `CExecutor` dan hanya menyentuh posisi SDBot; posisi manual dan posisi EA lain (magic di luar blok) tidak pernah disentuh. Ini satu-satunya operasi `CExecutor` yang boleh melintasi simbol dan magic instance (pengecualian R2-1).

### Requirement 6: Status bersama antar-instance

**User story:** Sebagai trader, saya ingin semua simbol SDBot di satu akun (12 simbol, PC-10) tunduk pada batas akun yang sama.

#### Acceptance criteria

6.1. Puncak equity, STOPPED, pause harian, flag lot × 0.5, level drawdown, status alert margin, balance dan tanggal awal hari, deal saldo terakhir, dan nilai terakhir `InpResetEmergencyStop` WAJIB disimpan di Global Variables akun (spec 02), dengan nilai awal aman spec 02 §4.5 saat belum ada.
6.2. KETIKA satu instance menyetel STOPPED atau pause MAKA instance lain WAJIB menolak entry mulai pemeriksaan berikutnya (status dibaca dari GV setiap pre-trade check, tidak di-cache).
6.3. Pergantian hari, transisi level drawdown, dan operasi saldo WAJIB diproses tepat sekali per akun walau beberapa instance berjalan di detik yang sama (compare-and-set).

### Requirement 7: Operasi saldo

**User story:** Sebagai trader, saya ingin deposit dan penarikan tidak terhitung sebagai profit atau rugi.

#### Acceptance criteria

7.1. KETIKA terjadi operasi saldo (deal balance atau credit) MAKA EA WAJIB menyesuaikan puncak equity dan balance awal hari sebesar nominalnya (positif atau negatif).
7.2. KETIKA EA di-init MAKA EA WAJIB memproses operasi saldo yang terjadi sejak deal saldo terakhir yang sudah diproses, berurutan dari yang terlama.
7.3. Setiap operasi saldo WAJIB diproses tepat sekali per akun.
7.4. EA WAJIB mencatat setiap operasi yang diproses ke `balance_ops` dan sebagai alert Info `BALANCE_OP`.
7.5. KETIKA status bersama belum ada (akun baru, GV dihapus, atau awal run tester) MAKA operasi saldo yang sudah ada di history WAJIB dianggap sudah diproses, tanpa mengubah puncak dan balance awal hari (deposit awal tidak dihitung ulang).

### Requirement 8: Harness memakai pengaman risiko

**User story:** Sebagai developer, saya ingin entry harness melewati jalur risiko yang sama dengan EA, agar skenario membuktikan pengaman yang dipakai di live.

#### Acceptance criteria

8.1. Setiap entry harness WAJIB lewat perhitungan lot (Req 1) dan pre-trade check (Req 2) sebelum `CExecutor`; hasil tolak dicatat perekam dengan alasannya.
8.2. BILA skenario memakai lot tetap, lot itu WAJIB tetap melewati pre-trade check (termasuk `RISK_PER_TRADE`).
8.3. Harness WAJIB bisa melakukan penarikan saldo di bar tertentu (`TesterWithdrawal`) untuk menguji Req 7.
8.4. Skenario spec 04 (SC-00, SC-06, SC-08) WAJIB tetap PASS setelah perubahan ini.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Lot hitungan 0.29 (galat floating point jadi 0.2899999) | Tetap 0.29 | 1.2 |
| EC-02 | Balance cent sangat kecil (100 USC), SL lebar | Entry ditolak `LOT_BELOW_MIN` | 1.3 |
| EC-03 | Posisi dari kemarin floating −2% saat pergantian hari | Rugi hari baru sudah 2% sejak awal (dasar = balance). Konsekuensi disadari dan dicatat | 4.1 |
| EC-04 | Empat instance melihat pergantian hari di detik yang sama | Hanya satu yang menyetel balance awal hari | 4.3, 6.3 |
| EC-05 | Pergantian hari saat akhir pekan (tidak ada tick) | Diproses dari timer; hari Senin tetap hari baru | 4.4 |
| EC-06 | Drawdown 15% saat akhir pekan | STOPPED segera, penutupan dicoba tiap 60 detik tanpa alert gagal, berhasil saat pasar buka | 5.1–5.3 |
| EC-07 | Trader lupa mengembalikan `InpResetEmergencyStop` ke false, lalu STOPPED lagi di kemudian hari | Restart tidak mereset otomatis | 5.6 |
| EC-08 | Deposit saat ada posisi terbuka | Puncak dan balance awal hari naik sebesar deposit, drawdown tidak berubah | 7.1 |
| EC-09 | Penarikan saat EA mati | Diproses di init | 7.2 |
| EC-10 | Kredit/bonus ditarik broker (credit negatif) | Diperlakukan seperti penarikan | 7.1 |
| EC-11 | Equity melonjak karena tick buruk lalu kembali | Puncak ikut naik (sesuai PRD); dicatat sebagai risiko yang diketahui | 3.2 |
| EC-12 | Posisi hasil rekonsiliasi atau manual SDBot tanpa SL | Risiko dihitung 1% balance, WARN | 2.5 |
| EC-13 | Drawdown berosilasi 9–10.5% | Flag tidak berkedip; kembali normal hanya di bawah 8% | 3.4, 3.5 |
| EC-14 | Chart GBPJPYc tertutup saat drawdown 15% | Posisi GBPJPYc tetap ditutup instance lain | 3.6, 5.8 |
| EC-15 | Posisi manual (magic 0) dan EA lain di akun saat STOPPED | Tidak disentuh; tidak dihitung di risiko terbuka | 2.4, 5.8 |
| EC-16 | Restart terminal di tengah close all | STOPPED dari GV, close all dilanjutkan di timer pertama | 5.1, 5.4 |
| EC-17 | Awal run Strategy Tester (GV kosong, deposit awal sudah ada di history) | Deposit awal tidak diproses sebagai operasi saldo; puncak = equity awal | 7.5 |
| EC-18 | Trader menghapus GV `SDB_<login>_*` lewat F3 saat STOPPED | STOPPED hilang (di luar kendali EA); EA mencatat alert `STATE_RESET` (spec 02) dan mulai dari nilai awal aman | 6.1, 7.5 |
| EC-19 | Lot tetap harness 1.0 dengan risiko per trade 0.5% | Ditolak `RISK_PER_TRADE` | 2.3, 8.2 |
| EC-20 | Order baru membuat margin level < 200% | Ditolak `MARGIN_LOW` tanpa dikirim | 2.6 |
| EC-21 | Pair JPY 3 digit (EURJPYc) dan akun USC | Nilai uang per lot dari `OrderCalcProfit`, bukan tabel pip | 1.1 |
| EC-22 | Mode optimasi Strategy Tester | Pengaman risiko tetap jalan (GV tester), tanpa DB | 3.1 |
| EC-23 | XAUUSDc terbuka 1 posisi, instance XAGUSDc mau entry | Ditolak `CLASS_POSITION_LIMIT` (komoditas maks 1) | 2.8 |
| EC-24 | Lot BTCUSDc atau XAUUSDc (nilai per point dan step volume berbeda dari forex) | Lot tetap dari `OrderCalcProfit` dan step simbol, tanpa tabel pip | 1.1, 1.2 |
| EC-25 | Simbol yang kategorinya tidak dikenali (misalnya indeks) | Dianggap kategori sendiri `OTHER` dengan batas 1, WARN sekali | 2.8 |

## Keputusan (disetujui 2026-09-30, dicatat sebagai PC-09)

1. **Alasan tolak baru `RISK_PER_TRADE`** (kriteria 2.3). PRD menyebut "risiko per trade" sebagai langkah pre-trade check, tapi `enums.md` belum punya kodenya. Cukup `enums.md` + `schema.py build`, tanpa migrasi (kolom tanpa CHECK), dicatat di `PENDING-CHANGES.md`.
2. **Gagal close all saat pasar tutup tidak dihitung** (kriteria 5.3). Tanpa ini, STOPPED di akhir pekan memicu Critical `CLOSE_ALL_FAILED` tiap 15 menit sepanjang akhir pekan, padahal penutupan memang mustahil. Satu Critical `DD_STOP` sudah memberi tahu.
3. **Posisi SDBot tanpa SL dihitung 1% balance** (kriteria 2.5). PRD tidak mengaturnya; 1% adalah risiko per trade maksimum. Alternatif: tolak semua entry selama ada posisi tanpa SL.
4. Tetap dari draft sebelumnya: reset emergency hanya pada transisi input false → true; dasar rugi harian = balance saat pergantian hari (EC-03); close all saat pasar tutup tiap 60 detik.

5. **[Disetujui 2026-09-30, PC-10] Batas posisi per kategori aset** (kriteria 2.8), mengikuti bot Python.

## Pertanyaan terbuka

- Tidak ada selain tiga keputusan di atas.
