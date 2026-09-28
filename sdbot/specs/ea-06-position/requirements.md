# Requirements — 06 Manajemen posisi dan closure

Status: Draft
Use case: UC-14, UC-15, UC-16 ([overview](../fase-1-overview.md))
Asal: ea-foundation R4, R7–R10, R16; [python-bot-lessons.md](../python-bot-lessons.md) §1–3 (alasan tutup, MFE/MAE, bug partial)
Butuh: spec 04, spec 05

## Pendahuluan

Spec ini membangun pengelolaan posisi per tick (breakeven, partial close, trailing), pencatatan setiap deal dan penutupan posisi dengan alasan yang dibedakan, MFE/MAE dalam R, serta rekonsiliasi setelah restart. Semua status posisi disimpulkan dari posisi dan history MT5, tidak dari DB (pelajaran bug partial di bot Python).

Selesai jika suite `PositionMath` dan `Closure` ALL PASS, skenario SC-01 dan SC-04 PASS lewat runner, dan checklist manual yang bisa dilakukan di Fase 1 dicek.

## Glosarium

- **SL awal**: SL saat posisi dibuka. Sumber: komentar order → `ORDER_SL` order pembuka di history → tabel `trades`.
- **R**: |harga buka − SL awal|.
- **BE aktif**: SL sudah di titik impas atau lebih baik (buy: SL ≥ harga buka).
- **Trailing aktif**: SL sudah lebih baik dari titik BE + buffer.
- **MFE / MAE**: pergerakan paling menguntungkan / paling merugikan selama posisi terbuka, dalam R.

## Requirements

### Requirement 1: Konteks posisi

**User story:** Sebagai trader, saya ingin EA selalu tahu status setiap posisi dari MT5, agar BE dan partial tidak terulang atau terlewat setelah restart.

#### Acceptance criteria

1.1. Untuk setiap posisi dengan magic dan simbol instance ini, EA WAJIB menentukan harga buka, SL dan TP sekarang, volume sekarang, volume awal (dari deal `IN`), SL awal, R, dan profit dalam R.
1.2. EA WAJIB mencari SL awal berurutan dari komentar order, `ORDER_SL` order pembuka di history, lalu event sink, dan menyimpan hasilnya di cache per posisi.
1.3. JIKA SL awal tidak ditemukan dari ketiga sumber MAKA EA WAJIB melewati BE dan partial untuk posisi itu, tetap menjalankan trailing bila BE sudah aktif, dan mencatat log ERROR sekali per posisi.
1.4. EA WAJIB menyimpulkan BE aktif dari posisi SL terhadap harga buka, dan partial sudah dilakukan dari volume sekarang < volume awal.

### Requirement 2: Breakeven

**User story:** Sebagai trader, saya ingin SL pindah ke titik impas setelah profit 1R.

#### Acceptance criteria

2.1. KETIKA profit ≥ `InpBreakevenR` R dan BE belum aktif MAKA EA WAJIB memindahkan SL ke harga buka ± (spread saat ini + `InpBreakevenBufferPoints`) searah posisi.
2.2. JIKA SL BE tidak valid terhadap harga saat ini, stops level, atau freeze level MAKA EA WAJIB menundanya ke tick berikutnya tanpa menghitung sebagai kegagalan.
2.3. KETIKA BE berhasil MAKA EA WAJIB mengirim event `BE` dengan SL lama, SL baru, volume, harga, dan spread.

### Requirement 3: Partial close

**User story:** Sebagai trader, saya ingin sebagian profit terkunci di 1.5R.

#### Acceptance criteria

3.1. KETIKA profit ≥ `InpPartialR` R dan partial belum dilakukan MAKA EA WAJIB menutup `InpPartialPct` persen dari volume awal, dibulatkan ke bawah sesuai step.
3.2. JIKA volume yang ditutup atau sisanya < lot minimum MAKA EA WAJIB melewati partial untuk posisi itu dan mengirim event `PARTIAL_SKIPPED` sekali.
3.3. KETIKA partial berhasil MAKA EA WAJIB mengirim event `PARTIAL` dengan volume yang ditutup, harga, dan spread.
3.4. JIKA trader menutup sebagian posisi secara manual MAKA EA WAJIB menganggap partial sudah dilakukan dan tidak menutup lagi.

### Requirement 4: Trailing stop

**User story:** Sebagai trader, saya ingin SL mengikuti harga berdasarkan volatilitas setelah BE.

#### Acceptance criteria

4.1. SELAMA BE aktif EA WAJIB menghitung SL trailing = harga − ATR(`InpTrailATRPeriod`, LTF) × `InpTrailATRMult` untuk buy (bid) dan + untuk sell (ask).
4.2. EA WAJIB mengirim SL trailing hanya jika lebih baik dari SL sekarang minimal 5 point dan valid terhadap stops/freeze level.
4.3. EA WAJIB memakai nilai ATR dari bar LTF yang sudah tutup, dengan handle dibuat saat init.
4.4. JIKA data ATR belum tersedia MAKA EA WAJIB melewati trailing pada tick itu.
4.5. KETIKA trailing pertama kali menggeser SL MAKA EA WAJIB mengirim event `TRAILING`, dan untuk geseran berikutnya paling sering satu event per bar LTF agar log tidak membanjir.

