# Requirements — 06 Manajemen posisi dan closure

Status: Done (2026-09-30)
Use case: UC-14, UC-15, UC-16 ([overview](../fase-1-overview.md))
Asal: PRD-EA §Position management, §Eksekusi order, §Notifikasi, §Data dan database; ea-foundation R4, R7–R10, R16; [python-bot-lessons.md](../python-bot-lessons.md) §1–3 (alasan tutup, MFE/MAE, bug partial); spec 04 (`CExecutor`, komentar `SDB|SL|ID`, `run_key`), spec 05 (close all lintas instance, PC-10)
Butuh: spec 04, spec 05

## Pendahuluan

Spec ini membangun pengelolaan posisi per tick (breakeven, partial close, trailing, SL yang hilang), pencatatan setiap deal dan penutupan posisi dengan alasan yang dibedakan, MFE/MAE dalam R, serta rekonsiliasi setelah restart. Semua status posisi disimpulkan dari posisi dan history MT5, tidak dari DB atau variabel yang bisa basi (pelajaran bug partial bot Python). Semua ambang memakai R dan ATR, jadi berlaku sama untuk forex, emas, dan crypto (PC-10).

Tidak termasuk: metrik `OnTester` dan preset (spec 07), entry dari sinyal (Fase 3), notifikasi Telegram (Fase 2; di sini event dan alert hanya tersimpan).

Selesai jika suite `PositionMath` dan `Closure` ALL PASS, skenario SC-01, SC-01b, SC-04, SC-04b PASS lewat runner, skenario spec 04–05 tetap PASS, EA naik ke v1.05, dan checklist manual yang bisa dilakukan di Fase 1 dicek.

## Glosarium

- **Posisi instance**: posisi yang deal pembukanya (`DEAL_ENTRY_IN`) memakai magic dan simbol instance ini. Deal penutupnya boleh membawa magic lain (close all dari instance lain, spec 05) atau magic 0 (manual).
- **SL awal**: SL saat posisi dibuka. Sumber berurutan: komentar order `SDB|<SL>|<ID>` → `ORDER_SL` order pembuka di history → tabel `trades` (event sink).
- **R**: |harga buka − SL awal|. **Profit dalam R**: pergerakan harga dari harga buka ke harga penutupan saat ini (bid untuk buy, ask untuk sell) dibagi R.
- **Titik BE**: harga buka ± (spread + biaya komisi dalam point + `InpBreakevenBufferPoints`) searah posisi.
- **BE aktif**: SL sudah di harga buka atau lebih baik.
- **Trailing aktif**: SL sudah lebih baik dari titik BE.
- **MFE / MAE**: pergerakan paling menguntungkan / paling merugikan selama posisi terbuka, dalam R.

## Requirements

### Requirement 1: Konteks posisi

**User story:** Sebagai trader, saya ingin EA selalu tahu status setiap posisi dari MT5, agar BE dan partial tidak terulang atau terlewat setelah restart.

#### Acceptance criteria

1.1. Untuk setiap posisi instance, EA WAJIB membaca dari MT5: harga buka, SL dan TP sekarang, volume sekarang, volume awal (deal `IN`), SL awal, R, dan profit dalam R.
1.2. EA WAJIB mencari SL awal berurutan dari komentar order, `ORDER_SL` order pembuka di history, lalu event sink, dan menyimpan hasil beserta sumbernya di cache per posisi.
1.3. JIKA SL awal tidak ditemukan dari ketiga sumber MAKA EA WAJIB melewati BE dan partial untuk posisi itu, tetap menjalankan trailing bila BE sudah aktif, dan mencatat log ERROR sekali per posisi.
1.4. EA WAJIB menyimpulkan BE aktif dari SL terhadap harga buka, dan partial sudah dilakukan dari volume sekarang < volume awal.

### Requirement 2: Breakeven

**User story:** Sebagai trader, saya ingin SL pindah ke titik impas setelah profit 1R.

