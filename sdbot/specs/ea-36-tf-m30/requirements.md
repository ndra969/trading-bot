# Requirements — Zona M30 (H9)

Status: Done (2026-10-14)
Use case: UC-83 ([fase-5c-overview.md](../fase-5c-overview.md)); permintaan user 2026-10-13: day trading terlalu lama menunggu dan memvalidasi, coba H1/M30/M15
Asal: PRD-EA §Gaya dan timeframe, §Parameter input; spec 34 (intraday H1/M15/M5 ditolak: zona M15 terlalu lemah, spread 20% risiko); PC-28 (aturan uji)
Butuh: spec 34 (selesai). Acuan = konfigurasi 1.31 (DAY H4/H1/M15, zona lawan wajib)

## Pendahuluan

Spec ini menguji hipotesis H9: zona di M30 adalah titik tengah antara zona H1 (positif tetapi jarang) dan zona M15 (sering tetapi rugi).

| Zona di | Uji | Trade/bulan (IS) | R per trade |
|---|---|---|---|
| H1 (DAY, sekarang) | acuan 1.31 | 4,5 | +0,164 |
| M15 (intraday) | spec 34 | 9,5 | −0,117 |
| **M30** | spec ini | ? | ? |

Penyebab kegagalan M15 menurut spec 34: zona lebih sering tembus (SL 55% vs 43%) dan spread memakan ~20% risiko (DAY ~12%). M30 diperkirakan berada di tengah keduanya.

Varian:
- **V1:** H1 / M30 / M15 (permintaan user);
- **V2:** H4 / M30 / M15 (bias tetap H4 seperti sekarang, hanya zona yang turun ke M30).

Agar tidak perlu perubahan skema DB setiap kali mencoba kombinasi timeframe, spec ini menambah input timeframe yang mengganti pasangan gaya. `signals.style` tetap mencatat gaya (DAY), dan timeframe sebenarnya tercatat di `inputs_json`.

Di luar lingkup:
- penyetelan parameter lain;
- R:R selain 2,0 (spec 34 menunjukkan R:R 1,5 lebih buruk).

Bukti selesai:
- suite unit dan regresi PASS dengan default identik dengan acuan;
- backtest IS kedua varian, lalu OOS + REAL untuk varian terpilih;
- keputusan H9.

## Requirements

### Requirement 1: Input timeframe
**User story:** Sebagai developer, saya ingin mengatur HTF/MTF/LTF lewat input, agar kombinasi timeframe bisa diuji tanpa gaya dan skema baru.

#### Acceptance criteria
1. Input `InpHtfTimeframe`, `InpMtfTimeframe`, `InpLtfTimeframe` (ENUM_TIMEFRAMES, default `PERIOD_CURRENT` = ikut gaya) WAJIB tersedia.
2. BILA ketiganya diisi, EA WAJIB memakai timeframe itu untuk bias, zona, trigger, ATR trailing, dan semua komponen yang sekarang membaca `StyleTimeframes`.
3. JIKA hanya sebagian diisi, atau urutan tidak HTF > MTF > LTF, MAKA EA WAJIB gagal init dengan pesan validasi.
4. BILA default, perilaku WAJIB identik dengan acuan.
5. `inputs_json` WAJIB memuat ketiga input. `signals.style` tidak berubah (skema tetap v5).

### Requirement 2: Pengukuran IS
#### Acceptance criteria
1. Backtest `-Period IS` untuk V1 dan V2, konfigurasi lain sama dengan acuan.
2. Laporan: trade, trade/bulan, R per trade, total R, PF, DD, lama posisi, alasan tutup, per simbol.
3. Varian lolos IS bila:
   - frekuensi ≥ 1,5× acuan (≥ 182 trade IS);
   - R per trade ≥ +0,05 dan PF ≥ 1,10;
   - total R IS ≥ acuan (+19,8R);
   - ≥ 8 trade per simbol.
4. Dari yang lolos pilih total R tertinggi. Bila tidak ada yang lolos, H9 ditolak.

### Requirement 3: Konfirmasi dan keputusan
#### Acceptance criteria
1. Varian terpilih dijalankan sekali di OOS dan REAL.
2. DITERIMA bila di OOS dan REAL:
   - total R ≥ acuan (OOS +8,84R, REAL +12,32R);
   - R per trade ≥ +0,05;
   - trade ≥ 1,5× acuan.
3. Bila DITERIMA: default timeframe dan preset 12 simbol berubah, versi naik, PC untuk PRD.
4. Bila DITOLAK: default tetap, input tetap ada untuk eksperimen.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Input HTF = M30, MTF = H1 (urutan terbalik) | Gagal init dengan pesan | 1.3 |
| EC-02 | Hanya MTF diisi | Gagal init | 1.3 |
| EC-03 | Usia zona 100 bar M30 (≈ 2 hari) | Dipakai apa adanya | 1.2 |
| EC-04 | Chart live di M15 sedangkan LTF M15 | Tidak masalah; EA membaca timeframe dari input, bukan chart | 1.2 |

## Keputusan (2026-10-13)

1. Ambang frekuensi 1,5× acuan.
2. Varian V2 (H4 / M30 / M15) ikut diuji.
3. **Amandemen 2026-10-13 (permintaan user, sesudah hasil IS V1, sebelum OOS/REAL):** varian **V3 H4 / H1 / M30** (zona H1 sama dengan acuan, trigger PA di M30) ikut diuji di IS dengan aturan pilih yang sama. Ekspektasi: frekuensi tidak naik (trigger M30 = setengah kesempatan M15), kualitas mungkin naik.
4. **Amandemen 2026-10-13 (permintaan user, sebelum OOS/REAL):** varian **V4 M30 / M15 / M5** ("scalping" versi user: bias M30, zona M15, trigger M5) ikut diuji di IS dengan aturan pilih yang sama. Ekspektasi: mirip atau lebih buruk dari intraday H1/M15/M5 (spec 34), karena zona tetap M15 dan bias lebih pendek.