### Requirement 5: Aturan umum modifikasi

**User story:** Sebagai trader, saya ingin SL tidak pernah memburuk dan kegagalan terlihat.

#### Acceptance criteria

5.1. EA WAJIB mengevaluasi BE, partial, dan trailing secara terpisah untuk setiap posisi di setiap tick.
5.2. EA WAJIB mengirim paling banyak satu modifikasi SL per posisi per tick (yang terbaik di antara BE dan trailing).
5.3. JIKA modifikasi gagal MAKA EA WAJIB mencoba lagi setelah 30 detik, maksimal 3 kali, lalu mengirim event `MODIFY_FAILED` dan alert Medium, dan berhenti mencoba untuk aksi itu sampai kondisinya berubah.
5.4. EA WAJIB tidak menutup posisi karena SL/TP tersentuh; penutupan itu oleh server broker.
5.5. JIKA posisi tidak punya SL (dihapus manual) MAKA EA WAJIB memasang kembali SL awal bila masih valid terhadap harga, atau SL terdekat yang valid, dan mengirim alert High.

### Requirement 6: Deal dan closure

**User story:** Sebagai trader, saya ingin setiap eksekusi dan penutupan tercatat dengan alasan yang tepat, agar kebocoran BE dan entry yang salah arah bisa diukur.

#### Acceptance criteria

6.1. KETIKA deal posisi instance ini terjadi MAKA EA WAJIB mengirim `DealRecord` (tiket, posisi, entry, arah, volume, harga, alasan, profit, komisi, swap, fee).
6.2. KETIKA posisi tertutup penuh MAKA EA WAJIB mengirim `ClosureRecord` dengan total volume, profit, komisi, swap, fee, net profit dari semua deal posisi itu.
6.3. EA WAJIB menentukan alasan tutup: `TP` (deal alasan TP), `TRAIL_STOP` (SL kena di atas titik BE + buffer), `BE_STOP` (SL kena di sekitar titik BE), `SL` (SL kena di bawah titik BE), `MANUAL` (client, mobile, web), `STOP_OUT`, `EA_CLOSE` (ditutup EA, misalnya emergency), `ROLLOVER`, atau `OTHER`.
6.4. EA WAJIB menghitung R hasil = net profit ÷ risiko uang awal, dan kosong jika risiko awal tidak diketahui.
6.5. EA WAJIB menghitung MFE dan MAE dalam R dari bar M1 antara waktu buka dan tutup; kosong jika bar tidak tersedia.
6.6. EA WAJIB menyimpan lama posisi dan flag BE, partial, trailing pada closure.

### Requirement 7: Rekonsiliasi dan restart

**User story:** Sebagai trader, saya ingin EA melanjutkan dengan benar setelah restart, update, atau PC menyala lagi.

#### Acceptance criteria

7.1. KETIKA EA di-init MAKA EA WAJIB mengirim `TradeRecord` sumber `RECONCILED` untuk setiap posisi terbuka instance ini (penulisan ganda dicegah oleh kunci unik).
7.2. KETIKA EA di-init MAKA EA WAJIB memindai history deal instance ini sejak deal terakhir yang diproses (Global Variable per magic), lalu mengirim deal dan closure yang terlewat saat EA mati.
7.3. KETIKA EA di-restart saat ada posisi yang sudah BE dan partial MAKA EA WAJIB tidak menggeser BE ulang dan tidak melakukan partial kedua.
7.4. Cache per posisi WAJIB dibersihkan saat posisi tertutup.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Spread melebar saat berita sehingga SL BE di atas bid | BE ditunda sampai valid | 2.2 |
| EC-02 | Harga gap melewati level BE dan partial dalam satu tick | BE dan partial dievaluasi terpisah di tick yang sama | 5.1 |
| EC-03 | Harga gap turun melewati SL BE sebelum modifikasi terkirim | Modifikasi ditunda; broker menutup di SL awal → `SL` | 2.2, 6.3 |
| EC-04 | Posisi 0.01 lot | Partial dilewati sekali, BE dan trailing tetap jalan | 3.2 |
| EC-05 | Trader menutup sebagian manual | Partial dianggap sudah, deal dicatat | 3.4, 6.1 |
| EC-06 | Trader menghapus SL | SL dipasang kembali + alert High | 5.5 |
| EC-07 | Trader memindah SL lebih jauh dari SL awal | EA tidak mengembalikan; R tetap dari SL awal | 1.2 |
| EC-08 | Broker mengubah komentar posisi | SL awal dari history order | 1.2 |
| EC-09 | Posisi ditutup saat EA mati | Closure direkam saat init dari history | 7.2 |
| EC-10 | Trailing bergeser tiap tick selama 1 jam | Satu event per bar LTF, bukan per tick | 4.5 |
| EC-11 | Posisi ditutup "close by" (hedging) | Deal `OUT_BY` diproses seperti close | 6.1 |
| EC-12 | Stop out sebagian posisi | Deal dicatat; closure hanya saat posisi habis, alasan `STOP_OUT` | 6.3 |
| EC-13 | History M1 tidak lengkap untuk posisi lama | MFE/MAE kosong, closure tetap tercatat | 6.5 |
| EC-14 | Modify ditolak broker 3 kali | Event `MODIFY_FAILED` + alert, tidak dicoba terus-menerus | 5.3 |