#### Acceptance criteria

2.1. KETIKA profit ≥ `InpBreakevenR` R dan BE belum aktif MAKA EA WAJIB memindahkan SL ke titik BE (spread saat ini + komisi pulang-pergi posisi dalam point + `InpBreakevenBufferPoints`).
2.2. JIKA SL BE tidak valid terhadap harga saat ini, stops level, atau freeze level MAKA EA WAJIB menundanya ke tick berikutnya tanpa menghitung sebagai kegagalan.
2.3. KETIKA BE berhasil MAKA EA WAJIB mengirim event `BE` dengan SL lama, SL baru, volume, harga, dan spread, serta alert Info.

### Requirement 3: Partial close

**User story:** Sebagai trader, saya ingin sebagian profit terkunci di 1.5R.

#### Acceptance criteria

3.1. KETIKA profit ≥ `InpPartialR` R dan partial belum dilakukan MAKA EA WAJIB menutup `InpPartialPct` persen dari volume awal, dibulatkan ke bawah sesuai step.
3.2. JIKA volume yang ditutup atau sisanya < lot minimum MAKA EA WAJIB melewati partial untuk posisi itu dan mengirim event `PARTIAL_SKIPPED` sekali per posisi.
3.3. KETIKA partial berhasil MAKA EA WAJIB mengirim event `PARTIAL` dengan volume yang ditutup, harga, dan spread, serta alert Info.
3.4. JIKA trader menutup sebagian posisi secara manual MAKA EA WAJIB menganggap partial sudah dilakukan dan tidak menutup lagi.

### Requirement 4: Trailing stop

**User story:** Sebagai trader, saya ingin SL mengikuti harga berdasarkan volatilitas setelah BE.

#### Acceptance criteria

4.1. SELAMA BE aktif EA WAJIB menghitung SL trailing = bid − ATR(`InpTrailATRPeriod`, LTF gaya trading) × `InpTrailATRMult` untuk buy, dan ask + ATR × pengali untuk sell.
4.2. EA WAJIB mengirim SL trailing hanya jika lebih baik dari SL sekarang minimal 5 point dan valid terhadap stops/freeze level.
4.3. EA WAJIB memakai nilai ATR dari bar LTF yang sudah tutup (shift 1), dengan handle dibuat saat init, dicek `INVALID_HANDLE`, dan dilepas saat deinit.
4.4. JIKA data ATR belum tersedia MAKA EA WAJIB melewati trailing pada tick itu.
4.5. KETIKA trailing pertama kali menggeser SL posisi MAKA EA WAJIB mengirim event `TRAILING`; geseran berikutnya paling sering satu event per bar LTF.

### Requirement 5: Aturan umum modifikasi

**User story:** Sebagai trader, saya ingin SL tidak pernah memburuk dan kegagalan terlihat tanpa membanjiri alert.

#### Acceptance criteria

5.1. EA WAJIB mengevaluasi BE, partial, dan trailing secara terpisah untuk setiap posisi di setiap tick, dari konteks yang sama.
5.2. EA WAJIB mengirim paling banyak satu modifikasi SL per posisi per tick (yang terbaik di antara BE dan trailing), dan tidak pernah SL yang lebih buruk dari SL sekarang.
5.3. JIKA modifikasi atau partial gagal (setelah ulangan cepat di `CExecutor`) MAKA EA WAJIB mencoba lagi setelah 30 detik, maksimal 3 kali per aksi per posisi, lalu mengirim event `MODIFY_FAILED` dan tepat satu alert Medium, dan berhenti mencoba aksi itu sampai kondisinya berubah (SL atau volume posisi berubah).
5.4. EA WAJIB tidak menutup posisi karena SL/TP tersentuh; penutupan itu oleh server broker.
5.5. JIKA posisi instance tidak punya SL (dihapus manual) MAKA EA WAJIB memasang kembali SL awal bila masih valid terhadap harga, atau SL valid terdekat, mengirim event `SL_RESTORED` dan alert High; gagal 3 kali berturut-turut → alert Critical.
5.6. SELAMA akun belum lolos validasi atau tidak boleh trading, EA WAJIB tidak mengirim modifikasi apa pun.

### Requirement 6: Deal dan closure

**User story:** Sebagai trader, saya ingin setiap eksekusi dan penutupan tercatat dengan alasan yang tepat, agar kebocoran BE dan entry yang salah arah bisa diukur.

#### Acceptance criteria

6.1. KETIKA deal posisi instance terjadi (apa pun magic deal itu) MAKA EA WAJIB mengirim `DealRecord` (tiket, posisi, entry, arah, volume, harga, alasan, profit, komisi, swap, fee) tepat sekali.
6.2. KETIKA posisi instance tertutup penuh MAKA EA WAJIB mengirim `ClosureRecord` dengan total volume, profit, komisi, swap, fee, dan net profit dari semua deal posisi itu, tepat sekali.
6.3. EA WAJIB menentukan alasan tutup dari deal penutup terakhir: `TP` (alasan TP), `TRAIL_STOP` (SL kena lebih baik dari titik BE), `BE_STOP` (SL kena di sekitar titik BE), `SL` (SL kena di sisi rugi dari harga buka), `MANUAL` (client, mobile, web), `STOP_OUT` (SO), `EA_CLOSE` (ditutup SDBot, termasuk close all dari instance lain), `ROLLOVER`, atau `OTHER`.
6.4. EA WAJIB menghitung R hasil = net profit ÷ risiko uang awal (dari SL awal dan volume awal), dan kosong jika risiko awal tidak diketahui.
6.5. EA WAJIB menghitung MFE dan MAE dalam R dari bar M1 antara waktu buka dan tutup; kosong jika bar tidak tersedia.
6.6. EA WAJIB menyimpan lama posisi dan flag BE, partial, trailing pada closure, disimpulkan dari event dan history posisi itu.
6.7. EA WAJIB mengabaikan deal operasi saldo dan deal posisi instance lain.

### Requirement 7: Rekonsiliasi dan restart

**User story:** Sebagai trader, saya ingin EA melanjutkan dengan benar setelah restart, update, atau PC menyala lagi.

#### Acceptance criteria

7.1. KETIKA EA di-init MAKA EA WAJIB mengirim `TradeRecord` sumber `RECONCILED` untuk setiap posisi instance yang terbuka (penulisan ganda dicegah kunci unik `login + run_key + position_id`); JIKA SL awal tidak diketahui MAKA SL sekarang dipakai, risiko uang kosong, dan log WARN.
7.2. KETIKA EA di-init MAKA EA WAJIB memindai history deal instance sejak deal terakhir yang diproses (Global Variable per magic), lalu mengirim deal dan closure yang terlewat saat EA mati; tanpa GV, 30 hari terakhir.
7.3. KETIKA EA di-restart saat ada posisi yang sudah BE dan partial MAKA EA WAJIB tidak menggeser BE ulang dan tidak melakukan partial kedua.
7.4. Cache per posisi WAJIB dibersihkan saat posisi tertutup.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Spread melebar saat berita sehingga SL BE di atas bid | BE ditunda sampai valid | 2.2 |
| EC-02 | Harga gap melewati level BE dan partial dalam satu tick | BE dan partial dievaluasi terpisah di tick yang sama | 5.1 |
| EC-03 | Harga gap turun melewati SL BE sebelum modifikasi terkirim | Modifikasi ditunda; broker menutup di SL awal → `SL` | 2.2, 6.3 |
| EC-04 | Posisi 0.01 lot | Partial dilewati sekali (`PARTIAL_SKIPPED`), BE dan trailing tetap jalan | 3.2 |
| EC-05 | Trader menutup sebagian manual | Partial dianggap sudah, deal dicatat | 3.4, 6.1 |
| EC-06 | Trader menghapus SL | SL dipasang kembali + `SL_RESTORED` + alert High | 5.5 |
| EC-07 | Trader memindah SL lebih jauh dari SL awal | EA tidak mengembalikan; R tetap dari SL awal | 1.2, 5.2 |
| EC-08 | Broker mengubah komentar posisi | SL awal dari history order | 1.2 |
| EC-09 | Posisi ditutup saat EA mati | Closure direkam saat init dari history | 7.2 |
| EC-10 | Trailing bergeser tiap tick selama 1 jam | Satu event per bar LTF, bukan per tick | 4.5 |
| EC-11 | Posisi ditutup "close by" (hedging) | Deal `OUT_BY` diproses seperti close | 6.1, 6.2 |
| EC-12 | Stop out sebagian posisi | Deal dicatat; closure hanya saat posisi habis, alasan `STOP_OUT` | 6.3 |
| EC-13 | History M1 tidak lengkap untuk posisi lama | MFE/MAE kosong, closure tetap tercatat | 6.5 |
| EC-14 | Modify ditolak broker terus | 3 percobaan berjarak 30 detik, satu `MODIFY_FAILED` + satu alert, lalu berhenti sampai kondisi berubah | 5.3 |
| EC-15 | Posisi GBPJPYc ditutup close all oleh instance EURUSDc (deal penutup bermagic EURUSDc) | Instance GBPJPYc mencatat deal dan closure `EA_CLOSE`; instance EURUSDc tidak mencatatnya | 6.1–6.3, 6.7 |
| EC-16 | Pemilik posisi tidak jalan saat posisinya ditutup (chart tertutup) | Closure tercatat saat pemilik di-init berikutnya | 7.2 |
| EC-17 | Pair JPY (3 digit), XAUUSDc, BTCUSDc | Titik BE, trailing, dan MFE/MAE dalam point dan R, tanpa tabel pip | 2.1, 4.1, 6.5 |
| EC-18 | Akun cent tanpa komisi | Komponen komisi di titik BE = 0 | 2.1 |
| EC-19 | Restart harness di tester di tengah posisi (run_key sama) | `TradeRecord` `RECONCILED` tidak menambah baris; BE/partial tidak diulang | 7.1, 7.3 |
| EC-20 | Deal dan deinit terjadi hampir bersamaan (transaksi hilang) | Deal diambil dari scan history saat init berikutnya, tidak ganda | 7.2, 6.1 |

## Keputusan (disetujui 2026-09-30, dicatat sebagai PC-11)

1. **Kepemilikan posisi dari deal pembuka**, bukan magic deal penutup (glosarium, EC-15). Tanpa ini closure dari close all lintas pair (spec 05) tidak pernah tercatat oleh pemilik posisi.
2. **Komisi masuk titik BE** sesuai PRD ("spread + komisi"): komisi pulang-pergi posisi (dari deal `IN`, × 2) dikonversi ke point lewat `OrderCalcProfit`. Di akun cent Exness komisi 0, jadi hasilnya sama dengan draft lama.
3. **Alert `MODIFY_FAILED` hanya dari manajer posisi** setelah 3 percobaan berjarak 30 detik; `CExecutor` tidak mengirim alert sendiri untuk modifikasi dari manajer posisi (spec 04 mengirim alert per operasi, yang akan menjadi 3 alert).
4. Tetap dari draft: alasan tutup dibedakan `SL`/`BE_STOP`/`TRAIL_STOP` dari level pemicu SL; MFE/MAE dari bar M1 saat tutup; SL yang dihapus manual dipasang kembali (PRD tidak mengatur; mengikuti aturan "setiap posisi selalu punya SL"); satu modifikasi SL per tick per posisi; event trailing paling sering sekali per bar LTF.

## Pertanyaan terbuka

- Tidak ada selain keputusan di atas.
